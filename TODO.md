# Watcom API Doc Generator — TODO

Project: Python tool to scan Watcom C++ header files and produce markdown API documentation.
Host platform: Debian Linux / MacOS
Target: Watcom C/C++ for 32-bit protected mode DOS

---

## Phase 1 — Project Setup

- [x] Create project directory structure: `wapi/` with `__init__.py`, `cli.py`, `parser.py`, `writer.py`, `models.py`
- [x] Create `wapi/TODO.md` (this file)
- [x] Create `README.md` in project root with usage instructions
- [x] Create `.gitignore` for Python artifacts

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

- [x] **Brace counting includes commented-out lines** — FIXED: Lines starting with `//` are now skipped when counting braces.
- [x] **Class methods not extracted** — FIXED: Added patterns for constructors, destructors, and `::` scope methods.
- [x] **Namespace items not extracted** — FIXED: `_extract_namespace_body` now extracts all item types from namespace bodies.
- [x] **Macros not extracted** — FIXED: Main loop now advances `i` after each construct match.
- [x] **Template classes treated as nested classes** — FIXED: Template lines are now skipped in main loop and class bodies.
- [x] **`_try_parse_class` and `_try_parse_namespace` don't return next index** — FIXED: Both now return the correct next index.
- [x] **Control flow keywords parsed as functions** — FIXED: Added keyword filtering in main loop and `_try_parse_function`.
- [x] **Function regex doesn't handle leading whitespace** — FIXED: Added `^\s*` and keyword handling to `_FUNC_SIG_RE`.
- [x] **Unnamed parameters cause regex failure** — FIXED: Parameter name is now optional in `_PARAM_RE`.

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

- [x] Run against EXAMPLE project:
  - `python3 wapi/cli.py /path/to/Sandbox/EXAMPLE -v -o /path/to/Sandbox/docs`
  - 28 header files processed, 0 errors
  - Output reviewed for GRAPHICS.MD, MATH32.MD, VECTOR.MD and others
- [x] **Block comments not stripped** — FIXED: `_strip_block_comments()` now handles nested comments, CRLF, and single quotes in line comments.
- [x] **Parameter extraction** — FIXED: `_PARAM_RE` regex now correctly extracts types, names, pointers, references, and multi-word types.
- [x] **Doxygen comments not extracted** — FIXED: `_strip_block_comments()` now preserves `/** */` Doxygen comments while stripping regular `/* */` block comments. `_find_comment_backwards()` now correctly handles `*/` as comment end and skips template lines between comments and declarations.
- [x] **Doxygen comments for functions/methods not extracted** — FIXED: `_find_comment_backwards()` now correctly extracts Doxygen comments for top-level functions, class methods, and multi-line declarations. Also fixed multi-line typedef parsing (`typedef struct/enum/union { ... } name;`).

- [x] Test with headers containing:
  - Heavy template usage (GRAPHICS.H) — tested, output reviewed
  - Inline assembly pragmas (MATH32.H) — tested, output reviewed
  - Namespace blocks (GRAPHICS.H — Tex8bpp) — tested, output reviewed
  - Multiple classes in one file (GRAPHICS.H) — tested, output reviewed
  - Forward declarations — tested
- [x] **Test harness created** — `test_harness.py` with 27 regression test cases covering block comments, parameter extraction, function signatures, classes, macros, typedefs, namespaces, and real-header integration patterns.
- [ ] Handle any Watcom-specific constructs not covered
- [ ] Performance test with larger projects

## Phase 7 — Documentation & Release

- [x] Write `README.md` with:
  - Project description
  - Installation & usage
  - Output format examples
  - Limitations & known issues
- [x] Final git commit with descriptive message

---

## Known Issues

These are the remaining known issues that affect output quality:

1. **Complex template types truncated** — Parameters like `Graphics<T>` are extracted as just `Graphics`. The simple regex-based parameter extraction doesn't handle complex template types with nested angle brackets.

2. **Duplicate function declarations** — FIXED: Deduplication now uses full signature key `(name, return_type, param_types)` instead of just `(name, return_type, param_count)`, correctly handling overloaded methods.

3. **Function body tracking** — The main loop doesn't track function bodies, so lines inside free function bodies may be incorrectly matched by regex patterns.

