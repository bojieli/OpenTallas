#!/usr/bin/env python3
"""Summarize the routed one-PC K request slice's extracted STA probes."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
from pathlib import Path


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--physical", type=Path, required=True)
    parser.add_argument("--probe", type=Path, required=True)
    parser.add_argument("--odb-gz", type=Path, required=True)
    parser.add_argument("--spef-gz", type=Path, required=True)
    parser.add_argument("--tcl", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    physical = json.loads(args.physical.read_text())
    assert physical["status"] == "pass"
    odb_hash = sha256(gzip.decompress(args.odb_gz.read_bytes()))
    assert odb_hash == physical["place_and_route"]["artifacts"]["6_final.odb"]["sha256"]
    spef_hash = sha256(gzip.decompress(args.spef_gz.read_bytes()))
    report = args.probe.read_text()
    timing = {}
    for section in report.split("=== ")[1:]:
        label = section.split(" ===", 1)[0]
        start = re.search(r"Startpoint: ([^\n]+)", section)
        end = re.search(r"Endpoint: ([^\n]+)", section)
        arrival = re.search(r"([0-9.]+)\s+data arrival time", section)
        slack = re.search(r"([0-9.]+)\s+slack \(MET\)", section)
        if not all((start, end, arrival, slack)):
            raise ValueError(f"incomplete routed timing path: {label}")
        timing[label] = {
            "startpoint": start.group(1), "endpoint": end.group(1),
            "arrival_ps": float(arrival.group(1)), "slack_ps": float(slack.group(1)),
        }
    if len(timing) != 23:
        raise ValueError(f"expected 23 input/output path groups, got {len(timing)}")
    record = {
        "schema": 1,
        "status": "pass",
        "scope": "routed one-PC request-only slice; extracted STA paths, not a sequential Liberty macro view",
        "corner": "ASAP7 TT predictive", "clock_period_ps": 920,
        "io_delay_ps": 184,
        "source_physical_record": str(args.physical),
        "source_physical_commit": physical["git"]["commit"],
        "source_routed_odb_sha256": odb_hash,
        "source_routed_spef_sha256": spef_hash,
        "probe_tcl_sha256": sha256(args.tcl.read_bytes()),
        "probe_log_sha256": sha256(args.probe.read_bytes()),
        "groups": timing,
        "request_trunk_budget_ps": round(920 - 184 - timing["state_to_h_wstrb"]["arrival_ps"], 4),
        "limits": [
            "The SPEF captures the local routed slice only; group response and cross-PC trunks are outside it.",
            "A complete characterized sequential Liberty model and powered four-PC route remain open.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    print(f"{args.output}: {len(timing)} extracted path groups")


if __name__ == "__main__":
    main()
