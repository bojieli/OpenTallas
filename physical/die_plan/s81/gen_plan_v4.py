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
REACH = 1500.0
FT_KIT_REACH_UM = 405.0  # measured M4-M7 kit reach at 833ps; M8/M9 are reserved die resources
FT_STATION_MAX = 750.0     # budgets.ft_station_max_um (tools/die_plan R3)
UNIFORM_SEG = True
SNAP = 0.192
TR = dict(M4=(0.048, 0.024), M5=(0.048, 0.024), M6=(0.064, 0.032), M7=(0.064, 0.032),
          M8=(0.080, 0.040), M9=(0.080, 0.040))   # pitch, offset (PLAN-TOOL symmetric tracks)
# COORD S81 ruling (1)(b) 10-23 07:43: the svc fold faces (svc_2k N | svc_2k+1 S, ~9.0 kb on a 1.44-mm face) take a
# third pin layer from the reserved die budget via partition_types.<t>.face_layers (PLAN-TOOL @7f9f10e1d).  The fold
# face is N/S, and the tool requires a vertical pin layer there (M8 is H -> 'layer M8 is H, a S face needs V'), so the
# grant is M9, the vertical die layer (die M9 PG bands avoided; the kit routes M2-M9 and obstructs the die M8/M9 bands).
FOLD_GRANT = [] if os.environ.get("S81_V4_NOGRANT") else ["M9"]
STATS_V4 = {}
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
_C_COMMON = [dict(inst="u_c.u_eg", module="ot_s81sl_eg", lef=_rt("s81sl_eg", "ot_s81sl_eg"), cells=261681, plan_core="eg"),
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
    "C:xrt1": dict(cores=_C_COMMON + [dict(inst="u_c.u_xr", module="ot_s81sl_xrt1", plan_core="xg_xr", cells=67849,
                                           lef=_rt("s81sl_xrt1", "ot_s81sl_xrt1"))], gaps=_C_GAPS),
    "C:xrt3": dict(cores=_C_COMMON + [dict(inst="u_c.u_xr", module="ot_s81sl_xrt3", plan_core="xg_xr", cells=78456,
                                           lef=_rt("s81sl_xrt3_b", "ot_s81sl_xrt3"))], gaps=_C_GAPS),
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
                       [dict(inst="u_lf.u_vn", module="ot_s81sl_vn", lef=_rt("s81sl_vn", "ot_s81sl_vn"), cells=375145,
                             plan_core="vn"),
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
                        # CORE-S81 10-23: ve r5 CLOSED view (closed_archive ot_s81sl_ve/s81sl_ve_r5-f51f4ec42-linked-eco-1021,
                        # TT +42.12 / FF +12.74 / DRC 0; LEF regenerated from provenance/raw, sha 01b54bf1 = the record)
                        dict(inst="u_lf.u_ve", module="ot_s81sl_ve", cells=460279, plan_core="ve",
                             lef=_ARCH % ("ot_s81sl_ve", "s81sl_ve_r5-f51f4ec42-linked-eco-1021", "ot_s81sl_ve",
                                          "ot_s81sl_ve"))],
                 gaps=[],
                 # vp's own logic (36,056) + leaf glue stay soft: residual = total - hard
                 place=dict([("u_lf.u_vp.g_ln[%d].u_l" % i, (34.56 if i < 8 else 172.8, 129.6 + 129.6 * (i % 8)))
                             for i in range(16)] +
                            [("u_lf.u_vp.u_b0", (432.0, 587.52)), ("u_lf.u_vp.u_b1", (432.0, 535.68)),
                             ("u_lf.u_vn", (345.6, 639.36)), ("u_lf.u_vq", (734.4, 613.44)),
                             ("u_lf.u_vs", (924.48, 587.52)), ("u_lf.u_vsw", (1175.04, 561.6)),
                             ("u_lf.u_ve", (812.16, 803.52)), ("u_lf.u_rxsf", (941.76, 432.0)),
                             ("u_lf.u_rxsb", (941.76, 276.48))]),
                 # the leaf bus face picks the variant: N bus = as placed, S bus = y mirror (every core MX'd with it)
                 mirrors=((False, False), (False, True)), mirror_by_bus=True),
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
                place=dict([(c_["inst"], tuple(c_["origin_um"])) for c_ in _SVC_HC] +
                           [("u_rsv.u_sx.g_r[%d].g_h[%d].u_hrow" % (r, b), (round(51.84 + 172.8 * (2 * r + b), 4), 1140.48))
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
                mirrors=((False, False),)),
}
HC_REPORT = {}
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
        _LF + "u_vn": dict(_cc(**{"hw_v,hw_j,hw_hf,hw_d,hq_v,hq_d,hr_v,hr_j,hr_hf": _HC}), **_cc(**{
            "wl_v,wl_i,wl_d": _ST, "n_go,n_pre": _ST + [_DN], "rb_v,rb_d": [_DN], "p_v,p_d": [_UP],
            "y_v,y_i,y": ["core:u_lf.u_vq"]})),
        _LF + "u_vq": _cc(**{"y_v,y_i,y": ["core:u_lf.u_vn"], "u_v,u_i,u,um_v,um_q,um_b,um_i": ["core:u_lf.u_vs"],
                             "xf_v,xf_s,xf,fault": [_UP], "k,sid,m_v,m_q,m_b,m_i": [_DN]}),
        _LF + "u_vs": _cc(**{"s_v,s_d,g_v,g_c,g_d": [_DN], "e_v,e_c,e_d,fault": [_UP],
                             "x_rv,x_ra,x_qv,x_qd,x_wv,x_wa,x_wm,x_wd": _ST,
                             "u_v,u_i,u,um_v,um_q,um_b,um_i": ["core:u_lf.u_vq"],
                             "ve_rv,ve_rc,ve_rh,ve_rk,ve_rw,ve_pv,ve_pc,ve_phh,ve_pkk,ve_pdd,ve_av,ve_ac,ve_ah,ve_aval,"
                             "ve_ag,ve_ov,ve_oc,ve_oy,ve_fi": ["core:u_lf.u_ve"],
                             "sw_v,sw_d,sw_w,sw_lim,sw_vi,sw_ri,sw_fi": ["core:u_lf.u_vsw"],
                             "ra_v,ra_x": ["core:u_lf.u_rxsf"], "ra_vi,ra_ri,ra_fi": ["core:u_lf.u_rxsb"]}),
        _LF + "u_ve": _cc(**{"r_v,r_c,r_h,r_k,r_w,p_v,p_c,p_hh,p_kk,p_dd,a_v,a_c,a_h,a_val,a_g,o_v,o_c,o_y,fault":
                             ["core:u_lf.u_vs"]}),
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
    "eng": {
        "u_eng.u_e": _cc(pci=["bus:unit_i0"], rco=["bus:unit_o0"], f_ks=["bus:unit_i1"], vi_s=["bus:xtier_i0"],
                         vo_s=["bus:xtier_o0"], vo_n=["bus:xtier_o1"], vi_n=["bus:xtier_i1"],
                         **{"hx_w,hx_res": ["core:u_eng.u_h0", "core:u_eng.u_h1"]}),
        "u_eng.u_h0": _cc(**{"in_w,out_res": ["core:u_eng.u_e"]}),
        "u_eng.u_h1": _cc(**{"in_w,out_res": ["core:u_eng.u_e"]}),
    },
}
CORE_CONNS_OUT = {}


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
    if spec.get("place"):
        # CORE-S81 10-23: explicit connectivity-aware origins (type frame, 8.64 lattice) where the shelf packer does not
        # fit; the corner mirroring and the gap / edge legality below still apply
        for c, (cw, ch) in items:
            pl_ = spec["place"][c["inst"]]
            ox_, oy_ = pl_[0], pl_[1]
            out.append(dict(inst=c["inst"], module=c["module"], lef=c["lef"], origin_um=[ox_, oy_], outline_um=[cw, ch],
                            orient=pl_[2] if len(pl_) > 2 else "R0", track_offset_um=list(CORE_TRACK_OFFSET),
                            pins_file=c.get("pins_file", "inputs/core_pins/%s.json" % c["module"])))
        items = []
    for c, (cw, ch) in items:
        if x + dx + cw > w - HC_EDGE_UM:
            x, y, row_h = x0, up(y + dy + row_h + HC_GAP_UM), 0.0
        if x + dx + cw > w - HC_EDGE_UM or y + dy + ch > h - HC_EDGE_UM:
            raise SystemExit("S81-P9-HC: type %s: core %s (%gx%g) does not fit the %gx%g outline" % (
                tn, c["inst"], cw, ch, w, h))
        out.append(dict(inst=c["inst"], module=c["module"], lef=c["lef"], origin_um=[round(x, 4), round(y, 4)],
                        outline_um=[cw, ch], orient="R0", track_offset_um=list(CORE_TRACK_OFFSET),
                        pins_file="inputs/core_pins/%s.json" % c["module"]))
        x = up(x + dx + cw + HC_GAP_UM)
        row_h = max(row_h, ch)
    # corner choice: the packed block is mirrored to each outline corner (lattice-snapped); the first variant that adds no
    # ft-slot station (ft_stations_macro: a core on a slot's in->out line pushes its stations off) and keeps the gap /
    # edge rules wins; else the one adding fewest stations
    def mirrored(mx, my):
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
            if oc in ("MY", "R180") and spec.get("place"):
                raise SystemExit("S81-CORES: x-mirrored explicit cores need a V-layer track shift (not implemented)")
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
    if spec.get("mirror_by_bus"):
        # S81-CORES: the cores' bus-side ports face N as placed; a type whose buses sit on its S face takes the y mirror
        bf = {b.get("face") for b in buses if b.get("face") in ("N", "S")}
        if len(bf) == 1:
            variants = [v for v in variants if v[1] == (bf == {"S"})]
    for mx, my in variants:
        o = mirrored(mx, my)
        if not legal(o):
            continue
        add = sum(ft_stations_macro(s_, o, w, h) - s_["stations"] for s_ in ftsl)
        if best is None or add < best[0]:
            best = (add, o, (mx, my))
        if add == 0:
            break
    if best is None:
        raise SystemExit("S81-P9-HC: type %s: no legal core packing" % tn)
    rep["emitted"] = True
    if k in CORE_CONNS:
        CORE_CONNS_OUT[tn] = CORE_CONNS[k]
    rep["corner"] = "%s%s" % ("E" if best[2][0] else "W", "N" if best[2][1] else "S")
    rep["ft_stations_added"] = best[0]
    return best[1]


