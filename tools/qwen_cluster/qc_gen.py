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
# Q-CLUSTER-LANDALL (coordinator 0fy 10-18, owner 0fd): the cluster is clocked like the die.  Each of the 16 regions has
# its OWN small local tree, and EVERY multi-bit region-to-region crossing is LANDED (LANDING-CONTRACT L1-L7,
# rtl/physical/qcluster/qfd_c_land.sv): the source register -> RING (qfd_c_land_w on ck_<src>, beside the source,
# flop-first) -> READ (qfd_c_land_r on ck_<dst>, slot (rc - K) mod D -> registered o, beside the destination register)
# -> the destination register.  Added latency E + 1 = 3 edges per landed crossing (K = E: both halves' epochs come from
# reset-tree runs of EQUAL depth, G == R0), compiler-known; the tree / column / feedthrough latencies are re-aligned
# with soft pad stages (hard station sites unchanged).  Cross-region skew is then free inside the window
# (E - D) T + t_hold < dL < E T - t_cq - t_setup (+/- ~1.6 ns at 833 ps); only intra-region spread <= 80 must hold.
# The 1-bit reset-tree hops are NOT landed (they define the epochs): they stay single registered hops, timed
# single-cycle with the inter-region uncertainty (quasi-static; hold repair is cheap on 1-bit nets).
# 'one' (Q-CL16-LAND 81deafc7e, the single landed crossing u_leg_3_1b_0 -> u_leg_3_1b_1) is superseded and not kept:
# that RTL is reproducible from 81deafc7e.  'off' = the unlanded Q-CLUSTER16 fabric.
LAND_E, LAND_D = 2, 4
LAND_A = LAND_E + 1                # added edges per landed crossing (ring write + E)
LAND_MUT = "leg_3_1b_1"            # the landing the bench mutants 6 / 7 act on (the Q-CL16-EARLY failing crossing)
FW_UM, ROW_UM = 1.08, 0.27         # fabric_sites_place.tcl soft-block geometry (DFF width, row height)


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


def lname(L):
    l, i, side = L["leg"]
    return f"leg_{l}_{i}{side}_{L['after']}"


def evaluate(host, land=None, tap_add=None, kfloor=None, rs_land=0):
    """cb_base.evaluate with landed crossings (Q-CLUSTER-LANDALL).  land = {(l, i, side): landed crossings on that leg}
    (each adds LAND_A edges); tap_add = {r: edges} (row r's tap arrives later: landed column-run crossings below it);
    kfloor = {(l, i, side): k}: every leg keeps at least the unlanded design's relay stations (hard station sites
    unchanged, the extra edges become soft pad stages); rs_land = landed crossings on the rs exit run.
    All defaults == cb_base.evaluate."""
    land, tap_add, kfloor = land or {}, tap_add or {}, kfloor or {}
    t, legs = {}, []
    for (l, i) in g.NODES:
        hc, hr = host[(l, i)]
        arr = []
        for side, (kind, ref) in zip("ab", g.children(l, i)):
            if kind == "leaf":
                c, r = ref
                ts, src, sname = g.tap_time(r) + tap_add.get(r, 0), g.pin(c, r, "t_out"), ("t_out", (c, r))
            else:
                c, r = host[ref]
                ts, src, sname = t[ref], g.pin(c, r, "n_y"), ("n_y", (c, r))
            dst = g.pin(hc, hr, "n_a" if side == "a" else "n_b")
            p = g.poly(src, g.W_FACE_CORR[c], dst, g.W_FACE_CORR[hc])
            d = g.plen(p)
            arr.append(dict(side=side, src=sname, ts=ts, d=d, kmin=max(g.relays(d), kfloor.get((l, i, side), 0)), poly=p,
                            land=LAND_A * land.get((l, i, side), 0), nland=land.get((l, i, side), 0)))
        a = max(x["ts"] + 1 + x["kmin"] + x["land"] for x in arr)
        for x in arr:
            x["k"] = a - x["ts"] - 1 - x["land"]
            assert x["k"] >= x["kmin"]
            legs.append(dict(node=(l, i), host=(hc, hr), **x))
        t[(l, i)] = a
    root = host[(4, 0)]
    p, rz = g.rs_route(root)
    k = g.relays(g.plen(p))
    rs_t = t[(4, 0)] + 1 + k + LAND_A * rs_land
    bits = sum(x["k"] for x in legs) * BW + (k + 1) * BW
    return rs_t, bits, legs, dict(root=root, d=g.plen(p), k=k, poly=p, corridor=rz), t


def leg_regions(x, k=None):
    """regions of a leg's register sequence: source tile, its relay stations (planned sites), destination tile"""
    k = x["k"] if k is None else k
    kind, (sc, sr) = x["src"]
    return [tile_quad(sc, sr)] + [quad(*g.along(x["poly"], (j + 1) / (k + 1))) for j in range(k)] + [tile_quad(*x["host"])]


def rs_points(rsx):
    k = rsx["k"]
    return [g.along(rsx["poly"], (j + 1) / (k + 1)) if j < k else (rsx["poly"][-1][0], g.STRIP / 2) for j in range(k + 1)]


def ncross(seq):
    return sum(a != b for a, b in zip(seq, seq[1:]))


class Emit:
    def __init__(self, mode="off", over=None):
        self.L, self.sites, self.regions = [], [], {q: 0 for q in QUADS}
        self.mode, self.over = mode, over or {}
        self.lands, self.alias, self.lrst = [], {}, []
        self.rnodes = {q: [] for q in QUADS}      # Q-CB16RST region reset trees: {region: [(net, (x, y), depth)]}
        self.rpins = {}                            # {region: (x, y) of its rst_<q> pin register}

    def w(self, s):
        self.L.append(s)

    def at(self, inst, x, y):
        return self.over.get(f"u_fab.{inst}", (x, y))

    def stage(self, name, width, d, q, x, y, note="", soft=False, region=None, target=None):
        x, y = self.at(name, x, y)
        r = region or quad(x, y)
        self.regions[r] += width
        # Q-CLUSTER3: every wide stage is a hard station tile (qfd_c_stn516 / qfd_c_stn514, own clock pin + local tree);
        # only the 1-bit reset stages stay soft flops of the cluster.  soft=True = a soft wide stage (the leg
        # re-alignment pads at a leg's destination end, in the destination region)
        hard = width > 1 and not soft
        if width > 1 and soft:
            self.alias[q] = d
        self.sites.append(dict(inst=f"u_fab.{name}", at=[round(x, 3), round(y, 3)], region=r, bits=width,
                               master=f"qfd_c_stn{width}" if hard else None, d=d, q=q,
                               **({"target": [round(v, 3) for v in target]} if target else {})))
        cell = f"qfd_c_stn{width}" if hard else f"qfd_q3h_stn #(.W({width}), .N(1))"
        self.w(f"    wire [{width - 1}:0] {q};  {cell} {name} (.ck(ck_{r}), .d({d}), .q({q}));"
               f"   // ({x:.2f}, {y:.2f}) {r}{(' ' + note) if note else ''}")

    def link(self, prev, preg, pat, reg, at, name, width):
        """prev = the net a register of region preg (planned point pat) drives into the next register (region reg, point
        at).  A region change in 'all' mode is LANDED; returns the net the next register takes."""
        if self.mode != "all" or preg is None or preg == reg:
            return prev
        return emit_land(self, name, prev, preg, reg, pat, at, width)


