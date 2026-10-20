#!/usr/bin/env python3
"""QW-CLUSTER3/CB16 (LEAD-QW 12:15 binding decision): the CB16 parent rebuilt as clock REGIONS joined only by LANDED
crossings made of the CLOSED hard halves qfd_c_land_{w,r}{257,258}_narrow, column stations = the CLOSED
qfd_c_xstnw_safe view, relays = the CLOSED qfd_c_stn514 / qfd_c_stn516 views.  A0 = the diagnostic stand-in
(no qualified A0 view exists) -- every A0 pin / timing figure is a stand-in figure.

The full 16-region parent is too large for one first gate, so this generator emits ONE REPRESENTATIVE INTERIOR REGION
(c1r1 of the 4 x 4 block: one A0, its column run, its four reduction legs and the DV feedthrough leg) PLUS every
crossing that touches it, both halves (the neighbour-side half on the neighbour's clock port).  The region's netlist
is derived from qfd_c_b16_dv_fabric.sv region c1r1 (same crossings, same bus widths); stage counts follow the new
geometry (every single-cycle wire <= 405 um, checked per bit on the real LEF pins below) and every added stage is
priced in results/arch/qwen_cluster_1017/q_cluster16/reg1/plan.json.

Variants (one RTL file, two tops, one SDC):
  qfd_c_b16_reg1   leg-a alignment delay (3 deep) = a same-clock hard ring pair (w257/r257 x2, K=2): checklist item 5
  qfd_c_b16_reg1b  fallback: leg-a alignment delay = three hard stn514 relays (no ring), otherwise identical
Usage: python3 tools/qwen_cluster/qc_reg_kit.py [--check]
"""
import json, re, sys, math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
U = 43.2
RT = "physical/ref_tile"
VIEW = {
    "stn514": f"{RT}/qfd_c_stn514/views/qfd_c_stn514",
    "stn516": f"{RT}/qfd_c_stn516/views/qfd_c_stn516",
    "xstnw": f"{RT}/qfd_c_xstnw_safe/views/qfd_c_xstnw_safe",
    "w258": f"{RT}/qfd_c_land_w258_narrow/views/qfd_c_land_w258_narrow",
    "r258": f"{RT}/qfd_c_land_r258_narrow/views/qfd_c_land_r258_narrow",
    "w257": f"{RT}/qfd_c_land_w257_narrow/views/qfd_c_land_w257_narrow",
    "r257": f"{RT}/qfd_c_land_r257_narrow/views/qfd_c_land_r257_narrow",
    "a0": f"{RT}/qfd_c_b16_dv_diag/a0_standin/qfd_tile_nk_rp2_romleaf_rr",
}
MOD = {"stn514": "qfd_c_stn514", "stn516": "qfd_c_stn516", "xstnw": "qfd_c_xstnw_safe", "w258": "qfd_c_land_w258_narrow",
       "r258": "qfd_c_land_r258_narrow", "w257": "qfd_c_land_w257_narrow", "r257": "qfd_c_land_r257_narrow",
       "a0": "qfd_tile_nk_rp2_romleaf_rr"}
SOURCES = ["physical/ref_tile/qfd_c_b16_dv_diag/a0_standin/a0_rr_bb.v", "rtl/physical/qcluster/qfd_c_stn.sv",
           "rtl/physical/qcluster/qfd_c_xstn_safe.sv", "rtl/physical/qcluster/qfd_c_land_safe.sv",
           "rtl/physical/qcluster/qfd_c_b16_reg1.sv"]
REG = "c1r1"
NB = {"S": "c1r0", "N": "c1r2", "W": "c0r1", "E": "c2r1"}
RDL = 6          # parent constant: every reset leaf (landing halves, A0, xstn) is RDL registered stages from its region pin

# ---------------------------------------------------------------------------------------------------------------- LEF
def lef(view):
    d = ROOT / view
    f = next(d.glob("*.lef"))
    t = f.read_text()
    w, h = map(float, re.search(r"SIZE ([\d.]+) BY ([\d.]+)", t).groups())
    pins = {}
    for n, b in re.findall(r"\n\s*PIN (\S+)(.*?)END \1", t, re.S):
        m = re.search(r"RECT\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)", b)
        if m:
            pins[n] = ((float(m[1]) + float(m[3])) / 2, (float(m[2]) + float(m[4])) / 2)
    return w, h, pins

LEFS = {k: lef(v) for k, v in VIEW.items()}

# --------------------------------------------------------------------------------------------------------- placement
# inst: (kind, x_u, y_u, orient, clock region).  Coordinates in 43.2-um lattice units (origin = lower-left of the child
# AFTER orientation, as ORFS place_macro).  Land halves: a crossing = lo half pair + hi half pair; each pair is a
# vertical stack (writer / reader, 43.2 gap, vld straight, bank_w / bank_e on the shared side channels).
P = {}
def put(n, kind, xu, yu, orient, reg):
    P[n] = dict(kind=kind, x=round(xu * U, 3), y=round(yu * U, 3), orient=orient, reg=reg)

