"""Read a block's extracted timing model (write_timing_model Liberty).

For every pin or bus: the worst setup constraint against the clock (an
input's internal budget used, setup included) and the worst clock-to-output
delay (an output's), in picoseconds, plus combinational through-arcs.  These
are the routed, extracted counterparts of the pre-layout boundary numbers the
budget divided the cycle with, so ``actual <= budget`` is the per-pin closure
check of a block against its budget.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

_NUM = re.compile(r"-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?")


def _groups(text: str, start: int = 0):
    """Yield (head, body_start, body_end) of the top-level groups in text."""
    i = start
    n = len(text)
    while i < n:
        m = re.compile(r"(\w+)\s*\(([^)]*)\)\s*\{").search(text, i)
        if not m:
            return
        depth, j = 1, m.end()
        while depth and j < n:
            c = text[j]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
            j += 1
        yield m.group(1), m.group(2).strip().strip('"'), m.end(), j - 1
        i = j


def _max_values(body: str, names: tuple[str, ...]) -> float | None:
    best = None
    for kind, _, b0, b1 in _groups(body):
        if kind in names:
            vm = re.search(r"values\s*\((.*?)\)\s*;", body[b0:b1], re.S)
            if vm:
                vals = [float(v) for v in _NUM.findall(vm.group(1))]
                if vals:
                    best = max(vals) if best is None else max(best, max(vals))
    return best


def read(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace")
    unit = re.search(r'time_unit\s*:\s*"1(\w+)"', text)
    scale = {"ps": 1.0, "ns": 1000.0}.get(unit.group(1) if unit else "ns", 1000.0)
    cell = next(((h, a, b0, b1) for h, a, b0, b1 in _groups(text) if h == "library"), None)
    lib_body = text[cell[2]:cell[3]] if cell else text
    out: dict[str, Any] = {}
    for kind, name, b0, b1 in _groups(lib_body):
        if kind != "cell":
            continue
        cbody = lib_body[b0:b1]
        for pk, pname, p0, p1 in _groups(cbody):
            if pk not in ("pin", "bus"):
                continue
            pbody = cbody[p0:p1]
            entry: dict[str, Any] = {}
            for tk, _, t0, t1 in _groups(pbody):
                if tk != "timing":
                    continue
                tb = pbody[t0:t1]
                ttype = re.search(r"timing_type\s*:\s*\"?(\w+)", tb)
                ttype = ttype.group(1) if ttype else "combinational"
                rel = re.search(r'related_pin\s*:\s*"?([\w\[\]]+)', tb)
                if ttype == "setup_rising":
                    v = _max_values(tb, ("rise_constraint", "fall_constraint"))
                    if v is not None:
                        entry["setup_ps"] = max(entry.get("setup_ps", -1e9), v * scale)
                elif ttype == "rising_edge":
                    v = _max_values(tb, ("cell_rise", "cell_fall"))
                    if v is not None:
                        entry["clk_to_out_ps"] = max(entry.get("clk_to_out_ps", -1e9), v * scale)
                elif ttype in ("combinational", "combinational_rise", "combinational_fall"):
                    v = _max_values(tb, ("cell_rise", "cell_fall"))
                    if v is not None:
                        entry.setdefault("through", {})
                        src = rel.group(1) if rel else "?"
                        entry["through"][src] = max(entry["through"].get(src, -1e9), v * scale)
            if entry:
                base = re.sub(r"\[\d+\]$", "", pname)
                prev = out.setdefault(base, {})
                for k, v in entry.items():
                    if k == "through":
                        prev.setdefault("through", {}).update(v)
                    else:
                        prev[k] = max(prev.get(k, -1e9), v)
    return out