def emit_land(E, n, src_q, sreg, dreg, src_at, dst_at, width):
    """One landed crossing: RING (qfd_c_land_w on ck_<sreg>) beside the source register, READ (qfd_c_land_r on ck_<dreg>)
    beside the destination register.  The halves' rsi come from equal-depth reset runs (emit_land_resets).  Returns o."""
    w = E.w
    D, K = LAND_D, LAND_E
    AW = max(1, (D - 1).bit_length())
    wi, ri = f"u_land_{n}_w", f"u_land_{n}_r"
    # legaliser targets: 15 % / 85 % of the way from the source to the destination register (ring beside the source,
    # read beside the destination, the ring -> read multicycle hop the long one, all three <= reach)
    tw = tuple(a_ + 0.15 * (b_ - a_) for a_, b_ in zip(src_at, dst_at))
    tr = tuple(a_ + 0.85 * (b_ - a_) for a_, b_ in zip(src_at, dst_at))
    ring = E.at(wi, *tw)
    rd = E.at(ri, *tr)
    fl_w = D * width + D + (AW + 1) + 1          # slots + written flags + wc + rq (epoch tags: assertion only, not built)
    fl_r = width + (AW + 1) + 2                  # o + rc + warm + rq
    E.regions[sreg] += fl_w
    E.regions[dreg] += fl_r
    E.sites.append(dict(inst=f"u_fab.{wi}", at=[round(v, 3) for v in ring], region=sreg, bits=fl_w, master=None, d=src_q,
                        q=f"land_{n}_bank", landing=n, half="ring", target=[round(v, 3) for v in tw]))
    E.sites.append(dict(inst=f"u_fab.{ri}", at=[round(v, 3) for v in rd], region=dreg, bits=fl_r, master=None,
                        d=f"land_{n}_bank", q=f"land_{n}", landing=n, half="read", target=[round(v, 3) for v in tr]))
    mut = n == LAND_MUT
    w(f"    // ---- LANDING {n}: {sreg} -> {dreg}, {width} b, D {D}, E = K = {K}, +{LAND_A} edges (LANDING-CONTRACT L1-L7)")
    w(f"    wire [{D * width - 1}:0] land_{n}_bank;  wire [{D * (AW + 1) - 1}:0] land_{n}_epo;  wire [{D - 1}:0] land_{n}_vld;"
      f"  wire [{width - 1}:0] land_{n};  wire lrst_{n}_w, lrst_{n}_r;")
    w(f"    qfd_c_land_w #(.W({width}), .D({D})) {wi} (.ck(ck_{sreg}), .rsi(lrst_{n}_w), .i({src_q}), "
      f".bank(land_{n}_bank), .epo(land_{n}_epo), .vld(land_{n}_vld));   // ({ring[0]:.2f}, {ring[1]:.2f}) {sreg} ring")
    rsr = f"lrst_{n}_r"
    if mut:
        w(f"    wire land_{n}_rsr;  qfd_q3h_run #(.W(1), .D(MUT == 7 ? 1 : 0)) u_m7_{n} (.ck(ck_{dreg}), .d(lrst_{n}_r), .q(land_{n}_rsr));")
        rsr = f"land_{n}_rsr"
    kk = f"MUT == 6 ? {K + 1} : {K}" if mut else f"{K}"
    w(f"    qfd_c_land_r #(.W({width}), .D({D}), .K({kk})) {ri} (.ck(ck_{dreg}), "
      f".rsi({rsr}), .bank(land_{n}_bank), .epo(land_{n}_epo), .vld(land_{n}_vld), .o(land_{n}));"
      f"   // ({rd[0]:.2f}, {rd[1]:.2f}) {dreg} read")
    E.lands.append(dict(name=n, src=sreg, dst=dreg, bits=width, ring=list(ring), read=list(rd), src_q=src_q,
                        src_at=list(src_at), dst_at=list(dst_at),
                        flops_ring=fl_w, flops_read=fl_r))
    E.lrst += [(f"lrst_{n}_w", n, "w", ring, sreg), (f"lrst_{n}_r", n, "r", rd, dreg)]
    E.alias[f"land_{n}"] = src_q
    return f"land_{n}"


def emit_land_resets(E, rnodes, rdepth):
    """Each landing half's rsi = a run of 1-bit soft stages from the nearest reset-tree node (same region preferred) to
    the half, ending at the half's site; the shorter run of each landing is padded so both halves sit at the SAME reset
    depth (write epoch G == read epoch R0, E = K).  Returns {landing: depth}."""
    pos = {nm: xy for nm, _, xy in rnodes}
    runs = {}
    for net, n, half, (hx, hy), reg in E.lrst:
        best = min(pos, key=lambda nm: (quad(*pos[nm]) != reg, abs(pos[nm][0] - hx) + abs(pos[nm][1] - hy)))
        tx, ty = pos[best]
        P = [(tx, ty), (tx, hy), (hx, hy)]
        k = g.relays(g.plen(P))
        runs[net] = (n, half, best, P, k, rdepth[best] + k + 1, reg)
    depth = {}
    for net, (n, half, best, P, k, dep, reg) in runs.items():
        depth[n] = max(depth.get(n, 0), dep)
    E.w("    // ---- landing epochs: equal-depth reset runs per landing (both halves at the same depth: G == R0)")
    for net, (n, half, best, P, k, dep, reg) in runs.items():
        prev = f"{best}_q"
        for j in range(k + 1):
            px, py = g.along(P, (j + 1) / (k + 1))
            E.stage(f"u_lrs_{n}_{half}_{j}", 1, prev, f"lrs_{n}_{half}_{j}_q", px, py, "landing reset run",
                    region=reg if j == k else None)
            prev = f"lrs_{n}_{half}_{j}_q"
        for j in range(depth[n] - dep):
            E.stage(f"u_lrp_{n}_{half}_{j}", 1, prev, f"lrp_{n}_{half}_{j}_q", P[-1][0], P[-1][1], "landing reset pad",
                    region=reg)
            prev = f"lrp_{n}_{half}_{j}_q"
        E.w(f"    assign {net} = {prev};")
    return depth


# ---- Q-CB16RST (10-19): DIE-DELIVERED REGIONAL RESETS.  The diag16bt gate (TritonCTS per region) stopped in hold repair at
# -1,333.6 ps on u_fab.u_lrs_leg_2_2a_3_r_0 = one of the 43 plain 1-bit reset hops between region trees: a single-cycle
# hop between two independent region trees (insertion 0.9..2.3 ns) cannot hold at TT and FF, and landing it needs an
# epoch, which is the reset itself.  So no reset hop crosses a region seam any more: each region q has its own reset pin
# rst_<q> (beside ck_<q>), registered at its entry (ROOT-RST rule: reset-derived inputs registered at the face) on ck_<q>,
# and its own equal-depth tree that stays inside the region (corridor / channel lanes only, never over the A0 tile).
# Every consumer keeps its depth from the pin, so the static calendar is UNCHANGED: tiles / xstn 19 edges, each landing's
# halves at the landing's old common depth (G == R0, E = K).  The die releases the 16 rst_<q> of an instance on the SAME
# calendar edge (each in its own region's clock; the die reset tree lands each, die_clock_contract.json obligation).
RST_REGION_MUT = "c1r2"
REGIONAL = [True]           # main(): False for --landings off (the single-rst_n Q-CLUSTER16 fabric)     # bench mutant 8: region c1r2's reset released one edge late (the die calendar slip witness)


def region_box(q):
    c, r = int(q[1]), int(q[3])
    xb = [0.0] + list(XSEAM) + [WIDTH]
    yb = [0.0] + list(YSEAM) + [HEIGHT]
    return xb[c], yb[r], xb[c + 1], yb[r + 1]


