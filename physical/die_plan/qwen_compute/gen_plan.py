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
      S2 | S1 | [coll 786.24 wide (UCIe PHY = planned hard core inside, keeps its FDI clocks off the seams)  +
      777.6-wide edge column: ucie_kv, glue, native59, tt_ctlm] | S3 (MX)
    coll abuts the W5 slice fw face; S2 reaches coll through the W5 far-bottom CB column 0 (ft slots).
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
REACH = 1000.0
ST_LEN = 900.0                       # one station per <= 900 um of slot route
DENS = 4.2                           # pins / um per port window (budget 6 incl. track rounding)
GAP = 0.96
EDGE = 4.32

CW = [622.08, 613.44, 613.44, 622.08]
RH = [1313.28, 1296.0, 1296.0, 1321.92]
A0W, A0H = 457.92, 1157.76
CLW, CLH = sum(CW), sum(RH)          # 2471.04 x 5227.2
SRH = 1080.0                         # slice row height (864 overflowed the slice faces at 4.7 pins/um)
SLH = 4 * SRH                        # 3456
NCOL = 12
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


def qlen(width, dens, layers, lo=100.0, flip=False):
    """smallest window length (from width/FACE_MAX up, 0.016 steps) at its ACTUAL die position (lattice 8.64: the same
    pins in every frame) whose pins, laid by the PLAN-TOOL rule itself (schema.pin_positions: coordinate-uniform
    spread, never on a partition PG stripe band), stay <= FACE_MAX/um in every 10-um span.  QC-P2: the old replica of
    the pin rule ignored the PG bands (G0 failed 1-bit ports whose window sat inside an M5/M7 band)."""
    key = (width, tuple(layers), round(lo % G, 4), flip)
    if key in _QL:
        return _QL[key]
    L = max(0.384, math.ceil(width / FACE_MAX / 0.016) * 0.016)
    while True:
        win = [lo - L, lo] if flip else [lo, lo + L]
        try:
            cs = sorted(c for _, _, c in _S.pin_positions(
                {"id": "q", "window_um": win, "layers": list(layers), "width": width, "epoch": False}, _LAYERS))
        except ValueError:
            cs = None
        ok = cs is not None
        if ok:
            j = 0
            for i in range(len(cs)):
                while cs[i] - cs[j] > 10.0 - 1e-6:
                    j += 1
                if (i - j + 1) > FACE_MAX * 10.0 + 1e-6:
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
        nl = (c == 3 and r == 3)
        cont.append({"inst": f"u_t{sfx}", "module": "qfd_tile_nl_romleaf_rpf" if nl else "qfd_tile_nk_romleaf_rpf",
                     "status": "reuse", "kit": A0L_KIT if nl else A0_KIT, "geom_pass": A0_GEOM,
                     "origin_um": [round(sum(CW[:c]) - ux + ox, 4), round(sum(RH[:r]) - uy + oy, 4)],
                     "outline_um": [A0W, A0H],
                     "note": "A0 reference (TOPDOWN L1: leaf RTL flattened, ROM leaf macros stay hard)"})
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
        for r in range(4):
            T.append((f"t0{r}", [(0, r), (1, r)], "t_o", "na_i", "t_out", "n_a"))
            T.append((f"t3{r}", [(3, r), (2, r)], "t_o", "na_i", "t_out", "n_a"))
        T += [("l1a", [(1, 1), (0, 1)], "y_o", "na_i", "n_y", "n_a"),
              ("l1b", [(1, 0), (1, 1), (0, 1)], "y_o", "nb_i", "n_y", "n_b"),
              ("l1c", [(2, 1), (3, 1)], "y_o", "na_i", "n_y", "n_a"),
              ("l1d", [(2, 0), (2, 1), (3, 1)], "y_o", "nb_i", "n_y", "n_b"),
              ("l1e", [(1, 2), (0, 2)], "y_o", "na_i", "n_y", "n_a"),
              ("l1f", [(1, 3), (1, 2), (0, 2)], "y_o", "nb_i", "n_y", "n_b"),
              ("l1g", [(2, 2), (3, 2)], "y_o", "na_i", "n_y", "n_a"),
              ("l1h", [(2, 3), (2, 2), (3, 2)], "y_o", "nb_i", "n_y", "n_b"),
              ("l2a", [(3, 1), (3, 0)], "y_o", "na_i", "n_y", "n_a"),
              ("l2b", [(0, 1), (0, 0), (1, 0), (2, 0), (3, 0)], "y_o", "nb_i", "n_y", "n_b"),
              ("l2c", [(0, 2), (0, 3)], "y_o", "na_i", "n_y", "n_a"),
              ("l2d", [(3, 2), (3, 3), (2, 3), (1, 3), (0, 3)], "y_o", "nb_i", "n_y", "n_b"),
              ("l3a", [(3, 0), (2, 0), (1, 0), (0, 0)], "y_o", "na_i", "n_y", "n_a"),
              ("l3b", [(0, 3), (0, 2), (0, 1), (0, 0)], "y_o", "nb_i", "n_y", "n_b")]
        for role, path, sb, db, sl, dl in T:
            s, d = path[0], path[-1]
            P.link(role, [p(*q) for q in path], f"{sb}{sfx(*s)}", f"{db}{sfx(*d)}", RSW,
                   src_leaf=f"u_t{sfx(*s)}.{sl}", dst_leaf=f"u_t{sfx(*d)}.{dl}")


