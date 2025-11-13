# arXiv to EPUB Converter - Code Improvements

This document outlines recommended improvements and refactors for the arXiv to EPUB converter project.

---

## 🏗️ Architecture & Organization

### 1. Split `utils.py` into logical modules
**Current Issue:** 700+ lines with too many responsibilities

**Recommended Structure:**
- `fetcher.py` - HTTP requests and content fetching
- `parser.py` - HTML parsing and content extraction
- `renderer.py` - Playwright-based rendering (math, tables, figures)
- `html_builder.py` - HTML construction for EPUB
- `epub_builder.py` - EPUB creation and assembly
- `template_manager.py` - Template loading and management

### 2. Create a `models.py` or `types.py`
Define data structures using dataclasses:
- `ContentItem` - Parsed content representation
- `ChapterData` - Chapter information
- `RenderConfig` - Rendering parameters
- Improves type safety and clarity

### 3. Introduce a `Config` class
Centralize all configuration:
- Viewport dimensions
- Thread pool size
- Font paths
- Template paths
- DPI settings
- Timeout values

---

## 🔧 Code Quality

### 4. Consistent path handling
**Current Issue:** Mix of string concatenation and Path objects

**Solution:** Use `pathlib.Path` throughout
- No more `f"{output_dir}/{arxiv_id}_{safe_title}.epub"`
- Consistent path operations

### 5. Type hints everywhere
**Current Issue:** Inconsistent type annotations

**Solution:**
- Add to all function parameters and returns
- Use `Optional`, `Union`, `List`, `Dict` appropriately
- Consider Python 3.10+ union syntax (`str | None`)

### 6. Extract magic numbers to constants
**Bad:**
```python
page = browser.new_page(viewport={'width': 2400, 'height': 2000, 'device_scale_factor': 2})
```

**Good:**
```python
RENDER_VIEWPORT_WIDTH = 2400
RENDER_VIEWPORT_HEIGHT = 2000
DEVICE_SCALE_FACTOR = 2
MAX_RENDER_THREADS = 5
```

### 7. Reduce duplication in rendering functions
**Current Issue:** `render_math_with_playwright`, `render_table_with_playwright`, `render_figure_with_playwright` share 80% logic

**Solution:**
- Create a base `render_with_playwright()` function
- Use strategy pattern or callbacks for element-specific handling

---

## 🛡️ Error Handling & Robustness

### 8. Improve error handling
**Current Issues:**
- Too many bare `except:` blocks that swallow errors
- No proper logging

**Solutions:**
- Be specific about exception types
- Add proper logging instead of just `print()`
- Validate inputs (URLs, arXiv IDs, file paths)

### 9. Resource cleanup (Critical Issue)
**Current Issue:** `clean_up()` only runs if script completes successfully

**Solutions:**
- Use context managers (`with` statements)
- Create a `TemporaryWorkspace` context manager for temp directories
- Ensure cleanup happens even on failure

### 10. Better validation
Add validation for:
- arXiv URLs before processing
- Required template files exist before starting
- Fonts are available
- Meaningful error messages for users

---

## 🧵 Concurrency & Performance

### 11. Configurable threading
**Current Issue:** Hard-coded `max_workers=5`

**Solutions:**
- Make configurable or based on `os.cpu_count()`
- Consider adding progress bar library (tqdm) instead of manual progress

### 12. Browser instance management
**Consideration:** Currently creates new browser for each equation (in threads)
- Could potentially pool browsers or pages more efficiently
- Consider memory trade-offs

---

## 📝 Template & Asset Management

### 13. Template loading is fragile
**Current Issues:**
- Hard-coded paths like `'templates/html_template.html'`
- No validation that files exist
- String replacement is error-prone: `.replace('[mathjax_abs_path]', mathjax_url)`

**Solution:** Consider using Jinja2 for proper templating

### 14. Font management
**Current Issues:**
- Hard-coded paths: `"fonts/Literata.ttf"`
- No fallback if missing

**Solution:** Create a `FontManager` class with fallback logic

---

## 🧹 Code Cleanliness

### 15. Break down giant functions
**`parse_arxiv_content()`** (~250 lines) - split into:
- `extract_content_items()`
- `process_math_elements()`
- `process_tables()`
- `process_figures()`

