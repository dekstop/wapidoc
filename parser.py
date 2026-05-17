"""
Watcom C++ header file parser.

Uses a simple line-by-line approach to extract API declarations
from Watcom C++ headers. Standard library only.
"""

import re
from typing import List, Optional

try:
    from .models import (
        HeaderDoc, Class, Function, Attribute, Parameter,
        Namespace, Enum, EnumMember, Typedef, Macro
    )
except ImportError:
    from models import (
        HeaderDoc, Class, Function, Attribute, Parameter,
        Namespace, Enum, EnumMember, Typedef, Macro
    )


# ─── Regex patterns ───────────────────────────────────────────────

_CLASS_RE = re.compile(r'^\s*(class|struct)\s+(\w+)')
_NAMESPACE_RE = re.compile(r'^\s*namespace\s+(\w+)')
_ENUM_RE = re.compile(r'^\s*enum\s+(class\s+)?(\w+)')
_TYPEDEF_RE = re.compile(r'^\s*typedef\s+')
_FUNC_SIG_RE = re.compile(r'^\s*(?:inline\s+|static\s+|virtual\s+)?(\w+(?:\s*\*)*)\s+(\w+(?:\s*::\s*\w+)?)\s*\(')
# Keywords that look like types but aren't
_SKIP_KEYWORDS = {'return', 'if', 'else', 'while', 'for', 'switch', 'case',
                  'do', 'goto', 'break', 'continue', 'new', 'delete', 'throw',
                  'sizeof', 'alignof', 'decltype', 'typeid', 'static_cast',
                  'dynamic_cast', 'const_cast', 'reinterpret_cast', 'nullptr',
                  'true', 'false', 'this'}
_SIMPLE_DEFINE_RE = re.compile(r'^\s*#\s*define\s+(\w+)(?:\s*\([^)]*\))?\s+(.*)')
_INCLUDE_RE = re.compile(r'^\s*#\s*include\s*[<"](.+?)[">]')
_PRAGMA_RE = re.compile(r'^\s*#\s*pragma\s+(\w+)')
# Parameter regex: captures (type) (name) (default)
# Type can include complex templates like 'Graphics<T>'
# Type group is greedy (no * or &) so it captures everything up to the name
# Name group includes * and & for pointer/reference parameters
_PARAM_RE = re.compile(r'^((?:[\w<>,\[\]\s*&]+)\s+)([\w*&]+)(?:\s*=\s*([^\s,]+))?')
# For anonymous parameters (just type, no name)
_PARAM_RE_ANON = re.compile(r'^([\w<>,\[\]\s*&]+)$')

# Patterns for class method extraction
_METHOD_SCOPE_RE = re.compile(r'^\s*(?:inline\s+|static\s+|virtual\s+)?(\w+(?:\s*\*)*)\s+(\w+::\w+)\s*\(')
_DTOR_RE = re.compile(r'^\s*~(\w+)\s*\(')
_TEMPLATE_RE = re.compile(r'^\s*template\s*<')


# ─── Block comment stripping ──────────────────────────────────


