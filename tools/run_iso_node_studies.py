#!/usr/bin/env python3
"""Run the N7/A100 and leading-node/B300 inference studies.

The two configurations are loaded and reported independently.  This script does
not merge envelopes, retarget an N7 result to Blackwell, or infer a missing
technology multiplier from either study's output.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import replace
import hashlib
import io
import json
import math
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from opentallas.analytical import AnalyticalSimulator, OperatingPoint  # noqa: E402
from opentallas.config import load_architecture_envelopes  # noqa: E402
from opentallas.deployment import deployment_model  # noqa: E402
from opentallas.operations import operation_inventory  # noqa: E402
from opentallas.schema import (  # noqa: E402
    ArchitectureProfile,
    HardwareProfile,
    ModelProfile,
    SimulationRequest,
)
from opentallas.workload import kv_traffic, weight_traffic  # noqa: E402


STUDIES = {
    "n7_architecture_attribution": ROOT
    / "configs"
    / "hardware"
    / "n7_architecture_attribution.json",
    "leading_node_market": ROOT
    / "configs"
    / "hardware"
    / "leading_node_market.json",
}
MODEL_PATHS = {
    "DeepSeek-V4-Flash-0731": ROOT
    / "configs"
    / "models"
    / "deepseek-v4-flash-0731.json",
    "DeepSeek-V4-Pro-0813": ROOT
    / "configs"
    / "models"
    / "deepseek-v4-pro-0813.json",
}
CONTEXTS = (8_192, 32_768, 200_000, 1_000_000)
BATCHES = (1, 8, 32, 64)
B300_FP32_ROOF_SWEEP_OPS_S_PER_DEVICE = (
    19.5e12,
    45e12,
    90e12,
    180e12,
)
OUTPUT_ROOT = ROOT / "results" / "iso-node"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _finite(value: float) -> float | None:
    return value if math.isfinite(value) else None


def _json_metric(point: OperatingPoint, key: str) -> dict[str, Any]:
    raw = point.metrics[key]
    if not isinstance(raw, str):
        raise TypeError(f"metric {key} is not JSON text")
    decoded = json.loads(raw)
    if not isinstance(decoded, dict):
        raise TypeError(f"metric {key} did not decode to an object")
    return decoded


def _traffic(point: OperatingPoint) -> dict[str, float]:
    if not point.feasible or point.aggregate_tokens_s <= 0:
        return {
            "deployed_weight_read_bytes_s": 0.0,
            "kv_read_bytes_s": 0.0,
            "kv_write_bytes_s": 0.0,
            "kv_total_bytes_s": 0.0,
            "hbm_total_bytes_s": 0.0,
            "rom_array_bytes_s": 0.0,
            "sram_weight_bytes_s": 0.0,
            "sram_kv_bytes_s": 0.0,
            "tensor_operations_s": 0.0,
        }
    interval = point.step_interval_s
    weight = float(point.metrics["C1_weight_bytes_per_step"]) / interval
    read = (
        float(point.metrics["C2_kv_read_bytes_per_user_token"])
        * float(point.metrics["C2_kv_read_amplification"])
        * point.aggregate_tokens_s
    )
    write = (
        float(point.metrics["C2_kv_write_bytes_per_user_token"])
        * point.aggregate_tokens_s
    )
    kv_total = read + write
    weight_tech = str(point.metrics["weight_storage_technology"])
    kv_tech = str(point.metrics["kv_storage_technology"])
    hbm = (weight if weight_tech.startswith("HBM") else 0.0) + (
        kv_total if kv_tech.startswith("HBM") else 0.0
    )
    return {
        "deployed_weight_read_bytes_s": weight,
        "kv_read_bytes_s": read,
        "kv_write_bytes_s": write,
        "kv_total_bytes_s": kv_total,
        "hbm_total_bytes_s": hbm,
        "rom_array_bytes_s": weight if point.architecture_kind == "rom" else 0.0,
        "sram_weight_bytes_s": weight if point.architecture_kind == "sram" else 0.0,
        "sram_kv_bytes_s": kv_total if point.architecture_kind == "sram" else 0.0,
        "tensor_operations_s": (
            float(point.metrics["C5_tensor_operations_per_user_position"])
            * point.aggregate_tokens_s
        ),
    }


def _compact(
    point: OperatingPoint,
    *,
    official_weight_bytes_per_step: float,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "model": point.model,
        "architecture": point.architecture,
        "architecture_kind": point.architecture_kind,
        "model_deployment_policy": point.metrics["model_deployment_policy"],
        "weight_storage_technology": point.metrics["weight_storage_technology"],
        "kv_storage_technology": point.metrics["kv_storage_technology"],
        "storage_capacity_policy": point.metrics["storage_capacity_policy"],
        "storage_bandwidth_policy": point.metrics["storage_bandwidth_policy"],
        "context_tokens": point.context_tokens,
        "batch_size": point.batch_size,
        "feasible": point.feasible,
        "infeasible_reasons": list(point.infeasible_reasons),
        "stages": point.stages,
        "resident_users_required": int(
            float(point.metrics["C7_C8_resident_users_required"])
        ),
        "max_concurrent_users": point.max_concurrent_users,
        "max_batch_per_stage": int(
            float(point.metrics["C7_C8_max_batch_per_stage"])
        ),
        "official_packed_weight_bytes_per_step": official_weight_bytes_per_step,
        "deployed_weight_bytes_per_step": float(
            point.metrics["C1_weight_bytes_per_step"]
        ),
        "kv_read_bytes_per_user_token": float(
            point.metrics["C2_kv_read_bytes_per_user_token"]
        ),
        "kv_write_bytes_per_user_token": float(
            point.metrics["C2_kv_write_bytes_per_user_token"]
        ),
        "kv_read_amplification": float(point.metrics["C2_kv_read_amplification"]),
        "tensor_operations_per_user_token": float(
            point.metrics["C5_tensor_operations_per_user_position"]
        ),
        "operations_per_user_token_by_format": _json_metric(
            point, "C5_operations_per_user_position_by_format"
        ),
        "compute_paths": _json_metric(point, "C5_compute_paths"),
        "step_interval_s": _finite(point.step_interval_s),
        "per_user_token_latency_s": _finite(point.per_user_token_latency_s),
        "aggregate_tokens_s": point.aggregate_tokens_s,
        "per_user_tokens_s": point.per_user_tokens_s,
        "partial_tco_per_million_tokens": _finite(point.partial_tco_per_million_tokens),
        "power_w": point.power_w,
        "thermal_scale": float(point.metrics["thermal_scale"]),
        "raw_interval_before_thermal_s": (
            point.step_interval_s / float(point.metrics["thermal_scale"])
        ),
        "dynamic_power_w_before_throttle": float(
            point.metrics["dynamic_power_w_before_throttle"]
        ),
        "steady_operating_power_w": float(
            point.metrics["steady_operating_power_w"]
        ),
        "binding_constraint": point.binding_constraint,
        "component_times_s": point.component_times_s,
        "stage_balance_efficiency": float(
            point.metrics["C11_stage_balance_efficiency"]
        ),
        "communication_model": point.metrics["C6_communication_model"],
        "allreduce_events_per_layer": float(
            point.metrics["C6_allreduce_events_per_layer"]
        ),
        "cross_stage_payload_bytes_per_user_step": float(
            point.metrics["C10_cross_stage_payload_bytes_per_user_step"]
        ),
    }
    for key in (
        "C6_topology",
        "C6_event_latency_s",
        "C6_layer_service_time_after_sync_derate_s",
        "C6_propagation_cycles_per_direction",
        "C6_reduction_serialization_cycles_per_event",
        "C6_result_serialization_cycles_per_event",
    ):
        if key in point.metrics:
            result[key.removeprefix("C6_")] = point.metrics[key]
    result.update(_traffic(point))
    return result


def _architecture_summary(arch: ArchitectureProfile) -> dict[str, Any]:
    clock = arch.clock_efficiency * arch.defect_repair_efficiency
    return {
        "name": arch.name,
        "kind": arch.kind,
        "device_count": arch.device_count,
        "weight_storage_technology": arch.weight_storage_technology,
        "kv_storage_technology": arch.kv_storage_technology,
        "storage_capacity_policy": arch.storage_capacity_policy,
        "storage_bandwidth_policy": arch.storage_bandwidth_policy,
        "model_deployment_policy": arch.model_deployment_policy,
        "raw_weight_capacity_bytes_per_device": arch.weight_capacity_bytes_per_device,
        "raw_kv_capacity_bytes_per_device": arch.kv_capacity_bytes_per_device,
        "usable_weight_capacity_bytes_per_device": (
            arch.weight_capacity_bytes_per_device
            * (arch.hbm_capacity_utilization if arch.kind == "gpu" else 1.0)
        ),
        "usable_kv_capacity_bytes_per_device": (
            arch.kv_capacity_bytes_per_device * arch.hbm_capacity_utilization
        ),
        "raw_weight_bandwidth_bytes_s_per_device": (
            arch.weight_bandwidth_bytes_s_per_device
        ),
        "raw_kv_bandwidth_bytes_s_per_device": arch.kv_bandwidth_bytes_s_per_device,
        "effective_weight_bandwidth_bytes_s_per_device": (
            arch.weight_bandwidth_bytes_s_per_device
            * arch.weight_bandwidth_efficiency
            * clock
        ),
        "effective_kv_bandwidth_bytes_s_per_device": (
            arch.kv_bandwidth_bytes_s_per_device
            * arch.kv_bandwidth_efficiency
            * clock
        ),
        "compute_roofs_ops_s_per_device": arch.compute_roofs_ops_s_per_device,
        "compute_efficiency": arch.compute_efficiency,
        "load_balance_efficiency": arch.load_balance_efficiency,
        "clock_efficiency": arch.clock_efficiency,
        "defect_repair_efficiency": arch.defect_repair_efficiency,
        "effective_clock_multiplier": clock,
        "sync_efficiency": arch.sync_efficiency,
        "pipeline_efficiency": arch.pipeline_efficiency,
        "cost_per_device": arch.cost_per_device,
        "power_w_per_device": arch.power_w_per_device,
        "cooling_limit_w_per_device": arch.cooling_limit_w_per_device,
        "evidence": arch.evidence,
    }


def _resource_utilizations(
    point: dict[str, Any],
    architecture: dict[str, Any],
    model: dict[str, Any],
) -> dict[str, float]:
    """Return modeled service occupancies at the achieved final interval.

    GPU weight and KV transfers share HBM and are serial in the analytical
    model, so their occupancy is the sum of their component service times. ROM
    and SRAM profiles expose separate weight and KV banks and report each
    service independently. These are model occupancies, not measured counters.
    """

    if not point["feasible"] or point["aggregate_tokens_s"] <= 0:
        return {
            "weight_or_shared_hbm": 0.0,
            "kv": 0.0,
            "compute": 0.0,
            "cooling": 0.0,
        }
    used_devices = (
        architecture["device_count"]
        if architecture["kind"] == "gpu"
        else point["stages"]
    )
    interval = point["step_interval_s"]
    components = point["component_times_s"]
    weight_service = next(
        (
            float(components[key])
            for key in (
                "gpu_weight_memory_C3",
                "rom_full_array_read_C4",
                "sram_weight_banks_C4",
            )
            if key in components
        ),
        0.0,
    )
    kv_service = float(
        components.get("kv_memory_C2", components.get("kv_beachfront_C8", 0.0))
    )
    if architecture["kind"] == "gpu":
        weight_or_shared_hbm = (weight_service + kv_service) / interval
    else:
        weight_or_shared_hbm = weight_service / interval
    return {
        "weight_or_shared_hbm": weight_or_shared_hbm,
        "kv": kv_service / interval,
        "compute": float(components.get("compute_C5", 0.0)) / interval,
        "cooling": point["power_w"]
        / (used_devices * architecture["cooling_limit_w_per_device"]),
    }


def _consistency_audit(result: dict[str, Any]) -> dict[str, Any]:
    """Check generated identities and independent physical upper bounds."""

    errors: list[str] = []
    checks = 0
    architectures = {
        architecture["name"]: architecture
        for architecture in result["architecture_summaries"]
    }
    models = {model["model"]: model for model in result["model_summaries"]}
    seen: set[tuple[str, str, int, int]] = set()
    maxima = {
        "weight_or_shared_hbm": 0.0,
        "kv": 0.0,
        "compute": 0.0,
        "cooling": 0.0,
    }

    def check(condition: bool, message: str) -> None:
        nonlocal checks
        checks += 1
        if not condition:
            errors.append(message)

    def close(actual: float, expected: float) -> bool:
        return math.isclose(actual, expected, rel_tol=1e-9, abs_tol=1e-9)

    for point in result["points"]:
        key = (
            point["model"],
            point["architecture"],
            point["context_tokens"],
            point["batch_size"],
        )
        check(key not in seen, f"duplicate point {key}")
        seen.add(key)
        check(point["step_interval_s"] is not None, f"missing interval {key}")
        if not point["feasible"]:
            check(point["aggregate_tokens_s"] == 0.0, f"infeasible throughput {key}")
            check(point["per_user_tokens_s"] == 0.0, f"infeasible user rate {key}")
            check(
                point["partial_tco_per_million_tokens"] is None,
                f"infeasible TCO {key}",
            )
            continue

        interval = point["step_interval_s"]
        latency = point["per_user_token_latency_s"]
        check(interval > 0, f"non-positive interval {key}")
        check(latency is not None and latency > 0, f"non-positive latency {key}")
        check(
            close(point["aggregate_tokens_s"], point["batch_size"] / interval),
            f"aggregate throughput identity {key}",
        )
        check(
            close(point["per_user_tokens_s"], 1.0 / latency),
            f"per-user throughput identity {key}",
        )
        check(
            latency + 1e-15 >= point["stages"] * interval,
            f"pipeline latency below stages*interval {key}",
        )
        check(
            point["resident_users_required"] <= point["max_concurrent_users"],
            f"resident capacity exceeded {key}",
        )
        expected_weight_rate = point["deployed_weight_bytes_per_step"] / interval
        expected_kv_read = (
            point["kv_read_bytes_per_user_token"]
            * point["kv_read_amplification"]
            * point["aggregate_tokens_s"]
        )
        expected_kv_write = (
            point["kv_write_bytes_per_user_token"] * point["aggregate_tokens_s"]
        )
        check(
            close(point["deployed_weight_read_bytes_s"], expected_weight_rate),
            f"weight-rate identity {key}",
        )
        check(close(point["kv_read_bytes_s"], expected_kv_read), f"KV-read identity {key}")
        check(
            close(point["kv_write_bytes_s"], expected_kv_write),
            f"KV-write identity {key}",
        )
        check(
            close(
                point["tensor_operations_s"],
                point["tensor_operations_per_user_token"]
                * point["aggregate_tokens_s"],
            ),
            f"operation-rate identity {key}",
        )
        utilization = _resource_utilizations(
            point, architectures[point["architecture"]], models[point["model"]]
        )
        for resource, value in utilization.items():
            maxima[resource] = max(maxima[resource], value)
            check(value <= 1.0 + 1e-9, f"{resource} ceiling exceeded {key}: {value}")
        check(
            interval + 1e-15 >= max(point["component_times_s"].values()),
            f"interval below exposed component floor {key}",
        )

    expected_points = (
        len(result["model_summaries"])
        * len(result["inputs"]["contexts"])
        * len(result["inputs"]["required_batches"])
        * len(result["architecture_summaries"])
    )
    check(len(result["points"]) == expected_points, "point matrix is incomplete")
    return {
        "status": "pass" if not errors else "fail",
        "checks_evaluated": checks,
        "errors": errors,
        "maximum_observed_resource_utilization": maxima,
        "scope": [
            "Generated arithmetic identities and loose published/configured ceilings only.",
            "A passing audit is not evidence for ROM macro timing, simultaneous full-array activity, NoC timing, power delivery, package, yield, or model accuracy.",
        ],
    }


def _best(
    rows: list[dict[str, Any]], key: str, *, minimize: bool = False
) -> dict[str, Any] | None:
    feasible = [row for row in rows if row["feasible"]]
    if not feasible:
        return None
    return (min if minimize else max)(feasible, key=lambda row: row[key])


def _ratio(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator is None or denominator <= 0:
        return None
    return numerator / denominator


def _b300_fp32_sensitivity(
    *,
    models: list[ModelProfile],
    gpus: list[ArchitectureProfile],
    simulator: AnalyticalSimulator,
    points: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Sweep the undisclosed B300 full-FP32 roof at the central 200K points."""

    central = _central_name("leading_node_market")
    central_points = {
        (point["model"], point["batch_size"]): point
        for point in points
        if point["architecture"] == central and point["context_tokens"] == 200_000
    }
    rows: list[dict[str, Any]] = []
    for model in models:
        operations = operation_inventory(model, 200_000)
        fp32_fraction = (
            operations.operations_by_format.get("fp32_x_fp32", 0.0)
            / operations.total_tensor_operations
        )
        for batch in BATCHES:
            rom_point = central_points[(model.name, batch)]
            for roof in B300_FP32_ROOF_SWEEP_OPS_S_PER_DEVICE:
                candidates: list[tuple[ArchitectureProfile, OperatingPoint]] = []
                for gpu in gpus:
                    roofs = dict(gpu.compute_roofs_ops_s_per_device)
                    roofs["fp32_x_fp32"] = roof
                    variant = replace(
                        gpu,
                        name=f"{gpu.name}-FP32-sweep-{roof:.0f}",
                        compute_roofs_ops_s_per_device=roofs,
                    )
                    point = simulator.simulate(
                        model,
                        variant,
                        SimulationRequest(context_tokens=200_000, batch_size=batch),
                    )
                    if point.feasible:
                        candidates.append((gpu, point))
                if not candidates:
                    rows.append(
                        {
                            "model": model.name,
                            "context_tokens": 200_000,
                            "batch_size": batch,
                            "fp32_roof_ops_s_per_gpu": roof,
                            "fp32_fraction_of_tensor_operations": fp32_fraction,
                            "fastest_gpu_architecture": None,
                            "fastest_gpu_per_user_tokens_s": None,
                            "fastest_gpu_binding_constraint": None,
                            "central_rom_per_user_tokens_s": rom_point[
                                "per_user_tokens_s"
                            ],
                            "central_rom_to_gpu_speed_ratio": None,
                        }
                    )
                    continue
                fastest_gpu, fastest_point = max(
                    candidates, key=lambda candidate: candidate[1].per_user_tokens_s
                )
                rows.append(
                    {
                        "model": model.name,
                        "context_tokens": 200_000,
                        "batch_size": batch,
                        "fp32_roof_ops_s_per_gpu": roof,
                        "fp32_fraction_of_tensor_operations": fp32_fraction,
                        "fastest_gpu_architecture": fastest_gpu.name,
                        "fastest_gpu_per_user_tokens_s": fastest_point.per_user_tokens_s,
                        "fastest_gpu_binding_constraint": (
                            fastest_point.binding_constraint
                        ),
                        "central_rom_per_user_tokens_s": rom_point[
                            "per_user_tokens_s"
                        ],
                        "central_rom_to_gpu_speed_ratio": _ratio(
                            rom_point["per_user_tokens_s"],
                            fastest_point.per_user_tokens_s,
                        ),
                    }
                )
    return rows


