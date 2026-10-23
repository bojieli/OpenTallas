#!/usr/bin/env python3
"""PLAN-QC: Qwen compute die plan v1 generator (TOPDOWN-PLAN, owner-approved 2026-10-23).

    python3 physical/die_plan/qwen_compute/gen_plan.py --census QC_CENSUS.json.gz --slice-fp-w FP.json \
        --slice-fp-e FP.json [--out physical/die_plan/qwen_compute/die_plan.json]

Writes die_plan.json (schema opentallas.die_plan.v1, tools/die_plan) plus plan_notes.json (counts, reuse ledger,
open items).  Inputs: the as-built die connectivity (FT-TOOL census of the r50/r56 Qwen compute die: same cluster,
slice and IO connectivity; r56 differs only in reset padding) and the slice kit floorplans (leaf inventory).

Structure (every instance R0: mirrored placements put M4-M7 pins off-track for any 8.64-grid outline, so a mirrored
copy is its own type):
  * West IO strip (x 0 .. 2341.44): macro column (serdes x3, io_collective + clk_rx strip, ucie_kv) and a 777.6-um
    column (io_ucie, glue, native59, tt_ctlm, and station partitions s* that carry the W-strip lanes at <= 1 hop).
  * 12 compute columns, 2471.04 um pitch, each: far | near | slice | near | far (bottom to top).  Every CB16 cluster
    slot is a 4 x 4 grid of partitions, one A0 rpf (457.92 x 1157.76) each, abutted; column widths 622.08 / 613.44 /
    613.44 / 622.08, row heights 1313.28 / 1296 / 1296 / 1321.92 (8.64 grid).  One partition = one clock root = one
    reset synchronizer.  bc column words pass N through each row (xstn tap, functional); the exact 16-leaf pair tree
    is mapped onto the grid as an H-tree (quadrant L1/L2, L3 per half, L4 at (0,0)); the far cluster's result rides
    down column 0 of the near cluster (ft slot rsf).
  * Slices: one partition per slice in v1 (2471.04 x 4320, W/E modules, W-end / E-end types); split into <= 1-hop
    partitions is the v2 item (needs the slice-internal connectivity census).
"""
import argparse
import collections
import gzip
import json
import math
import re
from pathlib import Path

G = 8.64
REACH = 1000.0
ST_LEN = 900.0                       # one station per <= 900 um of slot route (hop margin for window jogs)
DENS = 4.8                           # pins / um per port window (budget 6 incl. track rounding)
GAP = 0.96
EDGE = 4.32

CW = [622.08, 613.44, 613.44, 622.08]
RH = [1313.28, 1296.0, 1296.0, 1321.92]
A0W, A0H = 457.92, 1157.76
A0X = [86.4, 69.12, 86.4, 77.76]
A0Y = [86.4, 69.12, 69.12, 69.12]
CLW, CLH = sum(CW), sum(RH)          # 2471.04 x 5227.2
SLH = 4320.0
NCOL = 12
WS_W = 2341.44                       # west strip width (1563.84 macro column + 777.6)
MC_W, C2_W = 1563.84, 777.6
BW, RSW = 516, 514                   # bc column word, reduction word

A0_KIT = "physical/ref_tile/qfd_tile_nk_romleaf_rpf (claude/a0-repack-1023 36a2db0b4)"
A0L_KIT = "physical/ref_tile/qfd_tile_nl_romleaf_rpf (claude/a0-repack-1023 36a2db0b4)"
XSTN_KIT = "physical/ref_tile/qfd_c_xstn_safe_rpf (codex/cb16-rederive-1023 72a7c837b)"
A0_GEOM = "lanes/GEOM-REVIEW.md A0 rpf PASS-CONDITIONAL (A0 r3 gates pending)"
XSTN_GEOM = "results geometry review e2e241ae9 (conditional child re-hardening)"


def snap(v):
    return round(round(v / G) * G, 4)


