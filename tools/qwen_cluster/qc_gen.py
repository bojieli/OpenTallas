#!/usr/bin/env python3
"""Q-CLUSTER generator: qfd_c_b16_dv, the adopted dv2r8f compute-die cluster (results/arch/qwen_cluster_1017/SPEC.md).

Base: the CB cluster generator (claude/q3h-cb-1016 e7e22d5b6, copied as tools/qwen_cluster/cb_base.py, unchanged).
Its geometry helpers, morton tree, host map, leg router, column runs and reset tree are reused through module globals.
This generator changes:
  * corridors A / T / B 64.8 -> 129.6 um (SPEC 1; outline 2285.28 x 5184), reach: planning hop 390 <= limit 405;
  * Q-CLUSTER16 (10-18): SIXTEEN regional roots ck_c<c>r<r>, one per A0 tile (supersedes the eight below);
  * [was] eight regional clock roots ck_w0..ck_w3 / ck_e0..ck_e3 (SPEC 2, Q-CLUSTER2 10-17: the four quadrant roots measured
    26,984 sinks / iter-0 spread 3.9 ns on ck_sw, so each quadrant is split into its two tile rows): region = side (W/E
    of the T centreline) x tile row (seams at the row-gap centres); every register (station, relay, pin register, reset
    stage) and every A0 tile clock entry takes the root of the region it sits in; region seams are crossed only by
    registered hops.  Entries beside the register mass: rows 0 / 3 on the S / N face, rows 1 / 2 on the W / E face, each
    at its region's register centroid;
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
# Q-CLUSTER4 (coordinator 0de+6 (3)): L / R 43.2 -> 86.4 so the widened stations (51.84 / 56.16, faces <= 0.096 um/bit)
# fit with a >= 20-um channel to the A0 face (or the 8.64 straight tap stub of an xstn)
CORR_W = {"L": 86.4, "A": 146.88, "T": 146.88, "B": 146.88, "R": 86.4}
STRIP_UM = 86.4
LATTICE = 43.2
HOP, LIMIT = 390.0, 405.0
BW, DW = g.BW, g.DW
# Q-CLUSTER16 (owner 0ei 10-18): ONE clock region per A0 ROM-leaf tile, 16 roots ck_c<c>r<r> (column x tile row).
# Region of a fabric register: column band (seams at the A / T / B corridor centres; the T centre lane, the rs_i -> rs_o
# feedthrough, goes to column 2 as it went to E before) x tile-row band (seams at the row-gap centres).  Every A0 clock
# entry of tile (c, r) takes ck_c<c>r<r>.  Region seams are crossed only by single registered hops <= 405 um between
# neighbouring regions (region_audit.py), each a fixed one-edge link: no added latency, no flow control.
QUADS = tuple(f"c{c}r{r}" for c in range(4) for r in range(4))   # regional clock roots (name kept: was the four quadrants)
REF_QUADS = ("w0", "w1", "w2", "w3", "e0", "e1", "e2", "e3")      # the c392aa534 reference fabric's eight roots


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
YSEAM = [(g.ROWY[r] + g.TH + g.ROWY[r + 1]) / 2 for r in range(3)]   # region seams = row-gap centres
YMID = YSEAM[1]
XSEAM = [g.ccx("A"), XT, g.ccx("B")]                                 # column-band seams = A / T / B corridor centres


def col_of(x):
    # a register exactly on a seam (the T centre lane) belongs to the higher column (as the T lane went to E before)
    return sum(x >= v - 1e-6 for v in XSEAM)


def row_of(y):
    return sum(y >= v for v in YSEAM)


def quad(x, y):
    """clock region of a register at (x, y): column band x tile-row band (one A0 tile per region)"""
    return f"c{col_of(x)}r{row_of(y)}"


def tile_quad(c, r):
    return f"c{c}r{r}"


A0_REF = "30d3d3510"   # Q-ROMPARENT-2 c1r6 (codex/romleaf-native-1621): ck_tx4/5 on E face M4, mirror-legal
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


def ft_chain(rs_x):
    """rs_i -> rs_o.  Q-DV dv2r8f5 delta (10-17): rs_i sits on the N face straight above rs (x of the rs lane), so every
    far-cluster rs crosses the band gap face to face with no jog; inside the cluster the word runs along the N strip to
    the T centre lane and down T to rs_o on the S face.  Registers every <= LIMIT along that path (pin registers at both
    ends)."""
    yN, yS = HEIGHT - g.STRIP / 2, g.STRIP / 2
    P = [(rs_x, yN), (XT, yN), (XT, yS)]
    L = g.plen(P)
    k = max(0, math.ceil(L / (LIMIT - 40.0)) - 1)   # Q-CLUSTER4: 40-um margin: T-lane stations step around the 56.16-wide xstn pairs
    return [g.along(P, i / (k + 1)) for i in range(k + 2)]


class Emit:
    def __init__(self):
        self.L, self.sites, self.regions = [], [], {q: 0 for q in QUADS}

    def w(self, s):
        self.L.append(s)

    def stage(self, name, width, d, q, x, y, note=""):
        r = quad(x, y)
        self.regions[r] += width
        # Q-CLUSTER3: every wide stage is a hard station tile (qfd_c_stn516 / qfd_c_stn514, own clock pin + local tree);
        # only the 1-bit reset stages stay soft flops of the cluster
        hard = width > 1
        self.sites.append(dict(inst=f"u_fab.{name}", at=[round(x, 3), round(y, 3)], region=r, bits=width,
                               master=f"qfd_c_stn{width}" if hard else None, d=d, q=q))
        cell = f"qfd_c_stn{width}" if hard else f"qfd_q3h_stn #(.W({width}), .N(1))"
        self.w(f"    wire [{width - 1}:0] {q};  {cell} {name} (.ck(ck_{r}), .d({d}), .q({q}));"
               f"   // ({x:.2f}, {y:.2f}) {r}{(' ' + note) if note else ''}")


def gen_fabric(host, spare, legs, rsx, rnodes, rleaves, rdepth, RD, mut_swap):
    E = Emit()
    w = E.w
    w("`timescale 1ns/1ps")
    w(f"// GENERATED by tools/qwen_cluster/qc_gen.py -- do not edit.  {FABRIC}: every register of qfd_c_b16_dv outside the")
    w("// tiles (Q-CLUSTER 2026-10-17, results/arch/qwen_cluster_1017/SPEC.md): the four column runs (entry / relays /")
    w("// qfd_xcst_n / exit), the morton reduction legs, the rs exit run, the DV far-band feedthrough rs_i -> rs_o and the")
    w("// equal-depth reset tree.  Each register sits in one of 16 clock regions (one per A0 tile) and takes its root; seams")
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
                E.sites.append(dict(inst=f"u_fab.u_x_{s}", at=[round(x, 3), round(y, 3)], region=q, bits=DW, station=True,
                                    master="qfd_c_xstnw" if c in (1, 3) else "qfd_c_xstn", d=cin, q=f"dn{c}_{nm}", col=c, row=r))
                w(f"    wire [{DW-1}:0] dn{c}_{nm};")
                w(f"    {'qfd_c_xstnw' if c in (1, 3) else 'qfd_c_xstn'} u_x_{s} (.ck(ck_{q}), .rst_n(rstl_{g.E_FACE_CORR[c]}_{r}), .sidx({{far, {b1}, {b0}}}), .b_d({cin}),"
                  f" .a_d(dn{c}_{nm}), .tap_d(tap_{s}));   // ({x:.2f}, {y:.2f}) {q}")
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
    ch = ft_chain(rsx["poly"][-1][0])
    w(f"    // ---- DV far-band feedthrough rs_i (N) -> rs_o (S): {len(ch)} registers in the T centre lane, hop <= "
      f"{max(abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in zip(ch, ch[1:])):.1f} um")
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
    w("// Sixteen regional clock roots (Q-CLUSTER16): tile (c, r) takes ck_c<c>r<r> on every clock entry; each root is")
    w("// centre-fed (die area pin) and its tree balances to the child flops (A0 / station ETM insertion).  Straps cid /")
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


# ---- Q-CLUSTER3: hard station placement (qc_stn_kit.py masters) -------------------------------------------------------
SW, XW, XH = 51.84, 56.16, 86.4   # qfd_c_stn5xx 51.84 x 51.84; qfd_c_xstn(w) 56.16 x 86.4 (qc_stn_kit.py, Q-CLUSTER4)
SL = 8.64                    # station snapping step in the corridors / y (on the 4.32 child lattice: track-safe for M3 / M4 / M5)
XSTN_DY = 414.72             # xstn origin above its A0 row origin: tap pins at the A0 tap y range 437.184..485.856
# Q-CLUSTER4 channel rule (coordinator 0de+6 (4)): < 20 um only between pin-free sides; a channel facing pins is sized to
# the bits crossing it.  Station E / W sides are pin-free (data on S / N), the A0 W / E faces carry pins.
GAP_A0 = 21.6                # station side <-> A0 face (A0 pins: >= 20 um)
GAP_TAP = 8.64               # xstn tap face <-> A0 tap face: 508 straight M4 stubs, one track each (= the bits crossing)
GAP_X = 8.64                 # station <-> station side by side (both sides pin-free)
GAP_Y = 21.6                 # station <-> station stacked (S / N pin faces facing) and row-gap station <-> tile rows
GAP_EDGE = 8.64              # L / R strip station <-> cluster W / E edge (pin-free but for the two M4 clock entries)
GAP = GAP_Y


def _sn(v):
    return round(round(v / SL) * SL, 4)


def place_stations(E, fabric_rtl, spare):
    """Each hard station of E.sites -> (x0, y0, orient) on the 8.64 lattice near its planned site.  Orientation from the
    word's flow: R0 = d on S / q on N (northward), MX = southward; xstn R0 (tap E) or MY (tap W) toward its tile.
    Returns the child list and the pin-to-pin hop audit (raises on overlap or a hop > LIMIT)."""
    alias = {}
    for m in re.finditer(r"qfd_q3h_run #\(.*?\) \w+ \(\.ck\(\w+\), \.d\((\w+)\), \.q\((\w+)\)\)", fabric_rtl):
        alias[m.group(2)] = m.group(1)
    for m in re.finditer(r"assign (\w+) = (\w+);", fabric_rtl):
        alias[m.group(1)] = m.group(2)
    def res(n):
        while n in alias:
            n = alias[n]
        return n
    hard = [st for st in E.sites if st.get("master")]
    prod = {st["q"]: st for st in hard}
    cons = {}
    for st in hard:
        cons.setdefault(res(st["d"]), []).append(st)
    def end_y(n):     # planned y of a non-station endpoint (pins / A0 tile faces)
        n = res(n)
        if n in prod:
            return prod[n]["at"][1]
        if n.startswith(("bc", "rs_i")):
            return 0.0 if n.startswith("bc") else HEIGHT
        mm = re.match(r"(t_out|n_y)_(\d)_(\d)", n)
        if mm:
            return g.ROWY[int(mm.group(3))] + 362.0
        return None
    out_y = {}         # q net -> consumer endpoint y (pins / tiles) when no station consumes it
    for m in re.finditer(r"assign (bco\d|rs|rs_o) = (\w+);", fabric_rtl):
        out_y[res(m.group(2))] = HEIGHT if m.group(1).startswith("bco") else 0.0
    for m in re.finditer(r"assign (n_[ab])_(\d)_(\d) = (\w+);", fabric_rtl):
        out_y[res(m.group(4))] = g.ROWY[int(m.group(3))] + 160.0
    for m in re.finditer(r"\.d\((\w+)\), \.q\((n_a_(\d)_(\d))\)", fabric_rtl):
        out_y[res(m.group(1))] = g.ROWY[int(m.group(4))] + 160.0
    kids = []
    corr = {k: v for k, v in g.CORR.items()}
    for st in hard:
        x, y = st["at"]
        if st["master"].startswith("qfd_c_xstn"):
            c, r = st["col"], st["row"]
            # tap face GAP_TAP from its tile: lanes L / T(c2) have the tile E of the station, T(c1) / R W of it
            x0 = {0: corr["L"][1] - GAP_TAP - XW, 1: corr["T"][0] + GAP_TAP, 2: corr["T"][1] - GAP_TAP - XW,
                  3: corr["R"][0] + GAP_TAP}[c]
            if c in (1, 3):    # tile W of the lane: the tap-W master (no MY: track lattice), R0
                st["master"] = "qfd_c_xstnw"
            kids.append(dict(st=st, x=round(x0, 4), y=round(g.ROWY[r] + XSTN_DY, 4), w=XW, h=XH, orient="R0"))
            continue
        yp = end_y(st["d"])
        cs = cons.get(st["q"])
        yn = cs[0]["at"][1] if cs else out_y.get(st["q"])
        dy = (y - yp if yp is not None else 0.0) + (yn - y if yn is not None else 0.0)
        o = "R0" if dy >= 0 else "MX"
        k = next((k for k, (lo, hi) in corr.items() if lo - 1e-6 <= x <= hi + 1e-6), None)
        x0 = _sn(x - SW / 2)
        if k is not None:
            lo, hi = corr[k]
            if k == "L":          # 86.4-um strip: GAP_EDGE to the cluster edge, 25.92 (>= GAP_A0) to the A0 face
                lo_ok = hi_ok = lo + GAP_EDGE
            elif k == "R":
                lo_ok = hi_ok = hi - GAP_EDGE - SW
            else:
                lo_ok, hi_ok = lo + GAP_A0, hi - SW - GAP_A0
            x0 = min(max(x0, lo_ok), hi_ok)
            y0 = _sn(y - SW / 2)
        else:          # row-gap / S-N strip station (horizontal leg): keep GAP to the tile rows above / below
            glo, ghi = next((a, b) for a, b in g.CHANNELS if a - 1e-6 <= y <= b + 1e-6)
            y0 = min(max(_sn(y - SW / 2), glo + GAP), ghi - GAP - SW)
        # Q-CLUSTER4: 12.96 = 86.4 strip - GAP_Y - 51.84: the face toward the S / N edge carries only this pin register's own
        # straight pin connections (the bits crossing); the face toward the tile row keeps GAP_Y
        y0 = min(max(y0, 12.96), HEIGHT - 12.96 - SW)
        kids.append(dict(st=st, x=round(x0, 4), y=round(y0, 4), w=SW, h=SW, orient=o))
    # overlap: stations among themselves (GAP) and against the A0 tiles (GAP); resolve station-station by stepping y
    tiles = [(g.COLX[c][0], g.ROWY[r], g.TW, g.TH) for c in range(4) for r in range(4)]
    def clash(a, b, gap, gy=None):
        gy = gap if gy is None else gy
        return not (a[0] + a[2] + gap <= b[0] + 1e-6 or b[0] + b[2] + gap <= a[0] + 1e-6 or
                    a[1] + a[3] + gy <= b[1] + 1e-6 or b[1] + b[3] + gy <= a[1] + 1e-6)
    placed = []
    for kd in sorted(kids, key=lambda k: (not k["st"]["master"].startswith("qfd_c_xstn"), k["y"])):
        base = kd["y"]
        for step in [0] + [s * j for j in range(1, 30) for s in (1, -1)]:
            kd["y"] = round(base + step * SL, 4)
            box = (kd["x"], kd["y"], kd["w"], kd["h"])
            if kd["y"] < 12.96 - 1e-6 or kd["y"] + kd["h"] > HEIGHT - 12.96 + 1e-6:
                continue
            tg = GAP_TAP if kd["st"]["master"].startswith("qfd_c_xstn") else GAP_A0
            if all(not clash(box, (p["x"], p["y"], p["w"], p["h"]), GAP_X, GAP_Y) for p in placed) and \
               all(not clash(box, t, tg - 1e-6, GAP_Y - 1e-6) for t in tiles):
                break
        else:
            raise SystemExit(f"station overlap unresolved: {kd['st']['inst']} at {kd['x']},{base}")
        placed.append(kd)
    if any(p["x"] < -1e-6 or p["x"] + p["w"] > WIDTH + 1e-6 or p["y"] < -1e-6 or p["y"] + p["h"] > HEIGHT + 1e-6 for p in placed):
        raise SystemExit("station outside the cluster outline")
    # pin-to-pin hop audit between consecutive registers (station face centres; endpoints at their planned pins)
    def face(p, which):   # which = "d" (input face) / "q" (output face) centre
        cx = p["x"] + p["w"] / 2
        south = (which == "d") == (p["orient"] in ("R0", "MY"))
        return cx, p["y"] if south else p["y"] + p["h"]
    byq = {p["st"]["q"]: p for p in placed}
    byd = {}
    for p in placed:
        byd.setdefault(res(p["st"]["d"]), []).append(p)
    def hop(a, b):
        (ax, ay), (bx, by) = face(a, "q"), face(b, "d")
        return abs(ax - bx) + abs(ay - by)
    def worst(p):
        h = [hop(byq[res(p["st"]["d"])], p)] if res(p["st"]["d"]) in byq else []
        return max(h + [hop(p, c) for c in byd.get(p["st"]["q"], [])] + [0.0])
    horiz = [p for p in placed if not p["st"]["master"].startswith("qfd_c_xstn") and p["h"] == SW and
             not any(lo - 1e-6 <= p["st"]["at"][0] <= hi + 1e-6 for lo, hi in corr.values())]
    for _ in range(4):   # horizontal (row-gap / strip) stations: the orientation that shortens their two hops
        for p in horiz:
            best = min(("R0", "MX"), key=lambda o: (p.__setitem__("orient", o), worst(p))[1])
            p["orient"] = best
    hops = []
    for p in placed:
        src = byq.get(res(p["st"]["d"]))
        if src is None:
            continue
        (ax, ay), (bx, by) = face(src, "q"), face(p, "d")
        hops.append((abs(ax - bx) + abs(ay - by), src["st"]["inst"], p["st"]["inst"]))
    hmax = max(hops)
    if hmax[0] > LIMIT:
        raise SystemExit(f"station hop over reach after snapping: {hmax}")
    disp = max(abs(p["x"] + p["w"] / 2 - p["st"]["at"][0]) + abs(p["y"] + p["h"] / 2 - p["st"]["at"][1])
               for p in placed if not p["st"]["master"].startswith("qfd_c_xstn"))
    return placed, dict(max_um=round(hmax[0], 1), pair=hmax[1:], n=len(hops), max_site_displacement_um=round(disp, 1))


def gen_lockstep_tb(spare):
    """Q-CLUSTER16 lockstep bench: the 16-region fabric (this generator, MUT) against the 8-region fabric it replaces
    (rtl/test/qcluster_ref_8r_be7b9ff15.sv, MUT 0; the c392aa534 soft reference differs by design since Q-CLUSTER4:
    rs_i -> rs_o 16 -> 17 and reset 18 -> 19 edges), every input random every cycle (+ reset pulses), every output compared
    every cycle.  +FAR selects the far-band strap."""
    ins = [("rst_n", 1), ("far", 1)] + [(f"bc{c}", DW) for c in range(4)] + [("rs_i", BW)]
    outs = [(f"bco{c}", DW) for c in range(4)] + [("rs", BW), ("rs_o", BW)]
    for c in range(4):
        for r in range(4):
            sn = g.sname(c, r)
            ins.append((f"t_out_{sn}", BW))
            outs += [(f"tap_{sn}", DW - 8), (f"trst_{sn}", 1)]
            if (c, r) != spare:
                ins.append((f"n_y_{sn}", BW))
                outs += [(f"n_a_{sn}", BW), (f"n_b_{sn}", BW)]
    L = ["`timescale 1ns/1ps",
         "// GENERATED by tools/qwen_cluster/qc_gen.py (Q-CLUSTER16) -- do not edit.  Lockstep: the 16-region fabric (MUT) vs the",
         "// 8-region reference qfd_c_b16_dv_fabric_ref8 (be7b9ff15 = 0ed8da289 RTL, MUT 0); random inputs every cycle, outputs compared every cycle.",
         "module tb;",
         "    parameter integer MUT = 0;",
         "    parameter integer NCYC = 6000;",
         "    reg ck = 0;",
         "    always #0.5 ck = ~ck;"]
    for n, w_ in ins:
        L.append(f"    reg  [{w_ - 1}:0] {n};")
    for n, w_ in outs:
        L.append(f"    wire [{w_ - 1}:0] {n}_h, {n}_r;")
    def conn(sfx, qs=QUADS):
        c_ = [f".ck_{q}(ck)" for q in qs] + [f".{n}({n})" for n, _ in ins] + [f".{n}({n}_{sfx})" for n, _ in outs]
        return ",\n        ".join(c_)
    L.append(f"    {FABRIC} #(.MUT(MUT)) u_h (\n        {conn('h')});")
    L.append(f"    {FABRIC}_ref8 #(.MUT(0)) u_r (\n        {conn('r', REF_QUADS)});")
    L.append("    function automatic [1023:0] rnd1024(input integer dummy);")
    L.append("        integer k; begin for (k = 0; k < 32; k = k + 1) rnd1024[32*k +: 32] = $urandom; end")
    L.append("    endfunction")
    L.append("    integer cyc = 0, bad = 0, nfar = 0;")
    L.append("    initial begin")
    L.append("        if ($test$plusargs(\"FAR\")) nfar = 1;")
    L.append("        far = nfar[0]; rst_n = 0;")
    for n, w_ in ins[2:]:
        L.append(f"        {n} = 0;")
    L.append("    end")
    L.append("    always @(negedge ck) begin")
    L.append("        cyc <= cyc + 1;")
    L.append("        rst_n <= !((cyc < 24) || (cyc >= 2500 && cyc < 2530));")
    for n, w_ in ins[2:]:
        L.append(f"        {n} <= rnd1024(0);")
    cmp_ = " ||\n            ".join(f"({n}_h !== {n}_r)" for n, _ in outs)
    L.append("        if (cyc > 2 && (" + cmp_ + ")) begin")
    L.append("            bad = bad + 1;")
    L.append("            if (bad <= 5) $display(\"MISMATCH cycle %0d\", cyc);")
    L.append("        end")
    L.append("        if (cyc == NCYC) begin")
    L.append("            if (bad == 0) $display(\"LOCKSTEP_PASS MUT %0d FAR %0d cycles %0d\", MUT, nfar, NCYC);")
    L.append("            else $display(\"LOCKSTEP_FAIL MUT %0d FAR %0d mismatching cycles %0d\", MUT, nfar, bad);")
    L.append("            $finish;")
    L.append("        end")
    L.append("    end")
    L.append("endmodule")
    return "\n".join(L) + "\n"


def pin_plan(rsx, E):
    """Tile checklist 10-17 (pins <= ~6 / um, spread; clock entries next to the register mass) under the reach rule:
    each data port's range is centred on its run lane at DENS pins / um (so the pin -> lane wire stays ~200 um and the
    first registered hop stays inside reach); overlapping ranges are pushed apart in run order.  Each quadrant clock
    entry sits in a free gap of its face nearest the quadrant's register centroid x (with rst_n / straps beside ck_sw)."""
    DENS = 3.0
    cen, ceny = {}, {}
    for q in QUADS:
        ss = [x for x in E.sites if x["region"] == q]
        cen[q] = sum(x["at"][0] * x["bits"] for x in ss) / sum(x["bits"] for x in ss)
        ceny[q] = sum(x["at"][1] * x["bits"] for x in ss) / sum(x["bits"] for x in ss)
    lane = {f"bc{c}": g.run_x(c) for c in range(4)}
    lane.update({f"bco{c}": g.run_x(c) for c in range(4)})
    lane.update(rs=rsx["poly"][-1][0], rs_o=XT, rs_i=rsx["poly"][-1][0])   # rs_i above rs (Q-DV dv2r8f5)
    note = {"bc": "column word (corridor run)", "bco": "registered feed-through to the far cluster",
            "rs": "block word {fault, valid, 512}", "rs_i": "DV: far-band rs word in", "rs_o": "DV: far-band rs word out (rs_i + 15 edges)"}
    faces = {"S": ["bc0", "rs", "bc1", "rs_o", "bc2", "bc3"], "N": ["bco0", "rs_i", "bco1", "bco2", "bco3"]}
    islands = {"S": [(QUADS[0], [f"ck_{QUADS[0]}", "rst_n", "far", "cid", "tie_hi", "tie_lo"])] +
                    [(f"c{c}r0", [f"ck_c{c}r0"]) for c in (1, 2, 3)],
               "N": [(f"c{c}r3", [f"ck_c{c}r3"]) for c in range(4)]}
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
                                 note=f"region {q} entry island (register centroid x {cen[q]:.0f}, y {ceny[q]:.0f})"))
                x0 += w_ + 0.7
    # interior rows 1 / 2 have no S / N face within 1.3 mm: their entry is on the W / E face (M4) at the region's
    # register centroid y; the die delivers them along the inter-cluster sliver (no data pin on W / E)
    # Q-CLUSTER16: these face entries only seed the IO placer; the centre-fed kits move every ck_<q> to an M7 area pin
    # inside its region at PRE_CTS (qfd_c_b16_dv_centre_feed.tcl).  Columns 0 / 1 enter on W, 2 / 3 on E (offset 3 um).
    for q in [f"c{c}r{r}" for r in (1, 2) for c in range(4)]:
        c = int(q[1])
        f = "W" if c < 2 else "E"
        y0 = round(ceny[q] + (3.0 if c in (1, 2) else 0.0), 3)
        pins.append(dict(port=f"ck_{q}", bits=1, face=f, layer="M4", range_um=[y0, round(y0 + 0.3, 3)], pins_per_um=None,
                         note=f"region {q} entry (register centroid y {ceny[q]:.0f}, x {cen[q]:.0f})"))
    for p_ in pins:
        if p_["pins_per_um"] and p_["pins_per_um"] > 6.0:
            raise SystemExit(f"pin density over 6/um: {p_}")
    for f in "NSWE":
        rs_ = sorted(p_["range_um"] + [p_["port"]] for p_ in pins if p_["face"] == f)
        for a, b in zip(rs_, rs_[1:]):
            if b[0] < a[1] + 0.2:
                raise SystemExit(f"pin overlap on {f}: {a} {b}")
    return pins, cen, ceny


