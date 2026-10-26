#!/usr/bin/env python3
"""Conservative pre-build QC clone estimates, including real landing hardware.

This is a logical standard-cell planning bound, not mapped area or signoff.
Ring counts come from flattened canonical RTL at each actual width. Allow
three cells per FF (clock/output polarity included), six per Boolean primitive
(even a XOR or mux fits a six-NAND decomposition). Buffers/clock synthesis and
physical density still require the master plan and mapped implementation.
Collector bounds charge EVERY reset-tree node, including inactive nodes, and
one extra raw-reset FF per node and local landing. No active source is dropped.
"""
import json
import argparse
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def generate():
    sidecar = json.loads((HERE / "landing_sidecar88.json").read_text())
    plan = json.loads((ROOT / "physical/die_plan/qwen_compute/candidate_oneqc0733.json").read_text())
    notes = json.loads((ROOT / "physical/die_plan/qwen_compute/plan_notes.json").read_text())
    primitive_weights = {"$_DFF_P_": 3, "$_DFF_N_": 3,
                         "$_AND_": 6, "$_OR_": 6, "$_NOT_": 6,
                         "$_XOR_": 6, "$_MUX_": 6}
    rings = {}
    for path in (HERE / "cells").glob("width_*.stat.json"):
        data = json.loads(path.read_text())["design"]
        counts = data["num_cells_by_type"]
        assert not set(counts) - primitive_weights.keys(), path
        assert data["num_cells"] == sum(counts.values()), path
        rings[int(path.name.split("_")[1].split(".")[0])] = sum(
            n * primitive_weights[k] for k, n in counts.items())
    rows = {}
    assert set(plan["partition_types"]) == set(sidecar["collector"]["types"])
    for name, info in sidecar["collector"]["types"].items():
        base = info["base_type"]
        base_value = notes["cells_per_type"][base]
        base_cells = base_value if isinstance(base_value, int) else base_value["cells"]
        widths = [int(s["band"]["width"]) + 1 for s in info["local_sources"]]
        assert len(widths) == len(info["mask"]["inputs"]), name
        seams = sum(bool(c["seam"]) for c in info["children"])
        landing = sum(rings[w] for w in widths) + seams * rings[2]
        # Extra raw reset copies are needed only for gated mission taps. Charge
        # one for every local landing, safely including taps needing no copy.
        reset_copies = 3 * len(widths)
        nodes = len(info["tree"]["relays"]) + 1 if info["mask"]["active"] else 0
        # Sum of collector input degrees <= local/child sources + tree edges.
        inputs = len(widths) + len(info["children"]) + max(0, nodes - 1)
        collector = (9 * nodes + 6 * (2 * inputs + 2 * nodes + 3 * seams)
                     + 12 * bool(info["mask"].get("observer"))) if nodes else 0
        rows[name] = dict(cells=base_cells + landing + reset_copies + collector,
                          base_type=base, base_cells=base_cells,
                          landing_widths=widths, monitor_seams=seams,
                          landing_cells_upper=landing, reset_copy_cells_upper=reset_copies,
                          collector_cells_upper=collector, charged_collector_nodes=nodes)
    return dict(schema="opentallas.qc.landing_cell_estimates.v1",
                qualification="CONSERVATIVE LOGICAL PLAN ESTIMATE; NOT MAPPED OR SIGNED",
                basis=__doc__, primitive_weights=primitive_weights,
                ring_cells_upper_by_width=rings, cells_per_type=rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply-plan", action="store_true",
                        help="embed the estimate in this owned one-event candidate")
    args = parser.parse_args()
    out = HERE / "landing_cells_est.json"
    result = generate()
    out.write_text(json.dumps(result, indent=2) + "\n")
    if args.apply_plan:
        path = ROOT / "physical/die_plan/qwen_compute/candidate_oneqc0733.json"
        plan = json.loads(path.read_text())
        for name, row in result["cells_per_type"].items():
            plan["partition_types"][name]["cells"] = row["cells"]
        path.write_text(json.dumps(plan, indent=1) + "\n")
    print(f"{len(result['cells_per_type'])} complete type estimates -> {out}")
