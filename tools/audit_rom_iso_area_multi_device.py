#!/usr/bin/env python3
"""Iso-area against an A100 *cluster*, for models no single device can hold.

``tools/audit_rom_iso_area_inside_a100_die.py`` asks the one-die question: inside
the A100's own 826 mm2, does a ROM design that holds a whole model exist?  For
Qwen3-8B at q4p25 it does.  For DeepSeek-V4-Flash at bf16 or fp8, and for
DeepSeek-V4.1-Flash at every precision, the answer there is that **neither** side
fits -- the A100's 80 GB of HBM cannot hold the weights either -- and that audit
correctly refuses to report a ratio, because a comparison in which neither
machine can serve the model is vacuous rather than lost.

But "neither fits on one device" is not how either machine is deployed.  A large
model is served on as many devices as it takes.  So this audit asks the question
the one-die audit cannot:

    **Give each side the silicon it actually needs.  How many A100 dies does it
    take to hold this model's weights in HBM?  Charge OUR side exactly that much
    silicon -- the same total mm2 -- and compare.**

That is iso-area at the scale the model forces, and it is the only form in which
DeepSeek-V4.1-Flash can be compared at all.

Both sides shard, neither replicates
------------------------------------
The A100 cluster holds one copy of the weights spread over its devices, and so
does ours: the committed ROM array design shards a model across nodes, which is
what makes the comparison symmetric.  Neither side is charged for N copies.

Where this audit is deliberately generous to the A100
----------------------------------------------------
* Its cluster scales **linearly** -- N devices give N times the compute roof and
  N times the HBM bandwidth, with no collective, no tail and no imbalance.  A
  real tensor- or expert-parallel deployment pays all three.
* It is charged only for the weights when sizing the device count.  KV cache and
  activations are real and would raise N, which would raise the silicon budget
  this audit hands to *us*.

Where it is deliberately harsh on ours
--------------------------------------
* A ROM read is swept **once per token regardless of batch**, the same
  batch-independent model the one-die audit uses.  The A100's weight reads
  amortise over the batch and ours do not, which is why ours loses at large
  batch.  Keeping the identical model is what makes the two audits comparable.

Neither adjustment is applied silently: both are listed in ``not_a_claim``.
"""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "opentallas.derived.rom_iso_area_multi_device.v1"
TOOL = "tools/audit_rom_iso_area_multi_device.py"

#: The same committed inputs the one-die audit reads.  Restating the numbers here
#: rather than reading them would let the two audits drift apart.
ANALYTICAL = ROOT / "results/roofline/n6_vs_a100/analytical.json"
QUANTISED = ROOT / "results/roofline/quantised_variant/n6_vs_a100/analytical.json"
TECHNOLOGY_INPUTS = ROOT / "configs/hardware/technology_inputs.json"
DEVICE_LEVEL = ROOT / "results/derived/device_level_iso_area_audit.json"

A100_DIE_AREA_MM2 = 826.0

#: HBM stacks per die, capped at what the comparator's own die carries: giving
#: ours more stacks per die would compare two different dies.  The CLUSTER cap is
#: this times the device count, because each of our dies carries its own.
MAX_HBM_STACKS_PER_DIE = 5

PRECISIONS = {"bf16": 16.0, "fp8": 8.0, "q4p25": 4.25}
EXECUTION_FORMAT = {"bf16": "bf16", "fp8": "fp8", "q4p25": "w4a8"}

MODELS = {
    "Qwen3-8B": "configs/models/qwen3-8b.json",
    "DSV4-Flash": "configs/models/deepseek-v4-flash-0731.json",
    "DSV4.1-Flash": "configs/models/candidates/deepseek-v4.1-flash.json",
}

BATCHES = (1, 2, 4, 8, 16, 32, 64, 128, 256)


def _git_commit() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def _load(path: Path) -> Any:
    with path.open() as handle:
        body = json.load(handle)
    # Roofline studies are sharded: points in a sibling file, design provenance
    # in a table (see opentallas.roofline.load_study_artifact).
    if isinstance(body, dict) and body.get("points_file"):
        body["points"] = json.loads((path.parent / body.pop("points_file")).read_text())
        table = body.pop("provenance_table", {})
        for design in body.get("designs", ()):
            if isinstance(design.get("provenance"), str) and design["provenance"] in table:
                design["provenance"] = table[design["provenance"]]
    return body


