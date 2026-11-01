#!/usr/bin/env python3
"""Retain original state correspondence after private face outputs are copied.

Only proof snapshots gain wire names. Every alias is itself an equivalence
point; none is assumed. Unkept aliases survive write_verilog for its round-trip
proof, and normal synthesis may remove them. Changed/retimed state is skipped.
"""
import argparse
import hashlib
import json
from pathlib import Path

FF = {"$dff", "$adff", "$dffe", "$adffe", "$sdff", "$sdffe", "$sdffce",
      "$aldff", "$aldffe", "$dffsr", "$dffsre", "$_DFF_P_", "$_DFF_N_"}


def add_aliases(snapshots, top):
    modules = [snapshot["modules"][top] for snapshot in snapshots]
    count = bits = 0
    for name, cell in modules[0]["cells"].items():
        if cell["type"] not in FF:
            continue
        q = cell["connections"]["Q"]
        if any(name not in module["cells"] or
               module["cells"][name]["type"] != cell["type"] or
               module["cells"][name]["connections"].get("Q") != q
               for module in modules[1:]):
            continue
        alias = "hrproof_state_" + hashlib.sha256(name.encode()).hexdigest()[:24]
        for module in modules:
            if alias in module["netnames"] and module["netnames"][alias]["bits"] != q:
                raise ValueError("proof state alias collision: " + alias)
            # No keep: an alias must not become an extra physical face load.
            module["netnames"][alias] = {"hide_name": 0, "bits": list(q), "attributes": {}}
        count += 1
        bits += len(q)
    return {"original_ff_aliases": count, "state_bits": bits, "assumptions": 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshots", nargs="+", type=Path)
    parser.add_argument("--top", required=True)
    args = parser.parse_args()
    snapshots = [json.loads(path.read_text()) for path in args.snapshots]
    report = add_aliases(snapshots, args.top)
    for path, snapshot in zip(args.snapshots, snapshots):
        path.write_text(json.dumps(snapshot))
    print("HR_PROOF_STATE_ALIASES " + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