def region_lanes(q):
    """x of each corridor part inside region q's column band (vertical reset lanes)"""
    x0, _, x1, _ = region_box(q)
    out = []
    for lo, hi in g.CORR.values():
        lo2, hi2 = max(lo, x0), min(hi, x1)
        if hi2 - lo2 > 1.0:
            out.append(round((lo2 + hi2) / 2, 3))
    return out


def region_chans(q):
    """y of each channel part (S / N strip, row gaps) inside region q's row band (horizontal reset lanes)"""
    _, y0, _, y1 = region_box(q)
    out = []
    for lo, hi in g.CHANNELS:
        lo2, hi2 = max(lo, y0), min(hi, y1)
        if hi2 - lo2 > 1.0:
            out.append(round((lo2 + hi2) / 2, 3))
    return out


def _seg_hits(a, b, box):
    x0, y0, x1, y1 = box
    if abs(a[1] - b[1]) < 1e-9:
        return y0 < a[1] < y1 and max(a[0], b[0]) > x0 and min(a[0], b[0]) < x1
    return x0 < a[0] < x1 and max(a[1], b[1]) > y0 and min(a[1], b[1]) < y1


def rroute(a, b, q, relaxed=False):
    """shortest Manhattan route a -> b that stays inside region q and never crosses its A0 tile (vertical in corridors,
    horizontal in channels)"""
    c, r = int(q[1]), int(q[3])
    tile = (g.COLX[c][0] + 0.01, g.ROWY[r] + 0.01, g.COLX[c][1] - 0.01, g.ROWY[r] + g.TH - 0.01)
    cands = [[a, (a[0], b[1]), b], [a, (b[0], a[1]), b]]
    cands += [[a, (a[0], y), (b[0], y), b] for y in region_chans(q)]
    cands += [[a, (x, a[1]), (x, b[1]), b] for x in region_lanes(q)]
    cands += [[a, (a[0], y), (x, y), (x, b[1]), b] for y in region_chans(q) for x in region_lanes(q)]
    cands += [[a, (x, a[1]), (x, y), (b[0], y), b] for y in region_chans(q) for x in region_lanes(q)]
    ok = []
    for P in cands:
        if any(quad(*p_) != q for p_ in P):
            continue
        if any(_seg_hits(u, v, tile) for u, v in zip(P, P[1:])):
            continue
        ok.append(P)
    if not ok and relaxed:
        return cands[0]       # pass 1 only (provisional landing sites may sit over a tile); pass 2 is strict
    if not ok:
        raise SystemExit(f"region reset route {a} -> {b} in {q}: no in-region route clear of the A0 tile")
    return min(ok, key=g.plen)


def rpin_site(q, pin):
    """the pin register of rst_<q>: the in-region point nearest its pin (pin = (face, coordinate))"""
    x0, y0, x1, y1 = region_box(q)
    f, v = pin
    ins = 4.32
    if f in ("S", "N"):
        return (round(min(max(v, x0 + ins), x1 - ins), 3), round(g.STRIP / 2 if f == "S" else HEIGHT - g.STRIP / 2, 3))
    return (round(x0 + ins if f == "W" else x1 - ins, 3), round(min(max(v, y0 + ins), y1 - ins), 3))


def rpin_default(q):
    """provisional pin (pass 1, before the pin plan): rows 0 / 3 on the S / N face at the band centre, rows 1 / 2 on the W
    (columns 0 / 1) or E (2 / 3) face at the tile-row centre"""
    c, r = int(q[1]), int(q[3])
    x0, y0, x1, y1 = region_box(q)
    if r in (0, 3):
        return ("S" if r == 0 else "N", (x0 + x1) / 2)
    return ("W" if c < 2 else "E", g.ROWY[r] + g.TH / 2)


def emit_rpin(E, q, pin):
    x, y = rpin_site(q, pin)
    E.rpins[q] = (x, y)
    d = f"rst_{q}"
    if q == RST_REGION_MUT:
        E.w(f"    wire rst_{q}_m8;  qfd_q3h_run #(.W(1), .D(MUT == 8 ? 1 : 0)) u_m8 (.ck(ck_{q}), .d(rst_{q}), .q(rst_{q}_m8));")
        d = f"rst_{q}_m8"
    E.stage(f"u_rpin_{q}", 1, d, f"rpin_{q}_q", x, y, "region reset pin register", region=q)
    E.rnodes[q].append((f"rpin_{q}_q", (x, y), 1))


def emit_rrun(E, q, net, at, target, tag):
    """one consumer of region q's reset tree: a run of 1-bit stages from the in-region node that leaves the fewest new
    stages (the deepest node whose route still reaches 'at' within 'target' edges), padded to exactly 'target' edges after
    the pin (the static reset calendar).  Returns the depth reached before padding."""
    if quad(*at) != q:
        # only pass 1 (provisional, unlegalised landing sites): clamp into the region; pass 2 asserts E.rclamped == 0
        x0, y0, x1, y1 = region_box(q)
        at = (min(max(at[0], x0 + 4.32), x1 - 4.32), min(max(at[1], y0 + 4.32), y1 - 4.32))
        E.rclamped = getattr(E, "rclamped", 0) + 1
    best = None
    for nn, xy, nd in E.rnodes[q]:
        P = rroute(xy, at, q, relaxed=not E.over)
        k = g.relays(g.plen(P))
        if nd + k + 1 > target:
            continue
        key = (-nd, g.plen(P))
        if best is None or key < best[0]:
            best = (key, nn, nd, P, k)
    if best is None:
        raise SystemExit(f"region reset {q} -> {net} at {at}: no route within {target} edges")
    _, nn, nd, P, k = best
    prev, dep = nn, nd
    for j in range(k + 1):
        px, py = g.along(P, (j + 1) / (k + 1)) if j < k else (round(at[0], 3), round(at[1], 3))
        E.stage(f"u_rr_{tag}_{j}", 1, prev, f"rr_{tag}_{j}_q", px, py, "region reset run", region=q)
        prev, dep = f"rr_{tag}_{j}_q", dep + 1
        E.rnodes[q].append((prev, (px, py), dep))
    reached = dep
    for j in range(target - dep):
        E.stage(f"u_rq_{tag}_{j}", 1, prev, f"rq_{tag}_{j}_q", at[0], at[1], "region reset pad", region=q)
        prev, dep = f"rq_{tag}_{j}_q", dep + 1
        E.rnodes[q].append((prev, (round(at[0], 3), round(at[1], 3)), dep))
    E.w(f"    assign {net} = {prev};")
    return reached


def tile_rst_at(c, r):
    """tile (c, r)'s rst_n entry: its E-face corridor at RST_Y, 4.32 um off the tile face (inside the tile's region)"""
    lo, hi = g.CORR[g.E_FACE_CORR[c]]
    x = lo + 4.32 if abs(lo - g.COLX[c][1]) < 1.0 else hi - 4.32
    return (round(x, 3), round(g.ROWY[r] + g.RST_Y, 3))


def land_old_depth(E, rnodes, rdepth):
    """each landing's common reset depth under the Q-CLUSTER-LANDALL single tree (the calendar the compiler holds)"""
    pos = {nm: xy for nm, _, xy in rnodes}
    depth = {}
    for net, n, half, (hx, hy), reg in E.lrst:
        best = min(pos, key=lambda nm: (quad(*pos[nm]) != reg, abs(pos[nm][0] - hx) + abs(pos[nm][1] - hy)))
        tx, ty = pos[best]
        k = g.relays(g.plen([(tx, ty), (tx, hy), (hx, hy)]))
        depth[n] = max(depth.get(n, 0), rdepth[best] + k + 1)
    return depth


