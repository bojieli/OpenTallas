#!/usr/bin/env python3
"""Q-CLUSTER generator: qfd_c_b16_dv, the adopted dv2r8f compute-die cluster (results/arch/qwen_cluster_1017/SPEC.md).

Base: the CB cluster generator (claude/q3h-cb-1016 e7e22d5b6, copied as tools/qwen_cluster/cb_base.py, unchanged).
Its geometry helpers, morton tree, host map, leg router, column runs and reset tree are reused through module globals.
This generator changes:
  * corridors A / T / B 64.8 -> 129.6 um (SPEC 1; outline 2285.28 x 5184), reach: planning hop 390 <= limit 405;
  * four quadrant clock roots ck_sw / ck_se / ck_nw / ck_ne (SPEC 2): every register (station, relay, pin register,
    reset stage) and every A0 tile clock entry takes the root of the quadrant it sits in; region seams are crossed only
    by registered hops;
  * the DV far-band feedthrough rs_i (N face) -> rs_o (S face), 514 b, in the T centre lane: N pin register, relays,
    S pin register (SPEC 1, 14 edges);
  * every relay stage is its own qfd_q3h_stn instance (named, site-planned, clocked by its region).
Exactness is unchanged: the tree is the reference morton pair tree (cb_base.ordered_ast), legs are aligned by
construction (static schedule, no flow control).

  qc_gen.py gen [--hosts tools/qwen_cluster/cb16_hosts.json]   writes RTL, bench top, latency header, contract, kit spec, PNG
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("cb_base", Path(__file__).with_name("cb_base.py"))
g = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(g)

MASTER = "qfd_c_b16_dv"
FABRIC = "qfd_c_b16_dv_fabric"
OUT_RTL = ROOT / "rtl/physical/qcluster"
OUT_ARCH = ROOT / "results/arch/qwen_cluster_1017"
KIT = ROOT / "physical/ref_tile/qfd_c_b16_dv"
# tile checklist 10-17 (macros on the 43.2-um lattice): every A0 origin a multiple of 43.2 -> L = R = 43.2,
# A = T = B = 146.88 (>= the 129.6 of SPEC 1), S / N strips 86.4 (row pitch 1,296 = 30 x 43.2)
CORR_W = {"L": 43.2, "A": 146.88, "T": 146.88, "B": 146.88, "R": 43.2}
STRIP_UM = 86.4
LATTICE = 43.2
HOP, LIMIT = 390.0, 405.0
BW, DW = g.BW, g.DW
QUADS = ("sw", "se", "nw", "ne")


def setup():
    x = 0.0
    for n in ["L", 0, "A", 1, "T", 2, "B", 3, "R"]:
        if isinstance(n, str):
            g.CORR[n] = (round(x, 4), round(x + CORR_W[n], 4))
            x += CORR_W[n]
        else:
            g.COLX[n] = (round(x, 4), round(x + g.TW, 4))
            x += g.TW
    g.WIDTH = round(x, 4)
    g.STRIP = STRIP_UM
    g.ROWY = {r: round(g.STRIP + r * (g.TH + g.GAP), 4) for r in range(4)}
    g.HEIGHT = round(2 * g.STRIP + 4 * g.TH + 3 * g.GAP, 4)
    g.CHANNELS = [(0.0, g.STRIP)] + [(g.ROWY[r] + g.TH, g.ROWY[r + 1]) for r in range(3)] + [(g.HEIGHT - g.STRIP, g.HEIGHT)]
    g.GAPS = g.CHANNELS[1:4]
    for v in [lo for lo, _ in g.COLX.values()] + list(g.ROWY.values()) + [g.WIDTH - g.COLX[c][1] for c in range(4)]:
        if abs(v / LATTICE - round(v / LATTICE)) > 1e-6:
            raise SystemExit(f"A0 origin {v} (or its mirror) off the {LATTICE}-um lattice")
    g.T_CW = CORR_W["T"] * 2 / 3          # c1 / c2 lanes at T.lo + 21.6 / T.hi - 21.6; the feedthrough at the T centre
    g.HOP, g.LIMIT = HOP, LIMIT
    g.CHAIN = g.down_chain()
    g.STAGE = {n: i + 1 for i, (n, _) in enumerate(g.CHAIN)}


setup()
WIDTH, HEIGHT = g.WIDTH, g.HEIGHT
XT = g.ccx("T")
YMID = (g.ROWY[1] + g.TH + g.ROWY[2]) / 2


def quad(x, y):
    return ("s" if y < YMID else "n") + ("w" if x <= XT else "e")


def tile_quad(c, r):
    return ("s" if r < 2 else "n") + ("w" if c < 2 else "e")


A0_REF = "origin/codex/romleaf-native-1621"   # Q-ROMPARENT-2 c1 REGROOT wrappers (provisional until the A0 gate passes)
A0_NK, A0_NL = "qfd_tile_nk_rp2_romleaf_rr", "qfd_tile_nl_rp2_romleaf_rr"


def a0_clocks(path):
    import subprocess
    src = subprocess.run(["git", "-C", str(ROOT), "show", f"{A0_REF}:{path}"], check=True, capture_output=True,
                         text=True).stdout
    i = src.index("module ")
    head = src[i:src.index(");", i)]
    return re.findall(r"input\s+wire\s+(ck\w*)\s*,", head)


NK_CLOCKS = a0_clocks(f"rtl/physical/{A0_NK}.sv")
NL_CLOCKS = a0_clocks(f"rtl/physical/{A0_NL}.sv")


def ft_chain():
    """rs_i -> rs_o: N pin register, relays every <= HOP down the T centre lane, S pin register."""
    y0, y1 = HEIGHT - g.STRIP / 2, g.STRIP / 2
    k = max(0, math.ceil((y0 - y1) / LIMIT) - 1)      # 5,119 um / 13 = 394 um hops: 14 edges (SPEC 1)
    ys = [y0] + [round(y0 - (y0 - y1) * i / (k + 1), 3) for i in range(1, k + 1)] + [y1]
    return [(XT, y) for y in ys]


class Emit:
    def __init__(self):
        self.L, self.sites, self.regions = [], [], {q: 0 for q in QUADS}

    def w(self, s):
        self.L.append(s)

    def stage(self, name, width, d, q, x, y, note=""):
        r = quad(x, y)
        self.regions[r] += width
        self.sites.append(dict(inst=f"u_fab.{name}", at=[round(x, 3), round(y, 3)], region=r, bits=width))
        self.w(f"    wire [{width - 1}:0] {q};  qfd_q3h_stn #(.W({width}), .N(1)) {name} (.ck(ck_{r}), .d({d}), .q({q}));"
               f"   // ({x:.2f}, {y:.2f}) {r}{(' ' + note) if note else ''}")


def gen_fabric(host, spare, legs, rsx, rnodes, rleaves, rdepth, RD, mut_swap):
    E = Emit()
    w = E.w
    w("`timescale 1ns/1ps")
    w(f"// GENERATED by tools/qwen_cluster/qc_gen.py -- do not edit.  {FABRIC}: every register of qfd_c_b16_dv outside the")
    w("// tiles (Q-CLUSTER 2026-10-17, results/arch/qwen_cluster_1017/SPEC.md): the four column runs (entry / relays /")
    w("// qfd_xcst_n / exit), the morton reduction legs, the rs exit run, the DV far-band feedthrough rs_i -> rs_o and the")
    w("// equal-depth reset tree.  Each register sits in one clock quadrant and takes that quadrant's root; quadrant seams")
    w("// are crossed only by registered hops <= 405 um.  Static schedule: no ready / credit / backpressure.")
    w("// MUT (bench only, default 0 = the design): 1 = one extra relay on leg a of node (2,0); 2 = leaves of nodes (1,0).a")
    w("//   and (1,2).a exchanged; 3 = one extra relay on column 2's run before its row-1 station; 4 = one extra relay on")
    w("//   the rs_i -> rs_o feedthrough; 5 = feedthrough bits 0 / 1 exchanged.")
    w(f"module {FABRIC} #(parameter integer MUT = 0) (")
    ports = [f"    input  wire ck_{q}" for q in QUADS] + ["    input  wire rst_n", "    input  wire far"]
    for c in range(4):
        ports += [f"    input  wire [{DW-1}:0] bc{c}", f"    output wire [{DW-1}:0] bco{c}"]
    ports += [f"    output wire [{BW-1}:0] rs", f"    input  wire [{BW-1}:0] rs_i", f"    output wire [{BW-1}:0] rs_o"]
    for c in range(4):
        for r in range(4):
            s = g.sname(c, r)
            ports += [f"    output wire [{DW-9}:0] tap_{s}", f"    output wire trst_{s}", f"    input  wire [{BW-1}:0] t_out_{s}"]
            if (c, r) != spare:
                ports += [f"    output wire [{BW-1}:0] n_a_{s}", f"    output wire [{BW-1}:0] n_b_{s}",
                          f"    input  wire [{BW-1}:0] n_y_{s}"]
    w(",\n".join(ports))
    w(");")
    w("    wire far_n = ~far;   // static strap complement")
    # reset
    w(f"    // ---- reset: pin register + pipelined runs; every tile / station sees rst_n exactly {RD} edges after the pin")
    pos = {}
    for nm, par, (x, y) in rnodes:
        pos[nm] = (x, y)
        E.stage(f"u_{nm}", 1, "rst_n" if par is None else f"{par}_q", f"{nm}_q", x, y)
    for (cor, r), nm in sorted(rleaves.items()):
        pad = RD - rdepth[nm]
        prev = f"{nm}_q"
        x, y = pos[nm]
        for j in range(pad):
            E.stage(f"u_rpad_{cor}_{r}_{j}", 1, prev, f"rpad_{cor}_{r}_{j}_q", x, y)
            prev = f"rpad_{cor}_{r}_{j}_q"
        w(f"    wire rstl_{cor}_{r} = {prev};")
    for c in range(4):
        for r in range(4):
            w(f"    assign trst_{g.sname(c, r)} = rstl_{g.E_FACE_CORR[c]}_{r};")
    # column runs
    w("    // ---- column runs {tag 8, xl 128, ib 379, go}: entry pin register, relays, one qfd_xcst_n per row, exit pin register")
    for c in range(4):
        prev = f"bc{c}"
        x = g.run_x(c)
        for nm, y in g.chain_for(c):
            if nm.startswith("xcst"):
                r = int(nm[4:])
                s = g.sname(c, r)
                cin = prev
                if c == 2 and r == 1:
                    q = quad(x, y)
                    w(f"    wire [{DW-1}:0] dm3_{c};  qfd_q3h_run #(.W({DW}), .D(MUT == 3 ? 1 : 0)) u_dm3_{c} (.ck(ck_{q}), .d({prev}), .q(dm3_{c}));")
                    cin = f"dm3_{c}"
                b1 = "far_n" if (r >> 1) & 1 else "far"
                b0 = "far_n" if r & 1 else "far"
                q = quad(x, y)
                E.regions[q] += DW
                E.sites.append(dict(inst=f"u_fab.u_x_{s}", at=[round(x, 3), round(y, 3)], region=q, bits=DW, station=True))
                w(f"    wire [{DW-1}:0] dn{c}_{nm};")
                w(f"    qfd_xcst_n u_x_{s} (.ck(ck_{q}), .rst_n(rstl_{g.E_FACE_CORR[c]}_{r}), .sidx({{far, {b1}, {b0}}}), .b_d({cin}),"
                  f" .a_d(dn{c}_{nm}), .tap_d(tap_{s}), .tie_hi(), .tie_lo());   // ({x:.2f}, {y:.2f}) {q}")
            else:
                E.stage(f"u_dn{c}_{nm}", DW, prev, f"dn{c}_{nm}", x, y)
            prev = f"dn{c}_{nm}"
        w(f"    assign bco{c} = {prev};")
    # tree legs
    w("    // ---- morton reduction tree legs (legs of one node arrive on the same edge)")
    for x in legs:
        (l, i), side, (hc, hr) = x["node"], x["side"], x["host"]
        kind, (sc, sr) = x["src"]
        src = f"{kind}_{g.sname(sc, sr)}"
        if (l, i, side) in mut_swap:
            src = f"(MUT == 2 ? {mut_swap[(l, i, side)]} : {src})"
        k = x["k"]
        dst = f"n_{side}_{g.sname(hc, hr)}"
        w(f"    // node ({l},{i}).{side} on tile ({hc},{hr}) <- {kind}({sc},{sr}): {x['d']:.1f} um, {k} relays, hop <= {x['d'] / (k + 1):.1f} um")
        prev = src
        for j in range(k):
            px, py = g.along(x["poly"], (j + 1) / (k + 1))
            nm = f"u_leg_{l}_{i}{side}_{j}"
            E.stage(nm, BW, prev, f"leg_{l}_{i}{side}_{j}", px, py)
            prev = f"leg_{l}_{i}{side}_{j}"
        if (l, i, side) == (2, 0, "a"):
            px, py = g.along(x["poly"], 1.0)
            w(f"    qfd_q3h_run #(.W({BW}), .D(MUT == 1 ? 1 : 0)) u_m1 (.ck(ck_{quad(px, py)}), .d({prev}), .q({dst}));")
        else:
            w(f"    assign {dst} = {prev};")
    # rs exit
    rc, rr = host[(4, 0)]
    k = rsx["k"]
    w(f"    // ---- rs: root n_y ({rc},{rr}) -> {k} relays + the rs pin register (S face): {rsx['d']:.1f} um")
    prev = f"n_y_{g.sname(rc, rr)}"
    for j in range(k + 1):
        px, py = g.along(rsx["poly"], (j + 1) / (k + 1)) if j < k else rsx["poly"][-1]
        if j == k:
            py = g.STRIP / 2
        E.stage(f"u_rs_{j}", BW, prev, f"rs_{j}", px, py, "pin register" if j == k else "")
        prev = f"rs_{j}"
    w(f"    assign rs = {prev};")
    # DV feedthrough
    ch = ft_chain()
    w(f"    // ---- DV far-band feedthrough rs_i (N) -> rs_o (S): {len(ch)} registers in the T centre lane, hop <= "
      f"{max(a[1] - b[1] for a, b in zip(ch, ch[1:])):.1f} um")
    prev = "rs_i_m5"
    w(f"    wire [{BW-1}:0] rs_i_m5 = (MUT == 5) ? {{rs_i[{BW-1}:2], rs_i[0], rs_i[1]}} : rs_i;")
    for j, (px, py) in enumerate(ch):
        note = "rs_i pin register" if j == 0 else ("rs_o pin register" if j == len(ch) - 1 else "")
        E.stage(f"u_ft_{j}", BW, prev, f"ft_{j}", px, py, note)
        prev = f"ft_{j}"
        if j == len(ch) // 2:
            w(f"    wire [{BW-1}:0] ft_m4;  qfd_q3h_run #(.W({BW}), .D(MUT == 4 ? 1 : 0)) u_m4 (.ck(ck_{quad(px, py)}), .d({prev}), .q(ft_m4));")
            prev = "ft_m4"
    w(f"    assign rs_o = {prev};")
    w("endmodule")
    return "\n".join(E.L) + "\n", E, len(ch)


def gen_cluster(spare):
    L = []
    w = L.append
    w("`timescale 1ns/1ps")
    w(f"// GENERATED by tools/qwen_cluster/qc_gen.py -- do not edit.  {MASTER}: the dv2r8f compute-die cluster (Q-CLUSTER")
    w("// 2026-10-17) = one 4 x 4 reduction block of 16 A0 ROM-leaf tiles (hard children; nk = node host, one nl) + the fabric.")
    w("// Four quadrant clock roots: tiles (c<2|c>=2, r<2|r>=2) take ck_sw / ck_se / ck_nw / ck_ne on every clock entry; the")
    w("// cluster CTS balances each quadrant net to its tile entries (A0 ETM insertion) and fabric registers.  Straps cid /")
    w("// far come from the instance's own tie_hi / tie_lo (die); far clusters tie rs_i to tie_lo and leave rs_o open.")
    w(f"module {MASTER} (")
    ports = [f"    input  wire ck_{q}" for q in QUADS] + ["    input  wire rst_n", "    input  wire far", "    input  wire [11:0] cid"]
    for c in range(4):
        ports += [f"    input  wire [{DW-1}:0] bc{c}", f"    output wire [{DW-1}:0] bco{c}"]
    ports += [f"    output wire [{BW-1}:0] rs", f"    input  wire [{BW-1}:0] rs_i", f"    output wire [{BW-1}:0] rs_o",
              "    output wire tie_hi", "    output wire tie_lo"]
    w(",\n".join(ports))
    w(");")
    w("    (* keep = \"true\" *) wire tie_hi_w = 1'b1;")
    w("    (* keep = \"true\" *) wire tie_lo_w = 1'b0;")
    w("    assign tie_hi = tie_hi_w;")
    w("    assign tie_lo = tie_lo_w;")
    conn = []
    for c in range(4):
        for r in range(4):
            s = g.sname(c, r)
            w(f"    wire [{DW-9}:0] tap_{s};  wire trst_{s};  wire [{BW-1}:0] t_out_{s};  wire th_{s}, tl_{s};")
            conn += [f".tap_{s}(tap_{s})", f".trst_{s}(trst_{s})", f".t_out_{s}(t_out_{s})"]
            if (c, r) != spare:
                w(f"    wire [{BW-1}:0] n_a_{s}, n_b_{s}, n_y_{s};")
                conn += [f".n_a_{s}(n_a_{s})", f".n_b_{s}(n_b_{s})", f".n_y_{s}(n_y_{s})"]
    conn = [f".ck_{q}(ck_{q})" for q in QUADS] + [".rst_n(rst_n)", ".far(far)"] + [f".bc{c}(bc{c})" for c in range(4)] + \
           [f".bco{c}(bco{c})" for c in range(4)] + [".rs(rs)", ".rs_i(rs_i)", ".rs_o(rs_o)"] + conn
    w(f"    {FABRIC} u_fab (\n        " + ",\n        ".join(conn) + ");")
    for c in range(4):
        for r in range(4):
            s = g.sname(c, r)
            m = g.morton(c, r)
            bits = ", ".join(f"th_{s}" if (m >> b) & 1 else f"tl_{s}" for b in (3, 2, 1, 0))
            nk = (c, r) != spare
            mod = A0_NK if nk else A0_NL
            q = tile_quad(c, r)
            pc = [f".{k}(ck_{q})" for k in (NK_CLOCKS if nk else NL_CLOCKS)] + \
                 [f".rst_n(trst_{s})", f".tile_id({{cid, {bits}}})", f".tie_hi(th_{s})", f".tie_lo(tl_{s})",
                  f".tap(tap_{s})", f".t_out(t_out_{s})"]
            if nk:
                pc += [f".n_a(n_a_{s})", f".n_b(n_b_{s})", f".n_y(n_y_{s})"]
            w(f"    // slot ({c},{r}) {g.COL_ORIENT[c]} at ({g.COLX[c][0]}, {g.ROWY[r]}), K-slice {m}, clock quadrant {q}")
            w(f"    {mod} u_t_{s} (\n        " + ",\n        ".join(pc) + ");")
    w("endmodule")
    return "\n".join(L) + "\n"


def gen_tb(spare):
    """Fabric bench top: CB bench (real fabric, real qfd_xcst_n, real node leaves) + quadrant clocks + feedthrough checks."""
    src = (ROOT / "tools/qwen_cluster/tb_template.sv").read_text()
    decl, conn, faces = [], [], []
    for c in range(4):
        for r in range(4):
            s = g.sname(c, r)
            decl.append(f"    wire [507:0] tap_{s}; wire trst_{s}; wire [513:0] t_out_{s};")
            conn += [f".tap_{s}(tap_{s})", f".trst_{s}(trst_{s})", f".t_out_{s}(t_out_{s})"]
            h = (c, r) != spare
            if h:
                decl.append(f"    wire [513:0] n_a_{s}, n_b_{s}, n_y_{s};")
                conn += [f".n_a_{s}(n_a_{s})", f".n_b_{s}(n_b_{s})", f".n_y_{s}(n_y_{s})"]
            na, nb, ny = (f"n_a_{s}", f"n_b_{s}", f"n_y_{s}") if h else ("514'd0", "514'd0", "")
            faces.append(f"    tb_q3h_tile_face #(.C({c}), .R({r}), .K({g.morton(c, r)}), .HOST({int(h)}), .TLD(TLD), "
                         f".LAT(Q3H_LAT_TAP{r}), .NOPS(NOPS)) u_f_{s} (.ck(ck), .rst_n(trst_{s}), .tap(tap_{s}), "
                         f".t_out(t_out_{s}), .n_a({na}), .n_b({nb}), .n_y({ny}));")
    conn = [f".ck_{q}(ck)" for q in QUADS] + [".rst_n(rst_n)", ".far(far)"] + [f".bc{c}(bcw[{c}])" for c in range(4)] + \
           [f".bco{c}(bco{c})" for c in range(4)] + [".rs(rs)", ".rs_i(rsi)", ".rs_o(rso)"] + conn
    inst = f"    {FABRIC} #(.MUT(MUT)) u_fab (\n        " + ",\n        ".join(conn) + ");"
    gs = " + ".join(f"(u_f_{g.sname(c, r)}.gseen != NOPS)" for c in range(4) for r in range(4))
    return (src.replace("//@DECL", "\n".join(decl)).replace("//@FABRIC", inst).replace("//@FACES", "\n".join(faces))
            .replace("/*@GSEEN*/", gs))


def pin_plan(rsx, E):
    """Tile checklist 10-17 (pins <= ~6 / um, spread; clock entries next to the register mass) under the reach rule:
    each data port's range is centred on its run lane at DENS pins / um (so the pin -> lane wire stays ~200 um and the
    first registered hop stays inside reach); overlapping ranges are pushed apart in run order.  Each quadrant clock
    entry sits in a free gap of its face nearest the quadrant's register centroid x (with rst_n / straps beside ck_sw)."""
    DENS = 3.0
    cen = {}
    for q in QUADS:
        ss = [x for x in E.sites if x["region"] == q]
        cen[q] = sum(x["at"][0] * x["bits"] for x in ss) / sum(x["bits"] for x in ss)
    lane = {f"bc{c}": g.run_x(c) for c in range(4)}
    lane.update({f"bco{c}": g.run_x(c) for c in range(4)})
    lane.update(rs=rsx["poly"][-1][0], rs_o=XT, rs_i=XT)
    note = {"bc": "column word (corridor run)", "bco": "registered feed-through to the far cluster",
            "rs": "block word {fault, valid, 512}", "rs_i": "DV: far-band rs word in", "rs_o": "DV: far-band rs word out (14 edges)"}
    faces = {"S": ["bc0", "rs", "bc1", "rs_o", "bc2", "bc3"], "N": ["bco0", "bco1", "rs_i", "bco2", "bco3"]}
    islands = {"S": [("sw", ["ck_sw", "rst_n", "far", "cid", "tie_hi", "tie_lo"]), ("se", ["ck_se"])],
               "N": [("nw", ["ck_nw"]), ("ne", ["ck_ne"])]}
    pins = []
    lo0, hi0 = 4.32, WIDTH - 4.32
    for f, names in faces.items():
        segs = []
        for n in sorted(names, key=lambda n: lane[n]):
            b = BW if n.startswith("rs") else DW
            w_ = b / DENS
            segs.append([n, b, lane[n] - w_ / 2, lane[n] + w_ / 2])
        for _ in range(50):                           # push apart (keep order), clamp to the face
            moved = False
            for a, b in zip(segs, segs[1:]):
                ov = a[3] + 1.0 - b[2]
                if ov > 1e-6:
                    a[2] -= ov / 2; a[3] -= ov / 2; b[2] += ov / 2; b[3] += ov / 2; moved = True
            if segs[0][2] < lo0:
                d = lo0 - segs[0][2]; segs[0][2] += d; segs[0][3] += d; moved = True
            if segs[-1][3] > hi0:
                d = segs[-1][3] - hi0; segs[-1][2] -= d; segs[-1][3] -= d; moved = True
            if not moved:
                break
        for n, b, a, c in segs:
            pins.append(dict(port=n, bits=b, face=f, layer="M5", range_um=[round(a, 3), round(c, 3)],
                             pins_per_um=round(b / (c - a), 3), lane_x=round(lane[n], 1),
                             note=note["bco" if n.startswith("bco") else "bc" if n.startswith("bc") else n]))
        occ = sorted((a, c) for _, _, a, c in segs)
        gaps = [(lo0, occ[0][0])] + [(x[1], y[0]) for x, y in zip(occ, occ[1:])] + [(occ[-1][1], hi0)]
        for q, nm in islands[f]:
            need = 2.0 + 1.0 * len(nm) + (6.0 if "cid" in nm else 0.0)
            best = min((gp for gp in gaps if gp[1] - gp[0] >= need),
                       key=lambda gp: abs(min(max(cen[q], gp[0] + need / 2), gp[1] - need / 2) - cen[q]))
            x0 = min(max(cen[q], best[0] + need / 2), best[1] - need / 2) - need / 2 + 1.0
            gaps.remove(best)
            gaps += [(best[0], x0 - 1.0), (x0 - 1.0 + need, best[1])]
            for n in nm:
                w_ = 6.0 if n == "cid" else 0.3
                pins.append(dict(port=n, bits=12 if n == "cid" else 1, face=f, layer="M5",
                                 range_um=[round(x0, 3), round(x0 + w_, 3)], pins_per_um=None,
                                 note=f"quadrant {q} entry island (register centroid x {cen[q]:.0f})"))
                x0 += w_ + 0.7
    for p_ in pins:
        if p_["pins_per_um"] and p_["pins_per_um"] > 6.0:
            raise SystemExit(f"pin density over 6/um: {p_}")
    for f in "NS":
        rs_ = sorted(p_["range_um"] + [p_["port"]] for p_ in pins if p_["face"] == f)
        for a, b in zip(rs_, rs_[1:]):
            if b[0] < a[1] + 0.2:
                raise SystemExit(f"pin overlap on {f}: {a} {b}")
    return pins, cen


