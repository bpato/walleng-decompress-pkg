# walleng-pkg

Decompress `.pkg` files from Wallpaper Engine.

## Requirements

- Python 3.10+

## Installation

```bash
pip install .
```

Or install in development mode:

```bash
pip install -e .
```

**Note:** PySide6 is required and will be installed automatically.

## Testing

```bash
pip install pytest
pytest
```

Or install dev dependencies and run:

```bash
pip install -e ".[dev]"
pytest
```

## Usage

### Graphical Interface

![GUI Screenshot](assets/gui.png)

```bash
walleng-pkg-gui
```

Features:
- File browser to select .pkg or .tex files
- Preview of package contents before extraction
- Preview .tex contents inside .pkg (checkbox option)
- Single file extraction via double-click
- Extract individual textures from .tex files inside .pkg
- Configurable output directory
- Progress indication during extraction
- Cross-platform (Windows, macOS, Linux)
- Multi-language support (English, Spanish)

### Command Line

```bash
walleng-pkg archivo.pkg
walleng-pkg archivo.pkg -o /ruta/salida
walleng-pkg archivo.pkg -v
walleng-pkg archivo.pkg -l
walleng-pkg archivo.pkg -t
walleng-pkg -x textura.tex
```

**Options:**

- `file` - Path to the .pkg or .tex file (optional)
- `-o, --output` - Output directory (defaults to current directory)
- `-v, --verbose` - Print extracted file names
- `-l, --list` - List package contents without extracting
- `-t, --tex` - Extract PNG textures from .tex files found in .pkg
- `-x, --extract-tex` - Extract textures directly from a .tex file

### Python API

```python
from walleng_pkg.core import extract_package, parse_package

# Extract all files
extracted = extract_package("archivo.pkg")

# Extract with TEX texture extraction
extracted = extract_package("archivo.pkg", extract_tex=True)

# Extract to specific directory
extracted = extract_package("archivo.pkg", "/ruta/salida")

# Parse without extracting
info = parse_package("archivo.pkg")
print(f"Root: {info.root}")
for f in info.files:
    print(f"  {f.name} ({f.length} bytes)")
```

### TEX Texture Extraction

Extract textures from Wallpaper Engine `.tex` files (supports PNG, JPG, BMP, RAW with RLE decompression):

```python
from walleng_pkg.tex import extract_textures, extract_png_textures, extract_jpg_textures, parse_tex_package

# Parse TEX file
info = parse_tex_package("textura.tex")
print(f"Dimensions: {info.width}x{info.height}")
for tex in info.textures:
    print(f"  {tex.width}x{tex.height} ({tex.format.value}, {tex.data_size} bytes)")

# Extract all textures (auto-detects format, RAW -> BMP)
extract_textures("textura.tex")

# Extract only PNG textures
extract_png_textures("textura.tex")

# Extract only JPG textures
extract_jpg_textures("textura.tex")
```

### GUI Double-Click Extraction

In the graphical interface, you can double-click items in the file list to extract them:

- **.pkg file (checkbox off):** Double-click any file to extract just that file
- **.pkg file (checkbox on):** 
  - Double-click `[TEX] filename.tex` to extract all textures from that .tex file
  - Double-click a texture entry (`    0: 512x512...`) to extract just that texture
- **.tex file:** Double-click a texture entry to extract just that texture

## File Format

Technical documentation:
- [`.pkg` format specification](docs/pkg-format.md)
- [`.tex` format specification](docs/tex-format.md)

### .pkg Format

1. **Root path** - Length-prefixed null-terminated string
2. **Number of files** - 4-byte unsigned integer (little-endian)
3. **File entries** (repeated):
   - Filename - Length-prefixed null-terminated string
   - Offset - 4-byte unsigned integer
   - Length - 4-byte unsigned integer
4. **File data** - Raw binary data concatenated

## Project Structure

```
.
├── pyproject.toml          # Package configuration
├── README.md
├── .gitignore
├── assets/
│   └── gui.png             # GUI screenshot
├── src/
│   └── walleng_pkg/
│       ├── __init__.py
│       ├── core.py         # Core extraction logic
│       ├── tex.py          # TEX texture extraction
│       ├── cli.py          # Command-line interface
│       ├── gui.py          # Graphical interface (PySide6)
│       ├── i18n.py         # Internationalization module
│       └── translations/   # Language files
│           ├── en.json     # English
│           └── es.json     # Spanish
└── tests/
    ├── test_core.py        # Unit tests
    └── test_tex.py         # TEX extraction tests
```

## License

MIT
