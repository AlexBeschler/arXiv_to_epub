"""
Module for building HTML content for EPUB chapters.
"""
import html as html_module


def split_content_into_chapters(
    content_items: list[dict],
    chapter_level: int = 2
) -> list[dict]:
    """
    Split content items into chapters based on heading level.
    
    Args:
        content_items: List of content item dictionaries
        chapter_level: Heading level to use for chapter splits (default: h2)
    
    Returns:
        List of chapter dictionaries with 'title' and 'content_items' keys
    """
    chapters = []
    current_chapter = {
        'title': 'Frontmatter',
        'content_items': []
    }
    
    for item in content_items:
        if item['type'] == 'heading' and item['level'] == chapter_level:
            # Save current chapter if it has content
            if current_chapter['content_items']:
                chapters.append(current_chapter)
            
            # Start new chapter
            current_chapter = {
                'title': item['content'],
                'content_items': [item]  # Include the heading in the chapter
            }
        else:
            # Add to current chapter
            current_chapter['content_items'].append(item)
    
    # Add final chapter
    if current_chapter['content_items']:
        chapters.append(current_chapter)
    
    return chapters


def build_html(content_items: list[dict], title: str) -> str:
    """
    Build clean, simple HTML from extracted content items.
    
    Args:
        content_items: List of content item dictionaries
        title: Document title
    
    Returns:
        Complete HTML document as string
    """
    html_parts = []
    html_parts.append('<html xmlns="http://www.w3.org/1999/xhtml">')
    html_parts.append('<head>')
    html_parts.append(f'<title>{html_module.escape(title)}</title>')
    html_parts.append('</head>')
    html_parts.append('<body>')
    
    # Process content items in order
    for item in content_items:
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