FT_MACRO_ADD = []
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
    for nm, (side, row, cw) in sd.items():
        col = cw if side != "E" else mir(cw) - 1
        orient = "MY" if side == "E" else "R0"
        serdes[nm] = add(Part("lk_" + nm, "serdes", col, row, nc=2, orient=orient,
                              contents=[C("u_phy", "ot_pdie_serdes", "rework",
                                          note="SerDes PHY model re-aspected into a 2885.76 x 1226.88 slot; a strip "
                                               "beside it holds the boundary flops and ft stations")],
                              ckey="serdes"))
    # ---- centre: cols 6..15 ----
    # row 0: s_0S | iqf | phy (8-13) | eng | s_7S ; seqhost at (10,5) beside the svc band
    add(Part("phy_hbm", "phy", 8, 0, nc=6, hard=True,
             contents=[C("u_phy_hbm", "ot_hbm3e_phy_v41x_aw30_e8p5", "reuse",
                         note="hard HBM3E PHY 8500 x 1177 in a 6-cell S-edge slot (bump field at the die edge)")],
             ckey="phy"))
    add(Part("iqf", "unit", 7, 0, contents=[C("u_iqf", "dsdv_idx_qf")], ckey="iqf"))
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
            if hn == "s_7N":
                nrow = 8
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
                p = add(Part("%s_%s" % (hn, role if role != "X" else "x%d%d" % (c - c0, r - r0)), "slice", c, r,
                             orient=orient, contents=cont, ckey=ck, group=hn))
                p.role = role
                segs[(c - c0, r - r0)] = p
            slices[hn] = dict(master=m, c0=c0, r0=r0, ncol=ncol, nrow=nrow, segs=segs, k=k, half=half,
                              C=next(q for q in segs.values() if q.role == "C"),
                              LP=next((q for q in segs.values() if q.role == "LP"), None),
                              leaves=[q for q in segs.values() if q.role.startswith("L") and q.role != "LP"])
    # units row 19: WN3 (6-7) | bk_col 8 | gunit 9-10 | bk_sel 11-13 | s_7N top (14-15)
    add(Part("bk_col", "unit", 8, 19, contents=[C("u_bk_col", "dsfd_bk_collector")], ckey="bk_col"))
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
             for c, r in ((0, 0), (20, 0), (20, 19))]
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


