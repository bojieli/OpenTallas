"""Derive per-cut tap updates from colocated native placed sink bins.

The manifest maps a type to its native bins JSON, the footprint digest of
the plan used to place the kit, and an optional instance-named sink TSV.
The bin writer owns selection of the latest eligible placement. This step
adds the current cut's row flops to those native bins and changes tap sites.
The caller then runs normal landing/reset remap, retap, and tap-offset cover.
"""
import hashlib
import json
import os
import tempfile
from pathlib import Path

import numpy as np

import adv_sinkbin_stale
from placement_obstacles import placement_boxes
import row_normalize
import schema
from sink_bins_compose import compose_bins
from tap_class_census import kit_gate, largest_groups
import tap_split
import taps


def footprint_digest(tile):
    """Match the placed outline and macros before reusing their sink bins."""
    footprint = [tile["outline_um"], placement_boxes(tile)]
    return hashlib.sha256(json.dumps(footprint, sort_keys=True).encode()).hexdigest()


def _manifest_file(manifest, name):
    path = Path(name)
    return path if path.is_absolute() else manifest.parent / path


def _publish_bins(path, blob):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        stream.write(blob)
        os.fchmod(stream.fileno(), 0o644)
    os.replace(stream.name, path)


def _load_max(sites, bins):
    points = np.array([tuple(row) if len(row) == 3 else (*row, 1) for row in bins], dtype=float)
    _, load, span = tap_split.nearest(sites, points)
    return points, float(load.max()), float(span.max())


def _split(plan, tn, points, cap, target, span):
    tile = plan.types[tn]
    clock = tile["clock"]
    sites, fixed = tap_split.type_taps(schema, plan, clock, tn)
    explicit = clock.get("tap_mode") == "explicit"
    core = [(x, y) for _, x, y, _ in schema.core_taps(plan, tn)] if explicit else []

    def legalize(x, y, taken):
        if explicit:
            return tap_split.explicit_legalize(tile, x, y, taken + core)
        return schema.tap_clear(tile, x, y, taken, strict=True)[:2]

    return tap_split.split_type(sites, fixed, points, legalize, cap=cap, target=target,
                                far_added=span, far_grid=span, split_above=cap)


def _plan_type(raw, plan, tn, manifest, entry, bins_dir, tree, cap, target, span):
    tile = raw["partition_types"][tn]
    clock = tile.get("clock") or {}
    if cap is None:         # C-TAP-LOAD 11-27: the plan's own per-type tap cap (what the kit applies), never a tool constant
        cap = kit_gate(tile)[0]
        target = min(target, cap)
    mode = clock.get("tap_mode", "grid")
    report = {"mode": mode, "cap": cap}
    if tile.get("hard") or not clock or mode not in {"grid", "grid+explicit", "explicit", "density"}:
        return dict(report, status="unsupported clock form"), False
    if entry["footprint_sha256"] != footprint_digest(tile):
        return dict(report, status="placed footprint differs"), False

    bins_path = _manifest_file(manifest, entry["bins"])
    bins_bytes = bins_path.read_bytes()
    native = json.loads(bins_bytes)
    if native.get("type") != tn or native.get("native_only") is not True or not native.get("bins"):
        raise ValueError("expected non-empty, type-matched native-only placed bins")
    stale = adv_sinkbin_stale.judge_type(tn, tile, native, types=plan.types)
    if stale["frac_in"] > adv_sinkbin_stale.FRAC or stale["outside"]:
        return dict(report, status="bins intersect macros or outline", inside_fraction=stale["frac_in"]), False

    group = clock.get("tap_group") or {}
    if group.get("re"):
        tsv = _manifest_file(manifest, entry["sinks_tsv"]) if entry.get("sinks_tsv") else None
        groups = largest_groups(tsv, group["re"], group.get("fixed_taps", {}))
        max_group = max((groups.get(key) or ("", 0))[1] for key in
                        ("largest_group", "largest_fixed_tap_cohorts"))
        status = "overloaded clock cohort" if max_group > cap else "grouped sinks require scoped assignment"
        return dict(report, status=status, placed_kit=native.get("placed_kit"), **groups), False

    native_sha = hashlib.sha256(bins_bytes).hexdigest()
    native_copy = bins_dir / f"{tn}__native_{native_sha[:16]}.json"
    doc, composition = compose_bins(raw, tn, native, os.path.relpath(native_copy, tree), native_sha)
    sites = schema.tap_grid(plan, tn) if mode == "density" else tap_split.type_taps(
        schema, plan, clock, tn
    )[0]
    points, load_before, span_before = _load_max(sites, doc["bins"])
    report.update(placed_kit=native.get("placed_kit"), max_sinks_before=load_before,
                  max_span_before_um=span_before, row_sinks=composition["added"])
    if load_before <= cap and span_before <= span:
        return dict(report, status="within limits"), False

    if mode == "density":
        new_sites = None
        proposed = dict(clock, tap_max_sinks=min(cap, clock.get("tap_max_sinks", cap)),
                        tap_target_sinks=min(target, clock.get("tap_target_sinks", target)),
                        tap_radius_um=min(span, clock.get("tap_radius_um", span)))
    else:
        new_sites, result = _split(plan, tn, points, cap, target, span)
        report.update(max_sinks_after=max(result["load"]), max_span_after_um=max(result["far"]))
        if not new_sites or max(result["load"]) > cap or max(result["far"]) > span:
            return dict(report, status="site solver could not meet load/span"), False
        proposed = dict(clock)
        taps_key = "taps" if mode == "explicit" else "added_taps"
        existing = list(clock.get(taps_key) or [])
        existing.extend(dict(name=f"clk_t{len(sites) + i}", xy=[round(x, 3), round(y, 3)])
                        for i, (x, y) in enumerate(new_sites))
        proposed[taps_key] = existing
        if mode == "grid":
            proposed["tap_mode"] = "grid+explicit"

    if mode != "explicit":
        content = json.dumps(doc, sort_keys=True, separators=(",", ":")) + "\n"
        digest = hashlib.sha256(content.encode()).hexdigest()[:16]
        bins_file = bins_dir / f"{tn}__{digest}.json"
        _publish_bins(native_copy, bins_bytes)
        _publish_bins(bins_file, content.encode())
        proposed["sink_bins_file"] = os.path.relpath(bins_file, tree)
    tile["clock"] = proposed
    return dict(report, status="derive", new_taps=len(new_sites) if new_sites is not None else None), True


