from playwright.sync_api import sync_playwright, Browser
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import tempfile
import os
import io

# Import config
from config import Config, get_config


# ============================================================================
# Math Equation Rendering
# ============================================================================

def create_math_render_html(
    mathml_str: str,
    display_type: str,
    config: Config | None = None
) -> str:
    """
    Create a minimal HTML file for rendering a single equation.
    
    Args:
        mathml_str: MathML string to render
        display_type: 'block' or 'inline'
        config: Configuration object (uses global default if None)
    
    Returns:
        Complete HTML string ready for rendering
    """
    if config is None:
        config = get_config()
    
    mathjax_url = 'https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-svg.js'
    
    # Set padding based on display type
    padding = '20px' if display_type == 'block' else '10px'

    with open(config.paths.html_template, 'r') as f:
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
    temp_dir: str | Path,
    config: Config | None = None
) -> bytes:
    """
    Render a single math equation using Playwright.
    
    Args:
        mathml_str: MathML string to render
        display_type: 'block' or 'inline'
        browser: Playwright browser instance
        temp_dir: Temporary directory for HTML files
        config: Configuration object (uses global default if None)
    
    Returns:
        PNG screenshot as bytes
    """
    if config is None:
        config = get_config()
    
    temp_dir = Path(temp_dir)
    
    # Create temporary HTML file
    with tempfile.NamedTemporaryFile(
        mode='w',
        suffix='.html',
        dir=temp_dir,
        delete=False,
        encoding='utf-8'
    ) as f:
        html_content = create_math_render_html(mathml_str, display_type, config)
        f.write(html_content)
        temp_path = f.name
    
    try:
        # Create new page with config viewport settings
        page = browser.new_page(viewport=config.render.viewport_dict)
        
        # Load the HTML file
        file_url = f'file://{os.path.abspath(temp_path)}'
        page.goto(file_url)
        
        # Wait for MathJax to render using config timeout
        try:
            page.wait_for_selector('svg', timeout=config.render.mathjax_timeout)
        except:
            # Fallback: wait a bit if selector doesn't appear
            page.wait_for_timeout(config.render.short_fallback_timeout)
        
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
    temp_dir: str | Path,
    config: Config | None = None
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
        config: Configuration object (uses global default if None)
    
    Returns:
        (idx, screenshot_bytes) on success or (idx, None, exception) on error
    """
    if config is None:
        config = get_config()
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            screenshot_bytes = render_math_with_playwright(
                mathml_str, display_type, browser, temp_dir, config
            )
            browser.close()
            return (idx, screenshot_bytes)
    except Exception as e:
        return (idx, None, e)


def render_all_math_equations(
    math_elements_data: list[tuple[str, str, str]],
    temp_dir: str | Path,
    config: Config | None = None
) -> list[bytes]:
    """
    Render all math equations using multithreaded Playwright + MathJax.
    
    Args:
        math_elements_data: List of (mathml_str, display_type, alt_text) tuples
        temp_dir: Temporary directory for HTML files
        config: Configuration object (uses global default if None)
    
    Returns:
        List of PNG screenshots as bytes
    """
    if config is None:
        config = get_config()
    
    if not math_elements_data:
        return []
    
    temp_dir = Path(temp_dir)
    
    # Ensure temp directory exists
    temp_dir.mkdir(exist_ok=True, parents=True)
    
    print(f'Rendering {len(math_elements_data)} math equations with {config.render.max_render_threads} threads')
    
    results = {}  # {idx: screenshot_bytes}
    errors = {}   # {idx: error}
    
    # Use ThreadPoolExecutor with configurable workers
    with ThreadPoolExecutor(max_workers=config.render.max_render_threads) as executor:
        # Submit all equations as separate tasks
        futures = {}
        for idx, (mathml_str, display_type, alt_text) in enumerate(math_elements_data):
            future = executor.submit(
                render_equation_worker,
                idx, mathml_str, display_type, alt_text, temp_dir, config
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
                results[idx] = create_placeholder_image(alt_text, config=config)
    
    # Build ordered list of images
    math_images = [results[i] for i in range(len(math_elements_data))]
    print()
    
    if errors:
        print(f'Warning: Failed to render {len(errors)} math equation(s):')
        for idx, error in errors.items():
            print(f'  Equation {idx}: {error}')
    
    return math_images


# ============================================================================
# Utility Functions
# ============================================================================

def create_placeholder_image(
    text: str,
    config: Config | None = None
) -> bytes:
    """
    Create a simple placeholder image for failed rendering.
    
    Args:
        text: Text to display in the placeholder
        config: Configuration object (uses global default if None)
    
    Returns:
        PNG image as bytes
    """
    if config is None:
        config = get_config()
    
    width = config.render.placeholder_width
    height = config.render.placeholder_height
    
    img = Image.new('L', (width, height), color=255)
    draw = ImageDraw.Draw(img)

    font = ImageFont.truetype(str(config.paths.font_sans), 12)
    
    draw.text((10, height//2), f"[Math: {text[:50]}]", fill=0, font=font, anchor="lm")
    
    output = io.BytesIO()
    img.save(output, format='PNG')
    return output.getvalue()
