from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

# Import config
from config import CoverConfig, get_config

class CoverGenerator:
    """Generate book covers for EPUB files."""
    
    def __init__(self, config: CoverConfig | None = None):
        """
        Initialize cover generator.
        
        Args:
            config: CoverConfig instance (uses global default if None)
        """
        if config is None:
            config = get_config().cover
        
        self.config = config
        
        # Calculate layout from config ratios
        self.width = config.width
        self.height = config.height
        self.left_margin = int(config.width * config.left_margin_ratio)
        self.right_margin = int(config.width * config.right_margin_ratio)
        self.top_padding = int(config.height * config.top_padding_ratio)
        
    def _get_font(self, size: int, font_path: Path | None = None) -> ImageFont.FreeTypeFont:
        """
        Get font object of specified size.
        
        Args:
            size: Font size in points
            font_path: Path to font file (uses config default if None)
        
        Returns:
            PIL Font object
        """
        if font_path is None:
            # Use font from global config
            font_path = get_config().paths.font_regular
        
        return ImageFont.truetype(str(font_path), size)
    
    def _wrap_text(
        self,
        text: str,
        font: ImageFont.FreeTypeFont,
        max_width: int
    ) -> list[str]:
        """
        Wrap text to fit within max_width.
        
        Args:
            text: Text to wrap
            font: Font object
            max_width: Maximum width in pixels
            
        Returns:
            List of wrapped lines
        """
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            bbox = font.getbbox(test_line)
            width = bbox[2] - bbox[0]
            
            if width <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                    current_line = [word]
                else:
                    # Single word is too long, add it anyway
                    lines.append(word)
        
        if current_line:
            lines.append(' '.join(current_line))
        
        return lines
    
    def _format_authors(self, authors: list[str]) -> str:
        """
        Format author list for display.
        
        Args:
            authors: List of author names
            
        Returns:
            Formatted author string
        """
        if not authors:
            return ""
        elif len(authors) == 1:
            return authors[0]
        elif len(authors) == 2:
            return f"{authors[0]}, {authors[1]}"
        else:
            # For 3+ authors, use comma separation
            return ", ".join(authors)
    
    def generate_cover(
        self,
        title: str,
        authors: list[str],
        output_path: str | Path | None = None
    ) -> Image.Image:
        """
        Generate book cover image.
        
        Args:
            title: Paper title
            authors: List of author names
            output_path: Path to save image (optional)
            
        Returns:
            PIL Image object
        """
        # Create blank canvas with config colors
        img = Image.new('RGB', (self.width, self.height), self.config.bg_color)
        draw = ImageDraw.Draw(img)
        
        # Load fonts with config sizes
        title_font = self._get_font(self.config.title_font_size)
        author_font = self._get_font(self.config.author_font_size)
        
        # Calculate text area width
        text_width = self.width - self.left_margin - self.right_margin
        
        # Wrap title text
        title_lines = self._wrap_text(title, title_font, text_width)
        
        # Draw title
        y_position = self.top_padding
        line_spacing = int(self.config.title_font_size * self.config.title_line_spacing)
        
        for line in title_lines:
            draw.text(
                (self.left_margin, y_position),
                line,
                font=title_font,
                fill=self.config.text_color
            )
            y_position += line_spacing
        
        # Add spacing between title and authors (from config)
        y_position += int(self.height * self.config.title_author_gap_ratio)
        
        # Format and wrap authors
        author_text = self._format_authors(authors)
        author_lines = self._wrap_text(author_text, author_font, text_width)
        
        # Draw authors
        author_line_spacing = int(self.config.author_font_size * self.config.author_line_spacing)
        
        for line in author_lines:
            draw.text(
                (self.left_margin, y_position),
                line,
                font=author_font,
                fill=self.config.text_color
            )
            y_position += author_line_spacing
        
        # Save if output path provided (with config DPI)
        if output_path:
            img.save(str(output_path), dpi=self.config.dpi)
        
        return img
