#!/usr/bin/env python3
"""HOLD-REPAIR (METHODOLOGY 12.4a a1, OWNER 2026-10-26 ~17:3x): plan-declared seam hold demand + data-path hold-cell
estimate per die.  Plan analysis only: nothing here reads a measured clock arrival or a trim.

12.4a a1 allows the flow (repair_timing -hold) to insert delay cells on short DATA paths until FF hold passes; the
clock is never touched.  For a zero-logic seam pair (pin register -> abutted pin register of the neighbour partition)
the CPPR-left clock pessimism of the non-common clock branches is far above the plain pair budget (QC-MP-REGION-2:
10.9 ps FF budget vs >= 29.5 ps flat-OCV pessimism, UNCHECKED).  This tool turns the PLAN's declared clock arrival
model into a per-seam FF hold demand D (ps) that the RECEIVING tile carries as an input hold constraint
(gen_phys clock.io_hold = "plan_demand": min input delay = sender guarantee - D), so the tile's own FF hold repair
pads its seam inputs and the tile stays self-contained (option (a); see HOLD_PLACEMENT_RATIONALE).

Per seam (a region_clock pair row, via seam_landing.json: last common node, modelled non-common clock delay per corner,
bits per direction):
    D_ff = pessimism_FF(non-common, derate model) + declared FF arrival window (entry window + core tap window)
    pad per receiving bit (kit contract, what the flow inserts) = t_hold_FF + (1 - UNC_SPLIT) x UNC_HOLD - (g - D_ff)
        with g = the sender's guaranteed output-min (gen_phys.sender_out_guarantee_ps, 12.5 ps plan contract)
    physical need per bit (credits clk->q, seam_landing budget) = max(0, D_ff - hold budget 10.88)
    cells per bit = ceil(pad / (d_cell_FF_min x data cell_early)); TT cost = cells x d_cell_TT_max x data cell_late x IR
    TT setup after insertion = setup budget 631.8 - setup pessimism_TT - declared TT window - TT cost  (>= 0 -> "pad",
        else "land": the seam needs a landed/forwarded hop, hold delay cannot close it)
Derate models: "flat" (die_ci_margins.json clock derates, the region_clock / seam_landing numbers) and "aocv_draft"
(depth/distance placeholder until CLK-AOCV publishes its owner-reviewed table: random part ~ 1/sqrt(stages),
non-averaging systematic part + distance slope, differential IR only across regions, 12.4a b1).  --aocv-table JSON
replaces the placeholder.  A mesh what-if (--mesh-skew-ps) treats a SIGNED-OFF regional mesh as the common point
(12.8e exception): only the core tree below it is non-common, plus the mesh skew as explicit uncertainty.
All numbers are estimates (UNCHECKED) until a routed kit's census (hold_cell_census) and die STA confirm them.
"""
import argparse
import json
import math
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent

SCHEMA = "opentallas.hold_demand.v1"
from die_sta import PERIOD_PS  # exact canonical timing policy
UNC_HOLD_PS, UNC_SPLIT = 25.0, 0.5
# region_clock stage model (QC-MP-REGION-2): stage delay = d0 + k x um, full stage 450 um; cell share of a full stage
STAGE = {"TT": (52.713, 0.058822), "FF": (38.561, 0.060298)}
# opt-in stage models (--stage-model; default r4_native = STAGE above, output unchanged).
# r6_rcx_ndr016 (CLOCK-128-R8): the R4 native cell intercept d0 kept, the wire slope refit so the model reproduces the
# CLOCK-128-R6 routed-clock OpenRCX (ndr016 width-aware rules) legs: 235 single-load BUFx24 legs, mean 430.2 um,
# mean stage 103.16 ps TT / 85.68 ps FF (epyc2 clock128-r6-1026/r5x tree_{TT,FF}_rcx.txt).  A free 2-parameter fit is
# ill-conditioned on that narrow length range (354-442 um: d0 -11.5 ps TT, unphysical), so d0 stays the native one.
STAGE_MODELS = {
    "r4_native": dict(STAGE),
    "r6_rcx_ndr016": {"TT": (52.713, round((103.16 - 52.713) / 430.2, 6)),
                      "FF": (38.561, round((85.68 - 38.561) / 430.2, 6))},
}


def set_stage_model(name):
    """select a STAGE_MODELS entry for this process (module STAGE updated in place)"""
    STAGE.clear()
    STAGE.update(STAGE_MODELS[name])
    return dict(STAGE)