class Plan:
    def __init__(self):
        self.parts = {}        # name -> dict(type, origin, wh)
        self.types = {}        # name -> type dict
        self.links = []        # logical connections
        self.notes = collections.defaultdict(list)

    # ----------------------------------------------------------------- partitions / types
    def add_type(self, name, wh, module, contents, hard=False, kit=None, note=None, tap=None):
        if name in self.types:
            return self.types[name]
        w, h = wh
        t = {"module": module, "outline_um": [round(w, 4), round(h, 4)], "buses": [], "ft_slots": [],
             "contents": contents}
        if hard:
            t["hard"] = True
        if kit:
            t["kit"] = kit
        if note:
            t["note"] = note
        tp = tap or [snap(w / 2), snap(h / 2)]
        t["clock"] = {"tap_um": tp, "layer": "M9", "insertion_ps": 250, "insertion_tol_ps": 40}
        t["reset"] = {"tap_um": tp, "sync_stages": 2}
        self.types[name] = t
        return t

    def add_part(self, name, tname, x, y):
        assert name not in self.parts, name
        w, h = self.types[tname]["outline_um"]
        self.parts[name] = dict(type=tname, origin=(round(x, 4), round(y, 4)), wh=(w, h))

    def rect(self, n):
        (x, y), (w, h) = self.parts[n]["origin"], self.parts[n]["wh"]
        return (x, y, x + w, y + h)

    # ----------------------------------------------------------------- links
    def link(self, role, path, src_bus, dst_bus, width, kind="data", src_leaf=None, dst_leaf=None, param=None):
        self.links.append(dict(role=role, path=path, src_bus=src_bus, dst_bus=dst_bus, width=width, kind=kind,
                               src_leaf=src_leaf, dst_leaf=dst_leaf, param=param))


def shared_face(P, a, b):
    """die face of a touching b, and the overlap interval along it."""
    ax0, ay0, ax1, ay1 = P.rect(a)
    bx0, by0, bx1, by1 = P.rect(b)
    e = 1e-6
    if abs(ax1 - bx0) < e:
        f, lo, hi = "E", max(ay0, by0), min(ay1, by1)
    elif abs(ax0 - bx1) < e:
        f, lo, hi = "W", max(ay0, by0), min(ay1, by1)
    elif abs(ay1 - by0) < e:
        f, lo, hi = "N", max(ax0, bx0), min(ax1, bx1)
    elif abs(ay0 - by1) < e:
        f, lo, hi = "S", max(ax0, bx0), min(ax1, bx1)
    else:
        raise SystemExit(f"{a} and {b} do not abut")
    if hi - lo < 10:
        raise SystemExit(f"{a} / {b}: overlap {hi - lo:.1f} um too short")
    return f, lo, hi


OPP = dict(N="S", S="N", E="W", W="E")


def wlen(width):
    n = math.ceil(width / DENS / 0.192) * 0.192
    return max(round(n, 4), 0.384)


# ====================================================================== geometry
def build_geometry(P, slice_leaves):
    # ---- compute columns
    col_x = [WS_W + k * CLW for k in range(NCOL)]
    col_name = [f"W{5 - k}" for k in range(6)] + [f"E{k}" for k in range(6)]
    y_far_b, y_near_b, y_sl, y_near_t, y_far_t = 0.0, CLH, 2 * CLH, 2 * CLH + SLH, 3 * CLH + SLH
    H = 4 * CLH + SLH
    W = WS_W + NCOL * CLW
    clusters = []
    for k in range(NCOL):
        cx = col_x[k]
        for kind, half, y0 in (("far", "b", y_far_b), ("near", "b", y_near_b), ("near", "t", y_near_t),
                               ("far", "t", y_far_t)):
            cname = f"c_{col_name[k]}_{half}{kind[0]}"
            clusters.append(dict(name=cname, col=k, kind=kind, half=half, x=cx, y=y0))
            for c in range(4):
                for r in range(4):
                    tn = cb_type(P, kind, half, c, r)
                    # cluster frame row r -> die row: top half rows go up; bottom half rows go down (S face up)
                    if half == "t":
                        py = y0 + sum(RH[:r])
                    else:
                        py = y0 + CLH - sum(RH[:r + 1])
                    P.add_part(f"{cname}_{c}{r}", tn, cx + sum(CW[:c]), py)
        # slice
        side = "w" if k < 6 else "e"
        # l9 pair link (514 b): producers W5/W3/W1/E1/E3/E5 drive l9_eo, consumers W4/W2/W0/E0/E2/E4 take l9_wi
        prod = k in (0, 2, 4, 7, 9, 11)
        pos = "end" if k in (0, NCOL - 1) else ("c" if k in (5, 6) else ("p" if prod else "q"))
        tn = slice_type(P, side, pos, slice_leaves)
        P.add_part(f"sl_{col_name[k]}", tn, cx, y_sl)
    return dict(W=W, H=H, col_x=col_x, col_name=col_name, clusters=clusters, y_sl=y_sl)


def cb_frame(half, r, y):
    """cluster-frame y within row-r partition -> type-frame y (bottom half types are y-mirrored)."""
    return y if half == "t" else RH[r] - y


