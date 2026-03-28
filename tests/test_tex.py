"""Tests for TEX texture extraction."""

import io
import struct
import tempfile
from pathlib import Path

import pytest

from walleng_pkg.tex import (
    PNG_SIGNATURE,
    JPG_SIGNATURE,
    TextureFormat,
    extract_textures,
    extract_png_textures,
    extract_jpg_textures,
    parse_tex_package,
)


def create_test_tex(png_data_list: list[bytes], width: int = 1920, height: int = 1080) -> bytes:
    """Create a test TEX file with PNG textures following the real format."""
    buffer = io.BytesIO()
    
    buffer.write(b"TEXV")
    buffer.write(b"0005")
    buffer.write(b"\x00")
    
    buffer.write(b"TEXI")
    buffer.write(b"0001")
    buffer.write(b"\x00")
    
    buffer.write(b"\x00" * 4)
    buffer.write(struct.pack("<I", len(png_data_list)))
    buffer.write(struct.pack("<I", 2048))
    buffer.write(struct.pack("<I", 2048))
    buffer.write(struct.pack("<I", width))
    buffer.write(struct.pack("<I", height))
    buffer.write(b"\xDB\x2D\x39\xFF")
    
    buffer.write(b"TEXB")
    buffer.write(b"0003")
    buffer.write(b"\x00")
    
    buffer.write(b"\x00" * (0x37 - buffer.tell()))
    buffer.write(struct.pack("<I", 1))
    buffer.write(struct.pack("<I", 13))
    buffer.write(struct.pack("<I", len(png_data_list)))
    
    buffer.write(b"\x00" * (0x43 - buffer.tell()))
    
    for i, png_data in enumerate(png_data_list):
        current_width = max(1, width >> i)
        current_height = max(1, height >> i)
        
        buffer.write(struct.pack("<I", current_width))
        buffer.write(struct.pack("<I", current_height))
        buffer.write(b"\x00" * 8)
        buffer.write(struct.pack("<I", len(png_data)))
        buffer.write(png_data)
        buffer.write(b"\x00" * 12)
    
    return buffer.getvalue()


class TestParseTex:
    """Tests for TEX file parsing."""
    
    def test_parse_invalid_file(self):
        with pytest.raises(FileNotFoundError):
            parse_tex_package(Path("/nonexistent/file.tex"))
    
    def test_parse_too_small_file(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".tex") as f:
            f.write(b"INVALID")
            f.flush()
            
            with pytest.raises(ValueError, match="File too small"):
                parse_tex_package(Path(f.name))
            
            Path(f.name).unlink()


class TestExtractTextures:
    """Tests for texture extraction."""
    
    def test_extract_single_png(self):
        png_data = PNG_SIGNATURE + b"test png content"
        tex_data = create_test_tex([png_data])
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".tex") as f:
            f.write(tex_data)
            f.flush()
            tex_path = Path(f.name)
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            extracted = extract_textures(tex_path, Path(tmp_dir))
            
            assert len(extracted) == 1
            assert str(extracted[0]).endswith(".png")
            data = extracted[0].read_bytes()
            assert data == png_data
        
        tex_path.unlink()
    
    def test_extract_multiple_png(self):
        png1 = PNG_SIGNATURE + b"png1"
        png2 = PNG_SIGNATURE + b"png2"
        tex_data = create_test_tex([png1, png2])
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".tex") as f:
            f.write(tex_data)
            f.flush()
            tex_path = Path(f.name)
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            extracted = extract_textures(tex_path, Path(tmp_dir))
            
            assert len(extracted) >= 1
        
        tex_path.unlink()
    
    def test_extract_multiple(self):
        png1 = PNG_SIGNATURE + b"png1"
        png2 = PNG_SIGNATURE + b"png2"
        tex_data = create_test_tex([png1, png2])
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".tex") as f:
            f.write(tex_data)
            f.flush()
            tex_path = Path(f.name)
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            extracted = extract_textures(tex_path, Path(tmp_dir))
            
            assert len(extracted) >= 1
        
        tex_path.unlink()