def stack(name, width, xu, yu, src, dst, flow):
    """flow 'up': writer MX at yu (i on S), reader R0 above (o on N); 'down': writer R0 on top (i on N), reader MX below
    (o on S).  lo half at xu, hi half at xu + 3 (64.8 + 64.8 bank channel)."""
    for h, dx in (("lo", 0.0), ("hi", 3.0)):
        if flow == "up":
            put(f"u_{name}_w{h}", f"w{width}", xu + dx, yu, "MX", src)
            put(f"u_{name}_r{h}", f"r{width}", xu + dx, yu + 4, "R0", dst)
        else:
            put(f"u_{name}_w{h}", f"w{width}", xu + dx, yu + 4, "R0", src)
            put(f"u_{name}_r{h}", f"r{width}", xu + dx, yu, "MX", dst)

def span(name, width, w_at, r_at, w_or, r_or, src, dst):
    """E-W crossing: writer and reader halves side by side, R0 / MX only (an x-mirrored closed half puts 150 pins off the
    track grid: ref_tile macro_grid FAIL), so each bank bus wraps one half on the parent layers.  The writer -> reader bank paths are the landed multicycle
    window (setup E = 2 T), so the halves may sit several hundred um apart: the crossing IS the long-reach hop."""
    for h, (wx, wy), (rx, ry) in zip(("lo", "hi"), w_at, r_at):
        put(f"u_{name}_w{h}", f"w{width}", wx, wy, w_or, src)
        put(f"u_{name}_r{h}", f"r{width}", rx, ry, r_or, dst)

def placement(variant):
    P.clear()
    XA, YA = 21, 12                                        # A0 origin (907.2, 518.4); reduction face W, tap face E
    put("u_t", "a0", XA, YA, "R0", REG)
    # column run (east of A0): S -> landing dn1_rly3 -> stn516 -> xstnw (tap -> A0) -> stn516 -> landing dn1_rly6 -> N
    stack("l_dn1_rly3", 258, 33, 6, NB["S"], REG, "up")
    put("u_dn1_rly3", "stn516", 33, 17, "R0", REG)
    put("u_x", "xstnw", 33, 21, "R0", REG)
    put("u_dn1_rly4", "stn516", 33, 27, "R0", REG)
    stack("l_dn1_rly6", 258, 33, 32, REG, NB["N"], "up")
    # leg a (from c1r0): landing leg_2_0a_3 -> 3-deep alignment -> face stn (= old stn leg_2_0a_3) -> A0 n_a
    stack("l_leg_2_0a_3", 257, 7, 1, NB["S"], REG, "up")
    if variant == "ring":
        stack("p_2_0a", 257, 13, 6, REG, REG, "up")        # same-clock ring pair = 3-deep delay (K=2), checklist 5
    else:
        put("u_p0", "stn514", 13, 6, "R0", REG)
        put("u_p1", "stn514", 15, 8, "R0", REG)
        put("u_p2", "stn514", 17, 10, "R0", REG)
    put("u_na", "stn514", 19, 13, "R0", REG)
    # leg b (from c0r1): spanning crossing leg_2_0b_y, reader drives A0 n_b directly (as the old fabric)
    span("l_leg_2_0b_y", 257, [(4, 14), (1, 14)], [(16, 14), (13, 14)], "R0", "R0", NB["W"], REG)
    # t_out -> spanning crossing leg_1_1b_y (writer at the A0 face, reader at the W edge)
    span("l_leg_1_1b_y", 257, [(19, 19), (16, 19)], [(4, 19), (1, 19)], "MX", "MX", REG, NB["W"])
    # leg 3a: A0 n_y -> y0 -> y1 -> y2 (north of the face, west of the A0) -> spanning crossing leg_3_0a_4 to c2r1
    put("u_y0", "stn514", 19, 24, "R0", REG)
    put("u_y1", "stn514", 19, 32, "R0", REG)
    put("u_y2", "stn514", 21, 40, "R0", REG)
    span("l_leg_3_0a_4", 257, [(24, 42), (27, 42)], [(37, 42), (40, 42)], "MX", "MX", REG, NB["E"])
    # DV feedthrough leg 4b (c1r2 -> c1r0) down the east edge
    stack("l_leg_4_0b_1", 257, 38, 34, NB["N"], REG, "down")
    put("u_f1", "stn514", 39, 28, "MX", REG)
    put("u_f2", "stn514", 39, 21, "MX", REG)
    put("u_f3", "stn514", 39, 14, "MX", REG)
    stack("l_leg_4_0b_5", 257, 38, 1, REG, NB["S"], "down")
    return dict(W=44 * U, H=46 * U)

# -------------------------------------------------------------------------------------------------------- netlist
# edges: (src inst, src bus, src lsb, dst inst, dst bus, dst lsb, width)  -- single-cycle register-to-register wires
def crossings(variant):
    X = [  # name, width, src reg, dst reg, kind ('in'/'out'/'int'), producer, consumer
        ("l_dn1_rly3", 258, NB["S"], REG), ("l_dn1_rly6", 258, REG, NB["N"]),
        ("l_leg_2_0a_3", 257, NB["S"], REG), ("l_leg_2_0b_y", 257, NB["W"], REG),
        ("l_leg_1_1b_y", 257, REG, NB["W"]), ("l_leg_3_0a_4", 257, REG, NB["E"]),
        ("l_leg_4_0b_1", 257, NB["N"], REG), ("l_leg_4_0b_5", 257, REG, NB["S"])]
    if variant == "ring":
        X.append(("p_2_0a", 257, REG, REG))
    return X