# ====================================================================== slices
# slice regions on the 4x4 grid: chosen by slice_layout_search.py (negotiated routing over 3 x 524k layouts, fw/fe
# row 0/1/2; args 5517 3159 1500 <row>); fw/fe on the W/E edges of one row so they abut the neighbour slices; hc row fixed
# on the cluster side. Best max face load 0.928 at 5.15 pins/um, 1080-um rows (fw/fe row 2: 0.959; row 0: 1.028)
SL_CELLS_W = {"hc0": (0, 3), "hc1": (1, 3), "hc2": (2, 3), "hc3": (3, 3),
              "st_b": (0, 2), "ctl": (1, 2), "tap": (2, 2), "st_a": (3, 2),
              "fw": (0, 1), "stm": (1, 1), "sc": (2, 1), "fe": (3, 1),
              "su_l1": (0, 0), "su_c": [(1, 0), (2, 0)], "su_l0": (3, 0)}
# E slices: SAME layout as W (QC-P2 10-23, census coverage).  The as-built die places the e16real kit MY, so every
# slice has its dn face (fw: ch_dn/st_dn/l9/... = census *_eo on E slices) physically on the W edge: the inter-slice
# chain is linear E5 -> .. -> E0 -> W0 -> .. -> W5 (census pins: dvs_E1 ard_eo leaves at E1's W edge x=20001.6).  The
# v2 mirrored E layout put fw on the E edge, so slice-to-slice traffic could not abut (57.8k bits were dropped).
SL_CELLS_E = dict(SL_CELLS_W)
REGION_OF = {"r_fw": "fw", "r_fe": "fe", "r_stm": "stm", "r_ctl": "ctl", "r_sc": "sc", "r_su": "su_c",
             "r_tap": "tap", **{f"r_hc{i}": f"hc{i}" for i in range(4)},
             **{f"r_st{i}": ("st_a" if i < 4 else "st_b") for i in range(8)}}
LEAF_REGION = [(r"^u_r[0-3]$", "st_a"), (r"^u_r[4-7]$", "st_b"), (r"^u_btab\b", "st_a"), (r"^u_stm", "stm"),
               (r"^u_ctl", "ctl"), (r"^u_suvm", "su_c"), (r"^u_(lrly|head|exp|rcp|rsq)([0-3])$", "su_l0"),
               (r"^u_(lrly|head|exp|rcp|rsq)([4-7])$", "su_l1"), (r"^u_xh(\d)|^u_xl(\d)_", "hc")]
SOFT = {"fw": ["u_fdn"], "fe": ["u_fup"], "stm": ["u_stm", "u_fs (cs->cw_s forwarder: becomes plan lane)"],
        "ctl": ["u_ctl", "u_rp"], "sc": ["u_sc"], "tap": ["u_tap"], "su_c": ["u_suvm", "u_red"],
        "hc1": ["u_fn"], "st_a": ["u_frs"]}
