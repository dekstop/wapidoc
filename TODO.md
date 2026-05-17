# Watcom API Doc Generator — TODO

Project: Python tool to scan Watcom C++ header files and produce markdown API documentation.
Host platform: Debian Linux / MacOS
Target: Watcom C/C++ for 32-bit protected mode DOS

---

## Changelog

### 2026-05-17 — Namespace body extraction fixed

- Redirect header lists during namespace parsing so items collect locally
- Track and skip function bodies to prevent brace-counting confusion
- Count braces from skipped lines for correct namespace boundary detection
- Collect all namespace items (funcs, classes, enums, typedefs, macros) into `ns.items`
- Added `_count_braces_in_range()` and `_skip_function_body()` helper methods
- Updated test harness with `expected_namespace_items` validation
- Updated README.md with current status

### 2026-05-17 — Document parser limitations, test priorities, and known issues

- Restructured TODO.md with clear sections: changelog, limitations, future work, known issues
- Added test coverage priorities: regression tests, output validation, edge cases, CI/CD
- Documented remaining parser issues and planned improvements

### 2026-05-17 — Operator overload parsing

- Parse operator overloads: `operator*`, `operator[]`, `operator+`, `operator-`, `operator/`, `operator=`, `operator<<`, `operator>>`, `operator!`, `operator()`, `operator new`, `operator delete`, and compound assignment operators
- Added `_OPERATOR_RE` and `_OPERATOR_SCOPE_RE` regex patterns
- Updated `_try_parse_function` to try operator pattern first
- Updated `_extract_class_body` to handle operator methods
- Handles both class methods and free function operators

### 2026-05-17 — Template type handling improvements

- Extract template params from template lines and associate with next class/method/function
- Strip angle brackets from extracted template params for clean output
- Show template params in class declarations (e.g. `class Image<typename T>`)
- Show template params in method signatures (e.g. `fill<typename DrawPixel>`)
- Handle pointer return types without space before function name
- Fix false regex matches caused by backtracking

### 2026-05-17 — __main__.py wrapper and import fixes

- Added `__main__.py` wrapper for module invocation via `python3 -m wapidoc`
- Fixed import paths across cli.py, parser.py, and writer.py for relative imports

### 2026-05-17 — Rename from wapi to wapidoc

- Renamed tool from `wapi` to `wapidoc` throughout all files
- Updated README.md, TODO.md, cli.py, and test_harness.py

### 2026-05-17 — Attribute extraction and method deduplication

- Attribute extraction now handles multi-word types (e.g. `const unsigned int`) and multiple comma-separated variable names
- Method deduplication uses full signature key (name, return_type, param_types) instead of just (name, return_type, param_count)
- Correctly handles overloaded methods and eliminates false duplicates while keeping legitimately different overloads

### 2026-05-17 — Doxygen comments for all declarations and multi-line typedefs

- `_find_comment_backwards()` now correctly extracts Doxygen comments for top-level functions, class methods, and multi-line declarations
- Fixed multi-line typedef parsing (`typedef struct`/`enum`/`union { ... } name;`)

### 2026-05-17 — Preserve Doxygen comments and extract class-level documentation

- `_strip_block_comments()` now preserves `/** */` Doxygen comments while stripping regular `/* */` block comments
- `_find_comment_backwards()` correctly handles `*/` as comment end, skips template lines between comments and declarations, and skips lines starting with `*` (Doxygen content)

### 2026-05-17 — Test harness and pointer param regex

- Added `test_harness.py`: comprehensive regression test suite with 27 test cases covering block comments, parameter extraction, function signatures, classes, macros, typedefs, namespaces, and integration patterns from real headers
- Fixed `_PARAM_RE` regex to include `*` and `&` in type group, so `int* ptr` parses correctly as `type=int* name=ptr`

### 2026-05-17 — Test harness implementation plan

- Mark test harness creation as complete in Phase 6
- Added detailed implementation plan for future test harness work:
  - Priority 1: Expand coverage from git history (extract bug patterns)
  - Priority 2: Output validation (golden file comparison, AST structure)
  - Priority 3: Edge cases (empty headers, CRLF, operator overloading, etc.)
  - Priority 4: CI/CD integration

### 2026-05-17 — Block comment stripping and parameter extraction

- Fixed `_strip_block_comments()` to handle nested `/* ... */` patterns inside block comments, Windows CRLF line endings, and line comments (`//`) containing single quotes
- Fixed `_PARAM_RE` regex to correctly extract types and names:
  - Anonymous parameters (e.g. `float`) now extracted correctly
  - Pointer/reference parameters (e.g. `const Vector<T,Dim> &p`) now extracted correctly
  - Multi-word types (e.g. `const char *`) now extracted correctly
