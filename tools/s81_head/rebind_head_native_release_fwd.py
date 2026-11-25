#!/usr/bin/env python3
"""Compose a new HEAD plan receipt for an unchanged, qualified native reset contract."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys


def json_load(path):
    return json.loads(path.read_text())


def hexdigest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def serdes_parts(plan):
    return {part["name"]: part for part in plan["partitions"] if part["type"] == "hd_serdes"}


def fwd_only_delta(a, b, allow_physical=False):
    """FWDTAP-1 serdes requal: the hd_serdes type may differ ONLY by the reach_rules fix_fwd form on forwarded clock
    exports (pins[i].source_clock_port of an out clock pin fclk_out_*, and landing_contract.forwarded_clock_only_inputs
    -> true).  u_phy content, hard cores and every other key must be identical; qualify() then re-checks the receipt."""
    import copy
    a, b = copy.deepcopy(a), copy.deepcopy(b)
    # HEAD-WEST w5 (COORD 05:15): realize_internal_stations only adds the planned FIRM u_ist_ stations to the gen wrapper;
    # u_phy content, hard cores and the native reset production sources are untouched (qualify() re-checks them below).
    for k in ("realize_internal_stations", "note"):
        if a.get(k) != b.get(k):
            print("REALIZE_DELTA", k)
        a.pop(k, None); b.pop(k, None)
    la, lb = a.get("clock", {}).get("landing_contract", {}), b.get("clock", {}).get("landing_contract", {})
    if lb.get("forwarded_clock_only_inputs") not in (None, True) or la.get("forwarded_clock_only_inputs") not in (None, True):
        raise ValueError("HEAD native reset type changed: forwarded_clock_only_inputs")
    la.pop("forwarded_clock_only_inputs", None); lb.pop("forwarded_clock_only_inputs", None)
    pa, pb = la.get("pins", []), lb.get("pins", [])
    if len(pa) != len(pb):
        raise ValueError("HEAD native reset type changed: pin count")
    moved = []
    for x, y in zip(pa, pb):
        if x.get("source_clock_port") != y.get("source_clock_port"):
            if not (x.get("name") == y.get("name") and str(x.get("name", "")).startswith("fclk_out_")
                    and x.get("dir") == "out" and x.get("kind") == "clock"):
                raise ValueError("HEAD native reset type changed: source port of " + str(x.get("name")))
            moved.append((x["name"], x.get("source_clock_port"), y.get("source_clock_port")))
            x.pop("source_clock_port", None); y.pop("source_clock_port", None)
    # HEAD-SERDES-REFLOOR: physical-only hd_serdes deltas (pads[].sites_um/layer, clock.reserved_sites_um) are not part of the native
    # reset contract.  Default: reported and refused.  --allow-serdes-physical: reported, then ignored for the comparison.
    phys = []
    for x in (a, b):
        for pd in x.get("pads", []):
            phys.append(("pad:" + str(pd.get("name")), pd.pop("sites_um", None), pd.pop("layer", None)))
        phys.append(("reserved_sites_um", x.get("clock", {}).pop("reserved_sites_um", None), None))
        phys.append(("place_regions", x.pop("place_regions", None), None))
        phys.append(("hard_core_origins", [hc.pop("origin_um", None) for hc in x.get("hard_cores", [])], None))
    half = len(phys) // 2
    changed = sorted({p[0] for p, q in zip(phys[:half], phys[half:]) if p != q})
    if changed:
        print("PHYSICAL_DELTA", changed)
        if not allow_physical:
            raise ValueError("HEAD native reset type changed: physical-only delta " + ",".join(changed) + " (use --allow-serdes-physical)")
    if a != b:
        raise ValueError("HEAD native reset type changed")
    print("FWD_ONLY_DELTA", moved)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("old_plan", "new_plan", "old_receipt", "out", "tools"):
        parser.add_argument(name, type=Path)
    parser.add_argument("--allow-serdes-physical", action="store_true", help="accept hd_serdes pad-site / reserved-site deltas (report-only otherwise)")
    args = parser.parse_args()
    sys.path.insert(0, str(args.tools))
    import cores
    import head_native_release
    import reset_tree
    import schema

    old, new = json_load(args.old_plan), json_load(args.new_plan)
    receipt = json_load(args.old_receipt)
    fwd_only_delta(old["partition_types"]["hd_serdes"], new["partition_types"]["hd_serdes"], args.allow_serdes_physical)
    if serdes_parts(old) != serdes_parts(new):
        raise ValueError("HEAD native reset instance bindings changed")
    old_plan = schema.Plan(old, args.old_plan)
    head_native_release.qualify(old_plan, reset_tree.wf_plan(old_plan), args.old_receipt)
    args.out.mkdir(parents=True, exist_ok=False)
    old_root = args.old_receipt.parent.resolve()
    files = {}
    for name, sha in receipt["files"].items():
        old_file = (old_root / name).resolve()
        if old_file.is_relative_to(old_root):
            copied = args.out / name
            copied.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(old_file, copied)
            files[name] = sha
        else:
            files[os.path.relpath(old_file, args.out)] = sha
    sources = receipt["proof"]["production_sources"]
    if any(hexdigest(cores.resolve(name)) != sha for name, sha in sources.items()):
        raise ValueError("HEAD native reset production source differs from measured proof")
    receipt["files"] = files
    receipt["plan_sha256"] = head_native_release.digest(new)
    destination = args.out / "candidate_receipt.json"
    destination.write_text(json.dumps(receipt, indent=1) + "\n")
    new_plan = schema.Plan(new, args.new_plan)
    result = head_native_release.qualify(new_plan, reset_tree.wf_plan(new_plan), destination)
    accepted = args.out / "native_release_receipt.json"
    destination.replace(accepted)
    qualified = result["release_qualification"]
    print("NATIVE_RELEASE", qualified["verdict"], len(qualified["native_targets"]), "targets", accepted)
    print("ORIGINAL_PROOF", args.old_receipt, hexdigest(args.old_receipt))
    print("PLAN", args.new_plan, hexdigest(args.new_plan))


if __name__ == "__main__":
    main()
