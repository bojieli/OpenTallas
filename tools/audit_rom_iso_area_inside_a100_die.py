#!/usr/bin/env python3
"""The ROM products answered INSIDE the A100's own 826 mm2, not at matched area.

``tools/audit_rom_iso_area_against_gpu.py`` answers the ROM question at matched
SILICON AREA -- a 26,080 mm2 ROM array against 16 B200s -- and says the 826 mm2
frame "cannot express" it, because 16 GiB of mask ROM is larger than a GPU die by
construction.  That is true of the SHIPPED precisions and it is the reason the
826 mm2 answer went missing.  It is not true in general, and this audit supplies
the missing answer rather than restating why it is hard.

**The frame.** One A100 SXM 80GB is 826 mm2 at TSMC N7.  The committed comparison
contract already pairs that against one N6 reticle (815 mm2) -- "essentially the
same die one node apart".  So the question has a well-posed form: put the whole
design inside 826 mm2, charge it for its own weight storage, and ask what it
delivers against the one A100 that occupies the same silicon.

**The area policy is the study's own**, read out of the committed design records
rather than invented here: 10% overhead, 8% interconnect, ROM sized to the stored
weights, KV off-die in HBM, and compute takes what is left.  With KV off-die the
design spends nothing on SRAM, which is the allocation that gives ROM its best
chance inside a single die.

**What the audit finds is a crossover, not a win.**  At batch 1 the GPU must read
every weight from HBM for every token and the ROM design does not, so the ROM
design wins by a wide margin.  At large batch the GPU amortises that read across
the batch and becomes compute-bound -- while the ROM design has spent most of its
826 mm2 on storage and has little area left to compute with.  Past the crossover
batch the A100 wins.  Both halves are reported, because reporting only the first
would be the same selective framing the matched-area audit was criticised for.

Every density, roof and bandwidth is read from a committed artifact and carries
its grade.  Nothing here is fitted.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "opentallas.derived.rom_iso_area_inside_a100_die.v1"
TOOL = "tools/audit_rom_iso_area_inside_a100_die.py"

#: The committed N6-vs-A100 roofline, for its graded technology derivations.
ANALYTICAL = ROOT / "results/roofline/n6_vs_a100/analytical.json"
#: The committed quantised-variant study, for the q4p25 ROM footprint.
QUANTISED = ROOT / "results/roofline/quantised_variant/n6_vs_a100/analytical.json"
#: The committed A100 facts.
TECHNOLOGY_INPUTS = ROOT / "configs/hardware/technology_inputs.json"
#: The measured-ASAP7 device-level audit, for the compute-density sensitivity.
DEVICE_LEVEL = ROOT / "results/derived/device_level_iso_area_audit.json"

#: NVIDIA A100 SXM 80GB die area.  The roofline derives its own compute density by
#: dividing the published dense roof by this number, so it is already load-bearing
#: in the committed artifacts; it is restated here because it IS the area budget.
A100_DIE_AREA_MM2 = 826.0

#: The comparator's own HBM stack count.  Allowing our die more stacks than the A100
#: carries would compare two different dies: the PHY area is charged either way, but
#: the beachfront that hosts it is not modelled, so the count is capped at the A100's.
MAX_HBM_STACKS = 5

#: Weight bit widths.  ``q4p25`` is the quantised study's own name: 4 bits of
#: weight plus a 0.25-bit-per-weight share of the block scales.
PRECISIONS = {
    "bf16": 16.0,
    "fp8": 8.0,
    "q4p25": 4.25,
}

#: Which compute roof each weight precision executes against, by the study's
#: ``execution_format`` convention.
EXECUTION_FORMAT = {"bf16": "bf16", "fp8": "fp8", "q4p25": "w4a8"}

MODELS = {
    "Qwen3-8B": "configs/models/qwen3-8b.json",
    "DSV4-Flash": "configs/models/deepseek-v4-flash-0731.json",
    "DSV4.1-Flash": "configs/models/candidates/deepseek-v4.1-flash.json",
}

BATCHES = (1, 2, 4, 8, 16, 32, 64, 128, 256)


def _git_commit() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
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


def _model_weight_bytes(config: dict) -> tuple[int, dict]:
    """Stored weight bytes at the checkpoint's own precision, and how it splits.

    The ROM must hold every weight the model can reach, not only the active ones:
    a mask ROM cannot fault a expert in.  ``checkpoint_bytes`` is the released
    file size, which includes the quantisation scales, so it is the honest figure
    for how much storage the design must provide.
    """
    dense = int(config["dense_weight_bytes"])
    routed = int(config.get("routed_weight_bytes", 0))
    resident = int(config.get("resident_only_weight_bytes", 0))
    checkpoint = int(config["checkpoint_bytes"])
    return checkpoint, {
        "dense_weight_bytes": dense,
        "routed_weight_bytes": routed,
        "resident_only_weight_bytes": resident,
        "checkpoint_bytes": checkpoint,
        "basis": (
            "checkpoint_bytes: every weight the model can reach, because a mask "
            "ROM cannot fault an expert in on demand"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "results/derived/rom_iso_area_inside_a100_die.json")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    if args.output.exists() and not args.force:
        print(f"refusing to overwrite {args.output} without --force", file=sys.stderr)
        return 1

    analytical = _load(ANALYTICAL)
    quantised = _load(QUANTISED)
    derivations = analytical["technology_derivations"]

    rom_bits_per_mm2 = float(derivations["rom_capacity_bits_per_mm2"]["value"])
    rom_bytes_per_mm2 = rom_bits_per_mm2 / 8.0
    rom_read_bytes_s_per_mm2 = float(derivations["rom_read_bytes_s_per_mm2"]["value"])
    sweep_ceiling_tokens_s = float(derivations["rom_full_array_sweep_ceiling_tokens_s"])
    compute_density = {
        fmt: float(entry["value"])
        for fmt, entry in derivations["compute_ops_s_per_mm2"].items()
    }

    a100 = _find_key(_load(TECHNOLOGY_INPUTS), "a100_sxm_80gb")
    hbm_bandwidth = float(a100["hbm_bandwidth_bytes_s"])
    a100_bf16_ops_s = float(a100["bf16_dense_ops_s"])
    a100_hbm_capacity = float(a100["hbm_capacity_bytes"])

    # The area policy, read from a committed design record rather than assumed.
    sample = next(
        design
        for design in quantised["designs"]
        if design.get("area_split_per_device", {}).get("fractions", {}).get("overhead")
    )
    fractions = sample["area_split_per_device"]["fractions"]
    overhead_fraction = float(fractions["overhead"])
    interconnect_fraction = float(fractions["interconnect"])
    policy_note = sample["area_split_per_device"]["policy"]

    usable_fraction = 1.0 - overhead_fraction - interconnect_fraction
    usable_mm2 = A100_DIE_AREA_MM2 * usable_fraction

    cells: dict[str, Any] = {}
    for model_name, relative in MODELS.items():
        config = _load(ROOT / relative)
        checkpoint_bytes, split = _model_weight_bytes(config)
        active = float(config["active_parameters"])
        ops_per_token = active * float(config["operations_per_active_parameter"])

        per_precision: dict[str, Any] = {}
        for precision, bits in PRECISIONS.items():
            # The checkpoint is stored at 16 bits per weight (bf16 + scales); a
            # narrower precision scales the stored bytes by the bit ratio.
            weight_bytes = checkpoint_bytes * bits / 16.0
            rom_mm2 = weight_bytes / rom_bytes_per_mm2
            fits = rom_mm2 <= usable_mm2
            entry: dict[str, Any] = {
                "weight_bits_per_parameter": bits,
                "stored_weight_bytes": weight_bytes,
                "rom_area_mm2": rom_mm2,
                "usable_area_mm2": usable_mm2,
                "fits_inside_a100_die": fits,
            }
            if not fits:
                entry["shortfall_factor_x"] = rom_mm2 / usable_mm2
                entry["verdict"] = (
                    f"does not fit: the weights alone need {rom_mm2:,.0f} mm2 of mask "
                    f"ROM, {rom_mm2 / usable_mm2:.2f}x the {usable_mm2:,.0f} mm2 this "
                    f"die has to spend after overhead and interconnect"
                )
                per_precision[precision] = entry
                continue

            compute_mm2 = usable_mm2 - rom_mm2
            fmt = EXECUTION_FORMAT[precision]
            ours_ops_s = compute_mm2 * compute_density[fmt]
            ours_compute_tokens_s = ours_ops_s / ops_per_token
            # A ROM read is local to the array, so the whole weight set is swept
            # once per token regardless of batch -- the array's own hard ceiling.
            rom_read_tokens_s = (rom_mm2 * rom_read_bytes_s_per_mm2) / weight_bytes

            # The A100 holds the same weights in HBM.  Below its capacity it reads
            # every weight once per BATCH, so the read cost amortises.
            a100_fits_in_hbm = weight_bytes <= a100_hbm_capacity
            a100_compute_tokens_s = a100_bf16_ops_s / ops_per_token

            by_batch = []
            crossover_batch = None
            for batch in BATCHES:
                a100_weight_tokens_s = hbm_bandwidth * batch / weight_bytes
                a100_tokens_s = min(a100_weight_tokens_s, a100_compute_tokens_s)
                a100_bound = (
                    "weight_read" if a100_weight_tokens_s < a100_compute_tokens_s else "compute"
                )
                ours_tokens_s = min(
                    ours_compute_tokens_s, rom_read_tokens_s, sweep_ceiling_tokens_s
                )
                ours_bound = min(
                    (ours_compute_tokens_s, "compute"),
                    (rom_read_tokens_s, "rom_read"),
                    (sweep_ceiling_tokens_s, "rom_array_sweep_ceiling"),
                )[1]
                ratio = ours_tokens_s / a100_tokens_s if a100_tokens_s else None
                if ratio is not None and ratio < 1.0 and crossover_batch is None:
                    crossover_batch = batch
                by_batch.append(
                    {
                        "batch": batch,
                        "ours_tokens_s": ours_tokens_s,
                        "ours_binding_constraint": ours_bound,
                        "a100_tokens_s": a100_tokens_s,
                        "a100_binding_constraint": a100_bound,
                        "speed_ratio_ours_over_a100": ratio,
                    }
                )

            entry.update(
                {
                    "compute_area_mm2": compute_mm2,
                    "execution_format": fmt,
                    "kv_store": "hbm (off-die): the allocation that gives ROM its best chance inside one die",
                    "ours_compute_bound_tokens_s": ours_compute_tokens_s,
                    "ours_rom_read_bound_tokens_s": rom_read_tokens_s,
                    "rom_array_sweep_ceiling_tokens_s": sweep_ceiling_tokens_s,
                    "a100_compute_bound_tokens_s": a100_compute_tokens_s,
                    "a100_weights_fit_in_80gb_hbm": a100_fits_in_hbm,
                    "by_batch": by_batch,
                    "batch1_speed_ratio": by_batch[0]["speed_ratio_ours_over_a100"],
                    "batch256_speed_ratio": by_batch[-1]["speed_ratio_ours_over_a100"],
                    "crossover_batch_where_a100_overtakes": crossover_batch,
                    "verdict": (
                        f"fits: {rom_mm2:,.1f} mm2 of ROM leaves {compute_mm2:,.1f} mm2 to "
                        f"compute with"
                    ),
                }
            )
            per_precision[precision] = entry

        cells[model_name] = {
            "weight_inventory": split,
            "active_parameters": active,
            "operations_per_token": ops_per_token,
            "by_precision": per_precision,
        }

    # Cross-check: the q4p25 ROM footprint this audit computes from the densities
    # must reproduce the committed quantised design's own rom_mm2 total, or the
    # arithmetic here has drifted from the study it claims to extend.
    committed_rom_total = None
    for design in quantised["designs"]:
        name = design.get("design") or ""
        if name.endswith("-x1") and "q4p25" in name:
            split = design["area_split_per_device"]
            committed_rom_total = float(split["rom_mm2"])
            committed_rom_design = name
            break
    cross_check: dict[str, Any] = {"performed": committed_rom_total is not None}
    if committed_rom_total is not None:
        ours = cells["Qwen3-8B"]["by_precision"]["q4p25"]["rom_area_mm2"]
        relative = abs(ours - committed_rom_total) / committed_rom_total
        cross_check.update(
            {
                "committed_design": committed_rom_design,
                "committed_rom_mm2": committed_rom_total,
                "this_audit_rom_mm2": ours,
                "relative_difference": relative,
                "agrees": relative < 1e-9,
            }
        )
        if relative >= 1e-6:
            raise SystemExit(
                f"q4p25 ROM area {ours} disagrees with the committed design's "
                f"{committed_rom_total} (relative {relative:.3e})"
            )

    # A sensitivity, deliberately NOT folded into the answer above.  The compute
    # density used throughout is the roofline's, derived by scaling the A100's own
    # published roof to N6.  This repository also has a MEASURED compute density,
    # from the routed ASAP7 compute unit in the device-level audit.  It is about
    # 2.9x higher.  ADR-003 section 3.5 forbids combining two technology views, so
    # substituting it would not be a legitimate claim -- but not reporting it would
    # hide the fact that the binding constraint above is a derived density and that
    # the design's own measured silicon does better.
    sensitivity: dict[str, Any] = {"performed": False}
    if DEVICE_LEVEL.exists():
        device = _load(DEVICE_LEVEL)["iso_area_at_the_a100_budget"]
        best = next(
            point
            for point in device["points"]
            if point.get("case") == "best_case" and point.get("fits_in_the_a100_budget")
        )
        measured_bf16_density = float(best["bf16_ops_s_at_iso_area"]) / float(
            best["compute_area_mm2"]
        )
        format_ratio = compute_density["w4a8"] / compute_density["bf16"]
        measured_w4a8_density = measured_bf16_density * format_ratio
        sensitivity = {
            "performed": True,
            "why_separate": (
                "ADR-003 section 3.5 forbids combining two technology views.  The "
                "answer above is entirely N6-derived.  This block is ASAP7-measured "
                "and is a sensitivity, not a claim."
            ),
            "measured_compute_unit_mm2": device["compute_unit_mm2"],
            "measured_compute_unit_lanes": device["compute_unit_lanes"],
            "measured_datapath_clock_hz": best["datapath_clock_hz"],
            "measured_bf16_ops_s_per_mm2": measured_bf16_density,
            "roofline_bf16_ops_s_per_mm2": compute_density["bf16"],
            "measured_over_derived_x": measured_bf16_density / compute_density["bf16"],
            "w4a8_over_bf16_format_ratio": format_ratio,
            "measured_w4a8_ops_s_per_mm2": measured_w4a8_density,
            "source": "results/derived/device_level_iso_area_audit.json",
        }
        fit = cells["Qwen3-8B"]["by_precision"].get("q4p25")
        if fit and fit["fits_inside_a100_die"]:
            ops_per_token = cells["Qwen3-8B"]["operations_per_token"]
            tokens_s = fit["compute_area_mm2"] * measured_w4a8_density / ops_per_token
            tokens_s = min(tokens_s, fit["ours_rom_read_bound_tokens_s"], sweep_ceiling_tokens_s)
            rows = []
            crossover = None
            for row in fit["by_batch"]:
                ratio = tokens_s / row["a100_tokens_s"]
                if ratio < 1.0 and crossover is None:
                    crossover = row["batch"]
                rows.append(
                    {
                        "batch": row["batch"],
                        "ours_tokens_s": tokens_s,
                        "a100_tokens_s": row["a100_tokens_s"],
                        "speed_ratio_ours_over_a100": ratio,
                    }
                )
            sensitivity["qwen3_8b_q4p25_under_measured_compute"] = {
                "tokens_s": tokens_s,
                "by_batch": rows,
                "batch1_speed_ratio": rows[0]["speed_ratio_ours_over_a100"],
                "batch256_speed_ratio": rows[-1]["speed_ratio_ours_over_a100"],
                "crossover_batch_where_a100_overtakes": crossover,
            }

    # ---- the architectural optimisation -------------------------------------
    # Sizing ROM to hold the WHOLE model is one design point, not the best one.  It
    # spends 88% of the usable die on storage and leaves 80.9 mm2 to compute with,
    # which is why the GPU overtakes it past batch 16.  The split is a free variable:
    # hold a fraction f of the weights in on-die ROM and stream the rest from HBM,
    # charging the die for the HBM PHY it then needs.  Sweeping f finds the point
    # that maximises throughput at each batch, which is the question "as good as
    # possible inside 826 mm2" actually asks.
    hbm_per_stack_bytes_s = hbm_bandwidth / 5.0  # A100 80GB is five HBM2e stacks
    device_level = _load(DEVICE_LEVEL)["inputs"] if DEVICE_LEVEL.exists() else {}
    phy_mm2_per_stack = float(device_level.get("hbm_phy_mm2_per_stack") or 10.0)
    stack_capacity = float(device_level.get("hbm_stack_capacity_bytes") or 16e9)

    def _best_split(weight_bytes: float, ops_per_token: float, fmt: str, batch: int,
                    density: float) -> dict[str, Any]:
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
                # enough stacks to HOLD the streamed weights, at least one
                minimum_stacks = max(1, int(-(-streamed // stack_capacity)))
            if minimum_stacks > MAX_HBM_STACKS:
                # more stacks than the comparator's own die carries: not a die this
                # frame can claim, so the split is inadmissible rather than fast
                continue
            # More stacks buy bandwidth and cost PHY area; the optimiser picks,
            # bounded by what the A100 itself carries so the two dies are comparable.
            for stacks in range(minimum_stacks, MAX_HBM_STACKS + 1):
                if stacks == 0 and streamed > 0:
                    continue
                phy_mm2 = stacks * phy_mm2_per_stack
                compute_mm2 = usable_mm2 - rom_mm2 - phy_mm2
                if compute_mm2 <= 0:
                    continue
                # seconds to produce one batch of tokens
                compute_s = batch * ops_per_token / (compute_mm2 * density)
                rom_s = (
                    batch * rom_bytes / (rom_mm2 * rom_read_bytes_s_per_mm2)
                    if rom_mm2 else 0.0
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
            fmt = EXECUTION_FORMAT[precision]
            density = compute_density[fmt]
            rows = []
            for batch in BATCHES:
                point = _best_split(weight_bytes, ops_per_token, fmt, batch, density)
                if not point:
                    continue
                a100_weight = hbm_bandwidth * batch / weight_bytes
                a100_compute = a100_bf16_ops_s / ops_per_token
                a100_tokens = min(a100_weight, a100_compute)
                # Our side executes w4a8; the A100's committed roof is bf16.  Its
                # published INT8 roof is 2x that, and past the crossover the GPU is
                # compute-bound, so the whole high-batch margin would move.  Both are
                # reported rather than only the favourable one.
                a100_int8 = min(a100_weight, 2.0 * a100_compute)
                rows.append({**point, "batch": batch, "a100_tokens_s": a100_tokens,
                             "speed_ratio_ours_over_a100": point["tokens_s"] / a100_tokens,
                             "a100_tokens_s_at_int8_roof": a100_int8,
                             "speed_ratio_against_int8_roof": point["tokens_s"] / a100_int8})
            if rows:
                optimised[f"{model_name}/{precision}"] = {
                    "by_batch": rows,
                    "worst_ratio": min(r["speed_ratio_ours_over_a100"] for r in rows),
                    "best_ratio": max(r["speed_ratio_ours_over_a100"] for r in rows),
                    "above_parity_at_every_batch": all(
                        r["speed_ratio_ours_over_a100"] >= 1.0 for r in rows
                    ),
                    "worst_ratio_against_int8_roof": min(
                        r["speed_ratio_against_int8_roof"] for r in rows
                    ),
                    "above_parity_at_every_batch_against_int8_roof": all(
                        r["speed_ratio_against_int8_roof"] >= 1.0 for r in rows
                    ),
                }

    # Symmetry check.  A ratio is only meaningful if BOTH machines can serve the
    # model at this budget.  The A100 has 80 GB of HBM, and a model whose weights
    # exceed that cannot be served by one A100 at all -- so "our design does not
    # fit" is only a shortfall when the comparator does fit.  Recorded for every
    # row rather than only where it is convenient.
    symmetry: dict[str, Any] = {}
    for model_name, cell in cells.items():
        for precision, entry in cell["by_precision"].items():
            weight_bytes = entry["stored_weight_bytes"]
            a100_can = weight_bytes <= a100_hbm_capacity
            # Our side's real criterion is the OPTIMISED split, not the all-ROM
            # fit: sizing ROM to the whole model is one design point and the
            # sweep above finds better ones that stream most of the weights.
            ours_can = f"{model_name}/{precision}" in optimised
            symmetry[f"{model_name}/{precision}"] = {
                "stored_weight_bytes": weight_bytes,
                "a100_hbm_capacity_bytes": a100_hbm_capacity,
                "a100_can_serve_on_one_device": a100_can,
                "ours_has_an_admissible_split": ours_can,
                "ours_fits_as_all_rom": entry["fits_inside_a100_die"],
                "comparison_is_meaningful": bool(a100_can and ours_can),
                "verdict": (
                    "both fit: the ratio means something"
                    if a100_can and ours_can
                    else "NEITHER machine can serve this model at this budget: the "
                    "A100's 80 GB of HBM cannot hold the weights and our 826 mm2 "
                    "cannot either, so the comparison is vacuous rather than lost"
                    if not a100_can and not ours_can
                    else "only the A100 fits: this is a real shortfall on our side"
                    if a100_can
                    else "only ours fits: the A100 cannot serve this model on one "
                    "device, so there is no comparator to match"
                ),
            }

    fitting = [
        (model, precision, entry)
        for model, cell in cells.items()
        for precision, entry in cell["by_precision"].items()
        if entry["fits_inside_a100_die"]
    ]

    record = {
        "schema": SCHEMA,
        "question": (
            "inside the A100's own 826 mm2 -- not at matched silicon area -- does a "
            "ROM design that holds a whole model exist, and what does it deliver "
            "against the one A100 that occupies the same silicon?"
        ),
        "producer": {"tool": TOOL, "git": {"commit": _git_commit()}},
        "area_budget": {
            "a100_die_area_mm2": A100_DIE_AREA_MM2,
            "overhead_fraction": overhead_fraction,
            "interconnect_fraction": interconnect_fraction,
            "usable_area_mm2": usable_mm2,
            "policy": policy_note,
            "policy_source": "the committed quantised-variant design records' own area_split_per_device",
        },
        "technology": {
            "rom_capacity_bytes_per_mm2": rom_bytes_per_mm2,
            "rom_capacity_grade": derivations["rom_capacity_bits_per_mm2"]["grade"],
            "rom_read_bytes_s_per_mm2": rom_read_bytes_s_per_mm2,
            "rom_read_grade": derivations["rom_read_bytes_s_per_mm2"]["grade"],
            "compute_ops_s_per_mm2": compute_density,
            "rom_array_sweep_ceiling_tokens_s": sweep_ceiling_tokens_s,
            "source": "results/roofline/n6_vs_a100/analytical.json technology_derivations",
        },
        "a100_comparator": {
            "hbm_bandwidth_bytes_s": hbm_bandwidth,
            "bf16_dense_ops_s": a100_bf16_ops_s,
            "hbm_capacity_bytes": a100_hbm_capacity,
            "die_area_mm2": A100_DIE_AREA_MM2,
            "evidence": a100["evidence"],
            "roof_choice": (
                "the committed facts carry the A100's bf16 dense roof and no INT8 "
                "roof, so bf16 is what the compute-bound ceiling uses.  The A100's "
                "published INT8 roof is 2x its bf16 roof, which would DOUBLE the "
                "GPU's compute-bound ceiling and halve every ratio past the "
                "crossover.  Stated because it moves the answer against us."
            ),
        },
        "cells": cells,
        "both_sides_must_fit": {
            "what": (
                "a ratio at a fixed area budget is only meaningful if BOTH machines "
                "can serve the model there.  The A100 has 80 GB of HBM; a model "
                "whose weights exceed it cannot be served by one A100 at any of "
                "these precisions, so our not fitting is not a shortfall against a "
                "comparator that does not fit either."
            ),
            "per_model": symmetry,
        },
        "optimised_rom_hbm_split": {
            "what": (
                "sizing ROM to the whole model is one design point, not the best.  "
                "Holding a fraction of the weights on-die and streaming the rest "
                "from HBM -- charging the die for the HBM PHY it then needs -- is a "
                "free variable, and this sweeps it at every batch to find the point "
                "that maximises throughput inside the same 826 mm2."
            ),
            "hbm_phy_mm2_per_stack": phy_mm2_per_stack,
            "hbm_phy_grade": "assumed",
            "hbm_bytes_s_per_stack": hbm_per_stack_bytes_s,
            "max_hbm_stacks": MAX_HBM_STACKS,
            "max_hbm_stacks_basis": (
                "the A100 80GB carries five HBM2e stacks.  Our die is charged PHY "
                "area per stack but the beachfront that hosts it is not modelled, so "
                "the count is capped at the comparator's own rather than left free"
            ),
            "points": optimised,
        },
        "cross_check_against_committed_design": cross_check,
        "measured_compute_density_sensitivity": sensitivity,
        "answer": {
            "designs_that_fit": [
                {"model": m, "precision": p, "rom_area_mm2": e["rom_area_mm2"],
                 "compute_area_mm2": e["compute_area_mm2"],
                 "batch1_speed_ratio": e["batch1_speed_ratio"],
                 "batch256_speed_ratio": e["batch256_speed_ratio"],
                 "crossover_batch": e["crossover_batch_where_a100_overtakes"]}
                for m, p, e in fitting
            ],
            "count_that_fit": len(fitting),
            "count_considered": sum(len(c["by_precision"]) for c in cells.values()),
        },
        "not_a_claim": [
            "not an RTL measurement and not a simulation: this is the committed "
            "analytical roofline evaluated at a 826 mm2 area budget",
            "the ROM capacity density is graded 'derived' and the SRAM capacity "
            "density it is built beside is graded 'assumed'; a ROM array that "
            "misses its density target moves every area here",
            "the crossover batch is where the GPU overtakes us on THROUGHPUT.  It "
            "says nothing about latency, where a design that never reads weights "
            "off-die keeps its advantage at every batch",
            "one A100 is charged for its die only.  Its HBM stacks are real silicon "
            "that this frame does not charge it for, and charging them would move "
            "the comparison in our favour",
        ],
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w") as handle:
        json.dump(record, handle, indent=1, sort_keys=True)
        handle.write("\n")
    print(f"wrote {args.output}")
    for model, precision, entry in fitting:
        print(
            f"  FITS  {model}/{precision}: ROM {entry['rom_area_mm2']:.1f} mm2, "
            f"compute {entry['compute_area_mm2']:.1f} mm2, "
            f"batch1 {entry['batch1_speed_ratio']:.2f}x, "
            f"batch256 {entry['batch256_speed_ratio']:.2f}x, "
            f"crossover at batch {entry['crossover_batch_where_a100_overtakes']}"
        )
    for model, cell in cells.items():
        for precision, entry in cell["by_precision"].items():
            if not entry["fits_inside_a100_die"]:
                print(
                    f"  no fit {model}/{precision}: needs "
                    f"{entry['rom_area_mm2']:,.0f} mm2 ({entry['shortfall_factor_x']:.2f}x)"
                )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