SOFT_CELLS = {"fw": 60000, "fe": 50000, "stm": 60000, "ctl": 80000, "sc": 40000, "tap": 70000, "su_c": 60000,
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
    ("r_tap", "hw"): [("tap", "hc2"), ("hc2", "hc1"), ("hc1", "hc0"), ("hc2", "hc3")],
    ("r_stm", "tw_data"): [("stm", "ctl"), ("ctl", "st_a")],
}


def slice_internal_links(P, geo, record, su_split):
    for k in range(NCOL):
        agg = collections.Counter()
        trees = collections.Counter()
        for ld in record["landings"]:
            s, d = REGION_OF[ld["src_region"]], REGION_OF[ld["dst_region"]]
            if ld["net"] in ("cs0", "cs1", "cs2", "cs3"):
                continue                    # cs_c -> u_fs -> cw_s_c: replaced by the plan lane hc_c -> S face
            if s == d:
                continue
            bk = (ld["src_region"], ld["net"])
            if bk in BCAST:
                trees[bk] = max(trees[bk], ld["width"])
                continue
            agg[(s, d)] += ld["width"]
        flows = [(f"b_{bk[1]}_{a}_{b}", a, b, w, f"b_{bk[1]}_{b}_o", f"b_{bk[1]}_i", f"u_pstn.{bk[1]}_fwd",
                  f"u_{b}.{bk[1]}") for bk, w in trees.items() for a, b in BCAST[bk]]
        flows += [(f"x_{a}_{b}", a, b, w, f"x_{b}_o", f"x_{a}_i", f"u_{a}.x_{b}", f"u_{b}.x_{a}")
                  for (a, b), w in agg.items()]
        flows += [(f"x_su_c_{g}", "su_c", g, su_split[f"core|L{g[-1]}"], f"x_{g}_o", "x_su_c_i",
                   f"u_suvm.lane_{g}", "u_lanes.core") for g in ("su_l0", "su_l1")]
        paths = negotiate(P, geo, k, [(sl(geo, k, f[1]), sl(geo, k, f[2]), f[3]) for f in flows])
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
                cap = (sf[2] - sf[1] - 2 * EDGE) * 5.0
                d = abs(P.centre(n)[0] - P.centre(m)[0]) + abs(P.centre(n)[1] - P.centre(m)[1])
                nb[n].append((m, cap, d))
                nb[m].append((n, cap, d))
    base = {e: v for e, v in P.load.items() if e[0] in nb}
    sfc = {(n, m): shared_face(P, n, m)[0] for n in nb for m, _, _ in nb[n]}
    hist = collections.Counter()
    pf = 0.5
    order = sorted(range(len(flows)), key=lambda i: -flows[i][2])
    for it in range(iters):
        load = collections.Counter(base)
        paths = [None] * len(flows)
        for i in order:
            a, b, w = flows[i]
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
                    nd = dd + (d + 50.0) * (1 + hist[e]) * (1 + pf * over * 10)
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
        caps = {tuple(sorted((n, m))): cap for n in nb for m, cap, _ in nb[n]}
        over = {e: load[e] / caps[e] for e in caps if load[e] > caps[e]}
        if not over:
            return paths
        for e, r in over.items():
            hist[e] += r - 1.0 + 0.2
        pf = min(pf * 1.3, 1e4)
    rep = {f"{x[5:]}|{y[5:]}": (round(base.get((x, y), 0)), round(load[(x, y)]), round(caps[(x, y)])) for x, y in caps}
    raise SystemExit(f"slice {geo['col_name'][k]}: negotiated routing left overflow {over}; base/load/cap {rep}; "
                     f"flows {[(f[0][5:], f[1][5:], f[2]) for f in flows]}")


