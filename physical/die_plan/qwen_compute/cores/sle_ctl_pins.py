#!/usr/bin/env python3
"""QC-SLECTL-B 11-05: plan pin tables of the sle_ctl split children (delta_sle_ctl_split_1105.py).

Rings (ot_dp_clk_landing_cas wrapper masters): d[W-1:0] + fclk + t_rst_n on the face the band's parent pins enter, in
the parent pin order along that face; q[W-1:0] + clk + rst_n + ready + fault + strap_k on the opposite (inner) face.
ctl (qfd_dv_s5_ctl_repair4_leaf): each port bit on the child face toward its parent source / sink: the parent pin span of
the bus it lands from (x_*_i_q, pd12_*) or the output station it feeds (u_bout_<bus>, from the bound RTL), else the
type centre (u_rp, glue).  Pins sorted along each face by that target.  M5 ceiling: E/W pins M4, N/S pins M5, on the kit
track 0.012 + 0.048 k, step a multiple of 0.048 (>= 0.096).
"""
import re
from collections import defaultdict

LAYER = {"W": "M4", "E": "M4", "S": "M5", "N": "M5"}


def trk(v):
    return round(0.012 + 0.048 * round((v - 0.012) / 0.048), 3)


def face_xy(face, w, h, s):
    """pin location of along-face coordinate s on the face (core frame)."""
    return {"W": (0.042, trk(s)), "E": (round(w - 0.042, 3), trk(s)),
            "S": (trk(s), 0.048), "N": (trk(s), round(h - 0.048, 3))}[face]


def lay(names, face, w, h, lo=None, hi=None):
    """spread names (already ordered) centred on [lo, hi] (default: the whole face less 1 um ends)."""
    L = h if face in "WE" else w
    lo = 1.0 if lo is None else lo
    hi = L - 1.0 if hi is None else hi
    n = len(names)
    step = int((hi - lo) / max(n, 1) / 0.048) * 0.048
    step = min(step, 0.288)
    if n and step < 0.096 - 1e-9:
        raise SystemExit(f"PINS FAIL: {n} pins on face {face} span {hi - lo:.2f} um (step < 0.096)")
    p0 = (lo + hi) / 2 - (n - 1) * step / 2
    out = []
    for i, (nm, d) in enumerate(names):
        x, y = face_xy(face, w, h, p0 + i * step)
        out.append(dict(name=nm, dir=d, face=face, x=x, y=y, layer=LAYER[face]))
    return out


OPP = {"N": "S", "S": "N", "E": "W", "W": "E"}


def ring_pins(master, W, face, outline, order=None):
    """order: bit indices of d in increasing along-face coordinate of the parent pins (default 0..W-1)."""
    w, h = outline
    order = list(range(W)) if order is None else list(order)
    assert sorted(order) == list(range(W)), master
    half = len(order) // 2
    dn = [(f"d[{b}]", "in") for b in order]
    dn = dn[:half] + [("fclk", "in"), ("t_rst_n", "in")] + dn[half:]
    qn = [(f"q[{b}]", "out") for b in order]
    ctl = [("clk", "in"), ("rst_n", "in"), ("ready", "out"), ("fault", "out")] + [(f"strap_k[{k}]", "in") for k in range(6)]
    qn = qn[:half] + ctl + qn[half:]
    pins = lay(dn, face, w, h) + lay(qn, OPP[face], w, h)
    return dict(schema="opentallas.core_pins.v1", core=master, frame="core R0, origin (0,0)",
                source="sle_ctl_pins.py ring_pins (QC-SLECTL-B)", outline_um=list(outline), pins=pins,
                note=f"QC-SLECTL-B: ring child, d/fclk/t_rst_n on {face} (parent pin order), q/clk/rst_n/ready/fault/"
                     f"strap_k on {OPP[face]}; {LAYER[face]}, kit track 0.012 + 0.048 k")