**`create_clean_epub()`** (~150 lines) - split into smaller functions

### 16. Improve function naming
**Current Issues:**
- `create_clean_epub` - what makes it "clean"?
- `build_clean_html` - same issue

**Solution:** Be more descriptive or remove vague adjectives

### 17. HTML building is brittle
**Current Issue:** Manual string concatenation for HTML with manual escaping

**Solutions:**
- Consider using `xml.etree.ElementTree` or a proper HTML builder
- Or use a templating library

---

## 📊 Data Flow & Structure

### 18. Consolidate data structures
**Current Issue:** Content passed around as complex nested dictionaries

**Solution:** Define proper dataclasses/TypedDicts:
```python
@dataclass
class MathElement:
    mathml: str
    display_type: str
    alt_text: str
    index: int
```

### 19. Simplify state passing
**Current Issue:** Functions pass many parallel arrays (`math_images`, `table_images`, `figure_images`)

**Solution:** Bundle into a single `RenderResults` object

---

## 🔍 Parsing Logic

### 20. Improve content extraction
**Current Issues:**
- `extract_text_content()` recursively walks DOM - could be more efficient
- The skipping logic for nested elements is complex and fragile

**Solution:** Clearer logic with better comments

### 21. URL fixing is fragile
**Current Issue:** `fix_image_urls_in_html()` uses regex on HTML strings

**Solution:**
- Better to parse HTML, modify URLs in DOM, then serialize
- Current approach could break on edge cases

---

## 📦 Dependencies & Environment

### 22. Missing dependency documentation
**Current Issue:** No `requirements.txt` or `pyproject.toml`

**Solution:** Document dependencies:
- playwright
- ebooklib
- Pillow
- beautifulsoup4
- requests

### 23. Playwright setup
**Missing:** Documentation that `playwright install` is required

**Solution:**
- Document setup steps
- Consider checking if browsers are installed

---

## 🎨 Cover Generation

### 24. Better integration
**Current Issue:** `CoverGenerator` saves to hard-coded `"output/cover.png"` then immediately reads it

**Solution:** Should return bytes directly, not go through disk

### 25. Cover customization
**Current Issue:** No easy way to customize per-paper

**Solution:** Could extract metadata-specific styling

---

## 🔊 Logging & Observability

### 26. Replace print statements
**Solution:** Use Python's `logging` module
- Allows users to control verbosity
- Better for debugging and production use

### 27. Better progress indicators
**Current:**
```python
print(f'\r   Completed {completed}/{len(math_elements_data)}', end = '')
```

**Better:** Consider using `tqdm` for professional progress bars

---

## 🧪 Testability

### 28. Separate I/O from logic
**Current Issue:** Functions mix business logic with I/O

**Solution:**
- Makes unit testing difficult
- Extract pure functions where possible

### 29. Dependency injection
**Current Issue:** Hard-coded dependencies (Playwright, requests)

**Solution:** Could use dependency injection for testing

---

## 📋 Miscellaneous

### 30. Inconsistent spacing in function calls
**Issue:** Mix of `max_workers = 5` and `max_workers=5`

**Solution:** Choose one style (PEP 8 says no spaces around `=` in keyword arguments)

### 31. Dead code or unclear purpose
- `DEFAULT_CONFIG` dictionary barely used
- Could be more central to the design

### 32. Comment quality
**Good:** Section markers (`# ====...====`)

**Needs improvement:**
- Some complex logic lacks explanation
- The "skip if inside table/figure" logic especially needs better docs

---

## 🎯 Priority Recommendations

If prioritizing improvements:

1. **Split `utils.py`** into separate modules (biggest impact on maintainability)
2. **Add proper error handling and resource cleanup** (robustness)
3. **Create Config class** and extract constants (maintainability)
4. **Add comprehensive type hints** (code quality)
5. **Improve logging** (observability)
6. **Reduce rendering function duplication** (DRY principle)
7. **Better template management** (maintainability)
8. **Consolidate data structures with dataclasses** (clarity)

---

## 📝 Notes

- The current codebase is functional and demonstrates sophisticated features
- These improvements focus on maintainability, robustness, and scalability
- Many improvements can be implemented incrementally without breaking existing functionality