def cb_face(half, f):
    return f if half == "t" or f in "EW" else OPP[f]


def cb_type(P, kind, half, c, r):
    # near and far differ only in column 0 (rsf ft) and row 3 (bc_o to the far cluster)
    shared = (c != 0 and r != 3)
    tag = "x" if shared else kind[0]
    name = f"cb{tag}_{c}{r}{'' if half == 't' else 'b'}"
    if name in P.types:
        return name
    w, h = CW[c], RH[r]
    a0y = cb_frame(half, r, A0Y[r] + (A0H if half == "b" else 0))
    nl = (c == 3 and r == 3)
    cont = [{"inst": "u_t", "module": "qfd_tile_nl_romleaf_rpf" if nl else "qfd_tile_nk_romleaf_rpf",
             "status": "reuse", "kit": A0L_KIT if nl else A0_KIT, "geom_pass": A0_GEOM,
             "origin_um": [A0X[c], round(a0y, 4)], "outline_um": [A0W, A0H],
             "note": "reuse conditional: A0 r3 gate (insertion, registered faces) pending"},
            {"inst": "u_xstn", "module": "qfd_c_xstn_safe_rpf", "status": "rework", "kit": XSTN_KIT,
             "geom_pass": XSTN_GEOM, "outline_um": [43.2, 194.4],
             "note": "bc column station + 508-b tap at the A0 tap face; new 43.2x194.4 shape, gate running"},
            {"inst": "u_pstn", "module": f"qfd_qc_cbstn_{c}{r}", "status": "new",
             "note": "generated: boundary flops of every port, ft-slot stations (reset-less data + 1 epoch bit), "
                     "tree operand aligners from the latency table, reset synchronizer"}]
    tap = [snap(w / 2), snap(h / 2)]
    P.add_type(name, (w, h), f"qfd_qc_cb_{tag}{c}{r}{'' if half == 't' else 'b'}", cont,
               note=f"CB16 partition (c{c}, r{r}), {kind if not shared else 'near+far'}, "
                    f"{'top (S face = slice side)' if half == 't' else 'bottom (y-mirrored type)'}", tap=tap)
    return name


def slice_type(P, side, pos, leaves):
    name = f"sl_{side}{pos}"
    if name in P.types:
        return name
    cont = [{"inst": "u_slice", "module": f"qfd_dv_slice2_{side}_part", "status": "rework",
             "note": "slice parent re-derived from the plan (v2 splits it into <= 1-hop partitions)"}]
    for m, n, wh in leaves[side]:
        cont.append({"inst": f"u_{m}", "module": m, "status": "reuse", "outline_um": list(wh),
                     "note": f"{n} copies in the slice kit; reuse candidate pending GEOM PASS + insertion check"})
    P.add_type(name, (CLW, SLH), f"qfd_qc_slice_{side}{pos}", cont,
               note="slice partition v1 (exceeds one hop and has 10 kit clock roots: split is the v2 item)")
    return name


# ====================================================================== west strip
WS_BLOCKS = {
    # name: (type, module, (w, h), (x, y), hard, kit-note)
    "io_serdes_2": ("phy_serdes", "ot_qfd_serdes_112g_x12_phy_s597", (MC_W, 2324.16), (0.0, 0.0), True),
    "io_serdes_1": ("phy_serdes1", "ot_qfd_serdes_112g_x12_phy_s597", (MC_W, 2324.16), (0.0, 2324.16), True),
    "io_collective": ("coll", "qfd_collective_static_io_production", (MC_W, 4570.56), (0.0, 4648.32), False),
    "io_serdes": ("phy_serdes3", "ot_qfd_serdes_112g_x12_phy_s597", (MC_W, 2324.16), (0.0, 9218.88), True),
    "ucie_kv": ("phy_ucie_kv", "ot_qkvd_ucie_x64_phy", (777.6, 777.6), (786.24, 11543.04), True),
    "io_ucie": ("phy_ucie_coll", "ot_qfd_ucie_x64_phy", (777.6, 777.6), (MC_W, 5443.2), True),
    "glue": ("glue", "qfd_qc_wglue", (777.6, 1209.6), (MC_W, 10886.4), False),
    "native59": ("native59", "qfd_native59_dv_headprep_obs1", (777.6, 518.4), (MC_W, 12096.0), False),
    "tt_ctlm": ("tt_ctlm", "qfd_tt_ctlm_dv_hp13_rp", (777.6, 518.4), (MC_W, 12614.4), False),
}
STN = {"s2": 1555.2, "s3": 2332.8, "s4": 3110.4, "s5": 3888.0, "s6": 4665.6, "s9": 7776.0, "s10": 8553.6,
       "s11": 9331.2, "s12": 10108.8}
