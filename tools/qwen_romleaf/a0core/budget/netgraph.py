#!/usr/bin/env python3
"""QC a0v8 10-24: flatten a Yosys gate netlist (1_2_yosys.v) into a startpoint -> endpoint logical graph.

Startpoints: sequential cell outputs, hard-child (macro) output pins, top input ports.
Endpoints:   sequential cell inputs (D/SE/SI/reset...), macro input pins, top output ports.
Combinational cells are transparent.  Clock pins (CLK of flops, clk of macros, clock tap ports) are excluded.

Output (pickle): dict(nodes=[(kind, name, master, pin)], edges=list of (start_idx, [end_idx...])) where kind in
{seq, macro, port}.  Names are backslash-stripped instance names, macro pins are 'inst/pin'.
"""
import collections
import pickle
import re
import sys

OUT_PINS = {"Y", "Q", "QN", "CON", "SN", "H", "L", "GCLK", "YN"}
CLK_PINS = {"CLK", "clk", "ck", "CK", "GCLK", "ENA"}
SEQ_RE = re.compile(r"^(DFF|SDF|DHL|DLL|ASYNC_DFF|ICG)")
TOK = re.compile(r"\\\S+|[A-Za-z_][A-Za-z0-9_$]*|\d+'[bhdBHD][0-9a-fA-FxXzZ_]+|\d+|\[|\]|:|\(|\)|\{|\}|,|;|\.|=|#")


def tokens(text):
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
    text = re.sub(r"//[^\n]*", " ", text)
    text = re.sub(r"\(\*.*?\*\)", " ", text, flags=re.S)
    return TOK.findall(text)


def parse(path):
    toks = tokens(open(path).read())
    mods = {}
    i = 0
    n = len(toks)
    while i < n:
        if toks[i] != "module":
            i += 1
            continue
        name = toks[i + 1].lstrip("\\")
        i += 2
        while toks[i] != ";":
            i += 1
        i += 1
        m = dict(ports={}, wires={}, insts=[], assigns=[])
        while toks[i] != "endmodule":
            t = toks[i]
            if t in ("input", "output", "inout", "wire", "reg"):
                kind = t
                i += 1
                rng = None
                if toks[i] == "signed":
                    i += 1
                if toks[i] == "[":
                    hi, lo = int(toks[i + 1]), int(toks[i + 3])
                    rng = (hi, lo)
                    i += 5
                while True:
                    nm = toks[i].lstrip("\\")
                    m["wires"][nm] = rng
                    if kind in ("input", "output", "inout"):
                        m["ports"][nm] = (kind, rng)
                    i += 1
                    if toks[i] == ",":
                        i += 1
                        continue
                    break
                while toks[i] != ";":
                    i += 1
                i += 1
            elif t == "assign":
                j = i + 1
                lhs, j = expr(toks, j)
                assert toks[j] == "=", toks[j - 3:j + 3]
                rhs, j = expr(toks, j + 1)
                m["assigns"].append((lhs, rhs))
                i = j + 1
            else:
                master = t.lstrip("\\")
                j = i + 1
                if toks[j] == "#":  # parameters (not expected in gate netlists)
                    depth = 0
                    j += 1
                    while True:
                        if toks[j] == "(":
                            depth += 1
                        elif toks[j] == ")":
                            depth -= 1
                            if depth == 0:
                                j += 1
                                break
                        j += 1
                iname = toks[j].lstrip("\\")
                j += 1
                assert toks[j] == "(", (master, iname, toks[j:j + 5])
                j += 1
                conns = {}
                while toks[j] != ")":
                    if toks[j] == ",":
                        j += 1
                        continue
                    assert toks[j] == ".", toks[j - 3:j + 5]
                    pin = toks[j + 1].lstrip("\\")
                    assert toks[j + 2] == "("
                    if toks[j + 3] == ")":
                        conns[pin] = []
                        j += 4
                        continue
                    e, j = expr(toks, j + 3)
                    assert toks[j] == ")", toks[j - 3:j + 3]
                    conns[pin] = e
                    j += 1
                j += 1
                assert toks[j] == ";"
                m["insts"].append((master, iname, conns))
                i = j + 1
        mods[name] = m
        i += 1
    return mods


