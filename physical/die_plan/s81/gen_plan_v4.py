#!/usr/bin/env python3
"""PLAN-S81v2: S81 (DeepSeek ROM, 72-frame MU release) die plan v2 on a die lattice (TOPDOWN-PLAN, owner 10-23).

v2 vs v1 (COORD 04:46 + GEOM-REVIEW2 G1 04:47 on @0a79ca1ae):
  * ONE lattice for the whole die: cell = frame band 1442.88 x 1226.88 (167 x 142 grid of 8.64).  22 x 20 cells.
    Every partition is one cell (or a few cells for the hard HBM PHY and the units/serdes that need them).
  * Centre = a regular grid: slices are N-S chains of 1-cell segments (lep halves 2 x 8 / 2 x 7), svc 2 x 8 cells,
    cte row (ctrl pair + etap pair per svc column), irg columns, HBM PHY at the S edge, units + serdes at the N edge.
  * No lane columns: arrays abut the slices; W<->centre lanes run straight E-W through slice segments and frame b0
    bands as feedthrough (ft slots), Manhattan with <= 2 bends (router enumerates I/L/Z routes only).
  * Mirror symmetry: E array / E centre half are MY copies of the W ones; frames are MX (r0 band on top) / R180.
    PLAN-TOOL @764076fe6 symmetric tracks make mirrored copies ONE type; pins are declared on the TYPE.
  * No tie-offs: frame lk -> type parameter LK (per chain position), slice sid -> counted ID ring (seqhost -> slices
    -> seqhost, carries the fault OR), svc sid -> counted ID ring (seqhost -> rsv), slice ch_b -> parameter, slice bi
    -> BI_EN parameter (port only where a real PV source exists), rt padding -> N_RT parameter (one 70-b rt bus per
    frame), unit straps -> type parameters, frame chain-end xo -> XO_EN 0.
Inputs (read-only): cap30 gen-main plan.json (blocks + data links), FT census lanes tsv (ctl groups).
Output: OUT/die_plan.json + OUT/v2_stats.json + OUT/instance_map.json.
"""
import argparse
import shutil
import os
import sys
import collections
import csv
import json
import math
import re
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
from tools.die_plan.schema import pg_blocked   # noqa: E402  (PLAN-TOOL PG bands, same rule as pin_positions)

G = 8.64
MINW = 17.28                       # minimum port window (um): narrow ID-ring/ctl ports need tracks off the PG bands
PX, PY = 167 * G, 142 * G          # 1442.88 x 1226.88 cell (= frame band)
X0 = 12 * G                        # 103.68 seal ring
NC, NR = 22, 20
DIE_W = NC * PX + 2 * X0
DIE_H = NR * PY + 2 * X0
# OWNER DECISION 12 / METHODOLOGY rulings 9.3 + 9.4 (S81/DEC12 2026-10-24): every partition signal is on M4-M7, so the
# one-cycle signal hop is the 405-um M4-M7 figure for the WHOLE die (was REACH 1500 = an M8/M9 over-the-top hop) and ft
# stations sit at most 405 um apart in every type (was FT_STATION_MAX 750 for the non-S81-CORES keys).  Station counts
# keep the generator's 0.98 placement factor (<= 397 um planned spacing) against the exact 405-um check (no 0.9 G0C
# margin: budgets.reach_margin 1.0).  M8/M9 carry only the die clock spine, die reset and PG (die_use: no ft_reserved).
REACH = 405.0
FT_KIT_REACH_UM = 405.0  # measured M4-M7 kit reach at 833ps; M8/M9 are reserved die resources
FT_STATION_MAX = 405.0     # budgets.ft_station_max_um (tools/die_plan R3, ruling 9.4 ceiling)
UNIFORM_SEG = True
SNAP = 0.192
TR = dict(M3=(0.036, 0.009), M4=(0.048, 0.024), M5=(0.048, 0.024), M6=(0.064, 0.032), M7=(0.064, 0.032),
          M8=(0.080, 0.040), M9=(0.080, 0.040))   # pitch, offset (PLAN-TOOL symmetric tracks)
# COORD S81 ruling (1)(b) 10-23 07:43: the svc fold faces (svc_2k N | svc_2k+1 S, ~9.0 kb on a 1.44-mm face) take a
# third pin layer from the reserved die budget via partition_types.<t>.face_layers (PLAN-TOOL @7f9f10e1d).  The fold
# face is N/S, and the tool requires a vertical pin layer there (M8 is H -> 'layer M8 is H, a S face needs V'), so the
# grant is M9, the vertical die layer (die M9 PG bands avoided; the kit routes M2-M9 and obstructs the die M8/M9 bands).
# DEC12 (ruling 9.3): the M9 fold grant is withdrawn -- no signal pin on M8/M9.  The fold rung (svc_2k N | svc_2k+1 S,
# up to 9.3 kb on the 1442.88-um face = 6.5 pins/um) does not fit the two vertical partition layers M7/M5 at the 6/um
# face budget, and the fold face is fixed at one lattice cell (every svc_2k must abut the HBM PHY row, so a pair is one
# column).  The third pin layer therefore comes from the partition's own vertical layers: M3 (V, pitch 36 nm; 3.1
# pins/um/layer on the worst fold = ~11% of the M3 tracks; the pins land on the svc pin registers at the face).
# S81_V4_FOLDGRANT=<layer> overrides (e.g. M9 = the pre-DEC12 grant, a G0 ERROR m89_signals; '' = no grant).
FOLD_GRANT = [x for x in os.environ.get("S81_V4_FOLDGRANT", "").split(",") if x]
STATS_V4 = {}
INSTANCE_KEPT = []   # DEC12: types renamed back to their reference name by instance identity
XO_JOINED = []     # v4.6: xo lanes that share the x lane window (S81-P9)


def face_layers(pa, pb, face):
    """pin layers of the shared face of partitions pa|pb crossed in die direction `face` (die frame)."""
    base = ["M6", "M4"] if face in "EW" else ["M7", "M5"]
    if face in "NS" and pa.kind == "svc" and pb.kind == "svc" and getattr(pa, "group", None) and \
            pa.group == pb.group:
        return base + FOLD_GRANT
    return base
ALLOC_PPU = 4.6                    # pins/um inside a window (G0 limit 6/um in any 10-um window)
FACE_MAX = 0.6 * 6.0               # pins/um averaged over a cell face (COORD: face <= 0.6)
EDGE = 6.0
GAP = 2.0
XW, RW = 1104, 70
# v4.8 (S81-P9-R8EQ, BINDER4 b3r8 UNPLANNED 1,347 b): a slice's lep (LP partition) owns its SerDes rx/tx AND the MU /
# host-plane buses to seqhost (mu_rt / mu_c / mu_rc, f_host / f_ks / f_lf, t_host / t_kd: u_lep ports in the bound top);
# v4.7 put the latter on the hub C, so the plan lanes unit__*_C__seqhost carried nothing and 1,032 b crossed unplanned.
LP_BUS_RE = r"((rx|tx)\d|mu_(rt|c|rc)|f_(host|ks|lf)|t_(host|kd))$"
LP_BUS_RE_V47 = r"(rx|tx)\d$"
BOUND_SUPP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "inputs", "bound_supplement_v48.json")
OPP = dict(N="S", S="N", E="W", W="E")
STEP = dict(E=(1, 0), W=(-1, 0), N=(0, 1), S=(0, -1))
# S81-P6 10-23 (COORD: census from the band RTL): frame-internal lane widths per master = the band-to-band bits of the
# banded seam kits (frame_seam_pipe.py: band seams at plan width), via inputs/frame_band_census.json
# (frame_band_census.py).  The v1 constant (1263 / 1229 / 384 / 141) had no basis and r1 -> r0 was 120-126 b short.
FRAME_BAND_CENSUS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "inputs", "frame_band_census.json")


# S81-KITS-RTLC 10-24 (owner: register every partition pin, in RTL): the band pass-through stations (dsfd_qbank_N / _S,
# dsfd_rstg, ot_s81_sstn_payload536 / base566) gained an input pin register (+1 edge per station).  Max stations on a
# band path ending at each band-to-band bus (tools/s81_dv/frame_band_stations.py on the band RTL; per-field breakdown in
# results/rtl/s81_kits_rtlc_1024/frame_band_stations.json): priced as fixed cycles of the fi lane carrying that bus.
FRAME_BAND_STATION_EDGES = {"h9": {("r0", "r1"): 3, ("r1", "r0"): 3, ("r1", "r2"): 3, ("r2", "r1"): 3},
                            "h10": {("r0", "r1"): 4, ("r1", "r0"): 3, ("r1", "r2"): 3, ("r2", "r1"): 3}}


def frame_internal(h):
    m = json.load(open(FRAME_BAND_CENSUS))["masters"][h]
    return [(k.split("->")[0], k.split("->")[1], w) for k, w in sorted(m.items())]


# S81-P7 10-23 (COORD G3 band blockers): frame-band contents bound to the plan buses.  The band RTL
# rtl/dsrom_sys/s81_dv/frame_lp/plan/col_<M>_l4_lp_plan.sv (tools/s81_dv/frame_band_plan.py) has exactly the plan
# ports (frame_int_*, x/xo/ret, clk, rst_n; LK parameter; xk = clk; registered lpr_root ft), and the band macros /
# hard children sit at the positions of inputs/frame_band_macros.json (tools/s81_dv/frame_band_macros.py).
FRAME_BAND_MACROS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "inputs", "frame_band_macros.json")


def frame_contents(contents, buses):
    if len(contents) != 1 or not re.match(r"col_h(9|10)_l4_lp\.r\d$", contents[0]["module"]):
        return contents
    c = dict(contents[0])
    m, b = c["module"].split(".")
    k = int(b[1:])
    names = {x["name"] for x in buses}
    xo = "xo_o0" in names
    c["module"] = "%s_r%d%s" % (m, k, "_nx" if (k == 0 and not xo) else "")
    bind = {"clk": "clk"}
    if k == 0:
        bind.update(rst_n="rst_n", x_i0="bus:" + ("x_i0" if "x_i0" in names else "xo_i0"), ret_o0="bus:ret_o0")
        if xo:
            bind["xo_o0"] = "bus:xo_o0"
    for n in sorted(names):
        if n.startswith("frame_int_"):
            bind[n] = "bus:" + n
    c["bind"] = bind
    c.pop("status", None)
    c["status"] = "new"
    # LK: the x-lane landing strap of every frame = E 2 (the framed seam bench value); XO_EN is the module variant
    c["params"] = {"LK": "{4{3'd2}}"} if k == 0 else None
    if c["params"] is None:
        c.pop("params")
    return [c]


def FRAME_SOURCES(contents):
    if len(contents) != 1 or not re.match(r"col_h(9|10)_l4_lp\.r\d$", contents[0]["module"]):
        return None
    # the KIT form of the band contents (hard children without #() overrides, as the frame kits) + the soft leaves
    # of the frame kits (physical/ref_tile/s81frame_col_h9_vgch_b*/spec.json sources) + the plan seam primitives
    return ["rtl/common/landed_parent/ot_pl_land.sv",   # ot_reset_sync: the tool adds it
            "rtl/common/landed_parent/ot_pl_land_field_copies.sv", "rtl/common/landed_parent/ot_pl_land_reset_forest.sv",
            "rtl/common/landed_parent/ot_pl_seam.sv", "rtl/dsrom_sys/s81_glue/ot_s81_rly.sv",
            "rtl/dsrom_sys/s81_dv/frame/dsfd_rly_frame_exact.sv"] + \
        ["rtl/dsrom_sys/s81_glue/dsfd_rly_masters%s.sv" % x for x in ("", "_266ew", "_536", "_c26l", "_gen18", "_v16")] + \
        ["rtl/dsrom_sys/s81_dv/frame_lp/kit/dsfd_bf_col_kit.sv",
         "physical/asap7_memory_macros_v2/ot_rom_4096x72_m8/ot_rom_4096x72_m8_bb.v",
         "rtl/dsrom_sys/s81_dv/frame_lp/plan/%s_plan_kit.sv" % contents[0]["module"].split(".")[0]]


CORE_TRACK_OFFSET = [0.108, 0.012]
CORE_PINS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "inputs", "core_pins")
CORE_OFFSET_LOG = {}


def core_track_offset(e):
    """S81-P9 10-23 (COORD 19:36): sub-lattice track offset of one frame core, ORIENT-AWARE.  CORE-KS's [0.108, 0.012]
    puts R0 cores on the kit tracks; a mirrored core (MY flips x, MX flips y) lands its pins at outline - x, which
    is on track only for an offset that matches the outline residue.  Pick, per core, the (dx, dy) on the 0.012-um
    sub-grid (< one base lattice) with the fewest off-track M2-M7 pins in the type frame (die-frame M2/M3 of mirrored
    partitions are skipped by G0 like M1); ties keep CORE_TRACK_OFFSET.  Shapes are LEF pin centres (CORE-KS table)."""
    import sys as _s
    _s.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "tools", "die_plan"))
    import schema as _S
    L = {x["name"]: x for x in _S.ASAP7_LAYERS}
    f = os.path.join(CORE_PINS_DIR, e["module"] + ".json")
    if not os.path.exists(f):
        return CORE_TRACK_OFFSET
    js = json.load(open(f)); pins = js.get("pins", js) if isinstance(js, dict) else js
    w, h = e["size_um"]; o = e["orient"]; ox, oy = e["origin_um"]

    def pt(x, y):
        return {"R0": (x, y), "MX": (x, h - y), "MY": (w - x, y), "R180": (w - x, h - y)}[o]

    def off(c, l):
        k = (c - l["offset_um"]) / l["pitch_um"]
        return abs(k - round(k)) > 1e-4
    V = [(pt(q["x"], q["y"])[0], L[q["layer"]]) for q in pins if q["layer"] in L and q["layer"] != "M1" and L[q["layer"]]["dir"] == "V"]
    H = [(pt(q["x"], q["y"])[1], L[q["layer"]]) for q in pins if q["layer"] in L and q["layer"] != "M1" and L[q["layer"]]["dir"] == "H"]
    cand = [round(0.012 * k, 3) for k in range(0, 24)]

    def best(P, c0, base):
        sc = {d: sum(off(base + d + c, l) for c, l in P) for d in cand}
        m = min(sc.values())
        return (c0 if sc[c0] == m else min(d for d in cand if sc[d] == m)), m
    dx, bx = best(V, CORE_TRACK_OFFSET[0], ox)
    dy, by = best(H, CORE_TRACK_OFFSET[1], oy)
    CORE_OFFSET_LOG[(e["inst"], e["module"], o)] = (dx, dy, bx, by)
    return [dx, dy]


def frame_hard_cores(contents, buses):
    """band macros / hardened children of a frame type at their plan sites (lattice origins, frame_band_macros.json)"""
    if len(contents) != 1 or not re.match(r"col_h(9|10)_l4_lp\.r\d$", contents[0]["module"]):
        return []
    m, b = contents[0]["module"].split(".")
    mac = json.load(open(FRAME_BAND_MACROS))["masters"][m.replace("_l4_lp", "")][b]
    nx = b == "r0" and "xo_o0" not in {x["name"] for x in buses}
    # the chain-end variant col_<M>_l4_lp_r0_nx is r0 without the x-forward stations u_xo<j> (no xo bus)
    return [dict(inst=e["inst"], module=e["module"], lef=e["lef"], **({"lib": e["lib"]} if e["lib"] else {}),
                 origin_um=e["origin_um"], outline_um=e["size_um"], orient=e["orient"],
                 # S81-P9 10-23 (COORD 19:36, CORE-KS): core signal pins sit on the M4/M5 0.012 sub-grid (kit tracks
                 # 0.024): shift every frame core by the sub-lattice track offset + list its pins for the G0 track check
                 track_offset_um=core_track_offset(e), pins_file=f"inputs/core_pins/{e['module']}.json") for e in mac
            if not re.match(r"u_r0\.u_xo\d+$", e["inst"])]   # v4.6: u_xo -> soft u_y_xo<j>_0/_1 chain (S81-P9-RTL)


def frame_early_clock(ty):
    """Deliver slow frame cores early by their selected TT internal clock latency.

    This uses the CP2 core-tap contract: effective core flop arrival remains the
    common 250 ps target, with no data-cycle change. ROMs have clk->q arcs, not
    internal clock-tree insertion, and stay on the ordinary grid.
    """
    from tools.die_plan.cores import clock_pins, resolve
    from tools.die_plan.schema import tap_clear
    ck = ty["clock"]
    taps = []
    for c in ty.get("hard_cores", []):
        if c.get("module") not in ("ot_v41_rom_elem_q_qxpq_w10", "ot_v41_bf_col"):
            continue
        view_root = os.environ.get("S81_CORE_VIEW_ROOT")
        if not c.get("lib") or not resolve(c["lib"], view_root).is_file():
            raise ValueError("selected frame core has no readable clock timing library: " + c["inst"])
        pins = clock_pins(c, root=view_root)
        if not pins:
            raise ValueError("selected frame core has no readable clock timing view: " + c["inst"])
        for pin, timing in pins.items():
            latency = timing["rise"]
            if latency <= 250:
                continue
            x, y = c["origin_um"]
            cw, ch = c["outline_um"]
            # A dedicated tap in the adjacent macro-free channel; tap_clear also
            # keeps it clear of neighbouring cores and other dedicated taps.
            xy = tap_clear(ty, x + cw / 2, y - 8.64,
                           [t["xy"] for t in taps], clear=4.32)
            taps.append(dict(name=c["inst"] + "." + pin, kind="core", xy=list(xy),
                             insertion_ps=round(latency, 5),
                             budget_owner=c["lib"],
                             note="CP2 early core tap; selected TT max_clock_tree_path_rise"))
    if taps:
        ck.update(core_taps="early", taps=taps)
    return ty


# ---- S81-P9-HC 10-23 (COORD G0C): hard_cores[] of the NON-frame types over the 400k-cell cap -------------------------
# One entry per RTL child instance that has a closed physical view (LEF), keyed like cells_core_plan's partition kinds.
# cells: the cells_core_plan count of that child (plan_core = the planned core it belongs to; bucket=True: the planned
# core's count covers several children, carried once on its first member).  gaps[]: children with NO closed view (never
# invented): they stay soft until a view exists.  A type gets hard_cores[] only when its residual soft cells
# (type cells - hard-core cells) are <= HC_CELLS_MAX: a partial core list on a type still far over the cap would mark it
# G0C clean (and G3-eligible) while it cannot be built; such types keep the G0C error and are listed in hard_core_gaps.json.
HC_CELLS_MAX = 400_000
HC_GAP_UM = 13.8          # facing core-core gap (GEOM rule)
HC_EDGE_UM = 4 * 8.64     # core keep-off from the type outline (face flops / ft stations / tap channel)
_RT = "physical/ref_tile/%s/views/%s/%s.lef"


def _rt(kit, mod):
    return _RT % (kit, mod, mod)


_ARCH_SRC = "/home/ubuntu/closed_archive/%s/%s/run/record/views/%s/%s.lef.zst"
# S81-P9: the closed-archive views are imported into the repo (physical/s81_die_views/closed_import/<m>/, see PROVENANCE)
_ARCH = "physical/s81_die_views/closed_import/%s/%.0s%.0s%s.lef"
# S81/LEAFPLAN 10-24 (S81/KITS r6 geom FAIL ot_s81sl_eg_c): eg re-pinned (cores/leaf/repin.py ot_s81sl_eg): clk / rst_n
# from the W-top corner to the S-face centre, every face spread evenly (S peak 26.5 -> 0.7 pins/um); same ports, same size
_C_COMMON = [dict(inst="u_c.u_eg", module="ot_s81sl_eg", lef="physical/die_plan/s81/cores/eg/lef/ot_s81sl_eg_c.lef",
                  pins_file="inputs/core_pins/ot_s81sl_eg_c.json", cells=261681, plan_core="eg"),
             dict(inst="u_c.u_xf", module="ot_s81dv_xfin", lef=_rt("s81dv_xfin", "ot_s81dv_xfin"), cells=135954,
                  plan_core="xf_cap"),
             dict(inst="u_c.u_cap", module="ot_s81sl_capc5r", lef=_rt("s81sl_capc5r", "ot_s81sl_capc5r"), cells=22959,
                  plan_core="xf_cap")]
_C_GAPS = [dict(inst="u_c.u_xg", module="ot_s81sl_xg", cells=174928, plan_core="xg_xr",
                why="stand-in view only (physical/ref_tile/s81dv_slice_lp_k8a|b/standin_views/ot_s81sl_xg, 648x561.6): "
                    "no closed view")]
