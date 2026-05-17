# Watcom API Doc Generator — TODO

Project: Python tool to scan Watcom C++ header files and produce markdown API documentation.
Host platform: Debian Linux / MacOS
Target: Watcom C/C++ for 32-bit protected mode DOS

---

## In Progress

### Parser limitations (parser.py)

Remaining issues that affect output quality:

1. **Complex template types truncated** — Parameters like `Graphics<T>` are extracted as just `Graphics`. The simple regex-based parameter extraction doesn't handle complex template types with nested angle brackets.
2. **Function body tracking** — The main loop doesn't track function bodies, so lines inside free function bodies may be incorrectly matched by regex patterns.
3. **Line comments not extracted** — `//` line comments preceding declarations are skipped by `_find_comment_backwards()`. Only Doxygen-style `/** */` comments are extracted.

---

## Future Work

### Expand test coverage

The test harness skeleton (`test_harness.py`) is in place with 27 passing tests. The following enhancements are planned:

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
cd /home/mongo.guest/Users/mongo/Dropbox/Code/2026/Pi-agent-env/Sandbox
python3 wapidoc/cli.py /home/mongo.guest/Users/mongo/Dropbox/Code/2026/Pi-agent-env/Sandbox/EXAMPLE -v
```

### Watcom-Specific Considerations

- `#pragma aux` blocks can span many lines with escaped quotes — already handled (skipped).
- Watcom inline assembly uses `"` escaped strings — the parser skips these correctly.
- Template syntax with angle brackets `<>` — brace counting should not confuse `<` and `>` with `{` and `}`.
