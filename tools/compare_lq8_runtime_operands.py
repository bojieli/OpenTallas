#!/usr/bin/env python3
"""Compare matched numerical runs with serialized versus overlapped SRAM refill."""

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--overlap",
        type=Path,
        default=ROOT / "build/runtime_lq8_operands/evidence.json",
    )
    parser.add_argument(
        "--serial", type=Path, default=ROOT / "build/runtime_lq8_serial/evidence.json"
    )
    parser.add_argument(
        "--output", type=Path, default=ROOT / "results/rtl/a3_lq8_runtime_operands.json"
    )
    parser.add_argument(
        "--comparison", choices=["refill", "auxiliary", "capacity"], default="refill"
    )
    args = parser.parse_args()
    overlap, serial = [json.loads(p.read_text()) for p in (args.overlap, args.serial)]
    assert overlap["status"] == serial["status"] == "pass"
    if args.comparison == "refill":
        assert not overlap["serial_refill"] and serial["serial_refill"]
        assert overlap.get("future_auxiliary", False) == serial.get(
            "future_auxiliary", False
        )
    elif args.comparison == "auxiliary":
        assert overlap["serial_refill"] == serial["serial_refill"]
        assert overlap["future_auxiliary"] and not serial["future_auxiliary"]
    else:
        assert overlap["serial_refill"] == serial["serial_refill"]
        assert overlap["future_auxiliary"] and serial["future_auxiliary"]
        assert overlap["auxiliary_depth"] < serial["auxiliary_depth"]
    assert overlap["sources"] == serial["sources"], "different source snapshots"
    for run in (overlap, serial):
        for path, expected in {**run["sources"], **run["artifacts"]}.items():
            assert digest(ROOT / path) == expected, f"stale artifact: {path}"

    def images(run):
        return {
            Path(p).name: h
            for p, h in run["artifacts"].items()
            if p.endswith(".hex") or p.endswith("/manifest.json")
        }

    assert images(overlap) == images(serial), "different input/expected images"

    def verdict(run):
        return [m for m in run["markers"] if m.startswith(("PASS:", "checks="))]

    assert verdict(overlap) == verdict(serial), "different numerical verdicts"
    assert len(overlap["operations"]) == len(serial["operations"]) > 0
    manifest_path = next(
        p for p in overlap["artifacts"] if p.endswith("/manifest.json")
    )
    manifest = json.loads((ROOT / manifest_path).read_text())["cases"]
    assert len(manifest) == len(overlap["operations"])
    cases = []
    for i, (o, s) in enumerate(zip(overlap["operations"], serial["operations"])):
        fault = manifest[i]["expected"]["block"]["error_code"] != 0
        if args.comparison == "refill" or not fault:
            assert o["issues"] == s["issues"], f"case {i}: different issued work"
        cases.append(
            {
                "case": i,
                "issues": o["issues"],
                "baseline_issues": s["issues"],
                "expected_fault": fault,
                "overlap_cycles": o["cycles"],
                "serial_cycles": s["cycles"],
                "cycles_saved": s["cycles"] - o["cycles"],
            }
        )
    before = serial["total_operation_cycles"]
    after = overlap["total_operation_cycles"]
    result = {
        "schema": "opentallas.lq8_runtime_overlap_comparison.v1",
        "status": "pass",
        "comparison": args.comparison,
        "optimized_queue_entry_bits": 320 if overlap.get("future_auxiliary") else 0,
        "optimized_queue_storage_bits": 320 * overlap.get("auxiliary_depth", 0),
        "baseline_queue_storage_bits": 320 * serial.get("auxiliary_depth", 0),
        "scope": "Matched quick corpus. Two weight SRAM banks, 32-word tiles, four-word FIFO. The external auxiliary producer is behavioral with one outstanding request and address-dependent latency. Auxiliary comparison adds an independent RTL cursor and bounded response queue; not bounded activation SRAM, production scheduling, G2 integration, multi-row weight reuse, or routed performance.",
        "nonfault_baseline_cycles": sum(
            c["serial_cycles"] for c in cases if not c["expected_fault"]
        ),
        "nonfault_optimized_cycles": sum(
            c["overlap_cycles"] for c in cases if not c["expected_fault"]
        ),
        "extra_issued_bundles": sum(c["issues"] - c["baseline_issues"] for c in cases),
        "serial_cycles": before,
        "overlap_cycles": after,
        "speedup": before / after,
        "latency_reduction_percent": 100 * (before - after) / before,
        "cases": cases,
        "runs": {"overlap": overlap, "serial": serial},
        "comparison_tool_sha256": digest(Path(__file__)),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(
        f"Matched {len(cases)} cases: {before} -> {after} cycles; {before / after:.4f}x; {100 * (before - after) / before:.2f}% latency reduction"
    )


if __name__ == "__main__":
    main()