def chain_edges(variant):
    E = []
    def bus(src, sb, dst, db, w, so=0, do=0):
        E.append((src, sb, so, dst, db, do, w))
    def into_land(src, sb, ln, hw):          # 2*hw-bit bus into the two writer halves
        bus(src, sb, f"u_{ln}_wlo", "i", hw, 0, 0); bus(src, sb, f"u_{ln}_whi", "i", hw, hw, 0)
    def from_land(ln, dst, db, hw):
        bus(f"u_{ln}_rlo", "o", dst, db, hw, 0, 0); bus(f"u_{ln}_rhi", "o", dst, db, hw, 0, hw)
    from_land("l_dn1_rly3", "u_dn1_rly3", "d", 258)
    bus("u_dn1_rly3", "q", "u_x", "b_d", 516); bus("u_x", "tap_d", "u_t", "tap", 508)
    bus("u_x", "a_d", "u_dn1_rly4", "d", 516)
    into_land("u_dn1_rly4", "q", "l_dn1_rly6", 258)
    if variant == "ring":
        bus("u_l_leg_2_0a_3_rlo", "o", "u_p_2_0a_wlo", "i", 257); bus("u_l_leg_2_0a_3_rhi", "o", "u_p_2_0a_whi", "i", 257)
        bus("u_p_2_0a_rlo", "o", "u_na", "d", 257, 0, 0); bus("u_p_2_0a_rhi", "o", "u_na", "d", 257, 0, 257)
    else:
        from_land("l_leg_2_0a_3", "u_p0", "d", 257)
        bus("u_p0", "q", "u_p1", "d", 514); bus("u_p1", "q", "u_p2", "d", 514); bus("u_p2", "q", "u_na", "d", 514)
    bus("u_na", "q", "u_t", "n_a", 514)
    from_land("l_leg_2_0b_y", "u_t", "n_b", 257)
    into_land("u_t", "t_out", "l_leg_1_1b_y", 257)
    bus("u_t", "n_y", "u_y0", "d", 514)
    for a, b in (("u_y0", "u_y1"), ("u_y1", "u_y2")):
        bus(a, "q", b, "d", 514)
    into_land("u_y2", "q", "l_leg_3_0a_4", 257)
    from_land("l_leg_4_0b_1", "u_f1", "d", 257)
    for a, b in (("u_f1", "u_f2"), ("u_f2", "u_f3")):
        bus(a, "q", b, "d", 514)
    into_land("u_f3", "q", "l_leg_4_0b_5", 257)
    return E

# boundary ports: name, width, face, clock region, direction, (inst, bus) list of (inst, bus, lsb, width)
def ports():
    return [
        ("bc", 516, "S", NB["S"], "in", [("u_l_dn1_rly3_wlo", "i", 0, 258), ("u_l_dn1_rly3_whi", "i", 258, 258)]),
        ("bco", 516, "N", NB["N"], "out", [("u_l_dn1_rly6_rlo", "o", 0, 258), ("u_l_dn1_rly6_rhi", "o", 258, 258)]),
        ("la_i", 514, "S", NB["S"], "in", [("u_l_leg_2_0a_3_wlo", "i", 0, 257), ("u_l_leg_2_0a_3_whi", "i", 257, 257)]),
        ("lb_i", 514, "W", NB["W"], "in", [("u_l_leg_2_0b_y_wlo", "i", 0, 257), ("u_l_leg_2_0b_y_whi", "i", 257, 257)]),
        ("lt_o", 514, "W", NB["W"], "out", [("u_l_leg_1_1b_y_rlo", "o", 0, 257), ("u_l_leg_1_1b_y_rhi", "o", 257, 257)]),
        ("ly_o", 514, "E", NB["E"], "out", [("u_l_leg_3_0a_4_rlo", "o", 0, 257), ("u_l_leg_3_0a_4_rhi", "o", 257, 257)]),
        ("lf_i", 514, "N", NB["N"], "in", [("u_l_leg_4_0b_1_wlo", "i", 0, 257), ("u_l_leg_4_0b_1_whi", "i", 257, 257)]),
        ("lf_o", 514, "S", NB["S"], "out", [("u_l_leg_4_0b_5_rlo", "o", 0, 257), ("u_l_leg_4_0b_5_rhi", "o", 257, 257)]),
    ]

# ---------------------------------------------------------------------------------------------------- geometry check
def pin_xy(inst, pin):
    p = P[inst]; w, h, pins = LEFS[p["kind"]]
    x, y = pins[pin]
    if p["orient"] == "MX": y = h - y
    elif p["orient"] == "MY": x = w - x
    elif p["orient"] == "R180": x, y = w - x, h - y
    return p["x"] + x, p["y"] + y

