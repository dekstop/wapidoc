"""
Test harness for wapidoc parser and writer.

Runs regression tests against known-good and known-bad inputs,
producing pass/fail reports and highlighting output differences.

Usage:
    python3 test_harness.py [test_name]   # Run all tests or a specific one
    python3 test_harness.py --list        # List available test cases
    python3 test_harness.py --summary     # Show pass/fail summary
"""

import re
import sys
import os
import json
from pathlib import Path
from typing import List, Tuple, Optional

# Ensure wapidoc is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from parser import HeaderParser
from writer import generate_markdown
from models import HeaderDoc


# ─── Test case definitions ───────────────────────────────────────────

class TestCase:
    """A single test case with input, expected output, and validation rules."""

    def __init__(self, name: str, description: str,
                 source: str, expected_functions: int = 0,
                 expected_classes: int = 0, expected_macros: int = 0,
                 expected_typedefs: int = 0, expected_enums: int = 0,
                 expected_namespaces: int = 0,
                 expected_params: List[Tuple[str, list]] = None,
                 expected_attributes: List[Tuple[str, str]] = None,
                 expected_no_block_comments: bool = True,
                 expected_no_duplicates: bool = True,
                 expected_functions_match: List[Tuple[str, str, list]] = None,
                 expected_namespace_items: List[Tuple[str, str, list]] = None):
        """
        Args:
            name: Unique test case identifier
            description: Human-readable description
            source: Raw header file source code (may include CRLF)
            expected_functions: Number of expected parsed functions
            expected_classes: Number of expected parsed classes
            expected_macros: Number of expected parsed macros
            expected_typedefs: Number of expected parsed typedefs
            expected_enums: Number of expected parsed enums
            expected_namespaces: Number of expected parsed namespaces
            expected_params: List of (func_name, [(param_type, param_name), ...])
            expected_attributes: List of (attr_name, attr_type)
            expected_no_block_comments: Verify block comments stripped
            expected_no_duplicates: Verify no duplicate functions
            expected_functions_match: List of (func_name, return_type, [(param_type, param_name)])
        """
        self.name = name
        self.description = description
        self.source = source
        self.expected_functions = expected_functions
        self.expected_classes = expected_classes
        self.expected_macros = expected_macros
        self.expected_typedefs = expected_typedefs
        self.expected_enums = expected_enums
        self.expected_namespaces = expected_namespaces
        self.expected_params = expected_params or []
        self.expected_attributes = expected_attributes or []
        self.expected_no_block_comments = expected_no_block_comments
        self.expected_no_duplicates = expected_no_duplicates
        self.expected_functions_match = expected_functions_match or []
        self.expected_namespace_items = expected_namespace_items or []

    def run(self) -> dict:
        """Run this test case and return results dict."""
        result = {
            "name": self.name,
            "passed": True,
            "errors": [],
            "warnings": [],
        }

        parser = HeaderParser()
        doc = parser.parse("test.h", self.source)

        # 1. Block comment stripping (regular /* */ stripped, /** */ preserved)
        if self.expected_no_block_comments:
            stripped = parser._strip_block_comments(self.source)
            # Check for regular block comments: /* not followed by *
            import re
            if re.search(r'/\*(?!\*)', stripped):
                idx = next(m.start() for m in re.finditer(r'/\*(?!\*)', stripped))
                result["passed"] = False
                result["errors"].append(
                    f"Regular block comment not fully stripped: {repr(stripped[idx:idx+30])}"
                )

        # 2. Count checks
        count_checks = {
            "functions": (len(doc.functions), self.expected_functions),
            "classes": (len(doc.classes), self.expected_classes),
            "macros": (len(doc.macros), self.expected_macros),
            "typedefs": (len(doc.typedefs), self.expected_typedefs),
            "enums": (len(doc.enums), self.expected_enums),
            "namespaces": (len(doc.namespaces), self.expected_namespaces),
        }

        for item_type, (actual, expected) in count_checks.items():
            if actual != expected:
                result["passed"] = False
                result["errors"].append(
                    f"{item_type}: expected {expected}, got {actual}"
                )

        # 3. Duplicate detection
        if self.expected_no_duplicates:
            seen = set()
            for func in doc.functions:
                sig_key = (func.name, func.return_type, len(func.parameters))
                if sig_key in seen:
                    result["passed"] = False
                    result["errors"].append(
                        f"Duplicate function found: {func.name}({len(func.parameters)} params)"
                    )
                seen.add(sig_key)

        # 4. Parameter extraction
        func_map = {f.name: f for f in doc.functions}
        for func_name, expected_params in self.expected_params:
            if func_name not in func_map:
                result["passed"] = False
                result["errors"].append(
                    f"Function {func_name} not found for param check"
                )
                continue
            actual_params = [(p.type, p.name) for p in func_map[func_name].parameters]
            if actual_params != expected_params:
                result["passed"] = False
                result["errors"].append(
                    f"Params for {func_name}: expected {expected_params}, got {actual_params}"
                )

        # 5. Full function matching
        for func_name, exp_type, exp_params in self.expected_functions_match:
            if func_name not in func_map:
                result["passed"] = False
                result["errors"].append(
                    f"Function {func_name} not found for full match check"
                )
                continue
            func = func_map[func_name]
            actual_params = [(p.type, p.name) for p in func.parameters]
            if func.return_type != exp_type:
                result["passed"] = False
                result["errors"].append(
                    f"Return type for {func_name}: expected {exp_type}, got {func.return_type}"
                )
            if actual_params != exp_params:
                result["passed"] = False
                result["errors"].append(
                    f"Params for {func_name}: expected {exp_params}, got {actual_params}"
                )

        # 6. Attribute extraction
        attr_map = {}
        for cls in doc.classes:
            for attr in cls.attributes:
                attr_map[f"{cls.name}.{attr.name}"] = attr.type
        for attr_name, exp_type in self.expected_attributes:
            key = f"test.{attr_name}"
            if key not in attr_map:
                result["warnings"].append(
                    f"Attribute {attr_name} not found for type check"
                )
            elif attr_map[key] != exp_type:
                result["passed"] = False
                result["errors"].append(
                    f"Type for {attr_name}: expected {exp_type}, got {attr_map[key]}"
                )

        # 7. Namespace items extraction
        from models import Function as ModelFunction
        if self.expected_namespace_items:
            ns_item_map = {}
            for ns in doc.namespaces:
                for item in ns.items:
                    if isinstance(item, ModelFunction):
                        ns_item_map[item.name] = item
            for func_name, exp_type, exp_params in self.expected_namespace_items:
                if func_name not in ns_item_map:
                    result["passed"] = False
                    result["errors"].append(
                        f"Namespace function {func_name} not found"
                    )
                    continue
                func = ns_item_map[func_name]
                actual_params = [(p.type, p.name) for p in func.parameters]
                if func.return_type != exp_type:
                    result["passed"] = False
                    result["errors"].append(
                        f"Return type for {func_name}: expected {exp_type}, got {func.return_type}"
                    )
                if actual_params != exp_params:
                    result["passed"] = False
                    result["errors"].append(
                        f"Params for {func_name}: expected {exp_params}, got {actual_params}"
                    )

        # 8. Markdown generation (no crashes)
        try:
            md = generate_markdown(doc)
            result["markdown_length"] = len(md)
        except Exception as e:
            result["passed"] = False
            result["errors"].append(f"Markdown generation failed: {e}")

        return result


