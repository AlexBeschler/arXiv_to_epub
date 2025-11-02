import requests
from bs4 import BeautifulSoup, NavigableString
from ebooklib import epub
from PIL import Image, ImageDraw, ImageFont
from playwright.sync_api import sync_playwright
import io
import re
import os
import tempfile
from pathlib import Path
import html as html_module

# ============================================================================
# Fetch Content
# ============================================================================

def extract_arxiv_id(url):
    """Extract arXiv ID from URL."""
    match = re.search(r'(\d{4}\.\d{5})', url)
    return match.group(1) if match else None

def fetch_html(url):
    """Fetch HTML content from arXiv."""
    response = requests.get(url)
    response.raise_for_status()
    print(f"✓ Fetched {len(response.text):,} HTML characters")
    return response.text

# ============================================================================
# Math Equation Rendering with Playwright + MathJax
# ============================================================================

def extract_mathml_string(math_element):
    """Extract MathML as a string, preserving structure."""
    # Get the raw MathML with namespace
    mathml_str = str(math_element)
    
    # Ensure it has the MathML namespace
    if 'xmlns' not in mathml_str:
        mathml_str = mathml_str.replace('<math', '<math xmlns="http://www.w3.org/1998/Math/MathML"', 1)
    
    return mathml_str

def get_math_display_type(math_element):
    """Determine if math is inline or display (block)."""
    display_attr = math_element.get('display', 'inline')
    return 'block' if display_attr == 'block' else 'inline'

def create_math_render_html(mathml_str, display_type, mathjax_path):
    """Create a minimal HTML file for rendering a single equation."""
    # Use absolute path for MathJax
    mathjax_abs_path = os.path.abspath(mathjax_path)
    
    # Set container width based on display type
    container_width = '700px' if display_type == 'block' else '400px'
    padding = '20px' if display_type == 'block' else '10px'

    with open('templates/html_template.html', 'r') as f:
        html_template: str = ''.join(f.readlines())
        html_template = (
            html_template
                .replace('[mathjax_abs_path]', mathjax_abs_path)
                .replace('[padding]', padding)
                .replace('[container_width]', container_width)
                .replace('[mathml_str]', mathml_str)
        )
    
    return html_template

def render_math_with_playwright(mathml_str, display_type, mathjax_path, browser, temp_dir):
    """Render a single math equation using Playwright and MathJax."""
    
    # Create temporary HTML file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', dir=temp_dir, delete=False, encoding='utf-8') as f:
        html_content = create_math_render_html(mathml_str, display_type, mathjax_path)
        f.write(html_content)
        temp_path = f.name
    
    try:
        # Create new page
        page = browser.new_page()
        
        # Load the HTML file
        file_url = f'file://{os.path.abspath(temp_path)}'
        page.goto(file_url)
        
        # Wait for MathJax to render (wait for the mathjax SVG output)
        try:
            page.wait_for_selector('svg', timeout=5000)
        except:
            # Fallback: wait a bit if selector doesn't appear
            page.wait_for_timeout(2000)
        
        # Screenshot the equation container
        equation_element = page.locator('#equation-container')
        screenshot_bytes = equation_element.screenshot(type='png')
        
        # Close page
        page.close()
        
        return screenshot_bytes
        
    finally:
        # Clean up temp file
        try:
            os.remove(temp_path)
        except:
            pass

def render_all_math_equations(math_elements_data, mathjax_path, temp_dir):
    """Render all math equations using Playwright + MathJax."""
    if not math_elements_data:
        return []
    
    # Ensure temp directory exists
    Path(temp_dir).mkdir(exist_ok=True, parents=True)
    
    math_images = []
    
    # Start Playwright browser (reuse for all equations)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless = True)
        render_errors = []

        print('Rendering math equations')
        
        for idx, (mathml_str, display_type, alt_text) in enumerate(math_elements_data):
            try:
                screenshot_bytes = render_math_with_playwright(
                    mathml_str, display_type, mathjax_path, browser, temp_dir
                )
                math_images.append(screenshot_bytes)
            except Exception as e:
                render_errors.append({
                    'idx': idx,
                    'error': e
                })
                # Create a placeholder image
                math_images.append(create_placeholder_image(alt_text))
        
        if len(render_errors) > 0:
            print('⚠ Warning: Failed to render math equation(s): ')
            print('\n'.join([str(x) for x in render_errors]))
        
        browser.close()

    return math_images