def emit_land_resets_region(E, rnodes, rdepth):
    """Q-CB16RST: each landing half's rsi = a run in ITS OWN region's tree, padded to the landing's common depth (the
    old single-tree depth: G == R0 and the warm-up calendar unchanged)"""
    depth = land_old_depth(E, rnodes, rdepth)
    E.w("    // ---- landing epochs: each half's rsi from its own region's reset tree, both halves at the landing's depth (G == R0)")
    for net, n, half, (hx, hy), reg in E.lrst:
        emit_rrun(E, reg, net, (hx, hy), depth[n], f"l_{n}_{half}")
    return depth


def gen_fabric(host, spare, legs, rsx, rnodes, rleaves, rdepth, RD, mut_swap, mode="off", over=None, rpins=None):
    E = Emit(mode, over)
    regional = mode == "all"      # Q-CB16RST: die-delivered regional resets (16 rst_<q> pins) with the landed fabric
    w = E.w
    w("`timescale 1ns/1ps")
    w(f"// GENERATED by tools/qwen_cluster/qc_gen.py -- do not edit.  {FABRIC}: every register of qfd_c_b16_dv outside the")
    w("// tiles (Q-CLUSTER 2026-10-17, results/arch/qwen_cluster_1017/SPEC.md): the four column runs (entry / relays /")
    w("// qfd_xcst_n / exit), the morton reduction legs, the rs exit run, the DV far-band feedthrough rs_i -> rs_o and the")
    w("// equal-depth reset tree.  Each register sits in one of 16 clock regions (one per A0 tile) and takes its root.")
    if mode == "all":
        w(f"// Q-CLUSTER-LANDALL: EVERY multi-bit region-seam crossing is LANDED (qfd_c_land_w ring on the source root ->")
        w(f"// qfd_c_land_r read on the destination root, D {LAND_D}, E = K = {LAND_E}, +{LAND_A} edges each); soft pad stages")
        w("// re-align the tree.  Q-CB16RST: NO register hop crosses a seam unlanded: each region has its own reset pin rst_<q>")
        w("// (registered at its entry on ck_<q>) and its own in-region equal-depth tree; the die releases all 16 on the same")
        w("// calendar edge.  Static schedule: no ready / credit.")
    else:
        w("// Seams are crossed only by registered hops <= 405 um.  Static schedule: no ready / credit / backpressure.")
    w("// MUT (bench only, default 0 = the design): 1 = one extra relay on leg a of node (2,0); 2 = leaves of nodes (1,0).a")
    w("//   and (1,2).a exchanged; 3 = one extra relay on column 2's run before its row-1 station; 4 = one extra relay on")
    w(f"//   the rs_i -> rs_o feedthrough; 5 = feedthrough bits 0 / 1 exchanged; landing mutants (on {LAND_MUT}): 6 = read")
    w("//   slot K = E + 1 (wrong read slot), 7 = read-side epoch one edge late (released reset re-registered twice).")
    if regional:
        w(f"//   8 = region {RST_REGION_MUT}'s reset released one edge late (a die reset-calendar slip).")
    w(f"module {FABRIC} #(parameter integer MUT = 0) (")
    ports = [f"    input  wire ck_{q}" for q in QUADS] + \
        ([f"    input  wire rst_{q}" for q in QUADS] if regional else ["    input  wire rst_n"]) + ["    input  wire far"]
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
    if regional:
        w(f"    // ---- reset (Q-CB16RST): per region, the rst_<q> pin register + in-region runs; every tile / station sees its")
        w(f"    // region's rst_<q> exactly {RD} edges after the pin (the die releases the 16 pins on the same calendar edge)")
        for q in QUADS:
            emit_rpin(E, q, (rpins or {}).get(q) or rpin_default(q))
        xst = {}
        for c in range(4):
            for nm, y in g.chain_for(c):
                if nm.startswith("xcst"):
                    xst[(c, int(nm[4:]))] = (g.run_x(c), y)
        for c in range(4):
            for r in range(4):
                q = tile_quad(c, r)
                emit_rrun(E, q, f"rstl_t_{c}_{r}", tile_rst_at(c, r), RD, f"t_{c}_{r}")
                xq = quad(*xst[(c, r)])
                emit_rrun(E, xq, f"rstl_x_{c}_{r}", xst[(c, r)], RD, f"x_{c}_{r}")
                w(f"    assign trst_{g.sname(c, r)} = rstl_t_{c}_{r};")
    pos = {}
    for nm, par, (x, y) in ([] if regional else rnodes):
        pos[nm] = (x, y)
        E.stage(f"u_{nm}", 1, "rst_n" if par is None else f"{par}_q", f"{nm}_q", x, y)
    for (cor, r), nm in ([] if regional else sorted(rleaves.items())):
        pad = RD - rdepth[nm]
        prev = f"{nm}_q"
        x, y = pos[nm]
        for j in range(pad):
            E.stage(f"u_rpad_{cor}_{r}_{j}", 1, prev, f"rpad_{cor}_{r}_{j}_q", x, y)
            prev = f"rpad_{cor}_{r}_{j}_q"
        w(f"    wire rstl_{cor}_{r} = {prev};")
    for c in range(4):
        for r in range(0 if regional else 4):
            w(f"    assign trst_{g.sname(c, r)} = rstl_{g.E_FACE_CORR[c]}_{r};")
    # column runs
    w("    // ---- column runs {tag 8, xl 128, ib 379, go}: entry pin register, relays, one qfd_xcst_n per row, exit pin register")
    for c in range(4):
        prev, preg, pat = f"bc{c}", None, None
        x = g.run_x(c)
        for nm, y in g.chain_for(c):
            q = quad(x, y)
            prev = E.link(prev, preg, pat, q, (x, y), f"dn{c}_{nm}", DW)
            if nm.startswith("xcst"):
                r = int(nm[4:])
                s = g.sname(c, r)
                cin = prev
                if c == 2 and r == 1:
                    w(f"    wire [{DW-1}:0] dm3_{c};  qfd_q3h_run #(.W({DW}), .D(MUT == 3 ? 1 : 0)) u_dm3_{c} (.ck(ck_{q}), .d({prev}), .q(dm3_{c}));")
                    cin = f"dm3_{c}"
                xrst = f"rstl_x_{c}_{r}" if regional else f"rstl_{g.E_FACE_CORR[c]}_{r}"
                b1 = "far_n" if (r >> 1) & 1 else "far"
                b0 = "far_n" if r & 1 else "far"
                E.regions[q] += DW
                E.sites.append(dict(inst=f"u_fab.u_x_{s}", at=[round(x, 3), round(y, 3)], region=q, bits=DW, station=True,
                                    master="qfd_c_xstnw" if c in (1, 3) else "qfd_c_xstn", d=cin, q=f"dn{c}_{nm}", col=c, row=r))
                w(f"    wire [{DW-1}:0] dn{c}_{nm};")
                w(f"    {'qfd_c_xstnw' if c in (1, 3) else 'qfd_c_xstn'} u_x_{s} (.ck(ck_{q}), .rst_n({xrst}), .sidx({{far, {b1}, {b0}}}), .b_d({cin}),"
                  f" .a_d(dn{c}_{nm}), .tap_d(tap_{s}));   // ({x:.2f}, {y:.2f}) {q}")
            else:
                E.stage(f"u_dn{c}_{nm}", DW, prev, f"dn{c}_{nm}", x, y)
            prev, preg, pat = f"dn{c}_{nm}", q, (x, y)
        w(f"    assign bco{c} = {prev};")
    # tree legs
    w("    // ---- morton reduction tree legs (legs of one node arrive on the same edge)")
    for x in legs:
        (l, i), side, (hc, hr) = x["node"], x["side"], x["host"]
        kind, (sc, sr) = x["src"]
        src = f"{kind}_{g.sname(sc, sr)}"
        if (l, i, side) in mut_swap:
            w(f"    wire [{BW-1}:0] msw_{l}_{i}{side};")
            w(f"    assign msw_{l}_{i}{side} = (MUT == 2 ? {mut_swap[(l, i, side)]} : {src});")
            src = f"msw_{l}_{i}{side}"
        pad = x.get("pad", 0)
        k = x["k"] - pad         # the unlanded relay count stays on the leg (same stations, same sites)
        dst = f"n_{side}_{g.sname(hc, hr)}"
        dreg = tile_quad(hc, hr)
        w(f"    // node ({l},{i}).{side} on tile ({hc},{hr}) <- {kind}({sc},{sr}): {x['d']:.1f} um, {k} relays, hop <= {x['d'] / (k + 1):.1f} um"
          + (f", {x['nland']} landed crossings" if x.get("nland") else "") + (f" + {pad} re-alignment pad stages" if pad else ""))
        prev, preg, pat = src, tile_quad(sc, sr), x["poly"][0]
        for j in range(k):
            px, py = g.along(x["poly"], (j + 1) / (k + 1))
            q = quad(px, py)
            prev = E.link(prev, preg, pat, q, (px, py), f"leg_{l}_{i}{side}_{j}", BW)
            nm = f"u_leg_{l}_{i}{side}_{j}"
            E.stage(nm, BW, prev, f"leg_{l}_{i}{side}_{j}", px, py)
            prev, preg, pat = f"leg_{l}_{i}{side}_{j}", q, (px, py)
        ex, ey = x["poly"][-1]
        prev = E.link(prev, preg, pat, dreg, (ex, ey), f"leg_{l}_{i}{side}_y", BW)
        if pad:
            # re-alignment pads: soft stages at the destination pin, in the destination tile's region (legalised sites)
            w(f"    // re-alignment pad: {pad} soft stages (= the landed edges of the node's other leg / descendants)")
            for j in range(pad):
                E.stage(f"u_pad_{l}_{i}{side}_{j}", BW, prev, f"pad_{l}_{i}{side}_{j}", ex, ey, "re-alignment pad", soft=True,
                        region=dreg, target=(ex, ey))
                prev = f"pad_{l}_{i}{side}_{j}"
        if (l, i, side) == (2, 0, "a"):
            w(f"    qfd_q3h_run #(.W({BW}), .D(MUT == 1 ? 1 : 0)) u_m1 (.ck(ck_{dreg}), .d({prev}), .q({dst}));")
        else:
            w(f"    assign {dst} = {prev};")
    # rs exit
    rc, rr = host[(4, 0)]
    k = rsx["k"]
    w(f"    // ---- rs: root n_y ({rc},{rr}) -> {k} relays + the rs pin register (S face): {rsx['d']:.1f} um")
    prev, preg, pat = f"n_y_{g.sname(rc, rr)}", tile_quad(rc, rr), rsx["poly"][0]
    for j, (px, py) in enumerate(rs_points(rsx)):
        q = quad(px, py)
        prev = E.link(prev, preg, pat, q, (px, py), f"rs_{j}", BW)
        E.stage(f"u_rs_{j}", BW, prev, f"rs_{j}", px, py, "pin register" if j == k else "")
        prev, preg, pat = f"rs_{j}", q, (px, py)
    w(f"    assign rs = {prev};")
    # DV feedthrough
    ch = ft_chain(rsx["poly"][-1][0])
    w(f"    // ---- DV far-band feedthrough rs_i (N) -> rs_o (S): {len(ch)} registers in the T centre lane, hop <= "
      f"{max(abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in zip(ch, ch[1:])):.1f} um")
    prev, preg, pat = "rs_i_m5", None, None
    w(f"    wire [{BW-1}:0] rs_i_m5 = (MUT == 5) ? {{rs_i[{BW-1}:2], rs_i[0], rs_i[1]}} : rs_i;")
    for j, (px, py) in enumerate(ch):
        note = "rs_i pin register" if j == 0 else ("rs_o pin register" if j == len(ch) - 1 else "")
        q = quad(px, py)
        prev = E.link(prev, preg, pat, q, (px, py), f"ft_{j}", BW)
        E.stage(f"u_ft_{j}", BW, prev, f"ft_{j}", px, py, note)
        prev, preg, pat = f"ft_{j}", q, (px, py)
        if j == len(ch) // 2:
            w(f"    wire [{BW-1}:0] ft_m4;  qfd_q3h_run #(.W({BW}), .D(MUT == 4 ? 1 : 0)) u_m4 (.ck(ck_{q}), .d({prev}), .q(ft_m4));")
            prev = "ft_m4"
    w(f"    assign rs_o = {prev};")
    E.ldepth = (emit_land_resets_region(E, rnodes, rdepth) if regional else emit_land_resets(E, rnodes, rdepth)) if E.lands else {}
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
    w("// Q-CB16RST: sixteen regional resets rst_c<c>r<r> (one per region, beside its clock pin), released by the die on the")
    w("// same calendar edge; each is registered at its region's entry on ck_c<c>r<r> (no reset hop crosses a region seam).")
    w(f"module {MASTER} (")
    rin = [f"rst_{q}" for q in QUADS] if REGIONAL[0] else ["rst_n"]
    ports = [f"    input  wire ck_{q}" for q in QUADS] + [f"    input  wire {n}" for n in rin] + \
        ["    input  wire far", "    input  wire [11:0] cid"]
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
    conn = [f".ck_{q}(ck_{q})" for q in QUADS] + [f".{n}({n})" for n in rin] + [".far(far)"] + \
           [f".bc{c}(bc{c})" for c in range(4)] + \
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
    conn = [f".ck_{q}(ck)" for q in QUADS] + ([f".rst_{q}(rst_n)" for q in QUADS] if REGIONAL[0] else [".rst_n(rst_n)"]) + [".far(far)"] + \
           [f".bc{c}(bcw[{c}])" for c in range(4)] + \
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
    # Q-CLUSTER-LANDALL: station placement sees THROUGH landings and soft pads (o / pad q -> the source register), so the
    # hard station sites and orientations are exactly those of the unlanded fabric
    alias.update(E.alias)
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


