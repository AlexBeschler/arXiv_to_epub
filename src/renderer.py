"""
Module for rendering math equations, tables, and figures using Playwright.
"""
from playwright.sync_api import sync_playwright, Browser
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import tempfile
import os
import io

# ============================================================================
# Math Equation Rendering
# ============================================================================

def create_math_render_html(mathml_str: str, display_type: str) -> str:
    """
    Create a minimal HTML file for rendering a single equation.
    
    Args:
        mathml_str: MathML string to render
        display_type: 'block' or 'inline'
    
    Returns:
        Complete HTML string ready for rendering
    """
    mathjax_url = 'https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-svg.js'
    
    # Set padding based on display type
    padding = '20px' if display_type == 'block' else '10px'

    with open('templates/html_template.html', 'r') as f:
        html_template: str = ''.join(f.readlines())
        html_template = (
            html_template
                .replace('[mathjax_abs_path]', mathjax_url)
                .replace('[padding]', padding)
                .replace('[mathml_str]', mathml_str)
        )
    
    return html_template


def render_math_with_playwright(
    mathml_str: str,
    display_type: str,
    browser: Browser,
    temp_dir: str
) -> bytes:
    """
    Render a single math equation using Playwright.
    
    Args:
        mathml_str: MathML string to render
        display_type: 'block' or 'inline'
        browser: Playwright browser instance
        temp_dir: Temporary directory for HTML files
    
    Returns:
        PNG screenshot as bytes
    """
    # Create temporary HTML file
    with tempfile.NamedTemporaryFile(
        mode='w',
        suffix='.html',
        dir=temp_dir,
        delete=False,
        encoding='utf-8'
    ) as f:
        html_content = create_math_render_html(mathml_str, display_type)
        f.write(html_content)
        temp_path = f.name
    
    try:
        # Create new page with device scale factor for sharper rendering
        page = browser.new_page(
            viewport={'width': 2400, 'height': 2000, 'device_scale_factor': 2}
        )
        
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


def render_equation_worker(
    idx: int,
    mathml_str: str,
    display_type: str,
    alt_text: str,
    temp_dir: str
) -> tuple:
    """
    Worker function for rendering a single equation in a thread.
    Creates its own browser instance to ensure thread safety.
    
    Args:
        idx: Index of the equation
        mathml_str: MathML string to render
        display_type: 'block' or 'inline'
        alt_text: Alternative text for accessibility
        temp_dir: Temporary directory for HTML files
    
    Returns:
        (idx, screenshot_bytes) on success or (idx, None, exception) on error
    """
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            screenshot_bytes = render_math_with_playwright(
                mathml_str, display_type, browser, temp_dir
            )
            browser.close()
            return (idx, screenshot_bytes)
    except Exception as e:
        return (idx, None, e)


def render_all_math_equations(
    math_elements_data: list[tuple[str, str, str]],
    temp_dir: str
) -> list[bytes]:
    """
    Render all math equations using multithreaded Playwright + MathJax.
    
    Args:
        math_elements_data: List of (mathml_str, display_type, alt_text) tuples
        temp_dir: Temporary directory for HTML files
    
    Returns:
        List of PNG screenshots as bytes
    """
    if not math_elements_data:
        return []
    
    # Ensure temp directory exists
    Path(temp_dir).mkdir(exist_ok=True, parents=True)
    
    print(f'Rendering {len(math_elements_data)} math equations with 5 threads')
    
    results = {}  # {idx: screenshot_bytes}
    errors = {}   # {idx: error}
    
    # Use ThreadPoolExecutor with 5 workers
    with ThreadPoolExecutor(max_workers=5) as executor:
        # Submit all equations as separate tasks
        futures = {}
        for idx, (mathml_str, display_type, alt_text) in enumerate(math_elements_data):
            future = executor.submit(
                render_equation_worker,
                idx, mathml_str, display_type, alt_text, temp_dir
            )
            futures[future] = idx
        
        # Collect results as they complete
        for completed, future in enumerate(as_completed(futures), start=1):
            print(f'\r   Completed {completed}/{len(math_elements_data)}', end='')
            result = future.result()
            if len(result) == 2:
                # Success: (idx, screenshot_bytes)
                idx, screenshot_bytes = result
                results[idx] = screenshot_bytes
            else:
                # Error: (idx, None, exception)
                idx, _, error = result
                errors[idx] = error
                # Get alt_text for placeholder
                _, _, alt_text = math_elements_data[idx]
                results[idx] = create_placeholder_image(alt_text)
    
    # Build ordered list of images
    math_images = [results[i] for i in range(len(math_elements_data))]
    print()
    
    if errors:
        print(f'Warning: Failed to render {len(errors)} math equation(s):')
        for idx, error in errors.items():
            print(f'  Equation {idx}: {error}')
    
    return math_images


# ============================================================================
# Table Rendering
# ============================================================================