def create_placeholder_image(text, width=400, height=100):
    """Create a simple placeholder image for failed math rendering."""
    img = Image.new('L', (width, height), color=255)
    draw = ImageDraw.Draw(img)

    font = ImageFont.truetype("fonts/DejaVuSans.ttf", 12)
    
    draw.text((10, height//2), f"[Math: {text[:50]}]", fill=0, font=font, anchor="lm")
    
    output = io.BytesIO()
    img.save(output, format='PNG')
    return output.getvalue()

# ============================================================================
# Table Handling
# ============================================================================

def get_table_dimensions(table_element):
    """Get the dimensions of a table (rows, columns)."""
    rows = table_element.find_all('tr')
    if not rows:
        return 0, 0
    
    max_cols = 0
    for row in rows:
        cols = len(row.find_all(['td', 'th']))
        max_cols = max(max_cols, cols)
    
    return len(rows), max_cols

def fix_image_urls_in_html(html_str, arxiv_id):
    """Convert relative image URLs to absolute arXiv URLs in HTML string."""
    if not arxiv_id:
        return html_str
    
    base_url = f'https://arxiv.org/html/{arxiv_id}/'
    
    def replace_src(match):
        quote = match.group(1)  # Which quote character (" or ')
        url = match.group(2)     # The URL
        
        # If already absolute, don't change
        if url.startswith('http'):
            return match.group(0)
        
        # Convert relative to absolute
        clean_url = url.lstrip('/')
        return f'src={quote}{base_url}{clean_url}{quote}'
    
    # Pattern matches src="..." or src='...'
    return re.sub(r'src=(["\'])([^"\']+)\1', replace_src, html_str)

def create_figure_render_html(figure_html, css_content):
    """Create HTML page for rendering a figure."""
    return f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            margin: 0;
            padding: 20px;
            background: white;
            font-family: Georgia, serif;
        }}
        
        /* Generic figure styling */
        figure {{
            margin: 1em auto;
            text-align: center;
            max-width: 1200px;
        }}
        
        figure img {{
            max-width: 100%;
            height: auto;
            display: block;
            margin: 0.5em auto;
        }}
        
        figcaption {{
            font-size: 0.9em;
            font-style: italic;
            margin-top: 0.5em;
            text-align: center;
        }}
        
        /* Standalone image styling */
        .standalone-image {{
            margin: 1em auto;
            text-align: center;
            max-width: 1200px;
        }}
        
        .standalone-image img {{
            max-width: 100%;
            height: auto;
            display: block;
            margin: 0 auto;
        }}
        
        {css_content}
    </style>
</head>
<body>
    {figure_html}