GLUE_INSTS = ("d2d_rom", "sys_face", "embed_prov", "mu_ctxrx", "mu_dhobs", "rstseq_rom", "ckb_rom",
              "rs_bump", "bump_fwd_epoch", "bump_fwd_lrst")
COLL_INSTS = ("io_collective", "clk_rx", "ckdiv_coll_blk", "bump_pkg_s0", "bump_pkg_s1", "bump_die_ps", "ckb_core")
WS_PATHS = {   # partition sequences for non-abutting W-strip pairs (station column)
    ("io_serdes_2", "io_collective"): ["io_serdes_2", "s2", "s3", "s4", "s5", "s6", "io_collective"],
    ("io_collective", "SLW"): ["io_collective", "s9", "s10", "s11", "s12", "SLW"],
    ("glue", "io_collective"): ["glue", "s12", "s11", "s10", "s9", "io_collective"],
    ("tt_ctlm", "glue"): ["tt_ctlm", "native59", "glue"],
}


def build_west(P, census_blocks):
    for n, (tn, mod, wh, xy, hard) in WS_BLOCKS.items():
        cont = []
        if n == "glue":
            for i in GLUE_INSTS:
                cont.append({"inst": f"u_{i}", "module": census_blocks.get(i, i), "status": "reuse",
                             "note": "small W-strip block, merged into the glue partition (one clock/reset region)"})
        elif n == "io_collective":
            for i in COLL_INSTS:
                cont.append({"inst": f"u_{i}", "module": census_blocks.get(i, i), "status": "reuse",
                             "note": "collective macro + die clock receiver strip (PHY face clocks stay inside)"})
        elif n == "tt_ctlm":
            cont.append({"inst": "u_tt_ctlm", "module": "qfd_hp13_cpub39_rp_alt", "status": "rework",
                         "outline_um": [501.0, 514.0], "kit": "claude/qtile-r-1023 qfd_hp13_cpub39_rp_{main,alt}",
                         "note": "HP13 ctlm re-pack (rp main/alt CTS gates running); as-built stand-in has open f16 "
                                 "inputs/outputs (bind owed)"})
        else:
            cont.append({"inst": f"u_{n}", "module": mod, "status": "reuse",
                         "note": "hard IP / closed block used as-is" if hard else "reuse candidate"})
        P.add_type(tn, wh, mod if hard else f"qfd_qc_{tn}_part", cont, hard=hard,
                   note=f"west strip: {n}")
        P.add_part(n, tn, *xy)
    for s, y in STN.items():
        P.add_type(f"stn_{s}", (C2_W, 777.6), f"qfd_qc_wstn_{s}",
                   [{"inst": "u_pstn", "module": f"qfd_qc_wstn_{s}", "status": "new",
                     "note": "generated station partition (ft slots only)"}], note="west-strip station partition")
        P.add_part(s, f"stn_{s}", MC_W, y)


