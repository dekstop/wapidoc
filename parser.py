"""
Watcom C++ header file parser.

Uses a simple line-by-line approach to extract API declarations
from Watcom C++ headers. Standard library only.
"""

import re
from typing import List, Optional

from models import (
    HeaderDoc, Class, Function, Attribute, Parameter,
    Namespace, Enum, EnumMember, Typedef, Macro
)


# ─── Regex patterns ───────────────────────────────────────────────

_CLASS_RE = re.compile(r'^\s*(class|struct)\s+(\w+)')
_NAMESPACE_RE = re.compile(r'^\s*namespace\s+(\w+)')
_ENUM_RE = re.compile(r'^\s*enum\s+(class\s+)?(\w+)')
_TYPEDEF_RE = re.compile(r'^\s*typedef\s+')
_FUNC_SIG_RE = re.compile(r'^(\w+(?:\s*\*)*)\s+(\w+)\s*\(')
_SIMPLE_DEFINE_RE = re.compile(r'^\s*#\s*define\s+(\w+)(?:\s*\([^)]*\))?\s+(.*)')
_INCLUDE_RE = re.compile(r'^\s*#\s*include\s*[<"](.+?)[">]')
_PRAGMA_RE = re.compile(r'^\s*#\s*pragma\s+(\w+)')
_PARAM_RE = re.compile(r'(\w+(?:\s*\*)*)\s+(\w+)(?:\s*=\s*([^\s,]+))?')


# ─── Main Parser ──────────────────────────────────────────────────