def expr(toks, j):
    """returns list of bit atoms (MSB first): ('net', name, idx|None) or ('const', v)"""
    t = toks[j]
    if t == "{":
        out = []
        j += 1
        while toks[j] != "}":
            if toks[j] == ",":
                j += 1
                continue
            e, j = expr(toks, j)
            out.extend(e)
        return out, j + 1
    m = re.match(r"(\d+)'([bhdBHD])([0-9a-fA-FxXzZ_]+)", t)
    if m:
        w = int(m.group(1))
        base = {"b": 2, "h": 16, "d": 10}[m.group(2).lower()]
        s = m.group(3).replace("_", "")
        try:
            v = int(s, base)
            bits = [("const", (v >> k) & 1) for k in range(w - 1, -1, -1)]
        except ValueError:
            bits = [("const", "x")] * w
        return bits, j + 1
    if re.match(r"^\d+$", t):
        return [("const", int(t) & 1)], j + 1
    nm = t.lstrip("\\")
    j += 1
    if j < len(toks) and toks[j] == "[":
        a = int(toks[j + 1])
        if toks[j + 2] == ":":
            b = int(toks[j + 3])
            j += 5
            step = -1 if a >= b else 1
            return [("net", nm, k) for k in range(a, b + step, step)], j
        return [("net", nm, a)], j + 3
    return [("net", nm, "ALL")], j


def bits_of(mod, atom):
    if atom[0] == "const":
        return [atom]
    _, nm, idx = atom
    if idx == "ALL":
        rng = mod["wires"].get(nm)
        if rng is None:
            return [("net", nm, None)]
        hi, lo = rng
        step = -1 if hi >= lo else 1
        return [("net", nm, k) for k in range(hi, lo + step, step)]
    return [atom]


class Flat:
    def __init__(self, mods, top, macro_dirs):
        self.mods = mods
        self.macro_dirs = macro_dirs  # master -> {pin: dir}
        self.uf = {}
        self.pins = []  # (net_key, kind, owner, master, pin, dir)
        self.top = top
        self.walk(top, "", {})

    def find(self, a):
        uf = self.uf
        r = a
        while uf.get(r, r) != r:
            r = uf[r]
        while uf.get(a, a) != r:
            nx = uf[a]
            uf[a] = r
            a = nx
        return r

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.uf[ra] = rb

    def key(self, pfx, mod, b, portmap):
        if b[0] == "const":
            return ("const", b[1])
        _, nm, idx = b
        if (nm, idx) in portmap:
            return portmap[(nm, idx)]
        return (pfx + nm, idx)

    def walk(self, mname, pfx, portmap):
        mod = self.mods[mname]
        for lhs, rhs in mod["assigns"]:
            lb = [x for a in lhs for x in bits_of(mod, a)]
            rb = [x for a in rhs for x in bits_of(mod, a)]
            if len(lb) != len(rb):
                rb = rb[-len(lb):] if len(rb) > len(lb) else [("const", 0)] * (len(lb) - len(rb)) + rb
            for a, b in zip(lb, rb):
                self.union(self.key(pfx, mod, a, portmap), self.key(pfx, mod, b, portmap))
        for master, iname, conns in mod["insts"]:
            full = pfx + iname
            if master in self.mods:
                sub = self.mods[master]
                pm = {}
                for pin, e in conns.items():
                    bl = [x for a in e for x in bits_of(mod, a)]
                    kind, rng = sub["ports"][pin]
                    if rng is None:
                        sbits = [(pin, None)]
                    else:
                        hi, lo = rng
                        step = -1 if hi >= lo else 1
                        sbits = [(pin, k) for k in range(hi, lo + step, step)]
                    for sb, b in zip(sbits[-len(bl):] if len(bl) < len(sbits) else sbits, bl[-len(sbits):]):
                        pm[sb] = self.key(pfx, mod, b, portmap)
                self.walk(master, full + "/", pm)
                continue
            for pin, e in conns.items():
                bl = [x for a in e for x in bits_of(mod, a)]
                if master in self.macro_dirs:
                    d = self.macro_dirs[master].get(pin)
                    if d is None:
                        # bus pin: macro pins are bit-blasted pin[k]
                        for k, b in enumerate(reversed(bl)):
                            dd = self.macro_dirs[master].get(f"{pin}[{k}]")
                            self.pins.append((self.key(pfx, mod, b, portmap), "macro", full, master, f"{pin}[{k}]", dd))
                        continue
                    for b in bl:
                        self.pins.append((self.key(pfx, mod, b, portmap), "macro", full, master, pin, d))
                else:
                    d = "OUTPUT" if pin in OUT_PINS else "INPUT"
                    kind = "seq" if SEQ_RE.match(master) else "comb"
                    for b in bl:
                        self.pins.append((self.key(pfx, mod, b, portmap), kind, full, master, pin, d))


