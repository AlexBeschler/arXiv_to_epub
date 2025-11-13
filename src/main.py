import re
from pathlib import Path
import argparse

# First Party
from utils import process_arxiv_paper, clean_up
from epub_builder import create_epub

DEFAULT_CONFIG = {
    'output_dir': './output',
    'temp_dir': './temp_equations',  # Temporary directory for equation HTML files
}

# ============================================================================
# Main Conversion Function
# ============================================================================

def convert_arxiv_to_epub(
    html_url: str,
    output_dir: str | None = None,
    temp_dir: str | None = None
) -> str | None:
    """
    Main conversion function - orchestrates the entire process.
    
    Args:
        html_url: arXiv HTML URL (e.g., "https://arxiv.org/html/2510.26721v1")
        output_dir: Directory for output EPUB (default: './output')
        temp_dir: Temporary directory for equation rendering (default: './temp_equations')
    
    Returns:
        Path to the created EPUB file, or None if conversion failed
    """
    # Use defaults from config
    output_dir = output_dir or DEFAULT_CONFIG['output_dir']
    temp_dir = temp_dir or DEFAULT_CONFIG['temp_dir']
    
    try:
        # Ensure output directory exists
        Path(output_dir).mkdir(exist_ok=True, parents=True)
        
        # Process the arXiv paper (fetch, parse, render)
        content_data = process_arxiv_paper(html_url, output_dir, temp_dir)
        
        # Generate output filename
        title = content_data['title']
        arxiv_id = content_data['arxiv_id']
        safe_title = re.sub(r'[^\w\s-]', '', title[:50])
        safe_title = re.sub(r'[-\s]+', '_', safe_title)
        output_path = str(Path(output_dir) / f"{arxiv_id}_{safe_title}.epub")

        # Create EPUB
        create_epub(title, content_data, output_path)
        
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
    
    args = parser.parse_args()
    
    convert_arxiv_to_epub(
        args.url,
        output_dir=args.output_dir
    )

    clean_up()
