"""
Centralized configuration for arXiv to EPUB converter.
"""
from dataclasses import dataclass, field
from pathlib import Path
import os

@dataclass
class RenderConfig:
    """Configuration for Playwright rendering."""
    
    # Viewport settings for rendering
    viewport_width: int = 2400
    viewport_height: int = 2000
    device_scale_factor: int = 2
    
    # Threading configuration
    max_render_threads: int = 5
    
    # Timeout settings (in milliseconds)
    mathjax_timeout: int = 5000
    network_idle_timeout: int = 10000
    fallback_timeout: int = 3000
    short_fallback_timeout: int = 2000
    
    # Placeholder image settings
    placeholder_width: int = 400
    placeholder_height: int = 100
    
    @property
    def viewport_dict(self) -> dict:
        """Get viewport configuration as dictionary for Playwright."""
        return {
            'width': self.viewport_width,
            'height': self.viewport_height,
            'device_scale_factor': self.device_scale_factor
        }


@dataclass
class CoverConfig:
    """Configuration for cover generation."""
    
    # Cover dimensions (optimized for e-readers)
    width: int = 1600
    height: int = 2400
    
    # Colors
    bg_color: str = "white"
    text_color: str = "black"
    
    # Font sizes
    title_font_size: int = 120
    author_font_size: int = 80
    
    # DPI for high-quality cover images
    dpi: tuple[int, int] = (300, 300)
    
    # Layout proportions (as percentage of dimensions)
    left_margin_ratio: float = 0.12
    right_margin_ratio: float = 0.12
    top_padding_ratio: float = 0.25
    
    # Line spacing multipliers
    title_line_spacing: float = 1.3
    author_line_spacing: float = 1.3
    
    # Spacing between title and author
    title_author_gap_ratio: float = 0.08


@dataclass
class PathConfig:
    """Configuration for file paths and directories."""
    
    # Base directories
    output_dir: Path = field(default_factory=lambda: Path('./output'))
    temp_dir: Path = field(default_factory=lambda: Path('./temp_equations'))
    
    # Template paths
    templates_dir: Path = field(default_factory=lambda: Path('./templates'))
    
    # Font paths
    fonts_dir: Path = field(default_factory=lambda: Path('./fonts'))
    
    def __post_init__(self):
        """Convert string paths to Path objects if needed."""
        if isinstance(self.output_dir, str):
            self.output_dir = Path(self.output_dir)
        if isinstance(self.temp_dir, str):
            self.temp_dir = Path(self.temp_dir)
        if isinstance(self.templates_dir, str):
            self.templates_dir = Path(self.templates_dir)
        if isinstance(self.fonts_dir, str):
            self.fonts_dir = Path(self.fonts_dir)
    
    @property
    def html_template(self) -> Path:
        """Path to HTML template for math rendering."""
        return self.templates_dir / 'html_template.html'
    
    @property
    def css_template(self) -> Path:
        """Path to main CSS template."""
        return self.templates_dir / 'css_template.css'
    
    @property
    def table_template_html(self) -> Path:
        """Path to table HTML template."""
        return self.templates_dir / 'table_template.html'
    
    @property
    def table_template_css(self) -> Path:
        """Path to table CSS template."""
        return self.templates_dir / 'table_template.css'
    
    @property
    def figure_template_html(self) -> Path:
        """Path to figure HTML template."""
        return self.templates_dir / 'figure_template.html'
    
    @property
    def font_regular(self) -> Path:
        """Path to regular font."""
        return self.fonts_dir / 'Literata.ttf'
    
    @property
    def font_italic(self) -> Path:
        """Path to italic font."""
        return self.fonts_dir / 'Literata-Italic.ttf'
    
    @property
    def font_sans(self) -> Path:
        """Path to sans-serif font (for placeholders)."""
        return self.fonts_dir / 'DejaVuSans.ttf'
    
    @property
    def cover_output(self) -> Path:
        """Path where cover image is temporarily saved."""
        return self.output_dir / 'cover.png'
    
    def ensure_directories(self):
        """Create necessary directories if they don't exist."""
        self.output_dir.mkdir(exist_ok=True, parents=True)
        self.temp_dir.mkdir(exist_ok=True, parents=True)


@dataclass
class EPUBConfig:
    """Configuration for EPUB generation."""
    
    # Chapter splitting
    chapter_heading_level: int = 2
    
    # Author metadata
    default_author: str = 'arXiv Paper'
    
    # Language
    language: str = 'en'
    
    # Font MIME type
    font_mime_type: str = 'application/x-font-ttf'


@dataclass
class ParsingConfig:
    """Configuration for HTML parsing."""
    
    # Minimum text length thresholds
    min_heading_length: int = 2
    min_paragraph_length: int = 20
    min_paragraph_with_math_length: int = 10
    
    # Alt text truncation
    max_alt_text_length: int = 100
    
    # Title truncation for filename
    max_title_length_for_filename: int = 50