REP_UM = 450.0
CORE_LAT = {"TT": 250.0, "FF": 202.5}
CORE_STAGES = 10            # partition tree tap -> face flops: 8-14 stages (die_ci_margins.json ocv.why)
FLAT = dict(cell_late=0.05, cell_early=0.05, net_late=0.03, net_early=0.03, ir_late=0.051)
# DRAFT AOCV placeholder (NOT owner-reviewed; CLK-AOCV builds the real table, 12.4a b1).  Random cell part 5 % at the
# 10-stage reference of the flat number, scaled sqrt(10 / N); systematic (non-averaging) 1 % + 0.1 %/mm of span; net
# random 3 % x sqrt(10 / N) + 0.5 % systematic.  IR (owner 17:5x): differential only -> 0 for branches in one
# region / PDN region, the full one-sided 5.1 % across regions until PDNSim.
AOCV_DRAFT = dict(cell_rand_ref=0.05, net_rand_ref=0.03, ref_stages=10, cell_sys=0.01, net_sys=0.005,
                  sys_per_mm=0.001, ir_cross_region=0.051)
SAME_REGION = ("region_node", "region_root")
# hold delay cells (ASAP7 INVBUF RVT NLDM 220122, slew 20 ps, load = next cell pin + 1 fF; min/max of rise/fall):
# HB4xp67 is the pad cell of physical/common_flow/hold_pad_hb4.tcl (dont_use lifted only inside repair_timing -hold).
HOLD_CELLS = {
    "HB4xp67": dict(area_um2=0.1021, ff_min_ps=46.90, tt_max_ps=75.20),
    "BUFx2": dict(area_um2=0.0729, ff_min_ps=17.33, tt_max_ps=24.03),
}
DATA_DERATE = dict(cell_late=1.05, cell_early=0.95, ir_late=1.0511)   # data paths keep flat derates (12.4a b1)

HOLD_PLACEMENT_RATIONALE = (
    "(a) receiving tile, input path (chosen): hierarchical sign-off practice is top-down timing budgeting -- the top "
    "level hands each block IO constraints (set_input_delay -min/-max) derived from the top clock plan, the block "
    "closes them in its own flow (Cadence/Synopsys budgeting, ETM/ILM blocks), and the top only verifies.  Here the "
    "seams are ABUTTED (no die-top rows between neighbours), the receiver already owns its face flops and its FF "
    "hold repair (run_kit.sh FF GRT step), one value per type port covers every instance, and the delay sits on the "
    "receiver's own input net, so no new die-top placement, no ECO on a routed die and no hand edit.  (b) die-top "
    "cells in channels/bays: only where a channel exists; it would need std-cell rows + PG + a die-level repair "
    "step on the abutted seams, breaks tile self-containment and puts the cells far from the receiving flop -- kept "
    "as the fallback for channel crossings only (gen_phys keeps the fallback contract on channel ports).")


def stage_full(c):
    return STAGE[c][0] + STAGE[c][1] * REP_UM


def cell_share(c):
    return STAGE[c][0] / stage_full(c)


def noncommon_stages(nc, c, mesh=False):
    """approx. stage count of one non-common branch: die part at full 450 um stages + the core tree."""
    die = 0.0 if mesh else max(0.0, nc - CORE_LAT[c])
    return die / stage_full(c) + CORE_STAGES, die / stage_full(c) * REP_UM / 1000.0 / 2.0


def derates(model, cls, nc, c, mesh=False, table=None):
    """(cell late+early+ir, net late+early) summed derate fractions on the non-common clock delay of a pair."""
    if model == "flat":
        return (FLAT["cell_late"] + FLAT["ir_late"] + FLAT["cell_early"], FLAT["net_late"] + FLAT["net_early"])
    n, span_mm = noncommon_stages(nc, c, mesh)
    if table is not None:
        for row in table["rows"]:
            if n <= row["max_stages"] and span_mm <= row["max_mm"]:
                cell, net = row["cell"], row["net"]
                break
        else:
            raise ValueError(f"aocv table: no row for {n:.1f} stages / {span_mm:.2f} mm")
        ir = 0.0 if (cls in SAME_REGION or mesh) else float(table.get("ir_cross_region", AOCV_DRAFT["ir_cross_region"]))
        return 2 * cell + ir, 2 * net
    a = AOCV_DRAFT
    s = math.sqrt(a["ref_stages"] / n)
    cell = a["cell_rand_ref"] * s + a["cell_sys"] + a["sys_per_mm"] * span_mm
    net = a["net_rand_ref"] * s + a["net_sys"] + a["sys_per_mm"] * span_mm
    ir = 0.0 if (cls in SAME_REGION or mesh) else a["ir_cross_region"]
    return 2 * cell + ir, 2 * net


def pessimism(model, cls, nc, c, mesh=False, table=None):
    dc, dn = derates(model, cls, nc, c, mesh, table)
    f = cell_share(c)
    return nc * (f * dc + (1 - f) * dn)


