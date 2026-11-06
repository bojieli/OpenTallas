#!/usr/bin/env python3
"""Produce a private PV core-branch candidate; never edit the input plan."""
import argparse
import copy
import hashlib
import json
from pathlib import Path


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def apply(plan, event, variant):
    if variant not in ("A", "B"):
        raise ValueError("variant must be A or B")
    name = event["type"]
    before = plan["partition_types"][name]
    if digest(before) != event["base_type_sha256"]:
        raise ValueError("PV type differs from reviewed candidate base")
    result = copy.deepcopy(plan)
    clock = result["partition_types"][name]["clock"]
    if clock["core_taps"] != "internal":
        raise ValueError("reviewed source core mode is not internal")
    table = {x["name"]: x for x in clock["taps"] if x.get("kind") == "core"}
    entries = event["core_entries"]
    if len(table) != 20 or set(table) != {x["tap"] for x in entries}:
        raise ValueError("core clock inventory differs")
    for entry in entries:
        row = table[entry["tap"]]
        if (row["xy"] != entry["old_xy"] or
            row["insertion_ps"] != entry["mean_tt_ps"] or
            row["insertion_ff_ps"] != entry["mean_ff_ps"]):
            raise ValueError("core placement/clock means differ")
        row["xy"] = entry["entry_xy"]
    clock["core_taps"] = "early"
    if variant == "B":
        clock["tap_chain_affinity"] = event["affinity"]
    # Restoring the exact declared changes must reproduce the entire input plan.
    restored = copy.deepcopy(result)
    check = restored["partition_types"][name]["clock"]
    check["core_taps"] = "internal"
    if variant == "B":
        del check["tap_chain_affinity"]
    for row in check["taps"]:
        if row.get("kind") == "core":
            row["xy"] = next(x["old_xy"] for x in entries if x["tap"] == row["name"])
    if restored != plan:
        raise ValueError("candidate changed independent plan fields")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan")
    parser.add_argument("--variant", choices=["A", "B"], required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    source, output = Path(args.plan), Path(args.out)
    if output.exists() or source.resolve() == output.resolve():
        raise ValueError("output must be fresh and distinct")
    event = json.loads(Path(__file__).with_name("candidate.json").read_text())
    result = apply(json.loads(source.read_text()), event, args.variant)
    output.write_text(json.dumps(result, indent=1) + "\n")
    print(json.dumps(dict(type=event["type"], variant=args.variant,
                         core_ports_added=20, added_data_cycles=0,
                         native_context_regeneration_required=True, qualified=False)))


if __name__ == "__main__":
    main()