- Fixed writer.py to handle empty names and strip whitespace in params

### 2026-05-17 — Update TODO.md: remove duplicate phases, mark completed items, refresh known issues

- Cleaned up duplicate Phase 2 section
- Marked completed items and refreshed known issues list

### 2026-05-17 — Fix parser bugs: method extraction, brace counting, keyword filtering

- Fixed class method extraction to handle constructors, destructors, and methods with `::` scope resolution
- Fixed brace counting to detect class/namespace end immediately after brace changes, preventing free functions being captured as class members
- Added template line skipping in main loop and class bodies
- Added control flow keyword filtering (return, if, while, etc.)
- Fixed function regex to handle leading whitespace and inline/static/virtual
- Fixed parameter extraction to handle unnamed parameters
- Fixed namespace body extraction
- All 28 header files now parse without errors

### 2026-05-16 — Initial checkin

- Created project structure: `__init__.py`, `cli.py`, `parser.py`, `writer.py`, `models.py`
- Implemented Phase 1–5: data models, parser core, markdown writer, CLI & directory traversal
- Created initial TODO.md with implementation plan and known bug list
- Created README.md with project overview, usage, and architecture documentation

### 2026-05-16 — Initial commit

- Added `.gitignore` and `LICENSE`

---

## Current Limitations

### Parser issues (parser.py)

Remaining issues that affect output quality:

1. **Complex template types truncated** — Parameters like `Graphics<T>` are extracted as just `Graphics`. The simple regex-based parameter extraction doesn't handle complex template types with nested angle brackets.
2. **Free function body tracking** — The main parser loop doesn't track free function bodies, so lines inside free function bodies may be incorrectly matched by regex patterns.
3. **Line comments not extracted** — `//` line comments preceding declarations are skipped by `_find_comment_backwards()`. Only Doxygen-style `/** */` comments are extracted.

---

## Future Work

### Expand test coverage

The test harness (`test_harness.py`) is in place with 27 passing tests. The following enhancements are planned:

**Priority 1 — Regression tests from git history**

1. Review git commit history for bug patterns to test:
   - Run `git log --all --oneline -- wapidoc/parser.py` to find commits that fixed bugs
   - For each bug fix, create a regression test that reproduces the original bug
   - Key commits to review: block comment stripping, parameter extraction, class method extraction, control flow keyword filtering, template line skipping, duplicate deduplication
   - Extract representative source snippets from EXAMPLE headers and create test cases

2. Add integration tests against real header files:
   - Parse each EXAMPLE header file directly and validate the AST
   - Check that expected classes, functions, macros, typedefs, enums are present
   - Verify parameter counts and types match known-good output

**Priority 2 — Output validation**

3. Markdown output comparison tests:
   - Generate markdown for known headers and compare against golden files
   - Store golden output in `test_data/golden/`
   - Use diff-based comparison to catch regressions

4. AST structure validation:
   - Verify that `HeaderDoc` has correct structure (no circular references)
   - Check that class methods are properly nested (not duplicated in global functions)
   - Validate template parameter extraction accuracy

**Priority 3 — Edge cases**

5. Add edge case test cases:
   - Empty header files, headers with only comments
   - Deeply nested templates (e.g., `Map<String, Vector<int>>`)
   - Multiple `#pragma aux` blocks, `#ifdef` / `#endif` guards
   - Windows CRLF line endings, inline assembly blocks
   - Forward declarations only, operator overloading, template specialisations
   - Operator\* style functions (pointer return types)

6. Parser robustness tests:
   - Malformed syntax (unclosed braces, missing semicolons)
   - Extremely long lines, mixed tabs/spaces, unusual whitespace

**Priority 4 — CI/CD integration**

7. Automated test runner:
   - Add `Makefile` or shell script to run all tests
   - Configure CI to run `python3 test_harness.py` on every commit
   - Add `--export` flag support for JSON results in CI logs

---

## Known Issues

- [ ] Handle any Watcom-specific constructs not covered by current parser
- [ ] Performance test with even larger projects (100+ headers)

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
cd <project_root>
python3 wapidoc/cli.py <EXAMPLE_project_root> -v
```

### Watcom-Specific Considerations

- `#pragma aux` blocks can span many lines with escaped quotes — already handled (skipped).
- Watcom inline assembly uses `"` escaped strings — the parser skips these correctly.
- Template syntax with angle brackets `<>` — brace counting should not confuse `<` and `>` with `{` and `}`.