def x_row(fr):
    return 3 + 3 * fr


def lanes_all(ab, census, parts, frames, serdes, slices, v47=False):
    P = {p.name: p for p in parts}
    groups = frame_mapping(ab)
    lanes = []
    fmap = {}

    def L(lid, src, sbus, dst, dbus, width, kind="data", cls="data", role=None, path=None, fixed=0):
        lanes.append(dict(id=lid, src=(src, sbus), dst=(dst, dbus), width=int(width), kind=kind, cls=cls,
                          role=role or cls, path=path, fixed=fixed))

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
                      w, cls="frame_int", role="fi_%s%s" % (a, bb), fixed=1)   # band RTL seam = K + 1 = 3 edges
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
        agg.setdefault((ps, pd, c), 0)
        agg[(ps, pd, c)] += add_b
    if unmapped:
        raise SystemExit("census rows without a partition: %s" % unmapped[:5])
    for (ps, pd, c), b in agg.items():
        kind = "ctl" if c == "ctl" else "data"
        L("%s__%s__%s" % (c, ps, pd), ps, "%s_%s_o" % (c, pd), pd, "%s_%s_i" % (c, ps), b, kind=kind, cls=c, role=c)
    # ---- v4.8 (S81-P9-R8EQ): bound-top crossings the as-built census lacks (inputs/bound_supplement_v48.json, from the
    #      BINDER4 b3r8 UNPLANNED list): svc_rs chain svc_2k -> svc_2k+1 and the slice C -> LP 1-b lep inputs ----
    for e in ([] if v47 else json.load(open(BOUND_SUPP))["entries"]):
        ps, pd, c = e["src"], e["dst"], e["cls"]
        assert ps in P and pd in P, e
        L("%s__%s__%s" % (c, ps, pd), ps, "%s_%s_o" % (c, pd), pd, "%s_%s_i" % (c, ps), e["bits"], cls=c, role=c)
    # ---- ID rings (no tie-offs): slice sid + fault OR, svc sid; counted (sid_o = sid_i + 1), rooted at seqhost ----
    order_s = [slices["s_%dS" % k]["C"].name for k in range(7, -1, -1)] + \
              [slices["s_%dN" % k]["C"].name for k in range(8)]
    ring = ["seqhost"] + order_s + ["seqhost"]
    for a, b in zip(ring, ring[1:]):
        L("sid_%s__%s" % (a, b), a, "sid_o" if a != "seqhost" else "sidr_o", b, "sid_i" if b != "seqhost" else "sidr_i",
          5, kind="ctl", cls="sid", role="sid")
    svc_ring = ["seqhost"] + ["svc_%d" % n for n in list(range(0, 16, 2)) + list(range(15, 0, -2))] + ["seqhost"]
    for a, b in zip(svc_ring, svc_ring[1:]):
        L("vid_%s__%s" % (a, b), a, "vid_o" if a != "seqhost" else "vidr_o", b, "vid_i" if b != "seqhost" else "vidr_i",
          4, kind="ctl", cls="vid", role="vid")
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
LP_CELLS = {"dsdv_slice_lepw_mu": 88962 + 4 * 67956 + 4703, "dsdv_slice_lepw_mus": 51741 + 2 * 67956 + 4703,
            "dsdv_slice_lepe_mu": 67042 + 2 * 67956 + 4703, "dsdv_slice_lepe_nh_mus": 51741 + 2 * 67956 + 4703}
