#!/usr/bin/env python3
"""Derive inverse OpenTallas requirements from governed GPU comparators.

The calculation asks what a ROM-based product would have to achieve to equal
or exceed a comparator.  It never treats those requirements as achieved
OpenTallas measurements.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "configs" / "benchmarks" / "local_gpu_break_even.json"
DEFAULT_RESULT_DIR = ROOT / "results" / "gpu" / "break_even"


class BreakEvenError(RuntimeError):
    """Raised when an inverse-analysis input contract is violated."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def strict_json(path: Path) -> dict[str, Any]:
    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise BreakEvenError(f"duplicate JSON key {key!r} in {path}")
            result[key] = value
        return result

    try:
        decoded = json.loads(
            path.read_text(encoding="utf-8"), object_pairs_hook=reject_duplicates
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise BreakEvenError(f"cannot read {path}: {exc}") from exc
    if not isinstance(decoded, dict):
        raise BreakEvenError(f"expected a JSON object in {path}")
    return decoded


def resolve_input(relative: str) -> Path:
    path = (ROOT / relative).resolve()
    try:
        path.relative_to(ROOT)
    except ValueError as exc:
        raise BreakEvenError(f"input escapes repository root: {relative}") from exc
    if not path.is_file():
        raise BreakEvenError(f"required input is missing: {relative}")
    return path


def validate_config(config: dict[str, Any]) -> None:
    block = config.get("break_even")
    if not isinstance(block, dict):
        raise BreakEvenError("config.break_even is required")
    for name in (
        "comparator_inputs",
        "model",
        "comparator_architecture",
        "contexts",
        "batches",
        "throughput_multipliers",
        "rom_area_scenarios",
        "hbm_bandwidth_efficiency",
        "noc_payload_efficiency",
    ):
        if name not in block:
            raise BreakEvenError(f"break_even.{name} is required")
    for efficiency_name in ("hbm_bandwidth_efficiency", "noc_payload_efficiency"):
        efficiency = float(block[efficiency_name])
        if not 0 < efficiency <= 1:
            raise BreakEvenError(f"{efficiency_name} must be in (0,1]")
    multipliers = [float(value) for value in block["throughput_multipliers"]]
    if not multipliers or any(value < 1 for value in multipliers):
        raise BreakEvenError("throughput multipliers must be at least one")
    scenarios = block["rom_area_scenarios"]
    if not isinstance(scenarios, list) or not scenarios:
        raise BreakEvenError("at least one ROM area scenario is required")
    for scenario in scenarios:
        for field in (
            "name",
            "rom_area_fraction",
            "usable_capacity_fraction",
            "weight_bandwidth_efficiency",
        ):
            if field not in scenario:
                raise BreakEvenError(f"ROM area scenario is missing {field}")
        for field in (
            "rom_area_fraction",
            "usable_capacity_fraction",
            "weight_bandwidth_efficiency",
        ):
            value = float(scenario[field])
            if not 0 < value <= 1:
                raise BreakEvenError(
                    f"scenario {scenario['name']} {field} must be in (0,1]"
                )


def validate_comparator_inputs(inputs: dict[str, Any]) -> None:
    if inputs.get("schema_version") != 1:
        raise BreakEvenError("comparator input schema_version must be 1")
    model = inputs.get("model_profile")
    technology = inputs.get("technology")
    comparator = inputs.get("comparator")
    if not isinstance(model, dict) or not isinstance(model.get("name"), str):
        raise BreakEvenError("comparator inputs require a model profile")
    checkpoint = model.get("checkpoint_bytes")
    if (
        not isinstance(checkpoint, int)
        or isinstance(checkpoint, bool)
        or checkpoint <= 0
    ):
        raise BreakEvenError("comparator checkpoint_bytes must be a positive integer")
    if not isinstance(technology, dict):
        raise BreakEvenError("comparator inputs require technology facts")
    for field in ("wafer_area_mm2", "configured_wafer_cooling_limit_w"):
        value = technology.get(field)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise BreakEvenError(f"comparator technology {field} must be numeric")
        if not math.isfinite(float(value)) or float(value) <= 0:
            raise BreakEvenError(f"comparator technology {field} must be positive")
    envelopes = technology.get("rom_envelopes")
    if not isinstance(envelopes, list) or not envelopes:
        raise BreakEvenError("comparator inputs require ROM envelopes")
    if not isinstance(comparator, dict) or not isinstance(
        comparator.get("architecture"), str
    ):
        raise BreakEvenError("comparator inputs require an architecture")
    points = comparator.get("points")
    if not isinstance(points, list) or not points:
        raise BreakEvenError("comparator inputs require points")
    required = {
        "model",
        "architecture",
        "context_tokens",
        "batch_size",
        "feasible",
        "infeasible_reasons",
        "aggregate_tokens_s",
        "deployed_weight_bytes_per_step",
        "kv_read_bytes_per_user_token",
        "kv_write_bytes_per_user_token",
        "kv_storage_bytes_per_user",
        "operations_per_user_token_by_format",
        "tensor_operations_per_user_token",
        "cross_stage_payload_bytes_per_user_step",
        "power_w",
        "binding_constraint",
    }
    for index, point in enumerate(points):
        if not isinstance(point, dict):
            raise BreakEvenError(f"comparator point {index} must be an object")
        missing = required - set(point)
        if missing:
            raise BreakEvenError(
                f"comparator point {index} is missing fields: {sorted(missing)}"
            )
        if point["model"] != model["name"]:
            raise BreakEvenError(f"comparator point {index} model is inconsistent")
        if point["architecture"] != comparator["architecture"]:
            raise BreakEvenError(
                f"comparator point {index} architecture is inconsistent"
            )
        operations = point["operations_per_user_token_by_format"]
        if not isinstance(operations, dict) or not operations:
            raise BreakEvenError(f"comparator point {index} has no format operations")
        operation_total = sum(float(value) for value in operations.values())
        if not math.isclose(
            operation_total,
            float(point["tensor_operations_per_user_token"]),
            rel_tol=1e-12,
        ):
            raise BreakEvenError(
                f"comparator point {index} format operation total is inconsistent"
            )
        aggregate = float(point["aggregate_tokens_s"])
        if bool(point["feasible"]) != (aggregate > 0):
            raise BreakEvenError(
                f"comparator point {index} feasibility and throughput disagree"
            )
        if float(point["kv_storage_bytes_per_user"]) <= 0:
            raise BreakEvenError(
                f"comparator point {index} KV storage must be positive"
            )


def manifest(path: Path) -> dict[str, Any]:
    return {
        "path": str(path.relative_to(ROOT)),
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
    }


def select_points(
    points: list[dict[str, Any]],
    model: str,
    architecture: str,
    contexts: set[int],
    batches: set[int],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows = [
        point
        for point in points
        if point.get("model") == model
        and point.get("architecture") == architecture
        and int(point.get("context_tokens", -1)) in contexts
        and int(point.get("batch_size", -1)) in batches
    ]
    expected = {(context, batch) for context in contexts for batch in batches}
    actual = {(int(row["context_tokens"]), int(row["batch_size"])) for row in rows}
    if len(rows) != len(actual):
        raise BreakEvenError("analytical artifact contains duplicate comparison points")
    missing = expected - actual
    if missing:
        raise BreakEvenError(
            f"analytical artifact is missing points: {sorted(missing)}"
        )
    feasible = [
        row
        for row in rows
        if row.get("feasible") and row.get("aggregate_tokens_s", 0) > 0
    ]
    excluded = [
        {
            "context_tokens": int(row["context_tokens"]),
            "batch_size": int(row["batch_size"]),
            "reason": "comparator point is infeasible in its own governed capacity model",
            "infeasible_reasons": row.get("infeasible_reasons", []),
        }
        for row in rows
        if row not in feasible
    ]
    return sorted(
        feasible, key=lambda row: (row["context_tokens"], row["batch_size"])
    ), excluded


def capacity_requirements(
    checkpoint_bytes: float,
    wafer_area_mm2: float,
    scenarios: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows = []
    for scenario in scenarios:
        area = wafer_area_mm2 * float(scenario["rom_area_fraction"])
        usable_fraction = float(scenario["usable_capacity_fraction"])
        usable_density = checkpoint_bytes / area
        raw_density = usable_density / usable_fraction
        rows.append(
            {
                "scenario": scenario["name"],
                "rom_area_fraction": scenario["rom_area_fraction"],
                "rom_area_mm2": area,
                "usable_capacity_fraction": usable_fraction,
                "required_usable_capacity_bytes": checkpoint_bytes,
                "required_usable_density_bytes_mm2": usable_density,
                "required_usable_density_mbit_mm2": usable_density * 8 / 1e6,
                "required_raw_macro_density_bytes_mm2": raw_density,
                "required_raw_macro_density_mbit_mm2": raw_density * 8 / 1e6,
            }
        )
    return rows


def inverse_threshold(
    point: dict[str, Any],
    multiplier: float,
    kv_storage_bytes_per_user: float,
    checkpoint_bytes: float,
    wafer_area_mm2: float,
    area_scenarios: list[dict[str, Any]],
    hbm_efficiency: float,
    noc_efficiency: float,
    cooling_limit_w: float,
) -> dict[str, Any]:
    comparator_tokens_s = float(point["aggregate_tokens_s"])
    target_tokens_s = comparator_tokens_s * multiplier
    batch = int(point["batch_size"])
    step_rate = target_tokens_s / batch
    step_interval = 1 / step_rate
    effective_weight_bandwidth = (
        float(point["deployed_weight_bytes_per_step"]) * step_rate
    )
    kv_transfer_per_token = float(point["kv_read_bytes_per_user_token"]) + float(
        point["kv_write_bytes_per_user_token"]
    )
    effective_hbm_bandwidth = kv_transfer_per_token * target_tokens_s
    operations_by_format = {
        name: float(value) * target_tokens_s
        for name, value in point["operations_per_user_token_by_format"].items()
    }
    total_operations = (
        float(point["tensor_operations_per_user_token"]) * target_tokens_s
    )
    if not math.isclose(
        sum(operations_by_format.values()), total_operations, rel_tol=1e-12
    ):
        raise BreakEvenError(
            "format-specific operation totals do not match tensor operations"
        )
    comparator_power = float(point["power_w"])
    comparator_energy_token = comparator_power / comparator_tokens_s
    comparator_energy_op = comparator_energy_token / float(
        point["tensor_operations_per_user_token"]
    )
    energy_parity_power = comparator_energy_token * target_tokens_s
    iso_power_energy_token = comparator_power / target_tokens_s
    payload_per_user = float(point["cross_stage_payload_bytes_per_user_step"])
    effective_payload_bandwidth = payload_per_user * target_tokens_s
    area_rows = []
    for scenario in area_scenarios:
        area = wafer_area_mm2 * float(scenario["rom_area_fraction"])
        efficiency = float(scenario["weight_bandwidth_efficiency"])
        raw_bandwidth = effective_weight_bandwidth / efficiency
        area_rows.append(
            {
                "scenario": scenario["name"],
                "rom_area_mm2": area,
                "weight_bandwidth_efficiency": efficiency,
                "required_effective_rom_bandwidth_bytes_s": effective_weight_bandwidth,
                "required_raw_rom_bandwidth_bytes_s": raw_bandwidth,
                "required_raw_rom_bandwidth_density_bytes_s_mm2": raw_bandwidth / area,
            }
        )
    return {
        "context_tokens": int(point["context_tokens"]),
        "batch_size": batch,
        "throughput_multiplier": multiplier,
        "performance_semantics": "equality threshold"
        if multiplier == 1
        else "strict speedup target",
        "comparator_aggregate_tokens_s": comparator_tokens_s,
        "required_aggregate_tokens_s": target_tokens_s,
        "required_step_rate_s": step_rate,
        "maximum_decode_step_interval_s": step_interval,
        "required_usable_rom_capacity_bytes": checkpoint_bytes,
        "required_rom_bandwidth_by_area": area_rows,
        "required_hbm_active_batch_capacity_bytes": kv_storage_bytes_per_user * batch,
        "kv_storage_bytes_per_user": kv_storage_bytes_per_user,
        "required_effective_hbm_bandwidth_bytes_s": effective_hbm_bandwidth,
        "required_raw_hbm_bandwidth_bytes_s": effective_hbm_bandwidth / hbm_efficiency,
        "hbm_bandwidth_efficiency": hbm_efficiency,
        "required_operations_s_by_exact_format": operations_by_format,
        "required_total_tensor_operations_s": total_operations,
        "required_effective_cross_stage_payload_bytes_s": effective_payload_bandwidth,
        "required_raw_cross_stage_payload_bytes_s": effective_payload_bandwidth
        / noc_efficiency,
        "noc_payload_efficiency": noc_efficiency,
        "absolute_maximum_total_serial_service_latency_s": step_interval,
        "serial_latency_semantics": "hard interval ceiling before reserving time for ROM, compute, HBM, reductions, clock margin, or synchronization; not a usable implementation budget",
        "comparator_allocated_power_w": comparator_power,
        "comparator_energy_j_token": comparator_energy_token,
        "maximum_energy_j_tensor_operation_for_energy_parity": comparator_energy_op,
        "maximum_package_power_w_for_energy_parity": energy_parity_power,
        "maximum_energy_j_token_at_comparator_iso_power": iso_power_energy_token,
        "maximum_energy_j_tensor_operation_at_comparator_iso_power": iso_power_energy_token
        / float(point["tensor_operations_per_user_token"]),
        "configured_wafer_cooling_limit_w": cooling_limit_w,
        "energy_parity_power_within_configured_cooling_limit": energy_parity_power
        <= cooling_limit_w,
        "comparator_binding_constraint": point["binding_constraint"],
        "comparator_power_semantics": "governed analytical input, not a local measurement",
    }


def envelope_screen(
    derivations: list[dict[str, Any]],
    checkpoint_bytes: float,
    reference: dict[str, Any],
    area_scenarios: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_order = list(area_scenarios)
    rows = []
    for index, envelope in enumerate(derivations):
        scenario = by_order[index] if index < len(by_order) else None
        raw_required = None
        raw_headroom = None
        if scenario is not None:
            matching = next(
                row
                for row in reference["required_rom_bandwidth_by_area"]
                if row["scenario"] == scenario["name"]
            )
            raw_required = matching["required_raw_rom_bandwidth_bytes_s"]
            raw_headroom = (
                float(envelope["raw_weight_bandwidth_bytes_s"]) / raw_required
            )
        capacity = float(envelope["usable_weight_capacity_bytes"])
        rows.append(
            {
                "envelope": envelope["envelope"],
                "evidence": envelope["density_evidence"],
                "usable_weight_capacity_bytes": capacity,
                "checkpoint_capacity_ratio": capacity / checkpoint_bytes,
                "minimum_capacity_stages": math.ceil(checkpoint_bytes / capacity),
                "one_wafer_checkpoint_fit_under_assumptions": capacity
                >= checkpoint_bytes,
                "raw_weight_bandwidth_bytes_s": envelope[
                    "raw_weight_bandwidth_bytes_s"
                ],
                "reference_required_raw_weight_bandwidth_bytes_s": raw_required,
                "assumption_bandwidth_headroom_ratio": raw_headroom,
                "macro_density_bytes_mm2": envelope["macro_density_bytes_mm2"],
                "hbm_capacity_bytes": envelope["hbm"]["capacity_bytes"],
                "hbm_bandwidth_bytes_s": envelope["hbm"]["bandwidth_bytes_s"],
                "generic_fp8_marketing_derived_ceiling_ops_s": envelope[
                    "fp8_peak_ops_s"
                ],
                "compute_comparison_allowed": False,
                "screen_semantics": "arithmetic headroom under public/assumed envelope inputs; not target-ROM or package validation",
            }
        )
    return rows


def latest_measurement(result_root: Path) -> Path | None:
    candidates = sorted(result_root.glob("*/measurement.json"))
    return candidates[-1] if candidates else None


def local_measurement_summary(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    measurement = strict_json(path)
    if measurement.get("contamination_label") != "shared_contended":
        raise BreakEvenError("local measurement is missing the shared_contended label")
    return {
        "manifest": manifest(path),
        "benchmark_id": measurement.get("benchmark_id"),
        "status": measurement.get("status"),
        "contamination_label": measurement.get("contamination_label"),
        "endpoint_model": measurement.get("selected_endpoint_model"),
        "summary": measurement.get("summary", []),
        "comparison_use": "separate local Qwen service target only; never substituted for the DeepSeek/B300 inverse thresholds",
    }


def find_reference(rows: list[dict[str, Any]], block: dict[str, Any]) -> dict[str, Any]:
    matches = [
        row
        for row in rows
        if row["context_tokens"] == int(block["reference_context"])
        and row["batch_size"] == int(block["reference_batch"])
        and row["throughput_multiplier"]
        == float(block["reference_throughput_multiplier"])
    ]
    if len(matches) != 1:
        raise BreakEvenError("reference inverse threshold is not unique")
    return matches[0]


def build_result(config_path: Path, measurement_path: Path | None) -> dict[str, Any]:
    config = strict_json(config_path)
    validate_config(config)
    block = config["break_even"]
    comparator_path = resolve_input(block["comparator_inputs"])
    inputs = strict_json(comparator_path)
    validate_comparator_inputs(inputs)
    model = inputs["model_profile"]
    technology = inputs["technology"]
    comparator = inputs["comparator"]
    if model["name"] != block["model"]:
        raise BreakEvenError(
            f"model profile {model['name']!r} does not match break-even config"
        )
    if comparator["architecture"] != block["comparator_architecture"]:
        raise BreakEvenError("comparator architecture does not match break-even config")
    points, excluded = select_points(
        comparator["points"],
        block["model"],
        block["comparator_architecture"],
        {int(value) for value in block["contexts"]},
        {int(value) for value in block["batches"]},
    )
    wafer_area = float(technology["wafer_area_mm2"])
    cooling_limit = float(technology["configured_wafer_cooling_limit_w"])
    checkpoint_bytes = float(model["checkpoint_bytes"])
    thresholds = []
    for point in points:
        for multiplier in block["throughput_multipliers"]:
            thresholds.append(
                inverse_threshold(
                    point,
                    float(multiplier),
                    float(point["kv_storage_bytes_per_user"]),
                    checkpoint_bytes,
                    wafer_area,
                    block["rom_area_scenarios"],
                    float(block["hbm_bandwidth_efficiency"]),
                    float(block["noc_payload_efficiency"]),
                    cooling_limit,
                )
            )
    reference = find_reference(thresholds, block)
    capacity = capacity_requirements(
        checkpoint_bytes, wafer_area, block["rom_area_scenarios"]
    )
    return {
        "schema_version": 1,
        "analysis_id": "opentallas-inverse-gpu-break-even-v1",
        "generated_at": utc_now(),
        "status": "requirements_derived_not_achieved",
        "comparison_contract": {
            "model": block["model"],
            "comparator_architecture": block["comparator_architecture"],
            "power_semantics": block["comparison_power_semantics"],
            "speedup_semantics": block["strict_speedup_semantics"],
            "arithmetic": "exact per-format operation requirements retained; no integer-RTL substitution",
        },
        "input_manifests": {
            "runner": manifest(Path(__file__).resolve()),
            "config": manifest(config_path),
            "comparator_inputs": manifest(comparator_path),
        },
        "required_checkpoint_capacity_bytes": checkpoint_bytes,
        "wafer_area_mm2": wafer_area,
        "capacity_requirements_by_rom_area": capacity,
        "reference_threshold": reference,
        "thresholds": thresholds,
        "excluded_comparator_points": excluded,
        "public_assumption_envelope_screen": envelope_screen(
            technology["rom_envelopes"],
            checkpoint_bytes,
            reference,
            block["rom_area_scenarios"],
        ),
        "local_qwen_measurement": local_measurement_summary(measurement_path),
        "claim_boundary": [
            "Every number in this artifact is an inverse requirement or an assumption screen; none is an achieved OpenTallas result.",
            "The DeepSeek/B300 thresholds and local Qwen measurement are separate because they do not execute the same checkpoint.",
            "Public ROM-density and bandwidth anchors do not validate an N4 ROM compiler, PVT margin, simultaneous-array power, or manufacturability.",
            "A generic FP8 ceiling is not evidence that the exact FP8, MXFP4 x FP8, FP4, BF16, and FP32 operation mix is implemented.",
            "Strict performance superiority requires same-model measurement above the equality threshold with accuracy, latency, context, batch, concurrency, power scope, and software stack controlled.",
        ],
    }


def format_rate(value: float) -> str:
    if abs(value) >= 1e15:
        return f"{value / 1e15:.3f} P"
    if abs(value) >= 1e12:
        return f"{value / 1e12:.3f} T"
    if abs(value) >= 1e9:
        return f"{value / 1e9:.3f} G"
    return f"{value:.3f}"


def render_report(result: dict[str, Any]) -> str:
    ref = result["reference_threshold"]
    lines = [
        "# OpenTallas inverse GPU break-even requirements",
        "",
        "> **Outcome:** this report derives what OpenTallas would have to achieve;",
        "> it does not report that OpenTallas achieves it. The DeepSeek/B300 model",
        "> and the local Qwen service observation remain deliberately separate.",
        "",
        "## Reference equality threshold",
        "",
        f"The governed reference is `{result['comparison_contract']['model']}` on",
        f"`{result['comparison_contract']['comparator_architecture']}` at context",
        f"{ref['context_tokens']:,}, batch {ref['batch_size']}. Its analytical target is",
        f"**{ref['required_aggregate_tokens_s']:.3f} aggregate tokens/s**. To claim",
        "higher performance, a same-model measurement must be strictly above this",
        "number under the same comparison contract.",
        "",
        "| Necessary equality requirement | Value |",
        "| --- | ---: |",
        f"| Full usable ROM checkpoint capacity | {ref['required_usable_rom_capacity_bytes'] / 1e9:.3f} GB |",
        f"| Effective active-weight bandwidth | {ref['required_rom_bandwidth_by_area'][0]['required_effective_rom_bandwidth_bytes_s'] / 1e12:.3f} TB/s |",
        f"| Effective mutable-KV bandwidth | {ref['required_effective_hbm_bandwidth_bytes_s'] / 1e9:.3f} GB/s |",
        f"| Minimum active-batch KV capacity | {ref['required_hbm_active_batch_capacity_bytes'] / 1e6:.3f} MB |",
        f"| Exact tensor-operation rate | {ref['required_total_tensor_operations_s'] / 1e12:.3f} TOP/s |",
        f"| Effective cross-stage payload lower bound | {ref['required_effective_cross_stage_payload_bytes_s'] / 1e6:.3f} MB/s |",
        f"| Absolute decode interval ceiling | {ref['maximum_decode_step_interval_s'] * 1e3:.6f} ms |",
        f"| B300 allocated-energy parity | {ref['comparator_energy_j_token']:.6f} J/token |",
        f"| Energy parity per tensor operation | {ref['maximum_energy_j_tensor_operation_for_energy_parity'] * 1e12:.3f} pJ/op |",
        "",
        "The interval ceiling is not a component budget: ROM, arithmetic, HBM, NoC,",
        "clock margin, synchronization, and any pipeline bubbles must fit together.",
        "",
        "## Exact arithmetic requirement at the reference point",
        "",
        "| Format | Required operations/s |",
        "| --- | ---: |",
    ]
    for name, value in sorted(ref["required_operations_s_by_exact_format"].items()):
        lines.append(f"| `{name}` | {format_rate(value)}op/s |")
    lines.extend(
        [
            "",
            "The current public integer-DV RTL does not implement these arithmetic",
            "formats, so this table is an implementation requirement, not compute proof.",
            "",
            "## Capacity density required for one wafer",
            "",
            "| ROM-area scenario | ROM area | Required usable density | Required raw macro density |",
            "| --- | ---: | ---: | ---: |",
        ]
    )
    for row in result["capacity_requirements_by_rom_area"]:
        lines.append(
            f"| `{row['scenario']}` | {row['rom_area_mm2']:,.1f} mm^2 | "
            f"{row['required_usable_density_mbit_mm2']:.3f} Mbit/mm^2 | "
            f"{row['required_raw_macro_density_mbit_mm2']:.3f} Mbit/mm^2 |"
        )
    lines.extend(
        [
            "",
            "Raw density divides by the declared usable-capacity fraction. It still",
            "does not include an N4 compiler result, sense margin, repair layout,",
            "periphery closure, or a foundry-calibrated scaling error bar.",
            "",
            "## Public-assumption envelope screen",
            "",
            "| Envelope | Usable capacity | Minimum stages | One-wafer fit? | Reference raw-BW headroom |",
            "| --- | ---: | ---: | --- | ---: |",
        ]
    )
    for row in result["public_assumption_envelope_screen"]:
        headroom = row["assumption_bandwidth_headroom_ratio"]
        lines.append(
            f"| `{row['envelope']}` | {row['usable_weight_capacity_bytes'] / 1e9:.3f} GB | "
            f"{row['minimum_capacity_stages']} | "
            f"{'yes' if row['one_wafer_checkpoint_fit_under_assumptions'] else 'no'} | "
            f"{headroom:,.1f}x |"
        )
    lines.extend(
        [
            "",
            "This is only arithmetic headroom under public and assumed inputs. Large",
            "array-bandwidth headroom cannot be converted into a performance claim",
            "until simultaneous read activity, power delivery, timing, and exact",
            "arithmetic are implemented and validated.",
            "",
            "## Context, batch, and speedup sensitivity",
            "",
            "| Context | Batch | Target | Aggregate tok/s | Effective ROM BW | Raw HBM BW | Tensor op/s | Iso-power J/token |",
            "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in result["thresholds"]:
        lines.append(
            f"| {row['context_tokens']:,} | {row['batch_size']} | "
            f"{row['throughput_multiplier']:.1f}x | {row['required_aggregate_tokens_s']:.3f} | "
            f"{row['required_rom_bandwidth_by_area'][0]['required_effective_rom_bandwidth_bytes_s'] / 1e12:.3f} TB/s | "
            f"{row['required_raw_hbm_bandwidth_bytes_s'] / 1e9:.3f} GB/s | "
            f"{row['required_total_tensor_operations_s'] / 1e12:.3f} TOP/s | "
            f"{row['maximum_energy_j_token_at_comparator_iso_power']:.6f} |"
        )
    if result["excluded_comparator_points"]:
        lines.extend(
            ["", "Comparator-infeasible points were not assigned thresholds:", ""]
        )
        for row in result["excluded_comparator_points"]:
            lines.append(
                f"- Context {row['context_tokens']:,}, batch {row['batch_size']}."
            )
    lines.extend(["", "## Local Qwen observation", ""])
    local = result["local_qwen_measurement"]
    if local is None:
        lines.append("No local measurement was attached to this generated report.")
    else:
        lines.extend(
            [
                f"Attached run: `{local['benchmark_id']}` ({local['status']},",
                f"`{local['contamination_label']}`). It is shown only as a local Qwen",
                "service target and is not substituted into any DeepSeek threshold.",
                "",
                "| Qwen prompt | Concurrency | Successful requests | Median TTFT | Median E2E | Median completion tok/s E2E |",
                "| ---: | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        for row in local["summary"]:
            lines.append(
                f"| {row['prompt_tokens']} | {row['concurrency']} | "
                f"{row['successful_requests']} | {row['median_ttft_s'] * 1e3:.3f} ms | "
                f"{row['median_end_to_end_s'] * 1e3:.3f} ms | "
                f"{row['median_completion_tokens_s_end_to_end']:.3f} |"
            )
    lines.extend(["", "## Claim boundary", ""])
    lines.extend(f"- {item}" for item in result["claim_boundary"])
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--measurement", type=Path)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_RESULT_DIR)
    arguments = parser.parse_args()
    config_path = arguments.config.resolve()
    measurement = (
        arguments.measurement.resolve()
        if arguments.measurement
        else latest_measurement(DEFAULT_RESULT_DIR.parent / "local_rtx_pro_6000")
    )
    result = build_result(config_path, measurement)
    output_dir = arguments.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    analytical_path = output_dir / "break_even.json"
    report_path = output_dir / "REPORT.md"
    analytical_path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    report_path.write_text(render_report(result), encoding="utf-8")
    try:
        analytical_display = analytical_path.relative_to(ROOT)
        report_display = report_path.relative_to(ROOT)
    except ValueError:
        analytical_display = analytical_path
        report_display = report_path
    print(f"wrote {analytical_display}")
    print(f"wrote {report_display}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BreakEvenError as exc:
        raise SystemExit(f"break-even error: {exc}") from exc
