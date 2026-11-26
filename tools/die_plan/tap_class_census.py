#!/usr/bin/env python3
"""C-TAP-LOAD report for the instantiated types of a bound-plan cut.

Compare current tap geometry with same-type placed bins, and report historical
measured CTS maxima separately. The shared caches do not identify the plan
digest for every record, so a matching type/outline is a correlation sample.
"""
import argparse
from collections import Counter
import contextlib
import io
import json
import os
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adv_sinkbin_stale as stale
import adv_stale_bins
import adv_tap_load
from adv_tap_insbudget import loads
import schema
import taps


def largest_groups(path, group_re, fixed):
    """Count instance-named clock sinks from a placed TSV, including shared fixed taps."""
    if path is None or not group_re:
        return {}
    regex = re.compile(group_re)
    groups = Counter()
    fixed_loads = Counter()
    with Path(path).open() as stream:
        for line in stream:
            columns = line.split("\t")
            if len(columns) != 5:
                continue
            match = regex.search(columns[1])
            group = match.group(1) if match else None
            if group is not None:
                groups[group] += 1
                if group in fixed:
                    fixed_loads[fixed[group]] += 1
    return dict(
        largest_group=groups.most_common(1)[0] if groups else None,
        largest_fixed_tap_cohorts=fixed_loads.most_common(1)[0] if fixed_loads else None,
    )


def placement_load(plan, tn, placed):
    if not placed or not placed.get("bins"):
        return {}
    if tuple(round(x, 2) for x in placed.get("die_um", ())) != tuple(
        round(x, 2) for x in plan.types[tn]["outline_um"]
    ):
        return {"placement": "different outline"}
    mode = (plan.types[tn].get("clock") or {}).get("tap_mode")
    if mode == "explicit":
        sites = taps.explicit_tap_sites(plan, tn)
    elif mode == "grid+explicit":
        sites = taps.grid_explicit_sites(plan, tn)
    else:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            sites = schema.tap_grid(plan, tn)
    if not sites:
        return {"placement": "missing planned tap sites"}
    counts, spans = loads(sites, placed["bins"])
    worst = max(range(len(counts)), key=counts.__getitem__)
    return dict(
        placement="same type and outline",
        placed_kit=placed.get("kit"),
        predicted_tap=sites[worst][0],
        predicted_max_sinks=counts[worst],
        predicted_max_span_um=round(max(spans), 3),
    )


def census(plan, cache, measured, *, tree=None, sink_lists=None, cap=5000):
    placed_bins = cache.get("placed_bins", {})
    sink_lists = sink_lists or {}
    rows = []
    for tn in sorted({instance["type"] for instance in plan.parts.values()}):
        tile = plan.types[tn]
        clock = tile.get("clock") or {}
        if tile.get("hard") or not clock:
            continue
        row = dict(type=tn, tap_mode=clock.get("tap_mode", "grid"))
        bins_file = clock.get("sink_bins_file")
        if bins_file:
            try:
                path = taps.input_path(bins_file, Path(plan.path).parent, tree)
                doc = json.loads(Path(path).read_text())
                verdict = stale.judge_type(tn, tile, doc, types=plan.types)
                row.update(
                    bins_file=bins_file,
                    bins_source=doc.get("placed_kit") or doc.get("source"),
                    bins_stale=verdict["predates"],
                    bins_inside_fraction=round(verdict["frac_in"], 5),
                )
            except (OSError, ValueError, TypeError, KeyError) as error:
                row["bins_error"] = str(error)
        try:
            row.update(placement_load(plan, tn, placed_bins.get(tn)))
        except (OSError, ValueError, TypeError, KeyError) as error:
            row["placement_error"] = str(error)
        observed = measured.get(tn) or {}
        if observed.get("max_sinks") is not None:
            row.update(
                measured_max_sinks=observed["max_sinks"],
                measured_kit=observed.get("kit") or observed.get("path"),
            )
        group = clock.get("tap_group") or {}
        try:
            row.update(largest_groups(sink_lists.get(tn), group.get("re"), group.get("fixed_taps", {})))
        except (OSError, re.error, IndexError) as error:
            row["groups_error"] = str(error)
        rows.append(row)

    def tally(field):
        values = [row[field] for row in rows if field in row]
        return dict(samples=len(values), over_cap=sum(value > cap for value in values))

    return dict(
        die=plan.name, plan=plan.path, cap=cap, soft_types=len(rows),
        predicted=tally("predicted_max_sinks"), measured=tally("measured_max_sinks"),
        bins_inside_over_5pct=sum(row.get("bins_inside_fraction", 0) > .05 for row in rows),
        types=rows,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    parser.add_argument("--tree", type=Path)
    parser.add_argument("--flops-cache")
    parser.add_argument("--kit-sinks")
    parser.add_argument("--sinks-tsv", action="append", metavar="TYPE=PATH", default=[])
    parser.add_argument("--cap", type=int, default=5000)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    raw = json.loads(args.plan.read_text())
    if args.tree is not None:
        os.environ["OT_REPO_ROOT"] = str(args.tree.resolve())
    plan = schema.Plan(raw, str(args.plan.resolve()))
    cache, _ = adv_tap_load.load_cache(args.flops_cache)
    measured, _ = adv_stale_bins.load_kit_sinks(args.kit_sinks)
    result = census(
        plan, cache or {}, measured or {},
        tree=args.tree, sink_lists=dict(value.split("=", 1) for value in args.sinks_tsv), cap=args.cap,
    )
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: value for key, value in result.items() if key != "types"}))


if __name__ == "__main__":
    main()
