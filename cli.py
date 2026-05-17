"""
CLI entry point for the Watcom API Doc Generator.

Usage:
    python -m wapidoc <project_root> [--output <dir>] [--verbose]
"""

import argparse
import os
import sys
from pathlib import Path

from parser import HeaderParser
from writer import generate_markdown


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Generate API documentation from Watcom C++ header files."
    )
    parser.add_argument(
        "project_root",
        help="Root directory of the Watcom C++ project"
    )
    parser.add_argument(
        "-o", "--output",
        default="docs",
        help="Output directory for markdown files (default: docs)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Print progress information"
    )

    args = parser.parse_args()
    project_root = Path(args.project_root).resolve()
    output_dir = Path(args.output)

    if not project_root.is_dir():
        print(f"Error: {project_root} is not a directory", file=sys.stderr)
        sys.exit(1)

    # Find all .H files
    header_files = sorted(project_root.rglob("*.H"))
    header_files.extend(sorted(project_root.rglob("*.h")))

    if not header_files:
        print(f"No header files found in {project_root}", file=sys.stderr)
        sys.exit(1)

    if args.verbose:
        print(f"Found {len(header_files)} header file(s) in {project_root}")

    # Process each header
    processed = 0
    errors = 0
    parser_obj = HeaderParser()

    for header_path in header_files:
        rel_path = header_path.relative_to(project_root)
        output_path = output_dir / rel_path.with_suffix(".MD")

        try:
            # Read header file
            source = header_path.read_text(encoding="utf-8")

            # Parse
            header_doc = parser_obj.parse(str(rel_path), source)

            # Generate markdown
            markdown = generate_markdown(header_doc)

            # Write output
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(markdown, encoding="utf-8")

            processed += 1
            if args.verbose:
                print(f"  {rel_path} → {output_path}")

        except Exception as e:
            errors += 1
            if args.verbose:
                print(f"  ERROR: {rel_path}: {e}", file=sys.stderr)

    # Summary
    print(f"\nDone: {processed} file(s) processed, {errors} error(s).")
    print(f"Output written to: {output_dir}")


if __name__ == "__main__":
    main()
