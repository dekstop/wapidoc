# Watcom API Doc Generator — TODO

Project: Python tool to scan Watcom C++ header files and produce markdown API documentation.
Host platform: Debian Linux / MacOS
Target: Watcom C/C++ for 32-bit protected mode DOS

---

## Phase 1 — Project Setup

- [x] Create project directory structure: `wapi/` with `__init__.py`, `cli.py`, `parser.py`, `writer.py`, `models.py`
- [x] Create `wapi/TODO.md` (this file)
- [ ] Create `README.md` in project root with usage instructions
- [ ] Create `.gitignore` for Python artifacts

## Phase 2 — Data Models

- [x] Implement `models.py` with data classes:
  - `Comment` — extracted Doxygen comment text
  - `Function` — name, signature, return type, parameters, template params, comment
  - `Class` — name, template params, base class, attributes, methods, comment
  - `Namespace` — name, contained items (classes, functions, etc.)
  - `Macro` — name, value, comment
  - `Typedef` — name, type, comment
  - `Enum` — name, members, comment
  - `HeaderDoc` — the header filename, header-level comment, all top-level items

## Phase 3 — Parser Core

- [x] Initial implementation of `parser.py`:
  - Line-by-line parser (not tokeniser-based — simpler and more robust)
  - Handles `class`, `struct`, `namespace`, `template`, `enum`, `typedef`, `#define`
  - Extracts Doxygen comments (`/** ... */`) preceding declarations
  - Extracts function signatures (return type, name, params, template args)
  - Handles Watcom-specific preprocessor pragmas (`#pragma aux`) — skips them
  - Handles `#include` directives — records them but doesn't follow (isolation mode)
  - Brace counting for class/namespace body extraction

- [ ] **CRITICAL BUGS TO FIX:**
  - **Brace counting includes commented-out lines** — lines like `// void (*draw_pixel)(...)` contain `{` and `}` which break brace counting. Must skip commented lines (lines starting with `//`) when counting braces.
  - **Class methods not extracted** — `_extract_class_body` finds classes but doesn't extract methods. The `brace_count > 1` check skips function bodies correctly, but the function signature matching (`_FUNC_SIG_RE`) isn't triggering for class methods.
  - **Namespace items not extracted** — `_extract_namespace_body` finds namespaces but `_try_parse_class` returns `None` for namespace members because the brace counting is wrong. Fixing the brace counting bug should resolve this.
  - **Macros not extracted** — `_try_parse_macro` doesn't advance the line index, causing an infinite loop. The main loop in `parse()` needs to advance `i` after each construct match.
  - **Template classes treated as nested classes** — e.g., `template <typename T> class Image {` is parsed as a nested class inside `Font`. Need to skip template lines before checking for class/namespace.
  - **`_try_parse_class` and `_try_parse_namespace` don't return next index** — they return `None`/`False` instead of the index after the construct, so the main loop doesn't know where to continue.

## Phase 4 — Markdown Writer

- [x] Implement `writer.py`:
  - Generate markdown from `HeaderDoc` AST
  - Header-level comment section
  - Classes section with attributes, constructors, methods
  - Namespaces section with contained items
  - Macros section
  - Typedefs section
  - Enums section
  - Functions section (free functions)
  - Proper markdown formatting (headers, lists, code blocks)
  - Preserve full Doxygen comment text
  - Handle templated signatures properly in output

## Phase 5 — CLI & Directory Traversal

- [x] Implement `cli.py`:
  - `argparse` entry point
  - Accept project root directory as positional argument
  - `-o, --output` flag to override output directory (default: `docs/`)
  - `-v, --verbose` flag for progress output
  - Recursively find all `.H` files under project root
  - Mirror directory structure in output
  - Process each header file
  - Handle errors gracefully (unparseable files → warning + skip)
  - Print summary at end (files processed, errors, output location)

## Phase 6 — Testing & Refinement

- [ ] Run against EXAMPLE project:
  - `python -m wapi /home/mongo.guest/Users/mongo/Dropbox/Code/2026/Pi-agent-env/Sandbox/EXAMPLE`
  - Review output for MATH32.H, GRAPHICS.H, and others
  - Verify markdown quality and completeness
- [ ] Fix parser edge cases discovered during testing
- [ ] Test with headers containing:
  - Heavy template usage (GRAPHICS.H)
  - Inline assembly pragmas (MATH32.H)
  - Namespace blocks (GRAPHICS.H — Tex8bpp)
  - Multiple classes in one file
  - Forward declarations
- [ ] Handle any Watcom-specific constructs not covered
- [ ] Performance test with larger projects

## Phase 7 — Documentation & Release

- [ ] Write `README.md` with:
  - Project description
  - Installation & usage
  - Output format examples
  - Limitations & known issues
- [ ] Create example output in repository
- [ ] Final git commit with descriptive message

---

## Notes for Future Agents

### Current Architecture

- **Parser**: Line-by-line regex-based parser (not tokeniser-based). More robust than the original tokeniser approach which crashed on Watcom headers with inline assembly.
- **Brace counting**: Counts `{` and `}` to find class/namespace boundaries. **BUG**: Currently counts braces in commented-out lines, which breaks on headers like GRAPHICS.H where commented code contains `{` and `}`.
- **Construct matching**: Uses regex patterns to identify classes, functions, namespaces, enums, typedefs, and macros.

### Key Files

