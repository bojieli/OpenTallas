#!/usr/bin/env python3
"""W18: compose the hierarchical static IR drop of the V4.1 ROM layer die (element -> switch ring -> cluster ->
die) into one record per power scenario, against the supply budget.

Levels (each a committed, source-pinned result):
  element  W10 p5 pair, PSM on the routed odb (pair_w10p5_abstract.json ir), at 0.239 W; scaled linearly to
           the scenario's per-pair power (IR is linear in current)
  switch   the header ring (tools/w18/die_pdn.py switch_ring, 10 mV design point at 5% area, 20 mV at 2.5%)
  cluster  PSM on 16 pair current-map tiles (ir/cluster16_1p2/result.json), at 0.2663 W per pair
  die      M8/M9 + micro-bump mesh (ir/die_mesh_*.json)
The worst nodes of the levels need not coincide, so the sum is an upper bound.  VDD and VSS are both summed:
the switch ring is on VDD only.

    python3 tools/w18/ir_stack.py --output results/physical_abi3/asap7/chip/v41_w18/ir/ir_stack.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
D = ROOT / "results/physical_abi3/asap7/chip/v41_w18"
VDD = 0.7
PAIR_W_12 = 0.2663            # busy pair at 1.2 GHz (0.2296 measured x 1.16, root)
SS_BUDGET_MV = 70.0           # ASAP7 SS sign-off at 0.63 V = -10%: IR + droop + regulator tolerance share it


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args(argv)
    pair = json.loads((D / "pair_w10p5_abstract.json").read_text())
    p_ir = pair["ir"]
    p_w = pair["power_w_per_pair"]["scenarios"]["default"]
    cl = json.loads((D / "ir/cluster16_1p2/result.json").read_text())
    cl_w = cl["meta"]["pair_w"]
    ring = {10: dict(area_frac=0.05), 20: dict(area_frac=0.025)}
    scen = {
        "peak_all_busy_1p2": dict(die=D / "ir/die_mesh_peak_all_busy_1p2.json", pair_w=PAIR_W_12, cluster_frac=1.0,
                                  note="every holding pair busy at once (field-wide op, no cap)"),
        "peak_cap50_1p2": dict(die=D / "ir/die_mesh_peak_cap50_1p2.json", pair_w=PAIR_W_12, cluster_frac=0.5,
                               note="50% checkerboard cap: a pair still draws its full current on its beats "
                                    "(element level unchanged); cluster and die carry half"),
        "saturation_duty_1p2": dict(die=D / "ir/die_mesh_saturation_duty_1p2.json", pair_w=PAIR_W_12,
                                    cluster_frac=0.0765,
                                    note="model saturation duty (busy pair-equivalents 543 / 7,102) as an average; the "
                                         "peak of an op inside it is the peak case"),
    }
    rows = {}
    for k, s in scen.items():
        die = json.loads(s["die"].read_text())
        e = {n: p_ir[n]["worst_ir_drop_v"] * 1e3 * s["pair_w"] / p_w for n in ("VDD", "VSS")}
        c = {n: cl["ir"][n]["Worstcase IR drop"] * 1e3 * s["cluster_frac"] * (s["pair_w"] / cl_w) for n in ("VDD", "VSS")}
        dd = die["vdd_drop_mv"]["worst"]
        cur_cluster = 16 * s["pair_w"] * s["cluster_frac"] / VDD
        sw = {f"{mv}mV_design": round(mv * cur_cluster / (16 * PAIR_W_12 / VDD), 2) for mv in ring}
        vdd = e["VDD"] + sw["10mV_design"] + c["VDD"] + dd
        vss = e["VSS"] + c["VSS"] + dd
        rows[k] = dict(note=s["note"],
                       element_mv=dict(VDD=round(e["VDD"], 2), VSS=round(e["VSS"], 2)),
                       switch_ring_mv=sw,
                       cluster_mv=dict(VDD=round(c["VDD"], 2), VSS=round(c["VSS"], 2)),
                       die_mv=dict(VDD=round(dd, 2), VSS=round(dd, 2), mean=die["vdd_drop_mv"]["mean"]),
                       total_vdd_mv=round(vdd, 1), total_vss_mv=round(vss, 1),
                       rail_to_rail_mv=round(vdd + vss, 1), pct_of_vdd=round(100 * (vdd + vss) / (VDD * 1e3), 1),
                       within_ss_budget=(vdd + vss) <= SS_BUDGET_MV,
                       die_record=str(s["die"].relative_to(ROOT)), die_record_sha256=sha(s["die"]))
    rec = dict(
        schema="opentallas.v41.w18_ir_stack.v1",
        scenarios=rows,
        budget=dict(ss_signoff_v=0.63, budget_mv=SS_BUDGET_MV,
                    basis="ASAP7 SS libraries are characterised at 0.63 V (-10%); static IR, first droop and regulator "
                          "tolerance all spend it"),
        levers=[
            "element: the W10 pair's grid is M5/M6 only (5.4 um per net) and its worst node is 22.5 mV at 0.239 W -- "
            "the largest term; re-harden with M7 power straps (also needed for abutment and a reachable abstract)",
            "die: ASAP7 M8/M9 are thin (0.34 ohm/sq); a production 5 nm-class stack has thick top metals and an RDL, "
            "roughly an order of magnitude lower, so the die term here is pessimistic (ASSUMED ratio, PDK-limited)",
            "bump pitch 40 um with 1/3 VDD (ASSUMED); a denser power-bump share lowers the die term directly",
            "the 50% cap halves the cluster and die terms; saturation duty is an average, not a peak",
        ],
        sources=dict(pair_record=sha(D / "pair_w10p5_abstract.json"),
                     cluster=sha(D / "ir/cluster16_1p2/result.json")),
        tool_sha256=sha(Path(__file__)))
    a.output.write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps({k: {x: v[x] for x in ("element_mv", "switch_ring_mv", "cluster_mv", "die_mv", "rail_to_rail_mv",
                                            "pct_of_vdd", "within_ss_budget")} for k, v in rows.items()}, indent=1))


if __name__ == "__main__":
    main()