def route(P, a, b, geo, k, width=1):
    """shortest abutting path a -> b inside slice k (BFS on partition adjacency, Manhattan tie-break)."""
    names = [n for n in P.parts if n.startswith(f"sl_{geo['col_name'][k]}_")]
    if a not in names or b not in names:
        raise SystemExit(f"route {a}->{b}")
    import heapq
    ca = P.centre
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
            cap = (sf[2] - sf[1] - 2 * EDGE) * 5.6
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
            inner = route(P, sl(geo, k, entry), sl(geo, k, rs_dst), geo, k, 2 * RSW)
            P.link("rsn", [cb_part(variant, near, 0, 0)] + inner, f"y_o{sfx(0, 0)}", f"rs_{fs}0", RSW,
                   src_leaf=f"u_t{sfx(0, 0)}.n_y", dst_leaf=f"u_f{'n' if fs == 'n' else 'rs'}.rs_{fs}_lo")
            P.link("rsf", [cb_part(variant, far, 0, 0)] + [cb_part(variant, near, 0, r) for r in (3, 2, 1, 0)] +
                   inner, f"y_o{sfx(0, 0)}", f"rs_{fs}1", RSW, src_leaf=f"u_t{sfx(0, 0)}.n_y",
                   dst_leaf=f"u_f{'n' if fs == 'n' else 'rs'}.rs_{fs}_hi")


# ====================================================================== west strip
WS = {  # name: (type, module, (w, h), (x, y), orient, hard)
    "io_serdes_2": ("phy_serdes_b", "ot_qfd_serdes_112g_x12_phy_s597", (WS_W, 2324.16), (0.0, 0.0), "R0", True),
    "io_serdes_1": ("phy_serdes", "ot_qfd_serdes_112g_x12_phy_s597", (WS_W, 2324.16), (0.0, 2324.16), "R0", True),
    "io_collective": ("coll", "qfd_collective_static_io_production", (COLL_W, 9097.92), (SUB_W, 4648.32), "R0",
                      False),
    "io_serdes": ("phy_serdes", "ot_qfd_serdes_112g_x12_phy_s597", (WS_W, 2324.16), (0.0, 13746.24), "MX", True),
    "ucie_kv": ("phy_ucie_kv", "ot_qkvd_ucie_x64_phy", (SUB_W, 777.6), (0.0, 9244.8), "R0", True),
    "glue": ("glue", "qfd_qc_wglue", (SUB_W, 1209.6), (0.0, 10022.4), "R0", False),
    "native59": ("native59", "qfd_native59_dv_headprep_obs1", (SUB_W, 518.4), (0.0, 11232.0), "R0", False),
    "tt_ctlm": ("tt_ctlm", "qfd_tt_ctlm_dv_hp13_rp", (SUB_W, 518.4), (0.0, 11750.4), "R0", False),
}
WS_CELLS = {"coll": 900000, "glue": 120000, "native59": 60000, "tt_ctlm": 190000}
GLUE_INSTS = ("d2d_rom", "sys_face", "embed_prov", "mu_ctxrx", "mu_dhobs", "rstseq_rom", "ckb_rom",
              "rs_bump", "bump_fwd_epoch", "bump_fwd_lrst")
COLL_INSTS = ("io_collective", "clk_rx", "ckdiv_coll_blk", "bump_pkg_s0", "bump_pkg_s1", "bump_die_ps", "ckb_core")


