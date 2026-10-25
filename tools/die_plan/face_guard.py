"""Boundary-register guard on the Yosys netlist of a partition kit (CP1-R10, COORD 10-24).

    python3 tools/die_plan/face_guard.py NETLIST.v [--top MOD] [--pins pins.json] [--out face_guard.json]   # exit 1 = FAIL

Every planned face register (R2 face flops, one per pin bit of the R5 bit-level census) must survive synthesis as its
OWN flop:
  - an output port bit is driven by a flop (Q/QN, through at most MAX_CHAIN single-fanout buffers / inverters) whose
    output net reaches nothing but that port;
  - an input port bit loads exactly one cell pin, which leads (through single-fanout buffers / inverters) to the D pin
    of a flop.
Failure classes (the bugs this guards against): `merged` (Yosys opt_merge folded identical boundary flops of different
buses into one flop driving several ports: CP1 r6 u_bout_x_o0.q[718] -> frame_int_o0[892], S81-P9 shared epoch flops),
`shared` (the face flop also feeds internal logic), `const` (constant-D flop removed, port tied), `dropped` (input bit
with no register: its q was unused), `feedthrough` (port wired to port), `unregistered` (combinational logic between
the port and its flop).
The source-side prevention is gen_rtl.CELLS: ot_dp_st / ot_dp_ste / ot_dp_ep carry (* keep_hierarchy, keep *).
run_kit.sh runs this guard right after `make synth` and stops the kit on FAIL.
"""
import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

MAX_CHAIN = 3
OUT_PINS = {"Y", "Q", "QN", "H", "L", "CON", "SN", "Z", "ZN", "O"}
# Clocks and the reset/START *inputs* (arst_n / rst_n / start_i: root synchroniser or typed control) are not face
# registers.  The registered wavefront OUTS rst_o_<k> / start_o_<k> ARE partition pins and are checked like data: one
# dedicated relay per pin (reset_tree.py out relays; owner rule: register every partition pin, no shared fanout).
SKIP_RE = r"^(clk(_t[0-9]+|_c[0-9]+)?|arst_n|rst_n|start_i)$"


def is_ff(master):
    return "DFF" in master.upper()


def is_buf(master):
    m = master.upper()
    return m.startswith(("BUF", "INV", "HB", "$_NOT_", "$_BUF_"))


# ---- structural Verilog (Yosys write_verilog) ---------------------------------------------------------------------
_TOK = re.compile(r"\s*(?:(\\\S+)|([A-Za-z_][A-Za-z0-9_$]*)|(\d+'[bhdoBHDO][0-9a-fA-FxXzZ_]+)|(\d+)|(.))", re.S)


def _tokens(text):
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
    text = re.sub(r"\(\*.*?\*\)", " ", text, flags=re.S)
    text = re.sub(r"//[^\n]*", " ", text)
    pos, n, out = 0, len(text), []
    while pos < n:
        m = _TOK.match(text, pos)
        if not m or m.end() == pos:
            break
        pos = m.end()
        esc, ident, const, num, ch = m.groups()
        if esc:
            out.append(("id", esc[1:]))
        elif ident:
            out.append(("id", ident))
        elif const:
            out.append(("const", const))
        elif num:
            out.append(("num", num))
        elif ch and not ch.isspace():
            out.append(("p", ch))
    return out


def _const_bits(c):
    w, v = c.split("'")
    w, base, digits = int(w), v[0].lower(), v[1:].replace("_", "")
    if any(ch in "xXzZ" for ch in digits):
        return ["CONST_X"] * w
    val = int(digits, {"b": 2, "h": 16, "d": 10, "o": 8}[base])
    return [f"CONST_{(val >> i) & 1}" for i in range(w - 1, -1, -1)]     # msb first


class Module:
    def __init__(self, name):
        self.name, self.ports, self.dirs, self.wires = name, [], {}, {}
        self.cells, self.assigns = [], []        # cells: (type, inst, {pin: [bits msb..lsb]})