# ====================================================================== links
def cb_links(P, geo):
    """cluster-internal links + cluster <-> slice / near <-> far."""
    for cl in geo["clusters"]:
        n, kind = cl["name"], cl["kind"]
        p = lambda c, r: f"{n}_{c}{r}"  # noqa: E731
        # bc column runs (functional xstn per row)
        for c in range(4):
            for r in range(3):
                P.link(f"bc{c}", [p(c, r), p(c, r + 1)], "bc_o", "bc_i", BW,
                       src_leaf="u_xstn.b_o", dst_leaf="u_xstn.b_i")
        # tree (16-leaf pair tree; leaves of quadrant SW = 0..3, SE 4..7, NW 8..11, NE 12..15)
        T = []
        for r in range(4):
            T.append((f"t0{r}", [(0, r), (1, r)], "t_o", "na_i", "u_t.t_out", "u_t.n_a"))
            T.append((f"t3{r}", [(3, r), (2, r)], "t_o", "na_i", "u_t.t_out", "u_t.n_a"))
        T += [("l1a", [(1, 1), (0, 1)], "y_o", "na_i", "u_t.n_y", "u_t.n_a"),
              ("l1b", [(1, 0), (1, 1), (0, 1)], "y_o", "nb_i", "u_t.n_y", "u_t.n_b"),
              ("l1c", [(2, 1), (3, 1)], "y_o", "na_i", "u_t.n_y", "u_t.n_a"),
              ("l1d", [(2, 0), (2, 1), (3, 1)], "y_o", "nb_i", "u_t.n_y", "u_t.n_b"),
              ("l1e", [(1, 2), (0, 2)], "y_o", "na_i", "u_t.n_y", "u_t.n_a"),
              ("l1f", [(1, 3), (1, 2), (0, 2)], "y_o", "nb_i", "u_t.n_y", "u_t.n_b"),
              ("l1g", [(2, 2), (3, 2)], "y_o", "na_i", "u_t.n_y", "u_t.n_a"),
              ("l1h", [(2, 3), (2, 2), (3, 2)], "y_o", "nb_i", "u_t.n_y", "u_t.n_b"),
              ("l2a", [(3, 1), (3, 0)], "y_o", "na_i", "u_t.n_y", "u_t.n_a"),
              ("l2b", [(0, 1), (0, 0), (1, 0), (2, 0), (3, 0)], "y_o", "nb_i", "u_t.n_y", "u_t.n_b"),
              ("l2c", [(0, 2), (0, 3)], "y_o", "na_i", "u_t.n_y", "u_t.n_a"),
              ("l2d", [(3, 2), (3, 3), (2, 3), (1, 3), (0, 3)], "y_o", "nb_i", "u_t.n_y", "u_t.n_b"),
              ("l3a", [(3, 0), (2, 0), (1, 0), (0, 0)], "y_o", "na_i", "u_t.n_y", "u_t.n_a"),
              ("l3b", [(0, 3), (0, 2), (0, 1), (0, 0)], "y_o", "nb_i", "u_t.n_y", "u_t.n_b")]
        for role, path, sb, db, sl, dl in T:
            P.link(role, [p(*q) for q in path], sb, db, RSW, src_leaf=sl, dst_leaf=dl)
    # inter-cluster / slice
    byk = collections.defaultdict(dict)
    for cl in geo["clusters"]:
        byk[cl["col"]][(cl["half"], cl["kind"])] = cl["name"]
    for k in range(NCOL):
        sl = f"sl_{geo['col_name'][k]}"
        for half, fs in (("t", "n"), ("b", "s")):
            near, far = byk[k][(half, "near")], byk[k][(half, "far")]
            for c in range(4):
                P.link(f"cw{fs}{c}", [sl, f"{near}_{c}0"], f"cw_{fs}{c}", "bc_i", BW,
                       src_leaf=f"u_slice.cw_{fs}{c}", dst_leaf="u_xstn.b_i")
                P.link(f"bcf{c}", [f"{near}_{c}3", f"{far}_{c}0"], "bc_o", "bc_i", BW,
                       src_leaf="u_xstn.b_o", dst_leaf="u_xstn.b_i")
            P.link(f"rs{fs}0", [f"{near}_00", sl], "y_o", f"rs_{fs}0", RSW, src_leaf="u_t.n_y",
                   dst_leaf=f"u_slice.rs_{fs}0")
            P.link(f"rs{fs}1", [f"{far}_00", f"{near}_03", f"{near}_02", f"{near}_01", f"{near}_00", sl], "y_o",
                   f"rs_{fs}1", RSW, src_leaf="u_t.n_y", dst_leaf=f"u_slice.rs_{fs}1")