_GU = "physical/ref_tile/dsdv_gunit_%s/views/dsdv_gunit_%s/dsdv_gunit_%s.lef"
# S81-CORES: the GEOM-REVIEW8-passed hcore grid (CORE-S81-SVC cores_svc.json placement, 8 x 8, pitch 172.8 x 276.48)
_SVC_HC = [dict(inst="u_rsv.u_att.u_eng.g_t[%d].g_ts.u_t.u_hc.g_h[%d].u_c" % (i // 16, i % 16),
                origin_um=(round(34.56 + 172.8 * (i % 8), 4), [34.56, 311.04, 587.52, 864.0, 1321.92, 1598.4, 1874.88, 2151.36][i // 8]))
           for i in range(64)]
NONFRAME_HC = {
    # S81-KITS-RTLC 10-24 (ruling c): explicit hub-C placement = the former shelf rows (cap | xr | eg) with xfin moved
    # under eg (centred, 17.28 um gap): the xfin -> eg copy link (core_conns C:xrt*: xf e_* N face -> eg i_* S face)
    # faces its partner in every type; y-mirror only (the shelf packer never chose an x mirror for the hub C types)
    "C:xrt1": dict(cores=_C_COMMON + [dict(inst="u_c.u_xr", module="ot_s81sl_xrt1", plan_core="xg_xr", cells=67849,
                                           lef=_rt("s81sl_xrt1", "ot_s81sl_xrt1"))], gaps=_C_GAPS,
                   place={"u_c.u_cap": (34.56, 34.56), "u_c.u_xr": (388.8, 34.56), "u_c.u_xf": (751.68, 34.56),
                          "u_c.u_eg": (717.12, 233.28)}, mirrors=((False, False), (False, True))),
    "C:xrt3": dict(cores=_C_COMMON + [dict(inst="u_c.u_xr", module="ot_s81sl_xrt3", plan_core="xg_xr", cells=78456,
                                           lef=_rt("s81sl_xrt3_b", "ot_s81sl_xrt3"))], gaps=_C_GAPS,
                   place={"u_c.u_cap": (34.56, 34.56), "u_c.u_xr": (388.8, 34.56), "u_c.u_xf": (1010.88, 34.56),
                          "u_c.u_eg": (976.32, 233.28)}, mirrors=((False, False), (False, True))),
    "gunit": dict(cores=[dict(inst="u_gunit.u_" + m, module="dsdv_gunit_" + m, lef=_GU % (m, m, m), plan_core=pc,
                              cells=c, bucket=c is not None and pc != "l5f")
                         for m, pc, c in [("l0", "l0_l1_l2", 8213 + 110419 + 9853 + 43954 + 8215),
                                          ("l0r", "l0_l1_l2", None), ("l1", "l0_l1_l2", None),
                                          ("l1c", "l0_l1_l2", None), ("l2", "l0_l1_l2", None),
                                          ("l3", "l3_l4", 40887 + 81348 + 73342), ("l4", "l3_l4", None),
                                          ("l4r", "l3_l4", None), ("l5f", "l5f", 97736), ("l5", None, None)]],
                  gaps=[dict(inst="u_gunit.g_l1f[%d].u_l1f" % q, module="dsdv_gunit_l1f", cells=None, plan_core=None,
                             why="no closed view of dsdv_gunit_l1f (views exist only for the band split "
                                 "dsdv_gunit_l1f_ba0/ba1 of dsdv_gunit_l1f_band, not instantiated by dsdv_gunit); "
                                 "cells not in the plan basis") for q in range(4)]),
    "bk_sel": dict(cores=[dict(inst="u_bk_sel.u_sel.u_c", module="dsdv_bksel_c", lef=_rt("s81dvbk_selc2", "dsdv_bksel_c"),
                               cells=260094, plan_core="bksel_c_pa")] +
                   [dict(inst="u_bk_sel.u_sel.g_q[%d].u_q" % q, module="dsdv_bksel_q",
                         lef=_rt("s81dvbk_sq_hq3", "dsdv_bksel_q"), cells=113262,
                         plan_core="bksel_q01" if q < 2 else "bksel_q23") for q in range(4)] +
                   [dict(inst="u_bk_sel.u_sel.u_g", module="dsdv_bk_g", lef=_rt("s81dvbk_g2", "dsdv_bk_g"), cells=25144,
                         plan_core="bkg_tx_vmux"),
                    dict(inst="u_bk_sel.u_tx", module="dsdv_idx_tx_n32", cells=31602, plan_core="bkg_tx_vmux",
                         lef=_ARCH % ("dsdv_idx_tx_n32", "s81dv_idxtxn32x2-x2-b642addfb", "dsdv_idx_tx_n32",
                                      "dsdv_idx_tx_n32"))],
                   gaps=[dict(inst="u_bk_sel.u_vm", module="dsdv_idx_vmux", cells=3547, plan_core="bkg_tx_vmux",
                              why="views are of dsdv_idx_vmux_n32, a different module; flattened (small)")]),
    # S81-CORES 10-24 (GEOM-REVIEW8 21:04 leaf FAIL re-plan): vp is NOT one hard core any more.  Its closed view
    # (closed_archive s81sl_vp9_fb, 734.4 x 864, 2,413 pins) is lost with the old coordinator host, and its pin faces
    # (vn link on vp E, vs link on vp W, both full height) cannot face both partners in the 1442.88 x 1226.88 leaf.  vp
    # is flattened into the leaf exactly as its own cluster kit builds it (OT_S81SL_VP_HARD, RTL unchanged): its 16
    # closed pin-registered hc_post lanes (s81sl_hcpl ot_dsrom_su_hcpost_lane_pr) and its 2 leaf-store SRAM macros are
    # leaf hard cores, its 36,056-cell own logic (pin flops, sequencer) is leaf soft glue.  vs and vq are re-pinned
    # (cores/leaf/repin.py: same module / ports, pins moved to the faces that face their partners; stub LEFs until the
    # re-pinned views close); vn, ve (r5 closed), vsw, rxsf, rxsb are the closed views unchanged.  Placement (type frame,
    # bus-side variant; the S-bus types take the y mirror, cores mirrored with it):
    #   left half (x <= 712.8): hc lanes 2 x 8 W column, vn on the E edge of the half (vn W -> lanes / store), store SRAMs
    #   under vn's centre; right half (x >= 730.08): vq beside vn's y port (vn E -> vq W), vs E of vq, vsw E of vs
    #   (level), ve centred over vs (ve W / E faces both drop to vs N), rxsf / rxsb stacked under vs.
    #   No core covers the die-centre column x 712.8..730.08 (every E-W ft slot's 2-station midpoint) nor needs more
    #   than 122 um escape at the N-S slots' midline y 613.44: 0 ft stations added in every leaf type.
    "leaf": dict(cores=[dict(inst="u_lf.u_vp.g_ln[%d].u_l" % i, module="ot_dsrom_su_hcpost_lane_pr", cells=50540,
                             plan_core="vp_hcpl",
                             lef=_rt("s81sl_hcpl", "ot_dsrom_su_hcpost_lane_pr")) for i in range(16)] +
                       [dict(inst="u_lf.u_vp.u_b%d" % i, module="ot_sram_1r1w_512x128_m4_r2c2", cells=0,
                             plan_core="vp_store",
                             lef="physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/"
                                 "ot_sram_1r1w_512x128_m4_r2c2.lef") for i in range(2)] +
                       # S81/LEAFPLAN 10-24 (COORD C3: ve 468k > 400k cap, vn 385k at it): vn and ve split into two hard
                       # cores each (cores/leaf/split.py, plan pin tables + stub LEFs; RTL split = hand-off): vn = lanes
                       # 0..3 (u_a, h half 0) + lanes 4..7 (u_b, h half 1, chain tail, beat tree, p), stacked in vn's
                       # footprint; ve = sum (u_s: pack, chunk8 x 3, trees -> p) W of multiply (u_m: mul4, add8 -> o)
                       [dict(inst="u_lf.u_vn.u_a", module="ot_s81sl_vn_a", cells=183821, plan_core="vn",
                             lef="physical/die_plan/s81/cores/leaf/lef/ot_s81sl_vn_a.lef",
                             pins_file="inputs/core_pins/ot_s81sl_vn_a.json"),
                        dict(inst="u_lf.u_vn.u_b", module="ot_s81sl_vn_b", cells=191324, plan_core="vn",
                             lef="physical/die_plan/s81/cores/leaf/lef/ot_s81sl_vn_b.lef",
                             pins_file="inputs/core_pins/ot_s81sl_vn_b.json"),
                        dict(inst="u_lf.u_vs", module="ot_s81sl_vs", cells=117971, plan_core="vs_vsw",
                             lef="physical/die_plan/s81/cores/leaf/lef/ot_s81sl_vs_lfp.lef",
                             pins_file="inputs/core_pins/ot_s81sl_vs_lfp.json"),
                        dict(inst="u_lf.u_vsw", module="ot_s81sl_vsw", lef=_rt("s81sl_vsw", "ot_s81sl_vsw"),
                             cells=120703, plan_core="vs_vsw"),
                        dict(inst="u_lf.u_vq", module="ot_s81sl_vq", cells=46676, plan_core="vq_rx",
                             lef="physical/die_plan/s81/cores/leaf/lef/ot_s81sl_vq_lfp.lef",
                             pins_file="inputs/core_pins/ot_s81sl_vq_lfp.json"),
                        dict(inst="u_lf.u_rxsf", module="dsfd_su_t_rxsf", lef=_rt("s81su_rxsf_ref", "dsfd_su_t_rxsf"),
                             cells=82916, plan_core="vq_rx"),
                        dict(inst="u_lf.u_rxsb", module="dsfd_su_t_rxsb", lef=_rt("s81su_rxsb_ref", "dsfd_su_t_rxsb"),
                             cells=99597, plan_core="vq_rx"),
                        dict(inst="u_lf.u_ve.u_s", module="ot_s81sl_ve_s", cells=216331, plan_core="ve",
                             lef="physical/die_plan/s81/cores/leaf/lef/ot_s81sl_ve_s.lef",
                             pins_file="inputs/core_pins/ot_s81sl_ve_s.json"),
                        dict(inst="u_lf.u_ve.u_m", module="ot_s81sl_ve_m", cells=243948, plan_core="ve",
                             lef="physical/die_plan/s81/cores/leaf/lef/ot_s81sl_ve_m.lef",
                             pins_file="inputs/core_pins/ot_s81sl_ve_m.json")],
                 gaps=[],
                 # vp's own logic (36,056) + leaf glue stay soft: residual = total - hard
                 # base placement + per-type candidates: cores/leaf/alt_place.json (every hcpl lane box <= 300 um from vn;
                 # the 10-23 two-column lane block put lanes up to 592 um from vn -- GEOM review 10-24)
                 place={k_: tuple(v_) for k_, v_ in json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                                            "cores/leaf/alt_place.json")))["base"].items()},
                 alt_place_file="cores/leaf/alt_place.json",
                 # the leaf bus face picks the variant: N bus = as placed, S bus = y mirror (every core MX'd with it)
                 mirrors=((False, False), (False, True)), mirror_by_bus=True,
                 # S81/LEAFPLAN 10-24 (coordinator ruling (b)): x-mirrored PIN VARIANTS of vn / vq / vs (new core views,
                 # cores/leaf/xmirror.py: pins at x' = W - x snapped to the plan tracks; an MY orient cannot be placed).
                 # A candidate (alt_place.json "views") picks a view per core; every candidate is also tried x-mirrored
                 # as a whole (origins mirrored on the lattice, vn / vq / vs views swapped, the other cores R0: their
                 # partner faces are N/S (vsw) or both E and W toward vs (ve) or unchecked (hcpl lanes, store SRAMs);
                 # the face rule below rejects any mirrored candidate that turns a core port away from its partner)
                 # placement blocks (alt_place keys): the split vn / ve pairs move as one block, children at fixed
                 # offsets in the design frame (vn_b over vn_a, ve_m E of ve_s; 17.28 um facing gap)
                 blocks={"u_lf.u_vn": [("u_lf.u_vn.u_a", 0.0, 0.0), ("u_lf.u_vn.u_b", 0.0, 181.44)],
                         "u_lf.u_ve": [("u_lf.u_ve.u_s", 0.0, 0.0), ("u_lf.u_ve.u_m", 181.44, 0.0)]},
                 views={"xm": {**{"u_lf.%s.u_%s" % (b_, h_): dict(
                                  lef="physical/die_plan/s81/cores/leaf/lef/ot_s81sl_%s_%s_xm.lef" % (b_[2:], h_),
                                  pins_file="inputs/core_pins/ot_s81sl_%s_%s_xm.json" % (b_[2:], h_))
                                  for b_, hs_ in (("u_vn", "ab"), ("u_ve", "sm")) for h_ in hs_},
                               "u_lf.u_vq": dict(lef="physical/die_plan/s81/cores/leaf/lef/ot_s81sl_vq_xm.lef",
                                                 pins_file="inputs/core_pins/ot_s81sl_vq_xm.json"),
                               "u_lf.u_vs": dict(lef="physical/die_plan/s81/cores/leaf/lef/ot_s81sl_vs_xm.lef",
                                                 pins_file="inputs/core_pins/ot_s81sl_vs_xm.json")}},
                 xmirror_views="xm"),
    # S81-CORES 10-24: the attention engine as 64 ot_s81c_attn_hcore (CORE-S81-SVC: one head + its own hgrp_s HG1 PCOLP1
    # front end, every pin registered; tb_s81c_hgrp lockstep vs hgrp_s HG4 PASS every output every cycle, mutants caught;
    # GEOM-REVIEW8 PASS of this 8 x 8 grid, cores/svc/cores_svc.json; route gate record: TT -25.29 ps, re-close by the S81
    # lane WPRE 89c161bd5) + the 8 score-exchange half rows dsdv_svc_sx_hrow re-floorplanned 216x216 -> 138.24 x 164.16
    # (cores/leaf/repin.py, faces kept) into the centre band the grid leaves (y 1140.48..1308.12): the exchange's hop
    # geometry wants its leaf cluster at the slice centre (dsdv_svc_sx: 4 segments <= 335 um, NR = 1, zero added cycles).
    # Replaced soft cells: 64 hdp_s 183,981 + 16 hgrp_s local 30,272 + 8 hrow 51,397 = 12,670,312.
    "svc": dict(cores=[dict(inst=c_["inst"], module="ot_s81c_attn_hcore", cells=202789, plan_core="attn_hcore",
                            lef="physical/die_plan/s81/cores/svc/ot_s81c_attn_hcore.lef",
                            pins_file="inputs/core_pins/ot_s81c_attn_hcore.json") for c_ in _SVC_HC] +
                      [dict(inst="u_rsv.u_sx.g_r[%d].g_h[%d].u_hrow" % (r, b), module="dsdv_svc_sx_hrow", cells=51397,
                            lef="physical/die_plan/s81/cores/svc/lef/dsdv_svc_sx_hrow_c.lef", plan_core="sx_hrow_ab",
                            pins_file="inputs/core_pins/dsdv_svc_sx_hrow_c.json")
                       for r in range(4) for b in range(2)],
                gaps=[],
                replaces=64 * 183981 + 16 * 30272 + 8 * 51397,
                # half rows at 43.2 + 172.8 k in the centre band; r0b0 at the 34.56 edge (svc_hi_rs t1 ft1 N->W escape <= 61 um)
                place=dict([(c_["inst"], tuple(c_["origin_um"])) for c_ in _SVC_HC] +
                           [("u_rsv.u_sx.g_r[%d].g_h[%d].u_hrow" % (r, b), (round(43.2 + 172.8 * (2 * r + b), 4) if r or b else 34.56, 1140.48))
                            for r in range(4) for b in range(2)]),
                mirrors=((False, False),)),
    # S81-CORES 10-24: dsdv_eng_rr -> 3 hard cores E/H0/H1 (CORE-S81-ENG dsdv_eng_rr_split.sv, lockstep vs the monolith
    # PASS, 0 cycles added; GEOM-REVIEW8 E/H0/H1 PASS); origins = cores/eng/cores_eng.json placement
    "eng": dict(cores=[dict(inst="u_eng.u_e", module="dsdv_eng_rr_e", cells=96256, plan_core="eng_rr_e",
                            lef="physical/die_plan/s81/cores/eng/lef/dsdv_eng_rr_e.lef"),
                       dict(inst="u_eng.u_h0", module="dsdv_eng_rr_h0", cells=175659, plan_core="eng_rr_h0",
                            lef="physical/die_plan/s81/cores/eng/lef/dsdv_eng_rr_h0.lef"),
                       dict(inst="u_eng.u_h1", module="dsdv_eng_rr_h1", cells=176214, plan_core="eng_rr_h1",
                            lef="physical/die_plan/s81/cores/eng/lef/dsdv_eng_rr_h1.lef")],
                gaps=[],
                # the split replaces the whole monolith: its soft residual is the type glue only
                replaces=418942,
                place={"u_eng.u_e": (1028.16, 717.12), "u_eng.u_h0": (1028.16, 432.0), "u_eng.u_h1": (1209.6, 432.0)},
                # S81/LEAFPLAN 10-24 (ruling (a)): the GR8 E/H0/H1 group translated W toward the N-face unit / xtier windows
                # (x 523..832), ranked with the base by the generator key (internal-station cycles + ft stations)
                alt_place=[{"u_eng.u_e": (round(1028.16 - d_, 4), 717.12), "u_eng.u_h0": (round(1028.16 - d_, 4), 432.0),
                            "u_eng.u_h1": (round(1209.6 - d_, 4), 432.0)} for d_ in (86.4 * k_ for k_ in range(1, 7))],
                mirrors=((False, False),)),
}
# PORTFIX r4: keep existing hard-core pins facing their real partners.
from core_layout_r4 import apply as apply_core_layout_r4
apply_core_layout_r4(NONFRAME_HC)
HC_REPORT = {}
# declared port pairs where width / nearest matching is ambiguous: {key: {(core, port): partner port}}
CORE_PORT_PAIRS = {k_: {("u_c.u_eg", "g"): "eg_d", ("u_c.u_eg", "g_c"): "eg_c", ("u_c.u_eg", "g_v"): "eg_v",
                        ("u_c.u_eg", "eps"): "x_eps", ("u_c.u_eg", "scale"): "x_scale",
                        ("u_c.u_xr", "eg_d"): "g", ("u_c.u_xr", "eg_c"): "g_c", ("u_c.u_xr", "eg_v"): "g_v",
                        ("u_c.u_xr", "x_eps"): "eps", ("u_c.u_xr", "x_scale"): "scale"} for k_ in ("C:xrt1", "C:xrt3")}
# S81-CORES 10-24: core connectivity for the G0C core-face rule (core_conns.json sidecar, written next to die_plan.json):
# {key: {core inst: {core port: ["bus:<type bus>" | "core:<inst>"]}}}.  Ports whose partner is soft glue (the leaf's hc
# lanes and store SRAMs talk only to vp's own pin flops / sequencer) are not listed (unchecked by design).
_LF = "u_lf."
_HC = ["core:u_lf.u_vp.g_ln[%d].u_l" % i for i in range(16)]
_ST = ["core:u_lf.u_vp.u_b0", "core:u_lf.u_vp.u_b1"]
_DN, _UP = "bus:leafdn_i0", "bus:leafup_o0"


def _cc(**kw):
    return {p: list(v) for ps, v in kw.items() for p in ps.split(",")}


CORE_CONNS = {
    "leaf": {
        # S81/LEAFPLAN 10-24 split: vn_a / vn_b both on the lane h ports (each answers its half), the store gains,
        # the dn bus (n_go / n_pre / rb); vn_a's chain partial c -> vn_b; p from vn_b; y lanes 0..3 / 4..7 -> vq.
        # ve_m: r / a / o with vs, products m -> ve_s; ve_s: p -> vs; both faults -> vs
        **{_LF + "u_vn.u_" + h_: dict(_cc(**{"hw_v,hw_j,hw_hf,hw_d,hq_v,hq_d,hr_v,hr_j,hr_hf": _HC}), **_cc(**{
            "wl_v,wl_i,wl_d": _ST, "n_go,n_pre": _ST + [_DN], "rb_v,rb_d": [_DN], "y": ["core:u_lf.u_vq"],
            "c_v,c_s": ["core:u_lf.u_vn.u_" + ("b" if h_ == "a" else "a")]}),
            **(_cc(**{"p_v,p_d": [_UP], "y_v,y_i": ["core:u_lf.u_vq"]}) if h_ == "b" else {})) for h_ in "ab"},
        _LF + "u_vq": _cc(**{"y_v,y_i,y": ["core:u_lf.u_vn.u_a", "core:u_lf.u_vn.u_b"],
                             "u_v,u_i,u,um_v,um_q,um_b,um_i": ["core:u_lf.u_vs"],
                             "xf_v,xf_s,xf,fault": [_UP], "k,sid,m_v,m_q,m_b,m_i": [_DN]}),
        _LF + "u_vs": _cc(**{"s_v,s_d,g_v,g_c,g_d": [_DN], "e_v,e_c,e_d,fault": [_UP],
                             "x_rv,x_ra,x_qv,x_qd,x_wv,x_wa,x_wm,x_wd": _ST,
                             "u_v,u_i,u,um_v,um_q,um_b,um_i": ["core:u_lf.u_vq"],
                             "ve_rv,ve_rc,ve_rh,ve_rk,ve_rw,ve_av,ve_ac,ve_ah,ve_aval,ve_ag,ve_ov,ve_oc,ve_oy":
                                 ["core:u_lf.u_ve.u_m"],
                             "ve_pv,ve_pc,ve_phh,ve_pkk,ve_pdd": ["core:u_lf.u_ve.u_s"],
                             "ve_fi": ["core:u_lf.u_ve.u_m", "core:u_lf.u_ve.u_s"],
                             "sw_v,sw_d,sw_w,sw_lim,sw_vi,sw_ri,sw_fi": ["core:u_lf.u_vsw"],
                             "ra_v,ra_x": ["core:u_lf.u_rxsf"], "ra_vi,ra_ri,ra_fi": ["core:u_lf.u_rxsb"]}),
        _LF + "u_ve.u_m": _cc(**{"r_v,r_c,r_h,r_k,r_w,a_v,a_c,a_h,a_val,a_g,o_v,o_c,o_y,fault": ["core:u_lf.u_vs"],
                                 "m_v,m_pre,m_hh,m_kk,m_dd": ["core:u_lf.u_ve.u_s"]}),
        _LF + "u_ve.u_s": _cc(**{"p_v,p_c,p_hh,p_kk,p_dd,fault": ["core:u_lf.u_vs"],
                                 "m_v,m_pre,m_hh,m_kk,m_dd": ["core:u_lf.u_ve.u_m"]}),
        _LF + "u_vsw": _cc(**{"i_v,i_d,i_w,i_lim,o_v,o_d,o_f": ["core:u_lf.u_vs"]}),
        _LF + "u_rxsf": _cc(**{"i_v,i_x": ["core:u_lf.u_vs"], "o_v,o_u,o_u2,o_mx,o_f": ["core:u_lf.u_rxsb"]}),
        _LF + "u_rxsb": _cc(**{"i_v,i_u,i_u2,i_mx,i_f": ["core:u_lf.u_rxsf"], "o_v,o_r,o_f": ["core:u_lf.u_vs"]}),
    },
    # svc: the exchange half rows' face lanes run (via the dsfd_dvrly relay stations) to the svc face of the same name;
    # l_i / rt_o / t_o meet the attention engine glue (soft) and stay unchecked; the hcores' partners are the engine's
    # soft staging (unchecked, GEOM-REVIEW8 PASS on the grid)
    "svc": {"u_rsv.u_sx.g_r[%d].g_h[%d].u_hrow" % (r, b): {
        "%s_%s" % (io, f.lower()): ["face:%s" % f] for io in ("gi", "go", "si", "so") for f in "NESW"}
        for r in range(4) for b in range(2)},
    # S81/LEAFPLAN 10-24 (S81/KITS eg_c r7 partner distances: eg.g/g_c/g_v -> xrt eg_* up to 534 / 664 / 803 um in
    # c1x-lepw / kv512 / c3x): the C slices' eg <-> xrt bundles (eg g / g_c / g_v -> xrt eg_d / eg_c / eg_v; xrt
    # x_eps / x_scale -> eg eps / scale) get the R3-INTERNAL stations at 405 um like the hardened leaf types.  eg's
    # i_* (from xfin) are not in the xfin plan table (plan gap, reported) and stay unchecked.
    **{k_: {"u_c.u_eg": _cc(**{"g,g_c,g_v,eps,scale": ["core:u_c.u_xr"]}),
            "u_c.u_xr": _cc(**{"eg_d,eg_c,eg_v,x_eps,x_scale": ["core:u_c.u_eg"]})} for k_ in ("C:xrt1", "C:xrt3")},
    "eng": {
        "u_eng.u_e": _cc(pci=["bus:unit_i0"], rco=["bus:unit_o0"], f_ks=["bus:unit_i1"], vi_s=["bus:xtier_i0"],
                         vo_s=["bus:xtier_o0"], vo_n=["bus:xtier_o1"], vi_n=["bus:xtier_i1"],
                         **{"hx_w,hx_res": ["core:u_eng.u_h0", "core:u_eng.u_h1"]}),
        "u_eng.u_h0": _cc(**{"in_w,out_res": ["core:u_eng.u_e"]}),
        "u_eng.u_h1": _cc(**{"in_w,out_res": ["core:u_eng.u_e"]}),
    },
    # S81-KITS-RTLC 10-24 (ruling c): the slice hub C xfin -> eg copy link (ot_s81sl_slice_c1x / c3x xe_*): the re-pinned
    # xfin table carries e_v / e_c / e_hh / e_kk / e_dd (N face, M5) and eg reads them on i_*
    **{k: {"u_c.u_xf": _cc(**{"e_v,e_c,e_hh,e_kk,e_dd": ["core:u_c.u_eg"]}),
           "u_c.u_eg": _cc(**{"i_v,i_c,i_hh,i_kk,i_dd": ["core:u_c.u_xf"]})} for k in ("C:xrt1", "C:xrt3")},
}
CORE_CONNS_OUT = {}
# S81/PORTFIX 10-25: the hard-core types CORE_CONNS does not list (landed frames: qbank / node / ROM / view cores; gunit;
# bk_sel) take their core connectivity from inputs/core_conns_derived.json (core_conns_derive.py: yosys, cores black
# boxes, only DIRECT core-core / core-module-port nets).  A module port maps to a type bus through the contents bind
# ("bus:<bus>") or, for unbound contents, PF_PORT_BUS (the binder's port -> lane map; the unit fault output reaches flt_o0
# through the die-level ring stop, soft, so it is not listed).
CORE_CONNS_DERIVED = os.path.join(os.path.dirname(os.path.abspath(__file__)), "inputs", "core_conns_derived.json")
PF_PORT_BUS = {
    "dsdv_gunit": {"cw_a": "unit_i0", "cw_d": "unit_i0", "cw_v": "unit_i0", "vi_s": "xtier_i0", "vi_n": "xtier_i1",
                   "vo_s": "xtier_o0", "vo_n": "xtier_o1"},
    "dsdv_bk_sel_vmtx": {"ca": "ca_i0", "cb": "cb_i0", "vi_idx": "idx_i0", "vi_s": "xtier_i0", "vi_n": "xtier_i1",
                         "vo_s": "xtier_o0", "vo_n": "xtier_o1", "tl_o": "tl_o0",
                         "tpn_o": "tp_o1", "tps_o": "tp_o0", "tpn_i": "tp_i0"},
}


def derived_core_conns(types):
    """S81/PORTFIX: CORE_CONNS_OUT entries for every hard-core type with no hand-written CORE_CONNS key."""
    if not os.path.exists(CORE_CONNS_DERIVED):
        return
    der = json.load(open(CORE_CONNS_DERIVED))
    for tn, t in types.items():
        if tn in CORE_CONNS_OUT or not t.get("hard_cores") or len(t.get("contents", [])) != 1:
            continue
        c = t["contents"][0]
        d = der.get(c["module"])
        if d is None:
            continue
        buses = {b["name"] for b in t.get("buses", [])}
        pb = {k: v[4:] for k, v in (c.get("bind") or {}).items() if str(v).startswith("bus:")}
        pb.update(PF_PORT_BUS.get(c["module"], {}))
        hcs = {h["inst"] for h in t["hard_cores"]}
        ent = {}
        for ci, ports in d["cores"].items():
            inst = c["inst"] + "." + ci
            if inst not in hcs:
                continue
            for port, tgs in ports.items():
                out = []
                for tg in tgs:
                    k, _, n = tg.partition(":")
                    if k == "core" and c["inst"] + "." + n in hcs:
                        out.append("core:" + c["inst"] + "." + n)
                    elif k == "port" and pb.get(n) in buses:
                        out.append("bus:" + pb[n])
                if out:
                    ent.setdefault(inst, {})[port] = sorted(set(out))
        if ent:
            CORE_CONNS_OUT[tn] = ent


def nonframe_hc_key(p):
    m = p.contents[0]["module"] if p.contents else ""
    if p.kind == "svc":
        return "svc"
    if p.kind == "slice":
        role = getattr(p, "role", "X")
        if role == "C":
            return "C:xrt3" if "c3x" in m else "C:xrt1"
        if role.startswith("L") and "kv_leaf" not in m:
            return "leaf"
        return None
    return p.name if p.name in NONFRAME_HC else None


def _lef_size(lef):
    import subprocess as _sp
    root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..")
    if os.path.exists(os.path.join(root, lef)):
        raw = open(os.path.join(root, lef), "rb").read()
    elif os.path.exists(lef):
        raw = open(lef, "rb").read()
    else:
        raw = _sp.run(["git", "-C", root, "show", "HEAD:" + lef], check=True, capture_output=True).stdout
    if lef.endswith(".zst"):
        raw = _sp.run(["zstd", "-dc"], input=raw, check=True, capture_output=True).stdout
    sz = re.search(r"SIZE\s+([\d.]+)\s+BY\s+([\d.]+)", raw.decode())
    return [float(sz.group(1)), float(sz.group(2))]


_LEF_SIZE = {}
CORE_INT_REACH_UM = FT_KIT_REACH_UM   # S81/LEAFPLAN 10-24 ruling (a): R3 inside the hardened leaf / svc / eng types
_PGRP = {}


def _core_view(spec, c, view, **kw):
    """one hard_cores[] entry of core spec c on pin view `view` (None = the base view; spec["views"][view][inst])."""
    vw = spec.get("views", {}).get(view, {}).get(c["inst"]) if view else None
    e = dict(inst=c["inst"], module=c["module"], lef=(vw or c)["lef"], **kw)
    e["pins_file"] = (vw or {}).get("pins_file") or c.get("pins_file", "inputs/core_pins/%s.json" % c["module"])
    if vw:
        e["note"] = "view %s: x-mirrored pin variant of %s (cores/leaf/xmirror.py)" % (view, c.get("pins_file") or
                                                                                      c["module"])
    return e


def _xmirror(spec, byi, o, w):
    """candidate o mirrored in x as a whole (type frame, 8.64 lattice, same track offsets, orients kept), every core
    with an x-mirror view (spec xmirror_views) switched to the other view: R0 <-> x-mirrored pins."""
    xv = spec["xmirror_views"]
    r = []
    for c in o:
        (x_, y_), (cw, ch) = c["origin_um"], c["outline_um"]
        dx = c["track_offset_um"][0]
        x_ = math.floor(round((w - (x_ + dx + cw) - dx) / G, 6)) * G
        base = byi[c["inst"]]
        if c["inst"] in spec.get("views", {}).get(xv, {}):
            view = None if c.get("note", "").startswith("view %s" % xv) else xv
            r.append(_core_view(spec, base, view, origin_um=[round(x_, 4), y_], outline_um=[cw, ch],
                                orient=c.get("orient", "R0"), track_offset_um=list(c["track_offset_um"])))
        else:
            r.append(dict(c, origin_um=[round(x_, 4), y_]))
    return r


def _pin_groups(pins_file, W_, H_):
    """{port: (cx, cy, bits, {face: pins})} of one plan pin table, core frame R0, outline W_ x H_ (cached); the face of a
    pin is its nearest outline edge (check.py _core_face)."""
    if pins_file not in _PGRP:
        js = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), pins_file)))
        ps = js["pins"]
        g = {}
        for p_ in ps:
            b_ = re.sub(r"\[\d+\]$", "", p_["name"])
            f_ = min([(p_["x"], "W"), (W_ - p_["x"], "E"), (p_["y"], "S"), (H_ - p_["y"], "N")])[1]
            e_ = g.setdefault(b_, [0.0, 0.0, 0, {}])
            e_[0] += p_["x"]
            e_[1] += p_["y"]
            e_[2] += 1
            e_[3][f_] = e_[3].get(f_, 0) + 1
        cen_ = {b_: (e_[0] / e_[2], e_[1] / e_[2]) for b_, e_ in g.items()}
        spr_ = {}
        for p_ in ps:
            b_ = re.sub(r"\[\d+\]$", "", p_["name"])
            spr_[b_] = max(spr_.get(b_, 0.0), abs(p_["x"] - cen_[b_][0]) + abs(p_["y"] - cen_[b_][1]))
        # (cx, cy, bits, {face: pins}, spread = the farthest pin's manhattan distance from the centroid)
        _PGRP[pins_file] = {b_: (cen_[b_][0], cen_[b_][1], e_[2], e_[3], spr_[b_]) for b_, e_ in g.items()}
    return _PGRP[pins_file]


