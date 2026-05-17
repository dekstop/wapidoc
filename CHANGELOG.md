# Changelog — wapidoc

All notable changes to this project are documented here.

---

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