4. **Attribute type/name extraction** — FIXED: Now correctly extracts multi-word types (e.g., `const unsigned int`) and handles multiple comma-separated variable names.

5. **Line comments not extracted** — `//` line comments preceding declarations are skipped by `_find_comment_backwards()`. Only Doxygen-style `/** */` comments are extracted.

---

## Test Harness — Implementation Plan (Future Work)

The test harness skeleton (`test_harness.py`) is in place with 27 passing tests. The following enhancements are planned:

### Priority 1 — Expand coverage from git history

1. **Review git commit history for bug patterns to test**
   - Run `git log --all --oneline -- wapi/parser.py` to find commits that fixed bugs
   - For each bug fix, create a regression test that reproduces the original bug
   - Key commits to review:
     - Block comment stripping fixes (nested `/*`, CRLF, single quotes in `//`)
     - Parameter extraction regex fixes (anonymous params, pointers, references)
     - Class method extraction (constructors, destructors, `::` scope)
     - Control flow keyword filtering
     - Template line skipping
     - Duplicate function deduplication
   - Extract representative source snippets from EXAMPLE headers and create test cases

2. **Add integration tests against real header files**
   - Parse each EXAMPLE header file directly and validate the AST
   - Check that expected classes, functions, macros, typedefs, enums are present
   - Verify parameter counts and types match known-good output
   - Store expected AST snapshots in `test_data/` directory

### Priority 2 — Output validation

3. **Markdown output comparison tests**
   - Generate markdown for known headers and compare against golden files
   - Store golden output in `test_data/golden/`
   - Use diff-based comparison to catch regressions

4. **AST structure validation**
   - Verify that `HeaderDoc` has correct structure (no circular references)
   - Check that class methods are properly nested (not duplicated in global functions)
   - Validate template parameter extraction accuracy

### Priority 3 — Edge cases

5. **Edge case test cases**
   - Empty header files
   - Headers with only comments
   - Headers with deeply nested templates (e.g., `Map<String, Vector<int>>`)
   - Headers with multiple `#pragma aux` blocks
   - Headers with `#ifdef` / `#endif` guards
   - Headers with Windows CRLF line endings (real-world format)
   - Headers with inline assembly blocks
   - Headers with forward declarations only
   - Headers with operator overloading (`operator+`, etc.)
   - Headers with template specialisations

6. **Parser robustness tests**
   - Malformed syntax (unclosed braces, missing semicolons)
   - Extremely long lines
   - Headers with mixed tabs and spaces
   - Headers with unusual whitespace patterns

### Priority 4 — CI/CD integration

7. **Automated test runner**
   - Add `Makefile` or shell script to run all tests
   - Configure CI to run `python3 test_harness.py` on every commit
   - Add `--export` flag support for JSON results in CI logs

---

## Notes for Future Agents

### Current Architecture

- **Parser**: Line-by-line regex-based parser (not tokeniser-based). More robust than the original tokeniser approach which crashed on Watcom headers with inline assembly.
- **Brace counting**: Counts `{` and `}` to find class/namespace boundaries. Commented-out lines (`//`) are now skipped during brace counting.
- **Construct matching**: Uses regex patterns to identify classes, functions, namespaces, enums, typedefs, and macros.

### Key Files

- `models.py` — All data classes. Well-structured, no changes needed.
- `parser.py` — Main parser. **This is where all work is needed.**
- `writer.py` — Markdown generation. Works correctly once parser produces correct AST.
- `cli.py` — CLI entry point. Works correctly, just needs the parser to produce valid output.

### Testing

```bash
cd /home/mongo.guest/Users/mongo/Dropbox/Code/2026/Pi-agent-env/Sandbox
python3 wapi/cli.py /home/mongo.guest/Users/mongo/Dropbox/Code/2026/Pi-agent-env/Sandbox/EXAMPLE -v
```

### Watcom-Specific Considerations

- `#pragma aux` blocks can span many lines with escaped quotes — already handled (skipped).
- Watcom inline assembly uses `"` escaped strings — the parser skips these correctly.
- Template syntax with angle brackets `<>` — brace counting should not confuse `<` and `>` with `{` and `}`.
