#!/usr/bin/env python3
"""S81-CORE-LAT-R6 (COORD 13:56 envelope ruling): qxpq_w10 _gb CGR regions re-planned as MORE, SMALLER ONE-LEVEL regions
inside the PLAN-ICG-MODEL calibration envelope (tools/die_plan/core_infra_plan.CAL_ENVELOPE), predicted with the same
plan model (open_subtree + ICGx1 liberty arc) BEFORE any build (12.9d).

Input: physical/die_plan/s81/core_lat/qxpq_w10_regions.json (the 8 RTL gate regions of CGR 8: rects + Yosys sink census;
PRE-PLACEMENT census -- the sink positions inside a region are not known until the r6gb place run).
Structure planned here (12.8b, one level, no nested gates):
  * every RTL region k (gate u_cg_r<k>, registered enable zr[k]) is split into nx x ny equal sub-rects; each sub-rect gets
    ONE ICG copy on the same enable zr[k] at its centre (gate clone = same function, LEC-ICG proves it) driving only
    the gated sinks of that sub-rect -> CTS-open subtree of N_g = region flops / (nx*ny) (uniform density, UNCHECKED);
  * the 12,258 ungated clk flops get one planned ungated leaf buffer per sub-rect (cts_open), N_u = 12,258 / n_sub;
  * equal stage count by structure: a leaf whose ceil(log24 N) is below the design k gets plan-fixed extra buffer
    stages at its root (12.8c/d1 fixed chain, counted in the prediction as stage_ps each), never post-measurement pads;
  * the entry H-tree (centre pin -> sub-rect centres) is equal-length by construction; its delay is the REMAINDER
    to the 250 TT / 202.5 FF target and is reported, not assumed.
Window (core-pin target band 250 +-20, window <= 20) = max over leaves of (gate + subtree max) - min of (gate + subtree
min): the H-tree adds nothing by construction (PLAN MODEL, UNCHECKED; H-tree branch mismatch from legal-site
displacement not included).
usage: qxpq_cgr_plan.py REGIONS.json LIBDIR OUT.json [--grid NXxNY ...]
"""
import json
import math
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools/die_plan"))
import core_infra as CI          # noqa: E402
import core_infra_plan as CP     # noqa: E402
import die_clock_128 as C128     # noqa: E402

reg_js, libdir, out = sys.argv[1:4]
grids = [g for i, g in enumerate(sys.argv) if i > 0 and sys.argv[i - 1] == "--grid"] or ["2x3"]
R = json.load(open(reg_js))
W, H = R["outline_um"]
UNG = R["ungated_clk_flops"]
TARGET = {"TT": 250.0, "FF": 202.5}
ENV = CP.CAL_ENVELOPE
root_cap = {c: C128.lib_cells(c, libdir, names=(CP.CTS_ROOT_MASTER,))[CP.CTS_ROOT_MASTER]["cap"] for c in TARGET}
icg = {c: CP.icg_lib_cells(c, libdir)["ICGx1_ASAP7_75t_R"] for c in TARGET}
SLEW = 40.0
BUF_D = {"TT": None, "FF": None}


def leaves_for(grid):
    nx, ny = map(int, grid.split("x"))
    n_sub = nx * ny * len(R["regions"])
    leaves = []
    for r in R["regions"]:
        x0, y0, x1, y1 = r["rect_um"]
        n = r["sink_estimate"]["flops"] + r["sink_estimate"].get("macros", 0)
        for i in range(nx):
            for j in range(ny):
                rect = [x0 + (x1 - x0) * i / nx, y0 + (y1 - y0) * j / ny, x0 + (x1 - x0) * (i + 1) / nx,
                        y0 + (y1 - y0) * (j + 1) / ny]
                leaves.append(dict(name=f"r{r['region']}_{i}{j}", kind="gated", gate_of=r["gate"], rect_um=rect,
                                   sinks=math.ceil(n / (nx * ny))))
                leaves.append(dict(name=f"u{r['region']}_{i}{j}", kind="ungated", rect_um=rect,
                                   sinks=math.ceil(UNG / n_sub)))
    return leaves


def plan(grid):
    L = leaves_for(grid)
    for lf in L:
        lf["levels"] = CI._cts_levels(dict(domain_sinks=lf["sinks"], cts_fanout=CI.CTS_FANOUT), lf["name"])
    K = max(lf["levels"] for lf in L)
    res = dict(grid=grid, n_leaves=len(L), design_levels=K, envelope=ENV, corners={})
    bad = []
    for lf in L:
        reach = CP.region_reach(lf["rect_um"])
        why = CP.calibration_check(lf["sinks"], lf["levels"], reach, lf["rect_um"], [W, H])
        lf.update(reach_um=round(reach, 2), pad_stages=K - lf["levels"], envelope="IN" if not why else "OUT")
        if why:
            bad.append((lf["name"], why))
    for c in TARGET:
        cal = CP.OPEN_SUBTREE_CAL[c]
        g = icg[c]
        d_icg = C128._bilin(g["delay"], SLEW, root_cap[c])
        lo, hi, means = [], [], []
        for lf in L:
            s = CP.open_subtree(lf["sinks"], lf["rect_um"], c)
            front = (d_icg if lf["kind"] == "gated" else d_icg)   # ungated leaf buffer sized by the plan to the ICG arc
            pad = lf["pad_stages"] * cal["stage_ps"]
            lo.append(front + pad + s["min_ps"])
            hi.append(front + pad + s["max_ps"])
            means.append(front + pad + s["mean_ps"])
        mean = sum(means) / len(means)
        res["corners"][c] = dict(icg_arc_ps=round(d_icg, 2), leaf_mean_ps=round(mean, 2),
                                 leaf_mean_spread_ps=round(max(means) - min(means), 2),
                                 window_ps=round(max(hi) - min(lo), 2), entry_tree_budget_ps=round(TARGET[c] - mean, 2))
    res["envelope_out"] = bad
    res["valid"] = not bad
    res["in_band"] = all(v["window_ps"] <= 20.0 and v["entry_tree_budget_ps"] > 0 for v in res["corners"].values())
    res["leaves_sample"] = L[:4]
    res["sinks_range"] = [min(lf["sinks"] for lf in L if lf["kind"] == "gated"), max(lf["sinks"] for lf in L if lf["kind"] == "gated")]
    res["reach_max_um"] = max(lf["reach_um"] for lf in L)
    res["pad_stage_leaves"] = sum(1 for lf in L if lf["pad_stages"])
    return res


rows = [plan(g) for g in grids]
Path(out).write_text(json.dumps(dict(schema="opentallas.qxpq_cgr_plan.v1", model="PLAN-ICG-MODEL open_subtree + ICGx1 NLDM; "
                                     "uniform sink density per RTL region (PRE-PLACEMENT), UNCHECKED", regions=reg_js,
                                     rows=rows), indent=1) + "\n")
for r in rows:
    print(r["grid"], "leaves", r["n_leaves"], "k", r["design_levels"], "valid", r["valid"], "in_band", r["in_band"],
          "gated sinks", r["sinks_range"], "reach_max", r["reach_max_um"], "pad-leaves", r["pad_stage_leaves"],
          {c: (v["window_ps"], v["leaf_mean_ps"], v["entry_tree_budget_ps"]) for c, v in r["corners"].items()},
          "OUT", len(r["envelope_out"]))
