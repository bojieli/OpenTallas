#!/usr/bin/env python3
"""PLAN-QCv2: Qwen compute die plan v2 generator (TOPDOWN-PLAN, owner-approved 2026-10-23).

    python3 physical/die_plan/qwen_compute/gen_plan.py --variant A|B --census QC_CENSUS.json.gz \
        --slice-fp-w FP.json --slice-fp-e FP.json --slice-record S8_LP_RECORD.json [--out DIR/die_plan.json]

Writes die_plan.json (schema opentallas.die_plan.v1, tools/die_plan) plus plan_notes.json (counts, cell estimates,
reuse ledger, open items).  Inputs: the as-built die connectivity (FT-TOOL census of the r50/r56 die), the slice kit
floorplans (leaf inventory) and the slice landed-parent record (results/arch/codex_slice2_native_1021/s8: the 210
region-to-region landed crossings = the slice-internal connectivity census at region granularity).

v2 structure (die lattice 2.16 um; every dimension below is a multiple of 8.64):
  * 12 compute columns, 2471.04 um pitch: far | near | slice | near | far (bottom to top).
      variant A: each CB16 cluster slot = 4 x 4 abutted partitions (one A0 rpf reference each, ~0.62 x 1.30 mm).
      variant B: each CB16 cluster slot = 2 x 2 CB quads (4 A0 each, ~1.24 x 2.61 mm; internal stations).
    Bottom-half clusters are MX copies of the top types.  The A0 reference sits centred in its cell (one type for
    mirrored and column-shifted copies).
  * Slice row (v2 item 1): each slice = 15 partitions on a 4 x 4 grid aligned to the CB columns, rows 1080 um (864
    overflowed the region faces), slice height 4320.  Partitions = the slice's own landed clock regions (spec tools/landed_parent/specs/qfd_dv_s8
    .json): hc0..hc3 (N row, one per CB column), fw / fe (W / E face strips), stm, tap, ctl, sc, st_a (r_st0-3),
    st_b (r_st4-7), and the SU block r_su split into su_c (suvm + red, 2 cells) and two lane groups su_l0 / su_l1
    (lanes 0-3 / 4-7, 1 cell each).  Grid assignment = slice_layout_search.py (negotiated face routing; max face
    load 0.93).  Broadcast nets (tap hw -> hc0-3, stm tw_data -> ctl/st_a) become registered forwarding trees.  The cs_c -> u_fs -> cw_s_c forwarder becomes the plan lane hc_c -> S face of column c.
  * West strip (v2 item 2): one 1563.84-um column (the serdes PHY depth sets the width):
      S2 | S1 | [io_collective = 9 abutted y segments, 786.24 wide (QC-FIX: coll_s S1+S2 faces, coll_f0-2 ft,
      coll_core = collective core + P face + UCIe PHY + R face, coll_f3-5 ft, coll_n S0 face; one tap each, per-core
      taps in plan_notes.clock_taps) + 777.6-wide edge column: ucie_kv, glue, native59, tt_ctlm] | S3 (MX)
    coll_f4 abuts the W5 slice fw face; S2 reaches coll_s through the W5 far-bottom CB column 0 (ft slots).
  * Census (G0): census/ die_rows + slice_rows + coll_rows with their maps (write_census).
  * Fault chain (GEOM-REVIEW2 item: ~560 flt bits): one 1-bit registered OR tree per partition, re-derived: each
    cluster a serpentine ending at its (0,0) unit -> slice; each slice a BFS tree to its W-flowing face partition;
    slices chain E -> W; W5 -> coll -> glue (sys_face.obs).  Release age counted, not scheduled.
"""
import argparse
import collections
import gzip
import json
import math
import re
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools" / "die_plan"))
import schema as _S  # noqa: E402  (PLAN-TOOL pin rule: window sizing uses the exact G0 pin placement)

_LAYERS = {L["name"]: L for L in _S.ASAP7_LAYERS}

G = 8.64                             # die lattice: PLAN-TOOL G0 needs a multiple of every M2-M9 pitch (2.16 is not a multiple of 0.064)
G8 = 8.64
REACH = 405.0                         # METHODOLOGY 9.3/9.4 + OWNER DECISION 12 (10-24): die hops / ft stations <= 405 um, M2-M7
REACH_OLD = 1000.0
ST_LEN = float(__import__('os').environ.get('QC_FT_REACH', 405.0))  # OWNER DECISION 12 (10-24): ft on <= M7, stations every <= 405 um
ST_LEN_OLD = 750.0                       # one station per <= 750 um of slot route (GEOM-REVIEW4 10-23: a 1-station slot
                                     # hop must stay within the measured M5-M7 repeated reach 600-750 um)
DENS = 4.2                           # pins / um per port window (budget 6 incl. track rounding)
GAP = 0.96
EDGE = 4.32

CW = [622.08, 613.44, 613.44, 622.08]
RH = [1313.28, 1296.0, 1296.0, 1321.92]
A0W, A0H = 457.92, 1157.76
CLW, CLH = sum(CW), sum(RH)          # 2471.04 x 5227.2
# QC-SUROW 10-25: slice rows 1080 -> 1339.2 (155 x 8.64).  The SU row (su_l1 | su_c | su_l0) is
# crossed by every N-S cluster lane of its columns (cws*, rsf/rsn turning W->N: 1,544 bits through each su_l) and the
# lane cores filled 86% of the su_l width (macro-free V strip 69 + 17 um), so the slice negotiation with SU transit priced
# physically (QC_NEG_CORE_FT) was infeasible (su_l V 1.104 from the pre-routed lanes alone; ctl|stm 1.085, fw|stm 1.09).
# Taller rows + narrower/taller lane cores (SU_LANE_CORE) give each su_l a 190-um macro-free V channel: negotiation
# feasible with the S-half rs words on the SU row (SU_ROW_RS); E slices (extra fixed fe->fw lane) need 1339.2, 1296
# leaves E ctl|stm at 1.075.  Die height +4 x 259.2 = +1036.8 um (+32.4 mm2, 787.5 -> 819.9 mm2).
SRH = float(__import__("os").environ.get("QC_SRH", "1339.2"))   # slice row height (was 1080; 864 overflowed at 4.7 pins/um)
SLH = 4 * SRH
NCOL = 12
RESET_ENTRY_FACE = {"phy_serdes": "E", "phy_serdes_b": "E", "phy_ucie_kv": "E"}   # hard PHY reset entries face the coll column
WS_W = 1563.84                       # west strip = serdes PHY depth
SUB_W = 777.6                        # west-strip edge column (UCIe PHYs + glue)
COLL_W = WS_W - SUB_W                # 786.24
BW, RSW = 516, 514

A0_KIT = "physical/ref_tile/qfd_tile_nk_romleaf_rpf (claude/a0-repack-1023 36a2db0b4)"
A0L_KIT = "physical/ref_tile/qfd_tile_nl_romleaf_rpf (claude/a0-repack-1023 36a2db0b4)"
XSTN_KIT = "rtl/physical/qcluster/qfd_c_xstn_safe.sv (claude/plan-qcv2-1023 5da2a2abe: fanout tree, tap_p 444 b)"
A0_GEOM = "lanes/GEOM-REVIEW.md A0 rpf PASS-CONDITIONAL; TOPDOWN L1: reuse reference, flattened in the partition"
A0_CELLS = 187991                    # NL rpf synth_stat (agidock128 gate 10-23, incl. 10 ROM leaf macros)
CELL_UM2 = 0.52                      # avg std-cell area of that synth (std area / cells): density calibration
UTIL = 0.6

OPP = dict(N="S", S="N", E="W", W="E")


def snap(v, g=G):
    return round(round(v / g) * g, 4)


class Plan:
    def __init__(self):
        self.parts = {}
        self.types = {}
        self.links = []
        self.cells = {}            # type -> std-cell estimate
        self.internal_bits = collections.Counter()
        self.load = collections.Counter()      # face-pair bits (slice routing)

    def add_type(self, name, wh, module, contents, hard=False, kit=None, note=None, tap=None, cells=None):
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
        tp = tap or [snap(w / 2, G8), snap(h / 2, G8)]
        t["clock"] = {"tap_um": tp, "layer": "M9", "insertion_ps": 250, "insertion_tol_ps": 40}
        t["reset"] = {"tap_um": tp, "sync_stages": 2}
        if name in RESET_ENTRY_FACE:
            # OWNER DECISION 13 wavefront (RESET 10-24): a hard partition is a leaf whose reset tap = its registered
            # entry; put it on the face toward its soft neighbour so the parent rst_o hop stays <= 405 um
            f = RESET_ENTRY_FACE[name]
            t["reset"]["tap_um"] = {"E": [snap(w - 10.0, G8), snap(h / 2, G8)], "W": [snap(10.0, G8), snap(h / 2, G8)],
                                    "N": [snap(w / 2, G8), snap(h - 10.0, G8)], "S": [snap(w / 2, G8), snap(10.0, G8)]}[f]
        self.types[name] = t
        if cells is not None:
            self.cells[name] = cells
        return t

    def add_part(self, name, tname, x, y, orient="R0"):
        assert name not in self.parts, name
        w, h = self.types[tname]["outline_um"]
        self.parts[name] = dict(type=tname, origin=(round(x, 4), round(y, 4)), wh=(w, h), orient=orient)

    def tface(self, n, die_face):
        o = self.parts[n]["orient"]
        if o in ("MX", "R180") and die_face in "NS":
            return OPP[die_face]
        if o in ("MY", "R180") and die_face in "EW":
            return OPP[die_face]
        return die_face

    def rect(self, n):
        (x, y), (w, h) = self.parts[n]["origin"], self.parts[n]["wh"]
        return (x, y, x + w, y + h)

    def centre(self, n):
        x0, y0, x1, y1 = self.rect(n)
        return ((x0 + x1) / 2, (y0 + y1) / 2)

    def link(self, role, path, src_bus, dst_bus, width, kind="data", src_leaf=None, dst_leaf=None, param=None):
        p = [path[0]]
        for x in path[1:]:
            if x != p[-1]:
                p.append(x)
        if len(p) == 1:
            self.internal_bits[role] += width
            return
        for x, y in zip(p, p[1:]):
            self.load[tuple(sorted((x, y)))] += width
        self.links.append(dict(role=role, path=p, src_bus=src_bus, dst_bus=dst_bus, width=width, kind=kind,
                               src_leaf=src_leaf, dst_leaf=dst_leaf, param=param))


def shared_face(P, a, b, quiet=False):
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
        if quiet:
            return None
        raise SystemExit(f"{a} and {b} do not abut")
    if hi - lo < 10:
        if quiet:
            return None
        raise SystemExit(f"{a} / {b}: overlap {hi - lo:.1f} um too short")
    return f, lo, hi


PITCH = {"M4": (0.048, 0.024), "M5": (0.048, 0.024), "M6": (0.064, 0.032), "M7": (0.064, 0.032)}
# Joint face/over-the-top negotiation: 5.7 pins/um stays below G0 6/um and PIN_MAX 5.8.
NEG_PIN_UM = float(__import__("os").environ.get("QC_NEG_PIN_UM", "5.7"))   # slice negotiation face capacity (QC-P5 10-23: 5.0 -> 5.1 pins/um, G0 face budget 6; frees the detours that padded R8 classes)
NEG_BCAST_HOP = float(__import__("os").environ.get("QC_NEG_BCAST_HOP", "1"))  # hop-cost multiplier of broadcast-tree flows
NEG_BCAST_FIX = __import__("os").environ.get("QC_NEG_BCAST_FIX", "1") == "1"
NEG_HOP_UM = float(__import__("os").environ.get("QC_NEG_HOP_UM", "2500"))  # per-partition-hop cost of a slice flow (QC-P6-R8:
                                     # every hop is a register stage; raise it to trade face detours for fewer stages)
# QC-A0 10-24 (G0C ft_budget, xdie.check_ft_budget): a flow that crosses a partition uses its over-the-top die layers --
# M8 when its in/out faces include E/W, M9 when they include N/S (a turning slot uses both).  The negotiation now also
# prices each partition's M8 / M9 ft use against usable die-layer tracks across it (8.796 / um, the check's PG-free
# M8 / M9 count) x cut_avail 0.6 x NEG_FT_FILL (head-room for the census / treq / fault lanes routed after it).
NEG_FT_TRK_UM = float(__import__("os").environ.get("QC_NEG_FT_TRK_UM", "8.796"))
NEG_FT_AVAIL = 0.6
NEG_L9_RESERVE = int(__import__("os").environ.get("QC_NEG_L9_RESERVE", "514"))
NEG_SPLIT = int(__import__("os").environ.get("QC_NEG_SPLIT", "800"))
NEG_FT_FILL = float(__import__("os").environ.get("QC_NEG_FT_FILL", "1.0"))     # V (M9)
NEG_FT_FILL_H = float(__import__("os").environ.get("QC_NEG_FT_FILL_H", "1.0"))  # H (M8)
NEG_CORE_FT = __import__("os").environ.get("QC_NEG_CORE_FT", "1") == "1"   # price SU-core partitions by macro-free ft length
NEG_CORE_OVER = float(__import__("os").environ.get("QC_NEG_CORE_OVER", "0.3333"))  # share of cored length usable (M6/M7 of M2-M7)
PIN_MAX = 5.8                          # pins/um the laid window may reach at its worst 10-um span (G0 budget 6)
FACE_MAX = 6.0                         # QC-P2: per-window pins/um by the tool rule (G0 = 6/um + 2 pins/layer allowance)
_QL = {}