def seam_rows(sl, model, windows, cell, guarantee_ps, hold_ff_lib_ps, mesh_skew_ps=None, table=None):
    B = sl["budgets"]
    hc = HOLD_CELLS[cell]
    d_ff = hc["ff_min_ps"] * DATA_DERATE["cell_early"]
    d_tt = hc["tt_max_ps"] * DATA_DERATE["cell_late"] * DATA_DERATE["ir_late"]
    legacy_pad = hold_ff_lib_ps + (1 - UNC_SPLIT) * UNC_HOLD_PS + 40.0     # legacy in_min -insertion_tol 40
    rows = []
    for s in sl["seams"]:
        mesh = mesh_skew_ps is not None
        nc = {c: (CORE_LAT[c] if mesh else s[f"nc_{c.lower()}_ps"]) for c in ("TT", "FF")}
        p_ff = pessimism(model, s["cls"], nc["FF"], "FF", mesh, table) + (mesh_skew_ps or 0.0)
        p_tt = pessimism(model, s["cls"], nc["TT"], "TT", mesh, table) + (mesh_skew_ps or 0.0)
        D = p_ff + windows["FF"]
        pad = max(0.0, hold_ff_lib_ps + (1 - UNC_SPLIT) * UNC_HOLD_PS - (guarantee_ps - D))
        phys = max(0.0, D - B["hold_ff_ps"])
        n = math.ceil(pad / d_ff - 1e-9) if pad > 0 else 0
        setup = B["setup_tt_ps"] - p_tt - windows["TT"] - n * d_tt
        bits = s["bits_ab"] + s["bits_ba"]
        rows.append(dict(a=s["a"], b=s["b"], cls=s["cls"], bits=bits, demand_ff_ps=round(D, 2),
                         pess_ff_ps=round(p_ff, 2), pess_tt_ps=round(p_tt, 2), contract_pad_ps=round(pad, 2),
                         physical_need_ps=round(phys, 2), cells_per_bit=n,
                         physical_cells_per_bit=(math.ceil(phys / d_ff - 1e-9) if phys > 0 else 0),
                         legacy_cells_per_bit=math.ceil(legacy_pad / d_ff - 1e-9),
                         setup_tt_after_ps=round(setup, 2), action=("pad" if setup >= 0 else "land")))
    return rows


def summarise(rows, cell):
    a = HOLD_CELLS[cell]["area_um2"]
    tt_cost = HOLD_CELLS[cell]["tt_max_ps"] * DATA_DERATE["cell_late"] * DATA_DERATE["ir_late"]
    by = defaultdict(list)
    for r in rows:
        by[r["cls"]].append(r)
    out = {}
    for k, v in sorted(by.items()) + [("DIE", rows)]:
        pad = [r for r in v if r["action"] == "pad"]
        cells = sum(r["bits"] * r["cells_per_bit"] for r in pad)
        legacy = sum(r["bits"] * r["legacy_cells_per_bit"] for r in pad)
        out[k] = dict(seams=len(v), seams_pad=len(pad), seams_land=len(v) - len(pad),
                      bits_pad=sum(r["bits"] for r in pad), bits_land=sum(r["bits"] for r in v if r["action"] == "land"),
                      demand_ff_ps=[min(r["demand_ff_ps"] for r in v), max(r["demand_ff_ps"] for r in v)],
                      cells_per_bit=[min(r["cells_per_bit"] for r in v), max(r["cells_per_bit"] for r in v)],
                      hold_cells=cells, hold_area_um2=round(cells * a, 1),
                      physical_lower_bound_cells=sum(r["bits"] * r["physical_cells_per_bit"] for r in pad),
                      tt_added_ps_per_bit_max=(round(max(r["cells_per_bit"] for r in pad) * tt_cost, 2) if pad else 0),
                      legacy_contract_cells_same_bits=legacy,
                      setup_tt_after_min_ps=(round(min(r["setup_tt_after_ps"] for r in pad), 2) if pad else None))
    return out


def plan_fragment(rows, model, windows, cell, guarantee_ps, source_desc):
    """clock.hold_demand for the plan: pairs 'a|b' (sorted) -> D_ff ps for padded seams; landed seams listed (the
    kit keeps the fallback contract on them: they are closed by a landed hop, not by hold delay)."""
    return dict(source="plan", schema=SCHEMA, derate=model, cell=cell,
                windows_ps=windows, sender_guarantee_ps=guarantee_ps, basis=source_desc,
                pairs={"|".join(sorted((r["a"], r["b"]))): math.ceil(r["demand_ff_ps"] * 10) / 10.0
                       for r in rows if r["action"] == "pad"},
                landed=sorted("|".join(sorted((r["a"], r["b"]))) for r in rows if r["action"] == "land"))


