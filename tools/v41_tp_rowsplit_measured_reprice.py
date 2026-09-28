#!/usr/bin/env python3
"""Reprice batch-one V4.1 AR TP row split with adopted-width gather RTL tails.

Only the new activation and output gathers receive measured stage tails. The
other collective classes retain their existing bench terms. The six-position
MTP pass needs its own payload-matched bench. The result stays a conditional
model, since full-shape tokens and die route are not closed.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import arch_lanes_v41 as AL  # noqa: E402
import collective_exposure as CX  # noqa: E402
import decode_critical_path as DC  # noqa: E402
from v41_tp_exact_reprice import v41_moe_rowsplit  # noqa: E402

BENCH = ROOT / "results/rtl/v41_tp_rowsplit_die_collectives.json"
DEPTH_BENCH = ROOT / "results/rtl/v41_collective_depth_campaign.json"
SENSITIVITY = ROOT / "results/arch/v41_tp_exact_reprice.json"
INDEX_READER = ROOT / "results/rtl/hdc_v41x_idx_shard_reader_pc.json"
OUT = ROOT / "results/arch/v41_tp_rowsplit_measured_reprice.json"


def measured_gather_mutation(tails: dict[str, int]):
    names = {".ffn.act_allgather": "act", ".ffn.y_allgather": "y"}

    def f(graph, spec):
        for node_name, node in graph.nodes.items():
            tag = next((tag for suffix, tag in names.items() if node_name.endswith(suffix)), None)
            if tag is None:
                continue
            assert node["kind"] == "collective" and node["op"] == "all_gather"
            # The bench measures last result minus the ideal producer's last
            # word, including DMA producer delay, credits, engine and link.
            node["stream"] = False
            node["ctrl"] = 0.0
            node["issue"] = tails[tag] / AL.A._env()["clock"]
            node["depth"] = 0.0
            node["issue_cat"] = "collective_latency"
            node["depth_cat"] = "collective_latency"
            node["_measured_rowsplit_tail"] = tag
    return f


def build():
    bench = json.loads(BENCH.read_text())
    depth_bench = json.loads(DEPTH_BENCH.read_text())
    sensitivity = json.loads(SENSITIVITY.read_text())
    index_reader = json.loads(INDEX_READER.read_text())
    assert index_reader["schema"] == "opentallas.hdc-v41x-idx-shard-reader-pc.v1"
    assert index_reader["status"] == "pass_exact_below_bandwidth_target"
    scan = index_reader["timed_1040_key_scan"]
    assert scan["sectors"] == 2210 and scan["keys"] == 1040
    assert scan["sectors_per_cycle"] < index_reader["target_sectors_per_cycle"]
    assert bench["schema"] == "v41_tp_rowsplit_die_collectives_v1"
    contract = bench["die_contract"]
    for key, value in dict(CL_LANES=16, flit_bytes=64, CL_DEPTH=16,
                           DMA_VM_words_per_cycle=1, DMA_skid_words=2,
                           RELAY=1, ADD_LAT=3, PAIRWISE=1, GW=1).items():
        assert contract[key] == value, key
    assert depth_bench["schema"] == "v41_collective_depth_campaign_v1"
    selected = depth_bench["contract"]
    assert selected["selected_full_shape_CL_DEPTH"] == 128
    assert selected["PAIRWISE"] == 1 and selected["QTX"] == 2 and selected["PUSHW"] == 1
    assert selected["CL_LANES"] == 16 and selected["FLIT_BYTES"] == 64
    for record in (bench, depth_bench, sensitivity):
        for path, digest in record["source_sha256"].items():
            assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest, path
    tails = {name: depth_bench["summary"][name]["selected_tail_cycles"] for name in ("act", "y")}
    for name in ("act", "y"):
        assert depth_bench["summary"][name]["old_tail_cycles"] == bench["summary"][name]["measured_tail_cycles"]
        assert tails[name] >= depth_bench["summary"][name]["output_port_minimum_cycles"]
    lane = json.loads((ROOT / "results/arch/v41_lanes.json").read_text())
    point = AL.design_point()
    lev = lane["collective_exposure"]["levers"]
    common = point["muts"] + [point["ml"], CX.mutation(lev["terms"]),
                              CX.consumer_mutation(tuple(lev["consumers"]))]
    baseline = sensitivity["points"]["design_point"]
    previous = DC.v41_moe
    DC.v41_moe = v41_moe_rowsplit
    try:
        points = {}
        for context in (1_048_576, 200_000):
            unmeasured = AL.LX.evaluate(point["sp"], context, common,
                                        hz=point["hz"], draft_extra_s=point["draft_extra_s"])
            priced = AL.LX.evaluate(point["sp"], context, common + [measured_gather_mutation(tails)],
                                    hz=point["hz"], draft_extra_s=point["draft_extra_s"])
            assert abs(unmeasured["ar"] - baseline[str(context)]["ar"]["rowsplit"]) < 1e-8
            points[str(context)] = dict(
                ar=dict(old_ksplit_model=baseline[str(context)]["ar"]["baseline"],
                        row_split_old_tail=unmeasured["ar"],
                        row_split_measured_gathers=priced["ar"],
                        measured_vs_old_tail_fraction=priced["ar"] / unmeasured["ar"] - 1),
                mtp=dict(old_ksplit_model=baseline[str(context)]["mtp"]["baseline"],
                         row_split_old_tail=unmeasured["mtp"],
                         one_position_tail_transfer_sensitivity=priced["mtp"],
                         status="uncalibrated: six-position payload-matched collective RTL bench required"))
    finally:
        DC.v41_moe = previous
    sources = ("tools/v41_tp_rowsplit_measured_reprice.py", "tools/v41_tp_exact_reprice.py",
               "tools/arch_lanes_v41.py", "tools/arch_latency_ladder_v41.py",
               "tools/decode_critical_path.py", "tools/collective_exposure.py",
               "results/arch/v41_lanes.json", "results/arch/v41_tp_exact_reprice.json",
               "results/rtl/v41_tp_rowsplit_die_collectives.json",
               "results/rtl/v41_collective_depth_campaign.json",
               "results/rtl/hdc_v41x_idx_shard_reader_pc.json")
    pins = {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in sources}
    return dict(schema="v41_tp_rowsplit_measured_reprice_v1", source_sha256=pins,
                scope="batch-one per-user AR model with selected 128-entry receive FIFO gather stage RTL tails; MTP is an uncalibrated sensitivity; not full-shape chip throughput",
                selected_collective_source="results/rtl/v41_collective_depth_campaign.json",
                measured_tail_cycles=tails, points=points,
                index_scan_gate=dict(source="results/rtl/hdc_v41x_idx_shard_reader_pc.json",
                                     scope="exact tagged per-PC reader prototype; not the integrated full-token scan",
                                     sectors=scan["sectors"], cycles=scan["cycles"],
                                     measured_sectors_per_cycle=scan["sectors_per_cycle"],
                                     required_sectors_per_cycle=index_reader["target_sectors_per_cycle"],
                                     attained_fraction=index_reader["fraction_of_target"],
                                     throughput_claim_valid=False),
                limits=["stage bench has producer timing stubs and behavioural UCIe/T1, not a routed die",
                        "one 64-byte VM write/cycle imposes 1064/320-cycle activation/output minima; selected depth-128 exact tails are 1220/476 cycles, so the old 219/167-cycle model exposures remain physically unattainable at this port width",
                        "full-shape TP layer and die exact-token simulation is pending",
                        "local per-expert BF16 rounding and ordered sum are not separately timed",
                        "other collective tails are inherited from prior campaigns",
                        "MTP verifies six positions and needs its own 1596/480-flit gather bench",
                        "tagged sharded index reader is exact but delivers 2.154 of the modeled 125 sectors/cycle; parallel scan scheduler, exact multiuser isolation and route remain required for the 866-user headline"])


def main():
    rec = build()
    OUT.write_text(json.dumps(rec, indent=2, sort_keys=True) + "\n")
    print(json.dumps({c: dict(ar=round(p["ar"]["row_split_measured_gathers"]),
                              mtp_sensitivity=round(p["mtp"]["one_position_tail_transfer_sensitivity"]))
                      for c, p in rec["points"].items()}))


if __name__ == "__main__":
    main()
