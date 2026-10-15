#!/usr/bin/env python3
"""Pin actual native view bundles and conditional POST geometry; never launch a die route.

Artifact availability is distinct from closure qualification. A missing view or obstruction
coverage leaves the final-route gate closed, even when conditional footprint arithmetic fits.
"""
import argparse
import hashlib
import json
import math
import re
import subprocess
from pathlib import Path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bundle(root, master, directory, expected):
    paths = {"lef": directory / (master + ".lef")}
    paths.update({c: directory / (master + "_" + c + ".lib") for c in ("tt", "ff", "ss")})
    missing = [k for k, p in paths.items() if not p.exists()]
    size = None
    if paths["lef"].exists():
        text = paths["lef"].read_text()
        block = re.search(r"^MACRO " + re.escape(master) + r"\s*\n(.*?)^END " +
                          re.escape(master) + r"\s*$", text, re.M | re.S)
        if not block:
            missing.append("LEF master identity")
        else:
            match = re.search(r"SIZE\s+([\d.]+)\s+BY\s+([\d.]+)", block[1])
            size = list(map(float, match.groups())) if match else None
    for c in ("tt", "ff", "ss"):
        if paths[c].exists() and not re.search(r"cell\s*\(\s*\"?" + re.escape(master) +
                                              r"\"?\s*\)", paths[c].read_text()):
            missing.append(c + " cell identity")
    fit = size is not None and all(v <= e + 1e-6 for v, e in zip(size, expected))
    metadata = {}
    for name in ("corner_sta.json", "child_lint.json", "abstract.json", "insertion.json", "check.json"):
        p = directory / name
        if p.exists():
            metadata[name] = {"path": str(p.relative_to(root)), "sha256": digest(p)}
    return {"master": master, "files": {k: {"path": str(p.relative_to(root)), "sha256": digest(p)}
                                             for k, p in paths.items() if p.exists()},
            "same_export_directory": str(directory.relative_to(root)), "missing": missing,
            "native_corner_bundle_available": not missing, "outline_um": size,
            "reference_slot_um": expected, "fits_reference_footprint": fit,
            "export_metadata": metadata, "qualified_closed": False,
            "qualification": "not established: source/bench/mutant/child-lint/throughput receipts require verification"}