def hold_cell_census(paths, cell="HB4xp67"):
    """measured hold-cell count from kit logs (hold_pad_hb4.tcl 'OT_HB4PAD: after hold repair the design holds N')
    -> {path: cells}; the per-die report sums them.  Only for routed kits; never an input to D."""
    import re
    out = {}
    for p in paths:
        n = None
        for f in sorted(Path(p).rglob("*.log")):
            for m in re.finditer(r"OT_HB4PAD: after hold repair the design holds (\d+)", f.read_text(errors="replace")):
                n = int(m.group(1))
        out[str(p)] = n
    return dict(per_kit=out, cells=sum(v for v in out.values() if v), area_um2=round(
        sum(v for v in out.values() if v) * HOLD_CELLS[cell]["area_um2"], 1))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--seam-landing", required=True, help="seam_landing.json (tools/die_plan/seam_landing.py)")
    ap.add_argument("--region-summary", help="region_summary.json: declared die_path entry windows (TT/FF)")
    ap.add_argument("--entry-window-ff", type=float, help="declared FF entry arrival window ps (else region summary)")
    ap.add_argument("--entry-window-tt", type=float, help="declared TT entry arrival window ps (else region summary)")
    ap.add_argument("--core-window-ps", type=float, default=20.0, help="declared core tap window (12.3: <= 20 ps)")
    ap.add_argument("--derate", choices=("flat", "aocv_draft"), default="flat")
    ap.add_argument("--stage-model", choices=sorted(STAGE_MODELS), default="r4_native",
                    help="die tree stage delay model (default r4_native = unchanged; r6_rcx_ndr016 = CLOCK-128-R8 refit "
                         "to the R6 routed-clock RCX legs)")
    ap.add_argument("--aocv-table", help="CLK-AOCV table JSON {rows:[{max_stages,max_mm,cell,net}], ir_cross_region}")
    ap.add_argument("--mesh-skew-ps", type=float, help="what-if: signed-off regional mesh = common point + this skew")
    ap.add_argument("--cell", choices=sorted(HOLD_CELLS), default="HB4xp67")
    ap.add_argument("--sender-guarantee-ps", type=float, default=12.5,
                    help="sender guaranteed output-min after vclk (gen_phys plan contract 12.5)")
    ap.add_argument("--hold-ff-lib-ps", type=float, default=12.28, help="DFFHQNx1 FF hold (die_ci_margins lib)")
    ap.add_argument("--out", required=True, help="output dir: hold_demand.json + plan_hold_demand.json")
    a = ap.parse_args(argv)
    if a.stage_model != "r4_native":
        set_stage_model(a.stage_model)
    sl = json.loads(Path(a.seam_landing).read_text())
    rs = json.loads(Path(a.region_summary).read_text()) if a.region_summary else {}
    ew = {c: (getattr(a, f"entry_window_{c.lower()}") if getattr(a, f"entry_window_{c.lower()}") is not None else
              rs["die_path"][c]["input_to_entry_ps"]["window"]) for c in ("TT", "FF")}
    windows = {c: round(ew[c] + a.core_window_ps, 3) for c in ("TT", "FF")}
    table = json.loads(Path(a.aocv_table).read_text()) if a.aocv_table else None
    model = "aocv_table" if table else a.derate
    rows = seam_rows(sl, "aocv_draft" if table else a.derate, windows, a.cell, a.sender_guarantee_ps,
                     a.hold_ff_lib_ps, a.mesh_skew_ps, table)
    summ = summarise(rows, a.cell)
    desc = (f"seam_landing {a.seam_landing}; derate {model}; windows entry {ew} + core {a.core_window_ps:g}"
            + (f"; mesh what-if skew {a.mesh_skew_ps:g}" if a.mesh_skew_ps is not None else ""))
    rec = dict(schema=SCHEMA, label="UNCHECKED estimate (plan model; no routed census)", derate=model,
               mesh_skew_ps=a.mesh_skew_ps, cell=a.cell, cell_data=HOLD_CELLS[a.cell], data_derate=DATA_DERATE,
               windows_ps=windows, budgets=sl["budgets"], placement=HOLD_PLACEMENT_RATIONALE,
               aocv_draft=(AOCV_DRAFT if model == "aocv_draft" else None), summary=summ, seams=rows)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "hold_demand.json").write_text(json.dumps(rec, indent=1) + "\n")
    (out / "plan_hold_demand.json").write_text(json.dumps(
        plan_fragment(rows, model, windows, a.cell, a.sender_guarantee_ps, desc), indent=1) + "\n")
    print(json.dumps(dict(derate=model, mesh_skew_ps=a.mesh_skew_ps, windows_ps=windows, summary=summ), indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