def bitpin(inst, bus, k):
    w, h, pins = LEFS[P[inst]["kind"]]
    n = f"{bus}[{k}]"
    return pin_xy(inst, n if n in pins else bus)

def reach(variant):
    rows = []
    for (s, sb, so, d, db, do, w) in chain_edges(variant):
        worst = 0.0
        for k in range(w):
            (x0, y0), (x1, y1) = bitpin(s, sb, so + k), bitpin(d, db, do + k)
            worst = max(worst, abs(x0 - x1) + abs(y0 - y1))
        rows.append(dict(src=f"{s}.{sb}", dst=f"{d}.{db}", bits=w, worst_um=round(worst, 1),
                         cross=P[s]["reg"] != P[d]["reg"]))
    for (ln, hw, a, b) in crossings(variant):
        for h in ("lo", "hi"):
            worst = 0.0
            for bus in ("bank_w", "bank_e"):
                for k in range(2 * hw):
                    (x0, y0), (x1, y1) = bitpin(f"u_{ln}_w{h}", bus, k), bitpin(f"u_{ln}_r{h}", bus, k)
                    worst = max(worst, abs(x0 - x1) + abs(y0 - y1))
            rows.append(dict(src=f"u_{ln}_w{h}.bank", dst=f"u_{ln}_r{h}.bank", bits=4 * hw + 44, worst_um=round(worst, 1),
                             multicycle="setup 2 / hold 3 (landed window)", cross=a != b))
    return rows

def overlaps(env):
    bad = []
    R = {}
    for n, p in P.items():
        w, h, _ = LEFS[p["kind"]]
        R[n] = (p["x"], p["y"], p["x"] + w, p["y"] + h)
        if p["x"] < 20 or p["y"] < 20 or p["x"] + w > env["W"] - 20 or p["y"] + h > env["H"] - 20:
            bad.append(f"{n} within 20 um of the outline")
        if abs(p["x"] / U - round(p["x"] / U)) > 1e-6 or abs(p["y"] / U - round(p["y"] / U)) > 1e-6:
            if not (abs(p["x"] / (U / 2) - round(p["x"] / (U / 2))) < 1e-6 and abs(p["y"] / (U / 2) - round(p["y"] / (U / 2))) < 1e-6):
                bad.append(f"{n} off the 43.2 / 21.6 lattice")
    ks = list(R)
    for i, a in enumerate(ks):
        for b in ks[i + 1:]:
            A, B = R[a], R[b]
            gx = max(B[0] - A[2], A[0] - B[2]); gy = max(B[1] - A[3], A[1] - B[3])
            if gx < 20 - 1e-6 and gy < 20 - 1e-6:
                bad.append(f"{a} / {b} gap {max(gx, gy):.1f} um < 20")
    return bad, R

# ------------------------------------------------------------------------------------------------------------- ports
CK = {REG: "ck_c1r1"} | {r: f"ck_{r}" for r in NB.values()}
FACE_OF = {v: k for k, v in NB.items()}
A0_CKS = ["ck", "ck_lsl0", "ck_lsl1", "ck_lsl2", "ck_lsl3", "ck_lsl4", "ck_lsl5", "ck_lsl6", "ck_lsl7", "ck_node", "ck_fa0",
          "ck_fa1", "ck_fa2", "ck_fa3", "ck_fa4", "ck_rp0", "ck_rp1", "ck_rp2", "ck_rp3", "ck_rp4", "ck_rp5", "ck_rp6", "ck_rp7",
          "ck_rp8", "ck_rp9", "ck_tx0", "ck_tx1", "ck_tx2", "ck_tx3", "ck_tx4", "ck_tx5", "ck_tx6", "ck_tx7", "ck_rsw", "ck_rnw",
          "ck_dw", "ck_de", "ck_rs", "ck_rn"]

def leaves(variant):
    """reset leaves: (leaf name, [(inst, pin)]).  Own-region leaves come from the rst_c1r1 pin register through RDL-1 kept
    stages; neighbour-side halves take their leaf from a port (the neighbour region's tree, same depth RDL)."""
    own, nbr = [("t", [("u_t", "rst_n")]), ("x", [("u_x", "rst_n")])], []
    for (ln, hw, a, b) in crossings(variant):
        for side, reg in (("w", a), ("r", b)):
            pins = [(f"u_{ln}_{side}{h}", "rsi") for h in ("lo", "hi")]
            if ln.startswith("p_"):
                continue
            (own if reg == REG else nbr).append((f"{ln[2:]}_{side}", pins, reg))
    if variant == "ring":
        own.append(("p_2_0a", [(f"u_p_2_0a_{s}{h}", "rsi") for s in "wr" for h in ("lo", "hi")]))
    return [(o[0], o[1]) for o in own], nbr

