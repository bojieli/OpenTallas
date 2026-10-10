#!/usr/bin/env python3
"""Require all four source-identical terminal campaign predicates before V36 adoption."""
import argparse
import hashlib
import json
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("records", type=Path, nargs=4)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    cases = {json.loads(f.read_text())["campaign"]: (f, json.loads(f.read_text())) for f in a.records}
    assert set(cases) == {14, 15, 19, 20}, "Exactly the four original campaigns are required"
    for campaign, (_, r) in cases.items():
        assert r["gate_passed"] and r["source_receipt_matches"] and r["campaign_vehicle_matches"]
        assert r["role"] == ("positive_exactness" if campaign in (14, 19) else "negative_protocol_control")
        if campaign in (14, 19):
            assert r["metrics"]["overlapping_job_pairs"] > 0, "Positive must exercise the wavefront"
    assert len({r["source"]["core_sha256"] for _, r in cases.values()}) == 1
    assert len({r["source"]["tool_sha256"] for _, r in cases.values()}) == 1
    assert len({r["collector_sha256"] for _, r in cases.values()}) == 1
    for positive, negative in ((14, 15), (19, 20)):
        def fixture(r):
            return {Path(f["path"]).name: f["sha256"] for f in r["artifacts"]
                    if f["path"].endswith(".hex") or Path(f["path"]).name == "prepare_stage2_deep.json"}
        assert fixture(cases[positive][1]) == fixture(cases[negative][1]), "Pair must share exact fixture"
    result = dict(schema="opentallas.mtp_ring_dyn_four_campaign_gate.v1", passed=True,
                  decision="V36 conditional default-enable gate satisfied on the original ring8 fixture",
                  source=cases[14][1]["source"],
                  cases=[dict(campaign=c, path=str(f), sha256=hashlib.sha256(f.read_bytes()).hexdigest(),
                              total_cycles=r["metrics"]["total_cycles"], role=r["role"])
                         for c, (f, r) in sorted(cases.items())],
                  native_production_exactness_qualified=False,
                  sequencer_context_ss_ff_qualified=False,
                  latency="Five extra state bits per slot; zero added sequencer cycles. Invalid old numerical run is not a speed baseline.")
    with a.output.open("x") as f:
        json.dump(result, f, indent=2)
        f.write("\n")
    print("All four campaign predicates PASS; native and contextual physical gates remain separate")


if __name__ == "__main__":
    main()
