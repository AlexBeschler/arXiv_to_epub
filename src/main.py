import re
from pathlib import Path
import argparse

# First Party
from config import Config, PathConfig, RenderConfig
from utils import process_arxiv_paper, clean_up
from epub_builder import create_epub

# ============================================================================
# Main Conversion Function
# ============================================================================

def convert_arxiv_to_epub(
    html_url: str,
    config: Config | None = None
) -> str | None:
    """
    Main conversion function - orchestrates the entire process.
    
    Args:
        html_url: arXiv HTML URL (e.g., "https://arxiv.org/html/2510.26721v1")
        config: Configuration object (creates default if None)
    
    Returns:
        Path to the created EPUB file, or None if conversion failed
    """
    # Use provided config or create default
    if config is None:
        config = Config()
    
    # Validate config before starting
    issues = config.validate()
    if issues:
        print("Configuration issues:")
        for issue in issues:
            print(f"  - {issue}")
        return None
    
    try:
        # Ensure directories exist
        config.paths.ensure_directories()
        
        # Process the arXiv paper (fetch, parse, render)
        content_data = process_arxiv_paper(
            html_url,
            output_dir=str(config.paths.output_dir),
            temp_dir=str(config.paths.temp_dir),
            config=config  # Pass config through pipeline
        )
        
        # Generate output filename
        title = content_data['title']
        arxiv_id = content_data['arxiv_id']
        
        # Use config for title truncation
        safe_title = re.sub(r'[^\w\s-]', '', title[:config.parsing.max_title_length_for_filename])
        safe_title = re.sub(r'[-\s]+', '_', safe_title)
        output_path = config.paths.output_dir / f"{arxiv_id}_{safe_title}.epub"

        # Create EPUB
        create_epub(title, content_data, str(output_path), config=config)
        
        print("\n" + "=" * 70)
        print("✓ CONVERSION COMPLETE!")
        print("=" * 70)
        print(f"Output: {output_path}")
        
        return str(output_path)
        
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
    parser.add_argument(
        'url',
        help='arXiv HTML URL (e.g., https://arxiv.org/html/2510.26721v1)'
    )
    parser.add_argument(
        '-o', '--output-dir',
        help='Output directory (default: ./output)'
    )
    parser.add_argument(
        '-t', '--temp-dir',
        help='Temporary directory (default: ./temp_equations)'
    )
    parser.add_argument(
        '--threads',
        type=int,
        help='Number of rendering threads (default: 5)'
    )
    parser.add_argument(
        '--viewport-width',
        type=int,
        help='Rendering viewport width (default: 2400)'
    )
    parser.add_argument(
        '--env-config',
        action='store_true',
        help='Load configuration from environment variables'
    )
    parser.add_argument(
        '--validate-only',
        action='store_true',
        help='Validate configuration and exit'
    )
    
    args = parser.parse_args()
    
    # Build configuration based on arguments
    if args.env_config:
        # Load from environment variables
        config = Config.from_env()
        print("Loaded configuration from environment variables")
    else:
        # Build config from command-line arguments
        path_config = PathConfig()
        if args.output_dir:
            path_config.output_dir = Path(args.output_dir)
        if args.temp_dir:
            path_config.temp_dir = Path(args.temp_dir)
        
        render_config = RenderConfig()
        if args.threads:
            render_config.max_render_threads = args.threads
        if args.viewport_width:
            render_config.viewport_width = args.viewport_width
        
        config = Config(
            paths=path_config,
            render=render_config
        )
    
    # Print config
    print(config)
    
    # Validate if requested
    if args.validate_only:
        issues = config.validate()
        if issues:
            print("\n❌ Configuration issues:")
            for issue in issues:
                print(f"  - {issue}")
        else:
            print("\n✓ Configuration is valid")
        exit(0 if not issues else 1)
    
    # Run conversion
    result = convert_arxiv_to_epub(args.url, config=config)
    
    if result:
        clean_up(config)
