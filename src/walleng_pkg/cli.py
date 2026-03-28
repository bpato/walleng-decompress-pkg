"""Command-line interface for walleng-pkg."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from walleng_pkg.core import extract_package, parse_package
from walleng_pkg.tex import extract_textures, parse_tex_package


def main() -> int:
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        prog="walleng-pkg",
        description="Decompress .pkg files from Wallpaper Engine",
    )
    parser.add_argument(
        "file",
        type=Path,
        nargs="?",
        help="Path to the .pkg or .tex file",
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=None,
        help="Output directory (defaults to current directory)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Print extracted file names",
    )
    parser.add_argument(
        "-l", "--list",
        action="store_true",
        help="List package contents without extracting",
    )
    parser.add_argument(
        "-t", "--tex",
        action="store_true",
        help="Extract PNG textures from .tex files found in .pkg",
    )
    parser.add_argument(
        "-x", "--extract-tex",
        action="store_true",
        help="Extract textures from a .tex file",
    )
    
    args = parser.parse_args()
    
    if args.extract_tex:
        if not args.file:
            print("Error: --extract-tex requires a .tex file", file=sys.stderr)
            return 1
        
        if not args.file.is_file():
            print(f"Error: File not found: {args.file}", file=sys.stderr)
            return 1
        
        if args.file.suffix.lower() != ".tex":
            print(f"Error: --extract-tex requires a .tex file", file=sys.stderr)
            return 1
        
        try:
            extracted = extract_textures(args.file, args.output)
            
            if args.verbose:
                for path in extracted:
                    print(path)
            
            print(f"Extracted {len(extracted)} textures.")
            return 0
            
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
    
    if not args.file:
        parser.print_help()
        return 1
    
    if not args.file.is_file():
        print(f"Error: File not found: {args.file}", file=sys.stderr)
        return 1
    
    try:
        if args.list:
            info = parse_package(args.file)
            print(f"Root: {info.root}")
            print(f"Files: {len(info.files)}\n")
            for entry in info.files:
                print(f"  {entry.name} ({entry.length:,} bytes)")
            return 0
        
        extracted = extract_package(args.file, args.output, args.tex)
        
        if args.verbose:
            for path in extracted:
                print(path)
        
        print(f"Extracted {len(extracted)} files.")
        return 0
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
