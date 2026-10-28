"""Minimal Liberty / LEF scanners.

Only what the partitioner needs: per cell area, sequential flag, pin
directions, and macro footprints.  Not a general Liberty parser: it walks
group braces and reads a few simple attributes, which is robust for the
NLDM libraries shipped with ORFS platforms (ASAP7, Nangate45, sky130).
"""
from __future__ import annotations

import gzip
import re
from dataclasses import dataclass, field

_CELL_RE = re.compile(r'^\s*cell\s*\(\s*"?([^")\s]+)"?\s*\)\s*\{')
_PIN_RE = re.compile(r'^\s*(pin|bus)\s*\(\s*"?([^")\s]+)"?\s*\)\s*\{')
_AREA_RE = re.compile(r'^\s*area\s*:\s*([0-9.eE+-]+)')
_DIR_RE = re.compile(r'^\s*direction\s*:\s*"?(\w+)"?')
_SEQ_RE = re.compile(r'^\s*(ff|ff_bank|latch|latch_bank|statetable)\s*\(')
_CLK_RE = re.compile(r'^\s*clock\s*:\s*"?true"?')
_CAP_RE = re.compile(r'^\s*capacitance\s*:\s*([0-9.eE+-]+)')


@dataclass
class LibCell:
    name: str
    area: float = 0.0
    sequential: bool = False
    pins: dict = field(default_factory=dict)   # pin -> "input"/"output"/"inout"
    clock_pins: set = field(default_factory=set)
    pin_caps: dict = field(default_factory=dict)  # input pin -> capacitance (library unit, fF on ASAP7)
    is_macro: bool = False


def _open(path):
    if path.endswith(".gz"):
        return gzip.open(path, "rt", errors="replace")
    return open(path, "r", errors="replace")


def read_liberty(paths, cells=None):
    """Return {cell_name: LibCell} for every cell in the given files."""
    cells = {} if cells is None else cells
    for path in paths:
        cur = None
        cur_pin = None
        depth = 0
        cell_depth = pin_depth = -1
        with _open(path) as fh:
            text = fh.read()
        # one statement per line, whatever the source formatting
        text = re.sub(r"\\\n", " ", text)
        text = re.sub(r"([{;])", r"\1\n", text).replace("}", "\n}\n")
        for line in text.splitlines():
            m = _CELL_RE.match(line)
            if m and cur is None:
                cur = cells.setdefault(m.group(1), LibCell(m.group(1)))
                cell_depth = depth
            elif cur is not None:
                if cur_pin is None:
                    mp = _PIN_RE.match(line)
                    if mp and depth == cell_depth + 1:
                        cur_pin = mp.group(2)
                        pin_depth = depth
                    else:
                        ma = _AREA_RE.match(line)
                        if ma and depth == cell_depth + 1:
                            cur.area = float(ma.group(1))
                        if _SEQ_RE.match(line):
                            cur.sequential = True
                else:
                    md = _DIR_RE.match(line)
                    if md and depth == pin_depth + 1:
                        cur.pins[cur_pin] = md.group(1)
                    mc = _CAP_RE.match(line)
                    if mc and depth == pin_depth + 1:
                        cur.pin_caps[cur_pin] = float(mc.group(1))
                    if _CLK_RE.match(line):
                        cur.clock_pins.add(cur_pin)
            depth += line.count("{") - line.count("}")
            if cur_pin is not None and depth <= pin_depth:
                cur_pin = None
            if cur is not None and depth <= cell_depth:
                cur = None
    return cells


@dataclass
class LefMacro:
    name: str
    width: float
    height: float
    cls: str


def read_lef_macros(paths):
    """Return {macro: LefMacro} for every MACRO in the given LEF files."""
    out = {}
    for path in paths:
        name = cls = None
        w = h = 0.0
        with _open(path) as fh:
            for line in fh:
                t = line.split()
                if not t:
                    continue
                if t[0] == "MACRO" and len(t) > 1:
                    name, cls, w, h = t[1], "", 0.0, 0.0
                elif name and t[0] == "CLASS" and not cls:
                    cls = " ".join(t[1:]).rstrip(" ;")
                elif name and t[0] == "SIZE" and len(t) >= 4:
                    w, h = float(t[1]), float(t[3])
                elif name and t[0] == "END" and len(t) > 1 and t[1] == name:
                    out[name] = LefMacro(name, w, h, cls)
                    name = None
    return out


def mark_macros(cells, lef_macros):
    """Flag liberty cells whose LEF class is BLOCK (hard macros)."""
    for name, m in lef_macros.items():
        if m.cls.upper().startswith("BLOCK") and name in cells:
            cells[name].is_macro = True
            cells[name].area = max(cells[name].area, m.width * m.height)
    return cells