def _find_key(node: Any, wanted: str) -> Any:
    if isinstance(node, dict):
        if wanted in node:
            return node[wanted]
        for value in node.values():
            found = _find_key(value, wanted)
            if found is not None:
                return found
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "results/derived/rom_iso_area_multi_device.json",
    )
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    if args.output.exists() and not args.force:
        print(f"refusing to overwrite {args.output} without --force", file=sys.stderr)
        return 1

    analytical = _load(ANALYTICAL)
    quantised = _load(QUANTISED)
    derivations = analytical["technology_derivations"]

    rom_bytes_per_mm2 = float(derivations["rom_capacity_bits_per_mm2"]["value"]) / 8.0
    rom_read_bytes_s_per_mm2 = float(derivations["rom_read_bytes_s_per_mm2"]["value"])
    sweep_ceiling_tokens_s = float(
        derivations["rom_full_array_sweep_ceiling_tokens_s"]
    )
    compute_density = {
        fmt: float(entry["value"])
        for fmt, entry in derivations["compute_ops_s_per_mm2"].items()
    }

    a100 = _find_key(_load(TECHNOLOGY_INPUTS), "a100_sxm_80gb")
    hbm_bandwidth = float(a100["hbm_bandwidth_bytes_s"])
    a100_bf16_ops_s = float(a100["bf16_dense_ops_s"])
    a100_hbm_capacity = float(a100["hbm_capacity_bytes"])

    sample = next(
        design
        for design in quantised["designs"]
        if design.get("area_split_per_device", {}).get("fractions", {}).get("overhead")
    )
    fractions = sample["area_split_per_device"]["fractions"]
    overhead_fraction = float(fractions["overhead"])
    interconnect_fraction = float(fractions["interconnect"])
    usable_fraction = 1.0 - overhead_fraction - interconnect_fraction

    cells: dict[str, Any] = {}
    for model_name, relative in MODELS.items():
        config = _load(ROOT / relative)
        checkpoint_bytes = int(config["checkpoint_bytes"])
        active = float(config["active_parameters"])
        ops_per_token = active * float(config["operations_per_active_parameter"])

        per_precision: dict[str, Any] = {}
        for precision, bits in PRECISIONS.items():
            weight_bytes = checkpoint_bytes * bits / 16.0

            # How many A100s it takes to HOLD the model.  This is what sets the
            # silicon budget, and it is the comparator's own constraint: a device
            # that cannot hold its shard cannot serve at all.
            devices = max(1, math.ceil(weight_bytes / a100_hbm_capacity))
            budget_mm2 = devices * A100_DIE_AREA_MM2
            usable_mm2 = budget_mm2 * usable_fraction

            rom_mm2 = weight_bytes / rom_bytes_per_mm2
            fits = rom_mm2 <= usable_mm2
            entry: dict[str, Any] = {
                "weight_bits_per_parameter": bits,
                "stored_weight_bytes": weight_bytes,
                "a100_devices_to_hold_the_weights": devices,
                "a100_hbm_capacity_bytes_per_device": a100_hbm_capacity,
                "silicon_budget_mm2": budget_mm2,
                "usable_area_mm2": usable_mm2,
                "rom_area_mm2": rom_mm2,
                "ours_fits_in_the_same_silicon": fits,
            }
            if not fits:
                entry["shortfall_factor_x"] = rom_mm2 / usable_mm2
                entry["verdict"] = (
                    f"ours does NOT fit even at the cluster's own scale: {devices} "
                    f"A100 dies is {budget_mm2:,.0f} mm2, {usable_mm2:,.0f} mm2 of it "
                    f"usable, and the weights alone need {rom_mm2:,.0f} mm2 of mask "
                    f"ROM -- {rom_mm2 / usable_mm2:.2f}x over"
                )
                per_precision[precision] = entry
                continue

            compute_mm2 = usable_mm2 - rom_mm2
            fmt = EXECUTION_FORMAT[precision]
            ours_compute_tokens_s = (
                compute_mm2 * compute_density[fmt]
            ) / ops_per_token
            rom_read_tokens_s = (
                rom_mm2 * rom_read_bytes_s_per_mm2
            ) / weight_bytes
            # Each node sweeps the share it holds, and the nodes sweep together,
            # so the array ceiling scales with the node count.  Stated rather than
            # assumed: with one node it is the one-die audit's own ceiling.
            ours_sweep_ceiling = sweep_ceiling_tokens_s * devices

            # The cluster: N times the roof and N times the bandwidth, no
            # collective charged.  Generous, and said so.
            a100_compute_tokens_s = (a100_bf16_ops_s * devices) / ops_per_token

            by_batch = []
            crossover_batch = None
            for batch in BATCHES:
                a100_weight_tokens_s = (
                    hbm_bandwidth * devices * batch
                ) / weight_bytes
                a100_tokens_s = min(a100_weight_tokens_s, a100_compute_tokens_s)
                a100_bound = (
                    "weight_read"
                    if a100_weight_tokens_s < a100_compute_tokens_s
                    else "compute"
                )
                ours_tokens_s = min(
                    ours_compute_tokens_s, rom_read_tokens_s, ours_sweep_ceiling
                )
                ours_bound = min(
                    (ours_compute_tokens_s, "compute"),
                    (rom_read_tokens_s, "rom_read"),
                    (ours_sweep_ceiling, "rom_array_sweep_ceiling"),
                )[1]
                ratio = ours_tokens_s / a100_tokens_s if a100_tokens_s else None
                if ratio is not None and ratio < 1.0 and crossover_batch is None:
                    crossover_batch = batch
                by_batch.append(
                    {
                        "batch": batch,
                        "ours_tokens_s": ours_tokens_s,
                        "ours_binding_constraint": ours_bound,
                        "a100_cluster_tokens_s": a100_tokens_s,
                        "a100_binding_constraint": a100_bound,
                        "speed_ratio_ours_over_a100_cluster": ratio,
                    }
                )

            entry.update(
                {
                    "compute_area_mm2": compute_mm2,
                    "execution_format": fmt,
                    "ours_compute_bound_tokens_s": ours_compute_tokens_s,
                    "ours_rom_read_bound_tokens_s": rom_read_tokens_s,
                    "ours_rom_array_sweep_ceiling_tokens_s": ours_sweep_ceiling,
                    "a100_cluster_compute_bound_tokens_s": a100_compute_tokens_s,
                    "by_batch": by_batch,
                    "batch1_speed_ratio": by_batch[0][
                        "speed_ratio_ours_over_a100_cluster"
                    ],
                    "batch256_speed_ratio": by_batch[-1][
                        "speed_ratio_ours_over_a100_cluster"
                    ],
                    "crossover_batch_where_the_cluster_overtakes": crossover_batch,
                    "verdict": (
                        f"both sides fit at {devices} A100-die of silicon "
                        f"({budget_mm2:,.0f} mm2): {rom_mm2:,.1f} mm2 of ROM leaves "
                        f"{compute_mm2:,.1f} mm2 to compute with"
                    ),
                }
            )
            per_precision[precision] = entry

        cells[model_name] = {
            "active_parameters": active,
            "operations_per_token": ops_per_token,
            "checkpoint_bytes": checkpoint_bytes,
            "by_precision": per_precision,
        }

    # Cross-check.  At one device the budget IS the one-die audit's budget, so
    # every single-device cell here must reproduce that audit's ROM area and its
    # batch-1 ratio exactly.  A drift means this tool has stopped extending the
    # study it claims to extend.
    one_die = ROOT / "results/derived/rom_iso_area_inside_a100_die.json"
    cross_check: dict[str, Any] = {"performed": one_die.exists()}
    if one_die.exists():
        published = _load(one_die)["cells"]
        checks = []
        for model_name, cell in cells.items():
            for precision, entry in cell["by_precision"].items():
                if entry["a100_devices_to_hold_the_weights"] != 1:
                    continue
                theirs = published[model_name]["by_precision"][precision]
                same_rom = (
                    abs(entry["rom_area_mm2"] - theirs["rom_area_mm2"])
                    <= 1e-9 * max(1.0, theirs["rom_area_mm2"])
                )
                ours_ratio = entry.get("batch1_speed_ratio")
                their_ratio = theirs.get("batch1_speed_ratio")
                same_ratio = (
                    ours_ratio is None
                    and their_ratio is None
                    or (
                        ours_ratio is not None
                        and their_ratio is not None
                        and abs(ours_ratio - their_ratio)
                        <= 1e-9 * max(1.0, abs(their_ratio))
                    )
                )
                checks.append(
                    {
                        "cell": f"{model_name}/{precision}",
                        "rom_area_agrees": same_rom,
                        "batch1_ratio_agrees": same_ratio,
                    }
                )
        cross_check["single_device_cells_match_the_one_die_audit"] = all(
            c["rom_area_agrees"] and c["batch1_ratio_agrees"] for c in checks
        )
        cross_check["cells_checked"] = checks

    # ---- the same architectural optimisation, at the cluster's scale ---------
    # All-ROM is one design point and, at these model sizes, the wrong one: an HBM
    # stack holds far more per mm2 of die than on-die mask ROM does, which is why
    # every DeepSeek cell above needs more than the budget as pure ROM.  The split
    # is a free variable -- hold a fraction of the weights in ROM and stream the
    # rest from HBM, charging the die for the PHY it then needs -- and it is the
    # same sweep the one-die audit runs, with the stack cap multiplied by the
    # device count because each of our dies carries its own stacks.
    hbm_per_stack_bytes_s = hbm_bandwidth / 5.0  # A100 80GB is five HBM2e stacks
    device_level = _load(DEVICE_LEVEL)["inputs"] if DEVICE_LEVEL.exists() else {}
    phy_mm2_per_stack = float(device_level.get("hbm_phy_mm2_per_stack") or 10.0)
    stack_capacity = float(device_level.get("hbm_stack_capacity_bytes") or 16e9)

    def _best_split(
        weight_bytes: float,
        ops_per_token: float,
        batch: int,
        density: float,
        usable_mm2: float,
        max_stacks: int,
    ) -> dict[str, Any]:
        best: dict[str, Any] | None = None
        for step in range(0, 101):
            fraction = step / 100.0
            rom_bytes = weight_bytes * fraction
            streamed = weight_bytes - rom_bytes
            rom_mm2 = rom_bytes / rom_bytes_per_mm2
            if rom_mm2 > usable_mm2:
                continue
            minimum_stacks = 0
            if streamed > 0:
                minimum_stacks = max(1, int(-(-streamed // stack_capacity)))
            if minimum_stacks > max_stacks:
                continue
            for stacks in range(minimum_stacks, max_stacks + 1):
                if stacks == 0 and streamed > 0:
                    continue
                phy_mm2 = stacks * phy_mm2_per_stack
                compute_mm2 = usable_mm2 - rom_mm2 - phy_mm2
                if compute_mm2 <= 0:
                    continue
                compute_s = batch * ops_per_token / (compute_mm2 * density)
                rom_s = (
                    batch * rom_bytes / (rom_mm2 * rom_read_bytes_s_per_mm2)
                    if rom_mm2
                    else 0.0
                )
                hbm_s = streamed / (stacks * hbm_per_stack_bytes_s) if stacks else 0.0
                seconds = max(compute_s, rom_s, hbm_s)
                if seconds <= 0:
                    continue
                tokens_s = batch / seconds
                bound = max(
                    (compute_s, "compute"), (rom_s, "rom_read"), (hbm_s, "hbm_read")
                )[1]
                if best is None or tokens_s > best["tokens_s"]:
                    best = {
                        "rom_fraction_of_weights": fraction,
                        "rom_area_mm2": rom_mm2,
                        "hbm_stacks": stacks,
                        "hbm_phy_area_mm2": phy_mm2,
                        "compute_area_mm2": compute_mm2,
                        "tokens_s": tokens_s,
                        "binding_constraint": bound,
                    }
        return best or {}

    optimised: dict[str, Any] = {}
    for model_name, cell in cells.items():
        ops_per_token = cell["operations_per_token"]
        for precision, entry in cell["by_precision"].items():
            weight_bytes = entry["stored_weight_bytes"]
            devices = int(entry["a100_devices_to_hold_the_weights"])
            usable = float(entry["usable_area_mm2"])
            max_stacks = MAX_HBM_STACKS_PER_DIE * devices
            density = compute_density[EXECUTION_FORMAT[precision]]
            a100_compute = (a100_bf16_ops_s * devices) / ops_per_token
            rows = []
            worst = None
            best_ratio = None
            crossover = None
            for batch in BATCHES:
                point = _best_split(
                    weight_bytes, ops_per_token, batch, density, usable, max_stacks
                )
                if not point:
                    continue
                a100_weight = hbm_bandwidth * devices * batch / weight_bytes
                a100_tokens = min(a100_weight, a100_compute)
                ratio = point["tokens_s"] / a100_tokens if a100_tokens else None
                if ratio is not None:
                    worst = ratio if worst is None else min(worst, ratio)
                    best_ratio = ratio if best_ratio is None else max(best_ratio, ratio)
                    if ratio < 1.0 and crossover is None:
                        crossover = batch
                rows.append(
                    {
                        "batch": batch,
                        "rom_fraction_of_weights": point["rom_fraction_of_weights"],
                        "hbm_stacks": point["hbm_stacks"],
                        "rom_area_mm2": point["rom_area_mm2"],
                        "compute_area_mm2": point["compute_area_mm2"],
                        "ours_tokens_s": point["tokens_s"],
                        "ours_binding_constraint": point["binding_constraint"],
                        "a100_cluster_tokens_s": a100_tokens,
                        "speed_ratio_ours_over_a100_cluster": ratio,
                    }
                )
            if not rows:
                optimised[f"{model_name}/{precision}"] = {
                    "admissible": False,
                    "a100_devices": devices,
                    "silicon_budget_mm2": entry["silicon_budget_mm2"],
                    "why": (
                        "no split is admissible: even streaming every weight from "
                        f"HBM needs more than {max_stacks} stacks, which is more "
                        f"than {devices} dies can carry at the comparator's own "
                        "five per die"
                    ),
                }
                continue
            optimised[f"{model_name}/{precision}"] = {
                "admissible": True,
                "a100_devices": devices,
                "silicon_budget_mm2": entry["silicon_budget_mm2"],
                "hbm_stack_cap": max_stacks,
                "by_batch": rows,
                "worst_case_speed_ratio": worst,
                "best_case_speed_ratio": best_ratio,
                "crossover_batch_where_the_cluster_overtakes": crossover,
                "beats_the_cluster_at_every_batch": worst is not None and worst >= 1.0,
            }

    comparable = [
        {
            "model": model_name,
            "precision": precision,
            "a100_devices": entry["a100_devices_to_hold_the_weights"],
            "silicon_budget_mm2": entry["silicon_budget_mm2"],
            "batch1_speed_ratio": entry["batch1_speed_ratio"],
            "batch256_speed_ratio": entry["batch256_speed_ratio"],
            "crossover_batch": entry["crossover_batch_where_the_cluster_overtakes"],
        }
        for model_name, cell in cells.items()
        for precision, entry in cell["by_precision"].items()
        if entry["ours_fits_in_the_same_silicon"]
    ]

    report = {
        "schema": SCHEMA,
        "producer": {"tool": TOOL, "git": {"commit": _git_commit()}},
        "question": (
            "Give each side the silicon the MODEL forces: as many A100 dies as it "
            "takes to hold the weights in HBM, and exactly that many die-areas of "
            "ours.  At that matched silicon, what does each deliver?  This is the "
            "only form in which DeepSeek-V4.1-Flash can be compared at all, since "
            "no single device of either kind can hold it."
        ),
        "inputs": {
            "a100_die_area_mm2": A100_DIE_AREA_MM2,
            "a100_hbm_capacity_bytes": a100_hbm_capacity,
            "a100_hbm_bandwidth_bytes_s": hbm_bandwidth,
            "a100_bf16_dense_ops_s": a100_bf16_ops_s,
            "rom_bytes_per_mm2": rom_bytes_per_mm2,
            "rom_read_bytes_s_per_mm2": rom_read_bytes_s_per_mm2,
            "compute_ops_s_per_mm2": compute_density,
            "usable_area_fraction": usable_fraction,
            "area_policy": sample["area_split_per_device"]["policy"],
        },
        "answer": {
            "count_considered": sum(len(c["by_precision"]) for c in cells.values()),
            "count_comparable": len(comparable),
            "comparable_cells": comparable,
        },
        "cells": cells,
        "optimised_rom_hbm_split": {
            "what": (
                "All-ROM is one design point and, at these model sizes, the wrong "
                "one: an HBM stack holds far more per mm2 of die than on-die mask "
                "ROM, which is why every DeepSeek cell needs more than its budget "
                "as pure ROM.  This sweeps the fraction held in ROM against the "
                "fraction streamed from HBM, charges the die for the PHY, and caps "
                "the stacks at five per die -- the comparator's own count -- times "
                "the device count."
            ),
            "per_cell": optimised,
        },
        "cross_check_against_the_one_die_audit": cross_check,
        "not_a_claim": [
            "no row here is a silicon claim: the densities are N6 derivations and "
            "the ROM design is not fabricated",
            "the A100 cluster is modelled as scaling LINEARLY -- N times the "
            "compute roof and N times the HBM bandwidth, with no collective, no "
            "tail and no load imbalance.  A real tensor- or expert-parallel "
            "deployment pays all three, so every ratio here understates ours",
            "the device count is sized on WEIGHTS ONLY.  KV cache and activations "
            "are real and would raise it, which would raise the silicon budget "
            "handed to ours, so this too understates ours",
            "our ROM read is charged once per token REGARDLESS of batch, while the "
            "A100's weight reads amortise over the batch.  That is the one-die "
            "audit's own model, kept identical so the two are comparable, and it "
            "is why ours loses at large batch",
            "the array sweep ceiling is scaled by the device count on the reading "
            "that nodes sweep the shares they hold concurrently; at one device it "
            "is the one-die audit's own ceiling, which the cross-check verifies",
            "holding the weights is necessary, not sufficient: a cell that fits "
            "here has not been shown to run, and the nine-cell token matrix is "
            "where running is recorded",
        ],
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")

    print(f"comparable cells: {len(comparable)} of {report['answer']['count_considered']}")
    for row in comparable:
        print(
            f"  {row['model']:14s} {row['precision']:6s} "
            f"{row['a100_devices']:3d} A100 dies = {row['silicon_budget_mm2']:8,.0f} mm2  "
            f"batch1 {row['batch1_speed_ratio']:8.3f}x  batch256 "
            f"{row['batch256_speed_ratio']:7.3f}x  crossover at batch "
            f"{row['crossover_batch']}"
        )
    print("\nnot comparable:")
    for model_name, cell in cells.items():
        for precision, entry in cell["by_precision"].items():
            if not entry["ours_fits_in_the_same_silicon"]:
                print(
                    f"  {model_name:14s} {precision:6s} "
                    f"{entry['a100_devices_to_hold_the_weights']:3d} A100 dies, "
                    f"ours needs {entry['shortfall_factor_x']:.2f}x the usable area"
                )
    print("\noptimised ROM/HBM split, at the same silicon:")
    for key, row in optimised.items():
        if not row.get("admissible"):
            print(f"  {key:26s} INADMISSIBLE -- {row['why']}")
            continue
        print(
            f"  {key:26s} {row['a100_devices']:3d} dies  worst "
            f"{row['worst_case_speed_ratio']:7.3f}x  best "
            f"{row['best_case_speed_ratio']:8.3f}x  "
            + ("BEATS THE CLUSTER AT EVERY BATCH" if row["beats_the_cluster_at_every_batch"] else f"crossover at batch {row['crossover_batch_where_the_cluster_overtakes']}")
        )
    if cross_check.get("performed"):
        print(
            "\ncross-check against the one-die audit:",
            "AGREES" if cross_check["single_device_cells_match_the_one_die_audit"] else "DIFFERS",
        )
    print(f"-> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