def derive(raw, plan_path, tree, manifest, *, cap=None, target=1000, span=300.0, bins_dir=None):
    """Apply eligible tap derivations and return the types and per-type diagnostics.

    cap=None (default): each type is judged and re-solved against its OWN plan tap cap (kit_gate: OT_TAP_MAX_SINKS, else
    clock.tap_max_sinks, else 1500 density / 3000 grid; 1000 on the QC types), the target clamped to it.  An int forces one
    constant for every type (the old default was 5000, which called 3.9-4.6k taps 'within limits' on 1000-cap types)."""
    plan_path, tree, manifest = Path(plan_path), Path(tree).resolve(), Path(manifest).resolve()
    # a proof run may publish composed bins outside the (shared, read-only) tree; the plan then names them relative to it
    if bins_dir:
        bins_dir = Path(bins_dir).resolve()
    else:
        bins_dir = (plan_path.resolve().parent / "sink_bins" / "tap_derive").resolve()
        bins_dir.relative_to(tree)
    entries = json.loads(manifest.read_text())
    if not isinstance(entries, dict):
        raise ValueError("expected a type-to-placed-bins manifest")
    if cap is not None and not 0 < target <= cap or span <= 0:
        raise ValueError("target must be positive and within cap, with positive span")
    selected = []
    report = {}
    with row_normalize.in_tree(tree):
        plan = schema.Plan(raw, str(plan_path.resolve()))
        instantiated = {row["type"] for row in plan.parts.values()}
        for tn, entry in sorted(entries.items()):
            if tn not in instantiated:
                report[tn] = {"status": "type not instantiated"}
                continue
            try:
                report[tn], changed = _plan_type(raw, plan, tn, manifest, entry, bins_dir,
                                                 tree, cap, target, span)
            except (OSError, KeyError, TypeError, ValueError) as error:
                raise ValueError(f"{tn}: {error}") from error
            if changed:
                selected.append(tn)
    return selected, report


def density_results(raw, plan_path, tree, selected, *, cap=None, span=300.0):
    """Check the final density sites after the standard name/geometry normalize."""
    plan_path = Path(plan_path).resolve()
    report = {}
    with row_normalize.in_tree(tree):
        plan = schema.Plan(raw, str(plan_path))
        for tn in selected:
            clock = plan.types[tn]["clock"]
            if clock.get("tap_mode") != "density":
                continue
            path = taps.input_path(clock["sink_bins_file"], plan_path.parent, tree)
            bins = json.loads(path.read_text())["bins"]
            _, load, far = _load_max(schema.tap_grid(plan, tn), bins)
            tcap = kit_gate(plan.types[tn])[0] if cap is None else cap
            report[tn] = dict(max_sinks_after=load, max_span_after_um=far, cap=tcap,
                              within_limits=load <= tcap and far <= span)
    return report
