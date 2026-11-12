#!/usr/bin/env python3
"""HBM-HUB-RTL-1 11-11 (tag hbm-rd1-bind): core pin cycles as a BIND-side input.

A hard core whose recipe adds edges at its own output pins (a pin-cycle row of plan_of_record/<die>/corelat/
cycles_*.tsv, e.g. the vecd4ae rd1 read stage: rr0..rr4 / pr / status[16:0] +1) changes every fixed-latency consumer
of those pins, but the bind sees only lane depths: the added edge is inside the leaf.  This module reads the rows and
answers "how many core-internal edges does this source pin add" so the die hook (param_regen) and the latency-consumer
check (latency_consumers.py) can add them.  Default: no asbuilt.core_pin_cycles -> nothing changes (every bank
without the rd1 recipe is unchanged).

asbuilt.core_pin_cycles = [{"tsv": path (repo-relative or absolute), "core": core name in the TSV (column 1),
                            "module": as-built leaf master regex, "inst": optional leaf path regex}]
TSV columns: core, sub_block, port_or_bus (comma list; name, name[i], name[hi:lo]), dir, added_cycles, note.
"""
import csv
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
_TOK = re.compile(r"^\s*([A-Za-z_]\w*)\s*(?:\[\s*(\d+)\s*(?::\s*(\d+)\s*)?\])?\s*$")


def _ports(spec):
    """'rr0,status[16:0]' -> [(name, lo, hi)] (lo/hi None = all bits)"""
    out = []
    for t in spec.split(","):
        if not t.strip():
            continue
        m = _TOK.match(t)
        if not m:
            raise ValueError(f"core_pin_cycles: bad port token {t!r}")
        n, a, b = m.group(1), m.group(2), m.group(3)
        if a is None:
            out.append((n, None, None))
        else:
            hi, lo = int(a), int(b if b is not None else a)
            out.append((n, min(lo, hi), max(lo, hi)))
    return out


def load(ab, base=REPO):
    """-> [rule]; rule = dict(module=re, inst=re|None, rows=[(name, lo, hi, added)], src=str)"""
    rules = []
    for e in (ab or {}).get("core_pin_cycles", []) or []:
        p = Path(e["tsv"])
        p = p if p.is_absolute() else Path(base) / p
        rows = []
        with open(p, newline="") as f:
            for r in csv.DictReader(f, delimiter="\t"):
                if r.get("core") != e["core"]:
                    continue
                k = int(r["added_cycles"])
                for n, lo, hi in _ports(r["port_or_bus"]):
                    rows.append((n, lo, hi, k))
        if not rows:
            raise ValueError(f"core_pin_cycles: no rows for core {e['core']!r} in {p}")
        rules.append(dict(module=re.compile(e["module"]), inst=re.compile(e["inst"]) if e.get("inst") else None,
                          rows=rows, src=f"{p.name}:{e['core']}"))
    return rules


def added(rules, path, module, port, bit):
    """core-internal edges added at source pin path.port[bit] (0 when no rule names it)"""
    best = 0
    for r in rules:
        if not r["module"].fullmatch(module or "") or (r["inst"] and not r["inst"].fullmatch(path)):
            continue
        hit = None
        for n, lo, hi, k in r["rows"]:
            if n == port and (lo is None or lo <= bit <= hi):
                hit = k if hit is None else max(hit, k)
        if hit:
            best = max(best, hit)
    return best


def added_port(rules, path, module, port):
    """max edges added at any bit of source pin path.port (a port-level view for bus-group members)"""
    best = 0
    for r in rules:
        if not r["module"].fullmatch(module or "") or (r["inst"] and not r["inst"].fullmatch(path)):
            continue
        best = max([best] + [k for n, lo, hi, k in r["rows"] if n == port])
    return best


VECTOR = {"RD_LAT"}   # xload RD_LAT: scalar, or per-bank vector (element b = byte b, RD_LAT[63:8] != 0)


def plus(v, x, param=None):
    """v + x; a per-bank vector parameter adds x to every nonzero element"""
    if not isinstance(v, int) or not x:
        return v
    if param in VECTOR and v >> 8:
        out = 0
        for b in range(8):
            e = (v >> (8 * b)) & 255
            e = e + x if e else 0
            if e > 255:
                raise ValueError(f"{param}: element {b} overflows ({e})")
            out |= e << (8 * b)
        return out
    return v + x


def source_of(d):
    """bind sink tuple -> (source cell index, source port, source bit) or None"""
    if d and d[0] == "x":
        return d[2], d[3], d[4]
    if d and d[0] == "int":
        return d[1], d[2], d[3]
    return None


def sink_pins(ctx, rules, ci, port):
    """{sink bit: added} over the sink bits of cell ci port (intra-partition and crossing sources alike)"""
    F, out = ctx.F, {}
    for (c, pn, i), d in ctx.sinks.items():
        if c != ci or pn != port:
            continue
        s = source_of(d)
        if s is None:
            continue
        sc = F.cells[s[0]]
        out[i] = added(rules, sc.path, sc.module, s[1], s[2])
    return out