UNIT_CORES = {
    "eng": ([("eng_rr_a", 418942 // 2), ("eng_rr_b", 418942 - 418942 // 2)], "dsdv_eng_rr 418,942 (F ep7 ref_gate "
            "dsdv_eng_rr_b) > cap: 2 planned cores"),
    "gunit": ([("l0_l1_l2", 8213 + 110419 + 9853 + 43954 + 8215), ("l3_l4", 40887 + 81348 + 73342),
               ("l5f", 97736)], "dsdv_gunit = sum of closed leaves (instance counts not confirmed)"),
    "bk_sel": ([("bksel_c_pa", 260094), ("bksel_q01", 2 * 113262), ("bksel_q23", 2 * 113262),
                ("bkg_tx_vmux", 2 * 25144 + 31602 + 3547)], "dsdv_bk_sel_vmtx parts (whole pa_lp 1,243,436)"),
    "bk_col": ([], "bk_col FLATTENED: Yosys (PLAN-S81v4-SYN 10-23, ORFS asap7lock RVT) dsdv_bkcol_l 15,770 x4 (2 SRAM "
               "each) + dsdv_bkcol_m 73,514 + bk_g 2 x 25,144 measured = 186,882 cells, 8 SRAM macros"),
    "seqhost": ([("sh_children", 6989 + 11889 + 69671 + 40770)], "seq_host_mux children (sh_vc, mu_hslot, mu_hwin, "
                "seq_host_c_r3_lp); whole MISSING"),
    "iqf": ([("idx_qf", 11296)], "dsdv_idx_qf 11,296 (F gold2)"),
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
    if p.name == "bk_col":
        return [], 4 * 15770 + 73514 + 2 * 25144, UNIT_CORES["bk_col"][1]
    if p.name == "seqhost":
        # v4: the MU history window (dsdv_mu_hwin_capture_1019, 69,671 cells + SRAM columns) is a planned hard core
        # (GEOM-REVIEW: SUPERSEDED dsdv_mu_hwin_capture_1019 by seqhost core hwin); the other children flattened
        return [("hwin", 69671)], 6989 + 11889 + 40770 + 10000, \
            "seq_host_mux children: hwin core 69,671 + sh_vc/mu_hslot/seq_host_c_r3_lp flattened (whole MISSING)"
    if p.name in UNIT_CORES:
        c, why = UNIT_CORES[p.name]
        return c, 10000, why
    return [], 0, "MISSING"


def census_collapse(rows):
    """landing cells (ld_*) re-attributed to their single source (reset fan-in excluded)."""
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
        if lk.get("path") and lk["path"][0] == "xrow":
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
    res.update(route(grid, todo, {}))
    ROUTE_V48.update(kept=len(res) - len(todo), rerouted=sorted(l["id"] for l in todo))
    return res


ROUTE_V48 = {}


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
    shutil.copy(CENSUS_SRC[0], out / "census" / "s81_lanes.tsv")


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
    runs.sort(key=lambda r: (r["lane"] in new48, -len(r["ports"]), -r["width"], r["role"], r["lane"], r["line"]))
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
    tname = {}
    cnt = collections.Counter()
    for key in types:
        base = re.sub(r"[^A-Za-z0-9_]", "_", key[0])
        cnt[base] += 1
        tname[key] = "%s__t%d" % (base, cnt[base])
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
        hc_ = frame_hard_cores(rep.contents, buses) + nonframe_hard_cores(rep, rep.w, rep.h, tn, ftsl, buses)   # S81-P9-HC
        for s_ in ftsl:
            k0 = s_["stations"]
            s_["stations"] = ft_stations_macro(s_, hc_, rep.w, rep.h)
            if s_["stations"] != k0:
                FT_MACRO_ADD.append(dict(type=tn, slot=s_["name"], stations=[k0, s_["stations"]]))
        ty = dict(module="s81p_" + tn, outline_um=[rep.w, rep.h], hard=rep.hard, buses=buses, ft_slots=ftsl,
                  clock=dict(tap_um=[round(rep.w / 2 / G) * G, round(rep.h / 2 / G) * G], layer="M9"),
                  reset=dict(sync_stages=2), contents=frame_contents(rep.contents, buses),
                  **({"sources": FRAME_SOURCES(rep.contents)} if FRAME_SOURCES(rep.contents) else {}),
                  **({"hard_cores": hc_} if hc_ else {}),
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
    olanes = [dict(id=l["id"], ports=lane_ports[l["id"]], **({"fixed_cycles": l["fixed"]} if l.get("fixed") else {}))
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
                                 "die_use": ["clock_spine", "pg", "ft_reserved"], "cut_avail": {"M8": 0.6, "M9": 0.6}},
                "pg": {"partition_pg_max": "M7", "grid": [
                    {"layer": "M8", "width_um": 0.48, "pitch_um": 8.64, "offset_um": 4.32, "nets": ["VDD", "VSS"]},
                    {"layer": "M9", "width_um": 0.48, "pitch_um": 8.64, "offset_um": 4.32, "nets": ["VDD", "VSS"]}]},
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
        "clock": {"source": {"part": "@die", "bus": "clk"}, "insertion_ps": 250, "common_latency_ps": 250, "insertion_tol_ps": 40,   # R4 die-wide common latency (COORD G0C)
                  "neighbour_skew_ps": 80, "face_xing": "budgeted",
                  "spine": {"layers": ["M8", "M9"], "root_um": [round(X0 + 11 * PX, 4), round(X0 + 10 * PY, 4)],
                            "topology": "htree"}},
        "reset": {"source": {"part": "@die", "bus": "rst_n"}, "sync_stages": 2, "data_reset": False,
                  "epoch_bit": True, "release": "counted"},
        "census": [{"rows": "census/s81_lanes.tsv", "map": "census_map.json",
                    "note": "FT census of the bound as-built die (1364 rows); finer partition-level check incl. "
                            "bus-aware lep rx/tx and src-bus dedup: census_cov.py -> v3/census_cov.json"}],
        "budgets": {"face_pins_per_um": 6, "face_pin_layers": 2, "face_window_um": 10, "pin_track_max": 0.6,
                    "cut_ratio_max": 0.6, "cut_step_um": 250},
    }
    STATS_V4["macrofree_ft_reach"] = macrofree_ft_reach(plan)
    STATS_V4["face_layers"] = FACE_GRANTS     # svc fold faces (COORD S81 ruling (1)(b) 10-23 07:43)
    out.mkdir(parents=True, exist_ok=True)
    json.dump(plan, open(out / "die_plan.json", "w"), indent=0)
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