def _placed_groups(c):
    """(box, {port: (x, y, bits, {face: pins})}) of a placed core in the type frame (orient R0 / MX / MY / R180)."""
    x0, y0 = c["origin_um"][0] + c["track_offset_um"][0], c["origin_um"][1] + c["track_offset_um"][1]
    cw, ch = c["outline_um"]
    o = c.get("orient", "R0")
    fx, fy = o in ("MY", "R180"), o in ("MX", "R180")
    sw = dict(N="S", S="N", E="E", W="W") if fy else {}
    sw2 = dict(E="W", W="E") if fx else {}
    out = {}
    for b_, (x, y, n, fc, sp) in _pin_groups(c["pins_file"], cw, ch).items():
        out[b_] = (x0 + (cw - x if fx else x), y0 + (ch - y if fy else y), n,
                   {sw2.get(sw.get(f_, f_), sw.get(f_, f_)): v for f_, v in fc.items()}, sp)
    return (x0, y0, x0 + cw, y0 + ch), out


def _bus_pts(buses, w, h):
    r = {}
    for b_ in buses:
        if b_.get("face") in ("N", "S", "E", "W"):
            m_ = sum(b_["window_um"]) / 2
            r[b_["name"]] = dict(N=(m_, h), S=(m_, 0.0), E=(w, m_), W=(0.0, m_))[b_["face"]]
    return r


_NRM = dict(N=(0.0, 1.0), S=(0.0, -1.0), E=(1.0, 0.0), W=(-1.0, 0.0))


def core_faces_away(k, o, w, h, buses):
    """number of declared core ports whose pins' mean best cos(face normal, direction to a partner) < -0.1: the G0C
    core-face rule (tools/die_plan/check.py check_core_faces) on a candidate, partners = core box centres / bus window
    centres / face points (FIRM internal stations keep the direction of their straight window -> pin line)."""
    pl = {c["inst"]: _placed_groups(c) for c in o}
    cen = {i_: ((b_[0] + b_[2]) / 2, (b_[1] + b_[3]) / 2) for i_, (b_, _) in pl.items()}
    bp = _bus_pts(buses, w, h)
    bad = 0
    for ci, ports in CORE_CONNS.get(k, {}).items():
        if ci not in pl:
            continue
        cx, cy = cen[ci]
        for p_, tg in ports.items():
            g = pl[ci][1].get(p_)
            if not g:
                continue
            pts = []
            for t_ in tg:
                kd, _, nm = t_.partition(":")
                if kd == "bus" and nm in bp:
                    pts.append(bp[nm])
                elif kd == "core" and nm in cen and nm != ci:
                    pts.append(cen[nm])
                elif kd == "face" and nm in _NRM:
                    pts.append(dict(N=(cx, h), S=(cx, 0.0), E=(w, cy), W=(0.0, cy))[nm])
            dirs = [((tx - cx) / math.hypot(tx - cx, ty - cy), (ty - cy) / math.hypot(tx - cx, ty - cy))
                    for tx, ty in pts if math.hypot(tx - cx, ty - cy) > 1e-6]
            if not dirs:
                continue
            fc = g[3]
            mean = sum(v * max(_NRM[f_][0] * ux + _NRM[f_][1] * uy for ux, uy in dirs) for f_, v in fc.items()) / g[2]
            bad += mean < -0.1
    return bad


# S81/LEAFPLAN2 10-25 (GEOM review of r9: 65 / 74 leaf types had hcpl lanes > 50 um BEHIND the vn halves' lane face,
# up to 947 um, wrapping the 256-b h buses around the core): lane-side rule.  {key: (lane insts, {core: port}, exempt)}:
# the face that carries the core's port (the port group's majority face, placed orientation / pin view applied) splits
# the type: every lane box lies wholly in front of that face's plane (the lane field), and no other hard core (except
# the `exempt` ones: the leaf-store SRAMs, wired to the same vn face) reaches into the lane field -- so no lane sits
# behind a core.  The candidate ranking treats a violation as hard (after the G0C face rule); cores/leaf/search.py too.
LANE_SIDE = {"leaf": (["u_lf.u_vp.g_ln[%d].u_l" % i for i in range(16)],
                      {"u_lf.u_vn.u_a": "hq_d", "u_lf.u_vn.u_b": "hq_d"},
                      ["u_lf.u_vp.u_b0", "u_lf.u_vp.u_b1"])}
# the bus reach-excess ranking term keeps the 750-um legacy reach (S81 parent 10-25: a 405 term would dominate the
# ranking; station spacing still meets 405 exactly through the internal / ft station tools)
RANK_REACH_UM = 750.0


def core_lanes_behind(k, o):
    """(violations, um) of the LANE_SIDE rule: lane-core pairs with the lane box not wholly in front of the core's lane
    face + non-lane, non-exempt cores reaching into that face's lane field (um = total depth of both)."""
    if k not in LANE_SIDE:
        return 0, 0.0
    lanes, cores, exempt = LANE_SIDE[k]
    pl = {c["inst"]: _placed_groups(c) for c in o}
    n, um = 0, 0.0
    for ci, port in cores.items():
        if ci not in pl or port not in pl[ci][1]:
            continue
        b, fc = pl[ci][0], pl[ci][1][port][3]
        f = max(fc, key=lambda f_: fc[f_])
        for ot, (a, _) in pl.items():
            if ot in cores or ot in exempt:
                continue
            if ot in lanes:
                # lane: wholly in front (distance of its far-side edge beyond the plane >= 0)
                gap = dict(W=b[0] - a[2], E=a[0] - b[2], S=b[1] - a[3], N=a[1] - b[3])[f]
            else:
                # other core: wholly behind the plane (none of it in the lane field)
                gap = dict(W=a[0] - b[0], E=b[2] - a[2], S=a[1] - b[1], N=b[3] - a[3])[f]
            if gap < -1e-6:
                n += 1
                um += -gap
    return n, round(um, 2)


def _outside(x, y, boxes, w, h):
    """(x, y) moved to the nearest point outside every box it falls in (station legalisation), clamped to the outline."""
    for _ in range(4):
        hit = [b_ for b_ in boxes if b_[0] < x < b_[2] and b_[1] < y < b_[3]]
        if not hit:
            break
        b_ = hit[0]
        x, y = min([(x - b_[0], (b_[0], y)), (b_[2] - x, (b_[2], y)), (y - b_[1], (x, b_[1])),
                    (b_[3] - y, (x, b_[3]))])[1]
        x, y = min(max(x, 0.0), w), min(max(y, 0.0), h)
    return (x, y)


def core_internal_stations(k, o, w, h, buses, smax=None):
    """R3 inside the hardened types (S81/LEAFPLAN, coordinator ruling 10-24 (a)): every CORE_CONNS bundle -- core port
    pin-group centroid -> bus window centre, or -> the partner core's matching port group (same width, nearest; else
    the nearest point of the partner box) -- longer than the kit reach (405 um, no margin) for its farthest pin (the
    pin groups' spreads added to the end hops) gets FIRM stations at j / (n + 1) on the straight line, a site inside a
    hard core pushed out of it (n grows until every hop of every pin <= the reach).  A core-core bundle declared from both sides is emitted
    once.  Returns (internal_stations[] entries, cycles) where cycles = sum over links (core, partner) of the largest
    station count of their bundles (each station = +1 cycle on that pair's path; a broadcast port's partner set is one
    pair)."""
    smax = smax or CORE_INT_REACH_UM          # decision 12 (COORD 10-24): hops <= 405 um exactly
    pl = {c["inst"]: _placed_groups(c) for c in o}
    hb = [(b_[0] - FT_HALO, b_[1] - FT_HALO, b_[2] + FT_HALO, b_[3] + FT_HALO) for b_, _ in pl.values()]
    bp = _bus_pts(buses, w, h)
    conns = CORE_CONNS.get(k, {})
    ents, cyc, seen = [], {}, set()

    pairs = CORE_PORT_PAIRS.get(k, {})

    def match(a, pa, b):
        """b's port group wired to a.pa: the declared pair (CORE_PORT_PAIRS), else same width first, then nearest."""
        ga = pl[a][1][pa]
        if (a, pa) in pairs and pairs[(a, pa)] in pl[b][1]:
            return pairs[(a, pa)]
        rev = [p_ for p_, tg in conns.get(b, {}).items() if "core:" + a in tg and p_ in pl[b][1]]
        if not rev:
            return None
        return min(rev, key=lambda p_: (pl[b][1][p_][2] != ga[2],
                                        abs(pl[b][1][p_][0] - ga[0]) + abs(pl[b][1][p_][1] - ga[1])))
    for a, ports in conns.items():
        if a not in pl:
            continue
        for pa, tg in ports.items():
            ga = pl[a][1].get(pa)
            if not ga:
                continue
            for t_ in tg:
                kd, _, nm = t_.partition(":")
                sa_, sb_ = 0.0, ga[4]          # pin spread at the launch / capture end (every pin's hop <= reach)
                if kd == "bus" and nm in bp:
                    fr, to, conn, cap, pair = bp[nm], (ga[0], ga[1]), "bus:" + nm, "%s.%s" % (a, pa), (a, "bus:" + nm)
                elif kd == "core" and nm in pl and nm != a:
                    pb = match(a, pa, nm)
                    if pb is not None:
                        if (nm, pb, a, pa) in seen:
                            continue
                        seen.add((a, pa, nm, pb))
                        gb = pl[nm][1][pb]
                        to, cap = (gb[0], gb[1]), "%s.%s" % (nm, pb)
                        sa_, sb_ = ga[4], gb[4]
                    else:
                        bx = pl[nm][0]
                        to, cap = (min(max(ga[0], bx[0]), bx[2]), min(max(ga[1], bx[1]), bx[3])), nm
                        sa_, sb_ = ga[4], 0.0
                    # one latency key per link: a single-partner link (both sides), or a port's whole partner set
                    # (a broadcast such as vn hq / hw -> the 16 hcpl lanes adds its largest station count once)
                    pair = tuple(sorted((a, nm))) if len(tg) == 1 else (a,) + tuple(sorted(tg))
                    fr, conn = (ga[0], ga[1]), "core:%s.%s|core:%s" % (a, pa, nm)
                else:
                    continue
                L = abs(fr[0] - to[0]) + abs(fr[1] - to[1])
                if L + sa_ + sb_ <= smax + 1e-6:
                    continue
                n = max(1, math.ceil(L / smax - 1e-9) - 1)
                # a station is soft logic: a site inside a hard core (+ halo) is pushed to the nearest point outside
                # it; n grows until every hop (with the escapes) is within the reach (as ft_stations_macro)
                for _ in range(12):
                    regs = [_outside(fr[0] + (to[0] - fr[0]) * j / (n + 1), fr[1] + (to[1] - fr[1]) * j / (n + 1), hb,
                                     w, h) for j in range(1, n + 1)]
                    pts_ = [fr] + regs + [to]
                    hops_ = [abs(p_[0] - q_[0]) + abs(p_[1] - q_[1]) for p_, q_ in zip(pts_, pts_[1:])]
                    hops_[0] += sa_
                    hops_[-1] += sb_
                    if max(hops_) <= smax + 1e-6:
                        break
                    n += 1
                regs = [[round(x_, 3), round(y_, 3)] for x_, y_ in regs]
                n = len(regs)
                ents.append(dict(conn=conn, from_um=[round(fr[0], 3), round(fr[1], 3)],
                                 to_um=[round(to[0], 3), round(to[1], 3)], regs_um=regs, bits=ga[2],
                                 launch=conn.split("|")[0] if kd == "core" else "face bus " + nm, capture=cap,
                                 note="R3 inside cores (coordinator ruling 10-24 (a)): %.0f um > %.0f-um kit reach: "
                                      "%d FIRM station(s), +%d cycle(s)" % (L, CORE_INT_REACH_UM, n, n)))
                cyc[pair] = max(cyc.get(pair, 0), n)
    return ents, sum(cyc.values())