def census_links(P, geo, census):
    """slice chain + west strip from the as-built census groups."""
    col_of = {f"dvs_{n}": f"sl_{n}" for n in geo["col_name"]}

    def part_of(inst):
        if inst in col_of:
            return col_of[inst]
        if inst in GLUE_INSTS:
            return "glue"
        if inst in COLL_INSTS:
            return "io_collective"
        if inst in WS_BLOCKS:
            return inst
        return None
    seen = set()
    dropped = collections.Counter()
    for g in census["groups"]:
        s, d = part_of(g["src"]), part_of(g["dst"])
        if g["src"].startswith("c16") or g["dst"].startswith("c16"):
            continue                                    # cluster links are generated by cb_links
        if s is None or d is None:
            dropped[(g["src"].split("_")[0], g["dst"].split("_")[0], g["kind"])] += g["bits"]
            continue
        if s == d:
            continue                                    # inside one partition
        if g["kind"] == "reset":
            dropped[("reset", g["src"], g["dst"])] += g["bits"]
            continue                                    # plan reset: one synchronizer per partition
        if g["src"] == "clk_rx":
            dropped[("clock", g["src"], g["dst"])] += g["bits"]
            continue                                    # die clock spine branches
        key = (s, g["src"], g["src_bus"], d, g["dst"], g["dst_bus"])
        if key in seen:
            continue
        seen.add(key)
        sb = g["src_bus"] if s.startswith("sl_") or s in WS_BLOCKS and s not in ("glue", "io_collective") \
            else f"{g['src']}__{g['src_bus']}"
        db = g["dst_bus"] if d.startswith("sl_") or d in WS_BLOCKS and d not in ("glue", "io_collective") \
            else f"{g['dst']}__{g['dst_bus']}"
        # a fan-out to several partitions needs one out bus per destination
        sb_key = (s, sb)
        path = ws_path(P, s, d)
        role = re.sub(r"[^A-Za-z0-9]", "_", f"{g['src_bus']}_{g['dst_bus']}")
        kind = "clock" if g["src_bus"] == "lclk" else (g["kind"] if g["kind"] in ("data", "ctl") else "ctl")
        P.link(role, path, sb, db, g["bits"], kind=kind,
               src_leaf=leaf_of(s, g["src"], g["src_bus"]), dst_leaf=leaf_of(d, g["dst"], g["dst_bus"]))
    # fan-out: same (part, out bus) used by several links -> suffix by destination
    cnt = collections.Counter((lk["path"][0], lk["src_bus"]) for lk in P.links)
    for lk in P.links:
        if cnt[(lk["path"][0], lk["src_bus"])] > 1:
            lk["src_bus"] = f"{lk['src_bus']}__to_{lk['path'][-1]}__{lk['dst_bus']}"
    # several sources into one as-built bus (e.g. serdes_rx = 3 x 597): one in bus per source
    cnt = collections.Counter((lk["path"][-1], lk["dst_bus"]) for lk in P.links)
    for lk in P.links:
        if cnt[(lk["path"][-1], lk["dst_bus"])] > 1:
            lk["dst_bus"] = f"{lk['dst_bus']}__from_{lk['path'][0]}"
    # fault chain: slices E -> W, W5 -> glue; collective + tt_ctlm fault -> glue (local OR inside each partition)
    names = geo["col_name"]                     # W5..W0, E0..E5 (west to east)
    for k in range(NCOL - 1, 0, -1):
        P.link("flt", [f"sl_{names[k]}", f"sl_{names[k - 1]}"], "flt_o", "flt_i", 1, kind="ctl",
               src_leaf="u_slice.flt_o", dst_leaf="u_slice.flt_i")
    P.link("flt", [f"sl_{names[0]}", "glue"], "flt_o", "sl_flt_i", 1, kind="ctl", src_leaf="u_slice.flt_o",
           dst_leaf="u_sys_face.obs_fault_sl")
    P.link("fltc", ws_path(P, "io_collective", "glue"), "flt_o", "coll_flt_i", 1, kind="ctl",
           src_leaf="u_io_collective.fault_or", dst_leaf="u_sys_face.obs_fault_coll")
    P.link("fltt", ws_path(P, "tt_ctlm", "glue"), "flt_o", "ctlm_flt_i", 1, kind="ctl",
           src_leaf="u_tt_ctlm.cf", dst_leaf="u_sys_face.obs_fault_ctlm")
    return dropped


def leaf_of(part, inst, bus):
    if part.startswith("sl_"):
        return f"u_slice.{bus}"
    return f"u_{inst}.{bus}"


def ws_path(P, s, d):
    sw = lambda n: "SLW" if n == "sl_W5" else n  # noqa: E731
    for (a, b), path in WS_PATHS.items():
        if (sw(s), sw(d)) == (a, b):
            return [s if x == "SLW" and s == "sl_W5" else (d if x == "SLW" else x) for x in path]
        if (sw(s), sw(d)) == (b, a):
            rp = list(reversed(path))
            return [s if x == "SLW" and s == "sl_W5" else (d if x == "SLW" else x) for x in rp]
    shared_face(P, s, d)        # raises if they do not abut
    return [s, d]