def parse(text):
    toks = _tokens(text)
    mods, i = {}, 0

    def expect(v):
        nonlocal i
        if toks[i][1] != v:
            raise ValueError(f"expected {v} got {toks[i]} near token {i}")
        i += 1

    def rng():
        nonlocal i
        if toks[i] == ("p", "["):
            i += 1
            a = int(toks[i][1])
            i += 2
            b = int(toks[i][1])
            i += 2
            return a, b
        return None

    while i < len(toks):
        if toks[i] != ("id", "module"):
            i += 1
            continue
        i += 1
        M = Module(toks[i][1])
        i += 1
        if toks[i] == ("p", "("):
            while toks[i] != ("p", ")"):
                if toks[i][0] == "id":
                    M.ports.append(toks[i][1])
                i += 1
            i += 1
        expect(";")

        def expr():
            """-> bits msb first (names 'w' or 'w[i]', or CONST_*)."""
            nonlocal i
            t = toks[i]
            if t == ("p", "{"):
                i += 1
                bits = []
                while toks[i] != ("p", "}"):
                    if toks[i] == ("p", ","):
                        i += 1
                        continue
                    bits += expr()
                i += 1
                return bits
            if t[0] == "const":
                i += 1
                return _const_bits(t[1])
            if t[0] == "num":
                i += 1
                return _const_bits(f"32'd{t[1]}")
            name = t[1]
            i += 1
            if toks[i] == ("p", "["):
                i += 1
                a = int(toks[i][1])
                i += 1
                if toks[i] == ("p", ":"):
                    i += 1
                    b = int(toks[i][1])
                    i += 2
                    step = -1 if a >= b else 1
                    return [f"{name}[{k}]" for k in range(a, b + step, step)]
                i += 1
                return [f"{name}[{a}]"]
            r = M.wires.get(name)
            if r is None:
                return [name]
            a, b = r
            step = -1 if a >= b else 1
            return [f"{name}[{k}]" for k in range(a, b + step, step)]

        while toks[i] != ("id", "endmodule"):
            t = toks[i]
            if t[0] == "id" and t[1] in ("input", "output", "inout", "wire", "reg"):
                kind = t[1]
                i += 1
                if toks[i] in (("id", "wire"), ("id", "reg"), ("id", "signed")):
                    i += 1
                r = rng()
                while True:
                    nm = toks[i][1]
                    i += 1
                    if r:
                        M.wires[nm] = r
                    if kind in ("input", "output", "inout"):
                        M.dirs[nm] = kind
                    if toks[i] == ("p", ","):
                        i += 1
                        continue
                    break
                expect(";")
            elif t == ("id", "assign"):
                i += 1
                lhs = expr()
                expect("=")
                rhs = expr()
                expect(";")
                M.assigns.append((lhs, rhs))
            elif t[0] == "id":
                typ = t[1]
                i += 1
                if toks[i] == ("p", "#"):                  # parameters (not in Yosys netlists, but skip them)
                    d = 0
                    i += 1
                    while True:
                        d += toks[i] == ("p", "(")
                        d -= toks[i] == ("p", ")")
                        i += 1
                        if d == 0:
                            break
                inst = toks[i][1]
                i += 1
                expect("(")
                conns = {}
                while toks[i] != ("p", ")"):
                    if toks[i] == ("p", ","):
                        i += 1
                        continue
                    expect(".")
                    pin = toks[i][1]
                    i += 1
                    expect("(")
                    conns[pin] = expr() if toks[i] != ("p", ")") else []
                    expect(")")
                i += 1
                expect(";")
                M.cells.append((typ, inst, conns))
            else:
                i += 1
        i += 1
        mods[M.name] = M
    return mods


def _bits_of(M, name):
    r = M.wires.get(name)
    if r is None:
        return [name]
    a, b = r
    step = -1 if a >= b else 1
    return [f"{name}[{k}]" for k in range(a, b + step, step)]