class HeaderParser:
    """Parse a Watcom C++ header file and produce a HeaderDoc AST."""

    def __init__(self):
        self.header = HeaderDoc(filename="")

    def parse(self, filename: str, source: str) -> HeaderDoc:
        """Parse a header file and return the HeaderDoc AST."""
        self.header = HeaderDoc(filename=filename)
        lines = source.split('\n')

        # Extract header-level comment
        self._extract_header_comment(lines)

        # Extract #includes
        self._extract_includes(lines)

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

            # Try top-level constructs
            next_idx = self._try_parse_class(lines, i)
            if next_idx is not None:
                i = next_idx
                continue
            elif self._try_parse_namespace(lines, i):
                i += 1
            elif self._try_parse_enum(lines, i):
                i += 1
            elif self._try_parse_typedef(lines, i):
                i += 1
            elif self._try_parse_function(lines, i):
                i += 1
            elif self._try_parse_macro(lines, i):
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

    # ─── Top-level construct parsers ──────────────────────────────

    def _try_parse_class(self, lines: List[str], idx: int):
        """Parse a top-level class/struct declaration. Returns index after class body."""
        line = lines[idx]
        m = _CLASS_RE.match(line)
        if not m:
            return None

        kind = m.group(1)
        class_name = m.group(2)
        after = line[m.end():]

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
        end_idx = self._extract_class_body(lines, idx, methods, attributes)

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

    def _try_parse_namespace(self, lines: List[str], idx: int):
        """Parse a top-level namespace declaration. Returns index after namespace."""
        line = lines[idx]
        m = _NAMESPACE_RE.match(line)
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

    def _try_parse_enum(self, lines: List[str], idx: int) -> bool:
        """Parse a top-level enum declaration."""
        line = lines[idx]
        m = _ENUM_RE.match(line)
        if not m:
            return False

        enum_name = m.group(2)
        comment = self._find_comment_backwards(lines, idx)

        # Extract enum members from the line
        members = []
        after = line[m.end():].strip()
        if '{' in after:
            members = self._extract_enum_members(after)

        self.header.enums.append(Enum(name=enum_name, members=members, comment=comment))
        return True

    def _try_parse_typedef(self, lines: List[str], idx: int) -> bool:
        """Parse a top-level typedef."""
        line = lines[idx]
        if not _TYPEDEF_RE.match(line):
            return False

        after = line.strip()[8:]
        parts = after.rstrip(';').strip().split()
        if len(parts) >= 2:
            typedef_type = ' '.join(parts[:-1])
            typedef_name = parts[-1]
            comment = self._find_comment_backwards(lines, idx)
            self.header.typedefs.append(
                Typedef(name=typedef_name, type=typedef_type, comment=comment)
            )
        return True

    def _try_parse_function(self, lines: List[str], idx: int) -> bool:
        """Parse a top-level function declaration."""
        line = lines[idx]
        m = _FUNC_SIG_RE.match(line)
        if not m:
            return False

        return_type = m.group(1)
        func_name = m.group(2)
        after = line[m.end():]

        # Template params
        template_params = []
        if after.lstrip().startswith('<'):
            template_params = self._extract_template_params(after)

        # Parameters
        params = self._extract_params(after)

        comment = self._find_comment_backwards(lines, idx)

        self.header.functions.append(Function(
            name=func_name,
            return_type=return_type,
            parameters=params,
            template_params=template_params,
            comment=comment,
            is_inline='inline' in line.lower()
        ))
        return True

    def _try_parse_macro(self, lines: List[str], idx: int) -> bool:
        """Parse a #define macro."""
        line = lines[idx]
        m = _SIMPLE_DEFINE_RE.match(line)
        if not m:
            return False

        name = m.group(1)
        value = m.group(2).strip()

        if 'pragma' in value.lower():
            return False

        comment = self._find_comment_backwards(lines, idx)
        self.header.macros.append(Macro(name=name, value=value, comment=comment))
        return True

    # ─── Body extraction helpers ──────────────────────────────────

    def _extract_class_body(self, lines: List[str], start_idx: int,
                            methods: list, attributes: list) -> int:
        """Extract methods and attributes from a class body. Returns index after class."""
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

            # Skip lines inside function bodies (brace_count > 1 means we're inside a function)
            # Only process top-level class members (brace_count == 1)
            if brace_count > 1:
                i += 1
                continue

            # Attribute (simple type + name, no function call)
            if self._is_attribute(stripped, methods):
                attr_name = stripped.split()[-1].rstrip(';')
                attr_type = stripped.split()[0]
                comment = self._find_comment_backwards(lines, i)
                attributes.append(Attribute(name=attr_name, type=attr_type, comment=comment))
                i += 1
                continue

            # Function/method declaration
            m = _FUNC_SIG_RE.match(stripped)
            if m:
                return_type = m.group(1)
                func_name = m.group(2)
                after = stripped[m.end():]
                params = self._extract_params(after)
                comment = self._find_comment_backwards(lines, i)
                is_virtual = 'virtual' in stripped.lower()
                is_inline = 'inline' in stripped.lower()
                methods.append(Function(
                    name=func_name,
                    return_type=return_type,
                    parameters=params,
                    comment=comment,
                    is_virtual=is_virtual,
                    is_inline=is_inline
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

            if not started:
                i += 1
                continue

            if not stripped or stripped.startswith('//'):
                i += 1
                continue

            if self._is_pragma_aux_start(stripped):
                i = self._skip_pragma_aux(lines, i)
                continue

            # Try to parse namespace members
            next_idx = self._try_parse_class(lines, i)
            if next_idx is not None:
                i = next_idx
                continue
            elif self._try_parse_function(lines, i):
                i += 1
            elif self._try_parse_enum(lines, i):
                i += 1
            elif self._try_parse_typedef(lines, i):
                i += 1
            elif self._try_parse_macro(lines, i):
                i += 1
            else:
                i += 1

            if brace_count <= 0:
                return i + 1

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

    # ─── Comment extraction ───────────────────────────────────────

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
            # Found potential Doxygen comment
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

    # ─── Utility helpers ──────────────────────────────────────────

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
                param_name = m.group(2)
                default = m.group(3) if m.group(3) else ""
                params.append(Parameter(name=param_name, type=param_type, default=default))

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