def _simulate_study(study_id: str, config_path: Path) -> dict[str, Any]:
    gpus, wafers, metadata = load_architecture_envelopes(config_path)
    if not gpus or not wafers:
        raise ValueError(f"{study_id} needs GPU and wafer profiles")
    models = [ModelProfile.load(path) for path in MODEL_PATHS.values()]
    simulator = AnalyticalSimulator(HardwareProfile(gpus[0], wafers[0]))
    cache: dict[tuple[str, int, int, str], OperatingPoint] = {}

    def simulate(
        model: ModelProfile, arch: ArchitectureProfile, context: int, batch: int
    ) -> OperatingPoint:
        key = (model.name, context, batch, arch.name)
        if key not in cache:
            cache[key] = simulator.simulate(
                model,
                arch,
                SimulationRequest(context_tokens=context, batch_size=batch),
            )
        return cache[key]

    points: list[dict[str, Any]] = []
    comparisons: list[dict[str, Any]] = []
    capacity_endpoints: list[dict[str, Any]] = []
    model_summaries: list[dict[str, Any]] = []

    for model in models:
        context_summaries: list[dict[str, Any]] = []
        for context in CONTEXTS:
            packed_kv = kv_traffic(model, context)
            packed_b1_weight = weight_traffic(model, 1).total_bytes
            operations = operation_inventory(model, context)
            context_summaries.append(
                {
                    "context_tokens": context,
                    "official_packed_weight_bytes_B1": packed_b1_weight,
                    "official_packed_kv_read_bytes_per_token": packed_kv.read_bytes,
                    "official_packed_kv_write_bytes_per_token": packed_kv.write_bytes,
                    "official_packed_weight_to_kv_read_ratio_B1": (
                        packed_b1_weight / packed_kv.read_bytes
                    ),
                    "official_packed_weight_to_kv_total_ratio_B1": (
                        packed_b1_weight / packed_kv.total_transfer_bytes
                    ),
                    "tensor_operations_per_token": operations.total_tensor_operations,
                    "operations_per_token_by_format": operations.operations_by_format,
                }
            )

            for batch in BATCHES:
                official_weight = weight_traffic(model, batch).total_bytes
                gpu_rows: list[dict[str, Any]] = []
                wafer_rows: list[dict[str, Any]] = []
                for arch in [*gpus, *wafers]:
                    point = simulate(model, arch, context, batch)
                    row = _compact(
                        point,
                        official_weight_bytes_per_step=official_weight,
                    )
                    points.append(row)
                    (gpu_rows if arch.kind == "gpu" else wafer_rows).append(row)

                fastest_gpu = _best(gpu_rows, "per_user_tokens_s")
                cheapest_gpu = _best(
                    [
                        row
                        for row in gpu_rows
                        if row["partial_tco_per_million_tokens"] is not None
                    ],
                    "partial_tco_per_million_tokens",
                    minimize=True,
                )
                for wafer_row in wafer_rows:
                    resident_batch = wafer_row["resident_users_required"]
                    resident_gpu_rows: list[dict[str, Any]] = []
                    for gpu in gpus:
                        resident_point = simulate(model, gpu, context, resident_batch)
                        resident_gpu_rows.append(
                            _compact(
                                resident_point,
                                official_weight_bytes_per_step=weight_traffic(
                                    model, resident_batch
                                ).total_bytes,
                            )
                        )
                    resident_fastest = _best(
                        resident_gpu_rows, "per_user_tokens_s"
                    )
                    comparisons.append(
                        {
                            "model": model.name,
                            "context_tokens": context,
                            "batch_per_stage": batch,
                            "wafer_architecture": wafer_row["architecture"],
                            "wafer_kind": wafer_row["architecture_kind"],
                            "wafer_stages": wafer_row["stages"],
                            "wafer_resident_users": wafer_row[
                                "resident_users_required"
                            ],
                            "wafer_feasible": wafer_row["feasible"],
                            "wafer_per_user_tokens_s": wafer_row[
                                "per_user_tokens_s"
                            ],
                            "wafer_aggregate_tokens_s": wafer_row[
                                "aggregate_tokens_s"
                            ],
                            "wafer_partial_tco_per_million_tokens": wafer_row[
                                "partial_tco_per_million_tokens"
                            ],
                            "wafer_binding_constraint": wafer_row[
                                "binding_constraint"
                            ],
                            "fastest_same_batch_gpu": (
                                None if fastest_gpu is None else fastest_gpu["architecture"]
                            ),
                            "fastest_same_batch_gpu_per_user_tokens_s": (
                                None
                                if fastest_gpu is None
                                else fastest_gpu["per_user_tokens_s"]
                            ),
                            "same_batch_per_user_speed_ratio": _ratio(
                                wafer_row["per_user_tokens_s"]
                                if wafer_row["feasible"]
                                else None,
                                None
                                if fastest_gpu is None
                                else fastest_gpu["per_user_tokens_s"],
                            ),
                            "cheapest_same_batch_gpu": (
                                None
                                if cheapest_gpu is None
                                else cheapest_gpu["architecture"]
                            ),
                            "cheapest_same_batch_gpu_partial_tco_per_million_tokens": (
                                None
                                if cheapest_gpu is None
                                else cheapest_gpu["partial_tco_per_million_tokens"]
                            ),
                            "partial_tco_ratio_vs_cheapest_same_batch_gpu": _ratio(
                                None
                                if cheapest_gpu is None
                                else cheapest_gpu[
                                    "partial_tco_per_million_tokens"
                                ],
                                wafer_row["partial_tco_per_million_tokens"]
                                if wafer_row["feasible"]
                                else None,
                            ),
                            "fastest_resident_matched_gpu": (
                                None
                                if resident_fastest is None
                                else resident_fastest["architecture"]
                            ),
                            "fastest_resident_matched_gpu_per_user_tokens_s": (
                                None
                                if resident_fastest is None
                                else resident_fastest["per_user_tokens_s"]
                            ),
                            "resident_matched_per_user_speed_ratio": _ratio(
                                wafer_row["per_user_tokens_s"]
                                if wafer_row["feasible"]
                                else None,
                                None
                                if resident_fastest is None
                                else resident_fastest["per_user_tokens_s"],
                            ),
                        }
                    )

        for arch in [*gpus, *wafers]:
            for context in CONTEXTS:
                base = simulate(model, arch, context, 1)
                max_batch = int(float(base.metrics["C7_C8_max_batch_per_stage"]))
                endpoint = (
                    simulate(model, arch, context, max_batch)
                    if max_batch > 0
                    else base
                )
                capacity_endpoints.append(
                    _compact(
                        endpoint,
                        official_weight_bytes_per_step=weight_traffic(
                            model, max(1, max_batch)
                        ).total_bytes,
                    )
                )

        deployment_summaries = []
        for policy in sorted(
            {arch.model_deployment_policy for arch in [*gpus, *wafers]}
        ):
            deployed = deployment_model(model, policy)
            deployment_summaries.append(
                {
                    "policy": policy,
                    "checkpoint_bytes": deployed.checkpoint_bytes,
                    "decode_dense_weight_bytes": deployed.dense_weight_bytes,
                    "decode_routed_weight_bytes": deployed.routed_weight_bytes,
                    "kv_cache_policy": deployed.metadata.get("kv_cache_policy"),
                }
            )
        model_summaries.append(
            {
                "model": model.name,
                "source_repo": model.source_repo,
                "source_revision": model.source_revision,
                "official_checkpoint_bytes": model.checkpoint_bytes,
                "official_dense_weight_bytes": model.dense_weight_bytes,
                "official_routed_weight_bytes": model.routed_weight_bytes,
                "dense_compute_format": model.dense_compute_format,
                "routed_compute_format": model.routed_compute_format,
                "deployment_representations": deployment_summaries,
                "contexts": context_summaries,
            }
        )

    uncertainty_bands: list[dict[str, Any]] = []
    for model in models:
        for context in CONTEXTS:
            for batch in BATCHES:
                rows = [
                    row
                    for row in comparisons
                    if row["model"] == model.name
                    and row["context_tokens"] == context
                    and row["batch_per_stage"] == batch
                    and row["wafer_kind"] == "rom"
                ]
                feasible = [row for row in rows if row["wafer_feasible"]]
                all_feasible = len(feasible) == len(rows)
                feasible_ratios = [
                    row["same_batch_per_user_speed_ratio"]
                    for row in feasible
                    if row["same_batch_per_user_speed_ratio"] is not None
                ]
                uncertainty_bands.append(
                    {
                        "model": model.name,
                        "context_tokens": context,
                        "batch_per_stage": batch,
                        "scenario_count": len(rows),
                        "feasible_scenario_count": len(feasible),
                        "rom_per_user_tokens_s_low": (
                            min(row["wafer_per_user_tokens_s"] for row in feasible)
                            if feasible and all_feasible
                            else None
                        ),
                        "rom_per_user_tokens_s_min_feasible": (
                            min(row["wafer_per_user_tokens_s"] for row in feasible)
                            if feasible
                            else None
                        ),
                        "rom_per_user_tokens_s_high": (
                            max(row["wafer_per_user_tokens_s"] for row in feasible)
                            if feasible
                            else None
                        ),
                        "same_batch_speed_ratio_low": (
                            min(feasible_ratios)
                            if feasible_ratios and all_feasible
                            else None
                        ),
                        "same_batch_speed_ratio_min_feasible": (
                            min(feasible_ratios) if feasible_ratios else None
                        ),
                        "same_batch_speed_ratio_high": (
                            max(feasible_ratios) if feasible_ratios else None
                        ),
                        "bindings": sorted(
                            {row["wafer_binding_constraint"] for row in rows}
                        ),
                    }
                )

    b300_fp32_sensitivity = (
        _b300_fp32_sensitivity(
            models=models,
            gpus=gpus,
            simulator=simulator,
            points=points,
        )
        if study_id == "leading_node_market"
        else []
    )

    result = {
        "schema_version": 1,
        "study_id": study_id,
        "comparison_contract": metadata["comparison_contract"],
        "methodology": "docs/METHODOLOGY.md",
        "inputs": {
            "hardware_config": str(config_path.relative_to(ROOT)),
            "hardware_sha256": _sha256(config_path),
            "models": {
                name: {
                    "path": str(path.relative_to(ROOT)),
                    "sha256": _sha256(path),
                }
                for name, path in MODEL_PATHS.items()
            },
            "contexts": list(CONTEXTS),
            "required_batches": list(BATCHES),
            "counting_convention": "one multiply plus one add equals two operations",
            "cost_scope": "partial TCO only: assumed acquisition/NRE amortization plus active electricity",
        },
        "architecture_summaries": [
            _architecture_summary(arch) for arch in [*gpus, *wafers]
        ],
        "technology_derivations": metadata.get("derivations", {}),
        "model_summaries": model_summaries,
        "points": points,
        "comparisons": comparisons,
        "uncertainty_bands": uncertainty_bands,
        "b300_fp32_roof_sensitivity": b300_fp32_sensitivity,
        "capacity_endpoints": capacity_endpoints,
        "interpretation_boundary": [
            "Conservative/central/aggressive are deterministic envelopes, not confidence intervals.",
            "No target-node ROM macro, full-wafer read path, package, power, yield, or model throughput has been measured.",
            "A100 is bounded by two explicit deployments: exact offline BF16-resident expansion and a GPU-favorable packed-HBM/on-consumption-BF16 ceiling whose unpack cost is unmeasured and omitted. Neither receives native FP8/MXFP4 execution.",
            "B300 uses official packed checkpoint storage and public low-precision arithmetic roofs; its undisclosed full-FP32 roof is explicitly assumed and swept.",
            "Same-batch and resident-session-matched comparisons are both emitted because a wafer pipeline has batch times stages resident sessions.",
        ],
    }
    architectures_by_name = {
        architecture["name"]: architecture
        for architecture in result["architecture_summaries"]
    }
    models_by_name = {
        model["model"]: model for model in result["model_summaries"]
    }
    for point in result["points"]:
        point["resource_utilization"] = _resource_utilizations(
            point,
            architectures_by_name[point["architecture"]],
            models_by_name[point["model"]],
        )
    result["consistency_audit"] = _consistency_audit(result)
    return result