def nonframe_hard_cores(p, w, h, tn, ftsl=(), buses=()):
    """hard_cores[] of one non-frame type (S81-P9-HC): packed shelf placement (first cut for GEOM review): cores sorted by
    height, rows bottom-up, origins on the 8.64 lattice, >= HC_GAP_UM between facing core boxes (after the track
    offset), HC_EDGE_UM keep-off from the outline, orient R0, track_offset CORE_TRACK_OFFSET, CORE-KS pins_file."""
    k = nonframe_hc_key(p)
    if k is None:
        return []
    spec = NONFRAME_HC[k]
    cores, glue, basis = cells_core_plan(p)
    total = sum(c for _, c in cores) + glue
    hard = sum(c["cells"] or 0 for c in spec["cores"])
    # S81-CORES: a split / re-hardened core set can carry more cells than the soft cells it replaces (pin registers):
    # the residual soft cells are total - the replaced soft cells (spec "replaces"), else total - hard
    resid = total - spec.get("replaces", hard)
    if total <= HC_CELLS_MAX:
        return []
    rep = dict(key=k, cells=total, hard_cells=hard, residual_soft_cells=resid, basis=basis,
               gaps=[{kk: v for kk, v in g.items()} for g in spec["gaps"]], cores=len(spec["cores"]))
    HC_REPORT[tn] = rep
    if not spec["cores"] or resid > HC_CELLS_MAX:
        rep["emitted"] = False
        rep["why"] = "residual soft cells %d > %d with the closed views available: real gap (see gaps)" % (
            resid, HC_CELLS_MAX)
        return []
    dx, dy = CORE_TRACK_OFFSET
    items = []
    for c in spec["cores"]:
        if c.get("outline"):
            # S81-CORES: the core outline is given where the LEF is not in the tree (or the core is placed from a plan
            # pin table only); the pins_file carries the pins
            _LEF_SIZE[c["lef"]] = list(c["outline"])
        if c["lef"] not in _LEF_SIZE:
            _LEF_SIZE[c["lef"]] = _lef_size(c["lef"])
        items.append((c, _LEF_SIZE[c["lef"]]))
    items.sort(key=lambda t: (-t[1][1], -t[1][0], t[0]["inst"]))

    def up(v):
        return math.ceil(round(v / G, 6)) * G
    x0 = y0 = up(HC_EDGE_UM)
    x, y, row_h, out = x0, y0, 0.0, []
    alts = []
    if spec.get("place"):
        # CORE-S81 10-23: explicit connectivity-aware origins (type frame, 8.64 lattice) where the shelf packer does not
        # fit; the corner mirroring and the gap / edge legality below still apply.  S81-CORES: "alt_place" = ordered
        # per-instance overrides of the base placement, tried only when the base adds ft-slot stations in this type
        bsz_ = {c["inst"]: _LEF_SIZE[c["lef"]] for c, _ in items}

        def expand(d, views=None):
            """S81/LEAFPLAN: placement-block keys (spec "blocks") -> their child cores at the fixed offsets; a block on
            the x-mirror view has its children swapped inside the block box (their pins are mirrored with them)"""
            d = dict(d)
            for b_, ch_ in spec.get("blocks", {}).items():
                if b_ in d:
                    v_ = d.pop(b_)
                    bw_ = max(ox_ + bsz_[ci_][0] for ci_, ox_, _ in ch_)
                    for ci_, ox_, oy_ in ch_:
                        if (views or {}).get(b_):
                            ox_ = bw_ - ox_ - bsz_[ci_][0]
                        d[ci_] = (round(v_[0] + ox_, 4), round(v_[1] + oy_, 4)) + tuple(v_[2:])
            return d

        def eviews(v):
            v = dict(v or {})
            for b_, ch_ in spec.get("blocks", {}).items():
                if b_ in v:
                    vv_ = v.pop(b_)
                    v.update({ci_: vv_ for ci_, _, _ in ch_})
            return v
        base_place = expand(spec["place"])

        def explicit(over, views=None):
            o = []
            over, views = expand(over, views), eviews(views)
            for c, (cw, ch) in items:
                pl_ = over.get(c["inst"], base_place[c["inst"]])
                o.append(_core_view(spec, c, (views or {}).get(c["inst"]),
                                    origin_um=[pl_[0], pl_[1]], outline_um=[cw, ch],
                                    orient=pl_[2] if len(pl_) > 2 else base_place[c["inst"]][2]
                                    if len(base_place[c["inst"]]) > 2 else "R0",
                                    track_offset_um=list(CORE_TRACK_OFFSET)))
            return o
        alts = [explicit(a) for a in spec.get("alt_place", ())]
        if spec.get("alt_place_file"):
            alts += [explicit({kk: tuple(v) for kk, v in c_["place"].items()}, c_.get("views"))
                     for c_ in json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), spec["alt_place_file"])))["candidates"]]
        out = explicit({})
        if spec.get("xmirror_views"):
            # S81/LEAFPLAN: every candidate x-mirrored as a whole, vn / vq / vs on the other pin view (after the others)
            byi = {c["inst"]: c for c, _ in items}
            alts += [_xmirror(spec, byi, o_, w) for o_ in [out] + alts]
        items = []
    for c, (cw, ch) in items:
        if x + dx + cw > w - HC_EDGE_UM:
            x, y, row_h = x0, up(y + dy + row_h + HC_GAP_UM), 0.0
        if x + dx + cw > w - HC_EDGE_UM or y + dy + ch > h - HC_EDGE_UM:
            raise SystemExit("S81-P9-HC: type %s: core %s (%gx%g) does not fit the %gx%g outline" % (
                tn, c["inst"], cw, ch, w, h))
        out.append(dict(inst=c["inst"], module=c["module"], lef=c["lef"], origin_um=[round(x, 4), round(y, 4)],
                        outline_um=[cw, ch], orient="R0", track_offset_um=list(CORE_TRACK_OFFSET),
                        pins_file=c.get("pins_file", "inputs/core_pins/%s.json" % c["module"])))
        x = up(x + dx + cw + HC_GAP_UM)
        row_h = max(row_h, ch)
    # corner choice: the packed block is mirrored to each outline corner (lattice-snapped); the first variant that adds no
    # ft-slot station (ft_stations_macro: a core on a slot's in->out line pushes its stations off) and keeps the gap /
    # edge rules wins; else the one adding fewest stations
    def mirrored(mx, my, out=out):
        o = []
        for c in out:
            (x_, y_), (cw, ch) = c["origin_um"], c["outline_um"]
            if mx:
                x_ = math.floor(round((w - (x_ + dx + cw) - dx) / G, 6)) * G
            if my:
                y_ = math.floor(round((h - (y_ + dy + ch) - dy) / G, 6)) * G
            oc = c.get("orient", "R0")
            if spec.get("place"):
                # S81-CORES: explicit placements carry orients; a mirrored block mirrors its cores too (faces keep
                # facing their partners).  The shelf packer keeps R0 (unchanged output).
                fx, fy = oc in ("MY", "R180"), oc in ("MX", "R180")
                fx, fy = fx != bool(mx), fy != bool(my)
                oc = {(False, False): "R0", (True, False): "MY", (False, True): "MX", (True, True): "R180"}[(fx, fy)]
            to = list(c["track_offset_um"])
            if oc in ("MX", "R180"):
                # y-mirrored core: its H-layer (M4 / M6) pins keep the plan tracks when the sub-lattice y shift absorbs
                # the outline height: R0 pins sit at y = 0.012 (mod 0.048) after the [., 0.012] offset, so the mirrored
                # pin y' = dy + ch - 0.012 must be 0.024 (mod 0.048) (the core frame M6 tracks follow the same rule)
                to[1] = round((0.036 - ch) % 0.048, 4)
            if spec.get("place") and oc != "R0":
                # Reuse the frame-core orient-aware lattice search for fixed
                # non-frame placements. This preserves the actual LEF pins;
                # mirrored orientations need both V- and H-layer residues.
                to = core_track_offset(dict(c, size_um=[cw, ch],
                                            origin_um=[round(x_, 4), round(y_, 4)], orient=oc))
            o.append(dict(c, origin_um=[round(x_, 4), round(y_, 4)], orient=oc, track_offset_um=to))
        return o

    def legal(o):
        bx = [(c["origin_um"][0] + dx, c["origin_um"][1] + dy, c["origin_um"][0] + dx + c["outline_um"][0],
               c["origin_um"][1] + dy + c["outline_um"][1]) for c in o]
        if any(b_[0] < HC_EDGE_UM - 1e-6 or b_[1] < HC_EDGE_UM - 1e-6 or b_[2] > w - HC_EDGE_UM + 1e-6 or
               b_[3] > h - HC_EDGE_UM + 1e-6 for b_ in bx):
            return False
        for i, a_ in enumerate(bx):
            for b_ in bx[i + 1:]:
                if max(b_[0] - a_[2], a_[0] - b_[2], b_[1] - a_[3], a_[1] - b_[3]) < HC_GAP_UM - 1e-6:
                    return False
        return True
    best = None
    variants = spec.get("mirrors", ((False, False), (False, True), (True, False), (True, True)))
    if os.environ.get("S81_HC_DUMP"):
        # S81/LEAFPLAN: the exact per-type search inputs (cores/leaf/search.py) -- outline, buses, ft slots before cores
        with open(os.environ["S81_HC_DUMP"], "a") as f_:
            f_.write(json.dumps(dict(type=tn, key=k, w=w, h=h, buses=list(buses), ftsl=list(ftsl))) + "\n")
    if spec.get("mirror_by_bus"):
        # S81-CORES: the cores' bus-side ports face N as placed; a type whose buses sit on its S face takes the y mirror
        bf = {b.get("face") for b in buses if b.get("face") in ("N", "S")}
        if len(bf) == 1:
            variants = [v for v in variants if v[1] == (bf == {"S"})]
    # S81-CORES 10-24 (GEOM review): a core port wired to a type bus must sit within the R3 reach of its face window
    # (window centre -> core box <= FT_STATION_MAX; check.py's R3-INTERNAL measures only window -> leaf box).  Candidates
    # (base + alt_place, each with its mirror variants) rank by (reach excess um, added ft stations, order)
    bw_ = {}
    for b_ in buses:
        m_ = sum(b_["window_um"]) / 2
        bw_[b_["name"]] = dict(N=(m_, h), S=(m_, 0), E=(w, m_), W=(0, m_)).get(b_.get("face"))
    cbus = {ci: {t_[4:] for tg_ in pp.values() for t_ in tg_ if t_.startswith("bus:")}
            for ci, pp in CORE_CONNS.get(k, {}).items()}

    def reach_excess(o):
        ex = 0.0
        for c in o:
            x0_, y0_ = c["origin_um"][0] + c["track_offset_um"][0], c["origin_um"][1] + c["track_offset_um"][1]
            x1_, y1_ = x0_ + c["outline_um"][0], y0_ + c["outline_um"][1]
            for bn in cbus.get(c["inst"], ()):
                a_ = bw_.get(bn)
                if a_:
                    d_ = max(x0_ - a_[0], 0, a_[0] - x1_) + max(y0_ - a_[1], 0, a_[1] - y1_)
                    ex += max(0.0, d_ - RANK_REACH_UM)
        return round(ex, 1)
    # added stations are counted against the same model with no core (at the 405-um reach for the S81-CORES keys)
    sm_ = {"smax": min(FT_STATION_MAX, FT_KIT_REACH_UM) * 0.98} if k in CORES_405_KEYS else {}
    k0_ = [ft_stations_macro(s_, [dict(origin_um=[-1e6, -1e6], outline_um=[1, 1])], w, h, **sm_) if sm_ else s_["stations"]
           for s_ in ftsl]
    # S81/LEAFPLAN 10-24 (coordinator ruling (a)): R3 applies inside the hardened types: every declared core-core /
    # bus-core bundle (CORE_CONNS) over the 405-um kit reach gets FIRM internal stations (priced cycles).  Candidates rank
    # by (core ports facing away (G0C face rule, must be 0), bus reach excess over FT_STATION_MAX, added cycles = ft
    # stations over the no-core model + internal-station cycles per core pair + station flop bits / 4096, order)
    for ai, base_ in enumerate([out] + alts):
        for mx, my in variants:
            o = mirrored(mx, my, base_)
            if not legal(o):
                continue
            fb_ = core_faces_away(k, o, w, h, buses) if k in CORE_CONNS else 0
            ist_, icyc_ = core_internal_stations(k, o, w, h, buses) if k in INT_STATION_KEYS else ([], 0)
            ftc_ = sum((max(0, ft_stations_macro(s_, o, w, h, **sm_) - k0_[i_]) if sm_ else
                        ft_stations_macro(s_, o, w, h) - k0_[i_]) for i_, s_ in enumerate(ftsl))
            # added cost = ft stations + internal-station cycles + internal-station flop bits / STATION_BITS_PER_CYCLE
            # (a far lane / wide bundle pays its station area, not only its worst-hop cycle)
            # S81/LEAFPLAN2 10-25: lane-side rule (hard, after the face rule): every lane box in front of the face of
            # the core port it is wired to (core_lanes_behind)
            lb_ = core_lanes_behind(k, o)[0]
            key = (fb_, lb_, reach_excess(o), round(icyc_ + ftc_ + sum(len(e_["regs_um"]) * e_["bits"] for e_ in ist_)
                                                    / STATION_BITS_PER_CYCLE, 2), ftc_)
            if best is None or key[:4] < best[0][:4]:
                best = (key, o, (mx, my), ai, ist_, icyc_)
            if key[:4] == (0, 0, 0, 0):
                break
        if best is not None and best[0][:4] == (0, 0, 0, 0):
            break
    if best is not None:
        rep["bus_reach_excess_um"] = best[0][2]
        rep["faces_away"] = best[0][0]
        rep["lanes_behind"] = best[0][1]
        rep["internal_station_cycles"] = best[5]
        rep["internal_stations"] = best[4]
        rep["internal_station_bits"] = sum(len(e_["regs_um"]) * e_["bits"] for e_ in best[4])
        best = (best[0][4],) + best[1:]
    if best is None:
        raise SystemExit("S81-P9-HC: type %s: no legal core packing" % tn)
    rep["emitted"] = True
    if k in CORE_CONNS:
        CORE_CONNS_OUT[tn] = CORE_CONNS[k]
    rep["corner"] = "%s%s" % ("E" if best[2][0] else "W", "N" if best[2][1] else "S")
    rep["ft_stations_added"] = best[0]
    if alts:
        rep["alt_place"] = best[3]
        rep["views"] = {c["inst"]: c["note"].split()[1].rstrip(":") for c in best[1] if c.get("note", "").startswith("view ")}
    return best[1]


FT_MACRO_ADD = []
NF_HC_TYPES = []
STATION_BITS_PER_CYCLE = 4096   # S81/LEAFPLAN: placement ranking prices 4096 station flop bits like one added cycle
CORES_405_KEYS = ("leaf", "svc", "eng")
INT_STATION_KEYS = CORES_405_KEYS + ("C:xrt1", "C:xrt3", "gunit", "bk_sel")   # R3-INTERNAL stations (core_conns bundles > 405 um)
FT_HALO = 8.64


def ft_stations_macro(s, cores, w, h, smax=FT_STATION_MAX * 0.98):
    """v4.6 (S81-P9 10-23, R3 ft0 'jog' fix): station count of an ft slot from its ROUTE around the hard cores.  Station
    j of k sits at L*j/k on the straight in->out line of each bit (face_flops.tcl); a site inside a hard core (+ halo)
    is pushed off the core by legalisation, which adds the escape distance to both of its hops (S81 r0 ft0: s1 jogged
    120 um off the bf row -> 753-841-um hops).  k grows until every sampled bit's hop (L/k + escape) <= smax."""
    if not cores:
        return s["stations"]
    boxes = [(c["origin_um"][0] - FT_HALO, c["origin_um"][1] - FT_HALO, c["origin_um"][0] + c["outline_um"][0] + FT_HALO,
              c["origin_um"][1] + c["outline_um"][1] + FT_HALO) for c in cores]

    def face_pt(face, win, t):
        p = win[0] + t * (win[1] - win[0])
        return {"E": (w, p), "W": (0.0, p), "N": (p, h), "S": (p, 0.0)}[face]

    def escape(x, y):
        e = 0.0
        for (a, b, c, d) in boxes:
            if a < x < c and b < y < d:
                e = max(e, min(x - a, c - x, y - b, d - y))
        return e
    k = s["stations"]
    for _ in range(4):
        worst = 0.0
        for i in range(64):
            t = (i + 0.5) / 64
            ax, ay = face_pt(s["in_face"], s["in_window_um"], t)
            bx, by = face_pt(s["out_face"], s["out_window_um"], t)
            L = abs(ax - bx) + abs(ay - by)
            for j in range(1, k):
                x, y = ax + (bx - ax) * j / k, ay + (by - ay) * j / k
                worst = max(worst, L / k + escape(x, y))
            worst = max(worst, L / k)
        if worst <= smax:
            break
        k += 1
    return k


def macrofree_ft_reach(plan):
    """Use actual corresponding pin bits and the implemented M4-M7 reach."""
    from tools.die_plan.ft_reach import resize
    return resize(plan, reach_um=min(FT_STATION_MAX, FT_KIT_REACH_UM), margin=.98)


def mir(c):
    return NC - 1 - c


# ------------------------------------------------------------------------------------------------ partitions
class Part:
    def __init__(self, name, kind, c0, r0, nc=1, nr=1, orient="R0", contents=None, hard=False, ckey=None,
                 note="", group=None, ft_ok=True):
        self.name, self.kind, self.c0, self.r0, self.nc, self.nr = name, kind, c0, r0, nc, nr
        self.orient, self.contents, self.hard, self.note = orient, contents or [], hard, note
        self.ckey = ckey or name          # content key (type identity of the contents)
        self.group = group                # e.g. slice half name
        self.ft_ok = ft_ok and not hard
        self.ents = []                    # interface entries

    @property
    def x0(self):
        return X0 + self.c0 * PX

    @property
    def y0(self):
        return X0 + self.r0 * PY

    @property
    def w(self):
        return self.nc * PX

    @property
    def h(self):
        return self.nr * PY

    def cells(self):
        return [(c, r) for c in range(self.c0, self.c0 + self.nc) for r in range(self.r0, self.r0 + self.nr)]

    @property
    def xflip(self):
        return self.orient in ("MY", "R180")

    @property
    def yflip(self):
        return self.orient in ("MX", "R180")


def C(inst, module, status="rework", params=None, note=None):
    d = dict(inst=inst, module=module, status=status)
    if params:
        d["params"] = params
    if note:
        d["note"] = note
    return d


