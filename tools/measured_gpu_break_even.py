#!/usr/bin/env python3
"""Derive OpenTallas requirements from a governed measured local GPU service."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import statistics
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = (
    ROOT / "configs" / "benchmarks" / "local_gpu_measured_break_even_v2.json"
)
DEFAULT_MEASUREMENT_ROOT = (
    ROOT / "results" / "gpu" / "local_rtx_pro_6000_measured_break_even"
)
DEFAULT_RESULT_DIR = ROOT / "results" / "gpu" / "measured_break_even"


class MeasuredBreakEvenError(RuntimeError):
    """Raised when measured break-even evidence violates its contract."""


def strict_json(path: Path) -> dict[str, Any]:
    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise MeasuredBreakEvenError(f"duplicate JSON key {key!r} in {path}")
            result[key] = value
        return result

    try:
        value = json.loads(
            path.read_text(encoding="utf-8"), object_pairs_hook=reject_duplicates
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise MeasuredBreakEvenError(f"cannot read {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise MeasuredBreakEvenError(f"expected an object in {path}")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def manifest(path: Path) -> dict[str, Any]:
    try:
        name = str(path.resolve().relative_to(ROOT))
    except ValueError:
        name = str(path.resolve())
    return {
        "path": name,
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
    }


def resolve_repository_input(path_text: str) -> Path:
    path = (ROOT / path_text).resolve()
    try:
        path.relative_to(ROOT)
    except ValueError as exc:
        raise MeasuredBreakEvenError(
            f"configured input escapes repository root: {path_text}"
        ) from exc
    if not path.is_file():
        raise MeasuredBreakEvenError(f"configured input is missing: {path_text}")
    return path


def finite_positive(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise MeasuredBreakEvenError(f"{label} must be numeric")
    result = float(value)
    if not math.isfinite(result) or result <= 0:
        raise MeasuredBreakEvenError(f"{label} must be finite and positive")
    return result


def validate_config(config: dict[str, Any]) -> None:
    if config.get("schema_version") != 1:
        raise MeasuredBreakEvenError(
            "measured benchmark config schema_version must be 1"
        )
    block = config.get("measured_break_even")
    if not isinstance(block, dict):
        raise MeasuredBreakEvenError("config.measured_break_even is required")
    for field in (
        "model_profile_lock",
        "reference_prompt_tokens",
        "reference_concurrency",
        "throughput_multipliers",
        "rom_area_scenarios",
        "strict_speedup_semantics",
    ):
        if field not in block:
            raise MeasuredBreakEvenError(f"measured_break_even.{field} is required")
    multipliers = block["throughput_multipliers"]
    if (
        not isinstance(multipliers, list)
        or not multipliers
        or any(
            finite_positive(value, "throughput multiplier") < 1 for value in multipliers
        )
    ):
        raise MeasuredBreakEvenError("throughput multipliers must be at least one")
    scenarios = block["rom_area_scenarios"]
    if not isinstance(scenarios, list) or not scenarios:
        raise MeasuredBreakEvenError("at least one ROM area scenario is required")
    names = []
    for index, scenario in enumerate(scenarios):
        if not isinstance(scenario, dict):
            raise MeasuredBreakEvenError(f"ROM area scenario {index} must be an object")
        for field in (
            "name",
            "wafer_area_mm2",
            "rom_area_fraction",
            "usable_capacity_fraction",
        ):
            if field not in scenario:
                raise MeasuredBreakEvenError(f"ROM area scenario {index} lacks {field}")
        names.append(str(scenario["name"]))
        finite_positive(scenario["wafer_area_mm2"], f"scenario {index} wafer area")
        for field in ("rom_area_fraction", "usable_capacity_fraction"):
            value = finite_positive(scenario[field], f"scenario {index} {field}")
            if value > 1:
                raise MeasuredBreakEvenError(
                    f"scenario {index} {field} must not exceed one"
                )
    if len(names) != len(set(names)):
        raise MeasuredBreakEvenError("ROM area scenario names must be unique")


def validate_model_lock(lock: dict[str, Any]) -> None:
    if lock.get("schema_version") != 1 or lock.get("status") != "pass":
        raise MeasuredBreakEvenError("model profile lock must be schema 1 and passing")
    model = lock.get("model")
    checkpoint = lock.get("checkpoint")
    decode = lock.get("ordinary_text_decode")
    if not all(isinstance(item, dict) for item in (model, checkpoint, decode)):
        raise MeasuredBreakEvenError("model lock lacks model/checkpoint/decode blocks")
    role_bytes = checkpoint.get("role_bytes")
    dtype_bytes = checkpoint.get("dtype_bytes")
    if not isinstance(role_bytes, dict) or not isinstance(dtype_bytes, dict):
        raise MeasuredBreakEvenError("model lock lacks role or dtype byte accounting")
    full = int(checkpoint["full_checkpoint_payload_bytes"])
    if full <= 0 or sum(int(value) for value in role_bytes.values()) != full:
        raise MeasuredBreakEvenError("model lock role bytes do not sum to checkpoint")
    if sum(int(value) for value in dtype_bytes.values()) != full:
        raise MeasuredBreakEvenError("model lock dtype bytes do not sum to checkpoint")
    if int(decode["active_immutable_bytes_per_token"]) != int(
        decode["dense_active_bytes_per_token"]
    ) + int(decode["selected_expert_bytes_per_token"]):
        raise MeasuredBreakEvenError("model lock active-byte identity failed")
    operations = decode.get("matrix_operations_lower_bound_per_token_by_format")
    if not isinstance(operations, dict) or sum(
        int(value) for value in operations.values()
    ) != int(decode["matrix_operations_lower_bound_per_token"]):
        raise MeasuredBreakEvenError("model lock operation identity failed")
    finite_positive(
        decode.get("kv_bytes_per_context_token"), "KV bytes per context token"
    )


def expected_sweep(config: dict[str, Any]) -> dict[tuple[int, int], int]:
    result: dict[tuple[int, int], int] = {}
    for point in config.get("sweep", []):
        key = (int(point["prompt_tokens"]), int(point["concurrency"]))
        if key in result:
            raise MeasuredBreakEvenError(f"duplicate configured sweep point {key}")
        result[key] = int(point["repetitions"])
    return result


def validate_measurement(
    measurement: dict[str, Any],
    config: dict[str, Any],
    config_path: Path,
    model_lock: dict[str, Any],
) -> None:
    if measurement.get("schema_version") != 1 or measurement.get("status") != "pass":
        raise MeasuredBreakEvenError("measurement must be schema 1 and passing")
    if measurement.get("benchmark_id") != config.get("benchmark_id"):
        raise MeasuredBreakEvenError("measurement benchmark_id differs from config")
    if measurement.get("contamination_label") != "shared_contended":
        raise MeasuredBreakEvenError("measurement must remain shared_contended")
    selected = measurement.get("selected_endpoint_model")
    if (
        not isinstance(selected, dict)
        or selected.get("root") != model_lock["model"]["endpoint_root"]
    ):
        raise MeasuredBreakEvenError(
            "measurement endpoint root differs from model lock"
        )
    embedded_config = measurement.get("config")
    if (
        not isinstance(embedded_config, dict)
        or embedded_config.get("contents") != config
    ):
        raise MeasuredBreakEvenError(
            "measurement embedded config differs from current config"
        )
    if embedded_config.get("sha256") != sha256_file(config_path):
        raise MeasuredBreakEvenError("measurement config hash is stale")
    stability = measurement.get("endpoint_stability")
    if not isinstance(stability, dict) or not stability or not all(stability.values()):
        raise MeasuredBreakEvenError(
            "one or more endpoint identities changed during measurement"
        )
    version_stability = measurement.get("endpoint_version_stability")
    if (
        not isinstance(version_stability, dict)
        or not version_stability
        or not all(version_stability.values())
    ):
        raise MeasuredBreakEvenError(
            "one or more endpoint runtime versions changed during measurement"
        )
    if (
        config["contamination_policy"]["whole_gpu_energy_attribution_allowed"]
        is not False
    ):
        raise MeasuredBreakEvenError(
            "measurement config must forbid energy attribution"
        )
    waves = measurement.get("waves")
    if not isinstance(waves, list) or not waves:
        raise MeasuredBreakEvenError("measurement contains no waves")
    grouped: Counter[tuple[int, int]] = Counter()
    expected_completion = int(config["request"]["completion_tokens"])
    for wave in waves:
        if not isinstance(wave, dict):
            raise MeasuredBreakEvenError("measurement wave is not an object")
        key = (int(wave["prompt_tokens"]), int(wave["concurrency"]))
        grouped[key] += 1
        requests = wave.get("requests")
        if not isinstance(requests, list) or len(requests) != key[1]:
            raise MeasuredBreakEvenError(
                f"wave {key} request count differs from concurrency"
            )
        for request in requests:
            if request.get("status") != "pass":
                raise MeasuredBreakEvenError(
                    f"wave {key} contains a nonpassing request"
                )
            if int(request.get("prompt_tokens", -1)) != key[0]:
                raise MeasuredBreakEvenError(f"wave {key} prompt usage differs")
            if int(request.get("completion_tokens", -1)) != expected_completion:
                raise MeasuredBreakEvenError(f"wave {key} completion usage differs")
            finite_positive(request.get("end_to_end_s"), f"wave {key} request latency")
    if dict(grouped) != expected_sweep(config):
        raise MeasuredBreakEvenError(
            f"measurement wave inventory {dict(grouped)} differs from configured "
            f"{expected_sweep(config)}"
        )


def observed_scenarios(
    measurement: dict[str, Any], model_lock: dict[str, Any]
) -> list[dict[str, Any]]:
    grouped: dict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)
    kv_per_context = int(
        model_lock["ordinary_text_decode"]["kv_bytes_per_context_token"]
    )
    for wave in measurement["waves"]:
        key = (int(wave["prompt_tokens"]), int(wave["concurrency"]))
        requests = wave["requests"]
        completion_tokens = sum(
            int(request["completion_tokens"]) for request in requests
        )
        service_span = max(float(request["end_to_end_s"]) for request in requests)
        aggregate_rate = completion_tokens / service_span
        grouped[key].append(
            {
                "repetition": int(wave["repetition"]),
                "aggregate_completion_tokens_s_end_to_end": aggregate_rate,
                "service_span_s": service_span,
                "median_request_ttft_s": statistics.median(
                    float(request["ttft_s"]) for request in requests
                ),
                "median_request_end_to_end_s": statistics.median(
                    float(request["end_to_end_s"]) for request in requests
                ),
                "completion_tokens": completion_tokens,
            }
        )
    rows = []
    completion_per_request = int(
        measurement["config"]["contents"]["request"]["completion_tokens"]
    )
    for (prompt, concurrency), repetitions in sorted(grouped.items()):
        rates = [row["aggregate_completion_tokens_s_end_to_end"] for row in repetitions]
        average_prior_context = prompt + (completion_per_request - 1) / 2
        logical_kv_read_per_token = average_prior_context * kv_per_context
        rows.append(
            {
                "prompt_tokens": prompt,
                "completion_tokens_per_request": completion_per_request,
                "concurrency": concurrency,
                "repetitions": len(repetitions),
                "median_aggregate_completion_tokens_s_end_to_end": statistics.median(
                    rates
                ),
                "minimum_aggregate_completion_tokens_s_end_to_end": min(rates),
                "maximum_aggregate_completion_tokens_s_end_to_end": max(rates),
                "median_request_ttft_s": statistics.median(
                    row["median_request_ttft_s"] for row in repetitions
                ),
                "median_request_end_to_end_s": statistics.median(
                    row["median_request_end_to_end_s"] for row in repetitions
                ),
                "average_prior_context_tokens_during_completion": average_prior_context,
                "logical_kv_read_bytes_per_generated_token": logical_kv_read_per_token,
                "logical_kv_write_bytes_per_generated_token": kv_per_context,
                "wave_observations": repetitions,
            }
        )
    return rows


def inverse_threshold(
    observed: dict[str, Any], model_lock: dict[str, Any], multiplier: float
) -> dict[str, Any]:
    decode = model_lock["ordinary_text_decode"]
    measured_rate = float(observed["median_aggregate_completion_tokens_s_end_to_end"])
    required_rate = measured_rate * multiplier
    operations = {
        name: float(value) * required_rate
        for name, value in decode[
            "matrix_operations_lower_bound_per_token_by_format"
        ].items()
    }
    return {
        "prompt_tokens": observed["prompt_tokens"],
        "completion_tokens_per_request": observed["completion_tokens_per_request"],
        "concurrency": observed["concurrency"],
        "throughput_multiplier": multiplier,
        "threshold_semantics": (
            "median observed shared-service equality"
            if multiplier == 1
            else "speedup target relative to median observed shared service"
        ),
        "measured_median_aggregate_tokens_s": measured_rate,
        "measured_observed_rate_range_tokens_s": [
            observed["minimum_aggregate_completion_tokens_s_end_to_end"],
            observed["maximum_aggregate_completion_tokens_s_end_to_end"],
        ],
        "required_aggregate_tokens_s": required_rate,
        "maximum_aggregate_token_interval_s": 1 / required_rate,
        "required_full_checkpoint_capacity_bytes": model_lock["checkpoint"][
            "full_checkpoint_payload_bytes"
        ],
        "required_text_image_capacity_bytes": model_lock["checkpoint"][
            "text_image_payload_bytes"
        ],
        "active_immutable_bytes_per_generated_token": decode[
            "active_immutable_bytes_per_token"
        ],
        "required_effective_active_weight_bandwidth_bytes_s": float(
            decode["active_immutable_bytes_per_token"]
        )
        * required_rate,
        "logical_kv_read_bytes_per_generated_token": observed[
            "logical_kv_read_bytes_per_generated_token"
        ],
        "logical_kv_write_bytes_per_generated_token": observed[
            "logical_kv_write_bytes_per_generated_token"
        ],
        "required_logical_kv_read_bandwidth_bytes_s": float(
            observed["logical_kv_read_bytes_per_generated_token"]
        )
        * required_rate,
        "required_logical_kv_write_bandwidth_bytes_s": float(
            observed["logical_kv_write_bytes_per_generated_token"]
        )
        * required_rate,
        "required_matrix_operations_lower_bound_s_by_format": operations,
        "required_total_matrix_operations_lower_bound_s": sum(operations.values()),
        "energy_requirement": None,
        "energy_semantics": "unavailable: shared whole-GPU power is contaminated and is not attributed to this benchmark",
    }


def capacity_requirements(
    checkpoint_bytes: int, scenarios: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    rows = []
    for scenario in scenarios:
        rom_area = float(scenario["wafer_area_mm2"]) * float(
            scenario["rom_area_fraction"]
        )
        usable_fraction = float(scenario["usable_capacity_fraction"])
        usable_density = checkpoint_bytes / rom_area
        raw_density = usable_density / usable_fraction
        rows.append(
            {
                "scenario": scenario["name"],
                "wafer_area_mm2": scenario["wafer_area_mm2"],
                "rom_area_fraction": scenario["rom_area_fraction"],
                "rom_area_mm2": rom_area,
                "usable_capacity_fraction": scenario["usable_capacity_fraction"],
                "required_usable_density_bytes_mm2": usable_density,
                "required_usable_density_mbit_mm2": usable_density * 8 / 1e6,
                "required_raw_macro_density_bytes_mm2": raw_density,
                "required_raw_macro_density_mbit_mm2": raw_density * 8 / 1e6,
            }
        )
    return rows


def reference_threshold(
    thresholds: list[dict[str, Any]], block: dict[str, Any]
) -> dict[str, Any]:
    matches = [
        row
        for row in thresholds
        if row["prompt_tokens"] == int(block["reference_prompt_tokens"])
        and row["concurrency"] == int(block["reference_concurrency"])
        and row["throughput_multiplier"] == 1
    ]
    if len(matches) != 1:
        raise MeasuredBreakEvenError("measured reference threshold is not unique")
    return matches[0]


def build_result(config_path: Path, measurement_path: Path) -> dict[str, Any]:
    config = strict_json(config_path)
    validate_config(config)
    model_lock_path = resolve_repository_input(
        config["measured_break_even"]["model_profile_lock"]
    )
    model_lock = strict_json(model_lock_path)
    validate_model_lock(model_lock)
    measurement = strict_json(measurement_path)
    validate_measurement(measurement, config, config_path, model_lock)
    observed = observed_scenarios(measurement, model_lock)
    thresholds = [
        inverse_threshold(row, model_lock, float(multiplier))
        for row in observed
        for multiplier in config["measured_break_even"]["throughput_multipliers"]
    ]
    reference = reference_threshold(thresholds, config["measured_break_even"])
    return {
        "schema_version": 1,
        "analysis_id": "opentallas-local-measured-gpu-break-even-v1",
        "source_measurement_generated_at": measurement["generated_at"],
        "status": "measured_comparator_requirements_derived_not_achieved",
        "evidence_class": config["evidence_class"],
        "comparison_contract": {
            "gpu": measurement["gpu_before"]["name"],
            "gpu_uuid": measurement["gpu_before"]["uuid"],
            "endpoint_model": measurement["selected_endpoint_model"],
            "endpoint_runtime": measurement["selected_endpoint_version"],
            "model_accounting_revision": model_lock["model"]["revision"],
            "runtime_revision_binding": model_lock["runtime_binding"]["status"],
            "contamination_label": measurement["contamination_label"],
            "completion_rate_semantics": "total completion tokens divided by the maximum simultaneous request end-to-end interval for each wave; medians and observed ranges are retained",
            "speedup_semantics": config["measured_break_even"][
                "strict_speedup_semantics"
            ],
            "energy_semantics": "unavailable; whole-GPU samples include unrelated workloads",
        },
        "input_manifests": {
            "runner": manifest(Path(__file__).resolve()),
            "config": manifest(config_path),
            "model_profile_lock": manifest(model_lock_path),
            "measurement": manifest(measurement_path),
        },
        "model_accounting": {
            "full_checkpoint_payload_bytes": model_lock["checkpoint"][
                "full_checkpoint_payload_bytes"
            ],
            "text_image_payload_bytes": model_lock["checkpoint"][
                "text_image_payload_bytes"
            ],
            "active_immutable_bytes_per_generated_token": model_lock[
                "ordinary_text_decode"
            ]["active_immutable_bytes_per_token"],
            "matrix_operations_lower_bound_per_token_by_format": model_lock[
                "ordinary_text_decode"
            ]["matrix_operations_lower_bound_per_token_by_format"],
            "matrix_operations_lower_bound_per_token": model_lock[
                "ordinary_text_decode"
            ]["matrix_operations_lower_bound_per_token"],
            "kv_bytes_per_context_token": model_lock["ordinary_text_decode"][
                "kv_bytes_per_context_token"
            ],
            "decode_contract": model_lock["decode_contract"],
        },
        "observed_service_scenarios": observed,
        "reference_threshold": reference,
        "thresholds": thresholds,
        "capacity_requirements_by_rom_area": capacity_requirements(
            int(model_lock["checkpoint"]["full_checkpoint_payload_bytes"]),
            config["measured_break_even"]["rom_area_scenarios"],
        ),
        "measurement_environment": {
            "gpu_before": measurement["gpu_before"],
            "gpu_after": measurement["gpu_after"],
            "compute_process_count_before": len(
                measurement["compute_processes_before"]
            ),
            "compute_process_count_after": len(measurement["compute_processes_after"]),
            "endpoint_stability": measurement["endpoint_stability"],
            "endpoint_version_stability": measurement["endpoint_version_stability"],
        },
        "evidence_decomposition": {
            "measured": [
                "request token usage",
                "TTFT and end-to-end service timing",
                "observed aggregate completion rate distribution",
                "GPU identity and shared process inventory",
            ],
            "checkpoint_derived": [
                "full and text-image immutable capacity",
                "active selected-expert and dense weight bytes",
                "checkpoint-declared matrix-operation lower bound",
            ],
            "architecture_derived": [
                "logical BF16 KV read/write traffic from attention topology",
            ],
            "unavailable": [
                "attributable GPU energy or power",
                "clean peak RTX PRO 6000 throughput",
                "measured HBM bytes",
                "production router traces and expert locality",
                "achieved OpenTallas capacity, bandwidth, arithmetic, latency, or energy",
                "API-attested served checkpoint revision",
            ],
        },
        "claim_boundary": [
            "This artifact uses a measured model-root-matched service comparator with accounting tied to the sole local snapshot; the endpoint API does not attest its revision.",
            "The GPU was shared and contended; it is not a clean peak-GPU characterization.",
            "Only token usage and service timing are measured. Model bytes and matrix-operation lower bounds come from the exact pinned tensor headers; logical KV traffic comes from the declared topology.",
            "Whole-GPU power and joules are not attributed because unrelated workloads remained active.",
            "The matrix-operation values are lower bounds and omit vector, routing, sampling, and control work.",
            "Every OpenTallas value is a necessary inverse requirement, not an achieved implementation result.",
            "A performance-superiority claim still requires a statistically governed same-model comparison with accuracy, latency, context, concurrency, software, and power scope controlled.",
        ],
    }


def format_rate(value: float, suffix: str = "") -> str:
    if abs(value) >= 1e15:
        return f"{value / 1e15:.3f} P{suffix}"
    if abs(value) >= 1e12:
        return f"{value / 1e12:.3f} T{suffix}"
    if abs(value) >= 1e9:
        return f"{value / 1e9:.3f} G{suffix}"
    if abs(value) >= 1e6:
        return f"{value / 1e6:.3f} M{suffix}"
    return f"{value:.3f} {suffix}".rstrip()


def render_report(result: dict[str, Any]) -> str:
    reference = result["reference_threshold"]
    comparison = result["comparison_contract"]
    lines = [
        "# OpenTallas measured local-GPU break-even requirements",
        "",
        "> **Outcome:** the local GPU service timing is measured, and the model",
        "> accounting is pinned to the sole snapshot associated with the served",
        "> model root; the API does not attest its revision. The resulting",
        "> OpenTallas values are requirements, not achieved performance.",
        "",
        "## Measurement contract",
        "",
        f"- GPU: `{comparison['gpu']}` (`{comparison['gpu_uuid']}`)",
        f"- Endpoint: `{comparison['endpoint_model']['id']}` / `{comparison['endpoint_model']['root']}`",
        f"- Endpoint runtime: `vLLM {comparison['endpoint_runtime']['version']}`",
        f"- Accounting snapshot revision: `{comparison['model_accounting_revision']}`",
        f"- Runtime revision linkage: {comparison['runtime_revision_binding']}",
        f"- Evidence class: `{comparison['contamination_label']}`",
        "- Energy: **unavailable for attribution** because unrelated workloads remained active",
        "",
        "## Measured service distribution",
        "",
        "| Prompt | Completion | Concurrency | Repetitions | Median aggregate tok/s | Observed range | Median TTFT | Median E2E |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in result["observed_service_scenarios"]:
        lines.append(
            f"| {row['prompt_tokens']:,} | {row['completion_tokens_per_request']} | "
            f"{row['concurrency']} | {row['repetitions']} | "
            f"{row['median_aggregate_completion_tokens_s_end_to_end']:.3f} | "
            f"{row['minimum_aggregate_completion_tokens_s_end_to_end']:.3f}–"
            f"{row['maximum_aggregate_completion_tokens_s_end_to_end']:.3f} | "
            f"{row['median_request_ttft_s'] * 1e3:.3f} ms | "
            f"{row['median_request_end_to_end_s'] * 1e3:.3f} ms |"
        )
    lines.extend(
        [
            "",
            "These are shared-service observations, not a clean RTX PRO 6000 peak.",
            "The range is the observed repetition range, not a confidence interval.",
            "End-to-end timing includes prompt ingestion/prefill; it is a service-level",
            "threshold and cannot be substituted for a pure decode-only comparison.",
            "",
            "## Reference measured equality threshold",
            "",
            f"The governed reference is the {reference['prompt_tokens']:,}-token prompt, "
            f"{reference['completion_tokens_per_request']}-token completion, concurrency "
            f"{reference['concurrency']} point. Its median measured service rate is "
            f"**{reference['required_aggregate_tokens_s']:.3f} completion tokens/s**.",
            "",
            "| Necessary equality requirement | Value | Evidence |",
            "| --- | ---: | --- |",
            f"| Aggregate completion rate | {reference['required_aggregate_tokens_s']:.3f} token/s | measured median |",
            f"| Observed comparator range | {reference['measured_observed_rate_range_tokens_s'][0]:.3f}–{reference['measured_observed_rate_range_tokens_s'][1]:.3f} token/s | measured repetitions |",
            f"| Maximum aggregate token interval | {reference['maximum_aggregate_token_interval_s'] * 1e3:.6f} ms | inverse of measured median |",
            f"| Full endpoint checkpoint capacity | {reference['required_full_checkpoint_capacity_bytes'] / 1e9:.3f} GB | exact tensor headers |",
            f"| Text-image capacity | {reference['required_text_image_capacity_bytes'] / 1e9:.3f} GB | exact tensor roles |",
            f"| Active immutable bytes/token | {reference['active_immutable_bytes_per_generated_token'] / 1e9:.3f} GB | exact dense + 8/128 experts |",
            f"| Effective active-weight service | {reference['required_effective_active_weight_bandwidth_bytes_s'] / 1e9:.3f} GB/s | derived from measured rate |",
            f"| Logical KV read service | {reference['required_logical_kv_read_bandwidth_bytes_s'] / 1e9:.3f} GB/s | topology-derived, not measured HBM |",
            f"| Logical KV write service | {reference['required_logical_kv_write_bandwidth_bytes_s'] / 1e6:.3f} MB/s | topology-derived, not measured HBM |",
            f"| Matrix-operation lower bound | {reference['required_total_matrix_operations_lower_bound_s'] / 1e12:.3f} TOP/s | checkpoint-derived lower bound |",
            "| Attributable energy | unavailable | shared whole-GPU power rejected |",
            "",
            "The exact matrix lower-bound mix at equality is:",
            "",
        ]
    )
    for name, value in sorted(
        reference["required_matrix_operations_lower_bound_s_by_format"].items()
    ):
        lines.append(f"- `{name}`: {format_rate(value, 'op/s')}")
    lines.extend(
        [
            "",
            "This operation count is deliberately a lower bound. It excludes",
            "normalization, rotary embedding, softmax, routing selection, sampling,",
            "and other vector/control work.",
            "",
            "## Capacity density required for one wafer",
            "",
            "| Scenario | ROM area | Required usable density | Required raw density |",
            "| --- | ---: | ---: | ---: |",
        ]
    )
    for row in result["capacity_requirements_by_rom_area"]:
        lines.append(
            f"| `{row['scenario']}` | {row['rom_area_mm2']:,.1f} mm² | "
            f"{row['required_usable_density_mbit_mm2']:.3f} Mbit/mm² | "
            f"{row['required_raw_macro_density_mbit_mm2']:.3f} Mbit/mm² |"
        )
    lines.extend(
        [
            "",
            "These density requirements retain the full multimodal endpoint checkpoint",
            "even though the measurement exercises text-only decode. They do not include",
            "a target ROM compiler, periphery closure, sense margin, repair, or yield.",
            "",
            "## Context and speedup requirements",
            "",
            "| Prompt | Target | Required tok/s | Active-weight service | Logical KV read | Matrix lower bound | Max interval |",
            "| ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in result["thresholds"]:
        lines.append(
            f"| {row['prompt_tokens']:,} | {row['throughput_multiplier']:.1f}x | "
            f"{row['required_aggregate_tokens_s']:.3f} | "
            f"{row['required_effective_active_weight_bandwidth_bytes_s'] / 1e9:.3f} GB/s | "
            f"{row['required_logical_kv_read_bandwidth_bytes_s'] / 1e9:.3f} GB/s | "
            f"{row['required_total_matrix_operations_lower_bound_s'] / 1e12:.3f} TOP/s | "
            f"{row['maximum_aggregate_token_interval_s'] * 1e3:.3f} ms |"
        )
    lines.extend(
        [
            "",
            "## Evidence decomposition",
            "",
            "| Class | Included quantities |",
            "| --- | --- |",
        ]
    )
    for evidence_class, values in result["evidence_decomposition"].items():
        lines.append(f"| {evidence_class} | {'; '.join(values)} |")
    lines.extend(["", "## Claim boundary", ""])
    lines.extend(f"- {item}" for item in result["claim_boundary"])
    lines.append("")
    return "\n".join(lines)


def latest_measurement(root: Path) -> Path | None:
    candidates = sorted(root.glob("*/measurement.json"))
    return candidates[-1] if candidates else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--measurement", type=Path)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_RESULT_DIR)
    arguments = parser.parse_args()
    measurement = (
        arguments.measurement.resolve()
        if arguments.measurement
        else latest_measurement(DEFAULT_MEASUREMENT_ROOT)
    )
    if measurement is None:
        raise MeasuredBreakEvenError(
            "no measured local-GPU result found; pass --measurement or run the governed benchmark"
        )
    result = build_result(arguments.config.resolve(), measurement)
    output_dir = arguments.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    result_path = output_dir / "measured_break_even.json"
    report_path = output_dir / "REPORT.md"
    result_path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    report_path.write_text(render_report(result), encoding="utf-8")
    try:
        result_display = result_path.relative_to(ROOT)
        report_display = report_path.relative_to(ROOT)
    except ValueError:
        result_display = result_path
        report_display = report_path
    print(f"wrote {result_display}")
    print(f"wrote {report_display}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except MeasuredBreakEvenError as exc:
        raise SystemExit(f"measured break-even error: {exc}") from exc
