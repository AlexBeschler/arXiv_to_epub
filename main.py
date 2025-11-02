import re
import os
from pathlib import Path
import argparse

# First Party
import utils

DEFAULT_CONFIG = {
    'output_dir': './output',
    'mathjax_path': './mathjax/es5/tex-mml-svg.js',  # Path to local MathJax
    'temp_dir': './temp_equations',  # Temporary directory for equation HTML files
}

# ============================================================================
# Main Conversion Function
# ============================================================================

def convert_arxiv_to_epub(
    html_url, output_dir=None, mathjax_path=None, temp_dir=None
):
    """
    Main conversion function - orchestrates the entire process.
    
    Args:
        html_url: arXiv HTML URL (e.g., "https://arxiv.org/html/2510.26721v1")
        output_dir: Directory for output EPUB (default: './output')
        mathjax_path: Path to local MathJax file (default: './mathjax/es5/tex-mml-svg.js')
        temp_dir: Temporary directory for equation rendering (default: './temp_equations')
    
    Returns:
        Path to the created EPUB file
    """
    # Use defaults from config
    output_dir = output_dir or DEFAULT_CONFIG['output_dir']
    mathjax_path = mathjax_path or DEFAULT_CONFIG['mathjax_path']
    temp_dir = temp_dir or DEFAULT_CONFIG['temp_dir']
    
    try:
        # Ensure output directory exists
        Path(output_dir).mkdir(exist_ok=True, parents=True)
        
        # Check if MathJax exists
        if not os.path.exists(mathjax_path):
            print(f"\n⚠ WARNING: MathJax not found at {mathjax_path}")
            print("Math equations will use placeholder images.")
            print("To get proper rendering, download MathJax to ./mathjax/")
            mathjax_path = None
        
        # 1. Extract arXiv ID
        arxiv_id = utils.extract_arxiv_id(html_url)
        if not arxiv_id:
            raise ValueError("Could not extract arXiv ID from URL")
        
        # 2. Fetch HTML
        html_content = utils.fetch_html(html_url)
        
        # 3. Parse and extract content (including math, table, and figure rendering)
        content_data = utils.parse_arxiv_content(
            html_content,
            arxiv_id=arxiv_id,  # Pass arxiv_id for constructing image URLs
            mathjax_path=mathjax_path,
            temp_dir=temp_dir
        )
        
        # 4. Build clean HTML
        clean_html = utils.build_clean_html(content_data)
        
        # 5. Create EPUB
        title = content_data['title']
        safe_title = re.sub(r'[^\w\s-]', '', title[:50])
        safe_title = re.sub(r'[-\s]+', '_', safe_title)
        output_path = f"{output_dir}/{arxiv_id}_{safe_title}.epub"
        
        utils.create_clean_epub(
            title, 
            clean_html,
            content_data['math_images'],
            content_data['table_images'],
            content_data['figure_images'],
            output_path
        )
        
        print("\n" + "=" * 70)
        print("✓ CONVERSION COMPLETE!")
        print("=" * 70)
        
        return output_path
        
    except Exception as e:
        print("\n" + "=" * 70)
        print("✗ CONVERSION FAILED")
        print("=" * 70)
        print(f"Error: {e}")
        print("=" * 70)
        import traceback
        traceback.print_exc()
        return None

# ============================================================================
# Command-line Interface
# ============================================================================

if __name__ == "__main__":
    
    parser = argparse.ArgumentParser(
        description='Convert arXiv HTML papers to EPUB with perfect math rendering'
    )
    parser.add_argument('url', help='arXiv HTML URL (e.g., https://arxiv.org/html/2510.26721v1)')
    parser.add_argument('-o', '--output-dir', default='./output', help='Output directory (default: ./output)')
    parser.add_argument('--mathjax-path', default='./mathjax/es5/tex-mml-svg.js', help='Path to local MathJax (default: ./mathjax/es5/tex-mml-svg.js)')
    
    args = parser.parse_args()
    
    convert_arxiv_to_epub(
        args.url,
        output_dir=args.output_dir,
        mathjax_path=args.mathjax_path
    )