</body>
</html>'''

def render_figure_with_playwright(figure_html, css_content, browser, temp_dir):
    """Render a figure using Playwright, allowing browser to fetch images."""
    
    # Create temporary HTML file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', dir=temp_dir, delete=False, encoding='utf-8') as f:
        html_content = create_figure_render_html(figure_html, css_content)
        f.write(html_content)
        temp_path = f.name
    
    try:
        # Create new page
        page = browser.new_page(viewport={'width': 1400, 'height': 2000})
        
        # Load the HTML file
        file_url = f'file://{os.path.abspath(temp_path)}'
        page.goto(file_url, wait_until='networkidle')
        
        # Wait for images to load
        try:
            page.wait_for_load_state('networkidle', timeout=10000)
        except:
            page.wait_for_timeout(3000)
        
        # Screenshot the figure or image container
        # Try to locate figure first, fallback to body for standalone images
        try:
            element = page.locator('figure').first
            screenshot_bytes = element.screenshot(type='png')
        except:
            # Fallback for standalone images
            element = page.locator('.standalone-image').first
            screenshot_bytes = element.screenshot(type='png')
        
        # Close page
        page.close()
        
        return screenshot_bytes
        
    finally:
        # Clean up temp file
        try:
            os.remove(temp_path)
        except:
            pass

def render_all_figures(figure_elements_data, css_content, temp_dir):
    """Render all figures and images using Playwright."""
    if not figure_elements_data:
        return []
    
    # Ensure temp directory exists
    Path(temp_dir).mkdir(exist_ok=True, parents=True)
    
    figure_images = []
    
    # Start Playwright browser (reuse for all figures)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        render_errors = []

        print(f'Rendering {len(figure_elements_data)} figure(s)/image(s) with Playwright')
        
        for idx, figure_html in enumerate(figure_elements_data):
            try:
                screenshot_bytes = render_figure_with_playwright(
                    figure_html, css_content, browser, temp_dir
                )
                figure_images.append(screenshot_bytes)
            except Exception as e:
                render_errors.append({
                    'idx': idx,
                    'error': str(e)
                })
                # Create a placeholder
                figure_images.append(create_placeholder_image(f"Figure/Image {idx+1}"))
        
        if len(render_errors) > 0:
            print('⚠ Warning: Failed to render figure(s)/image(s): ')
            print('\n'.join([str(x) for x in render_errors]))
        
        browser.close()

    return figure_images
    """Create a minimal HTML file for rendering a table."""
    
    # Generic table CSS that works with any table structure
    generic_css = """
        /* Generic table styling for any structure */
        table {
            border-collapse: collapse;
            font-size: 0.85em;
            margin: 1em auto;
        }
        
        table th,
        table td {
            padding: 0.5em;
            border: 1px solid #333;
            text-align: left;
            vertical-align: top;
        }
        
        table th {
            font-weight: bold;
            background-color: #e0e0e0;
        }
        
        table img {
            max-width: 100%;
            height: auto;
            display: block;
            margin: 2px auto;
        }
        
        thead th {
            border-bottom: 2px solid #000;
        }
    """
    
    html_template = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            margin: 0;
            padding: 20px;
            background: white;
            font-family: Georgia, serif;
        }}
        
        {generic_css}
        
        {css_content}
    </style>
</head>
<body>
    {table_html}
</body>
</html>'''
    return html_template

def render_table_with_playwright(table_html, css_content, browser, temp_dir):
    """Render a table using Playwright, allowing browser to fetch images from arXiv."""
    
    # Create temporary HTML file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', dir=temp_dir, delete=False, encoding='utf-8') as f:
        html_content = create_table_render_html(table_html, css_content)
        f.write(html_content)
        temp_path = f.name
    
    try:
        # Create new page with larger viewport for tables
        page = browser.new_page(viewport={'width': 1400, 'height': 2000})
        
        # Load the HTML file
        file_url = f'file://{os.path.abspath(temp_path)}'
        page.goto(file_url, wait_until='networkidle')
        
        # Wait for images to load
        try:
            page.wait_for_load_state('networkidle', timeout=10000)
        except:
            # If timeout, just wait a bit
            page.wait_for_timeout(3000)
        
        # Screenshot the table
        table_element = page.locator('table')
        screenshot_bytes = table_element.screenshot(type='png')
        
        # Close page
        page.close()
        
        return screenshot_bytes
        
    finally:
        # Clean up temp file
        try:
            os.remove(temp_path)
        except:
            pass

def render_all_tables(table_elements_data, css_content, temp_dir):
    """Render all tables using Playwright."""
    if not table_elements_data:
        return []
    
    # Ensure temp directory exists
    Path(temp_dir).mkdir(exist_ok=True, parents=True)
    
    table_images = []
    
    # Start Playwright browser (reuse for all tables)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        render_errors = []

        print(f'Rendering {len(table_elements_data)} table(s) with Playwright')
        
        for idx, table_html in enumerate(table_elements_data):
            try:
                screenshot_bytes = render_table_with_playwright(
                    table_html, css_content, browser, temp_dir
                )
                table_images.append(screenshot_bytes)
            except Exception as e:
                render_errors.append({
                    'idx': idx,
                    'error': str(e)
                })
                # Create a placeholder
                table_images.append(create_placeholder_image(f"Table {idx+1}"))
        
        if len(render_errors) > 0:
            print('⚠ Warning: Failed to render table(s): ')
            print('\n'.join([str(x) for x in render_errors]))
        
        browser.close()

    return table_images

