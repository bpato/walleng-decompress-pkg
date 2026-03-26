"""Tests for walleng_pkg package."""

import io
import struct
import tempfile
from pathlib import Path

import pytest

from walleng_pkg.core import (
    FileEntry,
    PackageInfo,
    extract_files,
    extract_package,
    parse_package,
    read_uint32,
    read_string,
)


def create_test_pkg(files: list[tuple[str, bytes]], root: str = "test_output") -> bytes:
    """Create a test .pkg binary file.
    
    Args:
        files: List of (filename, content) tuples.
        root: Root directory name for the package.
        
    Returns:
        Binary content of the .pkg file.
    """
    buffer = io.BytesIO()
    
    root_bytes = root.encode("utf-8")
    buffer.write(struct.pack("<I", len(root_bytes)))
    buffer.write(root_bytes)
    
    buffer.write(struct.pack("<I", len(files)))
    
    data_offset = buffer.tell()
    data_parts: list[bytes] = []
    current_offset = 0
    
    for filename, content in files:
        filename_bytes = filename.encode("utf-8")
        buffer.write(struct.pack("<I", len(filename_bytes)))
        buffer.write(filename_bytes)
        
        buffer.write(struct.pack("<I", current_offset))
        buffer.write(struct.pack("<I", len(content)))
        
        data_parts.append(content)
        current_offset += len(content)
    
    for part in data_parts:
        buffer.write(part)
    
    return buffer.getvalue()


class TestReadFunctions:
    """Tests for binary read utilities."""
    
    def test_read_uint32_little_endian(self):
        data = b"\x2a\x00\x00\x00"
        assert read_uint32(data) == 42
    
    def test_read_uint32_zero(self):
        data = b"\x00\x00\x00\x00"
        assert read_uint32(data) == 0
    
    def test_read_string(self):
        data = b"hello\x00\x00"
        assert read_string(data) == "hello"
    
    def test_read_string_with_trailing_spaces(self):
        data = b"hello   \x00"
        assert read_string(data) == "hello"


class TestParsePackage:
    """Tests for package parsing."""
    
    def test_parse_invalid_file(self):
        with pytest.raises(FileNotFoundError):
            parse_package(Path("/nonexistent/file.pkg"))
    
    def test_parse_empty_package(self):
        """Test parsing a package with zero files."""
        pkg_data = create_test_pkg([])
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pkg") as f:
            f.write(pkg_data)
            f.flush()
            
            info = parse_package(Path(f.name))
            
            assert info.root == "test_output"
            assert len(info.files) == 0
            
            Path(f.name).unlink()
    
    def test_parse_single_file(self):
        """Test parsing a package with a single file."""
        pkg_data = create_test_pkg([("readme.txt", b"Hello, World!")])
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pkg") as f:
            f.write(pkg_data)
            f.flush()
            
            info = parse_package(Path(f.name))
            
            assert info.root == "test_output"
            assert len(info.files) == 1
            assert info.files[0].name == "readme.txt"
            assert info.files[0].length == 13
            
            Path(f.name).unlink()
    
    def test_parse_multiple_files(self):
        """Test parsing a package with multiple files."""
        files = [
            ("file1.txt", b"Content 1"),
            ("file2.txt", b"Content 2"),
            ("subdir/file3.txt", b"Content 3"),
        ]
        pkg_data = create_test_pkg(files)
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pkg") as f:
            f.write(pkg_data)
            f.flush()
            
            info = parse_package(Path(f.name))
            
            assert len(info.files) == 3
            assert info.files[0].name == "file1.txt"
            assert info.files[1].name == "file2.txt"
            assert info.files[2].name == "subdir/file3.txt"
            
            Path(f.name).unlink()


class TestExtractPackage:
    """Tests for package extraction."""
    
    def test_extract_single_file(self):
        """Test extracting a single file."""
        pkg_data = create_test_pkg([("readme.txt", b"Hello, World!")])
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pkg") as pkg_file:
            pkg_file.write(pkg_data)
            pkg_file.flush()
            pkg_path = Path(pkg_file.name)
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            extracted = extract_package(pkg_path, Path(tmp_dir))
            
            assert len(extracted) == 1
            
            output_file = Path(tmp_dir) / "test_output" / "readme.txt"
            assert output_file.exists()
            assert output_file.read_bytes() == b"Hello, World!"
        
        pkg_path.unlink()
    
    def test_extract_multiple_files(self):
        """Test extracting multiple files."""
        files = [
            ("file1.txt", b"First"),
            ("file2.txt", b"Second"),
            ("subdir/nested.txt", b"Nested content"),
        ]
        pkg_data = create_test_pkg(files)
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pkg") as pkg_file:
            pkg_file.write(pkg_data)
            pkg_file.flush()
            pkg_path = Path(pkg_file.name)
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            extracted = extract_package(pkg_path, Path(tmp_dir))
            
            assert len(extracted) == 3
            
            assert (Path(tmp_dir) / "test_output" / "file1.txt").read_bytes() == b"First"
            assert (Path(tmp_dir) / "test_output" / "file2.txt").read_bytes() == b"Second"
            assert (Path(tmp_dir) / "test_output" / "subdir" / "nested.txt").read_bytes() == b"Nested content"
        
        pkg_path.unlink()
    
    def test_extract_creates_directory_structure(self):
        """Test that extraction creates proper directory structure."""
        files = [
            ("a/b/c/deep.txt", b"Deep"),
            ("x/y.txt", b"Shallow"),
        ]
        pkg_data = create_test_pkg(files)
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pkg") as pkg_file:
            pkg_file.write(pkg_data)
            pkg_file.flush()
            pkg_path = Path(pkg_file.name)
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            extract_package(pkg_path, Path(tmp_dir))
            
            assert (Path(tmp_dir) / "test_output" / "a" / "b" / "c").is_dir()
            assert (Path(tmp_dir) / "test_output" / "x").is_dir()
        
        pkg_path.unlink()
    
    def test_extract_custom_root(self):
        """Test extraction with custom root directory name."""
        pkg_data = create_test_pkg([("file.txt", b"Data")], root="custom_root")
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pkg") as pkg_file:
            pkg_file.write(pkg_data)
            pkg_file.flush()
            pkg_path = Path(pkg_file.name)
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            extract_package(pkg_path, Path(tmp_dir))
            
            assert (Path(tmp_dir) / "custom_root" / "file.txt").exists()
        
        pkg_path.unlink()