def _fmt_rate(value: float | None) -> str:
    return "—" if value is None else f"{value:,.1f}"


def _fmt_ratio(value: float | None) -> str:
    return "—" if value is None else f"{value:.2f}×"


def _fmt_tco(value: float | None) -> str:
    return "—" if value is None else f"{value:.4f}"


def _fmt_bytes(value: float) -> str:
    return f"{value/1e9:,.1f} GB"


def _fmt_ms(value: float | None) -> str:
    return "—" if value is None else f"{value * 1e3:,.4f}"


def _fmt_percent(value: float | None) -> str:
    return "—" if value is None else f"{value * 100:,.1f}%"


def _central_name(study_id: str) -> str:
    return (
        "ROM-wafer-N7-HBM2e-central"
        if study_id == "n7_architecture_attribution"
        else "ROM-wafer-N4-class-HBM3e-central"
    )


def _aggressive_name(study_id: str) -> str:
    return (
        "ROM-wafer-N7-HBM2e-aggressive"
        if study_id == "n7_architecture_attribution"
        else "ROM-wafer-N4-class-HBM3e-aggressive"
    )


def render_report(result: dict[str, Any]) -> str:
    study_id = result["study_id"]
    central = _central_name(study_id)
    lines = [
        f"# {study_id.replace('_', ' ').title()}",
        "",
        f"> {result['comparison_contract']}",
        "",
        "This is an evidence-bounded decode simulation, not a fabricated-silicon or",
        "product-performance claim. `Low` and `high` below are deterministic hardware",
        "envelopes, not statistical confidence intervals.",
        "",
        "## Storage and execution contract",
        "",
        "| Architecture | Devices available | Weight store | Mutable KV store | Weight capacity/device | KV capacity/device | Raw weight BW/device | Raw KV BW/device | Deployment |",
        "|---|---:|---|---|---:|---:|---:|---:|---|",
    ]
    for arch in result["architecture_summaries"]:
        lines.append(
            f"| {arch['name']} | {arch['device_count']} | "
            f"{arch['weight_storage_technology']} | {arch['kv_storage_technology']} | "
            f"{_fmt_bytes(arch['raw_weight_capacity_bytes_per_device'])} | "
            f"{_fmt_bytes(arch['raw_kv_capacity_bytes_per_device'])} | "
            f"{arch['raw_weight_bandwidth_bytes_s_per_device']/1e12:,.2f} TB/s | "
            f"{arch['raw_kv_bandwidth_bytes_s_per_device']/1e12:,.2f} TB/s | "
            f"{arch['model_deployment_policy']} |"
        )

    lines.extend(
        [
            "",
            "GPU HBM capacity and bandwidth are shared by weights and KV. ROM weight",
            "capacity/bandwidth and mutable HBM KV capacity/bandwidth are physically",
            "separate. The SRAM-rich control uses a static 70% weight / 30% KV split.",
            "",
            "## Exact model work and deployment storage",
            "",
            "| Model | Official checkpoint | Deployment representation | Resident bytes | 200K tensor ops/token | Dense / routed format |",
            "|---|---:|---|---:|---:|---|",
        ]
    )
    for model in result["model_summaries"]:
        ops_200k = next(
            context["tensor_operations_per_token"]
            for context in model["contexts"]
            if context["context_tokens"] == 200_000
        )
        for deployment in model["deployment_representations"]:
            lines.append(
                f"| {model['model']} | {_fmt_bytes(model['official_checkpoint_bytes'])} | "
                f"{deployment['policy']} | {_fmt_bytes(deployment['checkpoint_bytes'])} | "
                f"{ops_200k/1e9:,.1f} Gop | {model['dense_compute_format']} / "
                f"{model['routed_compute_format']} |"
            )

    audit = result["consistency_audit"]
    maxima = audit["maximum_observed_resource_utilization"]
    lines.extend(
        [
            "",
            "## Mechanical consistency audit",
            "",
            "| Status | Checks | Max weight/shared-HBM service | Max KV service | Max compute service | Max cooling |",
            "|---|---:|---:|---:|---:|---:|",
            f"| {audit['status'].upper()} | {audit['checks_evaluated']:,} | "
            f"{_fmt_percent(maxima['weight_or_shared_hbm'])} | "
            f"{_fmt_percent(maxima['kv'])} | "
            f"{_fmt_percent(maxima['compute'])} | "
            f"{_fmt_percent(maxima['cooling'])} |",
            "",
            "The service columns are component-time occupancy divided by the final",
            "thermal-adjusted interval. GPU weight and KV time are added because",
            "they share HBM; ROM/SRAM weight and KV services remain separate.",
        ]
    )
    lines.extend(f"- {item}" for item in audit["scope"])

    lines.extend(
        [
            "",
            "## Central-envelope 200K results",
            "",
            "`GPU` is the fastest feasible allowed GPU cluster at the same active",
            "microbatch. The resident-matched ratio instead runs the GPU at `batch ×",
            "wafer stages`. Ratios above one favor the wafer.",
            "Partial TCO uses assumed acquisition cost, NRE allocation, utilization,",
            "electricity, and PUE. It is shown with enough precision to audit the",
            "arithmetic, but it is not a measured vendor-cost or profitability result.",
            "",
            "| Model | B/stage | Stages | Residents | ROM user tok/s | GPU | GPU user tok/s | Same-B ratio | Resident-matched ratio | ROM $/M tok | Bind |",
            "|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---|",
        ]
    )
    central_rows = [
        row
        for row in result["comparisons"]
        if row["wafer_architecture"] == central
        and row["context_tokens"] == 200_000
    ]
    for row in central_rows:
        lines.append(
            f"| {row['model']} | {row['batch_per_stage']} | {row['wafer_stages']} | "
            f"{row['wafer_resident_users']} | {_fmt_rate(row['wafer_per_user_tokens_s'])} | "
            f"{row['fastest_same_batch_gpu'] or 'infeasible'} | "
            f"{_fmt_rate(row['fastest_same_batch_gpu_per_user_tokens_s'])} | "
            f"{_fmt_ratio(row['same_batch_per_user_speed_ratio'])} | "
            f"{_fmt_ratio(row['resident_matched_per_user_speed_ratio'])} | "
            f"{_fmt_tco(row['wafer_partial_tco_per_million_tokens'])} | "
            f"{row['wafer_binding_constraint']} |"
        )

    component_architectures = (central, _aggressive_name(study_id))
    component_rows = [
        point
        for point in result["points"]
        if point["architecture"] in component_architectures
        and point["context_tokens"] == 200_000
    ]
    component_rows.sort(
        key=lambda point: (
            point["model"],
            component_architectures.index(point["architecture"]),
            point["batch_size"],
        )
    )
    lines.extend(
        [
            "",
            "## ROM component timing and occupancy at 200K",
            "",
            "Times are seconds of bottleneck-stage service expressed in milliseconds.",
            "Weight, KV, and compute may overlap; the layer collective is serialized;",
            "pipeline efficiency and any thermal scaling produce the final interval.",
            "The cross-stage entry is the initiation-interval serialization floor, not",
            "the full end-to-end propagation latency. Occupancies are modeled service",
            "time divided by the final interval, not silicon performance counters.",
            "",
            "| Model | Envelope | B/stage | Stages | Final interval ms | User latency ms | Weight ms | KV ms | Compute ms | Collective ms | Cross-stage ms | Weight util | KV util | Compute util | Thermal × | Bind |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
        ]
    )
    for point in component_rows:
        components = point["component_times_s"]
        weight_time = next(
            (
                components[key]
                for key in ("rom_full_array_read_C4", "sram_weight_banks_C4")
                if key in components
            ),
            None,
        )
        utilization = point["resource_utilization"]
        envelope = (
            "central" if point["architecture"] == central else "aggressive"
        )
        lines.append(
            f"| {point['model']} | {envelope} | {point['batch_size']} | "
            f"{point['stages']} | {_fmt_ms(point['step_interval_s'])} | "
            f"{_fmt_ms(point['per_user_token_latency_s'])} | "
            f"{_fmt_ms(weight_time)} | "
            f"{_fmt_ms(components.get('kv_beachfront_C8'))} | "
            f"{_fmt_ms(components.get('compute_C5'))} | "
            f"{_fmt_ms(components.get('collective_floor_C6'))} | "
            f"{_fmt_ms(components.get('cross_stage_link_C10'))} | "
            f"{_fmt_percent(utilization['weight_or_shared_hbm'])} | "
            f"{_fmt_percent(utilization['kv'])} | "
            f"{_fmt_percent(utilization['compute'])} | "
            f"{point['thermal_scale']:.3f} | {point['binding_constraint']} |"
        )

    if result["b300_fp32_roof_sensitivity"]:
        lines.extend(
            [
                "",
                "## B300 full-FP32 roof sensitivity at 200K",
                "",
                "The checked NVIDIA DGX B300 datasheet and system guide do not",
                "publish a full-FP32 roof. The configured 90 TOP/s value is assumed.",
                "The 19.5-TOP/s endpoint is A100's published full-FP32 rate used only",
                "as a deliberately low stress case; 45 and 180 TOP/s are half/double",
                "sweep points, not vendor claims. Each cell is the fastest feasible",
                "B300 cluster's per-user token rate at the stated active batch.",
                "",
                "| Model | B | FP32 op share | 19.5 TOP/s | 45 TOP/s | 90 TOP/s | 180 TOP/s | Fastest cluster(s) | Binding(s) | Central ROM/GPU ratio range |",
                "|---|---:|---:|---:|---:|---:|---:|---|---|---:|",
            ]
        )
        sensitivity = result["b300_fp32_roof_sensitivity"]
        for model_name in sorted({row["model"] for row in sensitivity}):
            for batch in BATCHES:
                rows = [
                    row
                    for row in sensitivity
                    if row["model"] == model_name and row["batch_size"] == batch
                ]
                rows.sort(key=lambda row: row["fp32_roof_ops_s_per_gpu"])
                rates = [
                    _fmt_rate(row["fastest_gpu_per_user_tokens_s"]) for row in rows
                ]
                ratios = [
                    row["central_rom_to_gpu_speed_ratio"]
                    for row in rows
                    if row["central_rom_to_gpu_speed_ratio"] is not None
                ]
                ratio_range = (
                    "—"
                    if not ratios
                    else f"{min(ratios):.2f}×–{max(ratios):.2f}×"
                )
                architectures = sorted(
                    {
                        row["fastest_gpu_architecture"]
                        for row in rows
                        if row["fastest_gpu_architecture"] is not None
                    }
                )
                bindings = sorted(
                    {
                        row["fastest_gpu_binding_constraint"]
                        for row in rows
                        if row["fastest_gpu_binding_constraint"] is not None
                    }
                )
                lines.append(
                    f"| {model_name} | {batch} | "
                    f"{rows[0]['fp32_fraction_of_tensor_operations'] * 100:.3f}% | "
                    f"{' | '.join(rates)} | {', '.join(architectures)} | "
                    f"{', '.join(bindings)} | {ratio_range} |"
                )

    lines.extend(
        [
            "",
            "## Central-envelope achieved byte rates at 200K",
            "",
            "These are rates implied by achieved token throughput, not raw hardware",
            "bandwidth. ROM arrays carry only weights; HBM carries only mutable KV on",
            "the proposed wafer. GPU HBM carries both deployed weights and KV.",
            "",
            "| Model | B | Architecture | Deployed weight read | KV read+write | Total HBM | Tensor operations |",
            "|---|---:|---|---:|---:|---:|---:|",
        ]
    )
    points_by_key = {
        (
            point["model"],
            point["context_tokens"],
            point["batch_size"],
            point["architecture"],
        ): point
        for point in result["points"]
    }
    for comparison in central_rows:
        architectures = [central]
        if comparison["fastest_same_batch_gpu"] is not None:
            architectures.append(comparison["fastest_same_batch_gpu"])
        for architecture in architectures:
            point = points_by_key[
                (
                    comparison["model"],
                    comparison["context_tokens"],
                    comparison["batch_per_stage"],
                    architecture,
                )
            ]
            lines.append(
                f"| {point['model']} | {point['batch_size']} | {point['architecture']} | "
                f"{point['deployed_weight_read_bytes_s']/1e12:,.2f} TB/s | "
                f"{point['kv_total_bytes_s']/1e12:,.3f} TB/s | "
                f"{point['hbm_total_bytes_s']/1e12:,.2f} TB/s | "
                f"{point['tensor_operations_s']/1e15:,.2f} Pop/s |"
            )

    lines.extend(
        [
            "",
            "## ROM uncertainty bands across context and batch",
            "",
            "An `infeasible–high` interval means at least one deterministic hardware",
            "envelope cannot place the checkpoint or resident KV sessions. Numeric",
            "lows are reported only when every envelope is feasible.",
            "",
            "| Model | Context | B/stage | Feasible envelopes | ROM user tok/s low–high | Same-B ROM/GPU low–high | Binding terms across envelopes |",
            "|---|---:|---:|---:|---:|---:|---|",
        ]
    )
    for band in result["uncertainty_bands"]:
        low = band["rom_per_user_tokens_s_low"]
        high = band["rom_per_user_tokens_s_high"]
        ratio_low = band["same_batch_speed_ratio_low"]
        ratio_high = band["same_batch_speed_ratio_high"]
        feasible_count = band["feasible_scenario_count"]
        scenario_count = band["scenario_count"]
        if feasible_count == 0:
            rate_interval = "infeasible"
            ratio_interval = "infeasible"
        elif feasible_count < scenario_count:
            rate_interval = f"infeasible–{_fmt_rate(high)}"
            ratio_interval = f"infeasible–{_fmt_ratio(ratio_high)}"
        else:
            rate_interval = f"{_fmt_rate(low)}–{_fmt_rate(high)}"
            ratio_interval = f"{_fmt_ratio(ratio_low)}–{_fmt_ratio(ratio_high)}"
        lines.append(
            f"| {band['model']} | {band['context_tokens']:,} | "
            f"{band['batch_per_stage']} | {feasible_count}/{scenario_count} | "
            f"{rate_interval} | {ratio_interval} | "
            f"{', '.join(band['bindings'])} |"
        )

    if study_id == "n7_architecture_attribution":
        lines.extend(
            [
                "",
                "## SRAM-rich N7 control at 200K",
                "",
                "This is an area-scaled Graphcore-style storage control, not a Graphcore",
                "product claim. It illustrates the capacity cost of replacing ROM with",
                "writable on-wafer SRAM while holding the general spatial model similar.",
                "",
                "| Model | B/stage | Stages | Feasible | User tok/s | Bind/reason |",
                "|---|---:|---:|---|---:|---|",
            ]
        )
        for row in result["comparisons"]:
            if (
                row["wafer_kind"] == "sram"
                and row["context_tokens"] == 200_000
            ):
                lines.append(
                    f"| {row['model']} | {row['batch_per_stage']} | "
                    f"{row['wafer_stages']} | {row['wafer_feasible']} | "
                    f"{_fmt_rate(row['wafer_per_user_tokens_s'])} | "
                    f"{row['wafer_binding_constraint']} |"
                )

    lines.extend(
        [
            "",
            "## Interpretation boundary",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in result["interpretation_boundary"])
    lines.extend(
        [
            "- Partial TCO is not a vendor-price or profitability claim. It excludes",
            "  staffing, financing, networking, facilities, maintenance, and spares.",
            "- Prefill and speculative decoding are intentionally absent from this",
            "  decode-only attribution study; adding either requires a separately",
            "  evidence-backed execution/deployment profile.",
            "- Huawei Tau/韬 scaling and 3-D integration are not applied as numerical",
            "  multipliers. Any vertical-ROM study must be a separate parameterized",
            "  thermal/yield/interconnect scenario under `docs/METHODOLOGY.md`.",
            "",
        ]
    )
    return "\n".join(lines)


CSV_FIELDS = (
    "model",
    "architecture",
    "architecture_kind",
    "model_deployment_policy",
    "context_tokens",
    "batch_size",
    "feasible",
    "stages",
    "resident_users_required",
    "max_batch_per_stage",
    "official_packed_weight_bytes_per_step",
    "deployed_weight_bytes_per_step",
    "kv_read_bytes_per_user_token",
    "kv_write_bytes_per_user_token",
    "tensor_operations_per_user_token",
    "step_interval_s",
    "per_user_token_latency_s",
    "aggregate_tokens_s",
    "per_user_tokens_s",
    "deployed_weight_read_bytes_s",
    "kv_read_bytes_s",
    "kv_write_bytes_s",
    "hbm_total_bytes_s",
    "rom_array_bytes_s",
    "sram_weight_bytes_s",
    "sram_kv_bytes_s",
    "tensor_operations_s",
    "partial_tco_per_million_tokens",
    "power_w",
    "binding_constraint",
)


def render_csv(result: dict[str, Any]) -> str:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=CSV_FIELDS, lineterminator="\n")
    writer.writeheader()
    for point in result["points"]:
        writer.writerow({field: point.get(field) for field in CSV_FIELDS})
    return output.getvalue()


def run_all(output_root: Path = OUTPUT_ROOT) -> dict[str, dict[str, Any]]:
    results: dict[str, dict[str, Any]] = {}
    for study_id, config_path in STUDIES.items():
        result = _simulate_study(study_id, config_path)
        results[study_id] = result
        destination = output_root / study_id
        destination.mkdir(parents=True, exist_ok=True)
        (destination / "analytical.json").write_text(
            json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        (destination / "sweep.csv").write_text(
            render_csv(result), encoding="utf-8", newline=""
        )
        (destination / "REPORT.md").write_text(
            render_report(result).rstrip() + "\n", encoding="utf-8"
        )
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT_ROOT)
    args = parser.parse_args(argv)
    run_all(args.output)
    for study_id in STUDIES:
        print((args.output / study_id / "REPORT.md").resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