# ============================================================================
# Content Parsing
# ============================================================================

def extract_text_content(element):
    """Recursively extract text from an element, skipping script/style tags and math."""
    if element.name in ['script', 'style', 'math']:
        return ''
    
    if isinstance(element, NavigableString):
        return str(element)
    
    text = ''
    for child in element.children:
        text += extract_text_content(child)
    return text

def parse_arxiv_content(html_content, arxiv_id=None, mathjax_path=None, temp_dir=None):
    """
    Parse arXiv HTML and extract content elements in order.
    Returns content items with MathML ready for rendering.
    """
    print("Parsing HTML content...")
    soup = BeautifulSoup(html_content, 'html.parser')
    
    content_items = []
    title = None
    math_elements_data = []  # Store MathML strings for batch rendering
    table_elements_data = []  # Store table HTML for batch rendering
    figure_elements_data = []  # Store figure/image HTML for batch rendering
    
    # Extract title
    h1 = soup.find('h1')
    if h1:
        title = extract_text_content(h1).strip()
    
    # Find the main body content
    body = soup.find('body') or soup
    
    # Track counts
    figure_count = 0
    math_count = 0
    table_count = 0
    
    # Walk through all elements in order
    for element in body.find_all(['h1', 'h2', 'h3', 'h4', 'p', 'img', 'figure', 'table', 'math']):
        
        # Skip if inside a script/style tag
        if element.find_parent(['script', 'style']):
            continue
        
        # Skip if inside a table or figure (but not if this element IS a table/figure)
        # This prevents duplicate content from nested elements that are already captured in screenshots
        if element.name not in ['table', 'figure'] and element.find_parent(['table', 'figure']):
            continue
        
        # Skip <img> elements inside <figure> - they'll be part of the figure screenshot
        if element.name == 'img' and element.find_parent('figure'):
            continue
        
        # Headings
        if element.name in ['h1', 'h2', 'h3', 'h4']:
            text = extract_text_content(element).strip()
            if text and len(text) > 2:
                level = int(element.name[1])
                content_items.append({
                    'type': 'heading',
                    'level': level,
                    'content': text
                })
        
        # Paragraphs - check for inline math and preserve order
        elif element.name == 'p':
            # Check if paragraph contains math
            math_elements = element.find_all('math')
            
            if math_elements:
                # Process paragraph with inline math - preserve order
                segments = []
                processed = set()  # Track processed elements
                
                # Walk through direct children in order
                for child in element.children:
                    if child in processed:
                        continue
                        
                    if hasattr(child, 'name') and child.name == 'math':
                        # This is a math element
                        mathml_str = extract_mathml_string(child)
                        display_type = get_math_display_type(child)
                        alt_text = child.get_text(strip=True)[:100]
                        
                        math_elements_data.append((mathml_str, display_type, alt_text))
                        
                        segments.append({
                            'type': 'math',
                            'index': math_count,
                            'display': display_type,
                            'alt': alt_text
                        })
                        math_count += 1
                        processed.add(child)
                        
                    elif isinstance(child, NavigableString):
                        # This is direct text content
                        text = str(child).strip()
                        if text:
                            segments.append({
                                'type': 'text',
                                'content': text
                            })
                        processed.add(child)
                        
                    elif hasattr(child, 'name') and child.name not in ['script', 'style']:
                        # Other inline elements - extract their text
                        text = extract_text_content(child).strip()
                        if text:
                            segments.append({
                                'type': 'text',
                                'content': text
                            })
                        processed.add(child)
                
                # Only add if we have substantial content
                total_text = ''.join(seg.get('content', '') for seg in segments if seg['type'] == 'text')
                if segments and len(total_text) > 10:
                    content_items.append({
                        'type': 'paragraph_with_math',
                        'segments': segments
                    })
            else:
                text = extract_text_content(element).strip()
                if text and len(text) > 20:
                    content_items.append({
                        'type': 'paragraph',
                        'content': text
                    })
        
        # Standalone math elements (display equations)
        elif element.name == 'math' and not element.find_parent('p'):
            mathml_str = extract_mathml_string(element)
            display_type = get_math_display_type(element)
            alt_text = element.get_text(strip=True)[:100]
            
            math_elements_data.append((mathml_str, display_type, alt_text))
            
            content_items.append({
                'type': 'math',
                'index': math_count,
                'display': display_type,
                'alt': alt_text
            })
            math_count += 1
        
        # Figures (will be rendered with Playwright)
        elif element.name == 'figure':
            # Extract original figure HTML (preserves structure, captions, sub-images)
            figure_html = str(element)
            
            # Fix relative image URLs to absolute arXiv URLs
            figure_html = fix_image_urls_in_html(figure_html, arxiv_id)
            
            figure_elements_data.append(figure_html)
            
            content_items.append({
                'type': 'figure',
                'index': figure_count
            })
            figure_count += 1
        
        # Standalone images (not inside figures, will be rendered with Playwright)
        elif element.name == 'img':
            # Extract image HTML
            img_html = str(element)
            
            # Fix relative image URLs to absolute arXiv URLs
            img_html = fix_image_urls_in_html(img_html, arxiv_id)
            
            # Wrap in a container div for rendering
            img_html = f'<div class="standalone-image">{img_html}</div>'
            
            figure_elements_data.append(img_html)
            
            content_items.append({
                'type': 'image',
                'index': figure_count
            })
            figure_count += 1
        
        # Tables
        elif element.name == 'table':
            rows, cols = get_table_dimensions(element)
            
            # Extract original table HTML (preserves all structure, attributes, classes)
            table_html = str(element)
            
            # Fix relative image URLs to absolute arXiv URLs
            table_html = fix_image_urls_in_html(table_html, arxiv_id)
            
            table_elements_data.append(table_html)
            
            content_items.append({
                'type': 'table_image',
                'index': table_count,
                'rows': rows,
                'cols': cols
            })
            table_count += 1
    
    # Now render all math equations with Playwright
    math_images = []
    if math_elements_data and mathjax_path and temp_dir:
        math_images = render_all_math_equations(math_elements_data, mathjax_path, temp_dir)
    
    # Render all tables with Playwright
    table_images = []
    if table_elements_data and temp_dir:
        # Load CSS content for table rendering
        try:
            with open('templates/css_template.css', 'r') as f:
                css_content = f.read()
        except:
            # Fallback to basic CSS if file not found
            css_content = """
                table.ereader-table { border-collapse: collapse; }
                table.ereader-table th, table.ereader-table td { 
                    border: 1px solid #333; 
                    padding: 8px; 
                }
            """
        
        table_images = render_all_tables(table_elements_data, css_content, temp_dir)
    
    # Render all figures and images with Playwright
    figure_images = []
    if figure_elements_data and temp_dir:
        # Load CSS content for figure rendering
        try:
            with open('templates/css_template.css', 'r') as f:
                css_content = f.read()
        except:
            css_content = ""
        
        figure_images = render_all_figures(figure_elements_data, css_content, temp_dir)
    
    return {
        'title': title or 'Untitled arXiv Paper',
        'content': content_items,
        'math_images': math_images,
        'table_images': table_images,
        'figure_images': figure_images
    }