def build_west(P, census_blocks):
    for n, (tn, mod, wh, xy, orient, hard) in WS.items():
        cont = []
        if n == "glue":
            for i in GLUE_INSTS:
                cont.append({"inst": f"u_{i}", "module": census_blocks.get(i, i), "status": "reuse",
                             "note": "small W-strip block, merged into the glue partition (one clock/reset region)"})
        elif n == "io_collective":
            for i in COLL_INSTS:
                cont.append({"inst": f"u_{i}", "module": census_blocks.get(i, i), "status": "reuse",
                             "note": "collective + die clock receiver; COLLIO re-derivation into <= 1-mm plan "
                                     "partitions is open (COORD ruling 05:32)"})
            cont.append({"inst": "u_codec_pl_land", "module": "qfd_coll_codec_pl_land", "status": "new",
                         "note": "COLLIO carry-over (fl2/flx all FAIL, STEWARD-QK 06:26): landed register bank at the "
                                 "codec_pl clock-domain boundary (ot_entry_6 -> ot_entry_11 cross-clock setup -50 to "
                                 "-117 ps in P/S0); the crossing becomes landed + 1 cycle, scheduled statically"})
            cont.append({"inst": "u_io_ucie", "module": "ot_qfd_ucie_x64_phy", "status": "reuse",
                         "outline_um": [777.6, 777.6], "origin_um": [0.0, 4596.48],
                         "note": "planned hard core (TOPDOWN L1 amend): the coll UCIe PHY sits inside the coll "
                                 "partition, so its forwarded FDI clocks (lclk -> fdi_ck / fdi_rx_ck) stay inside "
                                 "one partition (a seam carries no clock)"})
        elif n == "tt_ctlm":
            cont.append({"inst": "u_tt_ctlm", "module": "qfd_hp13_cpub39_rp_alt", "status": "rework",
                         "outline_um": [501.0, 514.0], "kit": "claude/qtile-r-1023 qfd_hp13_cpub39_rp_{main,alt}",
                         "note": "HP13 ctlm re-pack: two regional clock roots per COORD ruling (rp5 CTS ck_hr FAIL)"})
        else:
            cont.append({"inst": f"u_{n}", "module": mod, "status": "reuse",
                         "note": "hard IP used as-is (die-edge PHY)" if hard else "reuse candidate"})
        note = f"west strip: {n}"
        if n == "io_collective":
            note += ("; COLLIO re-derivation OPEN (~900k est. > 400k L1 cap: >= 3 planned cores, one per face group "
                     "P/R/S0-S2). Carry-over defects: (1) M4 congestion hotspot on the PHY/E side (flx R GRT overflow "
                     "x471 y162; E face 1,217 pins at 92%) -> E/W seam pins on M6 only (no M4), ft_track_frac 0.25; "
                     "(2) codec_pl cross-clock ot_entry_6 -> ot_entry_11 -> landed register u_codec_pl_land")
        if tn not in P.types:
            P.add_type(tn, wh, mod if hard else f"qfd_qc_{tn}_part", cont, hard=hard,
                       note=note, cells=0 if hard else WS_CELLS.get(tn, 50000))
        P.add_part(n, tn, *xy, orient)


def census_links(P, geo, census, fp_pins, face_map):
    cname = geo["col_name"]
    col_of = {f"dvs_{n}": k for k, n in enumerate(cname)}
    face_reg = {"w": {"W": "fw", "E": "fe"}, "e": {"W": "fe", "E": "fw"}}
    brect = {b["inst"]: (b["x"], b["y"], b["w"], b["h"]) for b in census["blocks"]}
    l9_flip = collections.Counter()

    def part_of(inst, bus, pt=None):
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
            return sl(geo, k, {"W": "fw", "E": "fe"}[f])
        if inst in GLUE_INSTS:
            return "glue"
        if inst in COLL_INSTS or inst == "io_ucie":
            return "io_collective"
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
        s, d = part_of(g["src"], g["src_bus"], g["src_pt"]), part_of(g["dst"], g["dst_bus"], g["dst_pt"])
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
        loc = lambda p, i, b: b if p.startswith("sl_") or (p in WS and p not in ("glue", "io_collective")) \
            else f"{i}__{b}"  # noqa: E731
        sb, db = loc(s, g["src"], g["src_bus"]), loc(d, g["dst"], g["dst_bus"])
        path = ws_path(P, s, d)
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
    owner = {i: "io_collective" for i in COLL_INSTS}
    owner.update({i: "glue" for i in GLUE_INSTS})
    unplanned = [i for i in fsrc if owner.get(i, i) not in lane_from and owner.get(i, i) != "glue"]
    total = sum(g["bits"] for g in census["groups"])
    rep = {"census_bits": total, **{k: out[k] for k in sorted(out)},
           "accounted": sum(out.values()), "unaccounted": total - sum(out.values()),
           "fault_sources": fsrc, "fault_sources_without_plan_lane": unplanned,
           "l9_face_flip_buses": getattr(P, "l9_flip", []), "cb_mismatches": bad[:20]}
    return rep