class Flat:
    """flattened bit-level connectivity: union-find over net bits, std cells with pin directions."""

    def __init__(self, mods, top):
        self.par = {}
        self.cells = []        # (master, path, {pin: (dir, [netbits])})
        self._flat(mods, top, "", None)

    def find(self, x):
        p = self.par.setdefault(x, x)
        while p != self.par.setdefault(p, p):
            self.par[p] = self.par[self.par[p]]
            p = self.par[p]
        self.par[x] = p
        return p

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            if rb.startswith("CONST_"):
                ra, rb = rb, ra
            self.par[rb] = ra

    def _flat(self, mods, mname, pfx, portmap):
        M = mods[mname]

        def net(b):
            if b.startswith("CONST_"):
                return b
            return pfx + b

        if portmap is not None:
            for p in M.ports:
                for b, outer in zip(_bits_of(M, p), portmap.get(p, [])):
                    self.union(net(b), outer)
        for lhs, rhs in M.assigns:
            for a, b in zip(lhs[::-1], rhs[::-1]):
                self.union(net(a), net(b))
        for typ, inst, conns in M.cells:
            path = pfx + inst
            if typ in mods:
                sub = mods[typ]
                pm = {}
                for p, bits in conns.items():
                    w = len(_bits_of(sub, p))
                    bits = [net(b) for b in bits]
                    pm[p] = (["CONST_X"] * (w - len(bits)) + bits)[-w:] if bits else []
                self._flat(mods, typ, path + "/", pm)
            else:
                pins = {p: ("out" if p in OUT_PINS else "in", [net(b) for b in bits]) for p, bits in conns.items()}
                self.cells.append((typ, path, pins))


def read_ft1(path):
    """slot names with ONE station from a kit's ft_stations.txt (`slot stations in_face out_face ...`)."""
    out = set()
    for ln in Path(path).read_text().splitlines():
        f = ln.split()
        if f and not f[0].startswith("#") and len(f) >= 2 and f[1] == "1":
            out.add(f[0])
    return out


def _ft1_pair(bs, ft1):
    """True when the bits are exactly S_i[k] and S_o[k] of one 1-station ft slot S: that slot's single station register
    is by plan both the in-face and the out-face register (ELEM-S81 10-24: slice_station types)."""
    if len(bs) != 2:
        return False
    m = [re.match(r"^(.+)_([io])(\[\d+\])?$", b) for b in bs]
    return (all(m) and m[0].group(1) == m[1].group(1) and m[0].group(1) in ft1 and m[0].group(3) == m[1].group(3)
            and {m[0].group(2), m[1].group(2)} == {"i", "o"})


STRAP_RE = re.compile(r"^strap_[A-Za-z0-9_]+$")   # = straps.STRAP_RE (kept inline: kits copy this file alone)


def strap_list(names):
    """declared ID strap bus names (OWNER 10-25 option B rule 1: strap_*, unique); anything else -> ValueError"""
    sl = list(names or [])
    bad = [n for n in sl if not isinstance(n, str) or not STRAP_RE.match(n)]
    if bad or len(set(sl)) != len(sl):
        raise ValueError(f"straps must be unique strap_<id> names (OWNER 10-25 option B): {bad or sl}")
    return sl


def kit_strap_list(kitdir):
    """the kit's declared straps: straps.json, else sdc_lint.json "straps", else core.json report.straps
    kind == id_strap (same order as straps.kit_straps).  [] when none."""
    kd = Path(kitdir)
    if (kd / "straps.json").is_file():
        d = json.loads((kd / "straps.json").read_text())
        return strap_list(d.get("straps", []) if isinstance(d, dict) else d)
    if (kd / "sdc_lint.json").is_file():
        s = json.loads((kd / "sdc_lint.json").read_text()).get("straps")
        if s:
            return strap_list(s)
    if (kd / "core.json").is_file():
        rep = (json.loads((kd / "core.json").read_text()).get("report") or {}).get("straps") or []
        return strap_list([x["port"] for x in rep if isinstance(x, dict) and x.get("kind") == "id_strap"])
    return []


