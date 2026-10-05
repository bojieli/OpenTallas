#!/usr/bin/env python3
"""Conservative resource witness for the exact 64-byte V4.1 gather subset.

Serializing each producer plus measured tail removes overlap between the two
gathers. This proves a bounded component reservation, not a mapped layer or
an achieved clock. Its unused reservations intentionally expose utilization
lost to a conservative schedule.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import v41_finite_schedule as FS

ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / "results/rtl/v41_collective_depth_campaign.json"
OUT = ROOT / "results/arch/v41_finite_schedule_subset.json"


def build():
    bench = json.loads(BENCH.read_text())
    assert bench["contract"]["CL_LANES"] == 16
    assert bench["contract"]["FLIT_BYTES"] == 64
    assert bench["contract"]["GW"] == 1
    assert bench["contract"]["selected_full_shape_CL_DEPTH"] == 128
    assert bench["contract"]["blocked_COLL_v1"]
    resources = {
        "dma_vm_read": dict(physical_id="vm_port_b_read", capacity_per_cycle=1, unit="64B_word", classes=["vm_read"]),
        "dma_vm_write": dict(physical_id="vm_port_b_write", capacity_per_cycle=1, unit="64B_word", classes=["vm_write"]),
        "collective_link": dict(physical_id="adopted_t1_link", capacity_per_cycle=1, unit="64B_word", classes=["link"]),
        "px_engine": dict(physical_id="die_px_engine", capacity_per_cycle=1, unit="engine_cycle", classes=["collective_engine"]),
    }
    operations = []
    t = 0
    for case in ("act", "y"):
        row = bench["summary"][case]
        count = row["input_words_per_die"]
        tail = row["selected_tail_cycles"]
        duration = count + tail
        end = t + duration
        operations.append({
            "id": f"L0.ffn.{case}_gather", "kind": "verified_collective_stage",
            "instruction_id": f"L0.ffn.{case}_gather", "die": 0, "cluster": 0,
            "start_cycle": t, "end_cycle": end,
            "ready_cycle": t,
            "deps": [] if not operations else [operations[-1]["id"]],
            "tensor_fragment_ids": [],
            "demands": dict(vm_read=count, vm_write=4 * count,
                            link=3 * count, collective_engine=duration),
            "reservations": [
                dict(resource="dma_vm_read", **{"class": "vm_read"}, start_cycle=t,
                     end_cycle=t + count, rate=1),
                dict(resource="dma_vm_write", **{"class": "vm_write"}, start_cycle=t,
                     end_cycle=end, rate=1),
                dict(resource="collective_link", **{"class": "link"}, start_cycle=t,
                     end_cycle=end, rate=1),
                dict(resource="px_engine", **{"class": "collective_engine"}, start_cycle=t,
                     end_cycle=end, rate=1),
            ],
            "exact_stage_record": dict(path="results/rtl/v41_collective_depth_campaign.json",
                                       case=case, input_words=count,
                                       output_words=row["output_words_per_die"], tail_cycles=tail),
        })
        t = end
    source_paths = ("tools/v41_finite_schedule.py", "tools/v41_finite_schedule_subset.py",
                    "results/rtl/v41_collective_depth_campaign.json")
    pins = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in source_paths}
    return {
        "schema": FS.SCHEMA, "scope": "operator_subset", "source_sha256": pins,
        "contract": dict(instruction_ids=[o["instruction_id"] for o in operations],
                         tensor_specs={}, physical_flit_bytes=64,
                         note="two exact gather components serialized; no full layer, shared HBM, ME or clock claim"),
        "resources": resources, "tensor_fragments": [], "operations": operations, "queues": {},
        "provenance_boundary": "The depth128 exact RTL bench validates each blocked gather and its internal queues. This witness reserves external ports for the full intervals and serializes the two stages; it does not replay their internal flit timestamps.",
    }


def main():
    witness = build()
    verdict = FS.audit(witness)
    assert verdict["status"] == "pass_resource_witness", verdict["errors"]
    OUT.write_text(json.dumps(witness, indent=2, sort_keys=True) + "\n")
    print(verdict)


if __name__ == "__main__":
    main()