def port_table(variant, env):
    """boundary ports with face, range and owning clock.  Data ranges follow the connected half faces; <= 6 pins/um."""
    T = []
    def rng(insts, axis):
        lo = min(P[i][axis] for i in insts); hi = max(P[i][axis] + LEFS[P[i]["kind"]][0 if axis == "x" else 1] for i in insts)
        return lo, hi
    for (name, w, face, reg, d, conns) in ports():
        insts = [c[0] for c in conns]
        a, b = rng(insts, "x" if face in "NS" else "y")
        need = w / 5.0
        if b - a < need:
            m = (a + b) / 2; a, b = m - need / 2, m + need / 2
        T.append(dict(port=name, bits=w, face=face, clock=CK[reg], dir=d, range_um=[round(a, 3), round(b, 3)],
                      layer="M5" if face in "NS" else "M4"))
    _, nbr = leaves(variant)
    used = {}
    for (lf, pins, reg) in nbr:
        face = FACE_OF[reg]
        c = sum(P[i]["x" if face in "NS" else "y"] for i, _ in pins) / len(pins) + 30
        k = used.get(face, 0); used[face] = k + 1
        T.append(dict(port=f"lrst_{lf}", bits=1, face=face, clock=CK[reg], dir="in",
                      range_um=[round(c + 3 * k, 3), round(c + 3 * k + 0.3, 3)], layer="M5" if face in "NS" else "M4"))
    cx = P["u_t"]["x"] + 229.0
    for k, reg in enumerate([REG] + list(NB.values())):
        face = "S" if reg in (REG, NB["S"]) else FACE_OF[reg]
        base = {"S": cx if reg == REG else P["u_l_dn1_rly3_wlo"]["x"] - 20, "N": P["u_l_dn1_rly6_rlo"]["x"] - 20,
                "W": P["u_l_leg_2_0b_y_whi"]["y"] - 10, "E": P["u_l_leg_3_0a_4_rlo"]["y"] - 10}[face]
        T.append(dict(port=CK[reg], bits=1, face=face, clock=CK[reg], dir="clock", range_um=[round(base, 3), round(base + 0.3, 3)],
                      layer="M5" if face in "NS" else "M4"))
    T.append(dict(port="rst_c1r1", bits=1, face="S", clock=CK[REG], dir="in", range_um=[round(cx + 2, 3), round(cx + 2.3, 3)], layer="M5"))
    T.append(dict(port="far", bits=1, face="S", clock=CK[REG], dir="strap", range_um=[round(cx + 4, 3), round(cx + 4.3, 3)], layer="M5"))
    T.append(dict(port="cid", bits=12, face="S", clock=CK[REG], dir="strap", range_um=[round(cx + 6, 3), round(cx + 12, 3)], layer="M5"))
    return T

