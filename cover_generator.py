from PIL import Image, ImageDraw, ImageFont

class CoverGenerator:
    def __init__(
        self,
        width: int = 1600,
        height: int = 2400,
        bg_color: str = "white",
        text_color: str = "black",
        font_path: str = None
    ):
        self.width = width
        self.height = height
        self.bg_color = bg_color
        self.text_color = text_color
        self.font_path = font_path
        
        # Layout proportions
        self.left_margin = int(width * 0.12)
        self.right_margin = int(width * 0.12)
        self.top_padding = int(height * 0.25)
        
        # Font sizes
        self.title_font_size = 120
        self.author_font_size = 80
        
    def _get_font(self, size: int) -> ImageFont.FreeTypeFont:
        """Get font object of specified size."""
        return ImageFont.truetype("fonts/Literata.ttf", size)
    
    def _wrap_text(
        self,
        text: str,
        font: ImageFont.FreeTypeFont,
        max_width: int
    ):
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
    
    def _format_authors(self, authors) -> str:
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
            # For 3+ authors, put each on new line or use comma separation
            return ", ".join(authors)
    
    def generate_cover(
        self,
        title: str,
        authors,
        output_path: str = None
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
        # Create blank canvas
        img = Image.new('RGB', (self.width, self.height), self.bg_color)
        draw = ImageDraw.Draw(img)
        
        # Load fonts
        title_font = self._get_font(self.title_font_size)
        author_font = self._get_font(self.author_font_size)
        
        # Calculate text area width
        text_width = self.width - self.left_margin - self.right_margin
        
        # Wrap title text
        title_lines = self._wrap_text(title, title_font, text_width)
        
        # Draw title
        y_position = self.top_padding
        line_spacing = int(self.title_font_size * 1.3)
        
        for line in title_lines:
            draw.text(
                (self.left_margin, y_position),
                line,
                font=title_font,
                fill=self.text_color
            )
            y_position += line_spacing
        
        # Add spacing between title and authors
        y_position += int(self.height * 0.08)
        
        # Format and wrap authors
        author_text = self._format_authors(authors)
        author_lines = self._wrap_text(author_text, author_font, text_width)
        
        # Draw authors
        author_line_spacing = int(self.author_font_size * 1.3)
        
        for line in author_lines:
            draw.text(
                (self.left_margin, y_position),
                line,
                font=author_font,
                fill=self.text_color
            )
            y_position += author_line_spacing
        
        # Save if output path provided
        if output_path:
            img.save(output_path, dpi = (300, 300))
        
        return img
    