@dataclass
class Config:
    """
    Master configuration class for arXiv to EPUB converter.
    
    Usage:
        # Use defaults
        config = Config()
        
        # Customize specific settings
        config = Config(
            render=RenderConfig(max_render_threads=10),
            paths=PathConfig(output_dir='./my_output')
        )
        
        # Access nested configs
        viewport = config.render.viewport_dict
        output_path = config.paths.output_dir
    """
    
    render: RenderConfig = field(default_factory=RenderConfig)
    cover: CoverConfig = field(default_factory=CoverConfig)
    paths: PathConfig = field(default_factory=PathConfig)
    epub: EPUBConfig = field(default_factory=EPUBConfig)
    parsing: ParsingConfig = field(default_factory=ParsingConfig)
    
    @classmethod
    def from_dict(cls, config_dict: dict) -> 'Config':
        """
        Create Config from dictionary.
        
        Args:
            config_dict: Dictionary with nested config values
            
        Returns:
            Config instance
            
        Example:
            config = Config.from_dict({
                'render': {'max_render_threads': 10},
                'paths': {'output_dir': './my_output'}
            })
        """
        render_dict = config_dict.get('render', {})
        cover_dict = config_dict.get('cover', {})
        paths_dict = config_dict.get('paths', {})
        epub_dict = config_dict.get('epub', {})
        parsing_dict = config_dict.get('parsing', {})
        
        return cls(
            render=RenderConfig(**render_dict),
            cover=CoverConfig(**cover_dict),
            paths=PathConfig(**paths_dict),
            epub=EPUBConfig(**epub_dict),
            parsing=ParsingConfig(**parsing_dict)
        )
    
    @classmethod
    def from_env(cls) -> 'Config':
        """
        Create Config from environment variables.
        
        Environment variables:
            ARXIV_OUTPUT_DIR - Output directory path
            ARXIV_TEMP_DIR - Temporary directory path
            ARXIV_MAX_THREADS - Maximum render threads
            ARXIV_VIEWPORT_WIDTH - Rendering viewport width
            ARXIV_VIEWPORT_HEIGHT - Rendering viewport height
        
        Returns:
            Config instance with values from environment
        """
        render_config = RenderConfig(
            max_render_threads=int(os.getenv('ARXIV_MAX_THREADS', 5)),
            viewport_width=int(os.getenv('ARXIV_VIEWPORT_WIDTH', 2400)),
            viewport_height=int(os.getenv('ARXIV_VIEWPORT_HEIGHT', 2000))
        )
        
        paths_config = PathConfig(
            output_dir=Path(os.getenv('ARXIV_OUTPUT_DIR', './output')),
            temp_dir=Path(os.getenv('ARXIV_TEMP_DIR', './temp_equations'))
        )
        
        return cls(
            render=render_config,
            paths=paths_config
        )
    
    def validate(self) -> list[str]:
        """
        Validate configuration and return list of issues.
        
        Returns:
            List of validation error messages (empty if valid)
        """
        issues = []
        
        # Check that essential template files exist
        if not self.paths.html_template.exists():
            issues.append(f"HTML template not found: {self.paths.html_template}")
        if not self.paths.css_template.exists():
            issues.append(f"CSS template not found: {self.paths.css_template}")
        
        # Check that essential fonts exist
        if not self.paths.font_regular.exists():
            issues.append(f"Regular font not found: {self.paths.font_regular}")
        if not self.paths.font_sans.exists():
            issues.append(f"Sans font not found: {self.paths.font_sans}")
        
        # Validate numeric values
        if self.render.max_render_threads < 1:
            issues.append(f"max_render_threads must be >= 1, got {self.render.max_render_threads}")
        if self.render.viewport_width < 100:
            issues.append(f"viewport_width too small: {self.render.viewport_width}")
        if self.render.viewport_height < 100:
            issues.append(f"viewport_height too small: {self.render.viewport_height}")
        
        if self.cover.width < 100 or self.cover.height < 100:
            issues.append(f"Cover dimensions too small: {self.cover.width}x{self.cover.height}")
        
        return issues
    
    def __str__(self) -> str:
        """String representation of config."""
        return (
            f"Config(\n"
            f"  Render: {self.render.max_render_threads} threads, "
            f"{self.render.viewport_width}x{self.render.viewport_height}\n"
            f"  Cover: {self.cover.width}x{self.cover.height} @ {self.cover.dpi[0]} DPI\n"
            f"  Paths: output={self.paths.output_dir}, temp={self.paths.temp_dir}\n"
            f")"
        )


# Default global config instance
_default_config: Config | None = None


def get_config() -> Config:
    """
    Get the global default config instance.
    
    Returns:
        Global Config instance (creates if doesn't exist)
    """
    global _default_config
    if _default_config is None:
        _default_config = Config()
    return _default_config


def set_config(config: Config):
    """
    Set the global default config instance.
    
    Args:
        config: Config instance to use as global default
    """
    global _default_config
    _default_config = config


def reset_config():
    """Reset global config to default values."""
    global _default_config
    _default_config = Config()