def build(ab):
    blk = {b["name"]: b for b in ab["blocks"]}
    parts = []

    def add(p):
        parts.append(p)
        return p

    # ---- frame arrays: rows 1..18, frame rows fr = 0..5 at rows 1+3fr .. 3+3fr, all MX (r0 band on top) ----
    # chain positions from the centre outward: p1 p2 p3 (inner chain) p4 p5 p6 (outer chain)
    frames = {}
    for side in "WE":
        for fr in range(6):
            for pos in range(1, 7):
                cw = 6 - pos                        # W column: p1 = col 5 ... p6 = col 0
                col = cw if side == "W" else mir(cw)
                orient = "MX" if side == "W" else "R180"
                for b in range(3):
                    row = 3 + 3 * fr - b            # MX: r0 top band, r1 middle, r2 bottom
                    p = add(Part("f%s%d_p%d_b%d" % (side, fr, pos, b), "frame", col, row, orient=orient))
                    frames[(side, fr, pos, b)] = p
    # ---- serdes (PHY model, re-aspected to a 2-cell row slot, soft: a strip beside the PHY carries ft) ----
    serdes = {}
    sd = {"WS0": ("W", 0, 4), "WS1": ("W", 0, 2), "WN0": ("W", 19, 4), "WN1": ("W", 19, 2), "WN2": ("W", 19, 0),
          "WN3": ("C", 19, 6), "ES0": ("E", 0, 4), "ES1": ("E", 0, 2), "EN0": ("E", 19, 4), "EN1": ("E", 19, 2)}
    # S81-XDIE 10-24 (RELEASE_RACK 2.1, S81-HEAD xdie_io GAP 1): the copy-A/B reserve 6th pair on EVERY layer die (one
    # logic design; wired on the 64 pre/post-group dies only): E column B = EN2/EN3 (s_7N pair B: copyb_in tx on
    # pre-group dies) at the N row, W column B = WS2/WS3 (s_0S pair B: copyb_out rx on post-group dies) at the S row.
    # Free slots: the NW/SE corner cells (were bump/ESD keep-out channels) + the top s_7N station cells (s_7N 8 -> 7
    # rows, like every other N half) + WS3 re-aspected to a 1 x 2 cell column on the S edge in place of the two
    # bottom s_0S station cells (s_0S rows 0-11 -> 2-11).  nc, nr default 2, 1.
    sd.update({"WS2": ("W", 0, 0), "WS3": ("W", 0, 6, 1, 2), "EN2": ("E", 19, 6), "EN3": ("E", 19, 0)})
    for nm, spec in sd.items():
        side, row, cw = spec[:3]
        nc, nr = (spec[3:] + (2, 1))[:2] if len(spec) > 3 else (2, 1)
        col = cw if side != "E" else mir(cw) - 1
        # S81-XDIE 10-24 (GEOM condition 1, lk_WS0 PHY off-shore): the W-column S-edge SerDes (lk_WS0..WS3) are MX, so
        # their face windows (packed from local y 0) sit on the CORE side of the slot and the PHY zone on the die edge,
        # as the N-edge slots (MY: local y 0 = core side).  The E-column S-edge slots (lk_ES0/ES1, MY) keep their
        # orient: the same off-shore pattern there predates the reserve pair and their change would rename the in-flight
        # s_7S station kits (ST405 t23..t28) -> S81 steward decision.
        orient = "MY" if side == "E" else ("MX" if row == 0 and side == "W" else "R0")
        serdes[nm] = add(Part("lk_" + nm, "serdes", col, row, nc=nc, nr=nr, orient=orient,
                              contents=[C("u_phy", "ot_pdie_serdes", "rework",
                                          note="SerDes PHY model re-aspected into a %.2f x %.2f slot; a strip " % (nc * PX, nr * PY) +
                                               "beside it holds the boundary flops and ft stations")],
                              ckey="serdes"))
    # ---- centre: cols 6..15 ----
    # row 0: s_0S | iqf | phy (8-13) | eng | s_7S ; seqhost at (10,5) beside the svc band
    add(Part("phy_hbm", "phy", 8, 0, nc=6, hard=True,
             contents=[C("u_phy_hbm", "ot_hbm3e_phy_v41x_aw30_e8p5", "reuse",
                         note="hard HBM3E PHY 8500 x 1177 in a 6-cell S-edge slot (bump field at the die edge)")],
             ckey="phy"))
    add(Part("iqf", "unit", 7, 0, contents=[C("u_iqf", "dsdv_idx_qfs")], ckey="iqf"))   # S81/IDXNET 10-25: qf + 2-beat qc serializer
    add(Part("seqhost", "unit", 10, 5, contents=[C("u_seqhost", "dsdv_seq_host_mux", "rework",
                                                  params={"TAP_K": "8'h00", "SINK_K": "8'h00", "SELECT_HBE": "1'b0"})],
             ckey="seqhost", note="GEOM-REVIEW2: seqhost beside the svc band; its slice/svc fan-out = ID rings"))
    # svc (v3, PLAN-S81v3 RTL check 10-23): the svc attention datapath is NOT bit-sliceable (q.k is row-parallel, but
    # the P.V transposer, the shared p/q operands, the SE assembler + SM softmax, the P.V drain and the HBM response
    # landing all cross rows: ~1.7-2.0 kb per cell boundary each way for one svc, 3.5-4 kb for a fold pair, vs the
    # 276-b spine of v2.1).  So every svc is ONE partition of 1 x 2 cells (1442.88 x 2453.76, > 1.2 mm -> L4 2-cycle
    # hop budget + internal stations): svc_2k at rows 1-2 (abuts the HBM PHY row: holds its HBM controller pair and
    # Engram tap pair), svc_2k+1 at rows 3-4 (holds irg_k).  The fold rung is the svc_2k | svc_2k+1 face, the attn
    # rails are the E/W faces between svc columns (2.45-mm faces).
    # Layout (the 2 x 8 attn ladder: fold rungs svc_2k <-> svc_2k+1 + even/odd rails 2k <-> 2k+2): column k (col 7+k) =
    # pair k, svc_2k at rows 1-2 (abuts the HBM PHY row), svc_2k+1 at rows 3-4; each svc partition is 1 x 2 cells
    # (1442.88 x 2453.76).  Rails cross the 2.45-mm E/W faces (~0.5); the fold face is 1.44 mm.  To keep only the fold
    # rung (~4.3 kb) and the odd svc's HBM request/read (rq 682 + rd 562) on that face, both HBM controllers, both
    # Engram taps and irg_k sit in the lower partition svc_2k (their mutual traffic stays inside).
    svcg = {}
    for k in range(8):
        for j2 in range(2):
            n = 2 * k + j2
            m = blk["rsv_%02d" % n]["master"]
            cont = [C("u_rsv", m, "rework",
                      note="whole svc (attention engine + sx + SE/SM + P.V + HBM request/landing); not bit-sliceable")]
            if j2 == 0:
                cont += [C("u_ctrl_a", "dsfd_ctrl_rg3_native32", "reuse"),
                         C("u_ctrl_b", "dsfd_ctrl_rg3_native32", "reuse"),
                         C("u_etap_a", "dsdv_eng_tap_w" if n == 0 else "dsdv_eng_tap", "reuse"),
                         C("u_etap_b", "dsdv_eng_tap", "reuse"),
                         C("u_irg", "dsdv_idx_rg3", "rework",
                           note="irg_k flattened into svc_2k as a planned hard core (57.5-79.9k cells, 45 SRAM); the "
                                "bottom-up rg3 sub-tiles (br/bs01/bs23/bx/bxm/bxmh) are superseded")]
            nm = "svc_%d" % n
            svcg[nm] = add(Part(nm, "svc", 7 + k, 1 + 2 * j2, nr=2, orient="R0" if k < 4 else "MY", contents=cont,
                                ckey="svc_%s_%s%s" % ("lo" if j2 == 0 else "hi", m, "_w" if n == 0 else ""),
                                group="svc_pair_%d" % k))
    # slices (v3): one slice = 6 landed bands of the as-built kit (k8c floorplan: lf4 | lf3 | lf2 | C | lf1 | lf0, each
    # ~1.12 mm tall): 5 identical leaf bands ot_s81sl_leaf (vp/vn/ve/vsw/vq/vs/rxsf/rxsb, ~2.15 M cells each) and one
    # hub band C (xgt_xo, xrt, xfin, eg, capc5r + landing, ~0.7-0.9 M cells).  Each band is one 1-cell partition: the
    # leaf partition is ONE replicated content type for every slice; every external slice lane ends at C (x/rt, xring,
    # xtier, bi/bo, unit, sid); lep slices add an LP partition (lep core + coll lanes + MU land) for the SerDes rx/tx.
    # C sits on row 8 (S) / 15 (N) for every slice, so xring (C<->C, 1104 b each way) runs straight along one row.
    slices = {}
    colmap = {0: (6, 2), 1: (8, 1), 2: (9, 1), 3: (10, 1), 4: (11, 1), 5: (12, 1), 6: (13, 1), 7: (14, 2)}
    CROW = {"S": 8, "N": 14}
    for k in range(8):
        c0, ncol = colmap[k]
        for half, (r0, nrow) in (("S", (5, 7)), ("N", (12, 7))):
            hn = "s_%d%s" % (k, half)
            if hn == "s_3S":
                r0, nrow = 6, 6          # (10,5) = seqhost, beside the svc band
            if hn in ("s_0S", "s_7S"):
                r0, nrow = 0, 12
            if hn == "s_0S":
                r0, nrow = 2, 10         # S81-XDIE: (6,0)-(6,1) = lk_WS3
            # S81-XDIE: s_7N no longer takes the top row (14-15,19) = lk_EN2 (was nrow 8)
            m = blk[hn]["master"]
            lep = ncol == 2
            # inner (centre-side) column carries the normal slice; the outer column of a lep holds LP + stations
            inner = c0 + 1 if (lep and k < 4) else c0
            outer = c0 if (lep and k < 4) else (c0 + 1 if lep else None)
            cr = CROW[half]
            cells = sorted({(c0 + dc, r0 + dr) for dc in range(ncol) for dr in range(nrow)
                            if not (r0 + dr < 5 and (c0 + dc) in range(7, 15))})
            col_rows = sorted(r for (c, r) in cells if c == inner)
            # leaves: 5 cells of the inner column, split below/above C to balance the two C faces, which also carry
            # this slice's x/rt lanes to its frame x rows (1104 + 3 x 70 b per chain); ~1265 b per leaf beyond the face
            side = "W" if k < 4 else "E"
            xr_ch = [x_row(fr) for fr in range(6) for ch in ROWPLAN[side][fr] if ch == hn]
            xb = sum(1 for x in xr_ch if x < cr) * 1314
            xa = sum(1 for x in xr_ch if x > cr) * 1314
            below = [r for r in col_rows if r < cr][::-1]
            above = [r for r in col_rows if r > cr]
            best = None
            for nb in range(0, 6):
                na = 5 - nb
                if nb > len(below) or na > len(above):
                    continue
                cost = max(xb + 1265 * nb, xa + 1265 * na)
                if best is None or cost < best[0]:
                    best = (cost, nb, na)
            _, nb, na = best
            leaf_rows = below[:nb] + above[:na]
            roles = {}
            roles[(inner, cr)] = "C"
            for i, r in enumerate(sorted(leaf_rows, key=lambda r: (abs(r - cr), r))):
                roles[(inner, r)] = "L%d" % i
            if lep:
                roles[(outer, cr)] = "LP"
            segs = {}
            for (c, r) in cells:
                role = roles.get((c, r), "X")
                orient = "R0" if k < 4 else "MY"
                if role == "C":
                    cont = [C("u_c", "%s.C" % m, "rework",
                              note="slice hub band C: xgt_xo + xrt + xfin + eg + capc5r + the slice landing (k8c kit "
                                   "band y 3412.8-4579.2); every external slice lane ends here")]
                    ck = "%s.C" % m
                elif role.startswith("L") and role != "LP":
                    lm = "ot_s81sl_kv_leaf" if m == "dsdv_slice_kv512" else "ot_s81sl_leaf"
                    cont = [C("u_lf", lm, "rework",
                              note="one landed leaf band (vp 16 hcpl, vn, ve, vsw, vq, vs, rxsf, rxsb); leaf index "
                                   "k arrives in-band on dn (+3 b) from C (no strap)")]
                    ck = lm
                elif role == "LP":
                    cont = [C("u_lp", "%s.LP" % m, "rework",
                              note="lep core region K + coll lanes (u_ln*) + MU land (ML): SerDes rx/tx end here")]
                    ck = "%s.LP" % m
                else:
                    cont = []
                    ck = "slice_station"
                pname = "%s_%s" % (hn, role if role != "X" else "x%d%d" % (c - c0, r - r0))
                if pname in PF_DROP_X:          # S81/PORTFIX: empty station cell (no lane), left free
                    PF_FREE.append((c, r, pname))
                    continue
                p = add(Part(pname, "slice", c, r,
                             orient=orient, contents=cont, ckey=ck, group=hn))
                p.role = role
                segs[(c - c0, r - r0)] = p
            slices[hn] = dict(master=m, c0=c0, r0=r0, ncol=ncol, nrow=nrow, segs=segs, k=k, half=half,
                              C=next(q for q in segs.values() if q.role == "C"),
                              LP=next((q for q in segs.values() if q.role == "LP"), None),
                              leaves=[q for q in segs.values() if q.role.startswith("L") and q.role != "LP"])
    # units row 19: WN3 (6-7) | (8 free: bk_col retired, S81/H4) | gunit 9-10 | bk_sel 11-13 | s_7N top (14-15)
    # S81/H4 10-24 (TOK-DS H3 + COORD 22:00): bk_col (dsfd_bk_collector / dsdv_bk_col, the column-1 V-rung row collector)
    # has no consumer in v4.8: no compiler job emits bk_col frames (dv_layer_compile attn.gather GAP: "nothing produces
    # bk_col frames"), the gather is the svc-local SEL_IDS fetch + ROWS frames (dsdv_svc_att types 7 / 6).  The partition
    # is dropped; its 4 rung lanes become the plain column-1 rung s_1S_C <-> s_1N_C (as columns 2 / 5: RETIRED_RUNG).
    add(Part("gunit", "unit", 9, 19, nc=2, contents=[C("u_gunit", "dsdv_gunit", "rework", params={"SID": "4'd3"},
                                                       note="re-aspected 950x1469 -> 2-cell row slot")],
             ckey="gunit"))
    add(Part("bk_sel", "unit", 11, 19, nc=3, contents=[C("u_bk_sel", "dsdv_bk_sel_vmtx", "rework",
                                                        params={"TAP_K": "8'h11", "SINK_K": "8'h10", "IK": "3'd4",
                                                                "EK": "3'd5", "UID": "8'h5B", "EG_N": "1'b0"},
                                                        note="re-aspected 907x4536 -> 3-cell row slot")],
             ckey="bk_sel"))
    add(Part("eng", "unit", 14, 0, contents=[C("u_eng", "dsdv_eng_rr")], ckey="eng"))
    chans = [dict(rect_um=[X0 + c * PX, X0 + r * PY, X0 + (c + 2) * PX, X0 + (r + 1) * PY],
                  reason="die-corner end of the SerDes PHY row: bump/ESD keep-out of the corner PHY (no logic routes "
                         "here; both neighbours are PHY or seal ring)")
             for c, r in ((20, 0),)]          # S81-XDIE: (0,0) = lk_WS2, (20,19) = lk_EN3
    # S81/H4 10-24: the cell bk_col held (retired, see above) carries no logic: top-edge cell between lk_WN3 and gunit, on
    # no lane path (every lane of this corner runs on row 18 / the slice columns); left free for die PG / decap
    chans.append(dict(rect_um=[X0 + 8 * PX, X0 + 19 * PY, X0 + 9 * PX, X0 + 20 * PY],
                      reason="free cell of the retired bk_col (S81/H4: no consumer in v4.8); top edge between lk_WN3 and "
                             "gunit, no lane routes here"))
    for c, r, pname in PF_FREE:
        chans.append(dict(rect_um=[X0 + c * PX, X0 + r * PY, X0 + (c + 1) * PX, X0 + (r + 1) * PY],
                          reason="free cell (S81/PORTFIX 10-25): %s was an empty slice station (no lane passes it), top "
                                 "edge; left free for die PG / decap" % pname))
    return parts, frames, serdes, slices, chans, svcg


# ---------------------------------------------------------------------------------------------- logical lanes
def frame_mapping(ab):
    blk = {b["name"]: b for b in ab["blocks"]}
    srv = collections.defaultdict(list)
    for l in ab["links"]:
        if l["c"] == "ret":
            srv[ab["blocks"][l["e"][1][0]]["name"]].append(ab["blocks"][l["e"][0][0]]["name"])
    groups = {}
    for s, fr in srv.items():
        fr = sorted(fr)
        chains = [fr[i:i + 3] for i in range(0, len(fr), 3)]       # [01,02,03] / [10,12,13] per chain
        groups[s] = [[(f, blk[f]["master"]) for f in ch] for ch in chains]
    return groups


# side -> frame row -> (inner half, outer half); S rows fr 0..2, N rows 3..5; x rows = 3 + 3 fr
ROWPLAN = {"W": {0: ("s_0S", "s_0S"), 1: ("s_2S", "s_2S"), 2: ("s_1S", "s_3S"),
                 3: ("s_1N", "s_3N"), 4: ("s_2N", "s_2N"), 5: ("s_0N", "s_0N")},
           "E": {0: ("s_7S", "s_7S"), 1: ("s_5S", "s_5S"), 2: ("s_6S", "s_4S"),
                 3: ("s_6N", "s_4N"), 4: ("s_5N", "s_5N"), 5: ("s_7N", "s_7N")}}
LK_ROLE = {1: "LK_HEAD", 2: "LK_MID", 3: "LK_TAIL", 4: "LK_HEAD", 5: "LK_MID", 6: "LK_TAIL"}


# DEC12 (S81 parent ruling 2026-10-24): fold-rung sub-buses (dsdv_svc_rs receive port stems) that go 2-beat; only
# sub-buses whose static-schedule duty is <= 50% qualify (TOK-DS calendar).  gi = score gather go/gi (2132 + v),
# si = scatter (1076 + v), ri = P.V return (514), up = status (16), dn = the q / hw stream (805, high duty: never).
FOLD_2BEAT = tuple(x for x in os.environ.get("S81_FOLD_2BEAT", "gi").split(",") if x)


def fold_pair(a, b):
    """DEC12: svc_2k <-> svc_2k+1 (the fold rung of svc column k)."""
    m = [re.match(r"svc_(\d+)$", x) for x in (a, b)]
    return all(m) and int(m[0].group(1)) // 2 == int(m[1].group(1)) // 2


def x_row(fr):
    return 3 + 3 * fr


