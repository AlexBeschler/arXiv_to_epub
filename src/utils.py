"""
Utility functions and workflow coordination.
"""
import shutil
import os

# First party
from fetcher import extract_arxiv_id, fetch_html
from parser import parse_arxiv_content
from renderer import render_all_math_equations, render_all_tables, render_all_figures

def clean_up():
    """Clean up temporary files and directories."""
    if os.path.exists('temp_equations'):
        shutil.rmtree('temp_equations')

    if os.path.exists('output/cover.png'):
        os.remove('output/cover.png')


def process_arxiv_paper(
    html_url: str,
    output_dir: str = './output',
    temp_dir: str = './temp_equations'
) -> dict:
    """
    Process an arXiv paper: fetch, parse, and render all content.
    
    Args:
        html_url: arXiv HTML URL
        output_dir: Directory for output files
        temp_dir: Temporary directory for rendering
    
    Returns:
        Dictionary containing:
            - title: Paper title
            - content: List of content items
            - math_images: Rendered math images
            - table_images: Rendered table images
            - figure_images: Rendered figure images
            - arxiv_id: arXiv paper ID
    """
    # 1. Extract arXiv ID
    arxiv_id = extract_arxiv_id(html_url)
    if not arxiv_id:
        raise ValueError("Could not extract arXiv ID from URL")
    
    # 2. Fetch HTML
    html_content = fetch_html(html_url)
    
    # 3. Parse content
    parsed_data = parse_arxiv_content(
        html_content,
        arxiv_id=arxiv_id,
        temp_dir=temp_dir
    )
    
    # 4. Render math equations
    math_images = []
    if parsed_data['math_elements_data'] and temp_dir:
        math_images = render_all_math_equations(
            parsed_data['math_elements_data'],
            temp_dir
        )
    
    # 5. Render tables
    table_images = []
    if parsed_data['table_elements_data'] and temp_dir:
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
        
        table_images = render_all_tables(
            parsed_data['table_elements_data'],
            css_content,
            temp_dir
        )
    
    # 6. Render figures
    figure_images = []
    if parsed_data['figure_elements_data'] and temp_dir:
        # Load CSS content for figure rendering
        try:
            with open('templates/css_template.css', 'r') as f:
                css_content = f.read()
        except:
            css_content = ""
        
        figure_images = render_all_figures(
            parsed_data['figure_elements_data'],
            css_content,
            temp_dir
        )
    
    return {
        'title': parsed_data['title'],
        'content': parsed_data['content'],
        'math_images': math_images,
        'table_images': table_images,
        'figure_images': figure_images,
        'arxiv_id': arxiv_id
    }
