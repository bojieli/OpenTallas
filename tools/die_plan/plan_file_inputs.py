#!/usr/bin/env python3
"""Presence of files used by active upper-metal grants and clock tap inventories."""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent))
import m8_grant
import schema
import taps


def _uses_sink_bins(t):
    """Match the tap planners that call taps.sink_sites and load aggregate bins."""
    clock = t.get("clock") if isinstance(t, dict) else None
    if not isinstance(clock, dict) or not isinstance(clock.get("sink_bins_file"), str) or not clock["sink_bins_file"]:
        return False
    if clock.get("native_domains") is not None:
        return False
    tap = clock.get("tap_um")
    if schema.bare_hard_single_tap(t) and isinstance(tap, (list, tuple)) and len(tap) == 2:
        return False
    mode = clock.get("tap_mode")
    return mode in ("density", "grid+explicit") or (
        mode == "explicit" and clock.get("child_root_taps") is None
    )


def missing(raw, plan, root, guide_types=None, bin_types=None):
    """List every missing active input, grouping a path shared by several types."""
    if not isinstance(raw, dict):
        return []
    types, die, parts = (raw.get(key) for key in ("partition_types", "die", "partitions"))
    if not isinstance(types, dict) or not isinstance(die, dict) or not isinstance(parts, list):
        return []  # Schema owns malformed plan structure.
    layer_budget = die.get("layer_budget") or {}
    if not isinstance(layer_budget, dict):
        return []
    budget = {**schema.DEFAULT_LAYER_BUDGET, **layer_budget}
    parts = {p["name"]: p for p in parts if isinstance(p, dict) and isinstance(p.get("name"), str)}
    view = SimpleNamespace(path=plan, layer_budget=budget, parts=parts)
    required = defaultdict(set)
    issues = []

    def guide(tn, layer, force=False):
        try:
            grant = m8_grant.kit_grant_inputs(view, tn, layer, force)
        except ValueError as exc:
            issues.append(str(exc))
            return None
        if grant is not None:
            key = m8_grant.GRANT_KEY[layer]
            for path in grant[1]:
                required[path].add((key, tn))
        return grant

    for tn in sorted(types if guide_types is None else types.keys() & guide_types):
        m8 = guide(tn, "M8")
        m9 = guide(tn, "M9")
        if m9 is not None and m8 is None:
            guide(tn, "M8", force=True)

    for tn in sorted(types if bin_types is None else types.keys() & bin_types):
        t = types[tn]
        if _uses_sink_bins(t):
            path = taps.input_path(t["clock"]["sink_bins_file"], Path(plan).parent, root)
            required[path].add(("clock.sink_bins_file", tn))

    for path, refs in sorted(required.items()):
        if not path.is_file():
            owners = ", ".join(f"{key} ({tn})" for key, tn in sorted(refs))
            issues.append(f"{path} (named by {owners})")
    return issues


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("plan", type=Path)
    ap.add_argument("--tree", type=Path, required=True)
    ap.add_argument("--guide-type", action="append")
    ap.add_argument("--bin-type", action="append")
    args = ap.parse_args(argv)
    if not args.plan.is_file():
        return 0  # The caller's ordinary input probe names this already.
    try:
        raw = json.loads(args.plan.read_text())
        issues = missing(raw, args.plan, args.tree,
                         set(args.guide_type) if args.guide_type is not None else None,
                         set(args.bin_type) if args.bin_type is not None else None)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(f"P cannot enumerate {args.plan}: {exc}")
        return 1
    for issue in issues:
        print(f"P {issue}")
    return bool(issues)


if __name__ == "__main__":
    sys.exit(main())