def build(path, top, macro_dirs, clock_ports):
    mods = parse(path)
    f = Flat(mods, top, macro_dirs)
    tm = mods[top]
    for p, (kind, rng) in tm["ports"].items():
        bits = [None] if rng is None else list(range(rng[0], rng[1] + (-1 if rng[0] >= rng[1] else 1), -1 if rng[0] >= rng[1] else 1))
        for k in bits:
            nm = p if k is None else f"{p}[{k}]"
            f.pins.append(((p, k), "port", nm, "PORT", p, "OUTPUT" if kind == "input" else "INPUT"))
    # nets
    drv = {}
    sinks = collections.defaultdict(list)
    for idx, (k, kind, owner, master, pin, d) in enumerate(f.pins):
        if k[0] == "const":
            continue
        r = f.find(k)
        if d == "OUTPUT":
            drv[r] = idx
        else:
            sinks[r].append(idx)
    # comb cell graph: comb output pin -> comb cell -> its input pins' nets
    cell_in = collections.defaultdict(list)   # comb cell -> input pin idx
    cell_out = collections.defaultdict(list)  # comb cell -> output nets
    for idx, (k, kind, owner, master, pin, d) in enumerate(f.pins):
        if kind == "comb":
            if d == "OUTPUT":
                if k[0] != "const":
                    cell_out[owner].append(f.find(k))
            else:
                cell_in[owner].append(idx)
    return f, drv, sinks, cell_out


def endpoints_bbox(f, drv, sinks, cell_out, pos, skip_clock=True):
    """for each startpoint pin idx: (bbox of reached endpoints, count).  pos(idx) -> (x, y) or None."""
    memo = {}

    def net_bb(r, stack_guard):
        if r in memo:
            return memo[r]
        memo[r] = None  # loop guard
        res = [1e9, 1e9, -1e9, -1e9, 0, -1e9, -1e9, -1e9, -1e9]
        for s in sinks.get(r, ()):
            k, kind, owner, master, pin, d = f.pins[s]
            if kind == "comb":
                for o in cell_out[owner]:
                    sub = net_bb(o, stack_guard + 1)
                    if sub:
                        res[0] = min(res[0], sub[0]); res[1] = min(res[1], sub[1])
                        res[2] = max(res[2], sub[2]); res[3] = max(res[3], sub[3]); res[4] += sub[4]
                        for q in range(5, 9):
                            res[q] = max(res[q], sub[q])
                continue
            if skip_clock and pin in CLK_PINS:
                continue
            p = pos(s)
            if p is None:
                continue
            res[0] = min(res[0], p[0]); res[1] = min(res[1], p[1])
            res[2] = max(res[2], p[0]); res[3] = max(res[3], p[1]); res[4] += 1
            res[5] = max(res[5], p[0] + p[1]); res[6] = max(res[6], p[0] - p[1])
            res[7] = max(res[7], -p[0] + p[1]); res[8] = max(res[8], -p[0] - p[1])
        memo[r] = res
        return res

    sys.setrecursionlimit(100000)
    out = {}
    for r, d in drv.items():
        k, kind, owner, master, pin, dd = f.pins[d]
        if kind == "comb":
            continue
        out[d] = net_bb(r, 0)
    return out


if __name__ == "__main__":
    import json
    path, top, macro_json, outp = sys.argv[1:5]
    mp = json.load(open(macro_json))
    macro_dirs = {m: {p[0]: p[1] for p in v["pins"]} for m, v in mp.items()}
    f, drv, sinks, cell_out = build(path, top, macro_dirs, [])
    pickle.dump(dict(pins=f.pins, uf=None, drv={str(k): v for k, v in drv.items()}), open(outp, "wb"))
    print("pins", len(f.pins), "nets", len(drv))
