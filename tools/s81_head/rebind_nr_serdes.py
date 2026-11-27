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


# P-RESET-RECEIPT guard change (HEAD-PROBE-R3 11-27): a CHANGED hd_serdes partition (reset_entry_phase, id_straps, ...) used to be refused outright,
# even when a receipt qualified on the new plan existed.  It is accepted only with --new-receipt: a receipt produced on the NEW plan digest by the
# stock producer (head_native_release_receipt.py) whose proof.exercised_plan_fields cover EVERY partition key that differs, and that qualifies.
def _flat(prefix, v, out):
    if isinstance(v, dict):
        for k in sorted(v):
            _flat(prefix + "." + str(k) if prefix else str(k), v[k], out)
    else:
        out[prefix] = json.dumps(v, sort_keys=True)


def part_diff(old_parts, new_parts):
    """sorted leaf paths 'partitions[NAME].key.sub' that differ between two {name: part} maps (added / removed / changed)"""
    out = []
    for name in sorted(set(old_parts) | set(new_parts)):
        a, b = {}, {}
        if name in old_parts:
            _flat("", old_parts[name], a)
        if name in new_parts:
            _flat("", new_parts[name], b)
        for k in sorted(set(a) | set(b)):
            if a.get(k) != b.get(k):
                out.append("partitions[%s].%s" % (name, k))
    return out


def norm_field(path):
    """partitions[lk_EN0].reset_entry_phase -> partitions[*].reset_entry_phase"""
    import re
    return re.sub(r"^partitions\[[^\]]*\]", "partitions[*]", path)


def check_changed_binding(old_parts, new_parts, new_receipt, new_digest):
    """-> sorted diff paths when the receipt covers the whole partition diff; raises ValueError otherwise (fail closed)"""
    diff = part_diff(old_parts, new_parts)
    if not diff:
        return diff
    if new_receipt is None:
        raise ValueError("HEAD native reset instance bindings changed")
    if new_receipt.get("plan_sha256") != new_digest:
        raise ValueError("HEAD native reset instance bindings changed: receipt is not for the new plan digest")
    fields = (new_receipt.get("proof") or {}).get("exercised_plan_fields")
    if not fields:
        raise ValueError("HEAD native reset instance bindings changed: receipt lists no exercised plan fields")
    covered = set(fields)
    bad = sorted({norm_field(p) for p in diff} - covered)
    if bad:
        raise ValueError("HEAD native reset instance bindings changed: receipt does not cover " + ", ".join(bad[:6]))
    return diff


def fwd_only_delta(a, b):
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
    # HEAD-SERDES-REFLOOR: physical-only keys (pad M7 sites, die-clock reserved sites) are not part of the native reset contract
    for x in (a, b):
        for pd in x.get("pads", []):
            pd.pop("sites_um", None); pd.pop("layer", None)
        x.get("clock", {}).pop("reserved_sites_um", None)
        x.pop("place_regions", None)
        for hc in x.get("hard_cores", []): hc.pop("origin_um", None)
    if a != b:
        raise ValueError("HEAD native reset type changed")
    print("FWD_ONLY_DELTA", moved)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("old_plan", "new_plan", "old_receipt", "out", "tools"):
        parser.add_argument(name, type=Path)
    parser.add_argument("--new-receipt", type=Path, default=None,
                        help="receipt produced on the NEW plan digest whose proof.exercised_plan_fields cover every changed hd_serdes partition key")
    args = parser.parse_args()
    sys.path.insert(0, str(args.tools))
    import cores
    import head_native_release
    import reset_tree
    import schema

    old, new = json_load(args.old_plan), json_load(args.new_plan)
    receipt = json_load(args.old_receipt)
    fwd_only_delta(old["partition_types"]["hd_serdes"], new["partition_types"]["hd_serdes"])
    if serdes_parts(old) != serdes_parts(new):
        nr = json_load(args.new_receipt) if args.new_receipt else None
        diff = check_changed_binding(serdes_parts(old), serdes_parts(new), nr, head_native_release.digest(new))
        new_plan = schema.Plan(new, args.new_plan)
        result = head_native_release.qualify(new_plan, reset_tree.wf_plan(new_plan), args.new_receipt)
        args.out.mkdir(parents=True, exist_ok=False)
        root = args.new_receipt.parent
        for item in root.iterdir():
            if item.is_file() and item.name != "native_release_receipt.json":
                shutil.copyfile(item, args.out / item.name)
        accepted = args.out / "native_release_receipt.json"
        shutil.copyfile(args.new_receipt, accepted)
        print("CHANGED_BINDING_COVERED", len(diff), "paths", diff[:8])
        print("NATIVE_RELEASE", result["release_qualification"]["verdict"], len(result["release_qualification"]["native_targets"]), "targets", accepted)
        print("PLAN", args.new_plan, hexdigest(args.new_plan))
        return
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