def plot(path, host, spare, legs, rsx, E, pins):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    fig, ax = plt.subplots(figsize=(8, 17))
    qcol = {"sw": "#e8f0fb", "se": "#eaf7e8", "nw": "#fbf1e4", "ne": "#f5e8f7"}
    for c in range(4):
        for r in range(4):
            x0, y0 = g.COLX[c][0], g.ROWY[r]
            ax.add_patch(Rectangle((x0, y0), g.TW, g.TH, fc=qcol[tile_quad(c, r)], ec="#555", lw=0.6))
            hs = [f"{l},{i}" for (l, i), h in host.items() if h == (c, r)]
            ax.text(x0 + g.TW / 2, y0 + g.TH / 2, f"({c},{r}) {g.COL_ORIENT[c]} K{g.morton(c, r)}\n{tile_quad(c, r)}\n"
                    + ("node " + hs[0] if hs else "nl"), ha="center", va="center", fontsize=7)
    for k, (lo, hi) in g.CORR.items():
        ax.add_patch(Rectangle((lo, 0), hi - lo, HEIGHT, fc="none", ec="#bbb", lw=0.4, ls="--"))
        ax.text((lo + hi) / 2, HEIGHT + 30, k, ha="center", fontsize=7)
    ax.axhline(YMID, color="#999", lw=0.6, ls=":")
    ax.axvline(XT, color="#999", lw=0.6, ls=":")
    for x in legs + [rsx]:
        p = x["poly"]
        ax.plot([q[0] for q in p], [q[1] for q in p], color="#06c" if x is not rsx else "#a0a", lw=0.7)
    colr = {"sw": "#1f4e9c", "se": "#2a7a2a", "nw": "#b26b00", "ne": "#8a2a9c"}
    for s in E.sites:
        ax.plot(s["at"][0], s["at"][1], "s" if s.get("station") else ".", color=colr[s["region"]],
                ms=5 if s.get("station") else 2.5)
    for p_ in pins:
        lo, hi = p_["range_um"]
        y = 0 if p_["face"] == "S" else HEIGHT
        ax.plot([lo, hi], [y, y], lw=4, color="#a0a" if p_["port"].startswith("rs") else ("#c33" if p_["port"].startswith("bc") else "#333"))
        ax.text((lo + hi) / 2, y + (-70 if p_["face"] == "S" else 60), p_["port"], ha="center", fontsize=5.5, rotation=90)
    ax.set_xlim(-60, WIDTH + 60)
    ax.set_ylim(-260, HEIGHT + 200)
    ax.set_aspect("equal")
    ax.set_title(f"{MASTER} {WIDTH} x {HEIGHT} um (A/T/B 129.6): tile fill = clock quadrant; dots = registers coloured by\n"
                 "quadrant root; blue = tree legs, purple = rs / rs_i->rs_o; dotted = quadrant seams", fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=110)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["gen"])
    ap.add_argument("--hosts", default=str(Path(__file__).with_name("cb16_hosts.json")))
    a = ap.parse_args()
    host, spare = g.load_hosts(a.hosts)
    assert len(set(host.values())) == 15 and spare not in host.values()
    rs_t, bits, legs, rsx, t = g.evaluate(host, True)
    la = next(x for x in legs if x["node"] == (1, 0) and x["side"] == "a")
    lb = next(x for x in legs if x["node"] == (1, 2) and x["side"] == "a")
    mut_swap = {(1, 0, "a"): "t_out_%s" % g.sname(*lb["src"][1]), (1, 2, "a"): "t_out_%s" % g.sname(*la["src"][1])}
    rnodes, rleaves, rdepth, RD = g.reset_tree()
    fab, E, nft = gen_fabric(host, spare, legs, rsx, rnodes, rleaves, rdepth, RD, mut_swap)
    OUT_RTL.mkdir(parents=True, exist_ok=True)
    (OUT_RTL / f"{FABRIC}.sv").write_text(fab)
    (OUT_RTL / f"{MASTER}.sv").write_text(gen_cluster(spare))
    (ROOT / "rtl/test/tb_qcluster_fabric.sv").write_text(gen_tb(spare))
    hdr = ["// GENERATED by tools/qwen_cluster/qc_gen.py: compiled fixed latencies of qfd_c_b16_dv_fabric (edges)"] + \
          [f"localparam integer Q3H_LAT_TAP{r} = {g.tap_time(r)};" for r in range(4)] + \
          [f"localparam integer Q3H_LAT_BCO = {g.STAGE['exit']};",
           f"localparam integer Q3H_LAT_RS_FABRIC = {rs_t};",
           f"localparam integer QC_LAT_FT = {nft};",
           f"localparam integer Q3H_RST_DEPTH = {RD};"]
    (ROOT / "rtl/test/qcluster_lat.svh").write_text("\n".join(hdr) + "\n")
    pins, cen = pin_plan(rsx, E)
    # hop audit (pin to pin, Manhattan between consecutive registers of each run)
    by = {}
    for s in E.sites:
        by[s["inst"]] = s["at"]
    hops = [x["d"] / (x["k"] + 1) for x in legs] + [rsx["d"] / (rsx["k"] + 1)]
    for c in range(4):
        ch = g.chain_for(c)
        hops += [b[1] - a[1] for a, b in zip(ch, ch[1:])]
    ft = ft_chain()
    hops += [a[1] - b[1] for a, b in zip(ft, ft[1:])]
    if max(hops) > LIMIT:
        raise SystemExit(f"hop over reach: {max(hops):.1f} > {LIMIT}")
    nflops = sum(s["bits"] for s in E.sites)
    contract = dict(
        schema="opentallas.qwen.qcluster.contract.v1", master=MASTER, provisional=True,
        generator="tools/qwen_cluster/qc_gen.py", base="tools/qwen_cluster/cb_base.py (claude/q3h-cb-1016 e7e22d5b6)",
        spec="results/arch/qwen_cluster_1017/SPEC.md",
        outline_um=dict(w=WIDTH, h=HEIGHT), corridors={k: list(v) for k, v in g.CORR.items()},
        quadrant_seams=dict(x=XT, y=YMID), register_centroid_x={q: round(v, 1) for q, v in cen.items()},
        tiles=[dict(inst=f'u_t_{c}_{r}', at=[g.COLX[c][0], g.ROWY[r]], orient=g.COL_ORIENT[c]) for c in range(4) for r in range(4)],
        clocks={q: dict(pin=f"ck_{q}", fabric_flops=E.regions[q],
                        tiles=[g.sname(c, r) for c in range(4) for r in range(4) if tile_quad(c, r) == q],
                        tile_entry_pins=sum(len(NK_CLOCKS if (c, r) != spare else NL_CLOCKS)
                                            for c in range(4) for r in range(4) if tile_quad(c, r) == q)) for q in QUADS},
        fabric_flops=nflops, latency_edges=dict(tap={r: g.tap_time(r) for r in range(4)}, bco=g.STAGE["exit"],
                                                rs_fabric=rs_t, rs_i_to_rs_o=nft, reset=RD),
        hop_um=dict(limit=LIMIT, plan=HOP, max=round(max(hops), 1)),
        tree=dict(hosts={f"{l}_{i}": list(h) for (l, i), h in host.items()}, nl_slot=list(spare)),
        ports=pins, a0=dict(ref=A0_REF, nk=A0_NK, nl=A0_NL, nk_clocks=NK_CLOCKS, nl_clocks=NL_CLOCKS),
        die_crossing=dict(
            rule="(a) + (c): no die link crosses a qfd_c_b16_dv outline (die repeaters never sit inside it; M9 over the "
                 "cluster carries die PG only in dv2r8f).  Die links run in the band gaps, the slice / head row and the W "
                 "column; the only data that passes through a cluster is its own registered feedthroughs bc -> bco "
                 "(4 x 516 b, 17 edges) and rs_i -> rs_o (514 b, 14 edges).  No die feedthrough repeater sites are reserved.",
            registered_feedthroughs={"bc0..3->bco0..3": g.STAGE["exit"], "rs_i->rs_o": nft}),
        gating=["A0 views qfd_tile_nk_romleaf_a0 / nl twin not CLOSED (Q-ROMPARENT-2): diagnostics only, no binding"])
    OUT_ARCH.mkdir(parents=True, exist_ok=True)
    (OUT_ARCH / "cluster_contract_dv.json").write_text(json.dumps(contract, indent=1) + "\n")
    (OUT_ARCH / "relay_sites_dv.json").write_text(json.dumps(dict(schema="opentallas.qcluster.sites.v1", sites=E.sites), indent=1) + "\n")
    plot(OUT_ARCH / "cluster_dv_plan.png", host, spare, legs, rsx, E, pins)
    print(json.dumps(dict(outline=[WIDTH, HEIGHT], rs_fabric=rs_t, ft=nft, bco=g.STAGE["exit"], reset=RD,
                          hop_max=round(max(hops), 1), flops=nflops, regions=E.regions,
                          nk_clocks=len(NK_CLOCKS), nl_clocks=len(NL_CLOCKS)), indent=1))


if __name__ == "__main__":
    main()