def _concat_bits(expr):
    """MSB-first list of (net, bit) for a Verilog concatenation / select expression."""
    e = expr.strip()
    if e.startswith("{") and e.endswith("}"):
        e = e[1:-1]
    out = []
    for tok in [x.strip() for x in e.split(",") if x.strip()]:
        m = re.fullmatch(r"(\w+)\[(\d+):(\d+)\]", tok)
        if m:
            a, b = int(m.group(2)), int(m.group(3))
            rng = range(a, b - 1, -1) if a >= b else range(a, b + 1)
            out += [(m.group(1), i) for i in rng]
            continue
        m = re.fullmatch(r"(\w+)\[(\d+)\]", tok)
        if m:
            out.append((m.group(1), int(m.group(2))))
            continue
        out.append((tok, None))
    return out


def port_decls(src_text):
    """{port: (dir, width)} from a flat ANSI-free declaration list (input wire [a:b] name;)."""
    out = {}
    for m in re.finditer(r"^\s*(input|output)\s+wire\s+(?:\[(\d+):(\d+)\]\s*)?(\w+)\s*;", src_text, re.M):
        w = abs(int(m.group(2)) - int(m.group(3))) + 1 if m.group(2) else 1
        out[m.group(4)] = ("in" if m.group(1) == "input" else "out", w)
    return out


def ctl_targets(bound_text, inst, bus_xy, centre, decls):
    """{(port, bit): (x, y)} parent target per ctl port bit (bit None for 1-bit ports); bus_xy {bus: (x, y)}."""
    m = re.search(r"\n\s*\w+\s+" + re.escape(inst) + r"\s*\((.*?)\n\s*\);", bound_text, re.S)
    conns = dict(re.findall(r"\.(\w+)\((.*?)\),?\s*\n", m.group(1) + "\n"))
    assert set(conns) == set(decls), sorted(set(conns) ^ set(decls))
    sink = {}       # (net, bit) -> bus of the output station that takes it
    for sm in re.finditer(r"u_bout_(\w+)\s*\((.*?)\);", bound_text, re.S):
        d = re.search(r"\.d\((.*?)\), \.ea", sm.group(2), re.S)
        if d:
            for nb in _concat_bits(d.group(1)):
                sink.setdefault(nb, sm.group(1))
    tgt = {}
    for p, e in conns.items():
        wd = decls[p][1]
        bits = _concat_bits(e)
        if len(bits) == 1 and bits[0][1] is None and re.fullmatch(r"\w+", e.strip()):
            bits = [(e.strip(), i) for i in range(wd - 1, -1, -1)] if wd > 1 else [(e.strip(), 0)]
        assert len(bits) == wd, (p, len(bits), wd)
        for k, (net, bit) in enumerate(bits):
            bus = sink.get((net, bit)) if bit is not None else None
            if bus is None:
                mm = re.fullmatch(r"(?:pd\d+_)?(\w+?_i)(?:_q|_\d+)?", net)
                if mm and mm.group(1) in bus_xy:
                    bus = mm.group(1)
            tgt[(p, wd - 1 - k if wd > 1 else None)] = bus_xy.get(bus, centre)
    return tgt


def ctl_pins(master, origin, outline, tgt, port_dir):
    w, h = outline
    cx, cy = origin[0] + w / 2, origin[1] + h / 2
    by = defaultdict(list)
    for (p, b), (x, y) in tgt.items():
        if p in ("ck", "rst_n"):
            continue
        dx, dy = x - cx, y - cy
        if abs(dx) * h >= abs(dy) * w:
            f = "E" if dx > 0 else "W"
        else:
            f = "N" if dy > 0 else "S"
        s = y if f in "WE" else x
        by[f].append((s, p, -1 if b is None else b, f"{p}[{b}]" if b is not None else p, port_dir[p]))
    pins = []
    for f in "NSEW":
        L = by[f]
        L.sort()
        names = [(nm, d) for _, _, _, nm, d in L]
        if f == "S":   # clock + reset at the centre of the south face
            half = len(names) // 2
            names = names[:half] + [("ck", "in"), ("rst_n", "in")] + names[half:]
        pins += lay(names, f, w, h)
    return dict(schema="opentallas.core_pins.v1", core=master, frame="core R0, origin (0,0)",
                source="sle_ctl_pins.py ctl_pins (QC-SLECTL-B)", outline_um=list(outline), pins=pins,
                note="QC-SLECTL-B: each port bit on the face toward its parent source/sink (bus pin span or output "
                     "station); E/W M4, N/S M5, kit track 0.012 + 0.048 k")