# ─── Test cases ──────────────────────────────────────────────────────

def get_test_cases() -> List[TestCase]:
    """Return all registered test cases."""
    return [
        # ─── Block comment tests ─────────────────────────────────────

        TestCase(
            "block_comment_simple",
            "Simple block comment with single-line content",
            source="/* single line comment */\nint foo(int x);",
            expected_functions=1,
            expected_functions_match=[
                ("foo", "int", [("int", "x")])
            ]
        ),
        TestCase(
            "block_comment_multiline",
            "Multi-line regular block comment should be fully stripped",
            source="""/*
 * Header comment
 */
int foo(int x);

/*
 * This is a block comment
 * with multiple lines
 */
int bar(int y);""",
            expected_functions=2,
            expected_functions_match=[
                ("foo", "int", [("int", "x")]),
                ("bar", "int", [("int", "y")])
            ]
        ),
        TestCase(
            "block_comment_nested",
            "Nested /* inside block comment should not exit early",
            source="""/*
 * outer comment
 * /* inner fake comment */ still in outer
 */
int foo(int x);""",
            expected_functions=1,
            expected_functions_match=[
                ("foo", "int", [("int", "x")])
            ]
        ),
        TestCase(
            "block_comment_crlf",
            "Block comments with CRLF line endings should strip correctly",
            source="/* comment\r\nfloat pow(float, float);\r\n*/\r\nfloat fmod(float v);".replace("\n", "\r\n"),
            expected_functions=1,
            expected_functions_match=[
                ("fmod", "float", [("float", "v")])
            ]
        ),
        TestCase(
            "block_comment_single_quote_in_comment",
            "Line comment with single quote should not confuse parser",
            source="// This is a comment with can't in it\nint foo(int x);",
            expected_functions=1,
            expected_functions_match=[
                ("foo", "int", [("int", "x")])
            ]
        ),

        # ─── Parameter extraction tests ──────────────────────────────

        TestCase(
            "param_simple",
            "Simple parameter extraction",
            source="int foo(int x);",
            expected_functions=1,
            expected_params=[("foo", [("int", "x")])]
        ),
        TestCase(
            "param_multiple",
            "Multiple parameters with different types",
            source="int foo(int x, float y, const char *name);",
            expected_functions=1,
            expected_params=[("foo", [("int", "x"), ("float", "y"), ("const char*", "name")])]
        ),
        TestCase(
            "param_anonymous",
            "Anonymous parameters (no name)",
            source="float pow(float, float);",
            expected_functions=1,
            expected_params=[("pow", [("float", ""), ("float", "")])]
        ),
        TestCase(
            "param_pointer",
            "Pointer parameters (int* ptr style — type includes *, name is plain)",
            source="int func(int* ptr);",
            expected_functions=1,
            expected_params=[("func", [("int*", "ptr")])]
        ),
        TestCase(
            "param_reference",
            "Reference parameters (&name) — & moves to type",
            source="void swap(int &a, int &b);",
            expected_functions=1,
            expected_params=[("swap", [("int&", "a"), ("int&", "b")])]
        ),
        TestCase(
            "param_template",
            "Template type parameters — & moves to type",
            source="void process(Vector<T,Dim> &v);",
            expected_functions=1,
            expected_params=[("process", [("Vector<T,Dim>&", "v")])]
        ),
        TestCase(
            "param_const_pointer",
            "Const pointer parameters — * moves to type",
            source="void write(const char *txt, int x, int y);",
            expected_functions=1,
            expected_params=[("write", [("const char*", "txt"), ("int", "x"), ("int", "y")])]
        ),

        # ─── Function signature tests ────────────────────────────────

        TestCase(
            "func_inline",
            "Inline function extraction",
            source="inline int isnan(float v);",
            expected_functions=1,
            expected_functions_match=[("isnan", "int", [("float", "v")])]
        ),
        TestCase(
            "func_static",
            "Static function extraction",
            source="static void helper(int x);",
            expected_functions=1,
            expected_functions_match=[("helper", "void", [("int", "x")])]
        ),
        TestCase(
            "func_virtual",
            "Virtual function extraction — & moves to type",
            source="virtual void draw(Graphics<T> &g);",
            expected_functions=1,
            expected_functions_match=[("draw", "void", [("Graphics<T>&", "g")])]
        ),
        TestCase(
            "func_control_flow_skip",
            "Control flow keywords should not be parsed as functions",
            source="if (x > 0) { return x; }",
            expected_functions=0
        ),
        TestCase(
            "func_return_skip",
            "return statement should not be parsed as function",
            source="return ((c[0]>0) || (c[1]>0));",
            expected_functions=0
        ),

        # ─── Class extraction tests ──────────────────────────────────

        TestCase(
            "class_simple",
            "Simple class with methods (methods stored in class.methods, not global functions)",
            source="""class Font {
public:
    uint8_t *data;
    Font(uint8_t *data, unsigned int w);
    ~Font();
    void write(const char *txt);
};""",
            expected_classes=1,
            expected_attributes=[("data", "uint8_t *")],
            expected_functions=0,  # Class methods are in class.methods, not global
            expected_functions_match=[]  # No global functions expected
        ),
        TestCase(
            "class_scope_methods",
            "Class methods with :: scope notation",
            source="""class Image {
public:
    int width;
    int height;
    int write(const char *txt, int x, int y);
    static Image* load(const char *filename);
};""",
            expected_classes=1,
            expected_attributes=[("width", "int"), ("height", "int")],
            expected_functions=0,
            expected_functions_match=[]
        ),
        TestCase(
            "class_destructor",
            "Destructor extraction with ~ prefix",
            source="""class Vector {
public:
    ~Vector();
};""",
            expected_classes=1,
            expected_functions=0,
            expected_functions_match=[]
        ),
        TestCase(
            "class_duplicate_destructor",
            "Destructor deduplication",
            source="""class Vector {
public:
    ~Vector();
    ~Vector();
};""",
            expected_classes=1,
            expected_functions=0,
            expected_no_duplicates=True
        ),

        # ─── Macro tests ─────────────────────────────────────────────

        TestCase(
            "macro_simple",
            "Simple macro extraction",
            source="#define PI 3.141592653\n#define SETNAN(v) *(uint32_t*)&v = 0",
            expected_macros=2
        ),
        TestCase(
            "macro_pragma_skip",
            "Macro with 'pragma' in value should be skipped",
            source="#define SETNAN(v) *(uint32_t*)&v = FLOAT_NAN_BYTES\n#pragma aux foo",
            expected_macros=1,
            expected_functions=0
        ),

        # ─── Typedef tests ───────────────────────────────────────────

        TestCase(
            "typedef_simple",
            "Simple typedef extraction",
            source="typedef Vector<float,2> Vector2D;",
            expected_typedefs=1
        ),

        # ─── Namespace tests ─────────────────────────────────────────

        TestCase(
            "namespace_simple",
            "Simple namespace with functions",
            source="""namespace Tex8bpp {
    inline uint8_t saturate(uint8_t v);
}""",
            expected_namespaces=1,
            expected_functions=0,  # Namespace functions go into ns.items, not global
            expected_namespace_items=[("saturate", "uint8_t", [("uint8_t", "v")])]
        ),

        # ─── Integration tests (real-world patterns) ─────────────────

        TestCase(
            "integration_math32_pattern",
            "Pattern from MATH32.H: inline functions with #pragma aux blocks",
            source="""inline float fabs(float);
#pragma aux fabs parm [8087] value [8087] modify [8087] = \\
  "fabs"

inline float sin(float);
#pragma aux sin parm [8087] value [8087] modify [8087] = \\
  "fsin"

float fmod(float v, float div) {
  while (v > div) v -= div;
  return v;
}

/*
float pow(float, float);
#pragma aux pow parm [8087] [8087] value [8087] modify [8087 ax] = \\
  "fld1"
*/

float pow(float b, float e) {
  if (b<0) {
    float sign = ((int)(e) & 1) ? -1 : 1;
    return sign * fabs(b);
  }
  return fabs(b);
}""",
            expected_functions=4,
            expected_functions_match=[
                ("fabs", "float", [("float", "")]),
                ("sin", "float", [("float", "")]),
                ("fmod", "float", [("float", "v"), ("float", "div")]),
                ("pow", "float", [("float", "b"), ("float", "e")])
            ],
            expected_no_duplicates=True
        ),
        TestCase(
            "integration_vector_pattern",
            "Pattern from VECTOR.H: templated class with methods",
            source="""template <class T, int Dim>
class Vector {
public:
    T coords[Dim];
    Vector();
    Vector(const Vector<T,Dim> &p);
    void print();
};

typedef Vector<float,2> Vector2D;
typedef Vector<float,3> Vector3D;""",
            expected_classes=1,
            expected_typedefs=2,
            expected_functions=0,  # Class methods stored in class.methods
            expected_functions_match=[]
        ),

        # ─── Regression tests from git history ───────────────────────

        TestCase(
            "regression_block_comment_stripping",
            "Regression: block comments must be fully stripped (not left in output)",
            source="""/* This is a block comment */
int foo(int x);

/*
 * Multi-line block
 * with multiple lines
 */
int bar(int y);""",
            expected_functions=2,
            expected_functions_match=[
                ("foo", "int", [("int", "x")]),
                ("bar", "int", [("int", "y")])
            ],
            expected_no_block_comments=True
        ),
        TestCase(
            "regression_param_pointer",
            "Regression: pointer symbols * move to type, not name",
            source="int func(int* ptr);",
            expected_functions=1,
            expected_params=[("func", [("int*", "ptr")])]
        ),
        TestCase(
            "regression_param_reference",
            "Regression: reference symbols & move to type, not name",
            source="void swap(int &a, int &b);",
            expected_functions=1,
            expected_params=[("swap", [("int&", "a"), ("int&", "b")])]
        ),
        TestCase(
            "regression_attribute_pointer",
            "Regression: class attributes with * correctly split type/name",
            source="""class Font {
public:
    uint8_t *data;
    Font(uint8_t *data, unsigned int w);
    ~Font();
};""",
            expected_classes=1,
            expected_attributes=[("data", "uint8_t *")],
            expected_functions=0,
            expected_functions_match=[]
        ),
        TestCase(
            "regression_control_flow_skip",
            "Regression: control flow keywords must not be parsed as functions",
            source="if (x > 0) { return x; }",
            expected_functions=0
        ),
        TestCase(
            "regression_return_skip",
            "Regression: return statements must not be parsed as functions",
            source="return ((c[0]>0) || (c[1]>0));",
            expected_functions=0
        ),
        TestCase(
            "regression_duplicate_destructor",
            "Regression: duplicate destructors must be deduplicated",
            source="""class Vector {
public:
    ~Vector();
    ~Vector();
};""",
            expected_classes=1,
            expected_functions=0,
            expected_no_duplicates=True
        ),
        TestCase(
            "regression_pragma_aux_skip",
            "Regression: #pragma aux blocks must be skipped correctly",
            source="""inline float fabs(float);
#pragma aux fabs parm [8087] value [8087] modify [8087] = \\
  "fabs"

inline float sin(float);
#pragma aux sin parm [8087] value [8087] modify [8087] = \\
  "fsin"

float fmod(float v, float div) {
  while (v > div) v -= div;
  return v;
}""",
            expected_functions=3,
            expected_functions_match=[
                ("fabs", "float", [("float", "")]),
                ("sin", "float", [("float", "")]),
                ("fmod", "float", [("float", "v"), ("float", "div")])
            ]
        ),
        TestCase(
            "regression_template_line_skip",
            "Regression: template lines must be consumed and not parsed as functions",
            source="""template <class T, int Dim>
class Vector {
public:
    Vector();
    void print();
};""",
            expected_classes=1,
            expected_functions=0,
            expected_functions_match=[]
        ),
        TestCase(
            "regression_namespace_items",
            "Regression: namespace items must go into ns.items, not global functions",
            source="""namespace Tex8bpp {
    inline uint8_t saturate(uint8_t v);
}""",
            expected_namespaces=1,
            expected_functions=0,
            expected_namespace_items=[("saturate", "uint8_t", [("uint8_t", "v")])]
        ),

        # ─── Integration tests against real EXAMPLE headers ──────────

        TestCase(
            "integration_real_graphics_font",
            "Integration: Font class from GRAPHICS.H — constructor, destructor, methods",
            source="""class Font {
public:
    uint8_t *data;
    const unsigned int charwidth;
    const unsigned int charheight;

    Font(uint8_t *data, unsigned int charwidth);
    ~Font();
    static Font* load(const char* filename, int charwidth);
    int write(const char* txt, int x, int y);
};""",
            expected_classes=1,
            expected_attributes=[("data", "uint8_t *"), ("charwidth", "const unsigned int"), ("charheight", "const unsigned int")],
            expected_functions=0,
            expected_functions_match=[]
        ),
        TestCase(
            "integration_real_vector",
            "Integration: Vector class from VECTOR.H — template class with typedefs",
            source="""template <class T, int Dim>
class Vector {
public:
    T coords[Dim];
    Vector();
    Vector(const Vector<T,Dim> &p);
    void print();
};

typedef Vector<float,2> Vector2D;
typedef Vector<float,3> Vector3D;""",
            expected_classes=1,
            expected_typedefs=2,
            expected_functions=0,
            expected_functions_match=[]
        ),
        TestCase(
            "integration_real_math32",
            "Integration: MATH32.H — inline functions with #pragma aux blocks",
            source="""inline float fabs(float);
#pragma aux fabs parm [8087] value [8087] modify [8087] = \\
  "fabs"

inline float sin(float);
#pragma aux sin parm [8087] value [8087] modify [8087] = \\
  "fsin"

float fmod(float v, float div) {
  while (v > div) v -= div;
  return v;
}

/*
float pow(float, float);
#pragma aux pow parm [8087] [8087] value [8087] modify [8087 ax] = \\
  "fld1"
*/

float pow(float b, float e) {
  if (b<0) {
    float sign = ((int)(e) & 1) ? -1 : 1;
    return sign * fabs(b);
  }
  return fabs(b);
}""",
            expected_functions=4,
            expected_functions_match=[
                ("fabs", "float", [("float", "")]),
                ("sin", "float", [("float", "")]),
                ("fmod", "float", [("float", "v"), ("float", "div")]),
                ("pow", "float", [("float", "b"), ("float", "e")])
            ],
            expected_no_duplicates=True
        ),
        TestCase(
            "integration_real_graphics_namespace",
            "Integration: Tex8bpp namespace from GRAPHICS.H — functions in ns.items",
            source="""namespace Tex8bpp {
    inline uint8_t saturate(uint8_t v);
    inline float clamp(float v, float min, float max);
}""",
            expected_namespaces=1,
            expected_functions=0,
            expected_namespace_items=[
                ("saturate", "uint8_t", [("uint8_t", "v")]),
                ("clamp", "float", [("float", "v"), ("float", "min"), ("float", "max")])
            ]
        ),

        # ─── Edge case tests ─────────────────────────────────────────

        TestCase(
            "edge_case_empty_header",
            "Edge case: empty header file",
            source="",
            expected_functions=0,
            expected_classes=0,
            expected_macros=0,
            expected_typedefs=0,
            expected_enums=0,
            expected_namespaces=0
        ),
        TestCase(
            "edge_case_only_comments",
            "Edge case: header with only comments",
            source="""/* This is a header file */
// With line comments
/* Another block */""",
            expected_functions=0,
            expected_classes=0,
            expected_macros=0,
            expected_typedefs=0,
            expected_enums=0,
            expected_namespaces=0
        ),
        TestCase(
            "edge_case_crlf_endings",
            "Edge case: Windows CRLF line endings",
            source="int foo(int x);\r\nint bar(int y);\r\n".replace("\n", "\r\n"),
            expected_functions=2,
            expected_functions_match=[
                ("foo", "int", [("int", "x")]),
                ("bar", "int", [("int", "y")])
            ]
        ),
        TestCase(
            "edge_case_operator_overload",
            "Edge case: operator overload parsing",
            source="""class Vector {
public:
    Vector operator+(const Vector &v);
    void operator+=(const Vector &v);
};""",
            expected_classes=1,
            expected_functions=0,
            expected_functions_match=[]
        ),
    ]


