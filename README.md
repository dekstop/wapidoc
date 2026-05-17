# wapidoc — Watcom C++ API Doc Generator

## Status

✅ **Parser** — Extracts classes, methods, namespaces, functions, enums, typedefs, macros, and Doxygen comments.
✅ **Test harness** — 27 passing tests covering parsers, output, and integration.
✅ **Output** — Generates clean markdown API documentation for Watcom C++ headers.

---

## Overview

`wapidoc` is a Python 3 tool that scans Watcom C++ header files and produces
structured markdown API documentation. It is designed for use by coding agents
that need to understand a C++ codebase without consuming the entire source in
context memory.

The tool extracts class declarations, methods, functions, enums, typedefs,
macros, and Doxygen-style comments from `.H` and `.h` header files, then
generates clean markdown summaries that agents can consult on demand.

## Requirements

* Python 3.8+
* No external dependencies — standard library only

## Usage

```bash
python3 wapidoc/cli.py <project_root> [options]
```

### Arguments

| Argument | Description |
|---|---|
| `project_root` | Root directory of the C++ project (required) |

### Options

| Option | Default | Description |
|---|---|---|
| `-o, --output` | `docs/` | Output directory for generated markdown files |
| `-v, --verbose` | Off | Print progress information for each file processed |

### Example

```bash
python3 wapidoc/cli.py /path/to/project -v -o /path/to/docs
```

This scans `/path/to/project` recursively for `.H` and `.h` files, parses each
one, and writes corresponding `.MD` files into `/path/to/docs`, mirroring the source
directory structure.

## Output Format

For each header file, a markdown file is generated with the following sections
(in order):

1. **Header Overview** — header-level Doxygen comment (if present)
2. **Includes** — list of `#include` directives found (for reference only)
3. **Classes and Structs** — each class with its attributes, methods, and
   Doxygen comments
4. **Namespaces** — namespace blocks with contained types, functions, enums, etc.
5. **Functions** — free-standing function declarations with signatures and comments
6. **Enums** — enum declarations and their members
7. **Typedefs** — typedef aliases and their underlying types
8. **Macros** — `#define` constants and their values

### Example output (excerpt)

```markdown
# API Documentation: SRC/VECTOR.H

## Header Overview

Vector class, accommodating any number of dimensions.

## Includes

- `stdarg.h`

## Classes and Structs

### class Vector<T>

Vector class with template dimension parameter.

**Attributes:**

- `T coords[Dim]`

## Functions

- `void print_vector3d()`

- `void print_vector4d()`
```

## Architecture

The tool is organised into four modules:

| Module | Purpose |
|---|---|
| `models.py` | Data classes (AST nodes): `Class`, `Function`, `Namespace`, `Enum`, `Typedef`, `Macro`, `HeaderDoc`, etc. |
| `parser.py` | Line-by-line regex-based parser that walks header files and builds the AST. Handles C++ constructs, Doxygen comments, Watcom `#pragma aux` blocks, and brace counting. |
| `writer.py` | Markdown generation from the AST. Formats all constructs into clean, readable markdown. |
| `cli.py` | CLI entry point with `argparse`. Traverses directories, processes headers, handles errors, and prints summaries. |

### Parser approach

The parser uses a simple line-by-line regex-based approach rather than a
tokeniser. This was chosen because it is more robust against Watcom headers
containing inline assembly blocks that would crash a tokeniser-based parser.

Key parsing features:
* Doxygen comment extraction (`/** ... */`) preceding declarations
* Brace counting for class/namespace body boundaries (skips commented-out lines)
* Watcom `#pragma aux` block detection and skipping
* Template parameter extraction with angle bracket depth tracking
* Function parameter parsing with default value detection

## Current Limitations

The parser currently has several known issues that affect output quality:

1. **Complex template types truncated** — Parameters like `Graphics<T>` are
   extracted as just `Graphics`. The regex-based parameter extraction doesn't
   handle complex template types with nested angle brackets.
2. **Free function body tracking** — The main parser loop doesn't track free
   function bodies, so lines inside free function bodies may be incorrectly
   matched by regex patterns.
3. **Line comments not extracted** — `//` line comments preceding declarations
   are skipped by `_find_comment_backwards()`. Only Doxygen-style `/** */`
   comments are extracted.

See `TODO.md` for the full list of bugs and planned fixes.