# ============================================================================
# HTML Building
# ============================================================================

def build_clean_html(content_data):
    """Build clean, simple HTML from extracted content."""
    html_parts = []
    html_parts.append('<html xmlns="http://www.w3.org/1999/xhtml">')
    html_parts.append('<head>')
    html_parts.append(f'<title>{html_module.escape(content_data["title"])}</title>')
    html_parts.append('</head>')
    html_parts.append('<body>')
    
    # Process content items in order
    for item in content_data['content']:
        if item['type'] == 'heading':
            level = item['level']
            html_parts.append(f'<h{level}>{html_module.escape(item["content"])}</h{level}>')
        
        elif item['type'] == 'paragraph':
            html_parts.append(f'<p>{html_module.escape(item["content"])}</p>')
        
        elif item['type'] == 'paragraph_with_math':
            # Build paragraph with inline math
            para_parts = ['<p>']
            for segment in item['segments']:
                if segment['type'] == 'text':
                    para_parts.append(html_module.escape(segment['content']))
                elif segment['type'] == 'math':
                    math_index = segment['index']
                    alt_text = html_module.escape(segment.get('alt', 'Mathematical equation'))
                    para_parts.append(
                        f'<img src="images/math_{math_index}.png" alt="{alt_text}" class="math-inline"/>'
                    )
            para_parts.append('</p>')
            html_parts.append(''.join(para_parts))
        
        elif item['type'] == 'figure':
            fig_index = item['index']
            html_parts.append(
                f'<div class="figure">'
                f'<img src="images/figure_{fig_index}.png" alt="Figure {fig_index + 1}"/>'
                f'</div>'
            )
        
        elif item['type'] == 'image':
            img_index = item['index']
            html_parts.append(
                f'<div class="figure">'
                f'<img src="images/figure_{img_index}.png" alt="Image {img_index + 1}"/>'
                f'</div>'
            )
        
        elif item['type'] == 'math':
            math_index = item['index']
            display_type = item.get('display', 'inline')
            alt_text = html_module.escape(item.get('alt', 'Mathematical equation'))
            
            # Display math as block
            html_parts.append(
                f'<div class="math-display">'
                f'<img src="images/math_{math_index}.png" alt="{alt_text}" class="math-display-img"/>'
                f'</div>'
            )
        
        elif item['type'] == 'table_image':
            table_index = item['index']
            rows, cols = item.get('rows', 0), item.get('cols', 0)
            html_parts.append(
                f'<div class="table-image">'
                f'<img src="images/table_{table_index}.png" alt="Table with {rows} rows and {cols} columns"/>'
                f'<p class="caption">Table {table_index + 1}</p>'
                f'</div>'
            )
    
    html_parts.append('</body>')
    html_parts.append('</html>')
    
    html_content = '\n'.join(html_parts)
    return html_content

