"""Structural Verilog reader for flat gate-level netlists (Yosys/OpenROAD style).

The reader keeps two views of one module:

* a *bit-level* view -- every port, wire and cell pin resolved to single-bit
  net names, with ``assign`` aliases merged -- which the scan inserter and the
  ATPG model builder analyse; and
* the *source spans* of every statement, so the scan inserter can rewrite the
  instances it changes and append new ones while leaving every other byte of
  the file exactly as the synthesis tool wrote it.

Only the constructs a flat mapped netlist uses are accepted: port, wire and
direction declarations with an optional ``[msb:lsb]`` range, cell instances
with named port connections, and ``assign`` with identifiers, bit and part
selects, sized constants and concatenations.  Anything else is an error, not
a silent skip.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

_TOKEN = re.compile(
    r"""
    (?P<ws>\s+)
  | (?P<comment>//[^\n]*|/\*.*?\*/)
  | (?P<attr>\(\*.*?\*\))
  | (?P<esc>\\\S+)
  | (?P<num>\d*'[sS]?[bBhHdDoO][0-9a-fA-FxXzZ_?]+|\d+)
  | (?P<id>[A-Za-z_$][A-Za-z0-9_$]*)
  | (?P<sym>[()\[\]{}.,;:=#])
    """,
    re.S | re.X,
)


@dataclass
class Tok:
    kind: str
    text: str
    start: int
    end: int


def tokenize(text: str) -> list[Tok]:
    out: list[Tok] = []
    pos = 0
    n = len(text)
    while pos < n:
        m = _TOKEN.match(text, pos)
        if not m:
            raise ValueError(f"netlist: cannot tokenise at offset {pos}: {text[pos:pos + 40]!r}")
        kind = m.lastgroup
        if kind not in ("ws", "comment", "attr"):
            tok_text = m.group(0)
            if kind == "esc":
                kind = "id"  # escaped identifiers keep their backslash spelling
            out.append(Tok(kind, tok_text, m.start(), m.end()))
        pos = m.end()
    return out


def canonical_name(name: str) -> str:
    """Escaped identifiers ``\\foo`` and plain ``foo`` name the same net."""
    if name.startswith("\\"):
        plain = name[1:]
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_$]*", plain):
            return plain
        return plain
    return name


def verilog_name(name: str) -> str:
    """Spell a canonical name as a Verilog identifier."""
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_$]*", name):
        return name
    return "\\" + name + " "


def parse_const(text: str) -> list[str]:
    """A sized or unsized constant as a list of bit characters, MSB first."""
    if "'" not in text:
        value = int(text)
        return [c for c in format(value, "032b")]
    size_text, rest = text.split("'", 1)
    rest = rest.lstrip("sS")
    base = rest[0].lower()
    digits = rest[1:].replace("_", "").lower()
    width = int(size_text) if size_text else 32
    per = {"b": 1, "o": 3, "h": 4}.get(base)
    bits: list[str] = []
    if per is None:  # decimal
        value = int(digits)
        bits = list(format(value, f"0{width}b"))
    else:
        for ch in digits:
            if ch in "xz?":
                bits.extend([ch if ch != "?" else "z"] * per)
            else:
                bits.extend(format(int(ch, 16 if base == "h" else 8 if base == "o" else 2), f"0{per}b"))
    if len(bits) < width:
        pad = bits[0] if bits and bits[0] in "xz" else "0"
        bits = [pad] * (width - len(bits)) + bits
    return bits[-width:]


@dataclass
class Instance:
    cell: str
    name: str            # canonical instance name
    pins: dict[str, list[str]]       # pin -> bit list (MSB first); bits are net names or "1'b0"/"1'b1"/"1'bx"
    pin_text: dict[str, str]          # pin -> original connection text
    span: tuple[int, int]             # byte span of the whole statement including ';'
    order: int = 0


@dataclass
class Module:
    name: str
    text: str
    ports: list[str] = field(default_factory=list)
    port_dirs: dict[str, str] = field(default_factory=dict)
    ranges: dict[str, tuple[int, int] | None] = field(default_factory=dict)
    instances: list[Instance] = field(default_factory=list)
    assigns: list[tuple[list[str], list[str], tuple[int, int]]] = field(default_factory=list)
    header_span: tuple[int, int] = (0, 0)       # 'module ... ;'
    port_list_close: int = 0                    # offset of the ')' closing the port list
    end_span: tuple[int, int] = (0, 0)          # 'endmodule'
    decl_end: int = 0                           # offset just after the header ';'

    # ------------------------------------------------------------------
    def bits_of(self, name: str) -> list[str]:
        rng = self.ranges.get(name)
        if rng is None:
            return [name]
        msb, lsb = rng
        step = -1 if msb >= lsb else 1
        return [f"{name}[{i}]" for i in range(msb, lsb + step, step)]

    def port_bits(self, direction: str) -> list[str]:
        out: list[str] = []
        for port in self.ports:
            if self.port_dirs.get(port) == direction:
                out.extend(self.bits_of(port))
        return out


class _Parser:
    def __init__(self, text: str):
        self.text = text
        self.toks = tokenize(text)
        self.i = 0

    def peek(self, k: int = 0) -> Tok | None:
        j = self.i + k
        return self.toks[j] if j < len(self.toks) else None

    def take(self, expect: str | None = None) -> Tok:
        tok = self.toks[self.i]
        if expect is not None and tok.text != expect:
            raise ValueError(f"netlist: expected {expect!r}, got {tok.text!r} at offset {tok.start}")
        self.i += 1
        return tok

    def parse_modules(self) -> list[Module]:
        mods: list[Module] = []
        while self.peek() is not None:
            tok = self.take()
            if tok.text == "module":
                mods.append(self.parse_module(tok.start))
            else:
                raise ValueError(f"netlist: unexpected {tok.text!r} outside a module at {tok.start}")
        return mods

    def parse_range(self) -> tuple[int, int] | None:
        if self.peek() and self.peek().text == "[":
            self.take("[")
            msb = int(self.take().text)
            self.take(":")
            lsb = int(self.take().text)
            self.take("]")
            return (msb, lsb)
        return None

    def parse_module(self, start: int) -> Module:
        name = canonical_name(self.take().text)
        mod = Module(name=name, text=self.text)
        if self.peek().text == "#":
            raise ValueError("netlist: parameterised modules are not supported")
        self.take("(")
        while self.peek().text != ")":
            tok = self.take()
            if tok.text == ",":
                continue
            if tok.text in ("input", "output", "inout", "wire"):
                raise ValueError("netlist: ANSI port declarations are not supported")
            mod.ports.append(canonical_name(tok.text))
        close = self.take(")")
        mod.port_list_close = close.start
        semi = self.take(";")
        mod.header_span = (start, semi.end)
        mod.decl_end = semi.end
        order = 0
        while True:
            tok = self.peek()
            if tok is None:
                raise ValueError("netlist: missing endmodule")
            if tok.text == "endmodule":
                self.take()
                mod.end_span = (tok.start, tok.end)
                break
            if tok.text in ("input", "output", "inout", "wire", "reg", "tri", "supply0", "supply1"):
                kind = self.take().text
                if self.peek().text == "signed":
                    self.take()
                rng = self.parse_range()
                while True:
                    net = canonical_name(self.take().text)
                    if kind in ("input", "output", "inout"):
                        mod.port_dirs[net] = kind
                    if net not in mod.ranges or rng is not None:
                        mod.ranges[net] = rng
                    sep = self.take()
                    if sep.text == ";":
                        break
                    if sep.text != ",":
                        raise ValueError(f"netlist: bad declaration near offset {sep.start}")
                continue
            if tok.text == "assign":
                self.take()
                lhs = self.parse_expr(mod)
                self.take("=")
                rhs = self.parse_expr(mod)
                semi = self.take(";")
                mod.assigns.append((lhs, rhs, (tok.start, semi.end)))
                continue
            # cell instance
            cell = canonical_name(self.take().text)
            if self.peek().text == "#":
                raise ValueError(f"netlist: parameterised instance of {cell} not supported")
            inst_name = canonical_name(self.take().text)
            self.take("(")
            pins: dict[str, list[str]] = {}
            pin_text: dict[str, str] = {}
            while self.peek().text != ")":
                t = self.take()
                if t.text == ",":
                    continue
                if t.text != ".":
                    raise ValueError(f"netlist: positional connections are not supported ({cell} {inst_name})")
                pin = canonical_name(self.take().text)
                open_tok = self.take("(")
                if self.peek().text == ")":
                    close_tok = self.take(")")
                    pins[pin] = []
                    pin_text[pin] = ""
                    continue
                expr_start = self.peek().start
                bits = self.parse_expr(mod)
                last = self.toks[self.i - 1]
                close_tok = self.take(")")
                pins[pin] = bits
                spelled = self.text[expr_start:close_tok.start].strip()
                if last.text.startswith("\\"):
                    spelled += " "   # an escaped identifier needs its terminating space
                pin_text[pin] = spelled
                del open_tok
            self.take(")")
            semi = self.take(";")
            mod.instances.append(Instance(cell, inst_name, pins, pin_text, (tok.start, semi.end), order))
            order += 1
        return mod

    def parse_expr(self, mod: Module) -> list[str]:
        tok = self.peek()
        if tok.text == "{":
            self.take("{")
            bits: list[str] = []
            while True:
                bits.extend(self.parse_expr(mod))
                sep = self.take()
                if sep.text == "}":
                    return bits
                if sep.text != ",":
                    raise ValueError(f"netlist: bad concatenation at {sep.start}")
        tok = self.take()
        if tok.kind == "num":
            return ["1'b" + b if b in "01" else "1'bx" for b in parse_const(tok.text)]
        name = canonical_name(tok.text)
        if self.peek() is not None and self.peek().text == "[":
            self.take("[")
            hi = int(self.take().text)
            if self.peek().text == ":":
                self.take(":")
                lo = int(self.take().text)
                self.take("]")
                step = -1 if hi >= lo else 1
                return [f"{name}[{i}]" for i in range(hi, lo + step, step)]
            self.take("]")
            return [f"{name}[{hi}]"]
        return mod.bits_of(name) if name in mod.ranges else [name]


def parse_netlist(text: str) -> list[Module]:
    return _Parser(text).parse_modules()


def read_module(path: Path, top: str | None = None) -> Module:
    text = Path(path).read_text(encoding="utf-8")
    mods = parse_netlist(text)
    if top is None:
        if len(mods) != 1:
            names = [m.name for m in mods]
            raise ValueError(f"netlist {path}: {len(mods)} modules {names}; name the top")
        return mods[0]
    for mod in mods:
        if mod.name == top:
            return mod
    raise ValueError(f"netlist {path}: no module {top}")


def is_const_bit(bit: str) -> bool:
    return bit.startswith("1'b")


class NetAliases:
    """Union-find over bit nets, merging the two sides of every ``assign``."""

    def __init__(self) -> None:
        self.parent: dict[str, str] = {}

    def find(self, x: str) -> str:
        parent = self.parent
        root = x
        while parent.get(root, root) != root:
            root = parent[root]
        while parent.get(x, x) != root:
            parent[x], x = root, parent[x]
        return root

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return
        # constants always win as representatives
        if is_const_bit(rb) and not is_const_bit(ra):
            ra, rb = rb, ra
        if is_const_bit(ra) and is_const_bit(rb) and ra != rb:
            raise ValueError(f"netlist: assign ties {ra} to {rb}")
        self.parent[rb] = ra


def build_aliases(mod: Module) -> NetAliases:
    aliases = NetAliases()
    for lhs, rhs, _ in mod.assigns:
        if len(lhs) != len(rhs):
            # Verilog zero-extends / truncates; align at the LSB
            if len(rhs) < len(lhs):
                rhs = ["1'b0"] * (len(lhs) - len(rhs)) + rhs
            else:
                rhs = rhs[len(rhs) - len(lhs):]
        for a, b in zip(lhs, rhs):
            if b == "1'bx":
                continue
            aliases.union(a, b)
    return aliases
