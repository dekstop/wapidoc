"""
Markdown writer for API documentation.

Generates structured markdown from HeaderDoc AST.
"""

from models import (
    HeaderDoc, Class, Function, Attribute,
    Namespace, Enum, Typedef, Macro
)


def generate_markdown(header_doc: HeaderDoc) -> str:
    """Generate complete markdown from a HeaderDoc AST."""
    lines = []

    # Title
    lines.append(f"# API Documentation: {header_doc.filename}")
    lines.append("")

    # Header comment
    if header_doc.header_comment:
        lines.append("## Header Overview")
        lines.append("")
        lines.append(header_doc.header_comment)
        lines.append("")

    # Includes
    if header_doc.includes:
        lines.append("## Includes")
        lines.append("")
        for inc in header_doc.includes:
            lines.append(f"- `{inc}`")
        lines.append("")

    # Classes
    if header_doc.classes:
        lines.append("## Classes and Structs")
        lines.append("")
        for cls in header_doc.classes:
            lines.extend(_format_class(cls))
            lines.append("")

    # Namespaces
    if header_doc.namespaces:
        lines.append("## Namespaces")
        lines.append("")
        for ns in header_doc.namespaces:
            lines.extend(_format_namespace(ns))
            lines.append("")

    # Free functions
    if header_doc.functions:
        lines.append("## Functions")
        lines.append("")
        for func in header_doc.functions:
            lines.extend(_format_function(func))
            lines.append("")

    # Enums
    if header_doc.enums:
        lines.append("## Enums")
        lines.append("")
        for enum in header_doc.enums:
            lines.extend(_format_enum(enum))
            lines.append("")

    # Typedefs
    if header_doc.typedefs:
        lines.append("## Typedefs")
        lines.append("")
        for td in header_doc.typedefs:
            lines.extend(_format_typedef(td))
            lines.append("")

    # Macros
    if header_doc.macros:
        lines.append("## Macros")
        lines.append("")
        for macro in header_doc.macros:
            lines.extend(_format_macro(macro))
            lines.append("")

    return '\n'.join(lines)


def _format_class(cls: Class) -> list:
    """Format a class/struct for markdown."""
    lines = []

    # Title
    kind = "struct" if cls.is_struct else "class"
    template_str = _format_template_params(cls.template_params)
    lines.append(f"### {kind} {cls.name}{template_str}")
    lines.append("")

    # Comment
    if cls.comment:
        lines.append(cls.comment)
        lines.append("")

    # Base class
    if cls.base_class:
        lines.append(f"**Extends:** `{cls.base_class}`")
        lines.append("")

    # Attributes
    public_attrs = [a for a in cls.attributes if a.access == "public"]
    if public_attrs:
        lines.append("**Attributes:**")
        lines.append("")
        for attr in public_attrs:
            comment_str = f" — {attr.comment}" if attr.comment else ""
            lines.append(f"- `{attr.type} {attr.name}`{comment_str}")
        lines.append("")

    # Nested classes
    if cls.nested_classes:
        lines.append("**Nested Types:**")
        lines.append("")
        for nested in cls.nested_classes:
            lines.append(f"- `{nested.name}`")
        lines.append("")

    # Methods
    public_methods = [m for m in cls.methods if m.access == "public"]
    if public_methods:
        lines.append("**Methods:**")
        lines.append("")
        for method in public_methods:
            lines.extend(_format_function(method))
            lines.append("")

    return lines


def _format_function(func: Function) -> list:
    """Format a function/method for markdown."""
    lines = []

    # Signature
    template_str = _format_template_params(func.template_params)
    params_str = _format_params(func.parameters)
    qualifiers = []
    if func.is_inline:
        qualifiers.append("inline")
    if func.is_static:
        qualifiers.append("static")
    if func.is_const:
        qualifiers.append("const")
    if func.is_virtual:
        qualifiers.append("virtual")
    qual_str = " ".join(qualifiers)
    if qual_str:
        qual_str = f"{qual_str} "

    lines.append(f"- `{qual_str}{func.return_type} {func.name}{template_str}({params_str})`")

    # Comment
    if func.comment:
        lines.append(f"  — {func.comment}")

    return lines


def _format_namespace(ns: Namespace) -> list:
    """Format a namespace for markdown."""
    lines = []
    lines.append(f"### namespace {ns.name}")
    lines.append("")

    if ns.comment:
        lines.append(ns.comment)
        lines.append("")

    # Process contained items
    classes = [i for i in ns.items if isinstance(i, Class)]
    functions = [i for i in ns.items if isinstance(i, Function)]
    enums = [i for i in ns.items if isinstance(i, Enum)]
    typedefs = [i for i in ns.items if isinstance(i, Typedef)]
    macros = [i for i in ns.items if isinstance(i, Macro)]

    if classes:
        lines.append("**Types:**")
        lines.append("")
        for cls in classes:
            lines.append(f"- `{cls.name}`")
        lines.append("")

    if functions:
        lines.append("**Functions:**")
        lines.append("")
        for func in functions:
            lines.extend(_format_function(func))
            lines.append("")

    if enums:
        lines.append("**Enums:**")
        lines.append("")
        for enum in enums:
            lines.extend(_format_enum(enum))
            lines.append("")

    if typedefs:
        lines.append("**Typedefs:**")
        lines.append("")
        for td in typedefs:
            lines.extend(_format_typedef(td))
            lines.append("")

    if macros:
        lines.append("**Macros:**")
        lines.append("")
        for macro in macros:
            lines.extend(_format_macro(macro))
            lines.append("")

    return lines


def _format_enum(enum: Enum) -> list:
    """Format an enum for markdown."""
    lines = []
    lines.append(f"- `{enum.name}`")
    if enum.comment:
        lines.append(f"  — {enum.comment}")
    return lines


def _format_typedef(td: Typedef) -> list:
    """Format a typedef for markdown."""
    lines = []
    lines.append(f"- `{td.name}` → `{td.type}`")
    if td.comment:
        lines.append(f"  — {td.comment}")
    return lines


def _format_macro(macro: Macro) -> list:
    """Format a macro for markdown."""
    lines = []
    lines.append(f"- `#define {macro.name} {macro.value}`")
    if macro.comment:
        lines.append(f"  — {macro.comment}")
    return lines


# ─── Helper formatting ────────────────────────────────────────────

def _format_template_params(params: list) -> str:
    """Format template parameters."""
    if not params:
        return ""
    return f"<{', '.join(params)}>"


def _format_params(params: list) -> str:
    """Format function parameters."""
    parts = []
    for p in params:
        if p.default:
            parts.append(f"{p.type} {p.name}={p.default}")
        else:
            parts.append(f"{p.type} {p.name}")
    return ", ".join(parts)