def create_table_render_html(table_html: str, css_content: str) -> str:
    """
    Create a minimal HTML file for rendering a table.
    
    Args:
        table_html: HTML string of the table
        css_content: CSS content for styling
    
    Returns:
        Complete HTML string ready for rendering
    """
    # Generic table CSS that works with any table structure
    with open('templates/table_template.css', 'r') as f:
        generic_css: str = ''.join(f.readlines())
    
    with open('templates/table_template.html', 'r') as f:
        html_template: str = ''.join(f.readlines())
        html_template = (
            html_template
                .replace('[generic_css]', generic_css)
                .replace('[css_content]', css_content)
                .replace('[table_html]', table_html)
        )

    return html_template


def render_table_with_playwright(
    table_html: str,
    css_content: str,
    browser: Browser,
    temp_dir: str
) -> bytes:
    """
    Render a table using Playwright, allowing browser to fetch images from arXiv.
    
    Args:
        table_html: HTML string of the table
        css_content: CSS content for styling
        browser: Playwright browser instance
        temp_dir: Temporary directory for HTML files
    
    Returns:
        PNG screenshot as bytes
    """
    # Create temporary HTML file
    with tempfile.NamedTemporaryFile(
        mode='w',
        suffix='.html',
        dir=temp_dir,
        delete=False,
        encoding='utf-8'
    ) as f:
        html_content = create_table_render_html(table_html, css_content)
        f.write(html_content)
        temp_path = f.name
    
    try:
        # Create new page with larger viewport for tables
        page = browser.new_page(
            viewport={'width': 2400, 'height': 2000, 'device_scale_factor': 2}
        )
        
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


def render_all_tables(
    table_elements_data: list[str],
    css_content: str,
    temp_dir: str
) -> list[bytes]:
    """
    Render all tables using Playwright.
    
    Args:
        table_elements_data: List of table HTML strings
        css_content: CSS content for styling
        temp_dir: Temporary directory for HTML files
    
    Returns:
        List of PNG screenshots as bytes
    """
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
            print('Warning: Failed to render table(s): ')
            print('\n'.join([str(x) for x in render_errors]))
        
        browser.close()

    return table_images


# ============================================================================
# Figure/Image Rendering
# ============================================================================

def create_figure_render_html(figure_html: str, css_content: str) -> str:
    """
    Create HTML page for rendering a figure.
    
    Args:
        figure_html: HTML string of the figure
        css_content: CSS content for styling
    
    Returns:
        Complete HTML string ready for rendering
    """
    with open('templates/figure_template.html', 'r') as f:
        html_template: str = ''.join(f.readlines())
        html_template = (
            html_template
                .replace('[css_content]', css_content)
                .replace('[figure_html]', figure_html)
        )

    return html_template


def render_figure_with_playwright(
    figure_html: str,
    css_content: str,
    browser: Browser,
    temp_dir: str
) -> bytes:
    """
    Render a figure using Playwright, allowing browser to fetch images.
    
    Args:
        figure_html: HTML string of the figure
        css_content: CSS content for styling
        browser: Playwright browser instance
        temp_dir: Temporary directory for HTML files
    
    Returns:
        PNG screenshot as bytes
    """
    # Create temporary HTML file
    with tempfile.NamedTemporaryFile(
        mode='w',
        suffix='.html',
        dir=temp_dir,
        delete=False,
        encoding='utf-8'
    ) as f:
        html_content = create_figure_render_html(figure_html, css_content)
        f.write(html_content)
        temp_path = f.name
    
    try:
        # Create new page
        page = browser.new_page(
            viewport={'width': 2400, 'height': 2000, 'device_scale_factor': 2}
        )
        
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


def render_all_figures(
    figure_elements_data: list[str],
    css_content: str,
    temp_dir: str
) -> list[bytes]:
    """
    Render all figures and images using Playwright.
    
    Args:
        figure_elements_data: List of figure/image HTML strings
        css_content: CSS content for styling
        temp_dir: Temporary directory for HTML files
    
    Returns:
        List of PNG screenshots as bytes
    """
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
            print('Warning: Failed to render figure(s)/image(s): ')
            print('\n'.join([str(x) for x in render_errors]))
        
        browser.close()

    return figure_images


# ============================================================================
# Utility Functions
# ============================================================================

def create_placeholder_image(text: str, width: int = 400, height: int = 100) -> bytes:
    """
    Create a simple placeholder image for failed rendering.
    
    Args:
        text: Text to display in the placeholder
        width: Image width in pixels
        height: Image height in pixels
    
    Returns:
        PNG image as bytes
    """
    img = Image.new('L', (width, height), color=255)
    draw = ImageDraw.Draw(img)

    font = ImageFont.truetype("fonts/DejaVuSans.ttf", 12)
    
    draw.text((10, height//2), f"[Math: {text[:50]}]", fill=0, font=font, anchor="lm")
    
    output = io.BytesIO()
    img.save(output, format='PNG')
    return output.getvalue()
