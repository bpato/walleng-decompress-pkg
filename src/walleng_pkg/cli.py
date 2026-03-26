"""Command-line interface for walleng-pkg."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from walleng_pkg.core import extract_package, parse_package


def main() -> int:
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        prog="walleng-pkg",
        description="Decompress .pkg files from Wallpaper Engine",
    )
    parser.add_argument(
        "package",
        type=Path,
        help="Path to the .pkg file to extract",
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
    
    args = parser.parse_args()
    
    if not args.package.is_file():
        print(f"Error: File not found: {args.package}", file=sys.stderr)
        return 1
    
    try:
        if args.list:
            info = parse_package(args.package)
            print(f"Root: {info.root}")
            print(f"Files: {len(info.files)}\n")
            for entry in info.files:
                print(f"  {entry.name} ({entry.length:,} bytes)")
            return 0
        
        extracted = extract_package(args.package, args.output)
        
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
