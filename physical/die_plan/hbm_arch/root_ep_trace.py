#!/usr/bin/env python3
"""Trace root idx-cluster core ports through the r18h5 as-built die netlist (transport stages hbfd_rly/pad/lh/lh0/land
are bitwise pass-through) to their real functional partners.  Output: json {inst.port: [{bit, dir, partner: inst.port[bit]|PORT|CONST, stages}]}"""
import re, sys, json, collections
src, out = sys.argv[1], sys.argv[2]
ROOT = sys.argv[3].split(",")
inst_re = re.compile(r"^\s{2}([A-Za-z_]\w*)\s+(?:#\(.*\)\s+)?([A-Za-z_]\w*)\s*\($")
port_re = re.compile(r"^\s+\.(\w+)\((.*)\),?$")
wire_re = re.compile(r"^\s*(?:input|output|inout)?\s*wire\s*(?:\[(\d+):(\d+)\])?\s*(\w+);?")
W = {}
insts = []
cur = None
with open(src) as f:
    for ln in f:
        m = wire_re.match(ln)
        if m and ("wire" in ln):
            nm = m.group(3)
            W[nm] = (int(m.group(1)), int(m.group(2))) if m.group(1) else (0, 0)
            continue
        if cur is None:
            m = inst_re.match(ln)
            if m and m.group(1) not in ("module",):
                cur = (m.group(1), m.group(2), {})
            continue
        if ln.strip().startswith(");"):
            insts.append(cur); cur = None; continue
        m = port_re.match(ln)
        if m:
            cur[2][m.group(1)] = m.group(2)

def bits(e):
    """LSB-first list of (net,idx) or None for constants."""
    e = e.strip()
    if not e:
        return []
    if e.startswith("{") and e.endswith("}"):
        inner = e[1:-1]
        m = re.match(r"^(\d+)\{(.*)\}$", inner.strip())
        if m:
            return bits(m.group(2)) * int(m.group(1))
        parts, d, s = [], 0, 0
        for i, c in enumerate(inner):
            if c == "{": d += 1
            elif c == "}": d -= 1
            elif c == "," and d == 0:
                parts.append(inner[s:i]); s = i + 1
        parts.append(inner[s:])
        r = []
        for p in reversed(parts):   # concat: last element = LSBs
            r += bits(p)
        return r
    m = re.match(r"^(\d+)'[sS]?([bdhBDH])([0-9a-fA-FxXzZ_]+)$", e)
    if m:
        return [None] * int(m.group(1))
    m = re.match(r"^(\w+)\[(\d+):(\d+)\]$", e)
    if m:
        hi, lo = int(m.group(2)), int(m.group(3))
        return [(m.group(1), i) for i in range(lo, hi + 1)]
    m = re.match(r"^(\w+)\[(\d+)\]$", e)
    if m:
        return [(m.group(1), int(m.group(2)))]
    if re.match(r"^\w+$", e):
        hi, lo = W.get(e, (0, 0))
        return [(e, i) for i in range(lo, hi + 1)]
    raise ValueError(e)

TR = re.compile(r"^hbfd_(rly|pad|lh|lh0|land|land0)(_|$)")
IO = {"rly": ("i", "o"), "pad": ("i", "o"), "lh": ("a", "b"), "lh0": ("a", "b"), "land": ("a", "b"), "land0": ("a", "b")}
fwd = collections.defaultdict(list)   # net bit -> [(kind, inst, port, k)]
back = {}                             # transport out bit -> (in bit, inst)
drv = {}                              # functional output net bit -> (inst, port, k) by naming inst__port
func = {}
for mod, nm, P in insts:
    m = TR.match(mod)
    if m:
        ip, op = IO[m.group(1)]
        a, b = bits(P.get(ip, "")), bits(P.get(op, ""))
        if len(b) > len(a) > 0:
            a = [a[k % len(a)] for k in range(len(b))]   # lh replicate: b = copies of a
        for k, (x, y) in enumerate(zip(a, b)):
            if y is not None:
                back[y] = (x, nm)
            if x is not None:
                fwd[x].append(("T", nm, y))
        continue
    func[nm] = (mod, P)
    for p, e in P.items():
        for k, x in enumerate(bits(e)):
            if x is None: continue
            if x[0] == f"{nm}__{p}":
                drv[x] = (nm, p, k)
            else:
                fwd[x].append(("F", nm, p, k))

def forward(x, st=0, seen=None):
    res = []
    for it in fwd.get(x, []):
        if it[0] == "T":
            if it[2] is not None:
                res += forward(it[2], st + 1)
        else:
            res.append((f"{it[1]}.{it[2]}[{it[3]}]", st))
    return res

def backward(x, st=0):
    while x in back:
        x2, _ = back[x]; st += 1
        if x2 is None:
            return ("CONST", st)
        x = x2
    if x in drv:
        i, p, k = drv[x]
        return (f"{i}.{p}[{k}]", st)
    return (f"NET:{x[0]}[{x[1]}]", st)

res = {}
for r in ROOT:
    mod, P = func[r]
    for p, e in P.items():
        bl = bits(e)
        rows = []
        for k, x in enumerate(bl):
            if x is None:
                rows.append(dict(bit=k, dir="in", partner="CONST", st=0)); continue
            if x[0] == f"{r}__{p}":
                rows.append(dict(bit=k, dir="out", partners=forward(x)))
            else:
                pt, st = backward(x)
                rows.append(dict(bit=k, dir="in", partner=pt, st=st))
        res[f"{r}.{p}"] = dict(module=mod, width=len(bl), rows=rows)
json.dump(res, open(out, "w"))
print("insts", len(insts), "func", len(func), "ports", len(res))
