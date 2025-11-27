"""
Module for creating and assembling EPUB files.
"""
from ebooklib import epub # pyright: ignore[reportMissingImports]
from pathlib import Path
import os

# First party
from cover_generator import CoverGenerator
from html_builder import split_content_into_chapters, build_html

def create_epub(
    title: str,
    content_data: dict,
    output_path: str
) -> None:
    """
    Create EPUB with clean CSS and support for math equations, tables, and figures.
    
    Args:
        title: Paper title
        content_data: Dictionary containing:
            - content: List of content items
            - math_images: List of rendered math equation images (bytes)
            - table_images: List of rendered table images (bytes)
            - figure_images: List of rendered figure images (bytes)
        output_path: Path where EPUB file should be saved
    """
    # Extract components from content_data
    all_content_items = content_data['content']
    math_images = content_data['math_images']
    table_images = content_data['table_images']
    figure_images = content_data['figure_images']
    
    book = epub.EpubBook()
    book.set_identifier(f'arxiv_{Path(output_path).stem}')
    book.set_title(title)
    book.set_language('en')
    book.add_author('arXiv Paper')

    # Generate cover
    cover_generator = CoverGenerator()
    cover = cover_generator.generate_cover(
        title=title,
        authors=['arXiv Paper'],
        output_path="output/cover.png"
    )

    with open("output/cover.png", 'rb') as cover_file:
        book.set_cover('cover.png', cover_file.read())
    
    # Add CSS
    with open('templates/css_template.css', 'r') as f:
        css = ''.join(f.readlines())
    
    css_item = epub.EpubItem(
        uid="style",
        file_name="style/style.css",
        media_type="text/css",
        content=css
    )
    book.add_item(css_item)
    
    # Add custom fonts
    font_files = [
        ('fonts/Literata.ttf', 'font-regular'),
        ('fonts/Literata-Italic.ttf', 'font-italic'),
    ]
    
    for font_path, font_uid in font_files:
        if os.path.exists(font_path):
            try:
                with open(font_path, 'rb') as f:
                    font_content = f.read()
                
                font_item = epub.EpubItem(
                    uid=font_uid,
                    file_name=f'fonts/{os.path.basename(font_path)}',
                    media_type='application/x-font-ttf',
                    content=font_content
                )
                book.add_item(font_item)
            except Exception as e:
                print(f"Warning: Failed to embed font {font_path}: {e}")
        else:
            print(f"Warning: Font file not found: {font_path}")
    
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
            print(f"Warning: Failed to process math {idx}: {e}")
    
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
            print(f"Warning: Failed to process table {idx}: {e}")
    
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
            print(f"Warning: Failed to process figure {idx}: {e}")
    
    # Split content into chapters based on h2 headings
    chapters_data = split_content_into_chapters(all_content_items, chapter_level=2)
    
    # Create EpubHtml objects for each chapter
    chapter_items = []
    for idx, chapter_data in enumerate(chapters_data):
        chapter_title = chapter_data['title']
        chapter_content_items = chapter_data['content_items']
        
        # Build HTML for this chapter
        html_content = build_html(chapter_content_items, chapter_title)
        
        # Create chapter
        chapter = epub.EpubHtml(
            title=chapter_title,
            file_name=f'chapter_{idx}.xhtml',
            lang='en'
        )
        chapter.content = html_content
        chapter.add_item(css_item)
        book.add_item(chapter)
        chapter_items.append(chapter)
    
    # Set up navigation with all chapters in ToC
    book.toc = tuple(chapter_items)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ['cover', 'nav'] + chapter_items
    
    # Write EPUB
    epub.write_epub(output_path, book)
    print(f"EPUB created!")
