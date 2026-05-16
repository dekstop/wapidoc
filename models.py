"""
Data models for parsed C++ header constructs.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Comment:
    """A Doxygen-style comment block."""
    text: str


@dataclass
class Parameter:
    """A single function parameter."""
    name: str
    type: str
    default: str = ""


@dataclass
class Function:
    """A function declaration (free or member)."""
    name: str
    return_type: str
    parameters: List[Parameter] = field(default_factory=list)
    template_params: List[str] = field(default_factory=list)
    is_static: bool = False
    is_inline: bool = False
    is_const: bool = False
    is_virtual: bool = False
    comment: str = ""
    access: str = "public"  # public, private, protected


@dataclass
class Attribute:
    """A class member variable."""
    name: str
    type: str
    comment: str = ""
    access: str = "public"  # public, private, protected


@dataclass
class Class:
    """A class or struct declaration."""
    name: str
    template_params: List[str] = field(default_factory=list)
    base_class: str = ""
    attributes: List[Attribute] = field(default_factory=list)
    methods: List[Function] = field(default_factory=list)
    nested_classes: List['Class'] = field(default_factory=list)
    comment: str = ""
    access: str = "public"
    is_struct: bool = False


@dataclass
class EnumMember:
    """A single enum member."""
    name: str
    value: str = ""


@dataclass
class Enum:
    """An enum declaration."""
    name: str
    members: List[EnumMember] = field(default_factory=list)
    comment: str = ""


@dataclass
class Typedef:
    """A typedef declaration."""
    name: str
    type: str
    comment: str = ""


@dataclass
class Macro:
    """A #define macro."""
    name: str
    value: str = ""
    comment: str = ""


@dataclass
class Namespace:
    """A namespace block."""
    name: str
    items: List = field(default_factory=list)  # Classes, Functions, Enums, etc.
    comment: str = ""


@dataclass
class HeaderDoc:
    """The complete parsed result for one header file."""
    filename: str
    header_comment: str = ""
    includes: List[str] = field(default_factory=list)
    classes: List[Class] = field(default_factory=list)
    namespaces: List[Namespace] = field(default_factory=list)
    functions: List[Function] = field(default_factory=list)
    enums: List[Enum] = field(default_factory=list)
    typedefs: List[Typedef] = field(default_factory=list)
    macros: List[Macro] = field(default_factory=list)