def gen_lockstep_tb(spare, delay=None, masked=(), mask_edges=0):
    """Q-CLUSTER16 lockstep bench: the 16-region fabric (this generator, MUT) against the 8-region fabric it replaces
    (rtl/test/qcluster_ref_8r_be7b9ff15.sv, MUT 0; the c392aa534 soft reference differs by design since Q-CLUSTER4:
    rs_i -> rs_o 16 -> 17 and reset 18 -> 19 edges), every input random every cycle (+ reset pulses), every output compared
    every cycle.  +FAR selects the far-band strap.
    Q-CL16-LAND: delay = {output port: added edges} (landed legs and the legs re-aligned to them): those DUT ports are
    compared against the reference delayed by exactly that many edges.  masked = ports fed through a landing: not compared
    while the landing is in reset / warm-up (mask_edges edges after each bench reset pulse starts and ends; the landing
    carries bubbles there by contract L3).  Every other cycle of every port is compared."""
    delay = delay or {}
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
        rin = [f".rst_{q}(rst_n)" for q in QUADS] if (sfx == "h" and REGIONAL[0]) else [".rst_n(rst_n)"]   # Q-CB16RST: 16 regional resets
        c_ = [f".ck_{q}(ck)" for q in qs] + rin + [f".{n}({n})" for n, _ in ins if n != "rst_n"] + \
             [f".{n}({n}_{sfx})" for n, _ in outs]
        return ",\n        ".join(c_)
    L.append(f"    {FABRIC} #(.MUT(MUT)) u_h (\n        {conn('h')});")
    L.append(f"    {FABRIC}_ref8 #(.MUT(0)) u_r (\n        {conn('r', REF_QUADS)});")
    for n, w_ in outs:
        if delay.get(n):
            L.append(f"    reg  [{w_ - 1}:0] {n}_rd [1:{delay[n]}];   // Q-CL16-LAND: reference delayed {delay[n]} edges")
            L.append(f"    always @(posedge ck) begin {n}_rd[1] <= {n}_r;" +
                     "".join(f" {n}_rd[{j}] <= {n}_rd[{j - 1}];" for j in range(2, delay[n] + 1)) + " end")
    L.append(f"    wire land_mask = (cyc < 24 + {mask_edges}) || (cyc >= 2500 && cyc < 2530 + {mask_edges});")
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
    def ref(n):
        return f"{n}_rd[{delay[n]}]" if delay.get(n) else f"{n}_r"
    cmp_ = " ||\n            ".join((f"(!land_mask && ({n}_h !== {ref(n)}))" if n in masked else f"({n}_h !== {ref(n)})")
                                    for n, _ in outs)
    L.append("        if (cyc > 2 + " + str(max(list(delay.values()) + [0])) + " && (" + cmp_ + ")) begin")
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