def plot(path, host, spare, legs, rsx, E, pins, stations=()):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    fig, ax = plt.subplots(figsize=(8, 17))
    _lt = ["#e8f0fb", "#fbf1e4", "#eaf7e8", "#f5e8f7"]
    _dk = ["#1f4e9c", "#b26b00", "#2a7a2a", "#8a2a9c"]
    qcol = {f"c{c}r{r}": _lt[(c + r) % 2 + 2 * (c % 2)] for c in range(4) for r in range(4)}
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
    for v in YSEAM:
        ax.axhline(v, color="#999", lw=0.6, ls=":")
    for v in XSEAM:
        ax.axvline(v, color="#999", lw=0.6, ls=":")
    for x in legs + [rsx]:
        p = x["poly"]
        ax.plot([q[0] for q in p], [q[1] for q in p], color="#06c" if x is not rsx else "#a0a", lw=0.7)
    colr = {f"c{c}r{r}": _dk[(c + r) % 2 + 2 * (c % 2)] for c in range(4) for r in range(4)}
    for s in E.sites:
        if not s.get("master"):
            ax.plot(s["at"][0], s["at"][1], ".", color=colr[s["region"]], ms=2.5)
    for p_ in stations:
        ax.add_patch(Rectangle((p_["x"], p_["y"]), p_["w"], p_["h"], fc=colr[p_["st"]["region"]], ec="k", lw=0.3,
                               alpha=0.9 if p_["st"]["master"].startswith("qfd_c_xstn") else 0.6))
    for p_ in pins:
        lo, hi = p_["range_um"]
        if p_["face"] in "WE":
            x = 0 if p_["face"] == "W" else WIDTH
            ax.plot([x, x], [lo - 25, hi + 25], lw=6, color="#d00")
            ax.text(x + (-55 if p_["face"] == "W" else 10), lo, p_["port"], fontsize=6, color="#d00")
            continue
        y = 0 if p_["face"] == "S" else HEIGHT
        ax.plot([lo, hi], [y, y], lw=4, color="#a0a" if p_["port"].startswith("rs") else ("#c33" if p_["port"].startswith("bc") else "#333"))
        ax.text((lo + hi) / 2, y + (-70 if p_["face"] == "S" else 60), p_["port"], ha="center", fontsize=5.5, rotation=90)
    ax.set_xlim(-140, WIDTH + 140)
    ax.set_ylim(-260, HEIGHT + 200)
    ax.set_aspect("equal")
    ax.set_title(f"{MASTER} {WIDTH} x {HEIGHT} um: tile fill = clock region (16 roots, one per A0); dots = registers coloured by\n"
                 "region root (squares = hard station tiles, dots = soft reset stages); red = W/E clock entries; blue = tree legs, purple = rs / rs_i->rs_o; dotted = region seams", fontsize=8)
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
    (ROOT / "rtl/test/tb_qcluster_lockstep.sv").write_text(gen_lockstep_tb(spare))
    hdr = ["// GENERATED by tools/qwen_cluster/qc_gen.py: compiled fixed latencies of qfd_c_b16_dv_fabric (edges)"] + \
          [f"localparam integer Q3H_LAT_TAP{r} = {g.tap_time(r)};" for r in range(4)] + \
          [f"localparam integer Q3H_LAT_BCO = {g.STAGE['exit']};",
           f"localparam integer Q3H_LAT_RS_FABRIC = {rs_t};",
           f"localparam integer QC_LAT_FT = {nft};",
           f"localparam integer Q3H_RST_DEPTH = {RD};"]
    (ROOT / "rtl/test/qcluster_lat.svh").write_text("\n".join(hdr) + "\n")
    pins, cen, ceny = pin_plan(rsx, E)
    stations, st_hops = place_stations(E, fab, spare)
    # hop audit (pin to pin, Manhattan between consecutive registers of each run)
    by = {}
    for s in E.sites:
        by[s["inst"]] = s["at"]
    hops = [x["d"] / (x["k"] + 1) for x in legs] + [rsx["d"] / (rsx["k"] + 1)]
    for c in range(4):
        ch = g.chain_for(c)
        hops += [b[1] - a[1] for a, b in zip(ch, ch[1:])]
    ft = ft_chain(rsx["poly"][-1][0])
    hops += [abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in zip(ft, ft[1:])]
    if max(hops) > LIMIT:
        raise SystemExit(f"hop over reach: {max(hops):.1f} > {LIMIT}")
    nflops = sum(s["bits"] for s in E.sites)
    contract = dict(
        schema="opentallas.qwen.qcluster.contract.v1", master=MASTER, provisional=True,
        generator="tools/qwen_cluster/qc_gen.py", base="tools/qwen_cluster/cb_base.py (claude/q3h-cb-1016 e7e22d5b6)",
        spec="results/arch/qwen_cluster_1017/SPEC.md",
        outline_um=dict(w=WIDTH, h=HEIGHT), corridors={k: list(v) for k, v in g.CORR.items()},
        quadrant_seams=dict(x=XT, y=YMID), region_seams=dict(x=[round(v, 3) for v in XSEAM], y=[round(v, 3) for v in YSEAM],
                          rule="column = #x-seams <= x (a register on a seam takes the higher column); row = #y-seams <= y"),
        register_centroid={q: [round(cen[q], 1), round(ceny[q], 1)] for q in QUADS},
        tiles=[dict(inst=f'u_t_{c}_{r}', at=[g.COLX[c][0], g.ROWY[r]], orient=g.COL_ORIENT[c]) for c in range(4) for r in range(4)],
        clocks={q: dict(pin=f"ck_{q}", fabric_flops=E.regions[q],
                        tiles=[g.sname(c, r) for c in range(4) for r in range(4) if tile_quad(c, r) == q],
                        tile_entry_pins=sum(len(NK_CLOCKS if (c, r) != spare else NL_CLOCKS)
                                            for c in range(4) for r in range(4) if tile_quad(c, r) == q)) for q in QUADS},
        fabric_flops=nflops, latency_edges=dict(tap={r: g.tap_time(r) for r in range(4)}, bco=g.STAGE["exit"],
                                                rs_fabric=rs_t, rs_i_to_rs_o=nft, reset=RD),
        hop_um=dict(limit=LIMIT, plan=HOP, max=round(max(hops), 1)),
        tree=dict(hosts={f"{l}_{i}": list(h) for (l, i), h in host.items()}, nl_slot=list(spare)),
        ports=pins,
        stations=dict(note="Q-CLUSTER3: hard fabric station tiles (qc_stn_kit.py masters), origins on the 4.32 lattice; "
                           ">= 8.64-um channels in A / T / B / row gaps, 4.32 to the A0 face and the cluster edge in L / R; R0 = word flows north (d S, q N), MX = south; "
                           "xstn = tap E, xstnw = tap W (both R0)",
                      masters={m: sum(1 for p_ in stations if p_["st"]["master"] == m)
                               for m in ("qfd_c_stn516", "qfd_c_stn514", "qfd_c_xstn", "qfd_c_xstnw")},
                      soft_reset_flops=sum(1 for st in E.sites if not st.get("master")),
                      hop_pin_to_pin=st_hops,
                      children=[dict(inst=p_["st"]["inst"], master=p_["st"]["master"], at=[p_["x"], p_["y"]],
                                     orient=p_["orient"], region=p_["st"]["region"]) for p_ in stations]),
        a0=dict(ref=A0_REF, nk=A0_NK, nl=A0_NL, nk_clocks=NK_CLOCKS, nl_clocks=NL_CLOCKS),
        die_crossing=dict(
            rule="(a) + (c): no die link crosses a qfd_c_b16_dv outline (die repeaters never sit inside it; M9 over the "
                 "cluster carries die PG only in dv2r8f).  Die links run in the band gaps, the slice / head row and the W "
                 "column; the only data that passes through a cluster is its own registered feedthroughs bc -> bco "
                 "(4 x 516 b, 17 edges) and rs_i -> rs_o (514 b, 15 edges).  No die feedthrough repeater sites are reserved.",
            registered_feedthroughs={"bc0..3->bco0..3": g.STAGE["exit"], "rs_i->rs_o": nft}),
        far_position="ONE master: in the far bands (0 / 3) rs_i is a declared-idle terminus tied to the instance's own "
                     "tie_lo by the die (valid bit 0 every cycle) and rs_o is left unconnected (output only)",
        gating=["A0 views qfd_tile_nk_romleaf_a0 / nl twin not CLOSED (Q-ROMPARENT-2): diagnostics only, no binding"])
    OUT_ARCH.mkdir(parents=True, exist_ok=True)
    (OUT_ARCH / "cluster_contract_dv.json").write_text(json.dumps(contract, indent=1) + "\n")
    tsv = ["# prefix\tx\ty\txlo\txhi  (qc_gen.py; fabric_sites_place.tcl)"]
    for st in E.sites:
        if st.get("master"):
            continue          # hard station: placed as a child macro (contract stations.children), not a soft site
        x, y = st["at"]
        cor = next(((lo, hi) for lo, hi in g.CORR.values() if lo - 1e-6 <= x <= hi + 1e-6), (max(0.0, x - 15), min(WIDTH, x + 15)))
        tsv.append(f"{st['inst']}\t{x}\t{y}\t{cor[0]}\t{cor[1]}")
    (ROOT / "physical/qcluster/qfd_c_b16_dv_sites.tsv").write_text("\n".join(tsv) + "\n")
    (OUT_ARCH / "relay_sites_dv.json").write_text(json.dumps(dict(schema="opentallas.qcluster.sites.v1", sites=E.sites), indent=1) + "\n")
    plot(OUT_ARCH / "cluster_dv_plan.png", host, spare, legs, rsx, E, pins, stations)
    print(json.dumps(dict(outline=[WIDTH, HEIGHT], rs_fabric=rs_t, ft=nft, bco=g.STAGE["exit"], reset=RD,
                          hop_max=round(max(hops), 1), flops=nflops, regions=E.regions,
                          nk_clocks=len(NK_CLOCKS), nl_clocks=len(NL_CLOCKS)), indent=1))


if __name__ == "__main__":
    main()
