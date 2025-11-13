"""
Module for parsing arXiv HTML content and extracting structured data.
"""
from bs4 import BeautifulSoup, NavigableString
import re

# ============================================================================
# Content Extraction
# ============================================================================

def extract_text_content(element) -> str:
    """
    Recursively extract text from an element, skipping script/style tags and math.
    
    Args:
        element: BeautifulSoup element
    
    Returns:
        Extracted text content
    """
    if element.name in ['script', 'style', 'math']:
        return ''
    
    if isinstance(element, NavigableString):
        return str(element)
    
    text = ''
    for child in element.children:
        text += extract_text_content(child)
    return text


def extract_mathml_string(math_element) -> str:
    """
    Extract MathML as a string, preserving structure.
    
    Args:
        math_element: BeautifulSoup element containing MathML
    
    Returns:
        MathML string with namespace
    """
    # Get the raw MathML with namespace
    mathml_str = str(math_element)
    
    # Ensure it has the MathML namespace
    if 'xmlns' not in mathml_str:
        mathml_str = mathml_str.replace(
            '<math',
            '<math xmlns="http://www.w3.org/1998/Math/MathML"',
            1
        )
    
    return mathml_str


def get_math_display_type(math_element) -> str:
    """
    Determine if math is inline or display (block).
    
    Args:
        math_element: BeautifulSoup element containing MathML
    
    Returns:
        'block' or 'inline'
    """
    display_attr = math_element.get('display', 'inline')
    return 'block' if display_attr == 'block' else 'inline'


def get_table_dimensions(table_element) -> tuple[int, int]:
    """
    Get the dimensions of a table (rows, columns).
    
    Args:
        table_element: BeautifulSoup table element
    
    Returns:
        Tuple of (num_rows, num_cols)
    """
    rows = table_element.find_all('tr')
    if not rows:
        return 0, 0
    
    max_cols = 0
    for row in rows:
        cols = len(row.find_all(['td', 'th']))
        max_cols = max(max_cols, cols)
    
    return len(rows), max_cols


def fix_image_urls_in_html(html_str: str, arxiv_id: str | None) -> str:
    """
    Convert relative image URLs to absolute arXiv URLs in HTML string.
    
    Args:
        html_str: HTML string containing image tags
        arxiv_id: arXiv paper ID (e.g., "2510.26721")
    
    Returns:
        HTML string with absolute URLs
    """
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


# ============================================================================
# Main Parsing Function
# ============================================================================

def parse_arxiv_content(
    html_content: str,
    arxiv_id: str | None = None,
    temp_dir: str | None = None
) -> dict:
    """
    Parse arXiv HTML and extract content elements in order.
    Returns content items with data ready for rendering.
    
    Args:
        html_content: Raw HTML content from arXiv
        arxiv_id: arXiv paper ID for constructing image URLs
        temp_dir: Temporary directory for rendering operations
    
    Returns:
        Dictionary containing:
            - title: Paper title
            - content: List of content items (paragraphs, headings, math, etc.)
            - math_elements_data: List of (mathml_str, display_type, alt_text) tuples
            - table_elements_data: List of table HTML strings
            - figure_elements_data: List of figure/image HTML strings
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
            # Skip figures that contain tables - render the table directly instead
            if element.find('table'):
                continue
            
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
    
    return {
        'title': title or 'Untitled arXiv Paper',
        'content': content_items,
        'math_elements_data': math_elements_data,
        'table_elements_data': table_elements_data,
        'figure_elements_data': figure_elements_data
    }
