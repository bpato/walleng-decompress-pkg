# .tex File Format Specification

Wallpaper Engine `.tex` files are texture containers that can hold multiple mipmap levels in various formats (PNG, JPG, BMP, RAW).

## Container Structure

The TEX file consists of three main sections:

```
TEXV - Version Header
TEXI - Index/Metadata  
TEXB - Binary Texture Data
```

## Header: TEXV (Offset 0x00)

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 4 bytes | Magic | `"TEXV"` signature |
| 0x04 | 4 bytes | Version | Version string (e.g., "2.0\0") |
| 0x09 | 1 byte | Null | Null terminator |

## Index: TEXI (Offset 0x09)

Contains metadata about the texture:

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x16 | 4 bytes | Texture Count | Number of textures/mipmaps |
| 0x22 | 4 bytes | Width | Base texture width |
| 0x26 | 4 bytes | Height | Base texture height |
| 0x3F | 4 bytes | Mipmap Count | Total number of mipmap levels |

## Data Section: TEXB (Offset variable)

The TEXB marker identifies where the texture data begins. Each mipmap level has:

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 4 bytes | Mip Width | Level width |
| 0x04 | 4 bytes | Mip Height | Level height |
| 0x08 | 8 bytes | Reserved | Padding |
| 0x10 | 4 bytes | Data Size | Size of texture data |
| 0x14 | Variable | Texture Data | Format-specific data |
| +size | 12 bytes | Trailer | Padding after data |

## Supported Texture Formats

### PNG (Portable Network Graphics)

- **Signature:** `\x89PNG\r\n\x1a\n`
- **Compression:** Lossless
- **Alpha:** Full support
- **Detection:** Check for PNG signature at start of texture data

### JPG (JPEG)

- **Signature:** `\xFF\xD8\xFF`
- **Compression:** Lossy
- **Alpha:** No (RGB only)
- **Detection:** Check for JPEG SOI marker

### BMP (Bitmap)

- **Signature:** `BM`
- **Compression:** None (raw pixels)
- **Alpha:** Via alpha channel in BI_RGB format
- **Detection:** Check for BMP signature

### RAW (Custom RLE)

- **Compression:** Custom RLE encoding
- **Format:** BGRA (4 bytes per pixel)
- **Detection:** No standard signature, assumed if not PNG/JPG/BMP
- **Status:** RLE decompression code implemented but not currently used in extraction
  - Raw data is extracted as-is without decompression
  - To convert RAW to viewable format, decompress using the RLE algorithm below and wrap in BMP
- **RLE Algorithm:**
  - High bit set (0x80+): Run-length encoded (copy byte N+1 times)
  - High bit clear: Literal copy of N+1 bytes

## RAW RLE Decompression

The RAW format uses a custom RLE scheme:

```
Control byte interpretation:
  0x00-0x7F: Copy next N+1 bytes literally
  0x80-0xFF: Repeat next byte (N & 0x7F) + 1 times
```

Example:
```
02 41 42 43    -> Copy "ABC" (literal)
83 2A          -> Repeat 0x2A four times (4 = 3+1)
```

## Python Implementation

```python
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
JPG_SIGNATURE = b"\xFF\xD8\xFF"

def detect_format(data):
    if data[:8] == PNG_SIGNATURE:
        return "png"
    if data[:3] == JPG_SIGNATURE:
        return "jpg"
    if data[:2] == b"BM":
        return "bmp"
    return "raw"  # RLE compressed

def decompress_rle(data, expected_size):
    result = bytearray()
    i = 0
    while i < len(data) and len(result) < expected_size:
        count = data[i]
        i += 1
        if count & 0x80:
            count = (count & 0x7F) + 1
            if i < len(data):
                value = data[i]
                i += 1
                result.extend([value] * count)
        else:
            count += 1
            for _ in range(count):
                if i < len(data):
                    result.append(data[i])
                    i += 1
        return bytes(result)
```

> **Note:** The `decompress_rle` function is implemented in `tex.py` but not currently used during extraction. RAW textures are extracted as raw compressed data. To enable full RAW support, call `decompress_rle` followed by `create_bmp` to convert to a viewable BMP format.

## Texture Data Flow

```
TEX File
├── TEXV header (version info)
├── TEXI index (metadata)
└── TEXB section
    ├── Mipmap 0 (largest)
    │   ├── Width/Height
    │   ├── Data Size
    │   ├── Texture Data (PNG/JPG/BMP/RAW)
    │   └── Trailer
    ├── Mipmap 1
    │   └── ...
    └── Mipmap N (smallest)
```

Each mipmap level halves the dimensions until reaching 1x1.