# ---------------------------------------------------------------------------------------------------------------- RTL
def rtl(variant, top):
    T = port_table(variant, placement(variant))
    own, nbr = leaves(variant)
    L = [f"// GENERATED by tools/qwen_cluster/qc_reg_kit.py -- do not edit.  {top}: CB16 representative region {REG}",
         "// (QW-CLUSTER3/CB16): one region clock root ck_c1r1 + every crossing touching it, each crossing = CLOSED hard",
         "// landing halves (writer on the source root, reader on the destination root, D 4 / K 2 static ring, no credit).",
         "// Neighbour-side halves run on the neighbour clock port and take their reset leaf from a port.  A0 = STAND-IN.",
         f"// Alignment delay of leg a: {'same-clock hard ring pair (K 2 = 3 edges)' if variant == 'ring' else '3 hard stn514 relays (fallback)'}.",
         f"module {top} ("]
    decl = []
    for p in T:
        d = "output" if p["dir"] == "out" else "input"
        decl.append(f"    {d} wire {'' if p['bits'] == 1 else f'[{p[chr(98)+chr(105)+chr(116)+chr(115)] - 1}:0] '}{p['port']}")
    L.append(",\n".join(decl)); L.append(");")
    # nets of every hard child pin that is internally connected
    nets = {}
    def net(inst, pin, w):
        n = f"{inst[2:]}__{pin}"
        nets.setdefault(n, w); return n
    conn = {n: {} for n in P}
    for (s, sb, so, d, db, do, w) in chain_edges(variant):
        ws = {"stn514": 514, "stn516": 516, "xstnw": 516}.get(P[s]["kind"])
        sw = {"a_d": 516, "tap_d": 508, "q": ws, "o": int(P[s]["kind"][1:]) if P[s]["kind"][0] in "wr" else None,
              "t_out": 514, "n_y": 514}[sb]
        n = net(s, sb, sw)
        conn[s][sb] = n
        conn[d].setdefault(db, []).append((n, so, do, w))
    for (ln, hw, a, b) in crossings(variant):
        for h in ("lo", "hi"):
            wi, ri = f"u_{ln}_w{h}", f"u_{ln}_r{h}"
            for bus, w in (("bank_w", 2 * hw), ("bank_e", 2 * hw), ("vld", 44)):
                n = net(wi, bus, w); conn[wi][bus] = n; conn[ri][bus] = [(n, 0, 0, w)]
    for (name, w, face, reg, d, cs) in ports():
        for (i, b, lsb, ww) in cs:
            if d == "in":
                conn[i][b] = [(name, lsb, 0, ww)]
            else:
                n = net(i, b, ww); conn[i][b] = n
                L.append(f"    assign {name}[{lsb + ww - 1}:{lsb}] = {n};")
    for n, w in sorted(nets.items()):
        L.insert(L.index(");") + 1, f"    wire [{w - 1}:0] {n};")
    # reset: pin register + RDL-1 kept stages per own leaf
    L.append(f"    // reset: rst_c1r1 -> pin register -> {RDL - 1} kept stages per leaf (equal depth RDL={RDL} for every leaf of every region)")
    L.append("    (* keep = 1 *) reg rpin_q;\n    always @(posedge ck_c1r1) rpin_q <= rst_c1r1;")
    leafnet = {}
    for (lf, pins) in own:
        L.append(f"    (* keep = 1 *) reg [{RDL - 2}:0] rr_{lf};")
        L.append(f"    always @(posedge ck_c1r1) rr_{lf} <= {{rr_{lf}[{RDL - 3}:0], rpin_q}};")
        for (i, p) in pins:
            leafnet[(i, p)] = f"rr_{lf}[{RDL - 2}]"
    for (lf, pins, reg) in nbr:
        for (i, p) in pins:
            leafnet[(i, p)] = f"lrst_{lf}"
    L.append("    wire far_n = ~far;   // static strap complement (xstn station index, as qfd_c_b16_dv)")
    L.append("    wire th_t, tl_t;")
    pw = {p["port"]: p["bits"] for p in T}
    def expr(lst, w):
        if isinstance(lst, str):
            return lst
        if len(lst) == 1 and lst[0][1] == 0 and lst[0][3] == w and lst[0][2] == 0 and nets.get(lst[0][0], pw.get(lst[0][0])) == w:
            return lst[0][0]
        parts = sorted(lst, key=lambda t: -t[2])
        return "{" + ", ".join(f"{n}[{so + ww - 1}:{so}]" for (n, so, do, ww) in parts) + "}"
    for inst, p in P.items():
        k = p["kind"]; c = conn[inst]; ckp = CK[p["reg"]]
        pins = []
        if k == "a0":
            pins += [f".{x}(ck_c1r1)" for x in A0_CKS]
            pins += [f".rst_n({leafnet[(inst, 'rst_n')]})", ".tile_id({cid, tl_t, tl_t, th_t, th_t})", ".tie_hi(th_t)", ".tie_lo(tl_t)",
                     f".tap({expr(c['tap'], 508)})", f".n_a({expr(c['n_a'], 514)})", f".n_b({expr(c['n_b'], 514)})",
                     f".t_out({c['t_out']})", f".n_y({c['n_y']})"]
        elif k.startswith("stn"):
            w = int(k[3:])
            pins += [f".ck({ckp})", f".d({expr(c['d'], w)})", f".q({c['q']})"]
        elif k == "xstnw":
            pins += [f".ck({ckp})", f".rst_n({leafnet[(inst, 'rst_n')]})", ".sidx({far, far, far_n})", f".b_d({expr(c['b_d'], 516)})",
                     f".a_d({c['a_d']})", f".tap_d({c['tap_d']})"]
        elif k[0] == "w":
            hw = int(k[1:])
            pins += [f".ck({ckp})", f".rsi({leafnet[(inst, 'rsi')]})", f".i({expr(c['i'], hw)})", f".bank_w({c['bank_w']})",
                     f".bank_e({c['bank_e']})", f".vld({c['vld']})"]
        else:
            hw = int(k[1:])
            pins += [f".ck({ckp})", f".rsi({leafnet[(inst, 'rsi')]})", f".o({c['o']})", f".bank_w({expr(c['bank_w'], 2 * hw)})",
                     f".bank_e({expr(c['bank_e'], 2 * hw)})", f".vld({expr(c['vld'], 44)})"]
        L.append(f"    {MOD[k]} {inst} ({', '.join(pins)});   // ({p['x']}, {p['y']}) {p['orient']} {p['reg']}")
    L.append("endmodule")
    return "\n".join(L) + "\n"

# ---------------------------------------------------------------------------------------------------------------- SDC
def sdc(variant_list):
    rest = [CK[r] for r in NB.values()]
    S = ["# GENERATED by tools/qwen_cluster/qc_reg_kit.py -- do not edit.  CB16 representative region c1r1: four neighbour",
         "# region roots (same period, related, neighbour-relative delivery), die residual between communicating pairs, and",
         "# the landed bank window on every crossing (LANDING-CONTRACT L5: writer -> reader multicycle -setup 2 -hold 3).",
         "set ot_q_per [get_property [get_clocks core_clk] period]"]
    S += [f"create_clock -name {c} -period $ot_q_per [get_ports {c}]" for c in rest]
    S += [f"set_clock_uncertainty -setup 60 [get_clocks {{{' '.join(rest)}}}]", f"set_clock_uncertainty -hold 25 [get_clocks {{{' '.join(rest)}}}]"]
    for c in rest:
        for f_, t_ in (("core_clk", c), (c, "core_clk")):
            S += [f"set_clock_uncertainty -setup 120 -from [get_clocks {f_}] -to [get_clocks {t_}]",
                  f"set_clock_uncertainty -hold 85 -from [get_clocks {f_}] -to [get_clocks {t_}]"]
    names = sorted({ln for v in variant_list for (ln, *_r) in crossings(v)})
    S.append("set ot_qc_lands {" + " ".join(names) + "}")
    S += ["set ot_qc_land_n 0",
          "foreach ot_ln $ot_qc_lands {",
          "  foreach ot_h {lo hi} {",
          "    set ot_lf [get_cells -quiet u_${ot_ln}_w${ot_h}]",
          "    set ot_lt [get_cells -quiet u_${ot_ln}_r${ot_h}]",
          "    if {[llength $ot_lf] == 0 || [llength $ot_lt] == 0} { continue }",
          "    set_multicycle_path -setup 2 -from $ot_lf -to $ot_lt",
          "    set_multicycle_path -hold 3 -from $ot_lf -to $ot_lt",
          "    incr ot_qc_land_n",
          "  }",
          "}",
          'puts "OT_QC_LAND_SDC $ot_qc_land_n landed half pairs constrained"']
    return S

