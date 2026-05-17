# wapidoc — Development TODO

Project: Python tool to scan Watcom C++ header files and produce markdown API documentation.
Host platform: Debian Linux / MacOS
Target: Watcom C/C++ for 32-bit protected mode DOS

---

## Plan

### Sprint 1: Fix output quality issues (current)

**Goal**: Improve accuracy of attribute parsing, multi-line parameter extraction, and namespace item collection.

| # | Task | Priority | Effort | Status |
|---|------|----------|--------|--------|
| 1.1 | Fix attribute type/name split for pointer types | High | Small | ✅ Done |
| 1.2 | Fix multi-line function parameter extraction | High | Medium | ✅ Done |
| 1.3 | Extract line comments (`//`) alongside Doxygen comments | Medium | Small | ✅ Done |
| 1.4 | Verify namespace items are correctly populated | Low | Small | Open |

**Details:**

1.1 **Attribute type/name split**
- Current: `uint8_t *data` → `name=*data`, `type=uint8_t`
- Expected: `name=data`, `type=uint8_t *`
- Root cause: `_is_attribute()` splits on whitespace and assumes uppercase-first tokens are types. Pointer `*` is attached to the name, not the type.
- Fix: In `_extract_class_body`, when splitting attribute parts, check if any part is `*` or `&` and move it to the type.

1.2 **Multi-line parameter extraction**
- Current: `Font::write(const char *txt, int x, int y, T col,\nT* screen, int screenWidth)` only extracts 4 params (first line only)
- Expected: 6 params including `T* screen` and `int screenWidth`
- Root cause: Method parsing extracts `after` from the matched line only, but the full parameter list spans multiple lines.
- Fix: After matching a method/func signature, if the line ends with `,\` or `,\n` (continuation), keep reading lines until `)` is found. Build the full param text before calling `_extract_params()`.

1.3 **Line comment extraction**
- Current: `_find_comment_backwards()` skips `//` lines immediately
- Expected: Extract `//` line comments as well as `/** */` block comments
- Fix: When walking backwards, if we hit a `//` line, capture the rest of the comment as the doc comment. Handle multiple consecutive `//` lines.

1.4 **Namespace items verification**
- Test: Ensure functions/classes inside namespaces populate `ns.items` not `header.functions`
- Already implemented in `_extract_namespace_body()`, but verify with real headers.

---

### Sprint 2: Expand test coverage

**Goal**: Add regression tests from real header patterns and golden file validation.

| # | Task | Priority | Effort | Status |
|---|------|----------|--------|--------|
| 2.1 | Add regression tests from git history patterns | High | Medium | Open |
| 2.2 | Add integration tests against real EXAMPLE headers | High | Medium | Open |
| 2.3 | Add golden file comparison tests | Medium | Large | Open |
| 2.4 | Add edge case tests (empty files, CRLF, nested templates) | Medium | Medium | Open |
| 2.5 | Add CI/CD integration with Makefile | Low | Small | Open |

---

### Sprint 3: Parser hardening

**Goal**: Improve robustness against malformed input and Watcom-specific edge cases.

| # | Task | Priority | Effort | Status |
|---|------|----------|--------|--------|
| 3.1 | Handle deeply nested templates (e.g. `Map<String, Vector<int>>`) | Medium | Medium | Open |
| 3.2 | Handle Watcom inline assembly blocks without crashing | Medium | Medium | Open |
| 3.3 | Handle forward declarations only (no body) | Low | Small | Open |
| 3.4 | Performance test with 100+ headers | Low | Small | Open |

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
