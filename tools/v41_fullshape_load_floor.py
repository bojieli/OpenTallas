#!/usr/bin/env python3
"""Conditional V4.1 full-shape activation-load floor on the batch-one DAG.

The shipped ShapeBuilder is a timing-only emitter. Its current wo_a splitj
descriptor is invalid for the full ACC buffer, so this prices the proposed
two no-splitj local o-group operations, not an executable token program.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import arch_lanes_v41 as AL  # noqa: E402
import collective_exposure as CX  # noqa: E402
import decode_critical_path as DC  # noqa: E402
import hdc_replay_v41 as R  # noqa: E402
from v41_tp_exact_reprice import v41_moe_rowsplit  # noqa: E402
from v41_tp_rowsplit_measured_reprice import measured_gather_mutation  # noqa: E402

OUT = ROOT / "results/arch/v41_fullshape_load_floor.json"


def wo_a_load_floor(cycles: int):
    def apply(graph, _spec):
        count = 0
        for name, node in graph.nodes.items():
            if name.endswith(".attn.wo_a"):
                assert node["kind"] == "matvec"
                # Model the activation copy as a serial pre-compute floor.
                # Retain the model's depth/control/wire charges. The original
                # sweep share is sub-2048 cycles at the design point.
                node["stream"] = False
                node["issue"] = max(node["issue"], cycles / AL.A._env()["clock"])
                node["issue_cat"] = "activation_load_floor"
                count += 1
        assert count == 40, count
    return apply


def build():
    program = R.build(R.SHIPPED, layers=[0], embed=False, head=False)
    wo = [f for f in program if f.get("me_k") == 4096 and f.get("me_xjs") == 2048]
    he = [f for f in program if f.get("he_k") == 2560]
    assert len(wo) == 1 and len(he) == 2
    assert all(f["he_nout"] == 24 for f in he)
    assert wo[0]["me_nout"] == 2048 and wo[0]["me_tiles"] == 4
    # Current splitj has 8 sub-operations; sj=7 adds 7*2048 to an
    # 8192-element ACC buffer. The replacement emitter is still pending.
    assert 7 * wo[0]["me_xjs"] >= 8192
    proposed_wo_load = 2 * (4096 // 4)
    he_load = 2 * 2560

    point = AL.design_point()
    lanes = json.loads((ROOT / "results/arch/v41_lanes.json").read_text())
    lev = lanes["collective_exposure"]["levers"]
    common = point["muts"] + [point["ml"], CX.mutation(lev["terms"]),
                              CX.consumer_mutation(tuple(lev["consumers"]))]
    depth = json.loads((ROOT / "results/rtl/v41_collective_depth_campaign.json").read_text())
    assert depth["contract"]["selected_full_shape_CL_DEPTH"] == 128
    gw1 = {k: depth["summary"][k]["selected_tail_cycles"] for k in ("act", "y")}
    assert gw1 == {"act": 1220, "y": 476}
    tails = {"gw1_depth128_exact_stage": gw1}
    old_moe = DC.v41_moe
    DC.v41_moe = v41_moe_rowsplit
    try:
        points = {}
        read_width_sensitivity = {}
        for ctx in (1_048_576, 200_000):
            points[str(ctx)] = {}
            for label, pair in tails.items():
                baseline = AL.LX.evaluate(point["sp"], ctx,
                                          common + [measured_gather_mutation(pair)],
                                          hz=point["hz"], draft_extra_s=point["draft_extra_s"])
                priced = AL.LX.evaluate(point["sp"], ctx,
                                        common + [measured_gather_mutation(pair),
                                                  wo_a_load_floor(proposed_wo_load)],
                                        hz=point["hz"], draft_extra_s=point["draft_extra_s"])
                points[str(ctx)][label] = {
                    "before_wo_load_ar_tok_s": baseline["ar"],
                    "proposed_wo_load_ar_tok_s": priced["ar"],
                    "proposed_wo_load_critical_path_us": priced["T_us"],
                    "status": "conditional model sensitivity, not full-shape RTL throughput",
                }
            read_width_sensitivity[str(ctx)] = {}
            for elements_per_cycle in (4, 8, 16):
                cycles = 2 * (4096 // elements_per_cycle)
                scenario = AL.LX.evaluate(point["sp"], ctx,
                                          common + [measured_gather_mutation(gw1),
                                                    wo_a_load_floor(cycles)],
                                          hz=point["hz"], draft_extra_s=point["draft_extra_s"])
                read_width_sensitivity[str(ctx)][str(elements_per_cycle)] = {
                    "activation_load_cycles_per_layer": cycles,
                    "conditional_ar_tok_s": scenario["ar"],
                    "gate": "banked ME activation read, corrected two-op emitter, exact full-token gate, physical closure"
                            if elements_per_cycle > 4 else "current G4 adapter width plus corrected emitter and full-token gate",
                }
    finally:
        DC.v41_moe = old_moe
    source_paths = ("tools/v41_fullshape_load_floor.py", "tools/hdc_replay_v41.py",
                    "tools/decode_critical_path.py", "tools/arch_lanes_v41.py",
                    "tools/v41_tp_exact_reprice.py", "tools/v41_tp_rowsplit_measured_reprice.py",
                    "rtl/hdc/v41x/ot_hdc_v41x_he_adapt.sv",
                    "rtl/hdc/v41x/ot_hdc_v41x_me_adapt.sv",
                    "rtl/hdc/v41x/ot_hdc_core_v41x.sv",
                    "results/rtl/v41_collective_depth_campaign.json",
                    "results/arch/v41_lanes.json")
    pins = {str(p): hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in source_paths}
    return {
        "schema": "v41_fullshape_load_floor_v1",
        "source_sha256": pins,
        "contract": {
            "fullshape_layers": 40, "tp_dies": 4,
            "current_wo_a_descriptor": "invalid: splitj=8, xjs=2048 exceeds 8192-element ACC",
            "proposed_wo_a_ops_per_layer": 2,
            "proposed_wo_a_k_per_op": 4096,
            "me_activation_read_elements_per_cycle": 4,
            "proposed_wo_a_load_cycles_per_layer": proposed_wo_load,
            "he_ops_per_layer": 2, "he_k_chunks_per_op": 2560,
            "he_load_cycles_per_layer_if_unhidden": he_load,
            "batch_one_dependency": "each next token follows terminal logits; all 40 wo_a nodes lie on the token DAG path",
        },
        "points": points,
        "me_read_width_sensitivity": read_width_sensitivity,
        "limits": [
            "The corrected two-operation wo_a program and exact image/token gate have not passed.",
            "The wo_a mutation floors model issue time at 2048 cycles and retains its depth/control/wire; it does not establish a cycle-exact RTL schedule.",
            "HE's two 2560-cycle LOADs may overlap other operators; the model prices no HE-load exposure yet.",
            "Current HE KCMAX=128 and ME KMAX=512 defaults do not hold full-shape K=2560/4096; width/depth RTL gate is pending.",
            "Current HCP HHW=8 differs from the design-point HW256/2048-lane geometry; a repacked image, exact bench and route are required.",
            "MTP has no corrected six-position emitter or activation-load timing; no MTP result is reported.",
            "G8/G16 read-width sensitivities require additional VM read banks/ports and corresponding area, power and route; they are not measured RTL.",
            "GW4 is excluded until its exact stage record is integrated and source-pinned here, and four-word VM/CDMA and route close.",
            "Sharded index delivery has not met the model's effective HBM bandwidth; no row is a delivered token rate.",
        ],
    }


def main():
    result = build()
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    for ctx, rows in result["points"].items():
        for name, row in rows.items():
            print(ctx, name, round(row["before_wo_load_ar_tok_s"]),
                  round(row["proposed_wo_load_ar_tok_s"]))


if __name__ == "__main__":
    main()