- `models.py` — All data classes. Well-structured, no changes needed.
- `parser.py` — Main parser. **This is where all work is needed.**
- `writer.py` — Markdown generation. Works correctly once parser produces correct AST.
- `cli.py` — CLI entry point. Works correctly, just needs the parser to produce valid output.

### Known Issues (see Phase 3 above)

1. **Commented-out brace counting** — Lines starting with `//` should be skipped when counting braces.
2. **Method extraction** — `_extract_class_body` needs to extract methods from class bodies.
3. **Namespace items** — `_extract_namespace_body` needs to extract classes, functions, etc. from namespaces.
4. **Macro infinite loop** — `_try_parse_macro` doesn't advance the line index.
5. **Template class detection** — Template classes should be detected at the top level, not as nested classes.

### Watcom-Specific Considerations

- `#pragma aux` blocks can span many lines with escaped quotes — already handled (skipped).
- Watcom inline assembly uses `"` escaped strings — the parser skips these correctly.
- Template syntax with angle brackets `<>` — brace counting should not confuse `<` and `>` with `{` and `}`.

### Testing

```bash
cd /home/mongo.guest/Users/mongo/Dropbox/Code/2026/Pi-agent-env/Sandbox
python3 wapi/cli.py /home/mongo.guest/Users/mongo/Dropbox/Code/2026/Pi-agent-env/Sandbox/EXAMPLE -v
```

---

## Phase 2 — Data Models

- [ ] Implement `models.py` with data classes:
  - `Comment` — extracted Doxygen comment text
  - `Function` — name, signature, return type, parameters, template params, comment
  - `Class` — name, template params, base class, attributes, methods, comment
  - `Namespace` — name, contained items (classes, functions, etc.)
  - `Macro` — name, value, comment
  - `Typedef` — name, type, comment
  - `Enum` — name, members, comment
  - `HeaderDoc` — the header filename, header-level comment, all top-level items

---

## Phase 3 — Parser Core

- [ ] Implement `parser.py`:
  - Tokeniser wrapper around Python's `tokenise` module
  - State-machine parser recognising C++ constructs
  - Handle `class`, `struct`, `namespace`, `template`, `enum`, `typedef`, `#define`
  - Extract Doxygen comments (`/** ... */`) preceding declarations
  - Extract function signatures (return type, name, params, template args)
  - Handle Watcom-specific preprocessor pragmas (`#pragma aux`) — skip them
  - Handle inline assembly blocks — skip them
  - Handle template specialisation syntax (`template<...>`)
  - Handle nested classes and namespace blocks
  - Handle forward declarations vs full declarations
  - Handle `inline` function declarations with bodies
  - Handle `friend` declarations
  - Handle `using` directives
  - Handle `#ifdef` / `#ifndef` guarded sections (include or skip based on guard)
  - Handle multi-line tokens (e.g. split across lines)
  - Handle string literals and character literals in tokens
  - Handle `#include` directives — record them but don't follow (isolation mode)

---

## Phase 4 — Markdown Writer

- [ ] Implement `writer.py`:
  - Generate markdown from `HeaderDoc` AST
  - Header-level comment section
  - Classes section with attributes, constructors, methods
  - Namespaces section with contained items
  - Macros section
  - Typedefs section
  - Enums section
  - Functions section (free functions)
  - Proper markdown formatting (headers, lists, code blocks)
  - Preserve full Doxygen comment text
  - Handle templated signatures properly in output

---

## Phase 5 — CLI & Directory Traversal

- [ ] Implement `cli.py`:
  - `argparse` entry point
  - Accept project root directory as positional argument
  - `-o, --output` flag to override output directory (default: `docs/`)
  - `-v, --verbose` flag for progress output
  - Recursively find all `.H` files under project root
  - Mirror directory structure in output
  - Process each header file
  - Handle errors gracefully (unparseable files → warning + skip)
  - Print summary at end (files processed, errors, output location)

---

## Phase 6 — Testing & Refinement

- [ ] Run against EXAMPLE project:
  - `python -m wapi /home/mongo.guest/Users/mongo/Dropbox/Code/2026/Pi-agent-env/Sandbox/EXAMPLE`
  - Review output for MATH32.H, GRAPHICS.H, and others
  - Verify markdown quality and completeness
- [ ] Fix parser edge cases discovered during testing
- [ ] Test with headers containing:
  - Heavy template usage (GRAPHICS.H)
  - Inline assembly pragmas (MATH32.H)
  - Namespace blocks (GRAPHICS.H — Tex8bpp)
  - Multiple classes in one file
  - Forward declarations
- [ ] Handle any Watcom-specific constructs not covered
- [ ] Performance test with larger projects

---

## Phase 7 — Documentation & Release

- [ ] Write `README.md` with:
  - Project description
  - Installation & usage
  - Output format examples
  - Limitations & known issues
- [ ] Create example output in repository
- [ ] Final git commit with descriptive message

---

## Notes for Future Agents

- Python 3.8+ required (f-strings, dataclasses)
- No external dependencies — stdlib only
- Use `tokenise` module for lexing, not `ast` (ast is for Python)
- C++ parsing is done via a custom state machine, not a full parser
- Watcom `#pragma aux` blocks can span many lines with `\"` escaped newlines — these must be skipped entirely
- Template syntax can be deeply nested with angle brackets — careful bracket counting needed
- Doxygen comments can span arbitrary lines — track them until next declaration
- The parser should be forgiving — emit warnings for unrecognised constructs, don't crash