def sdc_io(variant):
    T = port_table(variant, placement(variant))
    rest = [CK[r] for r in NB.values()]
    S = []
    io = [(p["port"], p["dir"], p["clock"], p["bits"]) for p in T if p["dir"] in ("in", "out") and p["clock"] != CK[REG]]
    for (n, d, c, b) in io:
        pat = n if b == 1 else f"{n}[*]"
        S.append(f"set_{'input' if d == 'in' else 'output'}_delay [expr {{0.2 * $ot_q_per}}] -clock {c} [get_ports {{{pat}}}]")
    S.append(f"if {{!$::ot_ref_pre_cts}} {{ set_propagated_clock [get_clocks {{{' '.join(rest)}}}] }}")
    return S, io

def full_sdc():
    S = sdc(["ring", "stn"])
    s_io, io = sdc_io("ring")
    S += s_io
    # post-CTS: neighbour-domain boundary buses referenced to their own propagated tree at the hard-half clock pin
    kit = (ROOT / "tools/qwen_cluster/qc_kit.py").read_text()
    a = kit.index('        "if {!$::ot_ref_pre_cts} {",\n        "  proc ot_qc_pinreg_cks')
    b = kit.index('        "  puts \\"OT_QC_IO_SDC')
    txt = kit[a:b]
    i0 = txt.index('        "  foreach {ot_qc_bus'); i1 = txt.index('"} {",', i0) + len('"} {",')
    lst = " ".join(f"{n} {d} {c}" for (n, d, c, bb) in io)
    txt = txt[:i0] + "        " + repr("  foreach {ot_qc_bus ot_qc_dir ot_qc_clk} {" + lst + "} {") + ",\n" + txt[i1:]
    block = eval("[" + txt + "]")
    S += block + ['  puts "OT_QC_IO_SDC $ot_qc_io_n buses referenced to their region tree"', "}"]
    S += ["set_case_analysis 0 [get_ports {cid[*]}]", "set_case_analysis 0 [get_ports far]"]
    return "\n".join(S) + "\n"

# ------------------------------------------------------------------------------------------------- spec / plan / main
KITS = {"ring": "qfd_c_b16_reg1", "stn": "qfd_c_b16_reg1b"}
SDC_PATH = "physical/qcluster/qfd_c_b16_reg1_regions.sdc"
PLAN = "results/arch/qwen_cluster_1017/q_cluster16/reg1"

def price(variant):
    """added edges per class vs qfd_c_b16_dv region c1r1 (old soft landing = +3 edges per crossing, unchanged by the hard
    halves: writer slot + K 2; their two face reset stages shift both epochs equally)."""
    return [
        dict(edge_class="crossing (landed, any seam)", count=8, old_edges="+3 (soft qfd_c_land D4/K2)", new_edges="+3 (hard halves D4/K2)", delta=0),
        dict(edge_class="column run bc -> bco through c1r1", old="land_r -> rly3 -> x -> rly4 -> rly5 -> land_w (5 hops)",
             new="land_r -> rly3 -> x -> rly4 -> land_w (4 hops)", delta=-1),
        dict(edge_class="leg 2_0a (c1r0 -> n_a)", old="land_r -> stn -> pad x3 -> n_a", new=("land_r -> ring(3) -> stn -> n_a" if variant == "ring" else "land_r -> stn x3 -> stn -> n_a"), delta=0),
        dict(edge_class="leg 2_0b_y (c0r1 -> n_b)", old="land_r -> n_b", new="land_r -> n_b", delta=0),
        dict(edge_class="leg 1_1b_y (t_out -> c0r1)", old="t_out -> land_w", new="t_out -> land_w", delta=0),
        dict(edge_class="leg 3_0a (n_y -> c2r1)", old="n_y -> stn x4 -> land_w", new="n_y -> stn x3 -> land_w", delta=-1),
        dict(edge_class="leg 4_0b feedthrough (c1r2 -> c1r0)", old="land_r -> stn x4 -> land_w", new="land_r -> stn x3 -> land_w", delta=-1),
        dict(edge_class="reset leaf depth", old="per-leaf chain from rst_c1r1 (soft)", new=f"RDL={RDL} for every leaf; landing halves add 2 face stages on BOTH sides (epochs equal)", delta=0),
    ]

