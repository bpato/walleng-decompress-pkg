"""Extract textures from Wallpaper Engine .tex files."""

from __future__ import annotations

import os
import re
import struct
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
JPG_SIGNATURE = b"\xFF\xD8\xFF"


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal and invalid characters."""
    filename = os.path.basename(filename)
    filename = re.sub(r'[^\w\-.]', '_', filename)
    return filename[:255]


def sanitize_extension(ext: str) -> str:
    """Validate and sanitize file extension."""
    ext = ext.lower().strip('.')
    if not re.match(r'^[a-z0-9]+$', ext):
        ext = 'bin'
    return ext


class TextureFormat(Enum):
    """Texture format types."""
    PNG = "png"
    JPG = "jpg"
    RAW = "raw"
    BMP = "bmp"


def detect_format(data: bytes) -> tuple[TextureFormat, bytes]:
    """Detect texture format from data."""
    if data[:8] == PNG_SIGNATURE:
        return TextureFormat.PNG, data
    if data[:3] == JPG_SIGNATURE:
        return TextureFormat.JPG, data
    if data[:2] == b"BM":
        return TextureFormat.BMP, data
    return TextureFormat.RAW, data


# TODO: RLE decompression and BMP conversion not yet working
# def decompress_rle(data: bytes, expected_size: int) -> bytes:
#     """Decompress RLE compressed data."""
#     ...
# 
# def create_bmp(width: int, height: int, data: bytes, bpp: int = 32) -> bytes:
#     """Create a BMP file from raw pixel data."""
#     ...
# 
# def convert_raw_to_bmp(raw_data: bytes, width: int, height: int) -> bytes:
#     """Convert raw RLE data to BMP format."""
#     ...


def decompress_rle(data: bytes, expected_size: int) -> bytes:
    """Decompress RLE compressed data - TODO: needs debugging."""
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


def create_bmp(width: int, height: int, data: bytes, bpp: int = 32) -> bytes:
    """Create a BMP file from raw pixel data."""
    row_size = ((width * bpp + 31) // 32) * 4
    image_size = row_size * height
    file_size = 54 + image_size
    
    bmp = bytearray()
    
    bmp.extend(b"BM")
    bmp.extend(struct.pack("<I", file_size))
    bmp.extend(struct.pack("<H", 0))
    bmp.extend(struct.pack("<H", 0))
    bmp.extend(struct.pack("<I", 54))
    
    bmp.extend(struct.pack("<I", 40))
    bmp.extend(struct.pack("<i", width))
    bmp.extend(struct.pack("<i", -height))
    bmp.extend(struct.pack("<H", 1))
    bmp.extend(struct.pack("<H", bpp))
    bmp.extend(struct.pack("<I", 0))
    bmp.extend(struct.pack("<I", image_size))
    bmp.extend(struct.pack("<i", 0))
    bmp.extend(struct.pack("<i", 0))
    bmp.extend(struct.pack("<I", 0))
    bmp.extend(struct.pack("<I", 0))
    
    if len(data) < image_size:
        data = data + b"\x00" * (image_size - len(data))
    elif len(data) > image_size:
        data = data[:image_size]
    
    bmp.extend(data)
    
    return bytes(bmp)


def convert_raw_to_bmp(raw_data: bytes, width: int, height: int) -> bytes:
    """Convert raw RLE data to BMP format - TODO: needs debugging."""
    expected_size = width * height * 4
    decompressed = decompress_rle(raw_data, expected_size)
    
    bgra_data = bytearray()
    for i in range(0, len(decompressed), 4):
        if i + 4 <= len(decompressed):
            b = decompressed[i]
            g = decompressed[i + 1]
            r = decompressed[i + 2]
            a = decompressed[i + 3] if i + 3 < len(decompressed) else 255
            bgra_data.extend([b, g, r, a])
        else:
            break
    
    return create_bmp(width, height, bytes(bgra_data), 32)


@dataclass
class TextureData:
    """Raw texture data with format information."""
    width: int
    height: int
    compression: int
    format_type: int
    data_size: int
    data: bytes
    format: TextureFormat


@dataclass
class TexInfo:
    """Information extracted from a TEX file."""
    version: str
    texture_count: int
    width: int
    height: int
    textures: list[TextureData]


def read_cstring(data: bytes, offset: int, max_len: int = 4) -> str:
    """Read a null-terminated string from bytes at offset."""
    end = offset
    for i in range(max_len):
        if offset + i >= len(data) or data[offset + i] == 0:
            end = offset + i
            break
    else:
        end = offset + max_len
    return data[offset:end].decode("ascii", errors="replace")


def parse_tex_package(pathfile: Path) -> TexInfo:
    """Parse a TEX texture container file."""
    if not pathfile.is_file():
        raise FileNotFoundError(f"TEX file not found: {pathfile}")
    
    with open(pathfile, "rb") as f:
        data = f.read()
    
    if len(data) < 64:
        raise ValueError("File too small to be a valid TEX")
    
    if data[0:4] != b"TEXV":
        raise ValueError(f"Invalid TEXV header: {data[0:4]}")
    
    version = read_cstring(data, 4, 4)
    
    texb_pos = data.find(b"TEXB")
    if texb_pos == -1:
        raise ValueError("TEXB data block not found")
    
    texture_count = struct.unpack("<I", data[0x16:0x1A])[0]
    width = struct.unpack("<I", data[0x22:0x26])[0]
    height = struct.unpack("<I", data[0x26:0x2A])[0]
    
    total_mipmaps = struct.unpack("<I", data[0x3F:0x43])[0]
    
    textures: list[TextureData] = []
    pos = texb_pos + 0x15
    
    for _ in range(total_mipmaps):
        if pos + 20 > len(data):
            break
        
        mip_width = struct.unpack("<I", data[pos:pos + 4])[0]
        mip_height = struct.unpack("<I", data[pos + 4:pos + 8])[0]
        data_size = struct.unpack("<I", data[pos + 16:pos + 20])[0]
        
        tex_data = data[pos + 20:pos + 20 + data_size]
        tex_format, _ = detect_format(tex_data)
        
        textures.append(TextureData(
            width=mip_width,
            height=mip_height,
            compression=-1,
            format_type=5,
            data_size=data_size,
            data=tex_data,
            format=tex_format,
        ))
        
        pos += data_size + 20
    
    return TexInfo(
        version=version,
        texture_count=texture_count,
        width=width,
        height=height,
        textures=textures,
    )


def extract_textures(tex_path: Path, output_dir: Path | None = None, overwrite: bool = False) -> list[Path]:
    """Extract all textures from a TEX file."""
    if output_dir is None:
        output_dir = tex_path.parent
    else:
        output_dir = Path(output_dir)
    
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    
    info = parse_tex_package(tex_path)
    
    extracted: list[Path] = []
    base_name = sanitize_filename(tex_path.stem)
    
    for i, texture in enumerate(info.textures):
        ext = texture.format.value
        safe_ext = sanitize_extension(ext)
        output_path = (output_dir / f"{base_name}_{texture.width}x{texture.height}.{safe_ext}").resolve()
        
        if not str(output_path).startswith(str(output_dir)):
            raise ValueError(f"Invalid output path: {output_path}")
        
        if not overwrite and output_path.exists():
            continue
        
        with open(output_path, "wb") as f:
            f.write(texture.data)
        
        extracted.append(output_path)
    
    return extracted


def extract_png_textures(tex_path: Path, output_dir: Path | None = None) -> list[Path]:
    """Extract only PNG textures from a TEX file."""
    return extract_textures_by_format(tex_path, output_dir, TextureFormat.PNG)


def extract_jpg_textures(tex_path: Path, output_dir: Path | None = None) -> list[Path]:
    """Extract only JPG textures from a TEX file."""
    return extract_textures_by_format(tex_path, output_dir, TextureFormat.JPG)


def extract_textures_by_format(tex_path: Path, output_dir: Path | None = None, target_format: TextureFormat | None = None, overwrite: bool = False) -> list[Path]:
    """Extract textures of a specific format from a TEX file."""
    if output_dir is None:
        output_dir = tex_path.parent
    else:
        output_dir = Path(output_dir)
    
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    
    info = parse_tex_package(tex_path)
    
    extracted: list[Path] = []
    base_name = sanitize_filename(tex_path.stem)
    count = 0
    
    for texture in info.textures:
        if target_format is None or texture.format == target_format:
            safe_ext = sanitize_extension(texture.format.value)
            output_path = (output_dir / f"{base_name}_{count}_{texture.width}x{texture.height}.{safe_ext}").resolve()
            
            if not str(output_path).startswith(str(output_dir)):
                raise ValueError(f"Invalid output path: {output_path}")
            
            if not overwrite and output_path.exists():
                continue
            
            with open(output_path, "wb") as f:
                f.write(texture.data)
            
            extracted.append(output_path)
            count += 1
    
    return extracted