# ====================================================================== ports / slots / windows
def materialize(P):
    """links -> buses, ft slots, ports, lanes; windows allocated per shared face pair."""
    ports, lanes = [], []
    facepairs = collections.defaultdict(list)     # (a, b) sorted -> [(port dict, width)]
    slot_req = {}                                  # (type, slot) -> dict
    bus_req = {}                                   # (type, bus) -> dict
    lid_n = collections.Counter()
    for lk in P.links:
        path, role, w = lk["path"], lk["role"], lk["width"]
        pids = []
        base = f"{path[0]}__{role}"
        lid_n[base] += 1
        lid = base if lid_n[base] == 1 else f"{base}_{lid_n[base]}"
        for i, (a, b) in enumerate(zip(path, path[1:])):
            f, lo, hi = shared_face(P, a, b)
            sb = lk["src_bus"] if i == 0 else f"{role}_o"
            db = lk["dst_bus"] if i == len(path) - 2 else f"{role}_i"
            pid = f"{lid}__{i}"
            pr = {"id": pid, "src": {"part": a, "bus": sb}, "dst": {"part": b, "bus": db}, "width": w,
                  "kind": lk["kind"], "face": f, "layers": ["M6", "M4"] if f in "EW" else ["M7", "M5"]}
            ports.append(pr)
            facepairs[(a, b) if a < b else (b, a)].append(pr)
            pids.append(pid)
            if i == 0:
                bus_req.setdefault((P.parts[a]["type"], sb), dict(name=sb, dir="out", width=w, kind=lk["kind"],
                                                                  leaf=lk["src_leaf"]))
            if i == len(path) - 2:
                bus_req.setdefault((P.parts[b]["type"], db), dict(name=db, dir="in", width=w, kind=lk["kind"],
                                                                  leaf=lk["dst_leaf"]))
        for j in range(1, len(path) - 1):
            part = path[j]
            fin = OPP[shared_face(P, path[j - 1], part)[0]]
            fout = shared_face(P, part, path[j + 1])[0]
            slot_req.setdefault((P.parts[part]["type"], role), dict(name=role, in_face=fin, out_face=fout, width=w))
        lanes.append({"id": lid, "ports": pids, **({"param": lk["param"]} if lk.get("param") else {})})
    # windows: per face pair, in the coordinates of the lower-left partition so replicated types match
    for (a, b), prs in facepairs.items():
        f, lo, hi = shared_face(P, a, b)
        ra, rb = P.rect(a), P.rect(b)
        ll = a if (ra[0], ra[1]) < (rb[0], rb[1]) else b
        prs.sort(key=lambda pr: pr["src"]["bus"] if pr["src"]["part"] == ll else pr["dst"]["bus"])
        cur = lo + EDGE
        for pr in prs:
            L = wlen(pr["width"])
            pr["window_um"] = [round(cur, 4), round(cur + L, 4)]
            cur += L + GAP
        if cur - GAP > hi - EDGE + 1e-6:
            raise SystemExit(f"face {a}/{b} ({f}) overfull: {cur - lo:.1f} um needed, {hi - lo:.1f} available")
    # station counts from the slot route length (in-face window centre -> out-face window centre)
    pmap = {pr["id"]: pr for pr in ports}
    for ln in lanes:
        for a, b in zip(ln["ports"], ln["ports"][1:]):
            pa, pb = pmap[a], pmap[b]
            part = pa["dst"]["part"]
            role = pa["dst"]["bus"][:-2]
            ka = (P.parts[part]["type"], role)
            ca, cb = port_pt(P, pa), port_pt(P, pb)
            L = abs(ca[0] - cb[0]) + abs(ca[1] - cb[1])
            k = max(1, math.ceil(L / ST_LEN))
            slot_req[ka]["stations"] = max(slot_req[ka].get("stations", 1), k)
    for (tn, bn), b in bus_req.items():
        P.types[tn]["buses"].append(b)
    for (tn, sn), s in slot_req.items():
        P.types[tn]["ft_slots"].append(s)
    return ports, lanes


def port_pt(P, pr):
    part = pr["src"]["part"]
    x0, y0, x1, y1 = P.rect(part)
    c = sum(pr["window_um"]) / 2
    return {"E": (x1, c), "W": (x0, c), "N": (c, y1), "S": (c, y0)}[pr["face"]]