def ws_path(P, s, d):
    """W-strip / W5-slice paths (fixed by the strip order); abutting pairs go direct."""
    fw = "sl_W5_fw"
    S2 = ["io_serdes_2"] + S2_CB[VARIANT] + ["io_collective"]
    table = {("io_serdes_2", "io_collective"): S2,
             ("native59", fw): ["native59", "io_collective", fw],
             ("tt_ctlm", fw): ["tt_ctlm", "io_collective", fw],
             ("glue", "tt_ctlm"): ["glue", "native59", "tt_ctlm"],
             ("glue", fw): ["glue", "io_collective", fw]}
    for (a, b), p in table.items():
        if (s, d) == (a, b):
            return list(p)
        if (s, d) == (b, a):
            return list(reversed(p))
    shared_face(P, s, d)
    return [s, d]


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
            P.link("flte", [root, "io_collective"], "flt_wo", "sl_flt_i", 1, kind="ctl",
                   src_leaf="u_pstn.flt_o", dst_leaf="u_io_collective.fault_sl")
    P.link("fltc", ["io_collective", "glue"], "flt_o", "coll_flt_i", 1, kind="ctl",
           src_leaf="u_io_collective.fault_or", dst_leaf="u_sys_face.obs_fault_coll")
    P.link("fltn", ["native59", "glue"], "flt_o", "n59_flt_i", 1, kind="ctl",
           src_leaf="u_native59.fault", dst_leaf="u_sys_face.obs_fault_n59")
    P.link("fltt", ["tt_ctlm", "native59", "glue"], "flt_o", "ctlm_flt_i", 1, kind="ctl",
           src_leaf="u_tt_ctlm.cf", dst_leaf="u_sys_face.obs_fault_ctlm")


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
        bus = pr["src"]["bus"] if pr["src"]["part"] == ll else pr["dst"]["bus"]
        mm = re.search(r"(\d)(\d)$", bus)
        j = 0
        if mm:
            j = (int(mm.group(1)) if f in "NS" else int(mm.group(2))) % 2
        groups[j].append(pr)
    return [(bounds[j], groups[j]) for j in range(2) if groups[j]]


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
                  "layers": (["M6"] if "io_collective" in (a, b) else ["M6", "M4"]) if f in "EW" else ["M7", "M5"]}
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
            cur = (slo + EDGE) if not flip else (shi - EDGE)
            for pr in sp:
                L = qlen(pr["width"] + 1, dens, pr["layers"], cur, flip)
                if not flip:
                    win = [round(cur, 4), round(cur + L, 4)]
                    cur += L + GAP
                else:
                    win = [round(cur - L, 4), round(cur, 4)]
                    cur -= L + GAP
                    pr["order"] = "lsb_high"
                pr["window_um"] = win
            if (not flip and cur - GAP > shi - EDGE + 1e-6) or (flip and cur + GAP < slo + EDGE - 1e-6):
                raise SystemExit(f"face {a}/{b} ({f}) segment {slo:.1f}-{shi:.1f} overfull: " +
                                 ", ".join(f"{pr['id']}:{pr['width']}" for pr in sp))
        del ref_lo, ref_hi
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
        for k in ("face", "window_um", "layers", "order"):
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
    return ports, lanes