def row_cut(root, row, member, column_width, xcols):
    """Partial native row cut from exact rectangles, including power/pin rectangles conservatively.

    This is not a full field cut: missing rows and other die wiring remain unknown.
    """
    text = (root / member["files"]["lef"]["path"]).read_text()
    rects, layer = [], None
    for line in text.splitlines():
        lm = re.search(r"\bLAYER\s+(M\d+)\s*;", line)
        if lm:
            layer = lm[1]
        match = re.search(r"\bRECT\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)", line)
        if match and layer:
            rects.append((layer, *map(float, match.groups())))
    count = {}
    copies = xcols if row.get("per_col") else [0.0]
    y = row["h"] / 2
    for metal, pitch, offset in (("M5", .048, .012), ("M7", .064, .016), ("M9", .080, .116)):
        blocked = [(x + x0, x + x1) for x in copies for l, x0, y0, x1, y1 in rects
                   if l == metal and y0 <= y <= y1]
        # Relative track phase is recorded as a conditional local phase; final global phase comes from the new DEF.
        grid = [offset + k * pitch for k in range(math.ceil(column_width / pitch))
                if offset + k * pitch < column_width]
        count[metal] = sum(not any(a <= x <= b for a, b in blocked) for x in grid)
    # The recorded c5 GRT uses M4-M9, so M3 must not be counted. M9 is a die-global/power layer;
    # give its PG stripes a conservative two-track guard, then retain the additional global reserve.
    m9_pg_bound = (2 * math.ceil(column_width / 9.092) + 2) * (math.ceil(.48 / .080) + 2)
    m9_after_pg = max(0, count["M9"] - m9_pg_bound)
    lower_supply = .8 * (count["M5"] + count["M7"])
    usable = lower_supply + .8 * m9_after_pg
    demand = 3056 + 2164 + 1728
    return {"row": row["tile"], "master": row["cell"], "row_relative_cut_y_um": row["y"] + y,
            "free_tracks_after_exact_native_rectangles": count, "conditional_supply_after_20pct_reserve": usable,
            "m5_m7_only_conditional_supply": lower_supply,
            "m5_m7_only_conditional_utilization": demand / lower_supply if lower_supply else None,
            "m9_pg_guard_bound_tracks": m9_pg_bound,
            "m9_global_plan_and_actual_background_verified": False,
            "hc_plus_worst_post_column_bits": demand, "conditional_utilization": demand / usable if usable else None,
            "complete_field_or_background_coverage": False}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--writer-root", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    root, writer = a.root.resolve(), a.writer_root.resolve()
    census = root / "results/physical/die_iter_1012/s81/real_view_census_20261013/c5_census.json"
    replacement = root / "results/physical/die_iter_1012/s81/real_view_census_20261013/c5_replacements.json"
    candidates = json.loads(replacement.read_text())["closed_tag_abstract_replacement_candidates"]
    native = []
    for row in candidates:
        exports = row["routed_lef_candidates"]
        choices = [bundle(root, row["master"], (root / x["path"]).parent, row["generated_outline_um"])
                   for x in exports]
        chosen = next((x for x in choices if x["native_corner_bundle_available"]), None)
        native.append({"master": row["master"], "reference_instances": row["instances"],
                       "binding": chosen, "rejected_or_incomplete_exports": choices if not chosen else []})
    writer_paths = ["results/arch/hier_contract_1011/s81.json",
                    "results/physical/die_iter_1012/s81/s81_layer1_v14.opts",
                    "tools/dsrom_s81_fulldie.py", "tools/s81/die_hop_gate.py"]
    writer_hashes = {n: digest(writer / n) for n in writer_paths}
    contract = json.loads((writer / writer_paths[0]).read_text())
    slots = {s["name"]: s for s in contract["slots"]}
    hc = slots["sp_hc_s"]
    lower = slots["sp_hc_t"]
    y0 = lower["origin"]["y"] + lower["outline"]["h"]
    y1 = hc["origin"]["y"]
    midpoint = [hc["origin"]["x"] + hc["outline"]["w"] / 2, (y0 + y1) / 2]
    layout = contract["sub_layouts"]["ot_s81_hc_cth"]
    leaf_members = []
    for cell in sorted({r["cell"] for r in layout["rows"]}):
        row = next(r for r in layout["rows"] if r["cell"] == cell)
        directory = root / "physical/ref_tile" / ("s81hc_" + cell.removeprefix("ot_s81_hc_") + "_ref") / "views" / cell
        leaf_members.append(bundle(root, cell, directory, [row["w"], row["h"]]))
    branches = []
    bases = [0, 22, 42]
    # Each branch stays within one side of the corridor. No regional serial path crosses the 1512 um band.
    for col, base in enumerate(bases):
        start = base
        for side, groups in (("north", [3, 3, 2, 2]),
                             ("south", [3, 3, 2, 2] if col == 1 else [3, 3, 3, 3])):
            for count in groups:
                positions = list(range(start, start + count))
                children = [slots[("sp_hc_s" if side == "north" else "sp_hc_t") + "/ctile_" + str(p)]
                            for p in positions]
                parent = hc if side == "north" else lower
                centers = [[parent["origin"]["x"] + s["origin"]["x"] + s["outline"]["w"] / 2,
                            parent["origin"]["y"] + s["origin"]["y"] + s["outline"]["h"] / 2]
                           for s in children]
                center = [sum(p[k] for p in centers) / len(centers) for k in (0, 1)]
                distance = sum(abs(center[k] - midpoint[k]) for k in (0, 1))
                local_distance = max(sum(abs(p[k] - center[k]) for k in (0, 1)) for p in centers)
                # Include a half-region width to expose unknown actual consumer pin/seam distances.
                local_bound = local_distance + max(s["outline"]["w"] for s in children) / 2
                branches.append({"id": len(branches), "column": col, "side": side,
                                 "half_positions": positions, "group_words": 4 * count,
                                 "payload_bits": 128 * count, "bundle_bits": 128 * count + 25,
                                 "completion_bits": 23, "conditional_center_um": center,
                                 "midpoint_manhattan_um": distance,
                                 "minimum_global_stages_at_500um": math.ceil(distance / 500),
                                 "local_pin_distance_envelope_um": local_bound,
                                 "minimum_local_stages_at_500um": math.ceil(local_bound / 500)})
                start += count
    assert len(branches) == 24 and sorted(p for b in branches for p in b["half_positions"]) == list(range(64))
    assert sum(b["payload_bits"] for b in branches) == 8192
    width = hc["outline"]["w"]
    # Physical track pitches recorded in the existing c5 DEF; absence of actual OBS prevents a capacity grant.
    pitches = {"M5": .048, "M7": .064, "M9": .080}
    raw = sum(math.floor(width / p) for p in pitches.values())
    conditional_supply = .8 * raw
    cuts = []
    for side in ("north", "south"):
        selected = [b for b in branches if b["side"] == side]
        extra = sum(b["bundle_bits"] + b["completion_bits"] for b in selected)
        cuts.append({"side": side, "post_extra_bits": extra, "existing_hc_bits": 3 * (3056 + 2164),
                     "total_demand_bits": extra + 3 * (3056 + 2164),
                     "raw_geometric_tracks": raw, "conditional_20pct_reserve_tracks": conditional_supply,
                     "conditional_utilization": (extra + 3 * (3056 + 2164)) / conditional_supply,
                     "actual_obstruction_and_background_cut_verified": False})
    by_leaf = {m["master"]: m for m in leaf_members}
    leaf_counts = {"available_native_bundles": 0, "missing_native_bundles": 0}
    for row in layout["rows"]:
        category = "available_native_bundles" if by_leaf[row["cell"]]["native_corner_bundle_available"] else "missing_native_bundles"
        leaf_counts[category] += 64 * (4 if row.get("per_col") else 1)
    leaf_counts.update(total_after_flattening_64_half_regions=sum(leaf_counts.values()),
                       binding_into_die_netlist_complete=False)
    observed_seam = re.search(r"HC_T_FWD, HC_T_RET\s*=\s*(\d+),\s*(\d+)",
                              (writer / "tools/dsrom_s81_fulldie.py").read_text())
    partial_cuts = [row_cut(root, r, by_leaf[r["cell"]], 619.92, layout["x_cols"])
                    for r in layout["rows"] if by_leaf[r["cell"]]["native_corner_bundle_available"]]
    # Detect concurrent writer edits, rather than claiming a mixed snapshot is authoritative.
    assert writer_hashes == {n: digest(writer / n) for n in writer_paths}, "writer changed during read; retry snapshot"
    record = {"schema": "s81-native-successor-manifest-v1",
              "codex_source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
              "manifest_builder_sha256": digest(Path(__file__)),
              "census_sha256": digest(census), "replacement_sha256": digest(replacement),
              "writer_snapshot": {"read_only": True, "source_root": str(writer), "files": writer_hashes,
                                  "published_contract_version": contract["version"],
                                  "v14_contract_published": False},
              "native_legacy_bindings": native, "hc_half_leaf_membership": leaf_members,
              "hc_reference_leaf_instances": leaf_counts,
              "native_bundle_reference_instances": sum(r["reference_instances"] for r in native if r["binding"]),
              "qualified_closed_instances_established": 0,
              "actual_hc_seam": {"forward_bits": 3056, "return_bits": 2164, "total_three_columns": 15660,
                                 "cut_after": [9, 31, 51], "native_parameters": {"S_RD": 2, "S_RT": 4},
                                 "rtl_source_sha256": digest(root / "rtl/dsrom_sys/s81_suhc/dsfd_sp_hc.sv"),
                                 "observed_writer_generator_bits": list(map(int, observed_seam.groups())) if observed_seam else None,
                                 "generator_widening_still_required": True},
              "post_conditional": {"midpoint_um": midpoint, "corridor_y_um": [y0, y1],
                                   "branches": branches, "cuts": cuts, "credit_beats_per_branch": 20,
                                   "existing_grt_signal_layers": "M4-M9",
                                   "m9_global_allocation_granted": False,
                                   "partial_native_row_cuts": partial_cuts,
                                   "minimum_usable_column_tracks_for_0p60": (3056 + 2164 + 1728) / .6,
                                   "payload_frame_bits": 8192 * 20, "immutable_post_max_cycles": 124.19,
                                   "measured_cycles": None, "placement_granted": False,
                                   "resident_coefficient_generation_gate_required": True},
              "final_die_grt_allowed": False,
              "blockers": ["Unpublished v14 geometry and widened HC generator input",
                           "Missing HC native leaf views and source-matched qualification receipts",
                           "Placeholder slab/field/glue models still cover most of the die",
                           "Actual native LEF OBS, existing-background cuts, consumer pin maps and clock seams unverified",
                           "Native registered express queue/dispatch/completion views not yet implemented",
                           "Physical minimum-delay seam remains owed; no synthetic-delay closure"]}
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps({"native_bundle_instances": record["native_bundle_reference_instances"],
                      "hc_leaf_bundles": sum(x["native_corner_bundle_available"] for x in leaf_members),
                      "branches": len(branches), "cuts": cuts, "route_gate": "BLOCKED"}))


if __name__ == "__main__":
    main()