# ====================================================================== main
def slice_leaves(fp_w, fp_e):
    out = {}
    for side, fp in (("w", fp_w), ("e", fp_e)):
        d = json.loads(Path(fp).read_text())
        c = collections.Counter((b["master"], b["w"], b["h"]) for b in d["blocks"])
        out[side] = [(m, n, (w, h)) for (m, w, h), n in sorted(c.items())]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--census", required=True)
    ap.add_argument("--slice-fp-w", required=True)
    ap.add_argument("--slice-fp-e", required=True)
    ap.add_argument("--out", default=str(Path(__file__).with_name("die_plan.json")))
    a = ap.parse_args()
    census = json.load(gzip.open(a.census)) if a.census.endswith(".gz") else json.loads(Path(a.census).read_text())
    cblocks = {b["inst"]: b["master"] for b in census["blocks"]}
    P = Plan()
    geo = build_geometry(P, slice_leaves(a.slice_fp_w, a.slice_fp_e))
    build_west(P, cblocks)
    cb_links(P, geo)
    dropped = census_links(P, geo, census)
    ports, lanes = materialize(P)
    W, H = geo["W"], geo["H"]
    # die channels: uncovered west-strip area (the strip content is shorter than the compute column)
    chans = [{"rect_um": [0.0, 11543.04, 786.24, H], "reason": "west strip spare (macro column): IO content ends at "
              "11.9 mm in a 25.2-mm column; bump/IO redistribution candidate"},
             {"rect_um": [786.24, 12320.64, MC_W, H], "reason": "west strip spare above ucie_kv"},
             {"rect_um": [MC_W, 13132.8, WS_W, H], "reason": "west strip spare above tt_ctlm"},
             {"rect_um": [MC_W, 0.0, WS_W, 1555.2], "reason": "station column below s2 (no lane)"},
             {"rect_um": [MC_W, 6220.8, WS_W, 7776.0], "reason": "station column between io_ucie and s9 (no lane)"}]
    plan = {
        "schema": "opentallas.die_plan.v1",
        "note": "PLAN-QC v1 2026-10-23: Qwen compute die, plan-first (TOPDOWN-PLAN). Generated by "
                "physical/die_plan/qwen_compute/gen_plan.py from the as-built connectivity (FT-TOOL census, r50/r56 "
                "die) and the A0 rpf geometry. Replaces the stale single-die TP8 contract.",
        "die": {"name": "qwen_compute", "label": "Qwen3-8B ROM compute die (TP8 pair with the KV/system die)",
                "tech": "asap7", "outline_um": [round(W, 4), round(H, 4)], "period_ps": 833, "reach_um": REACH,
                "rep_um": 450.0, "grid_um": G,
                "layer_budget": {"partition_signal_max": "M7", "die_layers": ["M8", "M9"],
                                 "die_use": ["clock_spine", "pg", "ft_reserved", "reset"],
                                 "cut_avail": {"M8": 0.6, "M9": 0.6}},
                "channels": chans,
                "pg": {"partition_pg_max": "M7", "grid": [
                    {"layer": "M8", "width_um": 0.48, "pitch_um": 8.64, "offset_um": 4.32, "nets": ["VDD", "VSS"]},
                    {"layer": "M9", "width_um": 0.48, "pitch_um": 8.64, "offset_um": 4.32, "nets": ["VDD", "VSS"]}]}},
        "partition_types": P.types,
        "partitions": [{"name": n, "type": p["type"], "origin_um": list(p["origin"]), "orient": "R0"}
                       for n, p in P.parts.items()],
        "ports": ports, "lanes": lanes,
        "clock": {"source": {"part": "io_collective", "bus": "clk_rx"}, "insertion_ps": 250, "insertion_tol_ps": 40,
                  "neighbour_skew_ps": 80, "face_xing": "budgeted",
                  "spine": {"layers": ["M8", "M9"], "root_um": [round(W / 2, 2), round(geo["y_sl"] + SLH / 2, 2)],
                            "topology": "htree"}},
        "reset": {"source": {"part": "glue", "bus": "rstseq_rom"}, "sync_stages": 2, "data_reset": False,
                  "epoch_bit": True, "release": "counted"},
        "budgets": {"face_pins_per_um": 6, "face_pin_layers": 2, "face_window_um": 10, "pin_track_max": 0.6,
                    "cut_ratio_max": 0.6, "cut_step_um": 250},
    }
    Path(a.out).write_text(json.dumps(plan, indent=1) + "\n")
    # notes / ledger
    st = collections.Counter()
    for n, p in P.parts.items():
        for c in P.types[p["type"]]["contents"]:
            st[c["status"]] += 1
    notes = {"partitions": len(P.parts), "types": len(P.types), "ports": len(ports), "lanes": len(lanes),
             "die_um": [round(W, 2), round(H, 2)], "die_mm2": round(W * H / 1e6, 1),
             "content_status_per_instance": dict(st),
             "type_status": dict(collections.Counter(c["status"] for t in P.types.values() for c in t["contents"])),
             "census_dropped_bits": {"|".join(map(str, k)): v for k, v in sorted(dropped.items())}}
    Path(a.out).with_name("plan_notes.json").write_text(json.dumps(notes, indent=1) + "\n")
    print(json.dumps({k: v for k, v in notes.items() if k != "census_dropped_bits"}))


if __name__ == "__main__":
    main()