def ft_fracs(P):
    """sparse soft partitions give more of their M4-M7 tracks to feedthroughs (G0 cut model default 0.25)."""
    for tn, t in P.types.items():
        if t.get("hard") or tn == "coll":
            continue
        w, h = t["outline_um"]
        cells = P.cells.get(tn) or 0
        fill = cells * CELL_UM2 / UTIL / (w * h)
        if fill < 0.25:
            t["ft_track_frac"] = 0.4
            t["note"] = (t.get("note", "") + f"; est. std-cell fill {fill:.2f} at util {UTIL}: 40% of M4-M7 to ft").lstrip("; ")


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
    su_split = json.loads(Path(a.su_split).read_text())["su_split_bits"]
    cblocks = {b["inst"]: b["master"] for b in census["blocks"]}
    P = Plan()
    P.cov = collections.defaultdict(list)
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
    slice_internal_links(P, geo, record, su_split)
    face_map = json.loads(Path(a.slice_face_map).read_text())
    dropped = census_links(P, geo, census, fp_pins, face_map)
    fault_links(P, a.variant, geo)
    cov = coverage(P, census)
    ports, lanes = materialize(P)
    merged = merge_types(P)
    bind_leaves(P)
    ft_fracs(P)
    chans = [{"rect_um": [0.0, 4648.32, SUB_W, 9244.8],
              "reason": "west-strip edge column below ucie_kv: the strip width is set by the serdes PHY depth "
                        "(1563.84 um); coll (786.24 wide) is taller than the edge-column content. PHY bump/decap/ESD "
                        "field, no logic"},
             {"rect_um": [0.0, 12268.8, SUB_W, 13746.24],
              "reason": "west-strip edge column above tt_ctlm: same strip-depth reason; decap"},
             {"rect_um": [0.0, 16070.4, WS_W, H],
              "reason": f"west strip above serdes S3: IO content (16.07 mm tall) is shorter than the compute "
                        f"column ({H / 1000:.2f} mm); strip width = serdes PHY depth. Bump/decap field; spare for the "
                        f"KV-die UCIe second port if the TP8 pair needs it"}]
    plan = {
        "schema": "opentallas.die_plan.v1",
        "note": f"PLAN-QCv2 2026-10-23 variant {a.variant}: Qwen compute die, plan-first (TOPDOWN-PLAN). Generated "
                "by physical/die_plan/qwen_compute/gen_plan.py from the as-built connectivity (FT-TOOL census, "
                "r50/r56 die), the slice landed-parent record (region census) and the A0 rpf geometry.",
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
        "partitions": [{"name": n, "type": p["type"], "origin_um": list(p["origin"]), "orient": p["orient"]}
                       for n, p in P.parts.items()],
        "ports": ports, "lanes": lanes,
        "clock": {"source": {"part": "io_collective", "bus": "clk_rx"}, "insertion_ps": 250, "insertion_tol_ps": 40,
                  "neighbour_skew_ps": 80, "face_xing": "budgeted",
                  "spine": {"layers": ["M8", "M9"], "root_um": [round(W / 2, 2), round(y_sl + SLH / 2, 2)],
                            "topology": "htree"}},
        "reset": {"source": {"part": "glue", "bus": "rstseq_rom"}, "sync_stages": 2, "data_reset": False,
                  "epoch_bit": True, "release": "counted"},
        "budgets": {"face_pins_per_um": 6, "face_pin_layers": 2, "face_window_um": 10, "pin_track_max": 0.6,
                    "cut_ratio_max": 0.6, "cut_step_um": 250},
    }
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
             "ports": len(ports), "lanes": len(lanes),
             "die_um": [round(W, 2), round(H, 2)], "die_mm2": round(W * H / 1e6, 1),
             "content_status_per_instance": dict(st),
             "max_cells_type": max(((v["cells"] or 0, k) for k, v in cells.items())),
             "cells_per_type": cells,
             "internal_bits_absorbed": dict(P.internal_bits),
             "cell_estimate_method": f"A0 = {A0_CELLS} cells (NL rpf synth_stat incl. 10 ROM leaf macros); other "
                                     f"leaves = outline area x {UTIL} / {CELL_UM2} um2 per cell (A0 calibration); "
                                     "soft slice glue / W-strip blocks = per-region guesses (SOFT_CELLS/WS_CELLS)",
             "census_coverage": cov,
             "census_dropped_bits": {"|".join(map(str, k)): v for k, v in sorted(dropped.items())}}
    Path(a.out).with_name("plan_notes.json").write_text(json.dumps(notes, indent=1) + "\n")
    print(json.dumps({k: v for k, v in notes.items() if k not in ("census_dropped_bits", "cells_per_type")}))


if __name__ == "__main__":
    main()