def lanes_all(ab, census, parts, frames, serdes, slices, v47=False):
    P = {p.name: p for p in parts}
    groups = frame_mapping(ab)
    lanes = []
    fmap = {}

    def L(lid, src, sbus, dst, dbus, width, kind="data", cls="data", role=None, path=None, fixed=0, beats=0,
          word_bits=0):
        lanes.append(dict(id=lid, src=(src, sbus), dst=(dst, dbus), width=int(width), kind=kind, cls=cls,
                          role=role or cls, path=path, fixed=fixed, **({"beats": beats, "word_bits": int(word_bits)}
                                                                       if beats else {})))

    def cell_of(seg):
        return (seg.c0, seg.r0)

    # ---- frames: contents + internal + chain + x/ret lanes ----
    for side in "WE":
        used = collections.Counter()
        for fr in range(6):
            inner, outer = ROWPLAN[side][fr]
            ch_in = groups[inner][used[inner]]
            used[inner] += 1
            ch_out = groups[outer][used[outer]]
            used[outer] += 1
            for pos in range(1, 7):
                f, m = (ch_in if pos <= 3 else ch_out)[(pos - 1) % 3]
                h = "h10" if m == "col_h10" else "h9"
                fmap["f%s%d_p%d" % (side, fr, pos)] = f
                for b in range(3):
                    p = frames[(side, fr, pos, b)]
                    prm = {}
                    if b == 0:
                        prm = {"LK": LK_ROLE[pos], "XO_EN": 0 if pos in (3, 6) else 1}
                    p.contents = [C("u_r%d" % b, "col_%s_l4_lp.r%d" % (h, b), "rework", params=prm or None,
                                    note="region r%d of the landed frame col_%s (ROM image per instance)" % (b, h))]
                    p.ckey = "col_%s.r%d" % (h, b) + ((".p%d" % pos) if b == 0 else "")
                    p.group = f
                fb = [frames[(side, fr, pos, b)].name for b in range(3)]
                for a, bb, w in frame_internal(h):
                    ia, ib = int(a[1]), int(bb[1])
                    L("fi_%s%d_p%d_%s%s" % (side, fr, pos, a, bb), fb[ia], "%s%s_o" % (a, bb), fb[ib], "%s%s_i" % (a, bb),
                      w, cls="frame_int", role="fi_%s%s" % (a, bb),
                      fixed=1 + FRAME_BAND_STATION_EDGES[h][(a, bb)])   # band RTL seam = K + 1 = 3 edges; + stations
            b0 = {pos: frames[(side, fr, pos, 0)].name for pos in range(1, 7)}
            xr = x_row(fr)
            for chain, (half, base) in (("in", (inner, 1)), ("out", (outer, 4))):
                sl = slices[half]
                # emitting segment: the half's segment on the x row, at the column nearest the array; fr0 S rows sit
                # one row below the S halves -> the bottom segment, path turns S then W/E
                seg = sl["C"]       # v3: every external slice lane ends at the hub band C
                tag = "%s%d_%s" % (side, fr, chain)
                L("x_" + tag, seg.name, "xc_%s" % chain, b0[base], "x_i", XW, cls="x",
                  role="x_" + chain, path=("xrow", side, xr))
                L("xo_%s_a" % tag, b0[base], "xo_o", b0[base + 1], "x_i", XW, cls="xo", role="xo")
                L("xo_%s_b" % tag, b0[base + 1], "xo_o", b0[base + 2], "x_i", XW, cls="xo", role="xo")
                for k in range(3):
                    L("rt_%s_%d" % (tag, k), b0[base + k], "ret_o", seg.name, "rt_%s%d" % (chain, k), RW, cls="ret",
                      role="ret_p%d" % (base + k), path=("xrow", side, xr))
    # ---- intra-slice lanes (v3, from the slice RTL): C -> leaf dn 594 b (+3 b leaf index k, was a strap), leaf -> C
    #      up 667 b + fault 1 b; lep C <-> LP (lep core / coll lanes / MU land): S<->K transport, budget 1104 b each way
    #      (lep<->u_sl widths not extracted yet: ESTIMATE, flagged) ----
    for hn, sl in slices.items():
        c = sl["C"]
        for lf in sl["leaves"]:
            L("dn_%s" % lf.name, c.name, "dn_%s_o" % lf.role, lf.name, "dn_i", 597, cls="leafdn", role="leafdn")
            L("up_%s" % lf.name, lf.name, "up_o", c.name, "up_%s_i" % lf.role, 668, cls="leafup", role="leafup")
        if sl["LP"] is not None:
            L("kd_%s" % hn, c.name, "kd_o", sl["LP"].name, "kd_i", 1104, cls="lepk", role="lepk")
            L("ku_%s" % hn, sl["LP"].name, "ku_o", c.name, "ku_i", 1104, cls="lepk", role="lepk")
    # ---- as-built non-frame traffic from the die census (v3: census-driven, so nothing is dropped; plan.json links
    #      lacked e.g. the HBM PHY -> controller read return).  instance -> partition, bus-aware for lep slices ----
    blkcls = {}
    for l in ab["links"]:
        if l["c"] in ("x_frame", "ret"):
            continue
        sn = ab["blocks"][l["e"][0][0]]["name"]
        for e in l["e"][1:]:
            blkcls.setdefault((sn, ab["blocks"][e[0]]["name"]), collections.Counter())[l["c"]] += int(l["b"])
    svc_part = {}
    for n in range(16):
        svc_part["rsv_%02d" % n] = "svc_%d" % n
        svc_part["ctrl_%02d" % n] = "svc_%d" % (2 * (n // 2))
        svc_part["etap_%02d" % n] = "svc_%d" % (2 * (n // 2))
    for k in range(8):
        svc_part["irg_%02d" % k] = "svc_%d" % (2 * k)

    def ipart(inst, bus):
        b = inst[2:]
        if b in svc_part:
            return svc_part[b]
        if b in slices:
            sl = slices[b]
            if sl["LP"] is not None and re.match(LP_BUS_RE_V47 if v47 else LP_BUS_RE, bus or ""):
                return sl["LP"].name
            return sl["C"].name
        return b if b in P else None

    rows = census_collapse(census)
    seen = {}
    agg = collections.OrderedDict()
    unmapped = []
    for r in rows:
        if r["kind"] == "reset" or r["src"] == "PORT" or r["dst"] == "PORT":
            continue
        if r["src"].startswith("u_f_") or r["dst"].startswith("u_f_"):
            continue                 # frame x/xo/ret: planned above (x via the xo relay chain)
        ps, pd = ipart(r["src"], r["src_bus"]), ipart(r["dst"], r["dst_bus"])
        if ps is None or pd is None:
            unmapped.append(r)
            continue
        if ps == pd:
            continue
        key = (r["src"], r["src_bus"], r["dst"])
        b = int(r["bits"])
        if b <= seen.get(key, 0):
            continue
        add_b = b - seen.get(key, 0)
        seen[key] = b
        cc = blkcls.get((r["src"][2:], r["dst"][2:]))
        c = cc.most_common(1)[0][0] if cc else ("hbmrd" if r["src"] == "u_phy_hbm" else r["kind"])
        c = r.get("cls") or c                         # S81/H4: a retired rung unit's rows stay V-rung (xtier) lanes
        if not v47 and c == "attn" and fold_pair(ps, pd) and re.sub(r"_[dv]$", "", r["dst_bus"]) in FOLD_2BEAT:
            c = "attnh"         # DEC12: a low-duty fold sub-bus -> the 2-beat lane
        agg.setdefault((ps, pd, c), 0)
        agg[(ps, pd, c)] += add_b
    if unmapped:
        raise SystemExit("census rows without a partition: %s" % unmapped[:5])
    for (ps, pd, c), b in agg.items():
        kind = "ctl" if c == "ctl" else "data"
        if c == "attnh":
            # DEC12 option (A) (S81 parent 2026-10-24, ruling 9.3): the LOW-DUTY fold sub-buses (FOLD_2BEAT) of the svc
            # fold rung svc_2k <-> svc_2k+1 travel 2-beat on their own lane attnh__<a>__<b> (bus attnh_<peer>_o/i):
            # word = the selected sub-buses concatenated in FOLD_2BEAT order (each {v, d}); port = {beat, payload[P-1:0]},
            # P = ceil(b / 2): beat 0 = word[P-1:0], beat 1 (next cycle) = word[b-1:P] (payload bit P-1 = 0 in beat 1
            # when b is odd); the word lands 1 cycle after the last beat (latency word_cycles).  The high-duty dn
            # stream and the rest stay full width on attn__<a>__<b>.
            L("%s__%s__%s" % (c, ps, pd), ps, "%s_%s_o" % (c, pd), pd, "%s_%s_i" % (c, ps), -(-b // 2) + 1,
              kind=kind, cls=c, role=c, beats=2, word_bits=b)
            continue
        L("%s__%s__%s" % (c, ps, pd), ps, "%s_%s_o" % (c, pd), pd, "%s_%s_i" % (c, ps), b, kind=kind, cls=c, role=c)
    # ---- v4.8 (S81-P9-R8EQ): bound-top crossings the as-built census lacks (inputs/bound_supplement_v48.json, from the
    #      BINDER4 b3r8 UNPLANNED list): svc_rs chain svc_2k -> svc_2k+1 and the slice C -> LP 1-b lep inputs ----
    for e in ([] if v47 else json.load(open(BOUND_SUPP))["entries"]):
        ps, pd, c = e["src"], e["dst"], e["cls"]
        assert ps in P and pd in P, e
        L("%s__%s__%s" % (c, ps, pd), ps, "%s_%s_o" % (c, pd), pd, "%s_%s_i" % (c, ps), e["bits"], cls=c, role=c)
    # ---- S81-XDIE 10-24: copy-A/B reserve pair (RELEASE_RACK 2.1): every layer die carries EN2/EN3 (s_7N pair B) and
    #      WS2/WS3 (s_0S pair B); one logic design, wired on the 64 pre/post-group dies.  Same circuit as pair A: per
    #      SerDes a 512-b tx lane LP -> lk (coll) and a 514-b rx lane lk -> LP (coll), ending at the lep LP partition.
    #      RTL (S81-XDIE 10-24): s_0S -> ot_s81sl_slice_lepw_mab_mu_72, s_7N -> ot_s81sl_slice_lepe_mab_mu_72 (lep
    #      ot_s81sl_lep_mu_hab), bind overlay tools/s81_dv/release72/mu72_overlay_xdie.json (tx2/tx3/rx2/rx3). ----
    if not v47:
        for half, names in (("s_7N", ("EN2", "EN3")), ("s_0S", ("WS2", "WS3"))):
            lp = slices[half]["LP"].name
            for nm in names:
                lk = "lk_" + nm
                L("coll__%s__%s" % (lp, lk), lp, "coll_%s_o" % lk, lk, "coll_%s_i" % lp, 512, cls="coll", role="coll")
                L("coll__%s__%s" % (lk, lp), lk, "coll_%s_o" % lp, lp, "coll_%s_i" % lk, 514, cls="coll", role="coll")
    # ---- S81/H4 10-24 (COORD H4 ruling = option A): the index RANK TREE lanes of the bk_sel master dsdv_bk_sel_vmtx.
    #      tl_o (its dsdv_idx_tx tree transmitter, the lane to the parent die) and ca / cb (the two landed child lanes into
    #      dsdv_idx_vmux) end at the s_0N lep (LP), which owns the STAGE circuits: the tree (lower_bk shard_tree) spans the
    #      k = 3 / 6 adjacent stages of one rank, i.e. stage NEXT = pair A (WN0/1) and stage PREV = pair B (WN2/3); the
    #      TP4 peer circuits (s_0S / s_7S / s_7N pair A) join ranks of the SAME stage and carry no tree edge.  The lep
    #      sends a tl beat as an IDX link frame (lane field 2 -> pair A, 3 -> pair B) and demuxes received IDX frames:
    #      pair B (from PREV) -> ca, pair A (from NEXT) -> cb (ot_s81sl_lep_mu_ab_idx).  276 b each, registered, ft <= M7.
    if not v47:
        # path: only slice STATION cells (row 18 x06/x16 of s_4N..s_0N, then s_0N's outer column x05..x03): no leaf, hub
        # or unit type gains a slot; the LP is entered on its N face (the coll lane face)
        lp = slices["s_0N"]["LP"].name
        lpc = (slices["s_0N"]["LP"].c0, slices["s_0N"]["LP"].r0)
        up = [(P["bk_sel"].c0, P["bk_sel"].r0), (P["bk_sel"].c0, 18), (lpc[0], 18), lpc]
        L("tl__bk_sel__%s" % lp, "bk_sel", "tl_o", lp, "tl_i", 276, cls="tl", role="tree", path=("cells", up))
        L("ca__%s__bk_sel" % lp, lp, "ca_o", "bk_sel", "ca_i", 276, cls="ca", role="tree", path=("cells", up[::-1]))
        L("cb__%s__bk_sel" % lp, lp, "cb_o", "bk_sel", "cb_i", 276, cls="cb", role="tree", path=("cells", up[::-1]))
        # ---- S81/IDXNET 10-25 (S81 DECISION 1, topk_final): the TP4 merge of the 4 rank roots, a two-step exchange with no
        #      single root.  Step 1 swaps candidates with the d+2 peer over the s_7N TP circuit (pair A, both ways); step 2
        #      sends to d+1 over s_7S and receives from d-1 over s_0S (pair A).  bk_sel's TX (dsdv_idx_tx re-encoder) feeds
        #      tpn_o / tps_o by the TX job's DST field; the peer lists land on bk_sel tpn_i (s_7N) and, for s_0S, on the s_0N
        #      lep's ca (tm_i merge: col 6 rows 15-18 are at face load 0.57, no 4th lane there; rows 9-13 are empty).
        #      276 b each, registered, ft <= M7, fixed station-only paths (col 15 / row 18 / col 6 rows 9-13), routed last.
        lp7n, lp7s, lp0s = (slices[k]["LP"].name for k in ("s_7N", "s_7S", "s_0S"))
        c7n = (slices["s_7N"]["LP"].c0, slices["s_7N"]["LP"].r0)
        c7s = (slices["s_7S"]["LP"].c0, slices["s_7S"]["LP"].r0)
        c0s = (slices["s_0S"]["LP"].c0, slices["s_0S"]["LP"].r0)
        bke = (P["bk_sel"].c0 + P["bk_sel"].nc - 1, P["bk_sel"].r0)        # bk_sel E cell, S face
        tpn = [bke, (bke[0], 18), (c7n[0], 18), c7n]
        L("tp__bk_sel__%s" % lp7n, "bk_sel", "tpn_o", lp7n, "tp_i", 276, cls="tp", role="idxnet", path=("cells", tpn))
        L("tp__%s__bk_sel" % lp7n, lp7n, "tp_o", "bk_sel", "tpn_i", 276, cls="tp", role="idxnet", path=("cells", tpn[::-1]))
        L("tp__bk_sel__%s" % lp7s, "bk_sel", "tps_o", lp7s, "tp_i", 276, cls="tp", role="idxnet",
          path=("cells", [bke, (bke[0], 18), (c7s[0], 18), c7s]))
        L("tp__%s__%s" % (lp0s, lp), lp0s, "tp_o", lp, "tm_i", 276, cls="tp", role="idxnet", path=("cells", [c0s, lpc]))
        # ---- S81/IDXNET 10-25 (S81 DECISION 2, rank-tree query fan-out): iqf (dsdv_idx_qf) <-> the s_0N lep.  ql (513 b,
        #      every Q word received from stage PREV) and qc (the root's own tree frame, 2-beat 258 b {256 data, beat, v}: a
        #      513-b qc would put the s_0S_LP S face at 0.607 > 0.60).  Path iqf -> svc_0 (S in, W out) -> col 6 north
        #      (s_0S_x00..x05, s_0S_LP, s_0S_x07..x09, s_0N_x00/x01) -> s_0N_LP S face; column 7 above svc_0 is leaves/hubs
        #      already over 0.6.  The lep relays Q frames NEXT-ward itself (cut-through, header relay count), qc1 is gone.
        iqc = (P["iqf"].c0, P["iqf"].r0)
        qp = [lpc, (lpc[0], iqc[1] + 2), (iqc[0], iqc[1] + 2), iqc]
        L("ql__%s__iqf" % lp, lp, "ql_o", "iqf", "ql_i", 513, cls="ql", role="idxnet", path=("cells", qp))
        L("qc__iqf__%s" % lp, "iqf", "qc_o", lp, "qc_i", 258, cls="qc", role="idxnet", path=("cells", qp[::-1]))
    # ---- ID rings (no tie-offs): slice sid + fault OR, svc sid; counted (sid_o = sid_i + 1), rooted at seqhost ----
    order_s = [slices["s_%dS" % k]["C"].name for k in range(7, -1, -1)] + \
              [slices["s_%dN" % k]["C"].name for k in range(8)]
    ring = ["seqhost"] + order_s + ["seqhost"]
    # S81/PORTFIX 10-25 (S81 DECISION 4): the rings carry ONE bit, the sticky fault OR (ot_s81_frs ring stops: fo <=
    # fi | own sticky fault), into seqhost (sid_ri / vid_ri), which reports the die fault word to the host in-band.  The
    # slice / svc ids stay declared position straps (partition parameters), so the 4-b id field is gone: sid 5 -> 1 b,
    # vid 4 -> 1 b (v4.8 only; the v4.7 route replay keeps the old widths so no v4.7 lane moves).
    for a, b in zip(ring, ring[1:]):
        L("sid_%s__%s" % (a, b), a, "sid_o" if a != "seqhost" else "sidr_o", b, "sid_i" if b != "seqhost" else "sidr_i",
          5 if v47 else 1, kind="ctl", cls="sid", role="sid")
    svc_ring = ["seqhost"] + ["svc_%d" % n for n in list(range(0, 16, 2)) + list(range(15, 0, -2))] + ["seqhost"]
    for a, b in zip(svc_ring, svc_ring[1:]):
        L("vid_%s__%s" % (a, b), a, "vid_o" if a != "seqhost" else "vidr_o", b, "vid_i" if b != "seqhost" else "vidr_i",
          4 if v47 else 1, kind="ctl", cls="vid", role="vid")
    # S81/PORTFIX 10-25 (DECISION 4): 1-b unit fault feeders into the nearest ring stop (a short unit chain): units with
    # no ring stop of their own (iqf, eng, the HBM PHY macro k_oor, bk_sel, gunit) and each lep LP partition (MU
    # lane-landing fault) -> the adjacent ring member.  bk_sel -> gunit -> s_3N_C is the top-edge unit chain.
    if not v47:
        feed = [("iqf", "svc_0"), ("eng", "svc_14"), ("phy_hbm", "svc_8"), ("bk_sel", "gunit"),
                ("gunit", slices["s_3N"]["C"].name)] + \
               [(slices[h]["LP"].name, slices[h]["C"].name) for h in ("s_0N", "s_0S", "s_7N", "s_7S")]
        for a, b in feed:
            L("flt__%s__%s" % (a, b), a, "flt_o", b, "flt_i", 1, kind="ctl", cls="flt", role="flt")
    fmap = dict(frames=fmap, inst_part={("u_" + k): v for k, v in svc_part.items()},
                slice_part={("u_" + hn): dict(C=sl["C"].name, LP=sl["LP"].name if sl["LP"] is not None else None)
                            for hn, sl in slices.items()})
    return lanes, fmap


# measured Yosys counts (PLAN-S81v3 10-23 search; sources in cells_sources.md)
LEAF_CORES = [("vp_a", 36056 + 6 * 50540), ("vp_b", 5 * 50540), ("vp_c", 5 * 50540),      # vp own + 16 hcpl 6/5/5
              ("ve_a", 460279 // 2), ("ve_b", 460279 - 460279 // 2),                       # ve 460,279 > cap: split x2
              ("vn", 375145), ("vs_vsw", 117971 + 120703), ("vq_rx", 46676 + 82916 + 99597)]
C_CORES = {"xrt1": [("eg", 261681), ("xg_xr", 174928 + 67849), ("xf_cap", 135954 + 22959)],
           "xrt3": [("eg", 261681), ("xg_xr", 174928 + 78456), ("xf_cap", 135954 + 22959)]}
# S81-XDIE 10-24 (reserve pair on every die): s_0S = the copy-A/B top of s_0N (lepw_mab_mu_72: lep_mu_ab + 4 lanes, same
# measured count); s_7N = lepe_mab_mu_72 (lep_mu_hab + 4 lanes): ESTIMATE lep_mu_h 67,042 + the measured A/B endpoint delta
# lep_mu_ab - lep_mu_a 37,221 (no Yosys count of lep_mu_hab yet)
LP_CELLS = {"dsdv_slice_lepw_mu": 88962 + 4 * 67956 + 4703, "dsdv_slice_lepw_mus": 88962 + 4 * 67956 + 4703,
            "dsdv_slice_lepe_mu": 67042 + 37221 + 4 * 67956 + 4703, "dsdv_slice_lepe_nh_mus": 51741 + 2 * 67956 + 4703}
UNIT_CORES = {
    "eng": ([("eng_rr_a", 418942 // 2), ("eng_rr_b", 418942 - 418942 // 2)], "dsdv_eng_rr 418,942 (F ep7 ref_gate "
            "dsdv_eng_rr_b) > cap: 2 planned cores"),
    "gunit": ([("l0_l1_l2", 8213 + 110419 + 9853 + 43954 + 8215), ("l3_l4", 40887 + 81348 + 73342),
               ("l5f", 97736)], "dsdv_gunit = sum of closed leaves (instance counts not confirmed)"),
    "bk_sel": ([("bksel_c_pa", 260094), ("bksel_q01", 2 * 113262), ("bksel_q23", 2 * 113262),
                ("bkg_tx_vmux", 2 * 25144 + 31602 + 3547 + 2600)], "dsdv_bk_sel_vmtx parts (whole pa_lp 1,243,436); S81/IDXNET 10-25 +2,600 est: dsdv_idx_vmux6 2 more inputs + tl/tpn/tps/loop regs 4 x 276"),
    "bk_col": ([], "bk_col FLATTENED: Yosys (PLAN-S81v4-SYN 10-23, ORFS asap7lock RVT) dsdv_bkcol_l 15,770 x4 (2 SRAM "
               "each) + dsdv_bkcol_m 73,514 + bk_g 2 x 25,144 measured = 186,882 cells, 8 SRAM macros"),
    "seqhost": ([("sh_children", 6989 + 11889 + 69671 + 40770)], "seq_host_mux children (sh_vc, mu_hslot, mu_hwin, "
                "seq_host_c_r3_lp); whole MISSING"),
    "iqf": ([("idx_qf", 11296 + 540)], "dsdv_idx_qf 11,296 (F gold2) + S81/IDXNET qc serializer ~540 (256 hold + 258 out + copies) - qc1 513 flops not removed from the estimate (conservative)"),
}


def cells_core_plan(p):
    """(cores [(name, cells)], glue cells, basis) for one partition (L1: cores <= 400k, glue flattened)."""
    if p.kind in ("phy", "serdes"):
        return [], 0, "hard PHY model (no std cells counted)"
    if p.kind == "frame":
        m = p.contents[0]["module"] if p.contents else ""
        band = m.rsplit(".", 1)[-1]
        # Yosys (PLAN-S81v4-SYN 10-23, ORFS asap7lock RVT, kit macro views): col_h9_l4_lp_b0/b1/b2 = 40,939 / 55,340
        # / 26,640 (whole 123,474, 220 macros); col_h10 has no banded RTL: whole 137,178 x the h9 band shares.
        H9 = dict(r0=40939, r1=55340, r2=26640)
        if "h10" in m:
            v = round(137178 * H9[band] / 122919)
            return [], v, "col_h10 band %s ~%d = Yosys whole 137,178 x h9 band share (no banded h10 RTL); flattened" % (
                band, v)
        return [], H9[band], "col_h9 band %s %d Yosys measured (col_h9_l4_lp_b%s); flattened" % (band, H9[band], band[1])
    if p.kind == "svc":
        # S81-P5 10-23: MEASURED attention engine (fresh ORFS Yosys, asap7lock RVT WC, hierarchical, ep9
        # plan-s81v4-syn2/jobs/svc_tile): one tile ot_hdc_v41x_attn_tile_s (H16 TD32 NBANK5 PWORDS2 FPL4 FML6 F12, the
        # dsdv_svc_att engine config) = 3,097,168 cells / 353,319 um2 = 4 head groups hgrp_s (774,424 max: 30,272 local
        # + 4 head datapaths hdp_s of 183,981 max / 20,721 um2).  The engine has NT = NL = 4 tiles -> 12.39 M cells,
        # 1.413 mm2 std area per svc partition.  Cores <= 400k: 64 hdp cores + 16 hgrp cores (local logic, the 4 hdp
        # as macros).  sx_hrow fresh synth 51,397 cells.  Engine staging / P.V glue (dsdv_svc_att whole) still MISSING.
        cores = [("sx_hrow_a", 4 * 51397), ("sx_hrow_b", 4 * 51397)] + \
            [("attn_t%d_g%d" % (t, g), 30272) for t in range(4) for g in range(4)] + \
            [("attn_t%d_g%d_h%d" % (t, g, h), 183981) for t in range(4) for g in range(4) for h in range(4)] + \
            [("se_sm_pv", 18044 + 2 * 1247)]
        glue = 60000
        if any(c["module"].startswith("dsfd_ctrl") for c in p.contents):
            cores.append(("ctrl_etap_irg", 2 * 21592 + 21759 + 21834 + 79867))
        return cores, glue, ("svc: attention engine MEASURED 4 tiles x 3,097,168 = 12,388,672 cells (1.413 mm2 std; "
                             "one 1.770-mm2 lattice cell cannot hold it) as 64 hdp cores 183,981 + 16 hgrp cores 30,272; "
                             "hrow x8 411,176 measured as 2 cores of 4; svc_att staging glue ESTIMATED 60k (whole synth MISSING)")
    if p.kind == "slice":
        role = getattr(p, "role", "X")
        m = p.contents[0]["module"] if p.contents else ""
        if role == "C":
            k = "xrt3" if "c3x" in m else "xrt1"
            return C_CORES[k], 60000, "slice hub: xgt_xo/xrt/xfin/capc5r/eg measured; landing ~40k flops (glue est)"
        if role == "LP":
            mm = m.split(".")[0]
            return [], LP_CELLS[mm], "lep core + coll lanes + MU land measured (flattened, < cap)"
        if role.startswith("L"):
            if "kv_leaf" in m:
                return [("kv_leaf", 62014 + 94804 + 58177 + 84923 + 43505)], 15000, \
                    "MISSING kv512 leaf; SU KV leaves kve/kvp/kvq/kvr/kvt summed"
            return LEAF_CORES, 15000, "ot_s81sl_leaf children measured (vp/vn/ve/vsw/vq/vs/rxsf/rxsb)"
        return [], 5000, "station-only partition (ft flops)"
    if p.name == "seqhost":
        # v4: the MU history window (dsdv_mu_hwin_capture_1019, 69,671 cells + SRAM columns) is a planned hard core
        # (GEOM-REVIEW: SUPERSEDED dsdv_mu_hwin_capture_1019 by seqhost core hwin); the other children flattened
        return [("hwin", 69671)], 6989 + 11889 + 40770 + 10000, \
            "seq_host_mux children: hwin core 69,671 + sh_vc/mu_hslot/seq_host_c_r3_lp flattened (whole MISSING)"
    if p.name in UNIT_CORES:
        c, why = UNIT_CORES[p.name]
        return c, 10000, why
    return [], 0, "MISSING"


# S81/H4 10-24: retired V-rung units {inst: {its rung output bus: the slice that feeds the opposite rung input}}.  The
# as-built census still carries them; their rung rows collapse onto the direct slice <-> slice rung (the unit was a
# fixed-latency transparent stop, ot_dsdv_vstop), every other row of the unit (reset) is dropped with it.
RETIRED_RUNG = {"u_bk_col": {"vo_n": "u_s_1S", "vo_s": "u_s_1N"}}


def retire_rung(rows):
    out = []
    for r in rows:
        if r["dst"] in RETIRED_RUNG:
            continue
        if r["src"] in RETIRED_RUNG:
            rr = dict(r, src=RETIRED_RUNG[r["src"]][r["src_bus"]], src_bus="vo", cls="xtier")
            out.append(rr)
            continue
        out.append(r)
    return out


def census_collapse(rows):
    """landing cells (ld_*) re-attributed to their single source (reset fan-in excluded)."""
    rows = retire_rung(rows)
    into = collections.defaultdict(set)
    for r in rows:
        if r["dst"].startswith("ld_") and r["kind"] != "reset":
            into[r["dst"]].add(r["src"])
    out = []
    for r in rows:
        if r["dst"].startswith("ld_"):
            continue
        s = r["src"]
        for _ in range(16):
            if not s.startswith("ld_"):
                break
            src = into.get(s, set())
            if len(src) != 1:
                raise SystemExit("landing cell %s has sources %s" % (s, sorted(src)))
            s = next(iter(src))
        rr = dict(r)
        if s != r["src"]:
            # keep landing cells apart in the per-driver-bus dedup: every ld output bus is named "o", so the
            # collapsed row is keyed by the landing cell + kind (go_d / so_d / dn_o of one svc land on 3 cells)
            rr["src_bus"] = "%s/%s" % (r["src"], r["kind"])
        rr["src"] = s
        out.append(rr)
    return out


# --------------------------------------------------------------------------------------------------- routing
class Grid:
    def __init__(self, parts):
        self.owner = {}
        self.P = {p.name: p for p in parts}
        for p in parts:
            for c in p.cells():
                assert c not in self.owner, (c, p.name, self.owner.get(c))
                self.owner[c] = p.name
        self.load = collections.Counter()     # (cellA, cellB) sorted -> pins

    def cap(self, a, b):
        lo, hi, _ = span(self.P[self.owner[a]], self.P[self.owner[b]], a, b)
        return FACE_MAX * (hi - lo - 2 * EDGE)

    def fkey(self, a, b):
        # load is booked per shared partition boundary (a wide port may use the whole shared face)
        return bkey(self.owner[a], self.owner[b], a, b)


def bkey(na, nb, a, b):
    return tuple(sorted((na, nb))) + (a[1] == b[1],)


def span(pa, pb, a, b):
    """die-coordinate span (lo, hi) of the boundary shared by pa and pb that the cell step a->b crosses."""
    if a[1] == b[1]:     # side by side -> E/W face along y
        r0 = max(pa.r0, pb.r0)
        r1 = min(pa.r0 + pa.nr, pb.r0 + pb.nr)
        return X0 + r0 * PY, X0 + r1 * PY, True
    c0 = max(pa.c0, pb.c0)
    c1 = min(pa.c0 + pa.nc, pb.c0 + pb.nc)
    return X0 + c0 * PX, X0 + c1 * PX, False


def seg_path(a, b):
    """cells from a to b along a straight line (inclusive)."""
    (x0, y0), (x1, y1) = a, b
    out = []
    if x0 == x1:
        s = 1 if y1 >= y0 else -1
        out = [(x0, y) for y in range(y0, y1 + s, s)]
    else:
        s = 1 if x1 >= x0 else -1
        out = [(x, y0) for x in range(x0, x1 + s, s)]
    return out


def poly_cells(pts):
    out = [pts[0]]
    for a, b in zip(pts, pts[1:]):
        out += seg_path(a, b)[1:]
    return out


def candidates(a, b):
    (ax, ay), (bx, by) = a, b
    if ax == bx or ay == by:
        yield [a, b]
        return
    yield [a, (bx, ay), b]
    yield [a, (ax, by), b]
    lo, hi = sorted((ax, bx))
    for m in range(lo + 1, hi):
        yield [a, (m, ay), (m, by), b]
    lo, hi = sorted((ay, by))
    for m in range(lo + 1, hi):
        yield [a, (ax, m), (bx, m), b]


XCOST = dict(svc=1.2, slice=0.6, unit=0.4, idx=0.4, serdes=0.6)


def route(grid, lanes, slices):
    P = grid.P
    res = {}
    order = sorted(lanes, key=lambda l: (l.get("path") is None, -l["width"]))
    for lk in order:
        s, d = lk["src"][0], lk["dst"][0]
        w = lk["width"] + 1
        if lk.get("path") and lk["path"][0] == "cells":
            # S81/H4: an explicit corner path (cell polyline); every cell between the end partitions must be ft-able
            seq = poly_cells(list(lk["path"][1]))
            assert grid.owner[seq[0]] == s and grid.owner[seq[-1]] == d, (lk["id"], seq[0], seq[-1])
            for c_ in seq[1:-1]:
                q_ = P[grid.owner[c_]]
                assert q_.ft_ok and q_.kind not in ("frame", "serdes"), (lk["id"], c_, q_.name)
        elif lk.get("path") and lk["path"][0] == "xrow":
            _, side, xr = lk["path"]
            # fixed: from the slice segment straight to the array on the x row (turn at the segment if the x row is
            # below the half), then through the frame b0 bands
            sp, dp = P[s], P[d]
            a_cell = (sp.c0, sp.r0)
            if lk["cls"] == "ret":
                a_cell = (dp.c0, dp.r0)
                fcell = (sp.c0, sp.r0)
            else:
                fcell = (dp.c0, dp.r0)
            pts = [a_cell, (a_cell[0], xr), fcell] if a_cell[1] != xr else [a_cell, fcell]
            cells = poly_cells(pts)
            if lk["cls"] == "ret":
                cells = cells[::-1]
            seq = cells
        else:
            both = s in slices and d in slices

            def cells_of(n):
                if n in slices:
                    cs = [c for q in slices[n]["segs"].values() for c in q.cells()]
                    # fixed slice rows per lane class (regular segment types): xring + ID ring on the ring row,
                    # xtier on the S top / N bottom rows
                    row = None
                    if both and lk["cls"] in ("xring", "sid"):
                        row = 7 if n.endswith("S") else 14
                    elif both and lk["cls"] == "xtier":
                        row = 11 if n.endswith("S") else 12
                    if row is not None and any(c[1] == row for c in cs):
                        cs = [c for c in cs if c[1] == row]
                    return cs
                return P[n].cells()
            best = None
            for ca in cells_of(s):
                for cb in cells_of(d):
                    for pts in candidates(ca, cb):
                        cells = poly_cells(pts)
                        cost = len(cells) * 1.0 + 0.3 * (len(pts) - 2)
                        ok = True
                        names = []
                        for c in cells:
                            o = grid.owner.get(c)
                            if o is None:
                                ok = False
                                break
                            if not names or names[-1] != o:
                                names.append(o)
                        if not ok or len(set(names)) != len(names):
                            continue
                        for o in names[1:-1]:
                            q = P[o]
                            if not q.ft_ok or q.kind == "frame" or (q.kind == "serdes" and not (s.startswith("lk_") or d.startswith("lk_"))):
                                ok = False
                                break
                            cost += XCOST.get(q.kind, 0.6)        # station / partition crossing (pin-limited kinds dearer)
                        if not ok:
                            continue
                        over = 0.0
                        for x, y in zip(cells, cells[1:]):
                            if grid.owner[x] == grid.owner[y]:
                                continue
                            k = grid.fkey(x, y)
                            u = (grid.load[k] + w) / grid.cap(x, y)
                            if u > 1.0:
                                over += 1e4
                            elif u > 0.7:
                                cost += 5 * (u - 0.7)
                        cost += over
                        if best is None or cost < best[0]:
                            best = (cost, cells, pts)
            if best is None:
                raise SystemExit("no route for %s" % lk["id"])
            seq = best[1]
            lk["src"] = (grid.owner[seq[0]], lk["src"][1])
            lk["dst"] = (grid.owner[seq[-1]], lk["dst"][1])
        # apply load
        for x, y in zip(seq, seq[1:]):
            if grid.owner[x] != grid.owner[y]:
                grid.load[grid.fkey(x, y)] += w
        res[lk["id"]] = seq
    return res


def route_v48(grid, lanes47, lanes):
    """v4.8 (S81-P9-R8EQ): route the v4.7 lane set first, exactly as v4.7 did (same order, same face loads), and keep
    those routes for every v4.8 lane that is unchanged (id, width, endpoints); only the lanes v4.8 adds or re-ends
    (lep buses C -> LP, bound supplement, the shrunk C lanes) are routed after, on top of the v4.7 loads (the removed
    v4.7 lanes stay as load: conservative).  So no v4.7 lane changes its route or its cycles (no schedule churn)."""
    key = {l["id"]: (l["width"], l["src"][0], l["dst"][0]) for l in lanes47}
    res47 = route(grid, lanes47, {})
    by47 = {l["id"]: l for l in lanes47}
    res, todo = {}, []
    for lk in lanes:
        if key.get(lk["id"]) == (lk["width"], lk["src"][0], lk["dst"][0]):
            o = by47[lk["id"]]
            lk["src"], lk["dst"] = (o["src"][0], lk["src"][1]), (o["dst"][0], lk["dst"][1])
            res[lk["id"]] = res47[lk["id"]]
        else:
            todo.append(lk)
    # S81-XDIE 10-24: the copy-A/B reserve pair lanes route LAST, on top of every v4.8 load, so no existing lane moves
    rsv = [l for l in todo if RESERVE_RE.search(l["id"])]
    tree = [l for l in todo if l["role"] in ("tree", "idxnet")]
    late = [l for l in todo if l["role"] in ("sid", "vid", "flt")]
    res.update(route(grid, [l for l in todo if l not in rsv and l not in tree and l not in late], {}))
    res.update(route(grid, rsv, {}))
    # S81/H4 10-24: the bk_sel tree lanes (fixed station path) are applied after every other lane: no lane moves
    res.update(route(grid, tree, {}))
    # S81/PORTFIX 10-25: the 1-b fault ring / feeder lanes (resized sid / vid, new flt) route after every other lane
    res.update(route(grid, late, {}))
    ROUTE_V48.update(kept=len(res) - len(todo), rerouted=sorted(l["id"] for l in todo))
    return res


ROUTE_V48 = {}
# S81/PORTFIX 10-25 (S81 DECISION 5): PORTBIND audit EMPTY_PARTITION s_1N_x06 / s_5N_x06.  s_1N_x06 is REUSED: the
# S81/H4 bk_sel tree lanes tl / ca / cb cross it on row 18 (3 ft slots).  s_5N_x06 carries no lane: it is not a
# partition; build() leaves it as a free cell (chans)
PF_DROP_X = {"s_5N_x06"}
PF_FREE = []
TYPE_NAMES_OUT = {}
RESERVE_RE = re.compile(r"lk_(WS[23]|EN[23])\b")


def bends(cells):
    dirs = []
    for a, b in zip(cells, cells[1:]):
        d = (b[0] - a[0], b[1] - a[1])
        if not dirs or dirs[-1] != d:
            dirs.append(d)
    return max(0, len(dirs) - 1)


# --------------------------------------------------------------------------------------------- plan emission
def face_dir(a, b):
    d = (b[0] - a[0], b[1] - a[1])
    return {(1, 0): "E", (-1, 0): "W", (0, 1): "N", (0, -1): "S"}[d]


TF = {"R0": {}, "MY": dict(E="W", W="E"), "MX": dict(N="S", S="N"), "R180": dict(E="W", W="E", N="S", S="N")}


def to_type_win(p, face, lo, hi):
    if face in "EW":
        a, b, flip, ext = lo - p.y0, hi - p.y0, p.yflip, p.h
    else:
        a, b, flip, ext = lo - p.x0, hi - p.x0, p.xflip, p.w
    if flip:
        a, b = ext - b, ext - a
    return round(a, 4), round(b, 4), flip


KPRIO = dict(frame=0, serdes=1, svc=2, cte=2, idx=2, slice=3, unit=4, phy=5)


def census_map(plan, lanes, fmap, out):
    """G0 census map (PLAN-TOOL census_cov.py schema): as-built instance -> partition or group.
    groups: a slice (hub C + leaf bands + LP + X stations) is one as-built block; the frames fed by one x relay chain
    (slice -> fA, then xo fA -> fB -> fC) form one group, because the plan re-topologises the as-built slice -> fB/fC x
    broadcast through fA's relay port (the extra hop is in the latency table).  Traffic inside a group is checked at
    partition level by physical/die_plan/s81/census_cov.py (v3/census_cov.json, dropped 0)."""
    names = [p_["name"] for p_ in plan["partitions"]]
    frame_of = {}                                   # plan frame position fW0_p1 -> as-built f_0L01
    for pos, ab in fmap["frames"].items():
        frame_of[pos] = ab
    par = {pos: pos for pos in frame_of}

    def find(x):
        while par[x] != x:
            x = par[x]
        return x
    for ln in lanes:
        if ln["id"].startswith("xo_"):
            a_, b_ = (re.match(r"(f[WE]\d_p\d)_b\d$", n).group(1) for n in (ln["src"][0], ln["dst"][0]))
            par[find(a_)] = find(b_)
    comp = collections.defaultdict(list)
    for pos in frame_of:
        comp[find(pos)].append(pos)
    groups, parts_ = {}, {}
    for root, poss in comp.items():
        g = "xch_" + "_".join(sorted(poss))
        groups[g] = sorted(n for n in names if re.match(r"(f[WE]\d_p\d)_b\d$", n) and n[:6] in poss)
        for pos in poss:
            parts_["u_" + frame_of[pos]] = g
    for hn in fmap["slice_part"]:
        g = hn[2:]
        groups[g] = sorted(n for n in names if n.startswith(g + "_"))
        parts_[hn] = g
    parts_.update(fmap["inst_part"])
    for n in names:
        parts_.setdefault("u_" + n, n)
    parts_["PORT"] = "@die"
    # landing cells (ld_*: the as-built receive-side landing register of a long link) live in the partition of the
    # instance they drive (their data/ctl outputs); a landing cell has data + ctl + reset inputs, so it is mapped,
    # not collapsed
    sink = {}
    for r in CENSUS_ROWS:
        if r["src"].startswith("ld_") and r["kind"] != "reset" and r["dst"] in parts_:
            sink.setdefault(r["src"], set()).add(parts_[r["dst"]])
    for ld, ps in sink.items():
        if len(ps) != 1:
            raise SystemExit("landing cell %s drives %s" % (ld, sorted(ps)))
        parts_[ld] = ps.pop()
    cm = {"note": "S81 v4 census map (gen_plan_v4.py census_map)", "parts": parts_, "groups": groups,
          "collapse_broadcast": True,     # a driver bus fanned out to several sink buses of one group counts once (PLAN-TOOL @4b819440d)
          "rules": [["^CELL:", "@die"]],          # as-built die-level reset tree cells (replaced by the reset spine)
          "exempt": [{"match": "^reset$", "kind": "reset", "replaced_by": "per-partition reset sync (reset.sync_stages)",
                      "reason": "as-built reset fan-out trees are replaced by the plan reset spine + 2-stage syncs"},
                     {"match": "^(rst_n|clk)$", "kind": "clock", "replaced_by": "clock spine / reset spine",
                      "reason": "die clock/reset ports"}]}
    json.dump(cm, open(out / "census_map.json", "w"), indent=0)
    (out / "census").mkdir(exist_ok=True)
    # S81/H4 10-24: the plan's census = the as-built census with the retired rung units (RETIRED_RUNG: bk_col) collapsed
    # onto the direct slice <-> slice rung, exactly as the lanes were derived (the as-built source stays inputs/)
    with open(CENSUS_SRC[0]) as f_:
        rd_ = csv.DictReader(f_, delimiter="\t")
        hdr_, rows_ = rd_.fieldnames, retire_rung(list(rd_))
    with open(out / "census" / "s81_lanes.tsv", "w", newline="") as f_:
        wr_ = csv.DictWriter(f_, fieldnames=hdr_, delimiter="\t", extrasaction="ignore", lineterminator="\n")
        wr_.writeheader()
        wr_.writerows(rows_)


CENSUS_SRC = []
CENSUS_ROWS = []


def emit(parts, lanes, routes, chans, fmap, out):
    P = {p.name: p for p in parts}
    grid_owner = {}
    for p in parts:
        for c in p.cells():
            grid_owner[c] = p.name
    # ports per lane
    ports = []
    lane_ports = {}
    for lk in lanes:
        cells = routes[lk["id"]]
        pids = []
        i = 0
        for x, y in zip(cells, cells[1:]):
            a, b = grid_owner[x], grid_owner[y]
            if a == b:
                continue
            pid = "%s__%d" % (lk["id"], i)
            i += 1
            ports.append(dict(id=pid, a=a, b=b, ca=x, cb=y, face=face_dir(x, y), width=lk["width"], kind=lk["kind"],
                              lane=lk["id"], cls=lk["cls"], role=lk["role"]))
            pids.append(pid)
        lane_ports[lk["id"]] = pids
    PT = {pt["id"]: pt for pt in ports}
    # v4 (COORD 10-23 07:5x): windows by STRAIGHT RUNS.  A run = the consecutive crossings of one lane along one
    # cell column (N/S faces) or one cell row (E/W faces).  Every face of a run gets the SAME die-coordinate window, so
    # a lane goes straight through the partitions of the run (no jog inside a pass-through partition); a lane bends
    # only where its cell route bends (<= 2).  Runs are packed first-fit (longest, then widest first) from the run's
    # packing end (E half / MY copies from the high x end, MX copies from the high y end) inside the intersection of
    # the faces' spans; a run that does not fit as a whole falls back to per-face placement, and a face that cannot
    # hold its ports at full width is re-packed in the v3 scaled form (G0 reports it).
    byface = collections.defaultdict(list)
    for pt in ports:
        byface[bkey(pt["a"], pt["b"], pt["ca"], pt["cb"])].append(pt)
    fspan, falloc = {}, {}
    for key, lst in byface.items():
        ca, cb = lst[0]["ca"], lst[0]["cb"]
        pa, pb = P[grid_owner[ca]], P[grid_owner[cb]]
        fspan[key] = span(pa, pb, ca, cb)
        falloc[key] = min((pa, pb), key=lambda q: (KPRIO[q.kind], q.name))
    pkey = {pt["id"]: bkey(pt["a"], pt["b"], pt["ca"], pt["cb"]) for pt in ports}
    # runs per lane
    runs = []
    for lk in lanes:
        cells = routes[lk["id"]]
        pids = iter(lane_ports[lk["id"]])
        cur, line = None, None
        for x, y in zip(cells, cells[1:]):
            vert = x[0] == y[0]
            ln = ("V", x[0]) if vert else ("H", x[1])
            if ln != line:
                cur = dict(line=ln, ports=[], width=lk["width"], role=lk["role"], lane=lk["id"])
                runs.append(cur)
                line = ln
            if grid_owner[x] != grid_owner[y]:
                cur["ports"].append(next(pids))
    runs = [r for r in runs if r["ports"]]
    # v4.6 (S81-P9 10-23, COORD R3-INTERNAL): the x forward of an r0 frame (x_i0 / xo_i0 E window -> u_y_xo stations ->
    # xo_o0 W window) is a straight E->W chain like an ft slot.  The xo lanes of a chain join the x lane's last straight
    # run on the frame row, so x_i0, every xo window and the in-frame forward share ONE die-y window (v4.5: x_i0 E at
    # 740-980 vs xo W at 98-336 = a 2.1-2.2 mm in-partition traverse).
    by_lane = collections.defaultdict(list)
    for r in runs:
        by_lane[r["lane"]].append(r)
    XO_JOINED.clear()
    for lk in lanes:
        if lk["cls"] != "x" or not by_lane.get(lk["id"]):
            continue
        last = by_lane[lk["id"]][-1]
        for suf in ("a", "b"):
            for r in by_lane.get("xo_%s_%s" % (lk["id"][2:], suf), []):
                if r["line"] == last["line"]:
                    last["ports"] += r["ports"]
                    XO_JOINED.append(r["lane"])
                    r["ports"] = []
    runs = [r for r in runs if r["ports"]]
    occ = collections.defaultdict(list)          # face key -> [(lo, hi)] occupied (die coords, incl. GAP)
    DIE_CX, DIE_CY = DIE_W / 2.0, X0 + NR * PY / 2.0

    def wlen(pt):
        return max((pt["width"] + 1) / ppu_of(pt), MINW)

    def ppu_of(pt):
        return ALLOC_PPU * len(face_layers(P[pt["a"]], P[pt["b"]], pt["face"])) / 2.0

    def fits(keys, a, b):
        return all(not (a < h - 1e-9 and l < b - 1e-9) for k in keys for (l, h) in occ[k])

    def place(keys, lo, hi, L, from_hi):
        """first free [a, a+L] in [lo, hi] over all faces in keys (candidate starts = edges of occupied spans)."""
        cand = {lo} if not from_hi else {hi}
        for k in keys:
            for (l, h) in occ[k]:
                cand.add(h if not from_hi else l)
        for c in sorted(cand, reverse=from_hi):
            a, b = (c, c + L) if not from_hi else (c - L, c)
            if a < lo - 1e-9 or b > hi + 1e-9:
                continue
            if fits(keys, a, b):
                return a, b
        return None
    raw = {}
    # v4.8: the runs of the lanes v4.8 adds / re-ends (route_v48 rerouted) are placed after every v4.7 run, so the
    # v4.7 windows (and with them the ft station spacing and lane cycles) stay where v4.7 put them
    new48 = set(ROUTE_V48.get("rerouted", ()))
    # S81-XDIE: the copy-A/B reserve lanes' runs go after every other run (no existing window moves for them)
    runs.sort(key=lambda r: (r["lane"] in new48, bool(RESERVE_RE.search(r["lane"])), -len(r["ports"]), -r["width"],
                             r["role"], r["lane"], r["line"]))
    single = []
    for r in runs:
        keys = [pkey[p] for p in r["ports"]]
        lo = max(fspan[k][0] for k in keys) + EDGE
        hi = min(fspan[k][1] for k in keys) - EDGE
        L = max(wlen(PT[p]) for p in r["ports"])
        if r["line"][0] == "V":
            from_hi = X0 + (r["line"][1] + 0.5) * PX > DIE_CX
        else:
            from_hi = falloc[keys[0]].yflip
        got = place(keys, lo, hi, L, from_hi) if hi - lo >= L else None
        if got is None or len(r["ports"]) == 1:
            if got is None:
                single.extend((p, from_hi) for p in r["ports"])
                continue
        a, b = got
        for p, k in zip(r["ports"], keys):
            occ[k].append((a - GAP / 2, b + GAP / 2))
            raw[p] = (a, b)
    over_faces = set()
    for p, from_hi in single:
        k = pkey[p]
        lo, hi = fspan[k][0] + EDGE, fspan[k][1] - EDGE
        got = place([k], lo, hi, wlen(PT[p]), from_hi)
        if got is None:
            over_faces.add(k)
            continue
        occ[k].append((got[0] - GAP / 2, got[1] + GAP / 2))
        raw[p] = got
    for k in over_faces:                          # v3 scaled packing for a face that cannot hold its ports
        lst = byface[k]
        alloc = falloc[k]
        lo, hi, vertical_face = fspan[k]
        flip = alloc.yflip if vertical_face else alloc.xflip
        lst.sort(key=lambda pt: (pt["role"], -pt["width"], pt["lane"]))
        need = sum(wlen(pt) + GAP for pt in lst)
        scale = min(1.0, (hi - lo - 2 * EDGE) / need)
        pos = (hi - EDGE) if flip else (lo + EDGE)
        for pt in lst:
            Lw, g = wlen(pt) * scale, GAP * scale
            if flip:
                raw[pt["id"]], pos = (pos - Lw, pos), pos - Lw - g
            else:
                raw[pt["id"]], pos = (pos, pos + Lw), pos + Lw + g
    STATS_V4.update(ft_macro_add=FT_MACRO_ADD, xo_joined=sorted(XO_JOINED), runs=len(runs), runs_multi=sum(1 for r in runs if len(r["ports"]) > 1),
                    run_fallback_ports=len(single), overfull_faces=sorted("|".join(map(str, k)) for k in over_faces))
    win = {}
    over = []
    for key, lst in byface.items():
        lo, hi, vertical_face = fspan[key]
        alloc = falloc[key]
        L_ = hi - lo
        flip = alloc.yflip if vertical_face else alloc.xflip
        over.append((sum(pt["width"] + 1 for pt in lst) / (6.0 * L_), lst[0]["a"], lst[0]["b"], key,
                     sum(pt["width"] + 1 for pt in lst), L_))
        lays_ = face_layers(P[lst[0]["a"]], P[lst[0]["b"]], lst[0]["face"])
        for pt in lst:
            w0, w1 = raw[pt["id"]]
            # snap to the 0.192-um grid (a multiple of every M4-M7 pitch; the lattice 8.64 = 45 x 0.192): window
            # edges then sit half a pitch from the nearest track in every instance frame -> identical pin tables
            q0, q1 = math.ceil(w0 / SNAP - 1e-6), math.floor(w1 / SNAP + 1e-6)
            lo_, hi_ = q0 * SNAP, q1 * SNAP
            # PLAN-TOOL pins sit symmetric about the window's centre track per layer; when k0 + k1 is odd for a
            # layer the span sits half a track low and a mirrored copy lands one pitch off -> trim hi until every
            # layer of the face has an even k0 + k1 (mirror-invariant pin table)
            # (trim the end that is the TYPE-frame high end of the allocating partition, so mirrored copies agree)
            for d in range(0, 200):
                l2, h2 = (lo_ + d * 0.004, hi_) if flip else (lo_, hi_ - d * 0.004)
                if all((math.ceil((l2 - TR[l][1]) / TR[l][0] - 1e-9) +
                        math.floor((h2 - TR[l][1]) / TR[l][0] + 1e-9)) % 2 == 0 for l in lays_):
                    lo_, hi_ = l2, h2
                    break
            else:
                raise SystemExit("no even-parity window for %s" % pt["id"])
            # PLAN-TOOL @2bb9e12ba spreader: a layer with an ODD pin count puts its middle pin on the track nearest the
            # window centre; if that track is inside a partition PG band the two neighbours tie and the pick is not
            # mirror-equivariant (pin tables of MX/R180 copies differ).  Move the centre (trim the type-frame high end
            # by 0.384 um = an even number of tracks on every layer, parity kept) until it sits on a usable track.
            nb = pt["width"] + 1
            for _ in range(400):
                bad = False
                for li, ln in enumerate(lays_):
                    n_l = len(range(li, nb, len(lays_)))
                    if n_l % 2:
                        # the middle pin and both inner half-picks must land without a PG-band collision push
                        cen, dw = (lo_ + hi_) / 2, min(1.6 * (hi_ - lo_) / n_l, 1.2)
                        pt_, off_ = TR[ln] if ln in TR else (0.064, 0.032)
                        ka, kb = math.ceil((cen - dw - off_) / pt_), math.floor((cen + dw - off_) / pt_)
                        if any(pg_blocked(ln, off_ + kk * pt_) for kk in range(ka, kb + 1)):
                            bad = True
                if not bad:
                    break
                lo_, hi_ = (lo_ + 0.384, hi_) if flip else (lo_, hi_ - 0.384)
            else:
                raise SystemExit("no usable centre track for %s" % pt["id"])
            win[pt["id"]] = (round(lo_, 4), round(hi_, 4))
    # bit order: ONE die-frame order per lane (a ft slot has one order for both faces); it is lsb_low in the type
    # frame of the lane's anchor end (a frame end if any, else the source), so mirrored copies keep one type
    for lid, pids in lane_ports.items():
        if not pids:
            continue
        p0, p1 = PT[pids[0]], PT[pids[-1]]
        if P[p1["b"]].kind == "frame" and P[p0["a"]].kind != "frame":
            anc, face = P[p1["b"]], OPP[p1["face"]]
        else:
            anc, face = P[p0["a"]], p0["face"]
        fl = anc.yflip if face in "EW" else anc.xflip
        for pid in pids:
            PT[pid]["order"] = "lsb_high" if fl else "lsb_low"
    # interface entries per partition
    for pt in ports:
        w0, w1 = win[pt["id"]]
        for role, part, df in (("out", pt["a"], pt["face"]), ("in", pt["b"], OPP[pt["face"]])):
            p = P[part]
            a, b, flip = to_type_win(p, df, w0, w1)
            tface = TF[p.orient].get(df, df)
            # bit order in the type frame
            border = pt["order"]
            if flip:
                border = "lsb_high" if border == "lsb_low" else "lsb_low"
            p.ents.append(dict(dir=role, port=pt["id"], lane=pt["lane"], face=tface, win=(a, b), width=pt["width"],
                               kind=pt["kind"], cls=pt["cls"], role_=pt["role"], order=border,
                               layers=tuple(face_layers(P[pt["a"]], P[pt["b"]], pt["face"]))))
    # pair ft crossings
    lane_idx = {}
    for lid, pids in lane_ports.items():
        for i, pid in enumerate(pids):
            lane_idx[pid] = (lid, i, len(pids))

    def port_pt(pid):
        pt = PT[pid]
        w0, w1 = win[pid]
        m = (w0 + w1) / 2
        x0 = X0 + pt["ca"][0] * PX
        y0 = X0 + pt["ca"][1] * PY
        f = pt["face"]
        return {"E": (x0 + PX, m), "W": (x0, m), "N": (m, y0 + PY), "S": (m, y0)}[f]

    sigs = {}
    for p in parts:
        ins = {e["port"]: e for e in p.ents if e["dir"] == "in"}
        outs = {e["port"]: e for e in p.ents if e["dir"] == "out"}
        slots, func, used = [], [], set()
        for pid, ei in ins.items():
            lid, i, n = lane_idx[pid]
            if i + 1 < n:
                nxt = lane_ports[lid][i + 1]
                if nxt in outs:
                    eo = outs[nxt]
                    a_, b_ = port_pt(pid), port_pt(nxt)
                    Ld = abs(a_[0] - b_[0]) + abs(a_[1] - b_[1])
                    # R3 (COORD 10-23): ft stations at most FT_STATION_MAX apart along the slot route (also <= REACH)
                    st = max(1, math.ceil(Ld / (min(REACH, FT_STATION_MAX) * 0.98)))
                    slots.append((ei, eo, st))
                    used |= {pid, nxt}
        for e in p.ents:
            if e["port"] not in used:
                func.append(e)
        fsig = tuple(sorted((e["dir"], e["face"], e["win"], e["width"], e["kind"], e["cls"], e["order"], e["layers"])
                           for e in func))
        ssig = tuple(sorted((ei["face"], ei["win"], eo["face"], eo["win"], ei["width"], ei["kind"], ei["order"],
                             eo["order"], st) for ei, eo, st in slots))
        ckey = json.dumps(p.contents, sort_keys=True)
        key = (p.ckey, ckey, round(p.w, 3), round(p.h, 3), p.hard, fsig, ssig)
        sigs[p.name] = (key, func, slots)
    types = collections.OrderedDict()
    for p in parts:
        types.setdefault(sigs[p.name][0], []).append(p.name)
    # S81 10-24 (stable type names): a type whose signature (key) is unchanged keeps the name it has in the reference
    # name table (S81_TYPE_NAMES, default physical/die_plan/s81/type_names.json: {sig sha1: type name}, written next to
    # every generated plan); new / changed signatures get the next free number of their base.  Without a reference the
    # names are the plain first-seen count (as before).  So a plan change that adds or alters a few types does not
    # renumber every other type (kits, SIGNED views and lane records stay keyed to the same names).
    import hashlib
    sig = {key: hashlib.sha1(repr(key).encode()).hexdigest() for key in types}
    ref_f = Path(os.environ.get("S81_TYPE_NAMES", Path(__file__).resolve().parent / "type_names.json"))
    ref = json.loads(ref_f.read_text()).get("names", {}) if ref_f.is_file() else {}
    tname = {}
    cnt = collections.Counter()
    if not ref:
        for key in types:
            base = re.sub(r"[^A-Za-z0-9_]", "_", key[0])
            cnt[base] += 1
            tname[key] = "%s__t%d" % (base, cnt[base])
    else:
        used = set()
        for key in types:
            nm = ref.get(sig[key])
            if nm and nm not in used:
                tname[key] = nm
                used.add(nm)
        # DEC12 (2026-10-24): a type whose signature changed but whose instances are exactly the instances of ONE
        # reference type (same partitions, same base) keeps that type's name -- a plan-wide change (e.g. ft station
        # counts at 405 um) re-kits the type under its old name instead of renumbering it.  Reference instances:
        # S81_TYPE_PARTS (default instance_map.json next to the name table: type_of {partition: type}).
        ref_parts_f = Path(os.environ.get("S81_TYPE_PARTS", ref_f.parent / "instance_map.json"))
        ref_of = json.loads(ref_parts_f.read_text()).get("type_of", {}) if ref_parts_f.is_file() else {}
        ref_inst = collections.defaultdict(set)
        for pn, tn_ in ref_of.items():
            ref_inst[tn_].add(pn)
        for key in sorted((k for k in types if k not in tname), key=lambda k: (-len(types[k]), types[k][0])):
            olds = {ref_of.get(n) for n in types[key]}
            base = re.sub(r"[^A-Za-z0-9_]", "_", key[0])
            if len(olds) == 1:
                old = olds.pop()
                if old and old not in used and ref_inst[old] == set(types[key]) and old.rsplit("__t", 1)[0] == base:
                    tname[key] = old
                    used.add(old)
                    INSTANCE_KEPT.append(old)
        top = collections.Counter()
        for nm in list(ref.values()) + list(used) + list(ref_of.values()):
            b_, n_ = nm.rsplit("__t", 1)
            top[b_] = max(top[b_], int(n_))
        for key in types:
            if key in tname:
                continue
            base = re.sub(r"[^A-Za-z0-9_]", "_", key[0])
            top[base] += 1
            tname[key] = "%s__t%d" % (base, top[base])
    TYPE_NAMES_OUT.update(names={sig[k]: tname[k] for k in types}, ref=ref_f.name if ref else None,
                          kept=sum(1 for k in types if ref.get(sig[k]) == tname[k]), types=len(types),
                          kept_by_instances=sorted(INSTANCE_KEPT))
    out_types, busname, ptype = {}, {}, {}

    def fsort(e):
        return (e["dir"], e["face"], e["win"], e["width"], e["kind"], e["cls"], e["order"])

    def ssort(t):
        ei, eo, st = t
        return (ei["face"], ei["win"], eo["face"], eo["win"], ei["width"], ei["kind"], ei["order"], eo["order"], st)

    def lays(face):
        return ["M6", "M4"] if face in "EW" else ["M7", "M5"]

    for key, names in types.items():
        tn = tname[key]
        rep = P[names[0]]
        _, func, slots = sigs[names[0]]
        fs = sorted(func, key=fsort)
        buses, canon = [], []
        cc = collections.Counter()
        for e in fs:
            nm = "%s_%s%d" % (e["cls"], "o" if e["dir"] == "out" else "i", cc[(e["cls"], e["dir"])])
            cc[(e["cls"], e["dir"])] += 1
            canon.append(nm)
            buses.append(dict(name=nm, dir=e["dir"], width=e["width"], kind=e["kind"], face=e["face"],
                              window_um=list(e["win"]), layers=list(e["layers"]), order=e["order"]))
        ss = sorted(slots, key=ssort)
        ftsl = []
        for i, (ei, eo, st) in enumerate(ss):
            ftsl.append(dict(name="ft%d" % i, in_face=ei["face"], out_face=eo["face"], width=ei["width"],
                             stations=st, in_window_um=list(ei["win"]), out_window_um=list(eo["win"]),
                             layers=list(ei["layers"]) if ei["layers"] == eo["layers"] else None,
                             order=ei["order"]))
        for s_ in ftsl:
            if s_["layers"] is None:
                s_.pop("layers")
        nf_ = nonframe_hard_cores(rep, rep.w, rep.h, tn, ftsl, buses)
        # S81/LEAFPLAN (ruling (a)): the FIRM internal stations of the chosen core arrangement (type frame)
        ist_ = HC_REPORT.get(tn, {}).pop("internal_stations", None) if nf_ else None
        hc_ = frame_hard_cores(rep.contents, buses) + nf_   # S81-P9-HC
        nf_ = nf_ if nonframe_hc_key(rep) in CORES_405_KEYS else []   # S81-CORES scope (other keys: S81's 750 model)
        if nf_:
            # S81-CORES: a type hardened here is skipped by macrofree_ft_reach (it has hard_cores); its slots are sized at
            # the implemented M4-M7 kit reach around the cores here, and by the actual pin bits at the end (corefull)
            NF_HC_TYPES.append(tn)
        for s_ in ftsl:
            k0 = s_["stations"]
            if nf_:
                # S81-CORES: the cores add only their escape stations over the same model's no-core count; the count
                # itself comes from the actual pin bits at the end (corefull resize, as macrofree_ft_reach for soft types)
                sm_ = min(FT_STATION_MAX, FT_KIT_REACH_UM) * 0.98
                s_["_core_add"] = (ft_stations_macro(s_, hc_, rep.w, rep.h, smax=sm_) -
                                   ft_stations_macro(s_, [dict(origin_um=[-1e6, -1e6], outline_um=[1, 1])], rep.w, rep.h,
                                                     smax=sm_))
                continue
            s_["stations"] = ft_stations_macro(s_, hc_, rep.w, rep.h)
            if s_["stations"] != k0:
                FT_MACRO_ADD.append(dict(type=tn, slot=s_["name"], stations=[k0, s_["stations"]]))
        ty = dict(module="s81p_" + tn, outline_um=[rep.w, rep.h], hard=rep.hard, buses=buses, ft_slots=ftsl,
                  clock=dict(tap_um=[round(rep.w / 2 / G) * G, round(rep.h / 2 / G) * G], layer="M9"),
                  reset=dict(sync_stages=2), contents=frame_contents(rep.contents, buses),
                  **({"sources": FRAME_SOURCES(rep.contents)} if FRAME_SOURCES(rep.contents) else {}),
                  **({"hard_cores": hc_} if hc_ else {}),
                  **({"internal_stations": ist_} if ist_ else {}),
                  note="%s partition; %d instance(s) (%s)" % (rep.kind, len(names),
                                                              ",".join(sorted({P[n].orient for n in names}))))
        if tn.startswith("col_"):
            frame_early_clock(ty)
        out_types[tn] = ty
        for n in names:
            _, f2, s2 = sigs[n]
            for e, nm in zip(sorted(f2, key=fsort), canon):
                busname[(n, e["port"], e["dir"])] = nm
            for i, (ei, eo, st) in enumerate(sorted(s2, key=ssort)):
                busname[(n, ei["port"], "in")] = "ft%d_i" % i
                busname[(n, eo["port"], "out")] = "ft%d_o" % i
            ptype[n] = tn
    gr = collections.defaultdict(set)
    for tn, ty in out_types.items():
        for b in ty["buses"]:
            for ln in b["layers"]:
                if ln in FOLD_GRANT:
                    gr[(tn, b["face"])].add(ln)
        for sl in ty["ft_slots"]:
            for ln in sl.get("layers", []):
                if ln in FOLD_GRANT:
                    gr[(tn, sl["in_face"])].add(ln)
                    gr[(tn, sl["out_face"])].add(ln)
    FACE_GRANTS = []
    for (tn, f), v in sorted(gr.items()):
        base = ["M6", "M4"] if f in "EW" else ["M7", "M5"]
        out_types[tn].setdefault("face_layers", {})[f] = base + sorted(v)
        FACE_GRANTS.append(dict(type=tn, face=f, layers=base + sorted(v)))
    oparts = [dict(name=p.name, type=ptype[p.name], origin_um=[round(p.x0, 4), round(p.y0, 4)], orient=p.orient)
              for p in parts]
    oports = []
    for pt in ports:
        w0, w1 = win[pt["id"]]
        oports.append(dict(id=pt["id"], src=dict(part=pt["a"], bus=busname[(pt["a"], pt["id"], "out")]),
                           dst=dict(part=pt["b"], bus=busname[(pt["b"], pt["id"], "in")]), width=pt["width"],
                           kind=pt["kind"], face=pt["face"], layers=face_layers(P[pt["a"]], P[pt["b"]], pt["face"]),
                           window_um=[w0, w1],
                           order=pt["order"]))
    olanes = [dict(id=l["id"], ports=lane_ports[l["id"]], **({"fixed_cycles": l["fixed"]} if l.get("fixed") else {}),
                   **({"beats": l["beats"], "word_bits": l["word_bits"]} if l.get("beats") else {}))
              for l in lanes]
    plan = {
        "schema": "opentallas.die_plan.v1",
        "note": "S81 72-frame MU release die, plan v3 (PLAN-S81v3 10-23; v2 base): one 1442.88 x 1226.88 lattice, MY-mirrored "
                "halves, frames as MX r0/r1/r2 bands in E-W 3-frame chains, slices as N-S 1-cell segment chains, svc "
                "2x8 cells, no lane columns. physical/die_plan/s81/gen_plan_v2.py.",
        "die": {"name": "s81", "label": "DeepSeek ROM S81 72-frame MU release die", "tech": "asap7",
                "outline_um": [round(DIE_W, 4), round(DIE_H, 4)], "period_ps": 833, "reach_um": REACH,
                "rep_um": 450.0, "grid_um": G,
                "layer_budget": {"partition_signal_max": "M7", "die_layers": ["M8", "M9"],
                                 "die_use": ["clock_spine", "pg"]},   # DEC12: no ft_reserved, no M8/M9 signal cut capacity
                "pg": {"partition_pg_max": "M7", "grid": [
                    {"layer": "M8", "width_um": 0.48, "pitch_um": 8.64, "offset_um": 4.32, "nets": ["VDD", "VSS"]},
                    {"layer": "M9", "width_um": 0.48, "pitch_um": 8.64, "offset_um": 4.32, "nets": ["VDD", "VSS"]}],
                    # OWNER DECISION 7 (2026-10-24): die.pg.domains (one VDDPHY supply + dedicated bump rows per
                    # SerDes window) are added from the die_io.py windows by pg_domains.py (run_v4.sh)
                    },
                "channels": chans + [
                    {"rect_um": [0, 0, round(DIE_W, 4), X0], "reason": "seal ring"},
                    {"rect_um": [0, round(DIE_H - X0, 4), round(DIE_W, 4), round(DIE_H, 4)], "reason": "seal ring"},
                    {"rect_um": [0, X0, X0, round(DIE_H - X0, 4)], "reason": "seal ring"},
                    {"rect_um": [round(DIE_W - X0, 4), X0, round(DIE_W, 4), round(DIE_H - X0, 4)],
                     "reason": "seal ring"}]},
        "partition_types": out_types,
        "partitions": oparts,
        "ports": oports,
        "lanes": olanes,
        "clock": {"source": {"part": "@die", "bus": "clk"}, "insertion_ps": 250, "common_latency_ps": 250, "insertion_tol_ps": 40, "ft_hop_in_share": 0.16,   # R4 die-wide common latency (COORD G0C)
                  "neighbour_skew_ps": 80, "face_xing": "budgeted",
                  "spine": {"layers": ["M8", "M9"], "root_um": [round(X0 + 11 * PX, 4), round(X0 + 10 * PY, 4)],
                            "topology": "htree"}},
        "reset": {"source": {"part": "@die", "bus": "rst_n"}, "sync_stages": 2, "data_reset": False,
                  "epoch_bit": True,
                  # DEC12 batch (OWNER DECISION 13, claude/reset-1024 on main c5834d0306): neighbour wavefront reset,
                  # one root synchroniser per die, registered rst_o relays (tools/die_plan/reset_tree.py)
                  "release": "wavefront"},
        "census": [{"rows": "census/s81_lanes.tsv", "map": "census_map.json",
                    "note": "FT census of the bound as-built die (1364 rows); finer partition-level check incl. "
                            "bus-aware lep rx/tx and src-bus dedup: census_cov.py -> v3/census_cov.json"}],
        "budgets": {"face_pins_per_um": 6, "face_pin_layers": 2, "face_window_um": 10, "pin_track_max": 0.6,
                    "cut_ratio_max": 0.6, "cut_step_um": 250,
                    # S81/LEAFPLAN 10-24 (coordinator ruling (a)): R3 inside the hardened leaf / svc / eng types at the
                    # 405-um kit reach (core_conns.json bundles; FIRM internal_stations[])
                    "core_internal_reach_um": CORE_INT_REACH_UM,
                    # DEC12 (COORD 22:35): hops / stations <= 405 um exactly -- no extra 0.9 G0C reach margin
                    "reach_margin": 1.0, "ft_station_max_um": FT_STATION_MAX},
    }
    STATS_V4["macrofree_ft_reach"] = macrofree_ft_reach(plan)
    from tools.die_plan.ft_reach import resize
    STATS_V4["corefull_ft_reach"] = resize(plan, reach_um=min(FT_STATION_MAX, FT_KIT_REACH_UM), margin=.98,
                                           types=NF_HC_TYPES, macrofree_only=False)
    for tn_ in NF_HC_TYPES:
        for s_ in plan["partition_types"][tn_]["ft_slots"]:
            a_ = s_.pop("_core_add", 0)
            if a_ > 0:
                FT_MACRO_ADD.append(dict(type=tn_, slot=s_["name"], stations=[s_["stations"], s_["stations"] + a_],
                                         why="core escape at the 405-um kit reach"))
                s_["stations"] += a_
    from tools.die_plan.ft_sites import place as place_ft_bits, reuse as reuse_ft_bits
    from tools.die_trial.legal_sites import RowAllocator
    # Every core field needs explicit row-legal FT bit sites, not just frames.
    # Retain unchanged committed sites so routine plan regeneration does not
    # repeat the same allocation. Any physical/clock/reset contract change
    # invalidates the seed and runs the exact allocator again.
    ft_types = [n for n, t in plan["partition_types"].items() if t.get("hard_cores") and t.get("ft_slots")]
    seed_path = Path(__file__).with_name("die_plan.json")
    reused = reuse_ft_bits(plan, json.load(open(seed_path)), types=ft_types) if seed_path.is_file() else []
    STATS_V4["ft_bit_sites_reused"] = reused
    STATS_V4["ft_bit_sites"], _ = place_ft_bits(
        plan, RowAllocator, types=[n for n in ft_types if n not in reused], reach_um=FT_KIT_REACH_UM, margin=.98)
    STATS_V4["frame_ft_bit_sites"] = [x for x in STATS_V4["ft_bit_sites"] if x["type"].startswith("col_")]
    STATS_V4["face_layers"] = FACE_GRANTS     # svc fold faces (COORD S81 ruling (1)(b) 10-23 07:43)
    out.mkdir(parents=True, exist_ok=True)
    json.dump(plan, open(out / "die_plan.json", "w"), indent=0)
    json.dump(TYPE_NAMES_OUT, open(out / "type_names.json", "w"), indent=0, sort_keys=True)
    # S81-PORTS 10-25: the derived connectivity turns on R3-INTERNAL internal_station / core_faces checks for the 13
    # landed col_h* frames + bk_sel + gunit (Codex faultfinal G0C: 4766 + 84 ERRORs, all pre-existing core-pair hops
    # > 405 um with no internal_stations[] entry; the missing-cores / core-relay lane owns them).  It is a separate
    # gate expansion, not part of the fault-feeder plan delta: opt-in until that lane adopts it.
    if os.environ.get("OT_S81_DERIVED_CORE_CONNS") == "1":
        derived_core_conns(plan["partition_types"])
    if CORE_CONNS_OUT:
        json.dump(CORE_CONNS_OUT, open(out / "core_conns.json", "w"), indent=0, sort_keys=True)
    json.dump(dict(note="S81-P9-HC: non-frame types over %d cells: hard cores emitted / residual soft cells / gaps (children "
                        "with no closed view)" % HC_CELLS_MAX, types=HC_REPORT),
              open(out / "hard_core_gaps.json", "w"), indent=1)
    census_map(plan, lanes, fmap, out)
    # ---- metrics ----
    lb, det = [], []
    for lk in lanes:
        cells = routes[lk["id"]]
        lb.append((bends(cells), lk["id"]))
        pids = lane_ports[lk["id"]]
        if not pids:
            continue
        pts = [port_pt(pid) for pid in pids]
        # endpoints: centre of src seg cell face path -> use first/last port points + half-cell legs
        Ln = sum(abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in zip(pts, pts[1:]))
        man = abs(pts[0][0] - pts[-1][0]) + abs(pts[0][1] - pts[-1][1])
        if len(pids) >= 3 and man > 0:
            det.append((Ln / man, lk["id"]))
    bs = sorted(b for b, _ in lb)
    ds = sorted(d for d, _ in det)

    def pct(v, q):
        return v[min(len(v) - 1, int(math.ceil(q * len(v))) - 1)] if v else 0

    over.sort(reverse=True)
    by_kind = collections.Counter(P[n[0]].kind for n in types.values())
    stats = dict(
        die_um=[round(DIE_W, 2), round(DIE_H, 2)], die_mm2=round(DIE_W * DIE_H / 1e6, 1),
        partitions=len(parts), types=len(types), types_by_kind=dict(by_kind),
        singleton_types=sum(1 for v in types.values() if len(v) == 1),
        lanes=len(lanes), ports=len(ports),
        bends_max=bs[-1], bends_p90=pct(bs, 0.9), bends_hist=dict(collections.Counter(bs)),
        detour_p90=round(pct(ds, 0.9), 3), detour_max=round(ds[-1], 3) if ds else 0,
        detour_worst=sorted(det, reverse=True)[:5],
        face_worst=[dict(a=a, b=b, ratio=round(r, 3), pins=n, len=round(L_, 1)) for r, a, b, k, n, L_ in over[:10]],
        faces_over_06=sum(1 for o in over if o[0] > 0.6 + 1e-9),
        channel_cells=len(chans),
        instances_per_type={tname[k]: len(v) for k, v in types.items()},
    )
    # L1 CAP 400k (COORD 06:12): leaf synthesis counts (Yosys synth_stat totals; closed archive A = ~/closed_archive,
    # fleet F = /srv/opentallas-scratch/claude/{closure-loop,ref_gate}); planned hard cores <= 400k per partition.
    est, why = {}, {}
    for p in parts:
        cores, glue, basis = cells_core_plan(p)
        est[p.name] = dict(cells=sum(c[1] for c in cores) + glue, glue=glue, cores=[dict(name=c[0], cells=c[1])
                                                                                      for c in cores],
                           n_cores=len(cores), basis=basis,
                           max_core=max([c[1] for c in cores] + [0]))
    over = {k: v for k, v in est.items() if v["max_core"] > 400000 or v["glue"] > 400000}
    kinds = collections.defaultdict(list)
    for p in parts:
        kinds[p.kind].append(est[p.name])
    stats["cells_by_kind"] = {k: dict(n=len(v), max_partition=max(x["cells"] for x in v),
                                      max_core=max(x["max_core"] for x in v), max_glue=max(x["glue"] for x in v),
                                      cores=sum(x["n_cores"] for x in v)) for k, v in kinds.items()}
    stats["cells_over_cap"] = sorted(over)
    stats["v4_runs"] = dict(STATS_V4)
    stats["cells_missing"] = sorted({v["basis"] for v in est.values() if "MISSING" in v["basis"]})
    json.dump(stats, open(out / "v4_stats.json", "w"), indent=1, default=str)
    json.dump(est, open(out / "cells_est.json", "w"), indent=1)
    json.dump(dict(fmap, type_of=ptype, lp_bus_re=LP_BUS_RE), open(out / "instance_map.json", "w"), indent=0)
    return stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--asbuilt", required=True)
    ap.add_argument("--census", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    ab = json.load(open(a.asbuilt))
    census = list(csv.DictReader(open(a.census), delimiter="\t"))
    CENSUS_SRC.append(a.census)
    CENSUS_ROWS.extend(census)
    parts, frames, serdes, slices, chans, svcg = build(ab)
    lanes, fmap = lanes_all(ab, census, parts, frames, serdes, slices)
    grid = Grid(parts)
    # every cell covered or a channel
    chan_cells = set()
    for ch in chans:
        x0, y0, x1, y1 = ch["rect_um"]
        for c in range(NC):
            for r in range(NR):
                cx, cy = X0 + (c + .5) * PX, X0 + (r + .5) * PY
                if x0 < cx < x1 and y0 < cy < y1:
                    chan_cells.add((c, r))
    miss = [(c, r) for c in range(NC) for r in range(NR) if (c, r) not in grid.owner and (c, r) not in chan_cells]
    assert not miss, miss
    routes = route_v48(grid, lanes_all(ab, census, parts, frames, serdes, slices, v47=True)[0], lanes)
    stats = emit(parts, lanes, routes, chans, fmap, Path(a.out))
    print(json.dumps({k: v for k, v in stats.items() if k != "instances_per_type"}, indent=1, default=str))


if __name__ == "__main__":
    main()