# ============================================================================
# EPUB Creation
# ============================================================================

def create_clean_epub(title, html_content, math_images, table_images, figure_images, output_path):
    """Create EPUB with clean CSS and support for math equations, tables, and figures."""
    
    book = epub.EpubBook()
    book.set_identifier(f'arxiv_{Path(output_path).stem}')
    book.set_title(title)
    book.set_language('en')
    book.add_author('arXiv Paper')
    
    # Enhanced CSS with inline/display math support
    with open('templates/css_template.css', 'r') as f:
        css = ''.join(f.readlines())
    
    css_item = epub.EpubItem(
        uid="style",
        file_name="style/style.css",
        media_type="text/css",
        content=css
    )
    book.add_item(css_item)
    
    # Add math equation images
    for idx, math_bytes in enumerate(math_images):
        try:
            img_item = epub.EpubImage(
                uid=f'math_{idx}',
                file_name=f'images/math_{idx}.png',
                media_type='image/png',
                content=math_bytes
            )
            book.add_item(img_item)
        except Exception as e:
            print(f"  ⚠ Warning: Failed to process math {idx}: {e}")
    
    # Add table images
    for idx, table_bytes in enumerate(table_images):
        try:
            img_item = epub.EpubImage(
                uid=f'table_{idx}',
                file_name=f'images/table_{idx}.png',
                media_type='image/png',
                content=table_bytes
            )
            book.add_item(img_item)
        except Exception as e:
            print(f"  ⚠ Warning: Failed to process table {idx}: {e}")
    
    # Add figure/image images (rendered with Playwright)
    for idx, figure_bytes in enumerate(figure_images):
        try:
            img_item = epub.EpubImage(
                uid=f'figure_{idx}',
                file_name=f'images/figure_{idx}.png',
                media_type='image/png',
                content=figure_bytes
            )
            book.add_item(img_item)
        except Exception as e:
            print(f"  ⚠ Warning: Failed to process figure {idx}: {e}")
    
    # Create main chapter
    chapter = epub.EpubHtml(
        title=title,
        file_name='content.xhtml',
        lang='en'
    )
    chapter.content = html_content
    chapter.add_item(css_item)
    book.add_item(chapter)
    
    # Set up navigation
    book.toc = (chapter,)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ['nav', chapter]
    
    # Write EPUB
    epub.write_epub(output_path, book)
    print(f"✓ EPUB created!")