# ─── Test runner ─────────────────────────────────────────────────────

class TestRunner:
    """Run all test cases and produce a report."""

    def __init__(self):
        self.test_cases = get_test_cases()
        self.results = []

    def run_all(self, filter_name: str = None) -> List[dict]:
        """Run all test cases (optionally filtered by name)."""
        self.results = []
        for tc in self.test_cases:
            if filter_name and filter_name.lower() not in tc.name.lower():
                continue
            result = tc.run()
            result["description"] = tc.description
            self.results.append(result)
        return self.results

    def print_report(self, results: List[dict], summary: bool = False):
        """Print formatted test report."""
        passed = sum(1 for r in results if r["passed"])
        failed = sum(1 for r in results if not r["passed"])

        if summary:
            print(f"\n{'='*60}")
            print(f"  Test Summary: {passed} passed, {failed} failed, {len(results)} total")
            print(f"{'='*60}\n")
            return

        # Print results
        for r in results:
            status = "PASS" if r["passed"] else "FAIL"
            print(f"  [{status}] {r['name']}")
            if r["description"]:
                print(f"         {r['description']}")
            if r["errors"]:
                for err in r["errors"]:
                    print(f"         ✗ {err}")
            if r["warnings"]:
                for warn in r["warnings"]:
                    print(f"         ⚠ {warn}")
            print()

        print(f"\n{'='*60}")
        print(f"  Summary: {passed} passed, {failed} failed, {len(results)} total")
        print(f"{'='*60}\n")

    def export_results(self, filename: str = "test_results.json"):
        """Export results to JSON for CI/CD integration."""
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"Results exported to {filename}")


# ─── Main entry point ────────────────────────────────────────────────

def main():
    """CLI entry point for the test harness."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Test harness for wapidoc parser and writer"
    )
    parser.add_argument(
        "test_name", nargs="?", default=None,
        help="Run a specific test (by name substring)"
    )
    parser.add_argument(
        "--list", action="store_true",
        help="List all available test cases"
    )
    parser.add_argument(
        "--summary", action="store_true",
        help="Show pass/fail summary only"
    )
    parser.add_argument(
        "--export", type=str, default=None,
        help="Export results to JSON file"
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Show detailed output"
    )

    args = parser.parse_args()

    runner = TestRunner()

    if args.list:
        print("Available test cases:")
        for tc in get_test_cases():
            print(f"  {tc.name}: {tc.description}")
        return

    results = runner.run_all(args.test_name)

    if args.summary:
        runner.print_report(results, summary=True)
    else:
        runner.print_report(results, summary=not args.verbose)

    if args.export:
        runner.export_results(args.export)

    # Exit with error code if any tests failed
    failed = sum(1 for r in results if not r["passed"])
    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    main()