def _pins(lo, hi, w, layers):
    """the PLAN-TOOL pin_positions() rule (schema.py): bits alternate over layers, even integer-track spread with
    the centre parity fix -- reproduced here to size windows by the pins G0 will actually count."""
    out = []
    nl = len(layers)
    for li, ln in enumerate(layers):
        p, off = PITCH[ln]
        n = len(range(li, w, nl))
        if n == 0:
            continue
        k0 = math.ceil((lo - off) / p - 1e-9)
        k1 = math.floor((hi - off) / p + 1e-9)
        ntr = k1 - k0 + 1
        if ntr < n:
            return None
        step = max(1, ntr // n)
        if (k0 + k1 - (n - 1) * step) % 2 and step > 1:
            step -= 1
        first = (k0 + k1 - (n - 1) * step) // 2
        out += [off + (first + j * step) * p for j in range(n)]
    return sorted(out)


def qlen(width, dens, layers, lo=100.0, flip=False, fmax=None):
    """smallest window length (from width/FACE_MAX up, 0.016 steps) at its ACTUAL die position (lattice 8.64: the same
    pins in every frame) whose pins, laid by the PLAN-TOOL rule itself (schema.pin_positions: coordinate-uniform
    spread, never on a partition PG stripe band), stay <= FACE_MAX/um in every 10-um span.  QC-P2: the old replica of
    the pin rule ignored the PG bands (G0 failed 1-bit ports whose window sat inside an M5/M7 band)."""
    fm = fmax or FACE_MAX
    key = (width, tuple(layers), round(lo % G, 4), flip, fm)
    if key in _QL:
        return _QL[key]
    L = max(0.384, math.ceil(width / fm / 0.016) * 0.016)
    while True:
        win = [lo - L, lo] if flip else [lo, lo + L]
        try:
            cs = sorted(c for _, _, c in _S.pin_positions(
                {"id": "q", "window_um": win, "layers": list(layers), "width": width, "epoch": False}, _LAYERS))
        except ValueError:
            cs = None
        ok = cs is not None
        if ok:
            # G0 budgets usable tracks per layer, including narrow control buses.
            # A legal pin position alone may consume the only track off the PG bands.
            ok = all(len(range(li, width, len(layers))) <=
                     0.6 * _S.usable_tracks(_LAYERS[ln], ln, *win)
                     for li, ln in enumerate(layers))
        if ok:
            j = 0
            for i in range(len(cs)):
                while cs[i] - cs[j] > 10.0 - 1e-6:
                    j += 1
                if (i - j + 1) > fm * 10.0 + 1e-6:
                    ok = False
                    break
        if ok:
            _QL[key] = round(L, 4)
            return _QL[key]
        L += 0.016


def wlen(width, dens=None):
    n = math.ceil(width / (dens or DENS) / 0.192) * 0.192
    return max(round(n, 4), 0.384)


# ====================================================================== CB clusters
def a0_origin(c, r, half):
    x = snap((CW[c] - A0W) / 2)
    y = snap((RH[r] - A0H) / 2)
    return [x, y]                          # centred: identical in the mirrored (bottom) frame


def unit_of(variant, c, r):
    """CB unit (partition) holding cluster cell (c, r): A = the cell, B = its 2 x 2 quad."""
    return (c, r) if variant == "A" else (c // 2, r // 2)


def unit_rect(variant, u):
    """unit origin and size inside the cluster frame (top-half orientation, row 0 at the slice side)."""
    if variant == "A":
        c, r = u
        return sum(CW[:c]), sum(RH[:r]), CW[c], RH[r]
    cq, rq = u
    return sum(CW[:2 * cq]), sum(RH[:2 * rq]), CW[2 * cq] + CW[2 * cq + 1], RH[2 * rq] + RH[2 * rq + 1]


def w_quad(variant, u):
    return unit_rect(variant, u)[2]


A0_CK = (457.824, 668.076)           # QC-A0 a0_core.json: single ck pin, core frame R0 (E edge)


def a0_ck(origin, orient):
    x = origin[0] + (A0W - A0_CK[0] if orient == "MY" else A0_CK[0])
    return [round(x, 3), round(origin[1] + A0_CK[1], 3)]


def cb_type(P, variant, kind, u):
    if variant == "A":
        c, r = u
        shared = (c != 0 and r != 3)
        cells = [(c, r)]
        tag = f"{'x' if shared else kind[0]}_{c}{r}"
    else:
        cq, rq = u
        shared = (cq != 0 and rq != 1)
        cells = [(c, r) for r in (2 * rq, 2 * rq + 1) for c in (2 * cq, 2 * cq + 1)]
        tag = f"{'x' if shared else kind[0]}_q{cq}{rq}"
    name = f"cb{tag}"
    if name in P.types:
        return name
    ux, uy, w, h = unit_rect(variant, u)
    cont = []
    for c, r in cells:
        sfx = "" if variant == "A" else f"{c}{r}"
        ox, oy = a0_origin(c, r, "t")
        nl = (c, r) == NL_CELL
        x = round(sum(CW[:c]) - ux + ox, 4)
        orient = "R0"
        if variant == "B" and c % 2 == 1:
            # QC-FIX (COORD/QC-A0 10-23): the east core of each quad row is MY-mirrored and placed mirror-symmetric to
            # the west core about the quad centre, so both ck pins (core E edge, a0_core.json) face the quad centre at
            # the same distance (west 73.5/82.2 um, east identical) -> one matched quad H-tap, no 640/1090-um skew.
            wx = round(sum(CW[:c - 1]) - ux + a0_origin(c - 1, r, "t")[0], 4)
            x = round(w_quad(variant, u) - (wx + A0W), 4)
            orient = "MY"
        cont.append({"inst": f"u_t{sfx}", "module": "qfd_tile_nl_romleaf_rpf" if nl else "qfd_tile_nk_romleaf_rpf",
                     "status": "reuse", "kit": A0L_KIT if nl else A0_KIT, "geom_pass": A0_GEOM,
                     "origin_um": [x, round(sum(RH[:r]) - uy + oy, 4)],
                     "outline_um": [A0W, A0H],
                     "note": f"A0 core, orient {orient} in the partition frame (TOPDOWN L1 amend: planned hard core "
                             f"qfd_tile_n{'l' if nl else 'k'}_a0c, spec cores/a0_core.json)"})
        cont.append({"inst": f"u_xstn{sfx}", "module": "qfd_c_xstn_safe", "status": "rework", "kit": XSTN_KIT,
                     "note": "bc column station + tap (registered fanout tree, no constant pins); flattened"})
    cont.append({"inst": "u_pstn", "module": f"qfd_qc_cb{tag}_stn", "status": "new",
                 "note": "generated: boundary flops of every port, ft-slot stations (reset-less data + 1 epoch bit), "
                         "tree operand aligners from the latency table, fault OR, reset synchronizer"})
    n = len(cells)
    est = n * A0_CELLS + n * 1700 + 6000 * n
    P.add_type(name, (w, h), f"qfd_qc_cb_{tag}", cont, cells=est,
               note=f"CB16 {'partition' if variant == 'A' else 'quad'} {u}, {'near+far' if shared else kind}; "
                    f"bottom half = MX copies")
    return name


def build_clusters(P, variant, col_x, col_name):
    clusters = []
    y_far_b, y_near_b, y_near_t, y_far_t = 0.0, CLH, 2 * CLH + SLH, 3 * CLH + SLH
    units = sorted({unit_of(variant, c, r) for c in range(4) for r in range(4)})
    for k in range(NCOL):
        cx = col_x[k]
        for kind, half, y0 in (("far", "b", y_far_b), ("near", "b", y_near_b), ("near", "t", y_near_t),
                               ("far", "t", y_far_t)):
            cname = f"c_{col_name[k]}_{half}{kind[0]}"
            clusters.append(dict(name=cname, col=k, kind=kind, half=half, x=cx, y=y0))
            for u in units:
                tn = cb_type(P, variant, kind, u)
                ux, uy, w, h = unit_rect(variant, u)
                py = y0 + uy if half == "t" else y0 + CLH - uy - h
                P.add_part(f"{cname}_{u[0]}{u[1]}", tn, cx + ux, py, "R0" if half == "t" else "MX")
    return clusters


def cb_part(variant, cname, c, r):
    u = unit_of(variant, c, r)
    return f"{cname}_{u[0]}{u[1]}"


# As-built CB16 reduction tree (qfd_c_b16_dv_fabric, traced through its stations/landings by QC-P3 10-23 for
# BINDER2's R7 finding: the old hand-written l1a..l3b map left 3 x 514 b per cluster UNPLANNED): every tile input
# (dst (c, r), port) <- source tile (c, r) output.  u_t_<c>_<r>; u_t_3_0 is the NL tile (no n_a/n_b).
CB_TREE = [((0, 0), "n_a", (2, 2), "n_y"), ((0, 1), "n_a", (0, 1), "t_out"), ((0, 2), "n_a", (0, 2), "t_out"),
           ((0, 3), "n_a", (0, 3), "t_out"), ((1, 0), "n_a", (0, 0), "t_out"), ((1, 1), "n_a", (1, 0), "n_y"),
           ((1, 2), "n_a", (1, 3), "n_y"), ((1, 3), "n_a", (0, 2), "n_y"), ((2, 0), "n_a", (2, 0), "t_out"),
           ((2, 1), "n_a", (2, 0), "n_y"), ((2, 2), "n_a", (1, 1), "n_y"), ((2, 3), "n_a", (3, 2), "n_y"),
           ((3, 1), "n_a", (2, 1), "t_out"), ((3, 2), "n_a", (2, 2), "t_out"), ((3, 3), "n_a", (2, 3), "t_out"),
           ((0, 0), "n_b", (1, 2), "n_y"), ((0, 1), "n_b", (1, 1), "t_out"), ((0, 2), "n_b", (1, 2), "t_out"),
           ((0, 3), "n_b", (1, 3), "t_out"), ((1, 0), "n_b", (1, 0), "t_out"), ((1, 1), "n_b", (0, 1), "n_y"),
           ((1, 2), "n_b", (2, 3), "n_y"), ((1, 3), "n_b", (0, 3), "n_y"), ((2, 0), "n_b", (3, 0), "t_out"),
           ((2, 1), "n_b", (3, 1), "n_y"), ((2, 2), "n_b", (2, 1), "n_y"), ((2, 3), "n_b", (3, 3), "n_y"),
           ((3, 1), "n_b", (3, 1), "t_out"), ((3, 2), "n_b", (3, 2), "t_out"), ((3, 3), "n_b", (3, 3), "t_out")]
NL_CELL = (3, 0)


def cb_links(P, variant, geo):
    for cl in geo["clusters"]:
        n = cl["name"]
        p = lambda c, r: cb_part(variant, n, c, r)  # noqa: E731
        sfx = (lambda c, r: "") if variant == "A" else (lambda c, r: f"{c}{r}")  # noqa: E731
        for c in range(4):
            for r in range(3):
                P.link(f"bc{c}{r}" if variant == "B" else f"bc{c}", [p(c, r), p(c, r + 1)], f"bc_o{sfx(c, r)}",
                       f"bc_i{sfx(c, r + 1)}", BW, src_leaf=f"u_xstn{sfx(c, r)}.a_d",
                       dst_leaf=f"u_xstn{sfx(c, r + 1)}.b_d")
        T = []
        for (dc, dr), dport, (sc, sr), sport in CB_TREE:
            sq, dq = unit_of(variant, sc, sr), unit_of(variant, dc, dr)
            path = [(sc, sr), (dc, dr)]
            if variant == "B" and sq[0] != dq[0] and sq[1] != dq[1]:
                # diagonal quad pair: forward through the quad beside both (q11->q00 via q01, q00->q11 via q10)
                path = [(sc, sr), (2 * dq[0], 2 * sq[1]), (dc, dr)]
            role = f"{'a' if dport == 'n_a' else 'b'}{dc}{dr}"
            T.append((role, path, "y_o" if sport == "n_y" else "t_o", "na_i" if dport == "n_a" else "nb_i",
                      sport, dport))
        for role, path, sb, db, sl, dl in T:
            s, d = path[0], path[-1]
            P.link(role, [p(*q) for q in path], f"{sb}{sfx(*s)}", f"{db}{sfx(*d)}", RSW,
                   src_leaf=f"u_t{sfx(*s)}.{sl}", dst_leaf=f"u_t{sfx(*d)}.{dl}")


# ====================================================================== slices
# slice regions on the 4x4 grid: chosen by slice_layout_search.py (negotiated routing over 3 x 524k layouts, fw/fe
# row 0/1/2; args 5517 3159 1500 <row>); fw/fe on the W/E edges of one row so they abut the neighbour slices; hc row fixed
# on the cluster side. Best max face load 0.928 at 5.15 pins/um, 1080-um rows (fw/fe row 2: 0.959; row 0: 1.028)
SL_CELLS_W = {"hc0": (0, 3), "hc1": (1, 3), "hc2": (2, 3), "hc3": (3, 3),
              "st_b": (0, 2), "ctl": [(1, 2), (2, 2)], "st_a": (3, 2),
              "fw": (0, 1), "stm": (1, 1), "sc": (2, 1), "fe": (3, 1),
              "su_l1": (0, 0), "su_c": [(1, 0), (2, 0)], "su_l0": (3, 0)}
# E slices: SAME layout as W (QC-P2 10-23, census coverage).  The as-built die places the e16real kit MY, so every
# slice has its dn face (fw: ch_dn/st_dn/l9/... = census *_eo on E slices) physically on the W edge: the inter-slice
# chain is linear E5 -> .. -> E0 -> W0 -> .. -> W5 (census pins: dvs_E1 ard_eo leaves at E1's W edge x=20001.6).  The
# v2 mirrored E layout put fw on the E edge, so slice-to-slice traffic could not abut (57.8k bits were dropped).
SL_CELLS_E = dict(SL_CELLS_W)
REGION_OF = {"r_fw": "fw", "r_fe": "fe", "r_stm": "stm", "r_ctl": "ctl", "r_sc": "sc", "r_su": "su_c",
             "r_tap": "ctl", **{f"r_hc{i}": f"hc{i}" for i in range(4)},
             **{f"r_st{i}": ("st_a" if i < 4 else "st_b") for i in range(8)}}
LEAF_REGION = [(r"^u_r[0-3]$", "st_a"), (r"^u_r[4-7]$", "st_b"), (r"^u_btab\b", "st_a"), (r"^u_stm", "stm"),
               (r"^u_ctl", "ctl"), (r"^u_suvm", "su_c"), (r"^u_(lrly|head|exp|rcp|rsq)([0-3])$", "su_l0"),
               (r"^u_(lrly|head|exp|rcp|rsq)([4-7])$", "su_l1"), (r"^u_xh(\d)|^u_xl(\d)_", "hc")]
SOFT = {"fw": ["u_fdn"], "fe": ["u_fup"], "stm": ["u_stm", "u_fs (cs->cw_s forwarder: becomes plan lane)"],
        "ctl": ["u_ctl", "u_rp", "u_tap"], "sc": ["u_sc"], "su_c": ["u_suvm", "u_red"],
        "hc1": ["u_fn"], "st_a": ["u_frs"]}
SOFT_CELLS = {"fw": 60000, "fe": 50000, "stm": 60000, "ctl": 150000, "sc": 40000, "su_c": 60000,
              "su_l0": 20000, "su_l1": 20000, "st_a": 20000, "st_b": 10000}


def leaf_region(inst):
    for pat, reg in LEAF_REGION:
        m = re.match(pat, inst.replace("*", "_"))
        if m:
            if reg == "hc":
                return f"hc{m.group(1) or m.group(2)}"
            return reg
    return None


def slice_cells(side):
    return SL_CELLS_W if side == "w" else SL_CELLS_E


def slice_geom(side, reg):
    cells = slice_cells(side)[reg]
    cells = cells if isinstance(cells, list) else [cells]
    c0 = min(c for c, r in cells)
    c1 = max(c for c, r in cells)
    r0 = min(r for c, r in cells)
    r1 = max(r for c, r in cells)
    return sum(CW[:c0]), r0 * SRH, sum(CW[c0:c1 + 1]), (r1 - r0 + 1) * SRH


def build_slices(P, col_x, col_name, y_sl, fp):
    """slice partitions: one TYPE per (side, region, column) here; identical ones are merged after windows."""
    for k in range(NCOL):
        side = "w" if k < 6 else "e"
        for reg in slice_cells(side):
            x, y, w, h = slice_geom(side, reg)
            tn = f"sl{side}_{reg}__{col_name[k]}"
            cont = []
            fpi = {b["inst"].replace("*", "_") for b in fp[side]["blocks"]}
            for m in SOFT.get(reg, []):
                if m.split()[0] in fpi:
                    continue
                cont.append({"inst": m.split()[0], "module": f"slice {'s8' if side == 'w' else 's6b'} {m}",
                             "status": "rework", "note": "slice glue re-derived per region partition"})
            area = 0.0
            for b in fp[side]["blocks"]:
                if leaf_region(b["inst"]) == reg:
                    area += b["w"] * b["h"]
                    cont.append({"inst": b["inst"].replace("*", "_"), "module": b["master"], "status": "reuse",
                                 "outline_um": [b["w"], b["h"]],
                                 "note": "closed slice leaf (reference; flattened unless macro)"})
            cells = int(area * UTIL / CELL_UM2) + SOFT_CELLS.get(reg, 15000)
            P.add_type(tn, (w, h), f"qfd_qc_sl{side}_{reg}", cont, cells=cells,
                       note=f"slice region partition {reg} ({'W' if side == 'w' else 'E'} slice, landed region "
                            f"{'r_su' if reg.startswith('su') else reg})")
            P.add_part(f"sl_{col_name[k]}_{reg}", tn, col_x[k] + x, y_sl + y)


def sl(geo, k, reg):
    return f"sl_{geo['col_name'][k]}_{reg}"


BCAST = {  # broadcast nets of the slice record -> plan forwarding trees (registered relay in the receiving partition)
    ("r_tap", "hw"): [("ctl", "hc0"), ("ctl", "hc1"), ("ctl", "hc2"), ("ctl", "hc3")],
    ("r_stm", "tw_data"): [("stm", "ctl"), ("ctl", "st_a")],
}
BCAST_PATH = {("ctl", "hc1"): ["ctl", "hc1"], ("ctl", "hc2"): ["ctl", "hc2"], ("ctl", "hc0"): ["ctl", "st_b", "hc0"],
              ("ctl", "hc3"): ["ctl", "st_a", "hc3"], ("stm", "ctl"): ["stm", "ctl"], ("ctl", "st_a"): ["ctl", "st_a"]}
# QC-P6-R8 10-23 (COORD R8 PAD BUDGET, target < 150k pad flops): the chain tap -> hc2 -> hc1 -> hc0 / hc2 -> hc3 landed
# hw at 2/4/6/4 (pads 4/2/0/2 x 1,573 b x 12 slices = 150k) and tw_data stm -> ctl -> st_a at 2/5.  Now r_tap and r_ctl
# share ONE partition `ctl` spanning slice cells (1,2)+(2,2), centred under hc1|hc2: hw is a balanced tree of direct
# lanes from it (hc1 / hc2 abut: 2 cycles; hc0 / hc3 one station: 3), and tw_data goes stm -> ctl and stm -> st_a as
# direct lanes (2 / 3, st_a through the merged partition's station) instead of being re-launched by ctl.
# QC-P5 10-23 (COORD R8 pad budget): the tw control bits travel WITH tw_data (same as-built cycle, same readers u_rp /
# u_btab).  As separate x flows they lost the full stm|ctl face and detoured 6 hops (12 cycles), so the whole tw class
# padded to 17 (331k pad flops).  One broadcast bundle keeps them on the 1-hop tree.
BCAST_ALIAS = {("r_stm", n): ("r_stm", "tw_data") for n in ("tw_addr", "tw_kind", "tw_we")}


def directed_slice_landings(record, su_directed):
    """Split the former r_su group using exact s8 child-pin source directions.

    The old L0|L1=504 was shared gb/gv/reset input overlap, not a driven lane.
    Preserve every external landing bit; count actual internal SU directions.
    """
    rows = [dict(r) for r in record["landings"] if "r_su" not in (r["src_region"], r["dst_region"])]
    # The landed-parent record describes entire source rings. Plan each destination's consumed port bits,
    # e.g. cid[23:0] is four independent six-bit identities, not a 24-bit input to every head.
    consumed = record.get("_reader_port_bits", {})
    for row in rows:
        readers = row.get("readers", [])
        if readers and all(reader in consumed for reader in readers):
            row["width"] = min(row["width"], sum(consumed[reader] for reader in set(readers)))
    rows += [dict(src_region=r["src"], dst_region=r["dst"], net=r["net"], width=r["bits"])
             for r in su_directed["external"]]
    return rows


def slice_internal_links(P, geo, record, su_split, su_directed):
    for k in range(NCOL):
        agg = collections.Counter()
        trees = collections.Counter()
        nets = {}                           # broadcast key -> {net: width} (bundle = sum of its nets)
        for ld in directed_slice_landings(record, su_directed):
            s, d = (REGION_OF.get(ld[x], ld[x]) for x in ("src_region", "dst_region"))
            if ld["net"] in ("cs0", "cs1", "cs2", "cs3"):
                continue                    # cs_c -> u_fs -> cw_s_c: replaced by the plan lane hc_c -> S face
            if s == d:
                continue
            bk = (ld["src_region"], ld["net"])
            if bk in BCAST or bk in BCAST_ALIAS:
                kk = BCAST_ALIAS.get(bk, bk)
                nets.setdefault(kk, {})[ld["net"]] = max(nets.setdefault(kk, {}).get(ld["net"], 0), ld["width"])
                continue
            agg[(s, d)] += ld["width"]
        for kk, nw in nets.items():
            trees[kk] = sum(nw.values())
        for row in su_directed["internal"]:
            agg[(row["src"], row["dst"])] += row["bits"]
        # QC-P6-R8: one lane per partition pair on a broadcast hop -- the pair's other bits ride the tree lane (the
        # binder packs a pair's crossings into its lanes in path order, so a separate x lane took tree bits onto a
        # detour: 2 tw bits at 11 cycles padded the whole tw class)
        hopw = collections.Counter()
        for bk, w in trees.items():
            for a, b in BCAST[bk]:
                hopw[(bk, a, b)] = w + agg.pop((a, b), 0)
        flows = [(f"b_{bk[1]}_{a}_{b}", a, b, hopw[(bk, a, b)], f"b_{bk[1]}_{b}_o", f"b_{bk[1]}_i",
                  f"u_pstn.{bk[1]}_fwd", f"u_{b}.{bk[1]}") for bk in trees for a, b in BCAST[bk]]
        # QC-A0 10-24 (G0C ft_budget): a pair flow wider than NEG_SPLIT bits becomes ceil(w / NEG_SPLIT) near-equal
        # lanes (x_a_b, x_a_b_p1, ...) so the negotiation can spread it over two feedthrough partitions; the binder packs
        # a pair's crossing bits over all of the pair's lanes (bind.py build_buses pass 1b).
        for (a, b), w in agg.items():
            n = max(1, -(-w // NEG_SPLIT)) if NEG_SPLIT > 0 else 1
            for j in range(n):
                wj = w // n + (1 if j < w % n else 0)
                sx = "" if j == 0 else f"_p{j}"
                flows.append((f"x_{a}_{b}{sx}", a, b, wj, f"x_{b}{sx}_o", f"x_{a}{sx}_i", f"u_{a}.x_{b}", f"u_{b}.x_{a}"))
        hopw = [NEG_BCAST_HOP if f[0].startswith("b_") else 1.0 for f in flows]
        fixed = [[sl(geo, k, r) for r in BCAST_PATH.get((f[1], f[2]), [])] if f[0].startswith("b_") and NEG_BCAST_FIX
                 and (f[1], f[2]) in BCAST_PATH else None for f in flows]
        nflows = [(sl(geo, k, f[1]), sl(geo, k, f[2]), f[3], hw, fx) for f, hw, fx in zip(flows, hopw, fixed)]
        # QC-A0 10-24: the E slices' l9 pair word (census_links, routed after this negotiation fe -> sc -> stm -> fw) is
        # reserved here on that straight middle-row path, so the face / ft budgets it needs stay free
        if geo["col_name"][k].startswith("E") and NEG_L9_RESERVE > 0:
            nflows.append((sl(geo, k, "fe"), sl(geo, k, "fw"), NEG_L9_RESERVE, 1.0,
                           [sl(geo, k, r) for r in ("fe", "sc", "stm", "fw")]))
        paths = negotiate(P, geo, k, nflows)[:len(flows)]
        for f, pth in zip(flows, paths):
            P.link(f[0], pth, f[4], f[5], f[3], src_leaf=f[6], dst_leaf=f[7])



def negotiate(P, geo, k, flows, iters=300):
    """PathFinder-style negotiated routing of slice flows over the partition adjacency (face capacity 5.6 pins/um)."""
    import heapq
    names = [n for n in P.parts if n.startswith(f"sl_{geo['col_name'][k]}_")]
    nb = {n: [] for n in names}
    for i, n in enumerate(names):
        for m in names[i + 1:]:
            sf = shared_face(P, n, m, quiet=True)
            if sf:
                cap = (sf[2] - sf[1] - 2 * EDGE) * NEG_PIN_UM
                d = abs(P.centre(n)[0] - P.centre(m)[0]) + abs(P.centre(n)[1] - P.centre(m)[1])
                nb[n].append((m, cap, d))
                nb[m].append((n, cap, d))
    base = {e: v for e, v in P.load.items() if e[0] in nb}
    sfc = {(n, m): shared_face(P, n, m)[0] for n in nb for m, _, _ in nb[n]}
    # partition over-the-top ft budget (H = M8 across the height, V = M9 across the width) and its use by the links
    # already planned through this slice's partitions (cluster lanes routed before the negotiation)
    ncap = {}
    for n in nb:
        x0, y0, x1, y1 = P.rect(n)
        f = NEG_FT_TRK_UM * NEG_FT_AVAIL
        ncap[(n, "H")], ncap[(n, "V")] = (y1 - y0) * f * NEG_FT_FILL_H, (x1 - x0) * f * NEG_FT_FILL
        reg = n.split("_", 2)[2]
        if NEG_CORE_FT and reg in ("su_l0", "su_l1", "su_c"):
            # QC-PLAN 10-25 (PROTO sle_su_l0 STRUCTURAL, GRT ov 17k point / 397k strict channel): ft runs on M2-M7
            # inside the partition (decision 12), the SU lane cores block M1-M5 and every station site must sit in
            # the macro-free strip / gaps.  Price a SU partition's transit capacity by its macro-free length plus
            # NEG_CORE_OVER of the cored length (M6/M7 over the macros), not by its full outline.
            ncol = 2 if reg == "su_c" else 1
            cw, ch = SU_LANE_CORE
            hfree, hcore = (y1 - y0) - len(SU_LANE_Y) * ch, len(SU_LANE_Y) * ch
            vfree, vcore = (x1 - x0) - ncol * cw, ncol * cw
            ncap[(n, "H")] = (hfree + NEG_CORE_OVER * hcore) * f
            ncap[(n, "V")] = (vfree + NEG_CORE_OVER * vcore) * f

    def ftdirs(fi, fo):
        fs = {fi, fo}
        return [d for d, ff in (("H", {"E", "W"}), ("V", {"N", "S"})) if fs & ff]

    nbase = collections.Counter()
    for lk in P.links:
        pth = lk["path"]
        for i in range(1, len(pth) - 1):
            n = pth[i]
            if n in nb:
                fi = shared_face(P, n, pth[i - 1], quiet=True)
                fo = shared_face(P, n, pth[i + 1], quiet=True)
                if fi and fo:
                    for d in ftdirs(fi[0], fo[0]):
                        nbase[(n, d)] += lk["width"]
    nhist = collections.Counter()
    if __import__("os").environ.get("QC_NEG_DUMP"):
        import pickle
        with open(__import__("os").environ["QC_NEG_DUMP"] + f".{k}.pkl", "wb") as fh:
            pickle.dump(dict(flows=[tuple(f) for f in flows], nb=nb, base=dict(base), sfc=sfc, nbase=dict(nbase),
                             ncap=ncap), fh)
    hist = collections.Counter()
    pf = 0.5
    order = sorted(range(len(flows)), key=lambda i: (len(flows[i]) < 5 or flows[i][4] is None, -flows[i][2]))
    for it in range(iters):
        load = collections.Counter(base)
        nload = collections.Counter(nbase)
        paths = [None] * len(flows)
        for i in order:
            a, b, w, hopw, fx = (tuple(flows[i]) + (1.0, None))[:5]
            if fx is not None:          # fixed broadcast-tree path (R8: shortest register depth, routed first)
                paths[i] = fx
                for x, y in zip(fx, fx[1:]):
                    load[tuple(sorted((x, y)))] += w
                for j in range(1, len(fx) - 1):
                    for dd_ in ftdirs(sfc[(fx[j], fx[j - 1])], sfc[(fx[j], fx[j + 1])]):
                        nload[(fx[j], dd_)] += w
                continue
            st0 = (a, None)
            dist, prev, pq = {st0: 0.0}, {}, [(0.0, a, None)]
            end = None
            while pq:
                dd, n, pn = heapq.heappop(pq)
                if n == b:
                    end = (n, pn)
                    break
                if dd > dist[(n, pn)]:
                    continue
                for m, cap, d in nb[n]:
                    if pn is not None and (m == pn or sfc[(n, pn)] == sfc[(n, m)]):
                        continue                  # no U-turn through one face (slot in_face == out_face)
                    st, seen = (n, pn), False
                    while st is not None:
                        if st[0] == m:
                            seen = True
                            break
                        st = prev.get(st)
                    if seen:
                        continue                  # simple paths only (one slot per partition per flow)
                    e = tuple(sorted((n, m)))
                    over = max(0.0, (load[e] + w) / cap - 1.0)
                    nover, nh = 0.0, 0.0
                    if pn is not None:          # n becomes a feedthrough of this flow: pn-face -> m-face
                        for dn in ftdirs(sfc[(n, pn)], sfc[(n, m)]):
                            nover = max(nover, (nload[(n, dn)] + w) / ncap[(n, dn)] - 1.0)
                            nh = max(nh, nhist[(n, dn)])
                    nd = dd + (d + NEG_HOP_UM * hopw) * (1 + hist[e] + nh) * (1 + pf * (over + nover) * 10)
                    if nd < dist.get((m, n), float("inf")):
                        dist[(m, n)], prev[(m, n)] = nd, (n, pn)
                        heapq.heappush(pq, (nd, m, n))
            if end is None:
                raise SystemExit(f"negotiate: no path {a}->{b} nb={[x[0] for x in nb[a]]} it={it}")
            pth, st = [], end
            while st is not None:
                pth.append(st[0])
                st = prev.get(st)
            pth.reverse()
            if len(set(pth)) != len(pth):
                raise SystemExit(f"negotiate: path revisits a partition {pth}")
            paths[i] = pth
            for x, y in zip(pth, pth[1:]):
                load[tuple(sorted((x, y)))] += w
            for j in range(1, len(pth) - 1):
                for dn in ftdirs(sfc[(pth[j], pth[j - 1])], sfc[(pth[j], pth[j + 1])]):
                    nload[(pth[j], dn)] += w
        caps = {tuple(sorted((n, m))): cap for n in nb for m, cap, _ in nb[n]}
        over = {e: load[e] / caps[e] for e in caps if load[e] > caps[e]}
        nover_ = {k_: nload[k_] / ncap[k_] for k_ in ncap if nload[k_] > ncap[k_]}
        if not over and not nover_:
            return paths
        for e, r in over.items():
            hist[e] += r - 1.0 + 0.2
        for k_, r in nover_.items():
            nhist[k_] += r - 1.0 + 0.2
        pf = min(pf * 1.3, 1e4)
    rep = {f"{x[5:]}|{y[5:]}": (round(base.get((x, y), 0)), round(load[(x, y)]), round(caps[(x, y)])) for x, y in caps}
    over = dict(over, **{f"ft:{a[0]}:{a[1]}": round(r, 3) for a, r in nover_.items()})
    raise SystemExit(f"slice {geo['col_name'][k]}: negotiated routing left overflow {over}; base/load/cap {rep}; "
                     f"flows {[(f[0][5:], f[1][5:], f[2]) for f in flows]}")


def _ftdirs(fi, fo):
    fs = {fi, fo}
    return [d for d, ff in (("H", {"E", "W"}), ("V", {"N", "S"})) if fs & ff]


def route(P, a, b, geo, k, width=1):
    """shortest abutting path a -> b inside slice k (BFS on partition adjacency, Manhattan tie-break)."""
    names = [n for n in P.parts if n.startswith(f"sl_{geo['col_name'][k]}_")]
    if a not in names or b not in names:
        raise SystemExit(f"route {a}->{b}")
    import heapq
    ca = P.centre
    # QC-A0 10-24 (G0C ft_budget): a hop that would push the partition it crosses over its over-the-top M8 / M9 budget
    # (xdie.check_ft_budget arithmetic: usable tracks x 0.6) is not taken; partitions already over keep the old rule
    nuse = collections.Counter()
    for lk in P.links:
        pth = lk["path"]
        for i in range(1, len(pth) - 1):
            fi = shared_face(P, pth[i], pth[i - 1], quiet=True)
            fo = shared_face(P, pth[i], pth[i + 1], quiet=True)
            if fi and fo:
                for dn in _ftdirs(fi[0], fo[0]):
                    nuse[(pth[i], dn)] += lk["width"]

    def ft_ok(n, pn, m):
        if pn is None:
            return True
        for dn in _ftdirs(shared_face(P, n, pn)[0], shared_face(P, n, m)[0]):
            x0, y0, x1, y1 = P.rect(n)
            capn = (y1 - y0 if dn == "H" else x1 - x0) * NEG_FT_TRK_UM * NEG_FT_AVAIL
            if nuse[(n, dn)] <= capn and nuse[(n, dn)] + width > capn:
                return False
        return True
    dist = {a: 0.0}
    prev = {}
    pq = [(0.0, a)]
    while pq:
        dd, n = heapq.heappop(pq)
        if n == b:
            break
        if dd > dist[n]:
            continue
        for m in names:
            sf = shared_face(P, n, m, quiet=True) if m != n else None
            if sf is None:
                continue
            if not ft_ok(n, prev.get(n), m):
                continue
            # QC-A0 10-24: after the slice negotiation (P.neg_done) the face capacity is the negotiation's (the l9 lane
            # reserved there must fit the same faces)
            cap = (sf[2] - sf[1] - 2 * EDGE) * (max(5.6, NEG_PIN_UM) if getattr(P, "neg_done", False) else 5.6)
            ld = P.load[tuple(sorted((n, m)))] + width
            if ld > cap:
                continue
            nd = dd + (abs(ca(n)[0] - ca(m)[0]) + abs(ca(n)[1] - ca(m)[1])) * (1 + (ld / cap) ** 4) + 1.0
            if nd < dist.get(m, 1e18):
                dist[m] = nd
                prev[m] = n
                heapq.heappush(pq, (nd, m))
    if b not in prev and a != b:
        raise SystemExit(f"route {a}->{b} width {width}: no capacity; loads " + str(
            {f"{x}|{y}": v for (x, y), v in P.load.items() if x.startswith(f"sl_{geo['col_name'][k]}_")}))
    path = [b]
    while path[-1] != a:
        path.append(prev[path[-1]])
    return list(reversed(path))


def slice_cluster_links(P, variant, geo):
    byk = collections.defaultdict(dict)
    for cl in geo["clusters"]:
        byk[cl["col"]][(cl["half"], cl["kind"])] = cl["name"]
    for k in range(NCOL):
        side = "w" if k < 6 else "e"
        for half, fs in (("t", "n"), ("b", "s")):
            near, far = byk[k][(half, "near")], byk[k][(half, "far")]
            sfx = (lambda c, r: "") if variant == "A" else (lambda c, r: f"{c}{r}")  # noqa: E731
            for c in range(4):
                if fs == "n":
                    path = [sl(geo, k, f"hc{c}"), cb_part(variant, near, c, 0)]
                    sleaf = "u_xh.n_d"
                else:          # cs_c: down column c of the slice to the S face (was u_fs)
                    col = [reg for reg, cc in slice_cells(side).items()
                           if (c in [x for x, _ in (cc if isinstance(cc, list) else [cc])])]
                    rows = sorted(col, key=lambda reg: -slice_geom(side, reg)[1])
                    path = [sl(geo, k, reg) for reg in rows] + [cb_part(variant, near, c, 0)]
                    sleaf = "u_xh.s_d"
                P.link(f"cw{fs}{c}", path, f"cw_{fs}{c}", f"bc_i{sfx(c, 0)}", BW, src_leaf=sleaf,
                       dst_leaf=f"u_xstn{sfx(c, 0)}.b_d")
                P.link(f"bcf{c}", [cb_part(variant, near, c, 3), cb_part(variant, far, c, 0)], f"bc_o{sfx(c, 3)}",
                       f"bc_i{sfx(c, 0)}", BW, src_leaf=f"u_xstn{sfx(c, 3)}.a_d", dst_leaf=f"u_xstn{sfx(c, 0)}.b_d")
            rs_dst = "hc1" if fs == "n" else "st_a"
            entry = "hc0" if fs == "n" else [reg for reg, cc in slice_cells(side).items()
                                             if (0, 0) in (cc if isinstance(cc, list) else [cc])][0]
            if fs == "s" and SU_ROW_RS:
                # QC-SUROW 10-25: the S-half rsn/rsf words (2 x 514) run along the SU row to st_a (su_l1 -> su_c -> su_l0
                # -> fe -> st_a) in every slice.  route() sent them up column 0 in W1/W2 (fw/st_b/ctl), which together
                # with the slice flows over-filled ctl|stm and st_b V once SU transit is priced physically; the SU row has
                # H room with the taller rows (su H ft <= 0.45).  8 of 12 slices already used this path.
                inner = [sl(geo, k, r) for r in ("su_l1", "su_c", "su_l0", "fe", "st_a")]
                assert inner[0] == sl(geo, k, entry), (inner, entry)
            else:
                inner = route(P, sl(geo, k, entry), sl(geo, k, rs_dst), geo, k, 2 * RSW)
            P.link("rsn", [cb_part(variant, near, 0, 0)] + inner, f"y_o{sfx(0, 0)}", f"rs_{fs}0", RSW,
                   src_leaf=f"u_t{sfx(0, 0)}.n_y", dst_leaf=f"u_f{'n' if fs == 'n' else 'rs'}.rs_{fs}_lo")
            P.link("rsf", [cb_part(variant, far, 0, 0)] + [cb_part(variant, near, 0, r) for r in (3, 2, 1, 0)] +
                   inner, f"y_o{sfx(0, 0)}", f"rs_{fs}1", RSW, src_leaf=f"u_t{sfx(0, 0)}.n_y",
                   dst_leaf=f"u_f{'n' if fs == 'n' else 'rs'}.rs_{fs}_hi")


# ====================================================================== west strip
# QC-FIX 10-23 (GEOM-REVIEW3 07:24 + COORD 07:24 ruling (2) CLOCK TAPS): io_collective is no longer ONE 786 x 9098-um
# partition with one tap.  It is a stack of abutted segments along y, each with its own tap + reset sync, with every
# collective face core at its PHY and the collective core in the middle, so no seam carries more than two record
# spokes (S1+S2 below the core, slice + S0 above: <= 2.2 kb on a 786-um face, <= 3/um):
#   coll_s     S1 + S2 face cores (S1 PHY below, S2 via the W5 far-bottom CB column)
#   coll_f0-2  feedthrough segments (S1/S2 record spokes + stations; bump/decap field to the W)
#   coll_core  collective core u_collective + P face core + UCIe PHY hard core + R face core + u_shared / u_gearbox /
#              ckdiv / clk_rx / bumps / codec_pl landing.  The FDI clocks and the P/R <-> share frames stay inside;
#              1589.76 um tall, so per ruling (2) it takes one tap per planned core (P, UCIe, R) + its glue tap
#   coll_f3/f4 feedthrough (slice in/out + S0 spokes, glue / native59 / tt_ctlm links; f4 abuts the W5 slice fw face)
#   coll_f5    feedthrough (S0 spoke)        coll_n  S0 face core (S0 PHY above)
# The face <-> core records (tx W+3 / rx W+1, rtl/physical/ot_qfd_collective_static_io.sv: the as-built RU/RS2 paid
# relay rows) become plan lanes with stations.
# QC-SUROW 10-25: the slice rows grew (SRH); the W5 fw row (slice row 1) starts WS_DY higher, so coll_f4 / f5 / coll_n,
# native59 / tt_ctlm and the top serdes PHY move up by WS_DY and the coll_f3 / glue segments below them grow by WS_DY
# (coll_f4 keeps its 734.4-um seam with W5 fw).
WS_DY = round(SRH - 1080.0, 2)
COLL_SEGS = [  # (partition, type, y0, h)
    ("coll_s", "coll_s", 4648.32, 803.52),
    ("coll_f0", "coll_ft", 5451.84, 993.6), ("coll_f1", "coll_ft", 6445.44, 993.6),
    ("coll_f2", "coll_ft", 7439.04, 993.6),
    ("coll_core", "coll_core", 8432.64, 1589.76),
    ("coll_f3", "coll_ftm", 10022.4, 1209.6 + WS_DY),
    ("coll_f4", "coll_ftc", 11232.0 + WS_DY, 1036.8),
    ("coll_f5", "coll_ftn", 12268.8 + WS_DY, 691.2),
    ("coll_n", "coll_n", 12960.0 + WS_DY, 786.24),
]
COLL_PARTS = [c[0] for c in COLL_SEGS]
WS = {  # name: (type, module, (w, h), (x, y), orient, hard)
    "io_serdes_2": ("phy_serdes_b", "ot_qfd_serdes_112g_x12_phy_s597", (WS_W, 2324.16), (0.0, 0.0), "R0", True),
    "io_serdes_1": ("phy_serdes", "ot_qfd_serdes_112g_x12_phy_s597", (WS_W, 2324.16), (0.0, 2324.16), "R0", True),
    **{n: (tn, f"qfd_qc_{tn}_part", (COLL_W, h), (SUB_W, y0), "R0", False) for n, tn, y0, h in COLL_SEGS},
    "io_serdes": ("phy_serdes", "ot_qfd_serdes_112g_x12_phy_s597", (WS_W, 2324.16), (0.0, 13746.24 + WS_DY), "MX", True),
    "ucie_kv": ("phy_ucie_kv", "ot_qkvd_ucie_x64_phy", (SUB_W, 777.6), (0.0, 9244.8), "R0", True),
    # QC-P6-G0C 10-23 (PLAN-TOOL5 die IO: a die PHY sits on the beachfront, <= 200 um from the edge): the coll UCIe PHY
    # leaves coll_core (778 um behind the edge column) for its own edge-column partition directly W of coll_core,
    # with u_shared + u_gearbox, so the FDI clocks (lclk -> fdi_ck / fdi_rx_ck) still never cross a seam.  The seam
    # coll_core | coll_ucie carries the P/R <-> shared frames (core clock).
    # PHY at the bottom (die y 7603-8381), share/gearbox glue band above it covers the whole coll_core seam (die y
    # 8432-9245), so no share-frame pin sits beside the full-width PHY (G2 v1 1209.6-tall: 59.9k overflow M7/M5)
    "coll_ucie": ("coll_ucie", "qfd_qc_coll_ucie_part", (SUB_W, 1641.6), (0.0, 7603.2), "R0", False),
    "glue": ("glue", "qfd_qc_wglue", (SUB_W, 1209.6 + WS_DY), (0.0, 10022.4), "R0", False),
    "native59": ("native59", "qfd_native59_dv_headprep_obs1", (SUB_W, 518.4), (0.0, 11232.0 + WS_DY), "R0", False),
    "tt_ctlm": ("tt_ctlm", "qfd_tt_ctlm_dv_hp13_rp", (SUB_W, 518.4), (0.0, 11750.4 + WS_DY), "R0", False),
}
COLL_FACE_WH = (518.4, 388.8)
COLL_FACE_CELLS = 116000
COLL_FIDX = {"p": 0, "r": 1, "s0": 2, "s1": 3, "s2": 4}
COLL_FW = {"p": 546, "r": 514, "s0": 546, "s1": 546, "s2": 546}     # face record width W (RTL localparam)
# face core -> (segment, origin in the segment frame)
# QC 10-24 (dec. 12, 405-um internal reach): s1 core 2.16 um up so its N-face rec windows are <= 405 um from it
COLL_CORES = {"s1": ("coll_s", (8.64, 10.8)), "s2": ("coll_s", (267.84, 406.08)),
              # QC-P6-G0C: R moves down beside P (the UCIe PHY left coll_core): both share-frame cores sit on the
              # coll_core | coll_ucie seam (W face y 0-812), R3-INTERNAL <= 750 um without stations
              "p": ("coll_core", (8.64, 8.64)), "r": ("coll_core", (8.64, 406.08)),
              "s0": ("coll_n", (8.64, 388.8))}
COLL_UCIE = ("coll_ucie", (0.0, 0.0), (777.6, 777.6))  # PHY on the W die edge; share/gearbox band above it
# coll-internal glue per segment (est.; the old one-partition coll glue was 150k): collective core + land + bumps
# in coll_core (collective core, share, gearbox, ckdiv, clk_rx, bumps, codec_pl landing), record stations + face pin regs elsewhere
COLL_GLUE = {"coll_s": 15000, "coll_ft": 6000, "coll_core": 120000, "coll_ucie": 40000, "coll_ftm": 8000, "coll_ftc": 8000,
             "coll_ftn": 6000, "coll_n": 10000}
# as-built census instance -> coll segment (io_collective itself is resolved per bus by coll_seg())
COLL_INST_SEG = {i: "coll_core" for i in ("clk_rx", "ckb_core", "bump_pkg_s0", "bump_pkg_s1", "bump_die_ps",
                                           "ckdiv_coll_blk")}
COLL_INST_SEG["io_ucie"] = "coll_ucie"
WS_CELLS = {**COLL_GLUE, "glue": 120000, "native59": 60000, "tt_ctlm": 190000}
GLUE_INSTS = ("d2d_rom", "sys_face", "embed_prov", "mu_ctxrx", "mu_dhobs", "rstseq_rom", "ckb_rom",
              "rs_bump", "bump_fwd_epoch", "bump_fwd_lrst")
COLL_INSTS = ("io_collective", "clk_rx", "ckdiv_coll_blk", "bump_pkg_s0", "bump_pkg_s1", "bump_die_ps", "ckb_core")


def coll_contents(P, n, tn, census_blocks):
    """QC-FIX: contents of one coll segment (face cores at their PHYs, UCIe PHY core, collective core glue)."""
    cont = []
    for f, (seg, (ox, oy)) in COLL_CORES.items():
        if seg != n:
            continue
        cont.append({"inst": f"u_coll_face_{f}", "module": "qfd_coll_static_face", "status": "rework",
                     "outline_um": list(COLL_FACE_WH), "origin_um": [ox, oy], "obs_max": "M5",
                     "kit": f"physical/ref_tile/qfd_cb16c_{f}_fx (codex/collio-fl2-render-1023; gates FAIL, re-derived "
                            "as a plan core: GEOM-REVIEW fx fixes = abutted SRAM columns + one codec spine band)",
                     "note": f"PLANNED HARD CORE coll_face_{f} (~{COLL_FACE_CELLS // 1000}k cells est.): "
                             f"u_io_collective.u_io.g[{COLL_FIDX[f]}].u_face, collective face {f.upper()}, at its PHY"})
        P.cores.append({"partition_type": tn, "partition": n, "core": f"coll_face_{f}", "inst": f"u_coll_face_{f}",
                        "rtl_path": f"u_io_collective.u_io.g[{COLL_FIDX[f]}].u_face",
                        "module": "qfd_coll_static_face", "origin_um": [ox, oy],
                        "outline_um": list(COLL_FACE_WH), "cells_est": COLL_FACE_CELLS})
    if n == COLL_UCIE[0]:
        cont.append({"inst": "u_io_ucie", "module": "ot_qfd_ucie_x64_phy", "status": "reuse",
                     "outline_um": list(COLL_UCIE[2]), "origin_um": list(COLL_UCIE[1]),
                     "note": "planned hard core (TOPDOWN L1 amend): the coll UCIe PHY sits in coll_core with u_shared + "
                             "u_gearbox, so its forwarded FDI clocks (lclk -> fdi_ck / fdi_rx_ck) stay inside one "
                             "partition (a seam carries no clock)"})
        cont.append({"inst": "u_shared", "module": "qfd_ucie_static_share", "status": "reuse",
                     "note": "u_io_collective.u_io.u_shared (P/R frame mux onto the shared UCIe), flattened"})
        cont.append({"inst": "u_gearbox", "module": "qfd_ucie_six_five", "status": "reuse",
                     "note": "u_io_collective.u_io.g_six_five.u_gearbox (FDI clock domains), flattened"})
    if n == "coll_core":
        cont.append({"inst": "u_collective", "module": "qfd_io_collective_static", "status": "reuse",
                     "note": "u_io_collective.u_io.u_collective (collective core: record ends of all 5 faces, "
                             "slice in/out), flattened"})
        cont.append({"inst": "u_codec_pl_land", "module": "qfd_coll_codec_pl_land", "status": "new",
                     "note": "COLLIO carry-over (fl2/flx all FAIL, STEWARD-QK 06:26): landed register bank at the "
                             "codec_pl clock-domain boundary (ot_entry_6 -> ot_entry_11 cross-clock setup -50 to "
                             "-117 ps in P/S0); the crossing becomes landed + 1 cycle, scheduled statically"})
    for i, seg in COLL_INST_SEG.items():
        if seg == n and i != "io_ucie":
            cont.append({"inst": f"u_{i}", "module": census_blocks.get(i, i), "status": "reuse",
                         "note": "as-built collective-side block (die clock receiver / divider / bump cell)"})
    return cont


def build_west(P, census_blocks):
    for n, (tn, mod, wh, xy, orient, hard) in WS.items():
        cont = []
        if n == "glue":
            for i in GLUE_INSTS:
                cont.append({"inst": f"u_{i}", "module": census_blocks.get(i, i), "status": "reuse",
                             "note": "small W-strip block, merged into the glue partition (one clock/reset region)"})
        elif n in COLL_PARTS or n == "coll_ucie":
            cont = coll_contents(P, n, tn, census_blocks) if tn not in P.types else []
        elif n == "tt_ctlm":
            cont.append({"inst": "u_tt_ctlm", "module": "qfd_hp13_cpub39_rp_alt", "status": "rework",
                         "outline_um": [501.0, 514.0], "kit": "claude/qtile-r-1023 qfd_hp13_cpub39_rp_{main,alt}",
                         "note": "HP13 ctlm re-pack: two regional clock roots per COORD ruling (rp5 CTS ck_hr FAIL)"})
        else:
            cont.append({"inst": f"u_{n}", "module": mod, "status": "reuse",
                         "note": "hard IP used as-is (die-edge PHY)" if hard else "reuse candidate"})
        note = f"west strip: {n}"
        if n in COLL_PARTS:
            note = (f"west strip: io_collective segment {tn} (QC-FIX: coll split along y into {len(COLL_SEGS)} "
                    "abutted segments <= 1209.6 um, one tap + reset sync each; face cores at their PHYs; "
                    "face<->core records = plan lanes with stations). Carry-over: E/W seam pins M6 only (flx R M4 "
                    "hotspot on the PHY side); codec_pl landing in coll_c")
        if tn not in P.types:
            P.add_type(tn, wh, mod if hard else f"qfd_qc_{tn}_part", cont, hard=hard,
                       note=note, cells=0 if hard else WS_CELLS.get(tn, 50000))
        P.add_part(n, tn, *xy, orient)


def coll_seg(other, bus):
    """the coll segment holding io_collective's end of an as-built census row (by counterpart)."""
    if other == "io_serdes":
        return "coll_n"
    if other in ("io_serdes_1", "io_serdes_2"):
        return "coll_s"
    if other == "io_ucie" or bus == "shared_fault":
        return "coll_ucie"          # u_shared / u_gearbox moved with the PHY (shared_fault is u_shared's)
    return "coll_core"


def census_links(P, geo, census, fp_pins, face_map):
    cname = geo["col_name"]
    col_of = {f"dvs_{n}": k for k, n in enumerate(cname)}
    face_reg = {"w": {"W": "fw", "E": "fe"}, "e": {"W": "fe", "E": "fw"}}
    brect = {b["inst"]: (b["x"], b["y"], b["w"], b["h"]) for b in census["blocks"]}
    l9_flip = collections.Counter()
    kit_part = {}

    def part_of(inst, bus, pt=None, other=None):
        if inst in col_of:
            # slice: the census pin's PHYSICAL face picks the face partition (W edge = fw, E edge = fw's neighbour fe;
            # every slice has the same layout, SL_CELLS_E).  The kit face (die bus -> core port via the face wrapper
            # -> fp pins) agrees for every bus except the l9 pair word on E slices (paired toward the die centre:
            # E1 -> E0 leaves W, W1 -> W0 leaves E); counted in plan_notes census_coverage.l9_face_flip_bits.
            k = col_of[inst]
            side = "w" if k < 6 else "e"
            x, y, w, h = brect[inst]
            f = "W" if abs(pt[0] - x) < 1.0 else ("E" if abs(pt[0] - x - w) < 1.0 else None)
            if f is None:
                return None
            fk = fp_pins[side].get(face_map[side].get(bus, bus))
            if fk in face_reg[side] and face_reg[side][fk] != {"W": "fw", "E": "fe"}[f]:
                l9_flip[(inst, bus)] += 1
                # R7 (BINDER2 10-23): the core port lives in the KIT face partition (u_fup in fe), so the lane starts
                # / ends there and crosses its own slice to the physical face; landing on fw alone left 3 x 513 b
                # UNPLANNED (fe->fw).
                kit_part[(inst, bus)] = (k, sl(geo, k, face_reg[side][fk]))
            return sl(geo, k, {"W": "fw", "E": "fe"}[f])
        if inst in GLUE_INSTS:
            return "glue"
        if inst == "io_collective":
            return coll_seg(other, bus)
        if inst in COLL_INST_SEG:
            return COLL_INST_SEG[inst]
        if inst in WS:
            return inst
        return None
    seen = set()
    dropped = collections.Counter()
    cov = P.cov
    for g in census["groups"]:
        if g["src"].startswith("c16") or g["dst"].startswith("c16"):
            cov["c16"].append(g)                  # CB groups: checked against the plan CB/slice links (coverage())
            continue
        fs, fd = g["src"].startswith("flt_"), g["dst"].startswith("flt_")
        if g["kind"] == "reset" or g["src"].startswith("rstseq"):
            cov["replaced_reset"].append(g)       # per-partition 2-stage reset sync on the die async net
            continue
        if g["src"] == "clk_rx":
            cov["replaced_clock"].append(g)       # die clock spine + per-partition tap
            continue
        if fs or fd:
            cov["fault_tree"].append(g)           # as-built flt_root/hop chain -> the plan 1-bit OR tree
            continue
        s = part_of(g["src"], g["src_bus"], g["src_pt"], g["dst"])
        d = part_of(g["dst"], g["dst_bus"], g["dst_pt"], g["src"])
        if s is None or d is None:
            dropped[(g["src"].split("_")[0], g["dst"].split("_")[0], g["kind"])] += g["bits"]
            cov["dropped"].append(g)
            continue
        if s == d:
            cov["internal"].append(g)
            continue
        cov["planned"].append(g)
        key = (s, g["src"], g["src_bus"], d, g["dst"], g["dst_bus"])
        if key in seen:
            continue
        seen.add(key)
        loc = lambda p, i, b: b if p.startswith("sl_") or (p in WS and p != "glue" and p not in COLL_PARTS) \
            else f"{i}__{b}"  # noqa: E731
        sb, db = loc(s, g["src"], g["src_bus"]), loc(d, g["dst"], g["dst_bus"])
        path = ws_path(P, s, d)
        if (g["src"], g["src_bus"]) in kit_part:
            k, kp = kit_part[(g["src"], g["src_bus"])]
            if kp != s:
                path = route(P, kp, s, geo, k, g["bits"]) + path[1:]
                s = kp
        if (g["dst"], g["dst_bus"]) in kit_part:
            k, kp = kit_part[(g["dst"], g["dst_bus"])]
            if kp != d:
                path = path[:-1] + route(P, d, kp, geo, k, g["bits"])
                d = kp
        role = re.sub(r"[^A-Za-z0-9]", "_", f"{g['src_bus']}_{g['dst_bus']}")
        kind = "clock" if g["src_bus"] == "lclk" else (g["kind"] if g["kind"] in ("data", "ctl") else "ctl")
        P.link(role, path, sb, db, g["bits"], kind=kind,
               src_leaf=f"u_{g['src'] if not s.startswith('sl_') else 'f'}.{g['src_bus']}",
               dst_leaf=f"u_{g['dst'] if not d.startswith('sl_') else 'f'}.{g['dst_bus']}")
    P.l9_flip = sorted({b for (_, b) in l9_flip})
    cnt = collections.Counter((lk["path"][0], lk["src_bus"]) for lk in P.links)
    for lk in P.links:
        if cnt[(lk["path"][0], lk["src_bus"])] > 1:
            lk["src_bus"] = f"{lk['src_bus']}__to_{lk['path'][-1]}__{lk['dst_bus']}"
    cnt = collections.Counter((lk["path"][-1], lk["dst_bus"]) for lk in P.links)
    for lk in P.links:
        if cnt[(lk["path"][-1], lk["dst_bus"])] > 1:
            lk["dst_bus"] = f"{lk['dst_bus']}__from_{lk['path'][0]}"
    return dropped


# QC-P5-TIE 10-23 (BINDER2 15:19 TIED treq_i 108 b): the slice table-ROM loader request treq {valid, stage 6, user 2}
# (qfd_dv_s8_flat u_fdn.treq_i -> u_stm tload; u_fup.treq_o forwards it) has a REAL producer: the HP13 tt_ctlm leaf
# (corepub39 cpub39_1) port table_req[8:0] = the CALR g_calr.treq_q register.  The r56 die leaves table_req open and the
# release slice had no treq port, so the s8 substitution left every slice's treq_i open.  Contract (QDIE5-TLD 4b5a2975f,
# QW-TLPROD CONSUMER_GAP): table_req rides BESIDE cmd on every hop -- tt_ctlm -> W5, W5 -> .. -> W0, the W0 | E0 seam,
# E0 -> .. -> E5 -- on a lane twinned with the cmd lane of that hop (same path, same stations, same latency), so the
# per-hop treq lane latency equals the cmd lane latency (the bound slice itself forwards treq one edge ahead of cmd:
# s8 u_fup registers cmd_o (SETID) but passes treq_c through; that is as-built slice RTL, published per hop in
# qwen_compute_latency.json for the compiler).
TREQ_BUS = {"cmd": "table_req", "cmd_wi": "treq_wi", "cmd_eo": "treq_eo", "cmd_ei": "treq_ei", "cmd_wo": "treq_wo"}


def treq_links(P, geo, census, fp_pins, face_map):
    tw = []
    for g in census["groups"]:
        if g["src_bus"] in TREQ_BUS and g["dst_bus"] in TREQ_BUS and g["dst"].startswith("dvs_") and \
                (g["src"].startswith("dvs_") or (g["src"], g["src_bus"]) == ("tt_ctlm", "cmd")):
            t = dict(g, src_bus=TREQ_BUS[g["src_bus"]], dst_bus=TREQ_BUS[g["dst_bus"]], bits=9, relays=[],
                     twin_of=f"{g['src']}.{g['src_bus']} -> {g['dst']}.{g['dst_bus']}")
            tw.append(t)
    assert len(tw) == 12, [x["twin_of"] for x in tw]
    cov, P.cov = P.cov, collections.defaultdict(list)
    n0 = len(P.links)
    dropped = census_links(P, geo, {"groups": tw, "blocks": census["blocks"]}, fp_pins, face_map)
    assert not dropped and len(P.cov["planned"]) == 12, (dropped, len(P.cov["planned"]))
    P.cov = cov
    new = P.links[n0:]
    assert len(new) == 12, len(new)
    for lk, g in zip(new, tw):
        if lk["path"][0] == "tt_ctlm":
            lk["src_leaf"] = "u_tt_ctlm.table_req"
    P.treq = [{"lane_role": lk["role"], "path": lk["path"], "bits": lk["width"], "twin_of": g["twin_of"]}
              for lk, g in zip(new, tw)]
    return P.treq


VARIANT = "A"
S2_CB = {"A": ["c_W5_bf_02", "c_W5_bf_01", "c_W5_bf_00"], "B": ["c_W5_bf_01", "c_W5_bf_00"]}


def clone_s2_types(P):
    """the W5 far-bottom column-0 units carry the S2 <-> coll ft slots: own types (only there)."""
    for n in S2_CB[VARIANT]:
        tn = P.parts[n]["type"]
        new = f"{tn}_s2"
        if new not in P.types:
            P.types[new] = json.loads(json.dumps(P.types[tn]))
            P.types[new]["note"] += "; W5 far-bottom: carries the serdes S2 <-> coll ft slots"
            P.cells[new] = P.cells.get(tn)
        P.parts[n]["type"] = new


def coverage(P, census):
    """census coverage (GEOM-REVIEW2 06:26 FAIL, COORD 06:4x): every as-built bit is a planned port/lane, internal to one
    partition, or replaced by plan structure (reset sync, clock spine, fault OR tree).  CB groups (c16_*) are matched
    to the plan CB / slice links by role: bco_k -> bc_k = bcf{k} (near -> far); cw_{n,s}{k} = cw{n,s}{k}; rs / rs_o =
    rsn / rsf (the census types the 514-b level-7 rs word as 'reset' by name; it is data, planned at RSW)."""
    roles = collections.Counter()
    width = collections.defaultdict(int)
    for lk in P.links:
        roles[lk["role"]] += 1
        width[lk["role"]] = max(width[lk["role"]], lk["width"])
    out = collections.Counter()
    bad = []
    need = collections.Counter()
    for g in P.cov["c16"]:
        sb, db = g["src_bus"], g["dst_bus"]
        if g["src"].startswith("rstseq") or sb.startswith("rso"):
            out["replaced_reset"] += g["bits"]
            continue
        m = re.match(r"^bco(\d)$", sb)
        mc = re.match(r"^cw_([ns])(\d)$", sb)
        if m:
            role = f"bcf{m.group(1)}"
        elif mc:
            role = f"cw{mc.group(1)}{mc.group(2)}"
        elif sb in ("rs", "rs_o"):
            role = "rsn" if (sb == "rs" and g["dst"].startswith("dvs")) else "rsf"
        else:
            role = None
        if role is None or roles[role] == 0 or width[role] < g["bits"]:
            bad.append((g["src"], sb, g["dst"], db, g["bits"]))
            out["dropped"] += g["bits"]
            continue
        need[role] += 1
        out["planned_cb"] += g["bits"]
    for role, n in need.items():
        if role != "rsf" and roles[role] < n:
            bad.append((role, f"{roles[role]} plan links < {n} census groups"))
    for k in ("planned", "internal", "replaced_reset", "replaced_clock", "fault_tree", "dropped"):
        out[k] += sum(g["bits"] for g in P.cov.get(k, []))
    # every fault source outside the chain reaches a plan fault lane from its partition
    fsrc = sorted({g["src"] for g in P.cov.get("fault_tree", []) if not g["src"].startswith("flt_")})
    lane_from = {lk["path"][0] for lk in P.links if lk["role"].startswith("flt")}
    owner = {i: "coll_core" for i in COLL_INSTS}
    owner.update({i: "glue" for i in GLUE_INSTS})
    unplanned = [i for i in fsrc if owner.get(i, i) not in lane_from and owner.get(i, i) != "glue"]
    total = sum(g["bits"] for g in census["groups"])
    rep = {"census_bits": total, **{k: out[k] for k in sorted(out)},
           "accounted": sum(out.values()), "unaccounted": total - sum(out.values()),
           "fault_sources": fsrc, "fault_sources_without_plan_lane": unplanned,
           "l9_face_flip_buses": getattr(P, "l9_flip", []), "cb_mismatches": bad[:20]}
    return rep


def ws_path(P, s, d):
    """W-strip / W5-slice paths (fixed by the strip order); abutting pairs go direct, else one coll segment between,
    else along the coll stack."""
    S2 = ["io_serdes_2"] + S2_CB[VARIANT] + ["coll_s"]
    table = {("io_serdes_2", "coll_s"): S2,
             ("glue", "tt_ctlm"): ["glue", "native59", "tt_ctlm"]}
    for (a, b), p in table.items():
        if (s, d) == (a, b):
            return list(p)
        if (s, d) == (b, a):
            return list(reversed(p))
    if shared_face(P, s, d, quiet=True):
        return [s, d]
    if COLL_UCIE[0] in (s, d):      # coll_ucie reaches the strip through coll_core (its only logic neighbour)
        if s == COLL_UCIE[0]:
            return [s] + ws_path(P, "coll_core", d)
        return ws_path(P, s, "coll_core") + [d]
    for m in COLL_PARTS:
        if shared_face(P, s, m, quiet=True) and shared_face(P, m, d, quiet=True):
            return [s, m, d]
    ends = [x for x in (s, d) if x in COLL_PARTS]
    if len(ends) == 2:
        return coll_stack(s, d)
    for x in (s, d):
        if x in COLL_PARTS:
            y = d if x == s else s
            for m in COLL_PARTS:
                if shared_face(P, m, y, quiet=True):
                    p = coll_stack(x, m) + [y]
                    return p if x == s else list(reversed(p))
    raise SystemExit(f"ws_path: no W-strip path {s} -> {d}")


def coll_stack(a, b):
    i, j = COLL_PARTS.index(a), COLL_PARTS.index(b)
    return COLL_PARTS[i:j + 1] if i <= j else list(reversed(COLL_PARTS[j:i + 1]))


def coll_internal_links(P):
    """QC-FIX: io_collective internals that now cross segments (rtl/physical/ot_qfd_collective_static_io.sv):
    collective core (coll_c) <-> each face: tx {td,tv,ts,ps} = W+3, rx {frd,frv} = W+1 (the as-built RU/RS2 paid
    relay rows become the plan's stations); R face <-> u_shared (coll_core, internal): phy_tx frame PW=565 + valid + tx/rx slot
    (568) and the shared rx frame 565 + valid (566).  Faces in coll_c itself would be internal (none)."""
    rows = []
    for f, (seg, _) in COLL_CORES.items():
        W = COLL_FW[f]
        rows.append((f"crec_tx_{f}", "coll_core", seg, W + 3, f"rec_tx_{f}", f"rec_tx_{f}_i",
                     f"u_collective.{f}_tx_rec", f"u_coll_face_{f}.tx_data"))
        rows.append((f"crec_rx_{f}", seg, "coll_core", W + 1, f"rec_rx_{f}", f"rec_rx_{f}_i",
                     f"u_coll_face_{f}.rx_data", f"u_collective.{f}_rx_rec"))
    us = COLL_UCIE[0]
    rows.append(("cshr_rtx", "coll_core", us, 565 + 3, "shr_r_tx", "shr_r_tx_i", "u_coll_face_r.phy_tx",
                 "u_shared.r_frame"))
    rows.append(("cshr_rrx", us, "coll_core", 565 + 1, "shr_r_rx", "shr_r_rx_i", "u_shared.rx_frames",
                 "u_coll_face_r.phy_rx"))
    rows.append(("cshr_ptx", "coll_core", us, 600, "shr_p_tx", "shr_p_tx_i", "u_coll_face_p.phy_tx",
                 "u_shared.p_frame"))
    rows.append(("cshr_prx", us, "coll_core", 598, "shr_p_rx", "shr_p_rx_i", "u_shared.rx_frames",
                 "u_coll_face_p.phy_rx"))
    for role, a, b, w, sb, db, sl_, dl in rows:
        if a == b:
            P.internal_bits[role] += w
            continue
        path = [a, b] if us in (a, b) else coll_stack(a, b)
        P.link(role, path, sb, db, w, kind="data", src_leaf=sl_, dst_leaf=dl)
    return rows


# ====================================================================== fault tree
def fault_links(P, variant, geo):
    """1-bit registered OR tree, re-derived from the plan (replaces the as-built flt_root/hop chains)."""
    if variant == "A":
        units = ([(c, 3) for c in range(4)] + [(c, 2) for c in (3, 2, 1, 0)] + [(c, 1) for c in range(4)] +
                 [(c, 0) for c in (3, 2, 1, 0)])
    else:
        units = [(0, 1), (1, 1), (1, 0), (0, 0)]
    byk = collections.defaultdict(dict)
    for cl in geo["clusters"]:
        byk[cl["col"]][(cl["half"], cl["kind"])] = cl["name"]
    for k in range(NCOL):
        side = "w" if k < 6 else "e"
        for half, fs in (("t", "n"), ("b", "s")):
            near, far = byk[k][(half, "near")], byk[k][(half, "far")]
            chain = [f"{far}_{u[0]}{u[1]}" for u in units] + [f"{near}_{u[0]}{u[1]}" for u in units]
            for a, b in zip(chain, chain[1:]):
                P.link("flt", [a, b], "flt_o", "flt_i", 1, kind="ctl", src_leaf="u_pstn.flt_o",
                       dst_leaf="u_pstn.flt_i")
            entry = sl(geo, k, "hc0" if fs == "n" else [reg for reg, cc in slice_cells(side).items()
                                                         if (0, 0) in (cc if isinstance(cc, list) else [cc])][0])
            P.link("flt", [chain[-1], entry], "flt_o", f"flt_{fs}_i", 1, kind="ctl", src_leaf="u_pstn.flt_o",
                   dst_leaf="u_pstn.flt_cl")
        # slice: BFS tree to the W-flowing face partition (fw on W slices, fe on E slices)
        root = sl(geo, k, "fw")                          # fw is the W-edge partition of every slice
        names = [n for n in P.parts if n.startswith(f"sl_{geo['col_name'][k]}_")]
        seen, q = {root}, [root]
        while q:
            n = q.pop(0)
            for m in sorted(names, key=lambda m: (P.centre(m)[1], P.centre(m)[0])):
                if m not in seen and shared_face(P, n, m, quiet=True):
                    seen.add(m)
                    q.append(m)
                    P.link("flt", [m, n], "flt_o", f"flt_{m.split('_', 2)[2]}_i", 1, kind="ctl",
                           src_leaf="u_pstn.flt_o", dst_leaf="u_pstn.flt_i")
        # slice -> W neighbour (E -> W chain: its E-face partition is fe on W slices, fw on E slices); W5 -> coll
        if k > 0:
            dst = sl(geo, k - 1, "fe")
            P.link("flte", [root, dst], "flt_wo", "flt_e_i", 1, kind="ctl", src_leaf="u_pstn.flt_o",
                   dst_leaf="u_pstn.flt_e")
        else:
            P.link("flte", [root, "coll_f4", "coll_f3", "coll_core"], "flt_wo", "sl_flt_i", 1, kind="ctl",
                   src_leaf="u_pstn.flt_o", dst_leaf="u_collective.fault_sl")
    # QC-FIX: coll segments chain their face faults (transport cdc/abort/cause OR) to coll_core: S side through the ft
    # segments into coll_core; S0 -> f5 -> f4 -> f3 -> coll_core (ORed there with the share/gearbox faults)
    P.link("fltk", ["coll_s", "coll_f0", "coll_f1", "coll_f2", "coll_core"], "flt_o", "flt_s_i", 1,
           kind="ctl", src_leaf="u_pstn.flt_o", dst_leaf="u_pstn.flt_s_i")
    P.link("fltk", ["coll_n", "coll_f5", "coll_f4", "coll_f3", "coll_core"], "flt_o", "flt_n_i", 1, kind="ctl",
           src_leaf="u_pstn.flt_o", dst_leaf="u_pstn.flt_n_i")
    # P6 bound census: UCIe rx_valid[1:0] and tx_up need three status bits besides the fault bit.
    P.link("fltu", [COLL_UCIE[0], "coll_core"], "flt_o", "flt_u_i", 4, kind="ctl",
           src_leaf="u_pstn.flt_o", dst_leaf="u_collective.fault_ucie")
    P.link("fltc", ws_path(P, "coll_core", "glue"), "flt_o", "coll_flt_i", 1, kind="ctl",
           src_leaf="u_collective.fault_or", dst_leaf="u_sys_face.obs_fault_coll")
    # native59.fault already has the census-derived native59__fault_native_fault lane below.
    # A second fltn lane gives kit-rtl a duplicate source pin tied to zero (face_guard shared FAIL).
    P.link("fltt", ["tt_ctlm", "native59", "glue"], "flt_o", "ctlm_flt_i", 1, kind="ctl",
           src_leaf="u_tt_ctlm.cf", dst_leaf="u_sys_face.obs_fault_ctlm")
    # QC-P4 10-23 (BINDER2 per-bit UNPLANNED list on 16437c592, 85 b): the as-built carries the coll face fault
    # VECTORS bit by bit (fault_cause/cdc_fault/epoch_abort/fault_code -> sys_face.obs_fault; side-face cdc/abort/
    # rx_valid -> coll_core reduce-ORs and sr*_valid) where the 1-b flt lanes above carry only the OR, plus the two
    # MU fault bits glue -> tt_ctlm and the KV PHY reset glue -> ucie_kv.  Planned as static ctl lanes at the as-built
    # widths: S chain 9 (to coll_core) + 26 (forwarded to glue), N chain 4 + 13, coll_core -> glue 30 + 26 + 13.
    # P6 bound census includes g_face[4].fault_cause[7] in sys_face.obs_fault.
    P.link("fltv", ["coll_s", "coll_f0", "coll_f1", "coll_f2", "coll_core"], "fltv_o", "fltv_s_i", 36, kind="ctl",
           src_leaf="u_io.g_face.u_face.fault_cause", dst_leaf="u_sys_face.obs_fault")
    P.link("fltv", ["coll_n", "coll_f5", "coll_f4", "coll_f3", "coll_core"], "fltv_o", "fltv_n_i", 17, kind="ctl",
           src_leaf="u_io.g_face.u_face.fault_cause", dst_leaf="u_sys_face.obs_fault")
    P.link("fltvc", ws_path(P, "coll_core", "glue"), "fltv_o", "coll_fltv_i", 70, kind="ctl",
           src_leaf="u_io.g_face.u_face.fault_cause", dst_leaf="u_sys_face.obs_fault")
    P.link("mufl", ws_path(P, "glue", "tt_ctlm"), "mu_flt_o", "mu_flt_i", 2, kind="ctl",
           src_leaf="mu_ctxrx.mu_fault", dst_leaf="core.mu_fault")
    P.link("kvrst", ["glue", "ucie_kv"], "kv_phy_rst_o", "phy_rst_i", 1, kind="ctl",
           src_leaf="d2d_rom.phy_rst_n", dst_leaf="core.rst_n")


def drop_unloaded_lanes(P, path):
    """COORD 10-25 03:45 ruling (2): the plan carries the as-built loads only.  Lanes the fixed-source bind found with
    no as-built crossing bit (inputs/unloaded_lanes.json: 253 template fault-OR hops on CB/slice partitions whose
    as-built cells have no fault source there, 17 slice x_* template forwards, the duplicate shared-fault lane) are
    removed before materialize, so they take no ports, pins, stations or tracks.  As-built fault reducers keep their
    carried lanes; nothing is tied off (bind proof unbound/tied 0 is re-checked after the rebind)."""
    if not Path(path).exists():
        return dict(dropped=[], absent=[])
    want = set(json.loads(Path(path).read_text())["lanes"])

    def ids(links):
        n = collections.Counter()
        out = []
        for lk in links:
            base = f"{lk['path'][0]}__{lk['role']}"
            n[base] += 1
            out.append(base if n[base] == 1 else f"{base}_{n[base]}")
        return out
    before = ids(P.links)
    keep = [lk for lk, i in zip(P.links, before) if i not in want]
    kept_ids = [i for i in before if i not in want]
    if ids(keep) != kept_ids:
        raise SystemExit("drop_unloaded_lanes: dropping would rename surviving lanes: "
                         + str([(a, b) for a, b in zip(kept_ids, ids(keep)) if a != b][:5]))
    pairs = collections.defaultdict(list)
    for lk, i in zip(P.links, before):
        if i in want:
            pairs[(lk["path"][0], lk["path"][-1])].append(i)
            for x, y in zip(lk["path"], lk["path"][1:]):
                P.load[tuple(sorted((x, y)))] -= lk["width"]
    P.links = keep
    P.unloaded_pairs = dict(pairs)
    return dict(dropped=sorted(set(before) & want), absent=sorted(want - set(before)))


def unloaded_census_filter(P, rows, parts, tag):
    """census reconciliation for the dropped unloaded lanes (QC 10-25): a census row is removed only when BOTH
    (a) every plan lane between its two partitions was dropped by drop_unloaded_lanes, and (b) the fixed-source bind
    (inputs/bind_carried_pairs.json, bind_latency.json buses[]) has 0 bound crossing bits between those partitions.
    The template census rows ([1] slice record x 12, [2] io_collective) assume the base slice/collective RTL; the bound
    slice variants (qfd_dv_s8_ce_e5 / _l9h ...) and the single shared-fault source do not carry those bits.  Any other
    row stays and still fails the census if unplanned.  Returns (kept rows, removed records with evidence)."""
    ev = json.loads((Path(__file__).parent / "inputs" / "bind_carried_pairs.json").read_text())
    carried = {(s_, d_) for s_, d_, _w in ev["pairs"]}
    up = getattr(P, "unloaded_pairs", {})
    planned = {(lk["path"][0], lk["path"][-1]) for lk in P.links}
    kept, removed = [], []
    for r in rows:
        pr = (parts.get(r["src"]), parts.get(r["dst"]))
        if pr in up and pr not in carried and pr not in planned:
            removed.append(dict(r, census=tag, pair=list(pr), dropped_lanes=up[pr],
                                evidence="bind_carried_pairs.json: 0 bound bits " + ev["source"]["bind_latency.json_sha256"][:12]))
        else:
            kept.append(r)
    return kept, removed


# ====================================================================== ports / slots / windows
def to_type_geom(P, part, die_face, win, order):
    p = P.parts[part]
    w, h = p["wh"]
    o = p["orient"]
    tf = P.tface(part, die_face)
    if die_face in "EW":
        base, ext, flip = p["origin"][1], h, o in ("MX", "R180")
    else:
        base, ext, flip = p["origin"][0], w, o in ("MY", "R180")
    a, b = win[0] - base, win[1] - base
    if flip:
        a, b = ext - b, ext - a
        order = "lsb_high" if order == "lsb_low" else "lsb_low"
    return tf, [round(a, 4), round(b, 4)], order


def quad_segments(P, ll, f, flip, ref_lo, ref_hi, prs):
    """variant B: a CB quad's face is cut at its A0 cell boundaries and every cell-suffixed bus ({c}{r}) is laid in
    its own cell's segment, so one quad type has the same pins whether it faces a quad or two slice partitions."""
    m = re.match(r"^c_[WE]\d_[tb][fn]_(\d)(\d)$", ll)
    if VARIANT != "B" or not m:
        return [((ref_lo, ref_hi), prs)]
    qc, qr = int(m.group(1)), int(m.group(2))
    sizes = [CW[2 * qc], CW[2 * qc + 1]] if f in "NS" else [RH[2 * qr], RH[2 * qr + 1]]
    bounds = []
    for j in range(2):
        a0 = sum(sizes[:j])
        a1 = a0 + sizes[j]
        bounds.append((ref_lo + a0, ref_lo + a1) if not flip else (ref_hi - a1, ref_hi - a0))
    groups = [[], []]
    for pr in prs:
        # QC-P6-G0C 10-23 (G0C core_faces + R3-INTERNAL): an A0 core bus (y_o/t_o/na_i/nb_i<c><r>) on EITHER side picks
        # the segment, the SOURCE core first (its out pins), so a slot bus name on the reference side (a22_i) no
        # longer drops the window into segment 0.  The window is then packed from the type-frame end nearest that
        # core's data pins (A0 data pins: W edge in R0, E edge in MY = odd columns; upper part of the core).
        cm = [re.match(r"^(y_o|t_o|na_i|nb_i)(\d)(\d)$", pr[s_]["bus"]) for s_ in ("src", "dst")]
        cm = [m_ for m_ in cm if m_]
        bus = pr["src"]["bus"] if pr["src"]["part"] == ll else pr["dst"]["bus"]
        mm = cm[0] if cm else re.search(r"(\d)(\d)$", bus)
        j = 0
        hi = False
        if mm:
            c_, r_ = int(mm.group(len(mm.groups()) - 1)), int(mm.group(len(mm.groups())))
            j = (c_ if f in "NS" else r_) % 2
            if cm:
                hi = (c_ % 2 == 1) if f in "NS" else True
        pr["_pack_hi"] = hi
        groups[j].append(pr)
    return [(bounds[j], groups[j]) for j in range(2) if groups[j]]


# QC-P3 10-23 (GEOM-REVIEW4 coll_ftc FAIL): the single-instance coll feedthrough segments (no logic) get their W/S
# windows re-laid at the partner window of the same slot (straight slots run straight, turns sit at the corner), and
# their E faces ordered S-turns low / W-bound by neighbour / N-turns high.  Processed top-down (f5, f4, f3) so each
# segment's N face (the upper segment's re-laid S face) is the anchor.  E/W faces of these segments use M6+M4.
FT_COLL = ("coll_f5", "coll_f4", "coll_f3")


def _lay_targeted(P, a, b, prs, targets, slack=1.06):
    """lay the windows of face pair (a, b) in ascending target order, each as close to its target as the rest
    allows (greedy legaliser, same qlen/GAP/EDGE/density ladder as the default packing).  R0 frames only."""
    f, lo, hi = shared_face(P, a, b)
    ll = a if P.parts[a]["orient"] == "R0" else b
    assert P.parts[a]["orient"] == "R0" and P.parts[b]["orient"] == "R0", (a, b)
    x0, y0, x1, y1 = P.rect(ll)
    fl = f if ll == a else OPP[f]
    slo = max(y0 if fl in "EW" else x0, lo) + EDGE
    shi = min(y1 if fl in "EW" else x1, hi) - EDGE
    order = sorted(prs, key=lambda pr: targets[pr["id"]])
    for fm in [5.0, 5.5, 5.8, None]:
        lens = [qlen(pr["width"] + 1, PIN_MAX, pr["layers"], max(slo, targets[pr["id"]][0]), False, fmax=fm)
                for pr in order]
        need = slack * sum(lens) + GAP * (len(lens) - 1)
        if need > shi - slo + 1e-6:
            continue
        cur, wins, ok = slo, [], True
        for i, pr in enumerate(order):
            rest = slack * sum(lens[i + 1:]) + GAP * (len(lens) - 1 - i)   # slack: L grows near PG bands
            st = min(max(cur, targets[pr["id"]][0] - lens[i] / 2), shi - lens[i] - rest)
            L = qlen(pr["width"] + 1, PIN_MAX, pr["layers"], st, False, fmax=fm)
            if st + L > shi - (sum(lens[i + 1:]) + GAP * (len(lens) - 1 - i)) + 1e-6:
                ok = False
                break
            wins.append((pr, [round(st, 4), round(st + L, 4)]))
            cur = st + L + GAP
        if ok:
            for pr, w in wins:
                pr["window_um"] = w
                pr.pop("order", None)
            return True
    if slack > 1.0:
        return _lay_targeted(P, a, b, prs, targets, 1.0)
    if any(t[0] > -1e8 for t in targets.values()):
        # positions do not fit (PG-band / track quantisation at the targets): keep the target ORDER, pack densely
        print(f"align_coll_ft: face {a}/{b}: targeted fit failed, packing in target order", file=sys.stderr)
        return _lay_targeted(P, a, b, prs, {pr["id"]: (-1e9 + i, 0) for i, pr in enumerate(order)})
    raise SystemExit(f"align_coll_ft: face {a}/{b} cannot fit the windows in target order")


def align_coll_ft(P, facepairs, lanes, ports):
    pmap = {pr["id"]: pr for pr in ports}
    partner = {}
    for ln in lanes:
        ids = ln["ports"]
        for i in range(len(ids) - 1):
            partner[(ids[i], pmap[ids[i]]["dst"]["part"])] = ids[i + 1]
            partner[(ids[i + 1], pmap[ids[i + 1]]["src"]["part"])] = ids[i]

    def face_of(pr, x):           # the face of partition x that port pr crosses
        return pr["face"] if pr["src"]["part"] == x else OPP[pr["face"]]

    def point(pr, x):             # die point of port pr's window centre on partition x's face
        X0, Y0, X1, Y1 = P.rect(x)
        c = sum(pr["window_um"]) / 2
        return {"E": (X1, c), "W": (X0, c), "N": (c, Y1), "S": (c, Y0)}[face_of(pr, x)]

    for x in FT_COLL:
        pairs = {k: v for k, v in facepairs.items() if x in k}
        X0, Y0, X1, Y1 = P.rect(x)
        # E face anchor: re-order (low -> high) S turns, W-bound by W-neighbour height, N turns
        for k, prs in pairs.items():
            if face_of(prs[0], x) != "E":
                continue
            def ekey(pr):
                q = pmap[partner[(pr["id"], x)]]
                pf = face_of(q, x)
                if pf == "S":
                    return (0, 0.0, pr["id"])
                if pf == "W":
                    o = q["dst"]["part"] if q["src"]["part"] == x else q["src"]["part"]
                    return (1, P.rect(o)[1], pr["id"])
                return (2, 0.0, pr["id"])
            tg = {}
            for i, pr in enumerate(sorted(prs, key=ekey)):
                tg[pr["id"]] = (-1e9 + i, 0)          # pack low -> high in this order
            _lay_targeted(P, *k, prs, tg)
        # W and S faces follow their partner windows (projected on the face axis)
        for k, prs in pairs.items():
            fx = face_of(prs[0], x)
            if fx not in "WS":
                continue
            tg = {}
            for pr in prs:
                q = pmap[partner[(pr["id"], x)]]
                px, py = point(q, x)
                t = py if fx == "W" else px
                d = (px - X0) if fx == "W" else (py - Y0)     # partner's distance from this face (nest turns)
                tg[pr["id"]] = (t, -d)
            _lay_targeted(P, *k, prs, tg)


def materialize(P):
    ports, lanes = [], []
    facepairs = collections.defaultdict(list)
    slot_req = {}
    bus_req = {}
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
                  "kind": lk["kind"], "face": f,
                  "layers": (["M6"] if ((a in COLL_PARTS or b in COLL_PARTS) and not (a in FT_COLL or b in FT_COLL))
                             else ["M6", "M4"]) if f in "EW"
                  else ["M7", "M5"]}
            ports.append(pr)
            facepairs[(a, b) if a < b else (b, a)].append(pr)
            pids.append(pid)
            if i == 0:
                k = (P.parts[a]["type"], sb)
                if k in bus_req and bus_req[k]["width"] != w:
                    raise SystemExit(f"type {k}: bus width conflict")
                bus_req.setdefault(k, dict(name=sb, dir="out", width=w, kind=lk["kind"], leaf=lk["src_leaf"]))
            if i == len(path) - 2:
                bus_req.setdefault((P.parts[b]["type"], db), dict(name=db, dir="in", width=w, kind=lk["kind"],
                                                                  leaf=lk["dst_leaf"]))
        for j in range(1, len(path) - 1):
            part = path[j]
            fin = OPP[shared_face(P, path[j - 1], part)[0]]
            fout = shared_face(P, part, path[j + 1])[0]
            k = (P.parts[part]["type"], role)
            s = dict(name=role, in_face=P.tface(part, fin), out_face=P.tface(part, fout), width=w)
            if k in slot_req and (slot_req[k]["in_face"], slot_req[k]["out_face"]) != (s["in_face"], s["out_face"]):
                raise SystemExit(f"slot {k}: faces differ between instances")
            slot_req.setdefault(k, s)
        lanes.append({"id": lid, "ports": pids, **({"param": lk["param"]} if lk.get("param") else {})})
    ninst = collections.Counter(p["type"] for p in P.parts.values())
    for (a, b), prs in facepairs.items():
        f, lo, hi = shared_face(P, a, b)
        fb = OPP[f]
        cand = [x for x, df in ((a, f), (b, fb)) if P.tface(x, df) in "NE"]
        na, nb_ = ninst[P.parts[a]["type"]], ninst[P.parts[b]["type"]]
        if na != nb_:
            ll = a if na > nb_ else b         # the more-replicated type sets the layout (one pin table)
        elif len(cand) == 1:
            ll = cand[0]
        else:
            r0 = [x for x in (a, b) if P.parts[x]["orient"] == "R0"]
            ll = r0[0] if r0 else a
        o = P.parts[ll]["orient"]
        flip = (o in ("MX", "R180") and f in "EW") or (o in ("MY", "R180") and f in "NS")
        prs.sort(key=lambda pr: pr["src"]["bus"] if pr["src"]["part"] == ll else pr["dst"]["bus"])
        dens = DENS
        dens = PIN_MAX
        # windows laid out from the reference's TYPE-frame low end, relative to its own face (shift invariant)
        x0, y0, x1, y1 = P.rect(ll)
        ref_lo = y0 if f in "EW" else x0
        ref_hi = y1 if f in "EW" else x1
        segs = quad_segments(P, ll, f, flip, ref_lo, ref_hi, prs)
        for (slo, shi), sp in segs:
            slo, shi = max(slo, lo), min(shi, hi)
            # QC-FIX (c): W-strip faces (PHYs, coll segments, glue) are laid at the lowest density that fits
            # (5.0 -> 5.5 -> 5.8 -> 6.0 pins/um), so the G0 count (track quantisation + PG push) stays <= 6/um
            ladder = [5.0, 5.5, 5.8, None] if (a in WS or b in WS) else [None]
            for fm in ladder:
                # die-frame packing: type-frame-high windows (_pack_hi) go from the die-high end when the reference
                # is unflipped, from the die-low end when flipped; the rest as before
                up = [pr for pr in sp if not (pr.get("_pack_hi", False) ^ flip)]
                dn = [pr for pr in sp if pr.get("_pack_hi", False) ^ flip]
                cur, top = slo + EDGE, shi - EDGE
                for pr in up:
                    L = qlen(pr["width"] + 1, dens, pr["layers"], cur, False, fmax=fm)
                    pr["window_um"] = [round(cur, 4), round(cur + L, 4)]
                    pr.pop("order", None)
                    cur += L + GAP
                for pr in dn:
                    L = qlen(pr["width"] + 1, dens, pr["layers"], top, True, fmax=fm)
                    pr["window_um"] = [round(top - L, 4), round(top, 4)]
                    pr["order"] = "lsb_high"
                    top -= L + GAP
                over = cur - GAP > top + GAP + 1e-6 if (up and dn) else (cur - GAP > shi - EDGE + 1e-6 or
                                                                          top + GAP < slo + EDGE - 1e-6)
                if not over:
                    break
            if over:
                raise SystemExit(f"face {a}/{b} ({f}) segment {slo:.1f}-{shi:.1f} overfull: " +
                                 ", ".join(f"{pr['id']}:{pr['width']}" for pr in sp))
        del ref_lo, ref_hi
    align_coll_ft(P, facepairs, lanes, ports)
    pmap = {pr["id"]: pr for pr in ports}
    for ln in lanes:
        for a, b in zip(ln["ports"], ln["ports"][1:]):
            pa, pb = pmap[a], pmap[b]
            part = pa["dst"]["part"]
            role = pa["dst"]["bus"][:-2]
            ka = (P.parts[part]["type"], role)
            ca, cb = port_pt(P, pa), port_pt(P, pb)
            L = abs(ca[0] - cb[0]) + abs(ca[1] - cb[1])
            # OWNER 12: route / stations <= ST_LEN (check.py R3 convention); ft_regs then checks the ROUTED hops around
            # hard cores and adds stations where a detour exceeds it
            k = max(1, math.ceil(L / ST_LEN))
            slot_req[ka]["stations"] = max(slot_req[ka].get("stations", 1), k)
    # pins on the TYPE: every out bus / slot out window in its type frame (from ANY instance, inverse transform);
    # instances of one type must agree
    tgeo = {}
    for pr in ports:
        a = pr["src"]["part"]
        tn, bus = P.parts[a]["type"], pr["src"]["bus"]
        tf, win, order = to_type_geom(P, a, pr["face"], pr["window_um"], pr.get("order", "lsb_low"))
        g = dict(face=tf, window_um=win, layers=pr["layers"], order=order)
        old = tgeo.setdefault((tn, bus), g)
        if old != g:
            raise SystemExit(f"type {tn} bus {bus}: instances disagree on the window {old} vs {g} ({pr['id']})")
    P.in_geo = {}
    for pr in ports:
        d = pr["dst"]["part"]
        tf, win, order = to_type_geom(P, d, OPP[pr["face"]], pr["window_um"], pr.get("order", "lsb_low"))
        g = dict(face=tf, window_um=win, layers=pr["layers"], order=order)
        old = P.in_geo.setdefault((P.parts[d]["type"], pr["dst"]["bus"]), g)
        if old != g:
            raise SystemExit(f"type {P.parts[d]['type']} in-bus {pr['dst']['bus']}: instances disagree {old} vs {g}")
    for pr in ports:
        for k in ("face", "window_um", "layers", "order", "_pack_hi"):
            pr.pop(k, None)
    for (tn, bn), b in bus_req.items():
        if (tn, bn) in tgeo:
            b.update(tgeo[(tn, bn)])
        elif (tn, bn) in P.in_geo:
            b.update(P.in_geo[(tn, bn)])
        P.types[tn]["buses"].append(b)
    for (tn, sn), s in slot_req.items():
        g = tgeo.get((tn, sn + "_o"))
        if g:
            s["out_window_um"] = g["window_um"]
            s["layers"] = g["layers"]
            if g["order"] != "lsb_low":
                s["order"] = g["order"]
        P.types[tn]["ft_slots"].append(s)
    stagger_coll_ft_stations(P)
    sink_anchored_taps(P)
    return ports, lanes


# QC-P6-FTC 10-23 (GEOM-REVIEW7 18:19, coll_ftc g3g: the 2x2 R4 grid taps sat 366-456 um from their sinks and the one
# centre u_rst_sync was a clock sink ~450 um from every tap -> 524.9 ps source latency, 324 ps setup skew).  The coll
# feedthrough types take the R4 grid taps PLUS sink-anchored taps as additions (QC-A0 10-24: tap_mode grid+sinks, CP1 r8
# RULING 21:26; tools/die_plan/taps.py, KV-P6-TAP: radius 250 um / cap 1,500 planned
# sinks, k-medians of face registers + ft stations); with > 1 tap gen_rtl gives every tap its own reset synchroniser,
# placed FIRM at the tap (reset_taps.tcl), so no clock or reset sink is > ~250 um from its root.
SINK_TAP_TYPES = ("coll_ftc",)


def sink_anchored_taps(P, radius=250.0, cap=1500):
    for tn in SINK_TAP_TYPES:
        if tn in P.types:
            P.types[tn]["clock"].update(tap_mode="grid+sinks", tap_radius_um=radius, tap_max_sinks=cap)


def stagger_coll_ft_stations(P, tap_keep=40.0, site_sep=24.0, step=8.64):
    """QC-P5 10-23 (coll_ftc GRT probes: 368 overflow at the partition centre on the tool's midpoint-Z / L stations;
    1,697 with stations only re-spaced along those routes, because the wires of every slot whose in->out box spans the
    centre still crossed the clock/reset tap).  Station 1 of each 2-station slot gets an explicit site (regs_um, honoured
    by face_flops.tcl) chosen so that NEITHER hop's bounding box (in pin -> site, site -> out pin) touches the
    tap keep-out (tap +/- tap_keep um): the router can then take any L/Z inside each box without crossing the tap.
    Among the legal sites (grid step um, every hop <= ST_LEN), widest slots first: >= site_sep um from the sites already
    taken, then the most balanced hops.  Station 0 stays at the in-face pin centre."""
    for tn in sorted({P.parts[p]["type"] for p in FT_COLL if p in P.parts}):
        t = P.types[tn]
        W, H = t["outline_um"]
        tap = t.get("clock", {}).get("tap_um", [W / 2, H / 2])
        kx0, kx1, ky0, ky1 = tap[0] - tap_keep, tap[0] + tap_keep, tap[1] - tap_keep, tap[1] + tap_keep
        slots = [s for s in t["ft_slots"] if int(s.get("stations", 1)) == 2 and s.get("out_window_um")]
        slots.sort(key=lambda s: -s["width"])
        taken = []

        def hits(p, q):
            return not (max(p[0], q[0]) < kx0 or min(p[0], q[0]) > kx1 or max(p[1], q[1]) < ky0 or min(p[1], q[1]) > ky1)
        for s in slots:
            gi = P.in_geo.get((tn, s["name"] + "_i"))
            if not gi:
                continue
            ci, co = sum(gi["window_um"]) / 2, sum(s["out_window_um"]) / 2
            fp = {"E": lambda c: (W, c), "W": lambda c: (0.0, c), "N": lambda c: (c, H), "S": lambda c: (c, 0.0)}
            a, b = fp[s["in_face"]](ci), fp[s["out_face"]](co)
            # QC-P6-FTC 10-23 (GEOM-REVIEW6 17:44 / 7 18:19: 240 of dr_o_dr_wi's 521 bits had an out-box spanning the
            # keep-out although the box to the window CENTRE was clear): test each hop against the whole pin window
            # (both window ends), i.e. against every bit's hop box, not the centre bit's.
            ae = [fp[s["in_face"]](c) for c in gi["window_um"]]
            be = [fp[s["out_face"]](c) for c in s["out_window_um"]]
            nx, ny = int(W / step), int(H / step)

            def search(strict):
                best = None
                for ix in range(1, nx):
                    for iy in range(1, ny):
                        x, y = ix * step, iy * step
                        h1 = abs(x - a[0]) + abs(y - a[1])
                        h2 = abs(x - b[0]) + abs(y - b[1])
                        if strict:
                            m1 = max(abs(x - p[0]) + abs(y - p[1]) for p in ae + [a])
                            m2 = max(abs(x - p[0]) + abs(y - p[1]) for p in be + [b])
                            bad = (m1 > ST_LEN or m2 > ST_LEN or any(hits(p, (x, y)) for p in ae)
                                   or any(hits((x, y), p) for p in be))
                        else:
                            bad = h1 > ST_LEN or h2 > ST_LEN or hits(a, (x, y)) or hits((x, y), b)
                        if bad:
                            continue
                        crowd = min((abs(x - u) + abs(y - v) for u, v in taken), default=1e9)
                        key = (crowd < site_sep, h1 + h2, abs(h1 - h2))
                        if best is None or key < best[0]:
                            best = (key, (round(x, 3), round(y, 3)))
                return best
            # whole-window test first; a slot with no such site keeps the centre-bit test (pre-10-23-18:19 sites)
            best = search(True) or search(False)
            if best is None:
                print(f"stagger_coll_ft_stations: {tn}.{s['name']}: no site keeps both hops off the tap; tool route kept")
                continue
            taken.append(best[1])
            s0 = (round(min(max(a[0], 1.0), W - 1.0), 3), round(min(max(a[1], 1.0), H - 1.0), 3))
            s["regs_um"] = [list(s0), list(best[1])]

# OWNER DEC. 16 + FP32 audit (COORD 10-25): PHY-edge clocks the bound coll / glue partitions take as bound-only ports
# (bind kit-rtl), declared so the kit SDC clocks them (create_clock, synchronous with clk) instead of leaving them
# unconstrained: clk_coll / clk_serdes = the collective core clock (die period), clk_d2d = the forwarded d2d clock
# (mesochronous, die period), clk_coll_blk = qfd_ckdiv6's /6 block clock (5000 ps).
EDGE_CLOCKS = {"coll_n": [("clk_coll", 1, "collective core clock"), ("clk_serdes", 1, "SerDes PHY parallel clock (die period)")],
               "coll_s": [("clk_coll", 1, "collective core clock"), ("clk_serdes", 1, "SerDes PHY parallel clock (die period)")],
               "coll_ucie": [("clk_coll", 1, "collective core clock"), ("clk_coll_blk", 6, "qfd_ckdiv6 /6 block clock")],
               "glue": [("clk_d2d", 1, "forwarded d2d clock (mesochronous)")]}


def edge_clocks(P):
    """interior pins one lattice step apart, E of the type's clock tap (never on a tap: GRT-0080)."""
    for tn, lst in EDGE_CLOCKS.items():
        t = P.types.get(tn)
        if t is None:
            continue
        x0, y0 = t["clock"]["tap_um"]
        t["clock"]["edge_clocks"] = [{"port": n, "tap_um": [round(x0 + 2 * G8 * (k + 1), 4), round(y0 + G8, 4)],
                                      "period_mult": m, "source": src} for k, (n, m, src) in enumerate(lst)]


def ft_fracs(P):
    """sparse soft partitions give more of their M4-M7 tracks to feedthroughs (G0 cut model default 0.25)."""
    for tn, t in P.types.items():
        if t.get("hard") or (tn.startswith("coll_") and not tn.startswith("coll_ft")):
            continue
        w, h = t["outline_um"]
        cells = P.cells.get(tn) or 0
        fill = cells * CELL_UM2 / UTIL / (w * h)
        if fill < 0.25:
            # METHODOLOGY 9.3 (10-24): M8/M9 carry no signals any more, so the cut capacity is the partitions' own
            # M4-M7 share; very sparse types (est. fill < 0.10) give half of it to feedthroughs
            fr = 0.5 if fill < 0.10 else 0.4
            t["ft_track_frac"] = fr
            t["note"] = (t.get("note", "") + f"; est. std-cell fill {fill:.2f} at util {UTIL}: {fr:.0%} of M4-M7 to ft").lstrip("; ")


def bind_leaves(P):
    """every bus binds to a content instance: a leaf named by the as-built record when it exists in the partition,
    else the partition's plan boundary block u_pstn (boundary registers, stations, relays, fault OR; new, flattened)."""
    for tn, t in P.types.items():
        insts = {c["inst"] for c in t["contents"]}
        need = False
        for b in t["buses"]:
            lf = b.get("leaf")
            if not lf or lf.split(".")[0] not in insts:
                b["leaf"] = f"u_pstn.{b['name']}"
                need = True
        if need and "u_pstn" not in insts:
            t["contents"].append({"inst": "u_pstn", "module": f"{tn}_pstn", "status": "new",
                                  "note": "plan boundary: pin registers, ft stations, forwarding relays, fault OR "
                                          "(generated from the plan, flattened with the glue)"})


def port_pt(P, pr):
    part = pr["src"]["part"]
    x0, y0, x1, y1 = P.rect(part)
    c = sum(pr["window_um"]) / 2
    return {"E": (x1, c), "W": (x0, c), "N": (c, y1), "S": (c, y0)}[pr["face"]]


def merge_types(P):
    """merge types identical in the type frame (outline, buses + pins, slots + pins, contents modulo inst names)."""
    def sig(t, tn):
        b = tuple(sorted(json.dumps(dict(x, _in=P.in_geo.get((tn, x["name"]))), sort_keys=True)
                         for x in t["buses"]))
        s = tuple(sorted(json.dumps(dict(x, _in=P.in_geo.get((tn, x["name"] + "_i"))), sort_keys=True)
                         for x in t["ft_slots"]))
        c = tuple(sorted(json.dumps({k: v for k, v in x.items() if k != "inst"}, sort_keys=True)
                         for x in t["contents"] if x.get("module", "").startswith(("qfd_tile", "qfd_c_xstn"))
                         or "outline_um" in x))
        return (tuple(t["outline_um"]), b, s, c, t.get("hard", False), json.dumps(t["clock"], sort_keys=True))
    groups = collections.defaultdict(list)
    for tn in sorted(P.types):
        groups[sig(P.types[tn], tn)].append(tn)
    ren = {}
    for g in groups.values():
        keep = min(g, key=lambda n: (len(n), n))
        for n in g:
            ren[n] = keep
    # canonical names for per-column slice types
    for n, k in list(ren.items()):
        pass
    for p in P.parts.values():
        p["type"] = ren[p["type"]]
    P.types = {n: t for n, t in P.types.items() if ren[n] == n}
    P.cells = {n: c for n, c in P.cells.items() if n in P.types}
    # rename slice types 'slw_fw__W3' -> 'slw_fw' when unique per (side, region), else keep column suffix
    base = collections.Counter(n.split("__")[0] for n in P.types)
    ren2 = {}
    seen = collections.Counter()
    for n in sorted(P.types):
        if "__" in n:
            b = n.split("__")[0]
            if base[b] == 1:
                ren2[n] = b
            else:
                seen[b] += 1
                ren2[n] = f"{b}_v{seen[b]}"
        else:
            ren2[n] = n
    for p in P.parts.values():
        p["type"] = ren2[p["type"]]
    P.types = {ren2[n]: t for n, t in P.types.items()}
    P.cells = {ren2[n]: c for n, c in P.cells.items()}
    return len(ren) - len(P.types)


# ====================================================================== clock taps (COORD 10-23 07:24 ruling (2))
INS_BASE, INS_PER_MM = 78.0, 224.0
GLUE_R = 940.0                         # glue region reach so ins(R) <= 289 ps (inside 250 +/- 40)     # est. CTS insertion = 78 ps + 224 ps per mm of Manhattan tap->farthest-sink
INS_NOTE = ("insertion estimate ins(R) = 78 ps + 224 ps/mm x R (R = Manhattan tap -> farthest sink of its region): a "
            "line through the PLAN-TOOL CP1 kit (one centre tap, 1.43 x 3.67 mm near-empty partition, ~650 ps at "
            "R 2.55 mm) and a ~0.1-mm leaf tree (~100 ps).  Hard cores carry their own budget below their ck pin.  "
            "To be replaced by the G3 measurement of each type.")


def ins_est(r_um):
    return round(INS_BASE + INS_PER_MM * r_um / 1000.0)


def far_from(pt, rect):
    x0, y0, x1, y1 = rect
    return max(abs(pt[0] - x) + abs(pt[1] - y) for x in (x0, x1) for y in (y0, y1))


def clock_taps(P):
    """one spine tap per planned core / landed glue region (schema clock.tap_um stays the partition H-tap root at the
    centre; the extra taps are the declared in-partition M8/M9 branch leaves)."""
    out = {}
    for tn, t in sorted(P.types.items()):
        if t.get("hard"):
            continue
        w, h = t["outline_um"]
        root = t["clock"]["tap_um"]
        taps = []
        cores = [c for c in t["contents"] if c["module"].startswith("qfd_tile_n")]
        if cores:          # CB quad: 4 A0 core taps at their ck pins (east cores MY: matched to the root)
            for c in cores:
                o = "MY" if "orient MY" in c.get("note", "") else "R0"
                ck = a0_ck(c["origin_um"], o)
                taps.append(dict(name=f"{c['inst']}.ck", kind="core", xy=ck, orient=o, insertion_ps=250,
                                 insertion_tol_ps=40, budget_owner="QC-A0 cores/a0_core.json (below the ck pin)"))
        else:
            for c in t["contents"]:
                if c.get("outline_um") and c.get("origin_um") and c["module"] in ("qfd_coll_static_face",
                                                                                  "ot_qfd_ucie_x64_phy"):
                    ox, oy = c["origin_um"]
                    cw, ch = c["outline_um"]
                    taps.append(dict(name=f"{c['inst']}.ck", kind="core",
                                     xy=[snap(ox + cw / 2), snap(oy + ch / 2)], insertion_ps=250, insertion_tol_ps=40,
                                     budget_owner="face core kit (11 internal roots below this tap)"
                                     if c["module"] == "qfd_coll_static_face" else
                                     "UCIe PHY hard IP (FDI side forwarded lclk; core-clock side at this tap)"))
        # glue: the fewest landed glue regions (nx x ny grid) whose centre tap reaches every corner within GLUE_R
        nx, ny = min(((i, j) for i in range(1, 6) for j in range(1, 6) if (w / i + h / j) / 2 <= GLUE_R),
                     key=lambda ij: (ij[0] * ij[1], ij))
        for i in range(nx):
            for j in range(ny):
                reg = (round(w * i / nx, 2), round(h * j / ny, 2), round(w * (i + 1) / nx, 2),
                       round(h * (j + 1) / ny, 2))
                g = [snap((reg[0] + reg[2]) / 2), snap((reg[1] + reg[3]) / 2)]
                R = far_from(g, reg)
                taps.append(dict(name=f"glue_{i}{j}" if nx * ny > 1 else "glue", kind="glue", xy=g,
                                 region_um=list(reg), reach_um=round(R, 1), insertion_ps=ins_est(R),
                                 insertion_tol_ps=40))
        # spacing: every tap within reach of the partition H-tap root; nearest-neighbour spacing
        for tp in taps:
            tp["from_root_um"] = round(abs(tp["xy"][0] - root[0]) + abs(tp["xy"][1] - root[1]), 1)
        nn = []
        for i, a in enumerate(taps):
            d = [abs(a["xy"][0] - b["xy"][0]) + abs(a["xy"][1] - b["xy"][1]) for j, b in enumerate(taps) if j != i]
            nn.append(min(d) if d else 0.0)
        glue_over = [tp["name"] for tp in taps if tp["kind"] == "glue" and tp["insertion_ps"] > 290]
        out[tn] = dict(root_um=root, taps=taps, max_from_root_um=max(tp["from_root_um"] for tp in taps),
                       max_nearest_tap_um=round(max(nn), 1), glue_taps_over_290ps=glue_over)
    return out


def declare_clock_taps(P, notes):
    """Promote the existing type-frame tap declarations without turning estimates into measurements."""
    fields = {"name", "xy", "kind", "orient", "insertion_ps", "insertion_tol_ps", "budget_owner", "from_root_um", "note"}
    for tn, entry in notes.items():
        P.types[tn]["clock"]["taps"] = [{k: v for k, v in tap.items() if k in fields} for tap in entry["taps"]]


# A0 hard cores (QC-A0 kits qfd_tile_n{k,l}_a0ck): built on PLATFORM tracks (ROM/node/LSL children cannot move to the
# plan phases), every boundary pin M4 at y = 0.012 mod 0.048.  COORD 10-23 08:36: the core is placed at the 8.64
# lattice origin + track_offset (0, +0.012) so its pins land on the plan M4 tracks (offset 0.024); MY (east cores)
# keeps y; partition MX is checked by G0 in every die frame (partition heights are multiples of 0.048).
A0_TRACK_OFFSET = [0.0, 0.012]
A0_PINS = {"nk": "cores/a0_nk_pins.json", "nl": "cores/a0_nl_pins.json"}
# measured core insertion at the boundary pin flops (QC-P3 10-23, a0ck gates post-CTS, placement RC; median/spread):
# NK @5a8a5c4b3 TT 924 (918..934) FF 742; NL @2019019b1 TT 1047 (1039..1077) FF 839.  The NL quads' NK taps need
# +123 ps TT / +97 ps FF branch delay (or the NL branch shortened) to hold quad core-to-core skew <= 80 ps.
A0_INSERTION_PS = {"nk": 924, "nl": 1047}


def declare_a0_hard_cores(P):
    for tn, t in sorted(P.types.items()):
        cores = [c for c in t["contents"] if c["module"].startswith("qfd_tile_n")]
        if not cores:
            continue
        kinds = set()
        hcs = []
        for c in cores:
            v = "nl" if c["module"].startswith("qfd_tile_nl") else "nk"
            kinds.add(v)
            o = "MY" if "orient MY" in c.get("note", "") else "R0"
            hcs.append(dict(inst=c["inst"], module=f"qfd_tile_{v}_a0c", origin_um=c["origin_um"],
                            outline_um=c["outline_um"], orient=o, track_offset_um=A0_TRACK_OFFSET,
                            pins_file=A0_PINS[v],
                            note=f"A0 {v.upper()} core (kit qfd_tile_{v}_a0ck), platform-track build: placed at "
                                 f"origin + (0, 0.012)"))
            for tp in t["clock"].get("taps", []):
                if tp["name"] == f"{c['inst']}.ck":
                    tp["insertion_ps"] = A0_INSERTION_PS[v]
                    tp["budget_owner"] = (f"measured qfd_tile_{v}_a0ck post-CTS TT boundary pin flops "
                                          f"(QC-P3 10-23; final after GRT/STA)")
        t["hard_cores"] = hcs
        if len(kinds) > 1:
            for tp in t["clock"].get("taps", []):
                if tp.get("kind") == "core" and tp.get("insertion_ps") == A0_INSERTION_PS["nk"]:
                    tp["note"] = ("mixed NK/NL quad: this NK tap branch needs +123 ps TT / +97 ps FF vs the NL tap "
                                  "(measured core insertion) so quad core-to-core skew stays <= 80 ps")


# QC-P6-G0C 10-23 (COORD G0C: types > 400k cells need hard_cores[]): the slice SU partitions are built from planned
# hard cores (variant B record: su_l0/l1 = 4 lane-group cores ~111k + ~20k glue; su_c = 8 leaf cores <= 106k + ~60k
# glue).  Core boxes are on the 8.64 lattice with outlines that are lattice multiples, pins on the SYMMETRIC M4 (E/W
# faces) / M5 (N/S faces) plan tracks (offset = pitch/2), so every R0/MX/MY instance frame is on track with
# track_offset [0, 0].  Glue taps (clock_taps) stay in the channels between cores.
# QC-SUROW 10-25: lane cores 414.72 x 267.84 (48 x 31 lattice = 111,081 um2, same area as the old 535.68 x 207.36) so the
# su_l partition keeps a 190.08-um macro-free V channel on its bus face side (ft stations + face pin registers) and a
# 17.28-um strip on the far side.  Rows (SRH 1339.2): 34.56 | core | 51.84 | core | 103.68 (glue tap gap, partition
# centre) | core | 51.84 | core | 25.92.  QC_SU_LANE_CORE=535.68x207.36 with QC_SRH=1080 restores the old geometry.
SU_LANE_CORE = tuple(float(v) for v in __import__("os").environ.get("QC_SU_LANE_CORE", "414.72x267.84").split("x"))


def _su_lane_y(srh, ch):
    """4 stacked lane cores; free height split like the 1080 plan (edges 3/26, inner gaps 5/26, centre tap gap 10/26)."""
    gaps = srh - 4 * ch
    e = round(gaps * 3 / 26 / 8.64) * 8.64
    tap = round(gaps * 10 / 26 / 8.64) * 8.64
    inner = round((gaps - 2 * e - tap) / 2 / 8.64) * 8.64
    return tuple(round(v, 2) for v in (e, e + ch + inner, e + 2 * ch + inner + tap, e + 3 * ch + 2 * inner + tap))


SU_ROW_RS = __import__("os").environ.get("QC_SU_ROW_RS", "1") == "1"   # S-half rs words along the SU row
SU_LANE_Y = ((25.92, 285.12, 578.88, 838.08) if (SRH, SU_LANE_CORE) == (1080.0, (535.68, 207.36)) else _su_lane_y(SRH, SU_LANE_CORE[1]))
SU_LANE_X = {"su_l0": round(622.08 - 17.28 - SU_LANE_CORE[0], 2), "su_l1": 17.28}   # channel on the bus face side (su_l0 W, su_l1 E)
# su_c: two leaf columns per half, centre channel x 561.6-665.28 keeps both glue taps (x 613.44) and the cws2 slot;
# the top band y 734-1080 is the glue (u_suvm / u_red rework + u_pstn) under the N-face ctl/sc windows.
SU_C_CORES = {"u_suvm_u_vm8q_u_va": (25.92, 51.84), "u_suvm_u_vm8q_u_vb": (302.4, 51.84),
              "u_suvm_u_vm8q_u_vc": (665.28, 51.84), "u_suvm_u_vm8q_u_cl": (941.76, 51.84),
              "u_suvm_u_vm8q_u_pg": (25.92, 380.16), "u_suvm_u_vm8q_u_ch": (302.4, 380.16),
              "u_suvm_u_vm8q_u_bt": (665.28, 380.16), "u_suvm_u_su8": (941.76, 380.16)}
SU_C_IO_PINS = 256                               # provisional core port 'io' until the leaf LEF port table is bound
_NRM = dict(N=(0.0, 1.0), S=(0.0, -1.0), E=(1.0, 0.0), W=(-1.0, 0.0))


def _face_toward(c, pt):
    dx, dy = pt[0] - c[0], pt[1] - c[1]
    d = math.hypot(dx, dy) or 1.0
    return max("NSEW", key=lambda f: _NRM[f][0] * dx / d + _NRM[f][1] * dy / d)


def _core_pin_table(cw, ch, groups):
    """[(port, width, face)] -> pins on symmetric tracks: E/W faces M4 (pitch 0.048), N/S faces M5 (0.048); pins every
    3rd track (0.144 um), each face's groups centred on the face."""
    out = []
    by_face = collections.defaultdict(list)
    for port, wd, f in groups:
        by_face[f].append((port, wd))
    for f, gs in by_face.items():
        n = sum(wd for _, wd in gs)
        span = ch if f in "EW" else cw
        step = 0.144
        while n * step > span - 4.32 and step > 0.048:
            step -= 0.048
        assert n * step <= span - 4.32, (f, n, span)
        k0 = int(round(((span - n * step) / 2 - 0.024) / 0.048))
        k = 0
        for port, wd in gs:
            for b in range(wd):
                a = round(0.024 + k0 * 0.048 + k * step, 4)
                k += 1
                nm = f"{port}[{b}]" if wd > 1 else port
                if f in "EW":
                    out.append({"name": nm, "layer": "M4", "x": 0.096 if f == "W" else round(cw - 0.096, 4), "y": a})
                else:
                    out.append({"name": nm, "layer": "M5", "x": a, "y": 0.096 if f == "S" else round(ch - 0.096, 4)})
    return out


def declare_su_hard_cores(P, outdir, su_directed):
    lane_c = collections.Counter()
    for r in su_directed["source_rows"]:
        if r["src_group"].startswith("su_l"):
            lane_c[int(re.sub(r"\D", "", r["src_inst"]))] += r["bits"]
    ext = su_directed["external_directed_bits"]
    conns, cells = {}, {}
    pdir = Path(outdir) / "cores" / "su"
    pdir.mkdir(parents=True, exist_ok=True)
    for tn, t in sorted(P.types.items()):
        m = re.match(r"^sl([we])_(su_l[01]|su_c)(?:_v[0-9]+)?$", tn)
        if not m:
            continue
        side, reg = m.groups()
        bt = {b["name"]: b for b in t["buses"]}

        def target(bus):
            b = bt[bus]
            w, h = t["outline_um"]
            a = 0.5 * sum(b["window_um"])
            return dict(N=(a, h), S=(a, 0.0), E=(w, a), W=(0.0, a))[b["face"]]
        hcs, tc = [], {}
        if reg.startswith("su_l"):
            g = int(reg[-1])
            cw, ch = SU_LANE_CORE
            for j, y in enumerate(SU_LANE_Y):
                lane = 4 * g + j
                inst = f"u_lane{lane}"
                c = (SU_LANE_X[reg] + cw / 2, y + ch / 2)
                sc = ext[f"{reg}->r_sc"]
                ports = [("c_i", 760, "x_su_c_i"), ("c_o", lane_c[lane], "x_su_c_o"),
                         ("ctl_o", ext[f"{reg}->r_ctl"] // 4, "x_ctl_o"),
                         ("stm_o", ext[f"{reg}->r_stm"] // 4, "x_stm_o"),
                         ("sc_o", sc // 4 + (1 if j < sc % 4 else 0), "x_sc_o")]
                groups = [(pn, wd, _face_toward(c, target(bus))) for pn, wd, bus in ports if wd]
                pins = _core_pin_table(cw, ch, groups)
                f = pdir / f"{tn}_{inst}_pins.json"
                f.write_text(json.dumps({"schema": "opentallas.core_pins.v1", "core": f"qfd_qc_su_lane_{side}",
                                         "frame": "core R0, origin (0,0)", "source": "QC-P6-G0C top-down plan pins",
                                         "pins": pins}, indent=0) + "\n")
                lv = [x for x in t["contents"] if re.match(rf"^u_(exp|rsq|head|rcp|lrly){lane}$", x["inst"])]
                hcs.append(dict(inst=inst, module=f"qfd_qc_su_lane_{side}", origin_um=[SU_LANE_X[reg], y],
                                outline_um=[cw, ch], orient="R0", track_offset_um=[0.0, 0.0],
                                pins_file=str(f.relative_to(outdir)),
                                note=f"SU lane-group {lane} hard core = {', '.join(x['inst'] for x in lv)} "
                                     f"(closed slice leaves, flattened inside the core); top-down pins (c_i 760 incl. "
                                     f"gb 500 broadcast, c_o {lane_c[lane]}, ctl/stm/sc share of the group)"))
                tc[inst] = {pn: [f"bus:{bus}"] for pn, wd, bus in ports if wd}
                cells[f"{tn}.{inst}"] = int(sum(x["outline_um"][0] * x["outline_um"][1] for x in lv) * UTIL / CELL_UM2)
        else:
            byi = {x["inst"]: x for x in t["contents"]}
            glue = (613.44, 907.2)
            for inst, (x0, y0) in SU_C_CORES.items():
                cw, ch = byi[inst]["outline_um"]
                c = (x0 + cw / 2, y0 + ch / 2)
                pins = _core_pin_table(cw, ch, [("io", SU_C_IO_PINS, _face_toward(c, glue))])
                f = pdir / f"{tn}_{inst}_pins.json"
                f.write_text(json.dumps({"schema": "opentallas.core_pins.v1", "core": byi[inst]["module"],
                                         "frame": "core R0, origin (0,0)",
                                         "source": "QC-P6-G0C provisional: one 'io' group facing the glue band; the "
                                                   "leaf LEF port table replaces it when the su_c leaves are bound",
                                         "pins": pins}, indent=0) + "\n")
                hcs.append(dict(inst=inst, module=byi[inst]["module"], origin_um=[x0, y0], outline_um=[cw, ch],
                                orient="R0", track_offset_um=[0.0, 0.0], pins_file=str(f.relative_to(outdir)),
                                note="su_c leaf hard core (closed slice leaf kit outline); pins provisional"))
                byi[inst]["origin_um"] = [x0, y0]
                cells[f"{tn}.{inst}"] = int(cw * ch * UTIL / CELL_UM2)
        t["hard_cores"] = hcs
        for h in hcs:
            ox, oy = h["origin_um"]
            cw, ch = h["outline_um"]
            t["clock"].setdefault("taps", []).append(dict(
                name=f"{h['inst']}.ck", kind="core", xy=[snap(ox + cw / 2), snap(oy + ch / 2)], orient="R0",
                insertion_ps=250, insertion_tol_ps=40, budget_owner="SU core kit (own CTS, balanced to the die 250)"))
        if tc:
            conns[tn] = tc
    (Path(outdir) / "core_conns.json").write_text(json.dumps(conns, indent=1, sort_keys=True) + "\n")
    return cells


def _a0_pin_groups(hc, outdir):
    """{port: (x, y)} type-frame centroid of each A0 core pin group (pins_file, orient, origin + track_offset)."""
    js = json.loads((Path(outdir) / hc["pins_file"]).read_text())
    cw, ch = hc["outline_um"]
    g = collections.defaultdict(list)
    for q in js["pins"]:
        x, y = q["x"], q["y"]
        if hc.get("orient") == "MY":
            x = cw - x
        g[re.sub(r"\[\d+\]$", "", q["name"])].append((x, y))
    dx, dy = hc.get("track_offset_um", [0.0, 0.0])
    return {k: (round(hc["origin_um"][0] + dx + sum(p[0] for p in v) / len(v), 3),
                round(hc["origin_um"][1] + dy + sum(p[1] for p in v) / len(v), 3)) for k, v in g.items()}


def declare_internal_stations(P, ports, lanes, outdir):
    """R3-INTERNAL (COORD 10-23 18:15): a reg-reg path inside a partition longer than ST_LEN (face flop at the bus
    window <-> the A0 core pin flop) gets FIRM plan stations.  Route: window -> along the face to the channel beside
    the core's data-pin edge -> along the channel -> pin; n = ceil(len / ST_LEN) - 1 stations at equal arclength,
    moved out of any core box.  Every lane that launches / lands on such a bus gets fixed_cycles += n (latency table
    + R8 pads count them).  Uses the TRUE pin-group distance, not the G0C box lower bound."""
    added = {}
    for tn, t in sorted(P.types.items()):
        hcs = [h for h in t.get("hard_cores", []) if h.get("module", "").startswith("qfd_tile_n")]
        if not hcs:
            continue
        w, h = t["outline_um"]
        boxes = [(hc["origin_um"][0], hc["origin_um"][1], hc["origin_um"][0] + hc["outline_um"][0],
                  hc["origin_um"][1] + hc["outline_um"][1]) for hc in hcs]
        pins = {hc["inst"]: (_a0_pin_groups(hc, outdir), hc) for hc in hcs}
        ist = []
        for b in t["buses"]:
            li, _, lp = (b.get("leaf") or "").partition(".")
            if li not in pins or lp not in pins[li][0] or "window_um" not in b:
                continue
            pp, hc = pins[li][0][lp], pins[li][1]
            m = 0.5 * sum(b["window_um"])
            a = dict(N=(m, h), S=(m, 0.0), E=(w, m), W=(0.0, m))[b["face"]]
            # channel beside the data-pin edge (W edge in R0, E edge in MY), centred in the gap to the outline /
            # to the neighbouring core
            x0 = hc["origin_um"][0]
            x1 = x0 + hc["outline_um"][0]
            if hc.get("orient") == "MY":
                nxt = min([bx[0] for bx in boxes if bx[0] >= x1 - 1e-6] + [w])
                xc = snap(0.5 * (x1 + nxt))
            else:
                prv = max([bx[2] for bx in boxes if bx[2] <= x0 + 1e-6] + [0.0])
                xc = snap(0.5 * (prv + x0))
            if b["face"] in "NS":
                path = [a, (xc, a[1]), (xc, pp[1]), pp]
            else:
                path = [a, (xc, a[1]), (xc, pp[1]), pp] if abs(a[0] - xc) < 0.5 * w else [a, (a[0], pp[1]), pp]
            segs = [abs(p[0] - q[0]) + abs(p[1] - q[1]) for p, q in zip(path, path[1:])]
            L = sum(segs)
            if L <= ST_LEN:
                continue
            n = math.ceil(L / ST_LEN) - 1
            while True:
                regs = []
                for k in range(1, n + 1):
                    d = L * k / (n + 1)
                    for (p, q), sl in zip(zip(path, path[1:]), segs):
                        if d <= sl + 1e-9 and sl > 0:
                            f_ = d / sl
                            regs.append([snap(p[0] + f_ * (q[0] - p[0])), snap(p[1] + f_ * (q[1] - p[1]))])
                            break
                        d -= sl
                for r_ in regs:          # a station is glue: never inside a core box
                    for bx in boxes:
                        if bx[0] < r_[0] < bx[2] and bx[1] < r_[1] < bx[3]:
                            r_[1] = snap(bx[3] + 8.64) if r_[1] > 0.5 * (bx[1] + bx[3]) else snap(bx[1] - 8.64)
                hops = [tuple(a)] + [tuple(r_) for r_ in regs] + [tuple(pp)]
                if max(abs(p[0] - q[0]) + abs(p[1] - q[1]) for p, q in zip(hops, hops[1:])) <= ST_LEN:
                    break
                n += 1
            ist.append(dict(conn=f"bus:{b['name']}", from_um=[round(a[0], 3), round(a[1], 3)],
                            to_um=[pp[0], pp[1]], regs_um=regs, bits=b["width"] + 1,
                            launch="face flop" if b["dir"] == "in" else f"{li}.{lp}",
                            capture=f"{li}.{lp}" if b["dir"] == "in" else "face flop",
                            note=f"R3-INTERNAL: {L:.0f} um window<->pin route, {n} FIRM station(s) (data + epoch); "
                                 f"counted in the lane fixed_cycles"))
            added[(tn, b["name"])] = n
        if ist:
            t["internal_stations"] = ist
    pmap = {pr["id"]: pr for pr in ports}
    nl = 0
    for ln in lanes:
        a, z = pmap[ln["ports"][0]], pmap[ln["ports"][-1]]
        k = 0
        for e in (a["src"], z["dst"]):
            if e["part"] in P.parts:
                k += added.get((P.parts[e["part"]]["type"], e["bus"]), 0)
        if k:
            ln["fixed_cycles"] = ln.get("fixed_cycles", 0) + k
            nl += 1
    return {"buses": {f"{tn}.{bn}": n for (tn, bn), n in sorted(added.items())}, "lanes": nl,
            "stations": sum(added.values())}


def neighbours(P):
    """abutting partitions per partition (G1 star flag > 6) and the linked subset."""
    names = list(P.parts)
    rect = {n: P.rect(n) for n in names}
    nb = collections.defaultdict(set)
    for i, a in enumerate(names):
        ax0, ay0, ax1, ay1 = rect[a]
        for b in names[i + 1:]:
            bx0, by0, bx1, by1 = rect[b]
            if bx0 > ax1 + 1e-6 or ax0 > bx1 + 1e-6 or by0 > ay1 + 1e-6 or ay0 > by1 + 1e-6:
                continue
            if shared_face(P, a, b, quiet=True):
                nb[a].add(b)
                nb[b].add(a)
    linked = collections.defaultdict(set)
    for lk in P.links:
        for x, y in zip(lk["path"], lk["path"][1:]):
            linked[x].add(y)
            linked[y].add(x)
    return {n: dict(abutting=len(nb[n]), linked=len(linked[n]), linked_to=sorted(linked[n])) for n in names}


# ====================================================================== census declaration (G0, COORD 06:45)
def _tsv(path, rows):
    with gzip.open(path, "wt") as fh:
        fh.write("src\tsrc_bus\tdst\tdst_bus\tkind\tbits\n")
        for r in rows:
            fh.write("\t".join(str(r[k]) for k in ("src", "src_bus", "dst", "dst_bus", "kind", "bits")) + "\n")


def write_census(P, geo, census, record, outdir, su_directed):
    """three census sources for tools/die_plan/census_cov.py:
    [0] the as-built die census (inputs/qc_census.json.gz, every row) with three edits only: rows touching the
        as-built fault OR network (flt_*) -> kind 'fault' (replaced by the plan 1-bit OR tree, exempted with reason),
        and the CB level-7 'rs'/'rs_o' word -> 'data' (the census types it 'reset' by name; it is 514-b data, planned
        as rsn/rsf), and the near cluster's rs_i -> rs_o relay collapsed (far rs -> slice = plan rsf through the near
        quads).  Slices, CB16 clusters and io_collective are GROUPS (one census block -> several partitions).
    [1] slice regions (inputs/s8_lp_record.json landings, the 210 region crossings), one copy per slice: covers the
        traffic inside the slice groups.  cs0-3 (cs -> u_fs -> cw_s forwarder) are the plan cw lanes, checked in [0];
        broadcast nets (BCAST) are counted per tree hop. The former r_su is split by source-bound child-pin
        directions in inputs/su_directed.json; actual internal SU rows are a finer census, not a hidden group.
    [2] io_collective internals (rtl/physical/ot_qfd_collective_static_io.sv): face <-> core records, R face <-> share
        frames, face <-> PHY flits, core <-> slice / sys_face: covers the traffic inside the coll group."""
    cdir = Path(outdir) / "census"
    cdir.mkdir(parents=True, exist_ok=True)
    cname = geo["col_name"]
    groups = {}
    for k, nm in enumerate(cname):
        groups[f"slice_{nm}"] = sorted(n for n in P.parts if n.startswith(f"sl_{nm}_"))
    for cl in geo["clusters"]:
        i = {("b", "far"): 0, ("b", "near"): 1, ("t", "near"): 2, ("t", "far"): 3}[(cl["half"], cl["kind"])]
        groups[f"cl_{cname[cl['col']]}_{i}"] = sorted(n for n in P.parts if n.startswith(cl["name"] + "_"))
    groups["coll"] = list(COLL_PARTS) + [COLL_UCIE[0]]
    base = {i: "glue" for i in GLUE_INSTS}
    base.update({i: "coll" for i in COLL_INSTS + ("io_ucie",)})
    base.update({i: i for i in WS if i not in COLL_PARTS and i != COLL_UCIE[0]})
    base.update({f"dvs_{nm}": f"slice_{nm}" for nm in cname})
    base.update({f"c16_{nm}_{i}": f"cl_{nm}_{i}" for nm in cname for i in range(4)})
    rows, parts = [], dict(base)
    known = sorted(base, key=len, reverse=True)
    for g in census["groups"]:
        r = {k: g[k] for k in ("src", "src_bus", "dst", "dst_bus", "kind", "bits")}
        if r["src"].startswith("flt_") or r["dst"].startswith("flt_"):
            r["kind"] = "fault"
        if r["src"].startswith("c16") and r["src_bus"] in ("rs", "rs_o"):
            r["kind"] = "data"
            if r["dst_bus"] == "rs_i":
                continue          # far rs -> near rs_i: the near cluster's rs_i -> rs_o is a pass-through relay ...
            if r["src_bus"] == "rs_o":   # ... so near rs_o -> slice is the far cluster's word (plan lane rsf, ft
                nm, i = r["src"].rsplit("_", 1)   # through the near quads)
                r["src"], r["src_bus"] = f"{nm}_{ {'1': 0, '2': 3}[i]}".replace(" ", ""), "rs"
        rows.append(r)
        for inst in (r["src"], r["dst"]):
            if inst.startswith("flt_") and inst not in parts:
                m = inst[len("flt_root_"):] if inst.startswith("flt_root_") else None
                own = next((x for x in known if m and (m == x or m.startswith(x + "_g"))), None)
                parts[inst] = base[own] if own else "@die"
    _tsv(cdir / "die_rows.tsv.gz", rows)
    exempt = [{"match": "^reset$", "kind": "reset", "replaced_by": "die reset spine + per-partition 2-stage sync",
               "reason": "as-built rstseq/rs_bump reset fan-out (and the fault roots' rs) is replaced by the plan reset"},
              {"match": "^fault$", "kind": "fault", "replaced_by": "plan fault OR tree (flt/flte/fltk/fltc/fltn/fltt "
               "1-bit registered lanes; plan_notes.census_coverage.fault_sources_without_plan_lane = [])",
               "reason": "the as-built flt_root/flt_hop/flt_leaf OR network (1-bit hops) is re-derived as a plan tree; "
                         "each flt_root_<blk> sits in <blk>'s partition, hop/leaf cells are die-level (@die)"}]
    json.dump({"note": "QC-FIX die census map (gen_plan.py write_census [0])", "parts": parts, "groups": groups,
               "exempt": exempt}, open(cdir / "die_map.json", "w"), indent=1)
    # [1] slice regions
    rows1, parts1, groups1 = [], {}, {}
    for k, nm in enumerate(cname):
        for ld in directed_slice_landings(record, su_directed):
            if ld["net"] in ("cs0", "cs1", "cs2", "cs3"):
                continue
            s_, d_ = ld["src_region"], ld["dst_region"]
            bk = (s_, ld["net"])
            if bk in BCAST or bk in BCAST_ALIAS:
                continue
            rows1.append(dict(src=f"{nm}/{s_}", src_bus=ld["net"], dst=f"{nm}/{d_}", dst_bus=ld["net"], kind="data",
                              bits=ld["width"]))
        for bk, hops in BCAST.items():
            grp = [bk] + [a_ for a_, b_ in BCAST_ALIAS.items() if b_ == bk]
            w = sum(max((ld["width"] for ld in record["landings"] if (ld["src_region"], ld["net"]) == g), default=0)
                    for g in grp)
            for a, b in hops:
                rows1.append(dict(src=f"{nm}/tree_{a}", src_bus=bk[1], dst=f"{nm}/tree_{b}", dst_bus=bk[1],
                                  kind="data", bits=w))
                for x in (a, b):
                    parts1[f"{nm}/tree_{x}"] = sl(geo, k, x)
        for rg, reg in REGION_OF.items():
            if rg != "r_su":
                parts1[f"{nm}/{rg}"] = sl(geo, k, reg)
        for reg in ("su_c", "su_l0", "su_l1"):
            parts1[f"{nm}/{reg}"] = sl(geo, k, reg)
        for row in su_directed["internal"]:
            rows1.append(dict(src=f"{nm}/{row['src']}", src_bus=row["net"],
                              dst=f"{nm}/{row['dst']}", dst_bus=row["net"], kind="data", bits=row["bits"]))
    rows1, unl1 = unloaded_census_filter(P, rows1, parts1, 1)
    _tsv(cdir / "slice_rows.tsv.gz", rows1)
    json.dump({"note": "QC-FIX slice-region census map (gen_plan.py write_census [1])", "parts": parts1,
               "groups": groups1, "unloaded_removed": unl1}, open(cdir / "slice_map.json", "w"), indent=1)
    # [2] io_collective internals
    rows2 = []
    for f, (seg, _) in COLL_CORES.items():
        W = COLL_FW[f]
        rows2 += [dict(src="u_collective", src_bus=f"tx_rec_{f}", dst=f"face_{f}", dst_bus="tx", kind="data", bits=W + 3),
                  dict(src=f"face_{f}", src_bus="rx", dst="u_collective", dst_bus=f"rx_rec_{f}", kind="data", bits=W + 1)]
    rows2 += [dict(src="face_r", src_bus="phy_tx", dst="u_shared", dst_bus="r_frame", kind="data", bits=568),
              dict(src="u_shared", src_bus="rx_frames", dst="face_r", dst_bus="phy_rx", kind="data", bits=566),
              dict(src="face_p", src_bus="phy_tx", dst="u_shared", dst_bus="p_frame", kind="data", bits=600),
              dict(src="u_shared", src_bus="rx_frames", dst="face_p", dst_bus="phy_rx", kind="data", bits=598),
              dict(src="u_shared", src_bus="shared_tx", dst="io_ucie", dst_bus="tx_flit", kind="data", bits=1044),
              dict(src="io_ucie", src_bus="rx_flit", dst="u_shared", dst_bus="shared_rx", kind="data", bits=1044)]
    for f, phy in (("s0", "io_serdes"), ("s1", "io_serdes_1"), ("s2", "io_serdes_2")):
        rows2 += [dict(src=f"face_{f}", src_bus="phy_tx", dst=phy, dst_bus="tx_flit", kind="data", bits=598),
                  dict(src=phy, src_bus="rx_flit", dst=f"face_{f}", dst_bus="phy_rx", kind="data", bits=599)]
    for g in census["groups"]:
        if g["src"] == "io_collective" and g["dst"] in ("dvs_W5", "sys_face"):
            rows2.append(dict(src="u_shared" if g["src_bus"] == "shared_fault" else "u_collective",
                              src_bus=g["src_bus"], dst=g["dst"], dst_bus=g["dst_bus"], kind=g["kind"],
                              bits=g["bits"]))
        if g["dst"] == "io_collective" and g["src"] == "dvs_W5":
            rows2.append(dict(src=g["src"], src_bus=g["src_bus"], dst="u_collective", dst_bus=g["dst_bus"],
                              kind=g["kind"], bits=g["bits"]))
    parts2 = {f"face_{f}": seg for f, (seg, _) in COLL_CORES.items()}
    parts2.update({"u_collective": "coll_core", "u_shared": COLL_UCIE[0], "io_ucie": COLL_UCIE[0], "io_serdes": "io_serdes",
                   "io_serdes_1": "io_serdes_1", "io_serdes_2": "io_serdes_2", "sys_face": "glue",
                   "dvs_W5": "slice_W5"})
    rows2, unl2 = unloaded_census_filter(P, rows2, parts2, 2)
    _tsv(cdir / "coll_rows.tsv.gz", rows2)
    json.dump({"note": "QC-FIX io_collective internal census map (gen_plan.py write_census [2]; widths from "
                       "rtl/physical/ot_qfd_collective_static_io.sv: record W+3/W+1, PW = W+51, slots 1+1)",
               "parts": parts2, "groups": {"slice_W5": groups["slice_W5"]}, "unloaded_removed": unl2},
              open(cdir / "coll_map.json", "w"), indent=1)
    # [3] CB16 cluster internals (R7, 10-23): the as-built reduction tree CB_TREE (traced from qfd_c_b16_dv_fabric)
    # per cluster (the bc relay chain u_dn<c>_rly* is BINDER2-clean and not re-traced here); parts = the tile cell's CB unit, so the 4-quad cl_* groups of [0] are
    # covered bit-for-bit (BINDER2 found 73,968 b of tree crossings the coarse group hid).
    rows3, parts3 = [], {}
    for cl in geo["clusters"]:
        n = cl["name"]
        for c in range(4):
            for r in range(4):
                parts3[f"{n}.t{c}{r}"] = cb_part(VARIANT, n, c, r)
        for (dc, dr), dport, (sc, sr), sport in CB_TREE:
            rows3.append(dict(src=f"{n}.t{sc}{sr}", src_bus=sport, dst=f"{n}.t{dc}{dr}", dst_bus=dport, kind="data",
                              bits=RSW))
    _tsv(cdir / "cb_rows.tsv.gz", rows3)
    json.dump({"note": "QC-P3 R7 CB16 cluster-internal census map (gen_plan.py write_census [3]; CB_TREE)",
               "parts": parts3, "groups": {}}, open(cdir / "cb_map.json", "w"), indent=1)
    return [{"rows": "census/die_rows.tsv.gz", "map": "census/die_map.json",
             "note": "as-built die census (FT-TOOL, r50 die; inputs/qc_census.json.gz), kind relabels only"},
            {"rows": "census/slice_rows.tsv.gz", "map": "census/slice_map.json",
             "note": "slice landed-region census (inputs/s8_lp_record.json) x 12 slices"},
            {"rows": "census/coll_rows.tsv.gz", "map": "census/coll_map.json",
             "note": "io_collective internals from the RTL (face cores, share, UCIe, PHY flits)"},
            {"rows": "census/cb_rows.tsv.gz", "map": "census/cb_map.json",
             "note": "CB16 cluster internals: as-built reduction tree (qfd_c_b16_dv_fabric trace)"}]


# ====================================================================== main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", choices=("A", "B"), default="B",
                    help="B = CB quads (COORD 10-23 06:41 VARIANT B CHOSEN, the main plan); A = per-A0 CB partitions (archived: regenerate on demand)")
    ap.add_argument("--census", required=True)
    ap.add_argument("--slice-fp-w", required=True)
    ap.add_argument("--slice-fp-e", required=True)
    ap.add_argument("--slice-record", required=True)
    ap.add_argument("--su-split", required=True, help="slice_grid.json (su core <-> lane-group bits)")
    ap.add_argument("--slice-face-map", required=True,
                    help="slice2_face_map.json (slice_face_map.py: die slice bus -> slice core port)")
    ap.add_argument("--out", default=str(Path(__file__).with_name("die_plan.json")))
    a = ap.parse_args()
    global VARIANT
    VARIANT = a.variant
    census = json.load(gzip.open(a.census)) if a.census.endswith(".gz") else json.loads(Path(a.census).read_text())
    fp = {"w": json.loads(Path(a.slice_fp_w).read_text()), "e": json.loads(Path(a.slice_fp_e).read_text())}
    fp_pins = {s: {b: f for f, bs in fp[s]["pins"].items() for b in bs} for s in "we"}
    record = json.loads(Path(a.slice_record).read_text())
    record["_reader_port_bits"] = json.loads(Path(a.slice_record).with_name("slice_reader_widths.json").read_text())["reader_port_bits"]
    su_split = json.loads(Path(a.su_split).read_text())["su_split_bits"]
    su_directed = json.loads(Path(a.su_split).with_name("su_directed.json").read_text())
    cblocks = {b["inst"]: b["master"] for b in census["blocks"]}
    P = Plan()
    P.cov = collections.defaultdict(list)
    P.cores = []
    col_x = [WS_W + k * CLW for k in range(NCOL)]
    col_name = [f"W{5 - k}" for k in range(6)] + [f"E{k}" for k in range(6)]
    y_sl = 2 * CLH
    H = 4 * CLH + SLH
    W = WS_W + NCOL * CLW
    geo = dict(W=W, H=H, col_x=col_x, col_name=col_name, y_sl=y_sl)
    geo["clusters"] = build_clusters(P, a.variant, col_x, col_name)
    build_slices(P, col_x, col_name, y_sl, fp)
    build_west(P, cblocks)
    clone_s2_types(P)
    cb_links(P, a.variant, geo)
    slice_cluster_links(P, a.variant, geo)
    slice_internal_links(P, geo, record, su_split, su_directed)
    P.neg_done = True
    face_map = json.loads(Path(a.slice_face_map).read_text())
    dropped = census_links(P, geo, census, fp_pins, face_map)
    treq_links(P, geo, census, fp_pins, face_map)
    P.coll_rows = coll_internal_links(P)
    fault_links(P, a.variant, geo)
    unl = drop_unloaded_lanes(P, Path(__file__).parent / "inputs" / "unloaded_lanes.json")
    print(f"unloaded lanes: dropped {len(unl['dropped'])}, absent {unl['absent']}")
    cov = coverage(P, census)
    ports, lanes = materialize(P)
    merged = merge_types(P)
    bind_leaves(P)
    ft_fracs(P)
    edge_clocks(P)
    chans = [{"rect_um": [0.0, 4648.32, SUB_W, 7603.2],
              "reason": "west-strip edge column below coll_ucie: the strip width is set by the serdes PHY depth "
                        "(1563.84 um); coll (786.24 wide) is taller than the edge-column content. PHY bump/decap/ESD "
                        "field, no logic"},
             {"rect_um": [0.0, 12268.8 + WS_DY, SUB_W, 13746.24 + WS_DY],
              "reason": "west-strip edge column above tt_ctlm: same strip-depth reason; decap"},
             {"rect_um": [0.0, 16070.4, WS_W, H],
              "reason": f"west strip above serdes S3: IO content (16.07 mm tall) is shorter than the compute "
                        f"column ({H / 1000:.2f} mm); strip width = serdes PHY depth. Bump/decap field; spare for the "
                        f"KV-die UCIe second port if the TP8 pair needs it"}]
    census_decl = write_census(P, geo, census, record, Path(a.out).parent, su_directed)
    taps = clock_taps(P)
    declare_clock_taps(P, taps)
    declare_a0_hard_cores(P)
    su_core_cells = declare_su_hard_cores(P, Path(a.out).parent, su_directed)
    r3i = declare_internal_stations(P, ports, lanes, Path(a.out).parent)
    nbrs = neighbours(P)
    plan = {
        "schema": "opentallas.die_plan.v1",
        "census": census_decl,
        "note": f"PLAN-QCv2 2026-10-23 variant {a.variant}: Qwen compute die, plan-first (TOPDOWN-PLAN). Generated "
                "by physical/die_plan/qwen_compute/gen_plan.py from the as-built connectivity (FT-TOOL census, "
                "r50/r56 die), the slice landed-parent record (region census) and the A0 rpf geometry.",
        "die": {"name": "qwen_compute", "label": "Qwen3-8B ROM compute die (TP8 pair with the KV/system die)",
                "tech": "asap7", "outline_um": [round(W, 4), round(H, 4)], "period_ps": 833, "reach_um": REACH,
                "rep_um": 450.0, "grid_um": G,
                "layer_budget": {"partition_signal_max": "M7", "die_layers": ["M8", "M9"],
                                 "die_use": ["clock_spine", "pg", "reset"],
                                 "cut_avail": {"M8": 0.6, "M9": 0.6}},
                "channels": chans,
                "pg": {"partition_pg_max": "M7", "grid": [
                    {"layer": "M8", "width_um": 0.48, "pitch_um": 8.64, "offset_um": 4.32, "nets": ["VDD", "VSS"]},
                    {"layer": "M9", "width_um": 0.48, "pitch_um": 8.64, "offset_um": 4.32, "nets": ["VDD", "VSS"]}]}},
        "partition_types": P.types,
        "partitions": [{"name": n, "type": p["type"], "origin_um": list(p["origin"]), "orient": p["orient"]}
                       for n, p in P.parts.items()],
        "ports": ports, "lanes": lanes,
        "clock": {"source": {"part": "coll_core", "bus": "clk_rx"}, "insertion_ps": 250, "insertion_tol_ps": 40,
                  "common_latency_ps": 250,
                  "neighbour_skew_ps": 80, "face_xing": "budgeted",
                  "spine": {"layers": ["M8", "M9"], "root_um": [round(W / 2, 2), round(y_sl + SLH / 2, 2)],
                            "topology": "htree"}},
        "reset": {"source": {"part": "glue", "bus": "rstseq_rom"}, "sync_stages": 2, "data_reset": False,
                  "epoch_bit": True, "release": "wavefront", "relay_um": REACH, "hop_um": REACH},
        "budgets": {"face_pins_per_um": 6, "face_pin_layers": 2, "face_window_um": 10, "pin_track_max": 0.6,
                    "cut_ratio_max": 0.6, "cut_step_um": 250, "ft_station_max_um": ST_LEN,
                    "reach_margin": 1.0},   # COORD 22:35: hops/stations <= 405 um exactly, no 0.9 margin
    }
    # QC-P6-A0 10-23: A0 v6 core clock drops per CB quad (inputs/a0_core_taps.json; no file -> no change)
    a0_taps = __import__("a0_core_taps").declare(P, Path(__file__).parent / "inputs" / "a0_core_taps.json", plan["clock"])
    # QC-A0 10-24 (GEOM-REVIEW batch 1): ft stations of hard-core partitions get declared sites off the cores
    # (routed hop = shortest path around the cores).  Slots whose routed hops still exceed the limit with their planned
    # station count are listed in ft_regs_report.json (more stations = a bound-RTL / R8 change: COORD decision)
    # QC 10-24 (owner-accepted capacity plan): every lane family into one hardened type gets ONE natural depth
    # (lane_eq.py: short lanes padded with ft stations along their route, not with per-instance landing pads);
    # ft_regs may add stations for routed hops, so equalise again until nothing moves
    leq = __import__("lane_eq")
    eqr = leq.equalise(plan)
    ftr = __import__("ft_regs").ft_regs_off_cores(plan)
    for _ in range(3):
        e2 = leq.equalise(plan)
        eqr["added"] += e2["added"]
        eqr["unfixed"], eqr["families_unequal_after"] = e2["unfixed"], e2["families_unequal_after"]
        if not e2["added"]:
            break
        f2 = __import__("ft_regs").ft_regs_off_cores(plan)
        ftr.setdefault("added_stations", []).extend(f2.get("added_stations", []))
        ftr["unfixed"] = f2["unfixed"]
    (Path(a.out).parent / "ft_regs_report.json").write_text(json.dumps(ftr, indent=1) + "\n")
    (Path(a.out).parent / "lane_eq_report.json").write_text(json.dumps(eqr, indent=1) + "\n")
    # Centres alone miss wide-window tails. Close every bit, allocate internal
    # cells in macro-free channels, and restore common lane-family depths.
    bsr = __import__("bit_stations").repair_equalised(plan)
    (Path(a.out).parent / "bit_stations_report.json").write_text(json.dumps(bsr, indent=1) + "\n")
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(plan, indent=1) + "\n")
    st = collections.Counter()
    for n, p in P.parts.items():
        for c in P.types[p["type"]]["contents"]:
            st[c["status"]] += 1
    inst = collections.Counter(p["type"] for p in P.parts.values())
    cells = {tn: dict(cells=P.cells.get(tn), instances=inst[tn], outline_um=P.types[tn]["outline_um"],
                      macros=sum(1 for c in P.types[tn]["contents"] if c["module"].startswith("qfd_tile")) * 10
                      + (1 if P.types[tn].get("hard") else 0))
             for tn in sorted(P.types)}
    notes = {"variant": a.variant, "partitions": len(P.parts), "types": len(P.types), "types_merged": merged,
             "ports": len(ports), "lanes": len(lanes), "unloaded_lanes_dropped": len(unl["dropped"]),
             "unloaded_lanes_absent": unl["absent"],
             "die_um": [round(W, 2), round(H, 2)], "die_mm2": round(W * H / 1e6, 1),
             "content_status_per_instance": dict(st),
             "max_cells_type": max(((v["cells"] or 0, k) for k, v in cells.items())),
             "cells_per_type": cells,
             "su_core_cells": su_core_cells,
             "r3_internal_stations": r3i,
             "internal_bits_absorbed": dict(P.internal_bits),
             "cell_estimate_method": f"A0 = {A0_CELLS} cells (NL rpf synth_stat incl. 10 ROM leaf macros); other "
                                     f"leaves = outline area x {UTIL} / {CELL_UM2} um2 per cell (A0 calibration); "
                                     "soft slice glue / W-strip blocks = per-region guesses (SOFT_CELLS/WS_CELLS)",
             "census_coverage": cov,
             "treq_lanes": {"note": "QC-P5-TIE: tt_ctlm.table_req -> every slice treq_i beside cmd (TREQ_BUS, "
                                    "treq_links); producer = HP13 cpub39 CALR treq_q (live, open in r56 die.v); the "
                                    "binder connects it with asbuilt rewire class 'treq' (bind/plan_rewires_treq.json)",
                            "lanes": P.treq},
             "planned_cores": P.cores,
             "a0_core_taps": a0_taps,
             # QC-P2 (COORD 10-23 head landed-LP 3317/27981): leaf parameters the die netlist binder MUST pass from
             # the plan.  The old landed parents qfd_tt_ctlm_dv_lpf.sv:93 / lp/qfd_tt_ctlm_dv_lpf_lp.sv:196 /
             # headprep/qfd_tt_ctlm_dv_lpf_hp.sv:123 instantiate ot_qfd_tt_ctlm_static_hr without .SEGCAL (default
             # 0) -> the head lockstep FAIL.  The plan's tt_ctlm partition binds the HP13 cpub39 leaf, whose source
             # (corepub39/qfd_tt_ctlm_dv_hp13_rrloc_native32_cpub39_1.sv:54572) elaborates SEGCAL=1, STAGE_ME=1.
             "leaf_params": {"tt_ctlm": {"ot_qfd_tt_ctlm_static_hr": {"SEGCAL": 1, "STAGE_ME": 1},
                                         "qfd_tt_ctlm_head_static": {"SEGCAL": 1},
                                         "check": "every instance of these modules under the tt_ctlm partition "
                                                  "carries these values (binder + elaborated-netlist grep)"}},
             "coll_split": {"segments": [dict(part=n, type=tn, y0_um=y0, h_um=h) for n, tn, y0, h in COLL_SEGS],
                            "cores": len(P.cores) + 1, "max_core_cells_est": max([c["cells_est"] for c in P.cores] or [0]),
                            "glue_cells_est": {k: v for k, v in COLL_GLUE.items()}, "cap": 400000,
                            "note": "5 face cores + the UCIe PHY hard core; face cells from the COLLIO-F face kits "
                                    "(std ~15k um2 each); glue = collective core + gearbox + share + clkrx + land "
                                    "(estimate; a synth count is owed)"},
             "clock_taps": {"rule": "COORD 10-23 07:24 ruling (2): one spine tap per planned core or landed glue "
                                     "region; die_plan clock.tap_um = the partition H-tap root (centre), the taps "
                                     "below are its declared M8/M9 branch leaves, also carried verbatim in "
                                     "schema clock.taps[] (insertion values remain estimates)", "insertion_model": INS_NOTE, "types": taps},
             "neighbours": {"max_abutting": max(v["abutting"] for v in nbrs.values()),
                            "max_linked": max(v["linked"] for v in nbrs.values()),
                            "over_6_abutting": {n: v for n, v in nbrs.items() if v["abutting"] > 6},
                            "coll": {n: nbrs[n] for n in COLL_PARTS}},
             "coll_internal_rows": [dict(role=r[0], src=r[1], dst=r[2], bits=r[3]) for r in P.coll_rows],
             "census_dropped_bits": {"|".join(map(str, k)): v for k, v in sorted(dropped.items())}}
    Path(a.out).with_name("plan_notes.json").write_text(json.dumps(notes, indent=1) + "\n")
    print(json.dumps({k: v for k, v in notes.items() if k not in ("census_dropped_bits", "cells_per_type")}))


if __name__ == "__main__":
    main()