def site_corridor(x):
    """the [xlo, xhi] fabric_sites_place.tcl clips a soft site's block to (its corridor, else x +/- 15)"""
    return next(((lo, hi) for lo, hi in g.CORR.values() if lo - 1e-6 <= x <= hi + 1e-6), (max(0.0, x - 15), min(WIDTH, x + 15)))


def soft_block(x, y, bits):
    """fabric_sites_place.tcl geometry of a soft site at (x, y) holding 'bits' flops: (x0, y0, w, h)"""
    xlo, xhi = site_corridor(x)
    bw = min(24.0, xhi - xlo - 4.0)
    per = max(1, int(bw / FW_UM))
    nrow = math.ceil(bits / per)
    x0 = max(xlo + 2.0, min(x - per * FW_UM / 2.0, xhi - 2.0 - per * FW_UM))
    return (x0, y - nrow * ROW_UM / 2.0, per * FW_UM, nrow * ROW_UM)


def _clash(a, b, gap):
    return not (a[0] + a[2] + gap <= b[0] or b[0] + b[2] + gap <= a[0] or a[1] + a[3] + gap <= b[1] or b[1] + b[3] + gap <= a[1])


def legalize_soft(E, stations, gap=4.32, radius=320.0):
    """Q-CLUSTER-LANDALL: every wide soft site (landing ring / read halves, re-alignment pads) -> the nearest point to its
    target whose fabric_sites_place.tcl block lies wholly inside its clock region, inside the outline, and clears every
    hard station, A0 tile and other soft block by 'gap'.  Returns {inst: (x, y)}."""
    tiles = [(g.COLX[c][0], g.ROWY[r], g.TW, g.TH) for c in range(4) for r in range(4)]
    obst = [(p_["x"], p_["y"], p_["w"], p_["h"]) for p_ in stations] + tiles
    n = int(radius / LATTICE * 10)
    offs = sorted(((i * 4.32, j * 4.32) for i in range(-n, n + 1) for j in range(-n, n + 1)
                   if abs(i) + abs(j) <= radius / 4.32), key=lambda o: (abs(o[0]) + abs(o[1]), o))
    out, placed = {}, []
    soft = [st for st in E.sites if not st.get("master") and st["bits"] > 1]
    for st in sorted(soft, key=lambda st: -st["bits"]):
        tx, ty = st.get("target", st["at"])
        reg = st["region"]
        for dx, dy in offs:
            x, y = round(tx + dx, 3), round(ty + dy, 3)
            b = soft_block(x, y, st["bits"])
            if b[0] < 4.32 or b[1] < 4.32 or b[0] + b[2] > WIDTH - 4.32 or b[1] + b[3] > HEIGHT - 4.32:
                continue
            if any(quad(cx, cy) != reg for cx in (b[0] + 0.01, b[0] + b[2] - 0.01) for cy in (b[1] + 0.01, b[1] + b[3] - 0.01)):
                continue
            if any(_clash(b, o, gap) for o in obst) or any(_clash(b, o, gap) for o in placed):
                continue
            break
        else:
            raise SystemExit(f"soft site {st['inst']} ({st['bits']} b, {reg}): no legal spot within {radius} um of {tx, ty}")
        placed.append(b)
        out[st["inst"]] = (x, y)
    return out