class HeaderParser:
    """Parse a Watcom C++ header file and produce a HeaderDoc AST."""

    def __init__(self):
        self.header = HeaderDoc(filename="")

    @staticmethod
    def _strip_block_comments(source: str) -> str:
        """Remove /* ... */ block comments but preserve /** ... */ Doxygen comments.
        Preserves line count so line indices remain valid.
        Handles both LF and CRLF line endings.
        Also strips // line comments to avoid quote confusion."""
        result = []
        i = 0
        in_block = False
        while i < len(source):
            if in_block:
                if source[i:i+2] == '*/':
                    in_block = False
                    i += 2
                    result.append(' ' * 2)
                elif source[i] == '\n':
                    result.append('\n')
                    i += 1
                elif source[i] == '\r':
                    # CRLF: keep the \r\n but strip the \r
                    result.append(' ')
                    i += 1
                else:
                    result.append(' ')
                    i += 1
            else:
                if source[i:i+3] == '/**':
                    # Doxygen comment start — preserve it
                    result.append('/**')
                    i += 3
                elif source[i:i+2] == '/*':
                    # Regular block comment — strip it
                    in_block = True
                    i += 2
                    result.append(' ' * 2)
                elif source[i:i+2] == '//':
                    # Line comment: skip to end of line
                    i += 2
                    while i < len(source) and source[i] != '\n' and source[i] != '\r':
                        i += 1
                    # Preserve the newline
                    if i < len(source):
                        if source[i] == '\r':
                            result.append(' ')
                            i += 1
                            if i < len(source) and source[i] == '\n':
                                result.append('\n')
                                i += 1
                        else:
                            result.append(source[i])
                            i += 1
                elif source[i] == '"':
                    quote = source[i]
                    result.append(quote)
                    i += 1
                    while i < len(source):
                        if source[i] == '\\' and i + 1 < len(source):
                            result.append(source[i:i+2])
                            i += 2
                        elif source[i] == quote:
                            result.append(source[i])
                            i += 1
                            break
                        else:
                            result.append(source[i])
                            i += 1
                else:
                    result.append(source[i])
                    i += 1
        return ''.join(result)

    def parse(self, filename: str, source: str) -> HeaderDoc:
        """Parse a header file and return the HeaderDoc AST."""
        self.header = HeaderDoc(filename=filename)
        # Strip block comments (/* ... */) before parsing
        source = self._strip_block_comments(source)
        lines = source.split('\n')

        # Extract header-level comment
        self._extract_header_comment(lines)

        # Extract #includes
        self._extract_includes(lines)

        # Track seen function signatures to avoid duplicates
        seen_functions = set()

        # Process line by line
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            # Skip empty lines, comments, preprocessor guards
            if not stripped or stripped.startswith('//') or stripped.startswith('/*'):
                i += 1
                continue
            if stripped.startswith('#if') or stripped.startswith('#endif'):
                i += 1
                continue

            # Skip #pragma aux blocks
            if self._is_pragma_aux_start(stripped):
                i = self._skip_pragma_aux(lines, i)
                continue

            # Skip template lines (extract params for next construct)
            if _TEMPLATE_RE.match(stripped):
                i = self._skip_template(lines, i)
                continue

            # Skip lines with control flow keywords (return, if, else, etc.)
            skip_words = {'return', 'if', 'else', 'while', 'for', 'switch',
                         'case', 'do', 'goto', 'break', 'continue'}
            first_word = stripped.split()[0] if stripped.split() else ""
            if first_word in skip_words:
                i += 1
                continue

            # Try top-level constructs (use stripped for matching)
            next_idx = self._try_parse_class(lines, i, stripped)
            if next_idx is not None:
                i = next_idx
                continue
            next_idx = self._try_parse_namespace(lines, i, stripped)
            if next_idx is not None:
                i = next_idx
                continue
            elif self._try_parse_enum(lines, i, stripped):
                i += 1
            elif self._try_parse_typedef(lines, i, stripped):
                i += 1
            elif self._try_parse_function(lines, i, stripped, seen_functions):
                i += 1
            elif self._try_parse_macro(lines, i, stripped):
                i += 1
            else:
                i += 1

        return self.header

    def _extract_header_comment(self, lines: List[str]):
        """Extract the header-level Doxygen comment."""
        for i, line in enumerate(lines):
            if line.strip().startswith('/**'):
                comment_lines = [line.strip()[3:].strip()]
                j = i + 1
                while j < len(lines):
                    s = lines[j].strip()
                    if s.startswith('/**'):
                        comment_lines.append(s[3:].strip())
                    elif s == '*/':
                        self.header.header_comment = ' '.join(comment_lines)
                        return
                    elif s.startswith('*'):
                        comment_lines.append(s[1:].strip())
                    elif s.startswith('//'):
                        comment_lines.append(s[2:].strip())
                    j += 1

    def _extract_includes(self, lines: List[str]):
        """Extract #include directives."""
        for line in lines:
            m = _INCLUDE_RE.match(line)
            if m:
                self.header.includes.append(m.group(1))

    # ─── Top-level construct parsers ──────────────────────────

    def _try_parse_class(self, lines: List[str], idx: int, stripped: str = None):
        """Parse a top-level class/struct declaration. Returns index after class body."""
        if stripped is None:
            stripped = lines[idx].strip()
        m = _CLASS_RE.match(stripped)
        if not m:
            return None

        kind = m.group(1)
        class_name = m.group(2)
        after = stripped[m.end():]

        # Template params
        template_params = []
        if after.lstrip().startswith('<'):
            template_params = self._extract_template_params(after)

        # Base class
        base_class = ""
        base_m = re.search(r':\s*(public|private|protected)?\s*(\w+(?:\s*\*)*)', after)
        if base_m:
            base_class = base_m.group(2)

        # Extract comment (look backwards for Doxygen comment)
        comment = self._find_comment_backwards(lines, idx)

        # Find the class body (skip to matching closing brace)
        methods = []
        attributes = []
        end_idx = self._extract_class_body(lines, idx, methods, attributes, class_name)

        cls = Class(
            name=class_name,
            template_params=template_params,
            base_class=base_class,
            attributes=attributes,
            methods=methods,
            comment=comment,
            is_struct=(kind == 'struct')
        )
        self.header.classes.append(cls)
        return end_idx

    @staticmethod
    def _count_braces_excluding_comments(lines: List[str], start_idx: int) -> int:
        """Count opening braces from start_idx, skipping commented lines.
        Returns the index after the matching closing brace."""
        brace_count = 0
        started = False
        i = start_idx

        while i < len(lines):
            stripped = lines[i].strip()

            # Skip commented-out lines for brace counting
            if not stripped.startswith('//'):
                for ch in stripped:
                    if ch == '{':
                        brace_count += 1
                        started = True
                    elif ch == '}':
                        brace_count -= 1

            if brace_count == 0 and started:
                return i + 1

            i += 1

        return i

    def _try_parse_namespace(self, lines: List[str], idx: int, stripped: str = None):
        """Parse a top-level namespace declaration. Returns index after namespace."""
        if stripped is None:
            stripped = lines[idx].strip()
        m = _NAMESPACE_RE.match(stripped)
        if not m:
            return None

        ns_name = m.group(1)
        comment = self._find_comment_backwards(lines, idx)

        # Find namespace body
        items = []
        end_idx = self._extract_namespace_body(lines, idx, items)

        ns = Namespace(name=ns_name, comment=comment, items=items)
        self.header.namespaces.append(ns)
        return end_idx

    def _try_parse_enum(self, lines: List[str], idx: int, stripped: str = None) -> bool:
        """Parse a top-level enum declaration."""
        if stripped is None:
            stripped = lines[idx].strip()
        m = _ENUM_RE.match(stripped)
        if not m:
            return False

        enum_name = m.group(2)
        comment = self._find_comment_backwards(lines, idx)

        # Extract enum members from the line
        members = []
        after = stripped[m.end():].strip()
        if '{' in after:
            members = self._extract_enum_members(after)

        self.header.enums.append(Enum(name=enum_name, members=members, comment=comment))
        return True

    def _try_parse_typedef(self, lines: List[str], idx: int, stripped: str = None) -> bool:
        """Parse a top-level typedef."""
        if stripped is None:
            stripped = lines[idx].strip()
        if not _TYPEDEF_RE.match(stripped):
            return False

        after = stripped[8:]
        parts = after.rstrip(';').strip().split()

        typedef_name = ""
        typedef_type = ""
        comment = self._find_comment_backwards(lines, idx)

        # Check for multi-line typedef (e.g., typedef struct/enum/union { ... } name;)
        if after.strip().startswith('struct {') or after.strip().startswith('union {') or after.strip().startswith('enum {'):
            # Look for the closing } name;
            for j in range(idx + 1, min(idx + 50, len(lines))):
                line = lines[j].strip()
                m = re.search(r'}\s+(\w+)\s*;', line)
                if m:
                    typedef_name = m.group(1)
                    typedef_type = after.strip().split()[0]  # struct, union, or enum
                    break
        elif len(parts) >= 2:
            typedef_type = ' '.join(parts[:-1])
            typedef_name = parts[-1]

        if typedef_name:
            self.header.typedefs.append(
                Typedef(name=typedef_name, type=typedef_type, comment=comment)
            )
        return True

    def _try_parse_function(self, lines: List[str], idx: int, stripped: str = None,
                            seen_functions: set = None) -> bool:
        """Parse a top-level function declaration.
        Uses seen_functions set to avoid duplicate declarations."""
        if stripped is None:
            stripped = lines[idx].strip()
        m = _FUNC_SIG_RE.match(stripped)
        if not m:
            return False

        return_type = m.group(1)
        func_name = m.group(2)

        # Skip if return type looks like a keyword (not a real type)
        if return_type in _SKIP_KEYWORDS:
            return False

        after = stripped[m.end():]

        # Template params
        template_params = []
        if after.lstrip().startswith('<'):
            template_params = self._extract_template_params(after)

        # Parameters
        params = self._extract_params(after)

        # Build a signature key for deduplication
        sig_key = (func_name, return_type, len(params))
        if seen_functions is not None:
            if sig_key in seen_functions:
                return False
            seen_functions.add(sig_key)

        comment = self._find_comment_backwards(lines, idx)

        self.header.functions.append(Function(
            name=func_name,
            return_type=return_type,
            parameters=params,
            template_params=template_params,
            comment=comment,
            is_inline='inline' in stripped.lower()
        ))
        return True

    def _try_parse_macro(self, lines: List[str], idx: int, stripped: str = None) -> bool:
        """Parse a #define macro."""
        if stripped is None:
            stripped = lines[idx].strip()
        m = _SIMPLE_DEFINE_RE.match(stripped)
        if not m:
            return False

        name = m.group(1)
        value = m.group(2).strip()

        if 'pragma' in value.lower():
            return False

        comment = self._find_comment_backwards(lines, idx)
        self.header.macros.append(Macro(name=name, value=value, comment=comment))
        return True

    def _skip_template(self, lines: List[str], start: int) -> int:
        """Skip a template <...> line, return the line after it."""
        return start + 1

    # ─── Body extraction helpers ──────────────────────────────

    def _extract_class_body(self, lines: List[str], start_idx: int,
                            methods: list, attributes: list, class_name: str = "") -> int:
        """Extract methods and attributes from a class body. Returns index after class."""
        # Track seen method signatures to avoid duplicates
        seen_methods = set()
        # Find opening brace
        brace_count = 0
        started = False
        i = start_idx

        while i < len(lines):
            stripped = lines[i].strip()

            # Count braces but skip commented-out lines
            if not stripped.startswith('//'):
                for ch in stripped:
                    if ch == '{':
                        brace_count += 1
                        started = True
                    elif ch == '}':
                        brace_count -= 1

            # Check for class end immediately after brace counting
            if brace_count <= 0 and started:
                return i + 1

            if not started:
                i += 1
                continue

            if not stripped or stripped.startswith('//'):
                i += 1
                continue

            # Skip pragma aux
            if self._is_pragma_aux_start(stripped):
                i = self._skip_pragma_aux(lines, i)
                continue

            # Access specifier
            if stripped in ('public:', 'private:', 'protected:'):
                i += 1
                continue

            # Skip brace-only lines (end of class, end of function, etc.)
            if stripped in ('}', '{', '};', '};', '{;'):
                i += 1
                continue

            # Skip template lines inside class body
            if _TEMPLATE_RE.match(stripped):
                i = self._skip_template(lines, i)
                continue

            # Skip lines starting with 'typedef' (typedef inside class is not a method)
            if _TYPEDEF_RE.match(stripped):
                i += 1
                continue

            # --- Method extraction (must happen BEFORE brace_count check) ---
            # Check for destructor: ~ClassName(
            if _DTOR_RE.match(stripped):
                m = _DTOR_RE.match(stripped)
                func_name = '~' + m.group(1)
                after = stripped[m.end():]
                params = self._extract_params(after)
                comment = self._find_comment_backwards(lines, i)
                # Dedup: same name + params
                sig_key = (func_name, tuple((p.type, p.name) for p in params))
                if sig_key not in seen_methods:
                    seen_methods.add(sig_key)
                    methods.append(Function(
                        name=func_name,
                        return_type='',
                        parameters=params,
                        comment=comment,
                        is_virtual=False,
                        is_inline=False
                    ))
                i += 1
                continue

            # Check for method with :: (e.g., int Font::write(...)
            m = _METHOD_SCOPE_RE.match(stripped)
            if m:
                return_type = m.group(1)
                scope_name = m.group(2)  # e.g., "Font::write"
                # Extract just the method name (after ::)
                func_name = scope_name.split('::')[-1]
                after = stripped[m.end():]
                params = self._extract_params(after)
                comment = self._find_comment_backwards(lines, i)
                is_virtual = 'virtual' in stripped.lower()
                is_inline = 'inline' in stripped.lower()
                is_static = 'static' in stripped.lower()
                # Dedup: same name + return_type + params
                sig_key = (func_name, return_type, tuple((p.type, p.name) for p in params))
                if sig_key not in seen_methods:
                    seen_methods.add(sig_key)
                    methods.append(Function(
                        name=func_name,
                        return_type=return_type,
                        parameters=params,
                        comment=comment,
                        is_virtual=is_virtual,
                        is_inline=is_inline,
                        is_static=is_static
                    ))
                i += 1
                continue

            # Check for constructor: ClassName(...)
            ctor_m = re.match(r'^\s*(\w+)\s*\(', stripped)
            if ctor_m and class_name and ctor_m.group(1) == class_name:
                func_name = ctor_m.group(1)
                after = stripped[ctor_m.end():]
                params = self._extract_params(after)
                comment = self._find_comment_backwards(lines, i)
                is_inline = 'inline' in stripped.lower()
                # Dedup: same name + params
                sig_key = (func_name, '', tuple((p.type, p.name) for p in params))
                if sig_key not in seen_methods:
                    seen_methods.add(sig_key)
                    methods.append(Function(
                        name=func_name,
                        return_type='',
                        parameters=params,
                        comment=comment,
                        is_virtual=False,
                        is_inline=is_inline
                    ))
                i += 1
                continue

            # Skip lines inside function bodies (brace_count > 1 means we're inside a function)
            # Only process top-level class members (brace_count == 1)
            if brace_count > 1:
                i += 1
                continue

            # Attribute (simple type + name, no function call)
            if self._is_attribute(stripped, methods):
                # Extract type and name: handle multi-word types like "const unsigned int"
                parts = stripped.rstrip(';').strip().split()
                # Find where the variable name starts (after type words)
                # Type words are words that look like types (not variable names)
                # Variable names are typically lowercase identifiers
                type_parts = []
                name_idx = 0
                for idx, part in enumerate(parts):
                    # A type word typically starts with uppercase or is a known type
                    # A variable name is lowercase alphanumeric
                    if part[0].isupper() or part in ('int', 'float', 'double', 'char', 'bool',
                        'uint8_t', 'uint16_t', 'uint32_t', 'uint64_t',
                        'int8_t', 'int16_t', 'int32_t', 'int64_t',
                        'size_t', 'long', 'short', 'unsigned', 'signed',
                        'const', 'volatile', 'static', 'extern', 'void',
                        'wchar_t', 'string', 'wstring', 'std'):
                        type_parts.append(part)
                    else:
                        name_idx = idx
                        break

                if name_idx > 0 and type_parts:
                    attr_type = ' '.join(type_parts)
                    # First variable name (may have comma-separated names after)
                    attr_name = parts[name_idx].rstrip(',;')
                elif parts:
                    attr_type = parts[0]
                    attr_name = parts[-1].rstrip(',;')

                comment = self._find_comment_backwards(lines, i)
                attributes.append(Attribute(name=attr_name, type=attr_type, comment=comment))
                i += 1
                continue

            # Function/method declaration (regular signature)
            m = _FUNC_SIG_RE.match(stripped)
            if m:
                return_type = m.group(1)
                func_name = m.group(2)
                after = stripped[m.end():]
                params = self._extract_params(after)
                comment = self._find_comment_backwards(lines, i)
                is_virtual = 'virtual' in stripped.lower()
                is_inline = 'inline' in stripped.lower()
                is_static = 'static' in stripped.lower()
                # Dedup: same name + return_type + params
                sig_key = (func_name, return_type, tuple((p.type, p.name) for p in params))
                if sig_key not in seen_methods:
                    seen_methods.add(sig_key)
                    methods.append(Function(
                        name=func_name,
                        return_type=return_type,
                        parameters=params,
                        comment=comment,
                        is_virtual=is_virtual,
                        is_inline=is_inline,
                        is_static=is_static
                    ))
                i += 1
                continue

            i += 1

            # Class body ended
            if brace_count <= 0:
                return i + 1

        return i + 1

    def _extract_namespace_body(self, lines: List[str], start_idx: int, items: list) -> int:
        """Extract items from a namespace body. Returns index after namespace."""
        brace_count = 0
        started = False
        i = start_idx

        while i < len(lines):
            stripped = lines[i].strip()

            # Count braces but skip commented-out lines
            if not stripped.startswith('//'):
                for ch in stripped:
                    if ch == '{':
                        brace_count += 1
                        started = True
                    elif ch == '}':
                        brace_count -= 1

            # Check for namespace end immediately after brace counting
            if brace_count <= 0 and started:
                return i + 1

            if not started:
                i += 1
                continue

            if not stripped or stripped.startswith('//'):
                i += 1
                continue

            # Skip brace-only lines
            if stripped in ('}', '{', '};', '};', '{;'):
                i += 1
                continue

            # Skip template lines
            if _TEMPLATE_RE.match(stripped):
                i = self._skip_template(lines, i)
                continue

            if self._is_pragma_aux_start(stripped):
                i = self._skip_pragma_aux(lines, i)
                continue

            # Try to parse namespace members
            next_idx = self._try_parse_class(lines, i, stripped)
            if next_idx is not None:
                i = next_idx
                continue
            elif self._try_parse_function(lines, i, stripped):
                i += 1
            elif self._try_parse_enum(lines, i, stripped):
                i += 1
            elif self._try_parse_typedef(lines, i, stripped):
                i += 1
            elif self._try_parse_macro(lines, i, stripped):
                i += 1
            else:
                i += 1

        return i + 1

    def _is_attribute(self, stripped: str, methods: list) -> bool:
        """Check if a line is a class attribute (not a function)."""
        # Must end with semicolon
        if not stripped.endswith(';'):
            return False
        # Must not contain parentheses (function call)
        if '(' in stripped:
            return False
        # Skip control flow keywords
        skip_words = {'if', 'else', 'for', 'while', 'switch', 'return',
                     'new', 'delete', 'this', 'using', 'sizeof', 'alignof'}
        parts = stripped.split()
        if parts and parts[0] in skip_words:
            return False
        return True

    # ─── Comment extraction ───────────────────────────────────

    def _find_comment_backwards(self, lines: List[str], idx: int) -> str:
        """Find the Doxygen comment immediately preceding a line."""
        i = idx - 1
        # Skip empty lines and regular comments
        while i >= 0:
            stripped = lines[i].strip()
            if stripped.startswith('/*') and not stripped.startswith('/**'):
                # Regular comment, skip
                i -= 1
                continue
            if stripped.startswith('//'):
                i -= 1
                continue
            if not stripped:
                i -= 1
                continue
            if stripped.startswith('template'):
                # Template line before class/struct, skip
                i -= 1
                continue
            # Found potential Doxygen comment end (*/)
            if stripped == '*/':
                # Look backwards for the opening /**
                j = i - 1
                while j >= 0:
                    s = lines[j].strip()
                    if s.startswith('/**'):
                        comment_lines = [s[3:].strip()]
                        # Collect lines between /** and */
                        k = j + 1
                        while k < i:
                            t = lines[k].strip()
                            if t.startswith('/**'):
                                comment_lines.append(t[3:].strip())
                            elif t.startswith('*') and not t.startswith('//'):
                                comment_lines.append(t[1:].strip())
                            elif t.startswith('//'):
                                comment_lines.append(t[2:].strip())
                            k += 1
                        return ' '.join(comment_lines)
                    elif s.startswith('*') or s == '*/' or not s:
                        j -= 1
                    else:
                        return ""
            # Found potential Doxygen comment start (/**)
            if stripped.startswith('/**'):
                comment_lines = [stripped[3:].strip()]
                j = i - 1
                while j >= 0:
                    s = lines[j].strip()
                    if s.startswith('/**'):
                        comment_lines.append(s[3:].strip())
                    elif s == '*/':
                        return ' '.join(comment_lines)
                    elif s.startswith('*'):
                        comment_lines.append(s[1:].strip())
                    elif s.startswith('//'):
                        comment_lines.append(s[2:].strip())
                    j -= 1
            return ""
        return ""

    # ─── Utility helpers ──────────────────────────────────────

    @staticmethod
    def _is_pragma_aux_start(stripped: str) -> bool:
        m = _PRAGMA_RE.match(stripped)
        return m and m.group(1).lower() == 'aux'

    def _skip_pragma_aux(self, lines: List[str], start: int) -> int:
        """Skip a #pragma aux block, return the line after it."""
        i = start + 1
        while i < len(lines):
            stripped = lines[i].strip()
            if not stripped.endswith('\\'):
                return i + 1
            i += 1
        return i

    def _extract_template_params(self, text: str) -> List[str]:
        """Extract template parameters from text like '<T, typename U>'."""
        params = []
        depth = 0
        current = ""
        for ch in text:
            if ch == '<':
                depth += 1
                current += ch
            elif ch == '>':
                depth -= 1
                current += ch
                if depth == 0:
                    break
            elif depth > 0 and ch == ',':
                params.append(current.strip())
                current = ""
            elif depth > 0:
                current += ch
        if current.strip():
            params.append(current.strip())
        return params

    def _extract_params(self, text: str) -> List[Parameter]:
        """Extract function parameters from text after the opening paren."""
        params = []
        depth = 1
        param_text = ""
        for ch in text:
            if ch == '(':
                depth += 1
                param_text += ch
            elif ch == ')':
                depth -= 1
                if depth == 0:
                    break
                param_text += ch
            elif depth > 0:
                param_text += ch

        if not param_text.strip():
            return params

        parts = self._split_params(param_text)
        for part in parts:
            part = part.strip()
            if not part:
                continue
            m = _PARAM_RE.match(part)
            if m:
                param_type = m.group(1).strip()
                param_name = m.group(2) if m.group(2) else ""
                default = m.group(3) if m.group(3) else ""
                # Clean up type: remove extra whitespace
                param_type = ' '.join(param_type.split())
                params.append(Parameter(name=param_name, type=param_type, default=default))
            else:
                # Try anonymous parameter (just type, no name)
                m = _PARAM_RE_ANON.match(part)
                if m:
                    param_type = m.group(1).strip()
                    param_type = ' '.join(param_type.split())
                    params.append(Parameter(name="", type=param_type, default=""))

        return params

    @staticmethod
    def _split_params(param_text: str) -> List[str]:
        """Split parameter text by commas, respecting angle brackets."""
        parts = []
        depth = 0
        current = ""
        for ch in param_text:
            if ch == '<':
                depth += 1
                current += ch
            elif ch == '>':
                depth -= 1
                current += ch
            elif ch == ',' and depth == 0:
                parts.append(current)
                current = ""
            else:
                current += ch
        if current.strip():
            parts.append(current)
        return parts

    def _extract_enum_members(self, text: str) -> List[EnumMember]:
        """Extract enum members from text like '{ A = 1, B, C }'."""
        members = []
        start = text.find('{')
        if start == -1:
            return members
        end = text.find('}', start)
        if end == -1:
            end = len(text)
        content = text[start + 1:end]

        parts = [p.strip() for p in content.split(',') if p.strip()]
        for part in parts:
            if '=' in part:
                name, value = part.split('=', 1)
                members.append(EnumMember(name=name.strip(), value=value.strip()))
            else:
                members.append(EnumMember(name=part.strip()))

        return members
