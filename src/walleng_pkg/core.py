"""Core functionality for parsing and extracting Wallpaper Engine .pkg files."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from walleng_pkg.tex import extract_textures as extract_tex_textures


@dataclass
class FileEntry:
    """Represents a file entry within a .pkg package."""
    name: str
    offset: int
    length: int


@dataclass
class PackageInfo:
    """Metadata extracted from a .pkg package."""
    root: str
    files: list[FileEntry]
    data_offset: int


def read_uint32(data: bytes) -> int:
    """Read a 32-bit unsigned integer from bytes (little-endian)."""
    return int.from_bytes(data, byteorder="little", signed=False)


def read_string(data: bytes) -> str:
    """Read a null-terminated UTF-8 string and strip padding."""
    return data.decode("utf-8").rstrip("\x00").rstrip()


def read_pascal_string(file: BinaryIO) -> str:
    """Read a length-prefixed string from a binary file."""
    length = read_uint32(file.read(4))
    return read_string(file.read(length))


def parse_package(pathfile: Path) -> PackageInfo:
    """Parse a .pkg file and extract its metadata.
    
    Args:
        pathfile: Path to the .pkg file.
        
    Returns:
        PackageInfo containing parsed metadata.
        
    Raises:
        FileNotFoundError: If the package file doesn't exist.
        ValueError: If the file format is invalid.
    """
    if not pathfile.is_file():
        raise FileNotFoundError(f"Package file not found: {pathfile}")
    
    with open(pathfile, "rb") as f:
        root = read_pascal_string(f)
        num_files = read_uint32(f.read(4))
        
        files: list[FileEntry] = []
        for _ in range(num_files):
            name = read_pascal_string(f)
            offset = read_uint32(f.read(4))
            length = read_uint32(f.read(4))
            files.append(FileEntry(name=name, offset=offset, length=length))
        
        data_offset = f.tell()
    
    return PackageInfo(root=root, files=files, data_offset=data_offset)


def create_directory_tree(info: PackageInfo, output_dir: Path) -> None:
    """Create the directory structure within a package.
    
    Args:
        info: Parsed package information.
        output_dir: Base directory to extract into.
    """
    base_path = output_dir / info.root
    
    for file_entry in info.files:
        file_path = base_path / file_entry.name
        file_path.parent.mkdir(parents=True, exist_ok=True)


def extract_files(info: PackageInfo, package_path: Path, output_dir: Path, extract_tex: bool = False) -> list[Path]:
    """Extract all files from a package.
    
    Args:
        info: Parsed package information.
        package_path: Path to the source .pkg file.
        output_dir: Base directory to extract into.
        extract_tex: If True, extract PNG textures from .tex files.
        
    Returns:
        List of paths to extracted files.
    """
    base_path = output_dir / info.root
    extracted: list[Path] = []
    
    with open(package_path, "rb") as pkg_file:
        for file_entry in info.files:
            file_path = base_path / file_entry.name
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            if not file_path.is_file():
                pkg_file.seek(info.data_offset + file_entry.offset)
                data = pkg_file.read(file_entry.length)
                
                with open(file_path, "wb") as out_file:
                    out_file.write(data)
                
                extracted.append(file_path)
                
                if extract_tex and file_path.suffix.lower() == ".tex":
                    try:
                        tex_extracted = extract_tex_textures(file_path)
                        extracted.extend(tex_extracted)
                    except Exception:
                        pass
    
    return extracted


def extract_package(package_path: Path, output_dir: Path | None = None, extract_tex: bool = False) -> list[Path]:
    """Extract all files from a Wallpaper Engine .pkg package.
    
    Args:
        package_path: Path to the .pkg file.
        output_dir: Optional output directory. Defaults to current directory.
        extract_tex: If True, extract PNG textures from .tex files.
        
    Returns:
        List of paths to extracted files.
    """
    if output_dir is None:
        output_dir = Path.cwd()
    else:
        output_dir = Path(output_dir)
    
    info = parse_package(package_path)
    create_directory_tree(info, output_dir)
    return extract_files(info, package_path, output_dir, extract_tex)