def guard(text, top=None, skip_re=SKIP_RE, pins=None, ft1=(), straps=()):
    """straps: declared ID strap ports (OWNER 10-25 option B, straps.py): quasi-static strap_* inputs tied at the
    parent need no pin register -> exempt (recorded in the result); any other name is refused (ValueError)."""
    if straps:
        sl = strap_list(straps)
        skip_re = r"(?:" + skip_re + r")|^(?:" + "|".join(re.escape(x) for x in sl) + r")$"
        if pins is not None:
            pins = [x for x in pins if str(x.get("bus")) not in set(sl)]
    mods = parse(text)
    if top is None:
        used = {typ for M in mods.values() for typ, _, _ in M.cells}
        tops = [m for m in mods if m not in used]
        if len(tops) != 1:
            raise ValueError(f"cannot pick the top module: {tops}")
        top = tops[0]
    T = mods[top]
    F = Flat(mods, top)
    drv, loads = defaultdict(list), defaultdict(list)
    for ci, (m, path, pp) in enumerate(F.cells):
        for p, (d, bits) in pp.items():
            for b in bits:
                r = F.find(b)
                (drv if d == "out" else loads)[r].append((ci, p))
    port_root = {}
    for p in T.ports:
        for b in _bits_of(T, p):
            port_root[b] = F.find(b)
    roots_ports = defaultdict(list)
    for b, r in port_root.items():
        roots_ports[r].append(b)
    res = dict(top=top, checked=0, ok=0, fails=defaultdict(list), flops={}, straps_exempt=sorted(straps or ()))
    claimed = defaultdict(list)

    def fail(cls, b, why):
        res["fails"][cls].append(f"{b}: {why}")

    for x in (straps or ()):                     # an exempt strap must be an input port of this block (rule 1)
        if T.dirs.get(x) != "input":
            fail("strap", x, f"declared ID strap is not an input port ({T.dirs.get(x)})")
    for p in T.ports:
        if re.match(skip_re, p):
            continue
        d = T.dirs.get(p)
        for b in _bits_of(T, p):
            res["checked"] += 1
            r = port_root[b]
            others = [x for x in roots_ports[r] if x != b]
            if others:
                fail("feedthrough", b, f"wired to port(s) {others[:3]}")
                continue
            if r.startswith("CONST_"):
                fail("const", b, f"tied {r}")
                continue
            if d == "output":
                cur, chain, ff = r, [], None
                ok = True
                for _ in range(MAX_CHAIN + 1):
                    if len(drv[cur]) != 1:
                        fail("unregistered", b, f"{len(drv[cur])} drivers")
                        ok = False
                        break
                    expect = 0 if cur == r else 1       # the port net feeds only the port; a chain net one stage
                    if len(loads[cur]) != expect:
                        fail("shared", b, f"net {cur} has {len(loads[cur]) - expect} loads besides the port chain")
                        ok = False
                        break
                    ci, pin = drv[cur][0]
                    m, path, pp = F.cells[ci]
                    if is_ff(m):
                        ff = (ci, path)
                        break
                    if not is_buf(m):
                        fail("const" if m.upper().startswith("TIE") else "unregistered", b, f"driven by {m} {path}")
                        ok = False
                        break
                    ins = [v for k, (dd, v) in pp.items() if dd == "in"]
                    if len(ins) != 1 or len(ins[0]) != 1:
                        fail("unregistered", b, f"buffer {path} pins")
                        ok = False
                        break
                    chain.append(path)
                    cur = F.find(ins[0][0])
                    if cur in roots_ports:
                        fail("feedthrough", b, f"buffered from port {roots_ports[cur][0]}")
                        ok = False
                        break
                if not ok:
                    continue
                if ff is None:
                    fail("unregistered", b, f"no flop within {MAX_CHAIN} buffers")
                    continue
            else:
                cur, ff, ok = r, None, True
                for _ in range(MAX_CHAIN + 1):
                    ld = loads[cur]
                    if not ld:
                        fail("dropped", b, f"no load on {cur} (register removed)")
                        ok = False
                        break
                    if len(ld) != 1:
                        fail("shared", b, f"{len(ld)} loads on {cur}")
                        ok = False
                        break
                    ci, pin = ld[0]
                    m, path, pp = F.cells[ci]
                    if is_ff(m):
                        if pin != "D":
                            fail("unregistered", b, f"reaches {path}.{pin}, not D")
                            ok = False
                        else:
                            ff = (ci, path)
                        break
                    if not is_buf(m):
                        fail("unregistered", b, f"loads {m} {path}")
                        ok = False
                        break
                    outs = [v for k, (dd, v) in pp.items() if dd == "out"]
                    cur = F.find(outs[0][0])
                if not ok:
                    continue
                if ff is None:
                    fail("unregistered", b, f"no flop within {MAX_CHAIN} buffers")
                    continue
            claimed[ff[0]].append(b)
            res["flops"][b] = ff[1]
            res["ok"] += 1
    for ci, bs in claimed.items():
        if len(bs) > 1 and _ft1_pair(bs, ft1):
            res["ft1_stations"] = res.get("ft1_stations", 0) + 1
            continue
        if len(bs) > 1:
            for b in bs:
                fail("merged", b, f"flop {F.cells[ci][1]} also registers {[x for x in bs if x != b][:3]}")
            res["ok"] -= len(bs)
    if pins is not None:
        want = {x['bus'] if x.get('bit') is None else f"{x['bus']}[{x['bit']}]" for x in pins}
        have = {b for p in T.ports if not re.match(skip_re, p) for b in _bits_of(T, p)}
        for b in sorted(want - have)[:50]:
            fail("missing_port", b, "planned pin bit not a netlist port")
        miss = len(want - have)
        res["planned_bits"] = len(want)
        res["missing_ports"] = miss
    res["fails"] = {k: v for k, v in res["fails"].items()}
    nf = sum(len(v) for v in res["fails"].values())
    res["fail_counts"] = {k: len(v) for k, v in res["fails"].items()}
    res["fails"] = {k: v[:50] for k, v in res["fails"].items()}
    empty = pins is not None and not res.get("planned_bits") and res["checked"] == 0    # a planned port-less type
    res["verdict"] = "PASS" if nf == 0 and (res["checked"] > 0 or empty) else "FAIL"
    res["flops"] = dict(list(res["flops"].items())[:20])
    return res


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("netlist")
    ap.add_argument("--top")
    ap.add_argument("--pins")
    ap.add_argument("--out")
    ap.add_argument("--ft", help="kit ft_stations.txt (default: beside --pins): 1-station slots share one register")
    ap.add_argument("--straps", help="kit straps.json (default: beside --pins): declared ID straps, exempt")
    a = ap.parse_args(argv)
    stf = a.straps or (str(Path(a.pins).parent) if a.pins else None)
    sl = kit_strap_list(Path(stf).parent if stf.endswith(".json") else stf) if stf else []
    pins = json.loads(Path(a.pins).read_text()) if a.pins else None
    ftf = a.ft or (str(Path(a.pins).with_name("ft_stations.txt")) if a.pins else None)
    ft1 = read_ft1(ftf) if ftf and Path(ftf).exists() else set()
    r = guard(Path(a.netlist).read_text(), a.top, pins=pins, ft1=ft1, straps=sl)
    r["netlist"] = a.netlist
    if a.out:
        Path(a.out).write_text(json.dumps(r, indent=1) + "\n")
    print(f"FACE_GUARD {r['verdict']} top {r['top']} bits {r['checked']} ok {r['ok']} fails {r['fail_counts']}")
    return 0 if r["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