def spec(variant):
    env = placement(variant)
    T = port_table(variant, env)
    faces = {f: [p["port"] for p in T if p["face"] == f] for f in "NSEW"}
    kids = [dict(view=VIEW[p["kind"]], count=1, inst=n, at=[p["x"], p["y"]], orient=p["orient"], at_exact=True) for n, p in P.items()]
    name = KITS[variant]
    return dict(
        name=name, top=name, kind="cluster", diagnostic=True, sources=SOURCES, params={}, clock="cts", child_clock_ref=None,
        clock_port="ck_c1r1", clock_ports=[CK[REG]] + [CK[r] for r in NB.values()],
        orfs_vars={"GPL_TIMING_DRIVEN": "0", "GPL_ROUTABILITY_DRIVEN": "0"},
        io_flop_at_pins=False, sdc_extra=[SDC_PATH], reset_ports=["rst_c1r1"] + [p["port"] for p in T if p["port"].startswith("lrst_")],
        outline=dict(w=round(env["W"], 3), h=round(env["H"], 3), exact=True), child_lattice_um=21.6,
        children=kids, macros=[], pins=faces,
        pin_ranges={p["port"]: p["range_um"] for p in T}, pin_layers={p["port"]: p["layer"] for p in T},
        route=dict(pd=0.5, threads=16, peak_ram_gb=96, pin_v="M5", pin_h="M4 M6", macro_halo_um=5.4, io_hold_margin_ns=0.03, hold_margin_ns=0.03),
        cluster_level=2, recipe=4, hold_budget="die", inhold=False, outhold=False,
        pin_regs=dict(enable=False, reason="every data port lands directly in a hard-half register (writer slot capture / reader "
                      "output flop, both closed views); rst_c1r1 is registered at the face (rpin_q) then 5 kept stages; lrst_* "
                      "neighbour leaves are registered twice inside each closed half (rst_l0 -> r2); cid / far are static straps"),
        reset_landing=dict(enable=False, reason="RTL lands rst_c1r1 in rpin_q + kept rr_* stages; every closed half lands rsi in 2 stages"),
        structural_change="QW-CLUSTER3/CB16 (LEAD-QW 12:15): CB16 parent as clock REGIONS joined only by LANDED crossings built from "
                          "the CLOSED hard halves qfd_c_land_{w,r}{257,258}_narrow (writer on the source root, reader on the "
                          "destination root, static D4/K2 ring, bank paths = landed multicycle window), CLOSED qfd_c_xstnw_safe "
                          "column station and CLOSED qfd_c_stn514/516 relays; intra-region single-cycle wires <= 405 um by "
                          "placement (per-bit LEF check, plan.json).  ONE representative interior region (c1r1) + all 8 crossings "
                          "touching it; A0 = diagnostic STAND-IN (no qualified A0 view).",
        job=dict(owner="Claude:QW-CLUSTER3/CB16", branch="claude/qw-cluster3-cb16-1019", tag="reg1" if variant == "ring" else "reg1b",
                 purpose="CB16 representative landed region c1r1 (critical prefix: gate only, no submit)", submit=False,
                 hold_merge="QW-CLUSTER3 diagnostic: stand-in A0 + closed station/landing views",
                 extra_paths=[PLAN],
                 no_bench_reason="representative-region PHYSICAL gate only (critical prefix, never submitted); region bench owed: "
                                 "ring K2 == 3-deep pad equivalence and reset-epoch equality across the 8 crossings"))

def write():
    out = {}
    body = rtl("ring", KITS["ring"]) + "\n" + rtl("stn", KITS["stn"])
    (ROOT / "rtl/physical/qcluster/qfd_c_b16_reg1.sv").write_text("`timescale 1ns/1ps\n`default_nettype none\n" + body + "`default_nettype wire\n")
    (ROOT / SDC_PATH).write_text(full_sdc())
    plan = {}
    for v, k in KITS.items():
        s = spec(v)
        p = ROOT / "tools/ref_tile/specs_qcluster" / f"{k}.json"
        p.parent.mkdir(parents=True, exist_ok=True); p.write_text(json.dumps(s, indent=1) + "\n")
        env = placement(v); bad, _ = overlaps(env); r = reach(v)
        plan[k] = dict(outline_um=[round(env["W"], 2), round(env["H"], 2)], children=len(P),
                       child_kinds={kk: sum(1 for q in P.values() if q["kind"] == kk) for kk in sorted({q["kind"] for q in P.values()})},
                       geometry_violations=bad,
                       single_cycle_max_um=max(x["worst_um"] for x in r if "multicycle" not in x),
                       single_cycle_over_405=[x for x in r if "multicycle" not in x and x["worst_um"] > 405],
                       bank_window_max_um=max(x["worst_um"] for x in r if "multicycle" in x),
                       edges=r, priced_cycles=price(v))
        out[k] = str(p)
    d = ROOT / PLAN; d.mkdir(parents=True, exist_ok=True)
    (d / "plan.json").write_text(json.dumps(plan, indent=1) + "\n")
    return out

if __name__ == "__main__":
    print(json.dumps(write(), indent=1))