def landing_record(E, stations, legs, leg_add, port_add, lat, lat0, nflops_land, hops):
    """contract record of every landed crossing (consumed by region_audit.py R5 and qc_kit.py's SDC)"""
    tiles = [(g.COLX[c][0], g.ROWY[r], g.TW, g.TH) for c in range(4) for r in range(4)]
    boxes = [(p_["x"], p_["y"], p_["w"], p_["h"]) for p_ in stations] + tiles
    for st in E.sites:     # final check: every wide soft block clears the hard children (legalize_soft did the search)
        if not st.get("master") and st["bits"] > 1:
            b = soft_block(*st["at"], st["bits"])
            for o in boxes:
                if _clash(b, o, 4.32 - 1e-6):
                    raise SystemExit(f"soft site {st['inst']} block {b} overlaps {o}")
    by = {st["inst"]: st for st in E.sites}
    rec = []
    for L in E.lands:
        n = L["name"]
        ring, rd = by[f"u_fab.u_land_{n}_w"], by[f"u_fab.u_land_{n}_r"]
        rec.append(dict(
            name=n, crossing=f"{L['src_q']} ({L['src']}) -> u_fab.u_{n} ({L['dst']})", src_region=L["src"],
            dst_region=L["dst"], bits=L["bits"], D=LAND_D, E=LAND_E, K=LAND_E, added_edges=LAND_A,
            ring=dict(inst=ring["inst"], master="qfd_c_land_w", clock=f"ck_{L['src']}", site=ring["at"], flops=L["flops_ring"]),
            read=dict(inst=rd["inst"], master="qfd_c_land_r", clock=f"ck_{L['dst']}", site=rd["at"], flops=L["flops_read"]),
            hop_um=hops[n], reset_depth=E.ldepth[n],
            sdc=f"set_multicycle_path -setup {LAND_E} / -hold {LAND_D - 1} -from u_fab.u_land_{n}_w.* -to u_fab.u_land_{n}_r.*"))
    return dict(
        mode="all", resets="region",
        rule="every region-seam crossing landed (Q-CLUSTER-LANDALL, coordinator 0fy; Q-CB16RST 10-19: no reset hop crosses a "
             "seam: 16 die-delivered regional resets rst_<q>, each registered at its region entry with an in-region tree)",
        D=LAND_D, E=LAND_E, K=LAND_E, added_edges_per_crossing=LAND_A,
        window_ps=f"({LAND_E} - {LAND_D}) T + t_hold < dL < {LAND_E} T - t_cq - t_setup (T = 833.3: about -1666 .. +1666 ps)",
        epochs="released reset (L3): each half's rsi = a run in its OWN region's reset tree (from rst_<q>), both halves at "
               "the landing's common depth after their pins; the die releases the 16 rst_<q> on the same calendar edge: "
               "G == R0, E = K",
        fault="assertion only ($error LAND_FAULT in simulation; synthesis drops the epoch tags)",
        rtl="rtl/physical/qcluster/qfd_c_land.sv", count=len(rec), bits=sum(r["bits"] for r in rec), flops=nflops_land,
        list=rec,
        realigned_legs={f"{x['node'][0]}_{x['node'][1]}{x['side']}": dict(added_edges=leg_add[(x["node"], x["side"])],
                        relay_stations=x["k"] - x.get("pad", 0), soft_pad_stages=x.get("pad", 0), landed_crossings=x["nland"])
                        for x in legs if leg_add[(x["node"], x["side"])]},
        port_added_edges=port_add, latency_edges=lat, latency_edges_unlanded=lat0)


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
    # Q-CB16RST: each region's reset pin rst_<q> sits in its clock entry island, beside ck_<q>
    islands = {"S": [(QUADS[0], [f"ck_{QUADS[0]}", f"rst_{QUADS[0]}", "far", "cid", "tie_hi", "tie_lo"])] +
                    [(f"c{c}r0", [f"ck_c{c}r0", f"rst_c{c}r0"]) for c in (1, 2, 3)],
               "N": [(f"c{c}r3", [f"ck_c{c}r3", f"rst_c{c}r3"]) for c in range(4)]}
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
                                 **({"region": q} if n.startswith("rst_") else {}),
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
        pins.append(dict(port=f"rst_{q}", bits=1, face=f, layer="M4", range_um=[round(y0 + 1.0, 3), round(y0 + 1.3, 3)],
                         pins_per_um=None, region=q,
                         note=f"region {q} reset (Q-CB16RST: beside ck_{q}; pin register u_fab.u_rpin_{q} on ck_{q})"))
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
        if not s.get("master") and s["bits"] > 1:     # Q-CLUSTER-LANDALL: landing rings (red) / reads (green), pads (grey)
            b = soft_block(*s["at"], s["bits"])
            fc = "#d22" if s.get("half") == "ring" else "#1a1" if s.get("half") == "read" else "#888"
            ax.add_patch(Rectangle((b[0], b[1]), b[2], max(b[3], 8.0), fc=fc, ec="k", lw=0.2))
        elif not s.get("master"):
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
                 "region root (squares = hard station tiles, dots = soft reset stages); red = W/E clock entries; blue = tree legs, purple = rs / rs_i->rs_o; dotted = region seams\n"
                 f"Q-CLUSTER-LANDALL: {len(E.lands)} landed crossings: red blocks = rings (source region), green = reads (destination region), grey = re-alignment pads", fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=110)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["gen"])
    ap.add_argument("--hosts", default=str(Path(__file__).with_name("cb16_hosts.json")))
    # Q-CLUSTER-LANDALL (coordinator 0fy 10-18): 'all' (default) lands every multi-bit region-seam crossing; 'off'
    # regenerates the unlanded Q-CLUSTER16 fabric (only comment changes)
    ap.add_argument("--landings", choices=["all", "off"], default="all")
    a = ap.parse_args()
    mode = a.landings
    REGIONAL[0] = mode == "all"
    host, spare = g.load_hosts(a.hosts)
    assert len(set(host.values())) == 15 and spare not in host.values()
    rs_t0, _, legs0, rsx0, t0 = evaluate(host)
    assert g.evaluate(host, True)[0] == rs_t0          # evaluate() with no landing is exactly cb_base.evaluate
    k0 = {(x["node"], x["side"]): x["k"] for x in legs0}
    ch0 = ft_chain(rsx0["poly"][-1][0])
    land, tap_add, col_exit, rs_land, ft_land = {}, {r: 0 for r in range(4)}, 0, 0, 0
    if mode == "all":
        # landed crossings from the UNLANDED geometry: the hard station sites (and so every register's region) stay put
        land = {(x["node"][0], x["node"][1], x["side"]): ncross(leg_regions(x)) for x in legs0}
        per_col = []
        for c in range(4):
            seq, xs_ = [], g.run_x(c)
            for nm, y in g.chain_for(c):
                seq.append((nm, quad(xs_, y)))
            cum, row_add = 0, {}
            for (n1, q1), (n2, q2) in zip(seq, seq[1:]):
                cum += q1 != q2
                if n2.startswith("xcst"):
                    row_add[int(n2[4:])] = cum
            per_col.append((row_add, cum))
        if any(pc != per_col[0] for pc in per_col):
            raise SystemExit(f"column runs cross the row seams differently: {per_col}")
        tap_add = {r: LAND_A * per_col[0][0].get(r, 0) for r in range(4)}
        col_exit = LAND_A * per_col[0][1]
        rs_land = ncross([tile_quad(*rsx0["root"])] + [quad(*p_) for p_ in rs_points(rsx0)])
        ft_land = ncross([quad(*p_) for p_ in ch0])
    kfloor = {(n_[0], n_[1], s_): k for (n_, s_), k in k0.items()} if mode == "all" else {}
    rs_t, bits, legs, rsx, t = evaluate(host, land, tap_add, kfloor, rs_land)
    # added edges per tree leg (landed crossings x LAND_A + re-alignment pads) -> per output port
    leg_add = {(x["node"], x["side"]): x["k"] + x["land"] - k0[(x["node"], x["side"])] for x in legs}
    port_add = {f"n_{x['side']}_{g.sname(*x['host'])}": leg_add[(x["node"], x["side"])] for x in legs
                if leg_add[(x["node"], x["side"])]}
    for x in legs:
        x["pad"] = x["k"] - k0[(x["node"], x["side"])]
        assert x["pad"] >= 0
    la = next(x for x in legs if x["node"] == (1, 0) and x["side"] == "a")
    lb = next(x for x in legs if x["node"] == (1, 2) and x["side"] == "a")
    mut_swap = {(1, 0, "a"): "t_out_%s" % g.sname(*lb["src"][1]), (1, 2, "a"): "t_out_%s" % g.sname(*la["src"][1])}
    rnodes, rleaves, rdepth, RD = g.reset_tree()
    # pass 1: provisional soft sites -> hard station placement -> legal soft sites; pass 2: the final RTL / sites
    fab1, E1, _ = gen_fabric(host, spare, legs, rsx, rnodes, rleaves, rdepth, RD, mut_swap, mode)
    st1, _ = place_stations(E1, fab1, spare)
    over = legalize_soft(E1, st1) if mode == "all" else {}
    rpins = None
    if mode == "all":
        # Q-CB16RST: the region reset pin registers sit at the pins the plan gives rst_<q> (beside ck_<q>)
        pins1, _, _ = pin_plan(rsx, E1)
        rpins = {p_["region"]: (p_["face"], sum(p_["range_um"]) / 2) for p_ in pins1 if p_["port"].startswith("rst_")}
    fab, E, nft = gen_fabric(host, spare, legs, rsx, rnodes, rleaves, rdepth, RD, mut_swap, mode, over, rpins)
    assert getattr(E, "rclamped", 0) == 0, "a pass-2 reset consumer lies outside its region"
    for st in E.sites:
        if not st.get("master") and st["bits"] > 1 and quad(*st["at"]) != st["region"]:
            raise SystemExit(f"soft site {st['inst']} at {st['at']} is not in its region {st['region']}")
    # every leg / run carries exactly the landed crossings the latency model charged
    nl = {}
    for L in E.lands:
        m = re.fullmatch(r"leg_(\d)_(\d+)([ab])_(\w+)", L["name"])
        if m:
            k_ = (int(m.group(1)), int(m.group(2)), m.group(3))
            nl[k_] = nl.get(k_, 0) + 1
    if mode == "all":
        assert {k_: v for k_, v in land.items() if v} == nl, (land, nl)
        assert sum(L["name"].startswith("dn") for L in E.lands) == 4 * col_exit // LAND_A
        assert sum(L["name"].startswith("rs_") for L in E.lands) == rs_land
        assert sum(L["name"].startswith("ft_") for L in E.lands) == ft_land
    OUT_RTL.mkdir(parents=True, exist_ok=True)
    (OUT_RTL / f"{FABRIC}.sv").write_text(fab)
    (OUT_RTL / f"{MASTER}.sv").write_text(gen_cluster(spare))
    (ROOT / "rtl/test/tb_qcluster_fabric.sv").write_text(gen_tb(spare))
    warm = (max(E.ldepth.values()) + LAND_E + 2) if E.lands else 0
    lat = dict(tap={r: g.tap_time(r) + tap_add[r] for r in range(4)}, bco=g.STAGE["exit"] + col_exit, rs_fabric=rs_t,
               rs_i_to_rs_o=nft + LAND_A * ft_land, reset=RD, landing_warm_after_rst=warm)
    lat0 = dict(tap={r: g.tap_time(r) for r in range(4)}, bco=g.STAGE["exit"], rs_fabric=rs_t0, rs_i_to_rs_o=nft, reset=RD)
    # lockstep vs the 8-region reference: every output port = the reference delayed by its documented offset; ports fed
    # through a landing are not compared while the landings are in reset / warm-up (bubbles by contract L3)
    delay = dict(port_add)
    for c in range(4):
        for r in range(4):
            if tap_add[r]:
                delay[f"tap_{g.sname(c, r)}"] = tap_add[r]
        if col_exit:
            delay[f"bco{c}"] = col_exit
    if rs_land:
        delay["rs"] = LAND_A * rs_land
    if ft_land:
        delay["rs_o"] = LAND_A * ft_land
    masked = [p_ for p_ in delay if not p_.startswith("n_")] + \
             [f"n_{x['side']}_{g.sname(*x['host'])}" for x in legs if x["nland"]]
    longest = max([x["k"] + x["land"] + 1 for x in legs] + [lat["bco"], lat["rs_i_to_rs_o"], rsx["k"] + 1 + LAND_A * rs_land])
    mask = (warm + longest + 8) if E.lands else 0
    (ROOT / "rtl/test/tb_qcluster_lockstep.sv").write_text(gen_lockstep_tb(spare, delay, masked, mask))
    hdr = ["// GENERATED by tools/qwen_cluster/qc_gen.py: compiled fixed latencies of qfd_c_b16_dv_fabric (edges)"] + \
          [f"localparam integer Q3H_LAT_TAP{r} = {lat['tap'][r]};" for r in range(4)] + \
          [f"localparam integer Q3H_LAT_BCO = {lat['bco']};",
           f"localparam integer Q3H_LAT_RS_FABRIC = {rs_t};",
           f"localparam integer QC_LAT_FT = {lat['rs_i_to_rs_o']};",
           f"localparam integer Q3H_RST_DEPTH = {RD};",
           f"localparam integer QC_LAT_WARM = {warm};"]
    (ROOT / "rtl/test/qcluster_lat.svh").write_text("\n".join(hdr) + "\n")
    pins, cen, ceny = pin_plan(rsx, E)
    rst_pin_um = {}
    if mode == "all":
        for p_ in pins:
            if p_["port"].startswith("rst_"):
                q = p_["region"]
                v = sum(p_["range_um"]) / 2
                assert abs(v - rpins[q][1]) < 30.0 and p_["face"] == rpins[q][0], ("rst pin moved between passes", p_, rpins[q])
                px, py = ((v, 0.0) if p_["face"] == "S" else (v, HEIGHT) if p_["face"] == "N" else
                          (0.0, v) if p_["face"] == "W" else (WIDTH, v))
                rx, ry = E.rpins[q]
                rst_pin_um[q] = round(abs(px - rx) + abs(py - ry), 1)
    stations, st_hops = place_stations(E, fab, spare)
    key = lambda P: [(p_["st"]["inst"], p_["x"], p_["y"], p_["orient"]) for p_ in P]
    assert key(stations) == key(st1), "hard station placement moved between the two passes"
    by = {st["inst"]: st["at"] for st in E.sites}
    sp = {p_["st"]["inst"]: (p_["x"] + p_["w"] / 2, p_["y"] + p_["h"] / 2) for p_ in stations}
    lhops = {}
    for L in E.lands:
        rg, rd = by[f"u_fab.u_land_{L['name']}_w"], by[f"u_fab.u_land_{L['name']}_r"]
        hx = abs(rg[0] - rd[0]) + abs(rg[1] - rd[1])
        if hx > LIMIT:
            raise SystemExit(f"landing {L['name']}: ring -> read hop {hx:.1f} um over reach")
        lhops[L["name"]] = round(hx, 1)
    nflops_land = sum(L["flops_ring"] + L["flops_read"] for L in E.lands)
    land_rec = landing_record(E, stations, legs, leg_add, port_add, lat, lat0, nflops_land, lhops) if E.lands else dict(list=[])
    # hop audit (pin to pin, Manhattan between consecutive registers of each run)
    by = {}
    for s in E.sites:
        by[s["inst"]] = s["at"]
    hops = [x["d"] / (x["k"] - x.get("pad", 0) + 1) for x in legs] + [rsx["d"] / (rsx["k"] + 1)]
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
        fabric_flops=nflops, latency_edges=lat,
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
        regional_resets=(dict(
            rule="Q-CB16RST (10-19): 16 die-delivered regional resets rst_<q> (pin beside ck_<q>); pin register u_fab.u_rpin_<q> "
                 "on ck_<q> at the region entry nearest the pin; in-region trees only (corridor / channel lanes, never over "
                 "the A0 tile); every tile / xstn rst_n exactly reset edges after its region pin, every landing half at the "
                 "landing's reset_depth.  Die obligation: release all 16 of an instance on the SAME calendar edge (each "
                 "timed against its own region tree, the die reset tree lands each); MUT 8 (bench) = one region one edge late.",
            pins={q: f"rst_{q}" for q in QUADS}, pin_register_um=rst_pin_um,
            pin_register_sites={q: list(v) for q, v in E.rpins.items()},
            flops=sum(1 for st in E.sites if st["inst"].startswith(("u_fab.u_rpin_", "u_fab.u_rr_", "u_fab.u_rq_"))),
            depth_edges=RD) if mode == "all" else None),
        far_position="ONE master: in the far bands (0 / 3) rs_i is a declared-idle terminus tied to the instance's own "
                     "tie_lo by the die (valid bit 0 every cycle) and rs_o is left unconnected (output only)",
        gating=["A0 views qfd_tile_nk_romleaf_a0 / nl twin not CLOSED (Q-ROMPARENT-2): diagnostics only, no binding"],
        landings=land_rec)
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
    print(json.dumps(dict(outline=[WIDTH, HEIGHT], mode=mode, landings=len(E.lands), landing_flops=nflops_land,
                          pad_stages=sum(x["pad"] for x in legs), latency=lat, latency_unlanded=lat0,
                          landing_hop_max=max(lhops.values()) if lhops else None,
                          hop_max=round(max(hops), 1), flops=nflops, regions=E.regions,
                          nk_clocks=len(NK_CLOCKS), nl_clocks=len(NL_CLOCKS)), indent=1))


if __name__ == "__main__":
    main()
