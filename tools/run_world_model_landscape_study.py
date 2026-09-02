#!/usr/bin/env python3
"""Generate the recent-world-model ROM decode-shape audit."""

from __future__ import annotations

import csv
from datetime import date
import hashlib
import io
import json
import math
from pathlib import Path
import re
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from opentallas.schema import ArchitectureProfile  # noqa: E402
from opentallas.world_model import (  # noqa: E402
    linear_row_storage_roofline,
)


CONFIG_PATH = ROOT / "configs/studies/world_model_landscape_rom.json"
OUTPUT_ROOT = ROOT / "results/world-model-landscape"


def _is_lower_hex(value: Any, length: int) -> bool:
    return (
        isinstance(value, str)
        and len(value) == length
        and all(character in "0123456789abcdef" for character in value)
    )


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _repo_path(relative_path: Any, *, label: str) -> Path:
    if not isinstance(relative_path, str) or not relative_path:
        raise RuntimeError(f"{label}: path must be a nonempty string")
    candidate = Path(relative_path)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise RuntimeError(f"{label}: path must stay inside the repository")
    resolved = (ROOT / candidate).resolve()
    if not resolved.is_relative_to(ROOT.resolve()):
        raise RuntimeError(f"{label}: path escapes the repository")
    if not resolved.is_file():
        raise RuntimeError(f"{label}: input does not exist: {relative_path}")
    return resolved


def _load_pinned_json(
    input_record: Any, *, label: str
) -> tuple[Path, dict[str, Any], dict[str, str]]:
    """Hash and parse the same captured bytes from a repository-contained input."""

    if not isinstance(input_record, dict) or set(input_record) != {
        "path",
        "sha256",
    }:
        raise RuntimeError(f"{label}: a pinned path/SHA-256 record is required")
    expected_sha256 = input_record.get("sha256")
    if not _is_lower_hex(expected_sha256, 64):
        raise RuntimeError(f"{label}: malformed pinned SHA-256")
    path = _repo_path(input_record.get("path"), label=label)
    payload = path.read_bytes()
    actual_sha256 = _sha256_bytes(payload)
    if actual_sha256 != expected_sha256:
        raise RuntimeError(
            f"{label}: SHA-256 mismatch: expected {expected_sha256}, "
            f"got {actual_sha256}"
        )
    try:
        decoded = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"{label}: invalid JSON") from exc
    if not isinstance(decoded, dict):
        raise RuntimeError(f"{label}: JSON root must be an object")
    identity = {
        "path": str(path.relative_to(ROOT)),
        "sha256": actual_sha256,
    }
    return path, decoded, identity


def _load_config() -> tuple[dict[str, Any], dict[str, str]]:
    payload = CONFIG_PATH.read_bytes()
    try:
        config = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("study config is invalid JSON") from exc
    if not isinstance(config, dict):
        raise RuntimeError("study config root must be an object")
    return config, {
        "path": str(CONFIG_PATH.relative_to(ROOT)),
        "sha256": _sha256_bytes(payload),
    }


def _positive_finite(value: Any) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(value)
        and value > 0
    )


def _validate_config(config: dict[str, Any]) -> None:
    if config.get("schema_version") != 1:
        raise RuntimeError("study config schema_version must be 1")
    if config.get("study_id") != "world_model_landscape_rom":
        raise RuntimeError("unexpected study_id")
    as_of_date = config.get("as_of_date")
    try:
        if (
            not isinstance(as_of_date, str)
            or date.fromisoformat(as_of_date).isoformat() != as_of_date
        ):
            raise ValueError
    except ValueError as exc:
        raise RuntimeError("as_of_date must be an ISO calendar date") from exc

    for key in ("inventory", "hardware_config", "existing_world_model_study"):
        record = config.get(key)
        if not isinstance(record, dict) or set(record) != {"path", "sha256"}:
            raise RuntimeError(f"{key} must be a pinned path/SHA-256 record")
        if not _is_lower_hex(record.get("sha256"), 64):
            raise RuntimeError(f"{key} has a malformed SHA-256")

    architectures = config.get("comparison_architectures")
    if (
        not isinstance(architectures, dict)
        or set(architectures) != {"gpu", "rom"}
        or any(
            not isinstance(value, str) or not value for value in architectures.values()
        )
        or architectures["gpu"] == architectures["rom"]
    ):
        raise RuntimeError(
            "comparison_architectures must name distinct GPU and ROM profiles"
        )

    contract = config.get("comparison_contract")
    if (
        not isinstance(contract, dict)
        or contract.get("actual_architecture_ratio_is_storage_attribution") is not False
        or contract.get("active_parameter_and_call_counts_are_normalizers") is not True
        or not isinstance(contract.get("same_compute_storage_attribution"), str)
        or not isinstance(contract.get("shared_omission_condition"), str)
    ):
        raise RuntimeError("comparison_contract is incomplete or unsafe")

    if not _positive_finite(config.get("active_matrix_parameters_normalizer")):
        raise RuntimeError(
            "active_matrix_parameters_normalizer must be finite and positive"
        )
    calls = config.get("calls_normalizer")
    if isinstance(calls, bool) or not isinstance(calls, int) or calls <= 0:
        raise RuntimeError("calls_normalizer must be a positive integer")

    formats = config.get("numeric_format_sweeps")
    expected_formats = {
        "bf16_x_bf16": 2.0,
        "fp8_e4m3_x_fp8_e4m3": 1.0,
    }
    if not isinstance(formats, list) or len(formats) != len(expected_formats):
        raise RuntimeError("exactly the BF16 and FP8 sweeps are required")
    observed_formats: dict[str, float] = {}
    for entry in formats:
        if not isinstance(entry, dict):
            raise RuntimeError("numeric format sweep entries must be objects")
        compute_format = entry.get("compute_format")
        weight_bytes = entry.get("weight_bytes_per_parameter")
        if compute_format in observed_formats or not _positive_finite(weight_bytes):
            raise RuntimeError("numeric format sweeps must be unique and positive")
        observed_formats[compute_format] = float(weight_bytes)
    if observed_formats != expected_formats:
        raise RuntimeError("numeric format sweeps do not match the governed formats")

    rows = config.get("row_sweep")
    if (
        not isinstance(rows, list)
        or any(
            isinstance(row, bool) or not isinstance(row, int) or row <= 0
            for row in rows
        )
        or rows != sorted(set(rows))
    ):
        raise RuntimeError("row_sweep must be sorted, unique, and positive")
    required_boundaries = {3, 4, 174, 175, 186, 187, 339, 340, 373, 374}
    if not required_boundaries.issubset(rows):
        raise RuntimeError("row_sweep omits a governed crossover neighbor")

    thresholds = config.get("target_storage_attribution_thresholds")
    if thresholds != [1.1, 2.0]:
        raise RuntimeError("governed storage-attribution thresholds must be [1.1, 2.0]")
    if config.get("threshold_metric") != "roofline_storage_attribution":
        raise RuntimeError("threshold_metric must name roofline_storage_attribution")

    evidence = config.get("evidence")
    if not isinstance(evidence, dict) or not evidence:
        raise RuntimeError("study config requires evidence records")
    for name, entry in evidence.items():
        if (
            not isinstance(entry, dict)
            or entry.get("grade") not in {"assumed", "derived", "published"}
            or not isinstance(entry.get("source"), str)
            or not entry["source"]
        ):
            raise RuntimeError(f"evidence entry {name!r} is malformed")


def _validate_inventory(
    inventory: dict[str, Any], *, expected_date: str, expected_rows: set[int]
) -> None:
    """Fail closed on the locally retained source and row-geometry record."""

    if inventory.get("schema_version") != 1:
        raise RuntimeError("inventory schema_version must be 1")
    if inventory.get("inventory_id") != "recent-world-models-2026-09":
        raise RuntimeError("unexpected inventory_id")
    if inventory.get("as_of_date") != expected_date:
        raise RuntimeError("inventory and study source-cut dates disagree")
    if not isinstance(inventory.get("evidence_policy"), str):
        raise RuntimeError("inventory requires an evidence policy")
    models = inventory.get("models")
    if not isinstance(models, list) or len(models) != 10:
        raise RuntimeError("inventory must contain exactly ten governed records")

    expected_roles = {
        "World Labs Atlas": "surveyed_release",
        "World Labs RTFM": "surveyed_release",
        "Alaya-EVOKE": "surveyed_release",
        "AlayaWorld v1.1": "surveyed_release",
        "LingBot-World-Infinity 14B causal-fast": "surveyed_release",
        "HY-World 1.5 WorldPlay 8B distilled": "surveyed_release",
        "Matrix-Game 3.0 5B distilled": "surveyed_release",
        "NVIDIA Cosmos 3": "surveyed_release",
        "Oasis causal-cache candidate": "existing_control",
        "MiniMax-H3 dense 5.17-second control": "existing_control",
    }
    allowed_screens = {
        "conditional_only",
        "quantified_row_screen",
        "split_by_runtime_surface",
        "existing_quantified_study",
    }

    seen: set[str] = set()
    for model in models:
        if not isinstance(model, dict):
            raise RuntimeError("inventory model records must be objects")
        name = model.get("model")
        if not isinstance(name, str) or not name or name in seen:
            raise RuntimeError("inventory model names must be unique nonempty strings")
        seen.add(name)
        if expected_roles.get(name) != model.get("record_role"):
            raise RuntimeError(f"{name}: unexpected or missing record role")
        if model.get("rom_screen") not in allowed_screens:
            raise RuntimeError(f"{name}: unsupported ROM-screen classification")
        for field in (
            "architecture",
            "cache_semantics",
            "current_rows_status",
            "open_release_status",
            "published_runtime",
        ):
            if not isinstance(model.get(field), str) or not model[field]:
                raise RuntimeError(f"{name}: missing {field}")

        release_date = model.get("release_date")
        precision = model.get("release_date_precision")
        try:
            if precision == "day":
                valid_date = (
                    isinstance(release_date, str)
                    and date.fromisoformat(release_date).isoformat() == release_date
                )
            elif precision == "month":
                valid_date = bool(
                    isinstance(release_date, str)
                    and re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", release_date)
                )
            elif precision == "year":
                valid_date = bool(
                    isinstance(release_date, str)
                    and re.fullmatch(r"\d{4}", release_date)
                )
            else:
                valid_date = False
        except ValueError:
            valid_date = False
        if not valid_date:
            raise RuntimeError(f"{name}: release date/precision disagree")

        rows = model.get("current_rows_per_call")
        if rows is not None and (
            isinstance(rows, bool) or not isinstance(rows, int) or rows <= 0
        ):
            raise RuntimeError(f"{name}: current rows must be null or positive int")
        factors = model.get("current_rows_factors")
        if rows is None:
            if factors is not None or model.get("current_rows_addends") is not None:
                raise RuntimeError(f"{name}: unknown rows cannot retain factors")
            if (
                model.get("row_evidence") is not None
                or model.get("row_scope") is not None
            ):
                raise RuntimeError(f"{name}: unknown rows cannot claim row evidence")
        else:
            if rows not in expected_rows:
                raise RuntimeError(
                    f"{name}: retained row count is absent from row_sweep"
                )
            if (
                not isinstance(factors, list)
                or not factors
                or any(
                    isinstance(value, bool) or not isinstance(value, int) or value <= 0
                    for value in factors
                )
            ):
                raise RuntimeError(f"{name}: row factors must be positive integers")
            derived_rows = math.prod(factors)
            addends = model.get("current_rows_addends", [])
            if not isinstance(addends, list) or any(
                isinstance(value, bool) or not isinstance(value, int) or value < 0
                for value in addends
            ):
                raise RuntimeError(f"{name}: row addends must be nonnegative integers")
            derived_rows += sum(addends)
            if rows != derived_rows:
                raise RuntimeError(
                    f"{name}: retained row factors yield {derived_rows}, not {rows}"
                )
            if not isinstance(model.get("current_rows_derivation"), str):
                raise RuntimeError(f"{name}: quantified rows require a derivation")
            if not isinstance(model.get("row_scope"), str) or not model["row_scope"]:
                raise RuntimeError(f"{name}: quantified rows require a row scope")
            row_evidence = model.get("row_evidence")
            if (
                not isinstance(row_evidence, dict)
                or row_evidence.get("grade") not in {"assumed", "derived"}
                or not isinstance(row_evidence.get("source"), str)
                or not row_evidence["source"]
            ):
                raise RuntimeError(f"{name}: quantified rows require graded evidence")
            assumption_text = (
                model["current_rows_status"] + " " + model["current_rows_derivation"]
            ).lower()
            if "assum" in assumption_text and row_evidence["grade"] != "assumed":
                raise RuntimeError(
                    f"{name}: assumed row components must be graded assumed"
                )

        sources = model.get("sources")
        if not isinstance(sources, list) or not sources:
            raise RuntimeError(f"{name}: at least one source is required")
        for source in sources:
            if not isinstance(source, dict):
                raise RuntimeError(f"{name}: source entries must be objects")
            if source.get("grade") not in {"published", "derived"}:
                raise RuntimeError(f"{name}: unsupported source grade")
            if source["grade"] == "derived":
                if (
                    not isinstance(source.get("evidence"), str)
                    or not source["evidence"]
                ):
                    raise RuntimeError(
                        f"{name}: local derived sources need evidence text"
                    )
                path = _repo_path(source.get("path"), label=f"{name} local source")
                expected_sha256 = source.get("sha256")
                if not _is_lower_hex(expected_sha256, 64):
                    raise RuntimeError(f"{name}: malformed local source SHA-256")
                if _sha256_bytes(path.read_bytes()) != expected_sha256:
                    raise RuntimeError(f"{name}: local source SHA-256 mismatch")
                continue

            locator = source.get("source")
            if not isinstance(locator, str) or not locator.startswith("https://"):
                raise RuntimeError(
                    f"{name}: published sources require an HTTPS locator"
                )
            has_commit = "commit" in source
            has_content_hash = "content_sha256" in source
            has_mutable_boundary = source.get("stability") == (
                "mutable_live_vendor_page_no_retained_snapshot"
            )
            if not (has_commit or has_content_hash or has_mutable_boundary):
                raise RuntimeError(
                    f"{name}: published source lacks a pin or mutable boundary"
                )
            if has_commit and not _is_lower_hex(source["commit"], 40):
                raise RuntimeError(f"{name}: malformed pinned Git commit")
            if has_content_hash and not _is_lower_hex(source["content_sha256"], 64):
                raise RuntimeError(f"{name}: malformed content SHA-256")
            files = source.get("files", [])
            if has_commit and (not isinstance(files, list) or not files):
                raise RuntimeError(f"{name}: commit-pinned sources require file pins")
            if not isinstance(files, list):
                raise RuntimeError(f"{name}: source files must be a list")
            for file_record in files:
                if (
                    not isinstance(file_record, dict)
                    or not isinstance(file_record.get("path"), str)
                    or not _is_lower_hex(file_record.get("sha256"), 64)
                ):
                    raise RuntimeError(f"{name}: malformed pinned file record")
            if has_mutable_boundary:
                checked_date = source.get("checked_date")
                try:
                    valid_checked_date = (
                        isinstance(checked_date, str)
                        and date.fromisoformat(checked_date).isoformat() == checked_date
                    )
                except ValueError:
                    valid_checked_date = False
                if not valid_checked_date:
                    raise RuntimeError(f"{name}: mutable source needs a checked date")

    if seen != set(expected_roles):
        raise RuntimeError("inventory model set does not match the governed survey")
    surveyed = [model for model in models if model["record_role"] == "surveyed_release"]
    controls = [model for model in models if model["record_role"] == "existing_control"]
    if len(surveyed) != 8 or len(controls) != 2:
        raise RuntimeError("inventory must contain eight releases and two controls")
    if sum(model["current_rows_per_call"] is not None for model in surveyed) != 5:
        raise RuntimeError("exactly five surveyed releases must have quantified rows")


def _find_architecture(
    hardware: dict[str, Any], name: str, *, expected_kind: str
) -> ArchitectureProfile:
    candidates = [
        *hardware.get("gpu_architectures", []),
        *hardware.get("wafer_architectures", []),
    ]
    matches = [item for item in candidates if item["name"] == name]
    if len(matches) != 1:
        raise RuntimeError(f"expected one architecture named {name!r}")
    profile = ArchitectureProfile.from_dict(matches[0])
    if profile.kind != expected_kind:
        raise RuntimeError(
            f"architecture {name!r} has kind {profile.kind!r}, "
            f"expected {expected_kind!r}"
        )
    return profile


def _phase_compute_rate(arch: ArchitectureProfile, compute_format: str) -> float:
    """Return the per-phase rate after the configured pipeline efficiency."""

    devices = arch.device_count if arch.kind == "gpu" else 1
    return (
        arch.compute_roof(compute_format)
        * arch.compute_efficiency
        * arch.clock_efficiency
        * arch.defect_repair_efficiency
        * arch.pipeline_efficiency
        * devices
    )


def _rom_weight_rate(arch: ArchitectureProfile) -> float:
    return (
        arch.weight_bandwidth_bytes_s_per_device
        * arch.weight_bandwidth_efficiency
        * arch.clock_efficiency
        * arch.defect_repair_efficiency
    )


def _same_compute_hbm_rate(arch: ArchitectureProfile) -> float:
    # Matches evaluate_video_workload: a model fitting one ROM stage receives
    # that stage's HBM service, not the sum over 64 possible pipeline stages.
    return (
        arch.kv_bandwidth_bytes_s_per_device
        * arch.kv_bandwidth_efficiency
        * arch.clock_efficiency
        * arch.defect_repair_efficiency
    )


def _gpu_hbm_rate(arch: ArchitectureProfile) -> float:
    return (
        arch.device_count
        * arch.weight_bandwidth_bytes_s_per_device
        * arch.weight_bandwidth_efficiency
        * arch.clock_efficiency
        * arch.defect_repair_efficiency
    )


def _actual_architecture_screen(
    *,
    rows: int,
    active_parameters: float,
    calls: int,
    weight_bytes: float,
    gpu_compute: float,
    gpu_hbm: float,
    rom_compute: float,
    rom_weight: float,
) -> dict[str, float | str]:
    """Compare each architecture's own compute/storage roofline.

    This intentionally is not storage attribution: both compute and immutable
    weight service change between the B300 and the modeled ROM wafer.
    """

    gpu = linear_row_storage_roofline(
        rows_per_call=rows,
        active_matrix_parameters=active_parameters,
        calls=calls,
        weight_bytes_per_parameter=weight_bytes,
        compute_ops_s=gpu_compute,
        hbm_weight_bytes_s=gpu_hbm,
        rom_weight_bytes_s=gpu_hbm,
    )
    rom = linear_row_storage_roofline(
        rows_per_call=rows,
        active_matrix_parameters=active_parameters,
        calls=calls,
        weight_bytes_per_parameter=weight_bytes,
        compute_ops_s=rom_compute,
        hbm_weight_bytes_s=rom_weight,
        rom_weight_bytes_s=rom_weight,
    )
    return {
        "actual_architecture_ratio_not_storage_attribution": (
            float(gpu["hbm_roofline_s"]) / float(rom["hbm_roofline_s"])
        ),
        "gpu_actual_roofline_s": float(gpu["hbm_roofline_s"]),
        "rom_actual_roofline_s": float(rom["hbm_roofline_s"]),
        "gpu_actual_binding_term": str(gpu["hbm_binding_term"]),
        "rom_actual_binding_term": str(rom["hbm_binding_term"]),
    }


def _fmt_ratio(value: float) -> str:
    return f"{value:,.3f}x"


def _fmt_rows(value: int | None) -> str:
    return "not disclosed" if value is None else f"{value:,}"


def _fmt_rate(value: float, scale: float, suffix: str) -> str:
    return f"{value / scale:,.3f} {suffix}"


def _classification(screen: dict[str, Any]) -> str:
    if screen["hbm_binding_term"] == "immutable_weight":
        return "HBM-weight-bound in the linear-only roofline"
    return "compute-bound before KV, attention, NoC, VAE, or runtime work"


def _model_verdict(model: dict[str, Any], screen: dict[str, Any] | None) -> str:
    name = model["model"]
    if name == "World Labs Atlas":
        return "Architecturally promising, numerically unquantifiable"
    if name == "World Labs RTFM":
        return "Real history KV; ROM value remains unquantifiable"
    if name == "NVIDIA Cosmos 3":
        return "Reasoner favorable; Generator unfavorable/unknown-width"
    if name == "Oasis causal-cache candidate":
        return "Conditional ROM opportunity after an unimplemented cache transform"
    if name.startswith("MiniMax-H3"):
        return "Full-clip control; ROM storage is immaterial"
    if screen is None:
        return "No row-width result"
    if screen["roofline_storage_attribution"] > 1.1:
        return "Potentially meaningful; requires a full KV/NoC audit"
    return "Block decode; ROM storage is not a meaningful primary accelerator"


def _report(result: dict[str, Any]) -> str:
    formats = {item["label"]: item for item in result["hardware_formats"]}
    bf16 = formats["BF16"]
    fp8 = formats["FP8"]
    screens = {item["model"]: item for item in result["model_screens"]}
    cross = result["existing_world_model_study"]
    atlas = result["atlas_conditions"]

    lines = [
        "# Recent world models: autoregressive diffusion and immutable ROM",
        "",
        "> **Result class: dated source-recorded architecture audit, with commit-",
        "> and file-pinned open implementations, plus a deterministic analytical",
        "> row roofline. Atlas and RTFM are mutable-page observations without retained",
        "> snapshots. This is not model execution, an Atlas benchmark,",
        "> a video compiler result, or silicon evidence.** The source cut is",
        f"> {result['as_of_date']}.",
        "",
        "## Executive answer",
        "",
        "The earlier Oasis/H3 study was intentionally scoped to those two",
        "architectures and did not include Atlas. This companion audit now includes",
        "World Labs Atlas and RTFM, EVOKE, AlayaWorld, LingBot-World-Infinity,",
        "HY-WorldPlay, Matrix-Game 3.0, and Cosmos 3.",
        "",
        "The result is not that autoregressive diffusion is automatically good for",
        "ROM. The outer autoregressive unit matters:",
        "",
        "- Atlas emits one multimodal **element** at a time, but an element can be",
        "  an entire image or depth map generated by rectified-flow denoising. That",
        "  is not the same execution shape as one-token LLM decode.",
        "- Exact history KV caching can remove repeated processing of old frames.",
        "  It does not remove the thousands of current spatial rows processed in",
        "  each denoising call, and the noisy current element cannot generally be",
        "  reused exactly across diffusion steps.",
        "- On the central OpenTallas same-compute comparison, a BF16 or matched-FP8",
        "  dominant matrix crosses from HBM-weight-bound to compute-bound at only",
        f"  {bf16['same_compute_hbm_ridge_rows']:.3f} rows/call. The recent open video",
        "  paths have 1,560 to 8,800 current rows before favorable exclusions; four",
        "  are source-derived and EVOKE's temporal factor is an explicit favorable",
        "  assumption. All five screens are beyond that ridge.",
        "- LingBot is the decisive counterexample to the idea that KV caching is",
        "  sufficient: it has a real sliding-window transformer KV cache, yet its",
        "  three-latent-frame query block is 4,680 rows. The standard storage",
        "  roofline therefore remains 1.000x.",
        "- Atlas and RTFM are more structurally promising than MiniMax-H3 because",
        "  they expose outer autoregression and history reuse. World Labs has not",
        "  published the quantities needed for a numerical ROM speedup, so any",
        "  Atlas number today would be fabricated.",
        "",
        "## Scope: immutable storage, not unproven DiT compute-in-ROM",
        "",
        "OpenTallas documents separate ROM-as-storage and per-stream",
        "compute-in-ROM forks. This study answers the storage-attribution question:",
        "it holds the compute fabric fixed and moves only immutable weight service",
        "between the same wafer's HBM path and ROM path. It therefore measures the",
        "benefit attributable to avoiding recurring weight reads.",
        "",
        "A fixed-weight select-and-accumulate fabric could in principle attack a",
        "compute-bound DiT, but that would be a different claim. It needs a",
        "video-shape array-sweep law, supported operators, compiler/runtime work,",
        "and physical evidence; none exists in OpenTallas today. Its per-stream",
        "batch law also differs from the amortising storage-plus-MAC design. No",
        "compute-in-ROM speedup is silently credited in the numbers below.",
        "",
        "## Why denoising-step count cancels",
        "",
        "For P active matrix parameters, R activation rows/call, K denoiser calls,",
        "and bw bytes/weight:",
        "",
        "    operations       = 2 K P R",
        "    HBM weight bytes = K P bw",
        "    linear intensity = 2 R / bw operations per weight byte",
        "",
        "P and K cancel from the compute-versus-weight balance. Three-step",
        "distillation can deliver a large absolute latency win, but it does not by",
        "itself increase the fraction of time removable by immutable ROM. Reducing",
        "R through a genuinely narrow causal query is the relevant transformation.",
        "This is why a wide current-frame DiT call resembles LLM prefill rather",
        "than tokenwise decode from the immutable-weight point of view.",
        "",
        "R includes every activation row that shares one matrix-weight load:",
        "batch size times current rows per stream. Every model screen below uses",
        "batch one, the setting most favorable to exposing weight service. Batching",
        "several simultaneous worlds only increases R and pushes the call farther",
        "into the compute-bound regime.",
        "",
        "For effective compute C and weight bandwidth B, the HBM ridge is:",
        "",
        "    R_ridge = bw C / (2 B)",
        "",
        "The checked OpenTallas model overlaps tensor compute and storage with a",
        "max roofline. The additive column below is a no-overlap sensitivity. The",
        "zero-cost column is a deliberately impossible upper endpoint: all HBM",
        "weight time serializes and ROM weight service is free.",
        "",
        "## Hardware ridge used by the screen",
        "",
        "| Format / architecture | Phase compute | HBM weight service | ROM weight service | HBM ridge | ROM ridge |",
        "|---|---:|---:|---:|---:|---:|",
        (
            f"| BF16 / central same-compute ROM wafer | "
            f"{_fmt_rate(bf16['rom_phase_compute_ops_s'], 1e15, 'POP/s')} | "
            f"{_fmt_rate(bf16['same_compute_hbm_weight_bytes_s'], 1e12, 'TB/s')} | "
            f"{_fmt_rate(bf16['rom_weight_bytes_s'], 1e12, 'TB/s')} | "
            f"{bf16['same_compute_hbm_ridge_rows']:.3f} | "
            f"{bf16['rom_ridge_rows']:.3f} |"
        ),
        (
            f"| FP8 / central same-compute ROM wafer | "
            f"{_fmt_rate(fp8['rom_phase_compute_ops_s'], 1e15, 'POP/s')} | "
            f"{_fmt_rate(fp8['same_compute_hbm_weight_bytes_s'], 1e12, 'TB/s')} | "
            f"{_fmt_rate(fp8['rom_weight_bytes_s'], 1e12, 'TB/s')} | "
            f"{fp8['same_compute_hbm_ridge_rows']:.3f} | "
            f"{fp8['rom_ridge_rows']:.3f} |"
        ),
        (
            f"| BF16 / B300 x1 | "
            f"{_fmt_rate(bf16['gpu_phase_compute_ops_s'], 1e15, 'POP/s')} | "
            f"{_fmt_rate(bf16['gpu_hbm_weight_bytes_s'], 1e12, 'TB/s')} | n/a | "
            f"{bf16['gpu_hbm_ridge_rows']:.3f} | n/a |"
        ),
        "",
        "The BF16 and FP8 ridge values match here because the configured FP8",
        "compute roof doubles while the weight representation halves. These are",
        "assumed/derived service envelopes, not measured OpenTallas hardware.",
        "Absolute FP8 service times are half the BF16 values; the attribution",
        "ratios are therefore identical rather than an independent sensitivity.",
        "",
        "The artifact also records an explicitly separate B300-versus-ROM ratio",
        "using each architecture's own compute and weight-service rates. It is not",
        "storage attribution: its large-row limit is the modeled compute-rate ratio",
        f"of {bf16['rom_over_gpu_compute_rate']:.6f}x, rather than 1.0x.",
        "",
        "## Row-width sweep",
        "",
        "| Rows/call | Representative use | Linear intensity | Roofline ROM attribution | Additive sensitivity | Dominant-linear zero-cost ceiling | HBM result | B300/ROM actual ratio (not attribution) |",
        "|---:|---|---:|---:|---:|---:|---|---:|",
    ]

    labels = {
        1: "tokenwise causal decode",
        64: "very compressed element",
        144: "Oasis cached-frame candidate",
        256: "small image element",
        374: "just beyond central ridge",
        1560: "HY-WorldPlay current block",
        2040: "AlayaWorld current block",
        4680: "LingBot current block",
        8640: "EVOKE current high-res tier",
        8800: "Matrix-Game fresh-row floor",
        38222: "MiniMax-H3 5.17-second packed clip",
    }
    for row in result["row_sweep"]:
        if row["rows_per_call"] not in labels:
            continue
        lines.append(
            f"| {row['rows_per_call']:,} | {labels[row['rows_per_call']]} | "
            f"{row['arithmetic_intensity_ops_per_weight_byte']:,.1f} | "
            f"{_fmt_ratio(row['roofline_storage_attribution'])} | "
            f"{_fmt_ratio(row['additive_storage_attribution'])} | "
            f"{_fmt_ratio(row['zero_cost_rom_additive_upper_bound'])} | "
            f"{row['hbm_binding_term']} | "
            f"{_fmt_ratio(row['actual_architecture_ratio_not_storage_attribution'])} |"
        )

    lines.extend(
        [
            "",
            "The zero-cost ceiling is especially useful for screening the dominant",
            "DiT matrices. Even if an HBM implementation serialized every modeled",
            "weight byte and ROM served those weights for free, LingBot's 4,680-row",
            "dominant linear path could improve by no more than "
            f"{_fmt_ratio(screens['LingBot-World-Infinity 14B causal-fast']['zero_cost_rom_additive_upper_bound'])}",
            "from weight relocation alone, before charging its KV reads, attention,",
            "multi-GPU communication, VAE, or runtime.",
            "",
            "## Model-by-model audit",
            "",
            "| Model / path | Actual inference unit and cache | Current rows/call | Rows / ridge | Standard roofline | Dominant-linear zero-cost ceiling | Finding |",
            "|---|---|---:|---:|---:|---:|---|",
        ]
    )

    model_rows = [
        (
            "World Labs Atlas",
            "one image/depth element; vendor says KV caching is applicable",
        ),
        (
            "World Labs RTFM",
            "one frame; previous posed frames are a retrieved KV cache",
        ),
        (
            "HY-World 1.5 WorldPlay 8B distilled",
            "four-latent-frame block; selected history K/V rebuilt each chunk",
        ),
        (
            "AlayaWorld v1.1",
            "four-latent-frame block; explicit 3D plus history memory",
        ),
        (
            "LingBot-World-Infinity 14B causal-fast",
            "three-latent-frame block; real sliding-window history K/V",
        ),
        (
            "Alaya-EVOKE",
            "assumed nine-latent-frame block; released path disables DiT history K/V",
        ),
        (
            "Matrix-Game 3.0 5B distilled",
            "multi-segment AR; bidirectional current/overlap/memory reprocessing",
        ),
        (
            "NVIDIA Cosmos 3",
            "q=1 text Reasoner vs full-attention diffusion Generator",
        ),
        (
            "Oasis causal-cache candidate",
            "one 144-patch frame; proposed temporal K/V",
        ),
        (
            "MiniMax-H3 dense 5.17-second control",
            "38,222-row full clip; no persistent autoregressive K/V",
        ),
    ]
    inventory_by_name = {item["model"]: item for item in result["inventory_models"]}
    for name, execution in model_rows:
        source = inventory_by_name[name]
        screen = screens.get(name)
        if screen is None:
            ratio = standard = ceiling = "n/a"
        else:
            ratio = f"{screen['rows_over_same_compute_hbm_ridge']:.2f}x"
            standard = _fmt_ratio(screen["roofline_storage_attribution"])
            ceiling = _fmt_ratio(screen["zero_cost_rom_additive_upper_bound"])
        lines.append(
            f"| {name} | {execution} | {_fmt_rows(source['current_rows_per_call'])} | "
            f"{ratio} | {standard} | {ceiling} | "
            f"{_model_verdict(source, screen)} |"
        )

    lines.extend(
        [
            "",
            "The four non-EVOKE surveyed row screens are source-derived current-block",
            "lower bounds for the dominant DiT matrices. EVOKE's nine-frame temporal",
            "factor is an explicit favorable assumption. None is a full parameter or",
            "FLOP inventory. A large",
            "one-row conditioning branch could retain a separate weight-bound term;",
            "that requires a tensor inventory like the existing H3 audit. Excluding",
            "history rows and auxiliary work is favorable to ROM. A 1.000x",
            "row-screen result is",
            "therefore a rejection of weight storage as the primary accelerator,",
            "not a claim that the complete model has zero optimization opportunity.",
            "",
            "## Atlas: what can and cannot be concluded",
            "",
            "World Labs publishes four facts relevant to this question: Atlas is a",
            "multimodal autoregressive diffusion transformer; videos are sequences",
            "of images; each multimodal element is generated one at a time; and the",
            "architecture can use KV caching. It also says diffusion gradually",
            "denoises high-dimensional outputs.",
            "",
            "That makes Atlas more favorable than MiniMax-H3 in one important way:",
            "stable earlier elements can be encoded once rather than reprocessed as",
            "part of every full clip. But the remaining current image is still a",
            "diffusion query block. The word autoregressive describes the sequence",
            "of elements, not necessarily the spatial rows inside one element.",
            "",
            "Because Atlas query geometry is unpublished, only generic row boundaries",
            "can be stated for the central BF16 screen:",
            "",
            "| Storage-only condition | Continuous row boundary | Largest qualifying integer row |",
            "|---|---:|---:|",
            (
                f"| Any standard-roofline benefit | "
                f"R < {atlas['any_roofline_benefit_continuous_upper_boundary_rows']:.3f} | "
                f"{atlas['largest_integer_row_with_any_roofline_benefit']:,} |"
            ),
            (
                f"| At least 1.1x standard-roofline attribution | "
                f"R <= {atlas['standard_1_1x_continuous_boundary_rows']:.3f} | "
                f"{atlas['standard_1_1x_largest_integer_row']:,} |"
            ),
            (
                f"| At least 2x standard-roofline attribution | "
                f"R <= {atlas['standard_2x_continuous_boundary_rows']:.3f} | "
                f"{atlas['standard_2x_largest_integer_row']:,} |"
            ),
            "",
            "These are generic linear-screen boundaries, not Atlas results. A real",
            "calculation requires at least: active parameters",
            "and dtypes by expert/tower, latent rows per image/depth element,",
            "denoiser calls and CFG schedule, exactly which historical tensors are",
            "cached, K/V bytes read per call, attention pattern, parallel topology,",
            "measured latency, and hardware. None is supplied by the launch post.",
            "",
            "If Atlas eventually discloses a current element below roughly 373",
            "dominant-matrix rows, ROM becomes worth a full audit. Above that point,",
            "the current block is already compute-bound in this OpenTallas roofline.",
            "Even below it, long-context K/V service and attention communication can",
            "erase the storage gain.",
            "",
            "## What the open causal models teach",
            "",
            "### LingBot: exact cache, wrong query width for ROM",
            "",
            "LingBot's released code is the cleanest test of the hypothesis. It",
            "processes three latent frames per block, retains per-layer self-attention",
            "K/V in an 18-frame local window plus six sink frames, and performs a",
            "clean cache-install pass. At 480x832, VAE stride 8 and DiT patch 2 leave",
            "1,560 tokens per latent frame, or 4,680 current rows/call. History",
            "caching is a real algorithmic win, but the main matrices remain",
            "compute-bound. ROM does not create a second large win.",
            "",
            "### WorldPlay: the least-unfavorable recent open block",
            "",
            "WorldPlay's four-frame latent block is 1,560 rows in its documented",
            "480x832 setting. It caches text and forms a visual K/V cache, but it",
            "dynamically selects and re-encodes history at each chunk. Its standard",
            f"roofline result is {_fmt_ratio(screens['HY-World 1.5 WorldPlay 8B distilled']['roofline_storage_attribution'])};",
            "under the same-compute attribution contract, the impossible",
            "zero-ROM-cost/additive endpoint is only "
            f"{_fmt_ratio(screens['HY-World 1.5 WorldPlay 8B distilled']['zero_cost_rom_additive_upper_bound'])}; "
            "context-cache construction, K/V, and NoC remain outside this screen.",
            "Only an identical nonnegative serialized term is guaranteed to reduce",
            "the ratio when ROM weight service is no slower; architecture-dependent",
            "HBM contention can change the end-to-end result in either direction.",
            "",
            "### EVOKE, AlayaWorld, and Matrix-Game",
            "",
            "These systems achieve or approach interactivity through model changes:",
            "few-step distillation, bounded/retrieved world memory, shorter chunks,",
            "quantization, VAE pruning, and asynchronous pipelines. Their current",
            "blocks remain 2,040 to 8,800 rows in the retained screens; EVOKE's",
            "nine-latent-frame temporal factor is assumed, while the other row",
            "factors are derived from commit-pinned public configurations.",
            "Those techniques are valuable, but they accelerate compute, attention,",
            "memory growth, or pipeline latency rather than recurring weight reads.",
            "",
            "### Cosmos 3 proves labels are insufficient",
            "",
            "One checkpoint family exposes two different hardware shapes. The",
            "Reasoner uses causal self-attention and next-token text prediction, while",
            "the Generator routes noisy visual/audio/action tokens through full",
            "attention and diffusion MLPs. The generic q=1 linear-only control in the",
            f"artifact reaches {_fmt_ratio(result['generic_token_decode_control']['roofline_storage_attribution'])} ROM attribution",
            "before KV/NoC, but that is illustrative and is not a Cosmos number; the",
            "Cosmos active weights, dtypes, and runtime row geometry remain null.",
            "The Generator is H3-like despite living in a",
            "unified autoregressive/diffusion architecture. The runtime branch, not",
            "the model-family label, determines ROM suitability.",
            "",
            "## Bottleneck map",
            "",
            "| Execution shape | What caching changes | Likely remaining bound | ROM-as-storage implication |",
            "|---|---|---|---|",
            "| Full-clip bidirectional DiT (H3) | Cross-step feature caches may be approximate; no exact persistent AR K/V | Dense linear compute, attention, sequence-parallel communication | Essentially no storage gain |",
            "| Outer AR, wide current frame/chunk (LingBot, WorldPlay, EVOKE, Matrix-Game) | Removes or bounds historical recomputation | Current-block GEMMs, attention, mutable K/V, all-to-all/NoC, VAE | Usually secondary or immaterial |",
            "| Outer AR, undisclosed current element (Atlas, RTFM) | Can remove historical prefill | Unknown until query rows and K/V traffic are published | Conditional, not quantifiable |",
            "| Narrow causal frame state (Oasis cache candidate) | Collapses a full window to one 144-row frame | Weight service can reappear, then KV and NoC become decisive | Meaningful under local cache and batched weight reuse |",
            "| Generic true q=1 token decode (Qwen/DeepSeek; Cosmos Reasoner is structurally similar but unquantified) | Reuses historical K/V while applying matrices to one new row | Weight read first; KV/communication at long context | OpenTallas's intended regime |",
            "",
            "Within the isolated linear roofline, a compute-bound call receives no",
            "benefit from moving its immutable weights. An identical nonnegative",
            "serialized term can only reduce an existing ratio when the ROM path is no",
            "slower. Architecture-dependent mutable-HBM contention, attention, and",
            "communication are not shared terms and require a full model; they can",
            "change the end-to-end ratio, as the existing Oasis sensitivities show.",
            "",
            "## Relation to the existing Oasis/H3 study",
            "",
            "The generic row screen predicts "
            f"{_fmt_ratio(screens['Oasis causal-cache candidate']['roofline_storage_attribution'])} for an ideal",
            "144-row linear-only Oasis call. The full existing study",
            "adds frame-conditioned matrices, VAE, mutable temporal K/V, and a 50%",
            "NoC critical cut and obtains "
            f"{cross['central_oasis_cached_rom_storage_speedup']:.3f}x. That direction and reduction are internally consistent.",
            "",
            "For MiniMax-H3, the 38,222-row screen is 1.000x and the zero-cost",
            f"additive ceiling is {_fmt_ratio(screens['MiniMax-H3 dense 5.17-second control']['zero_cost_rom_additive_upper_bound'])}.",
            "The full H3 study, including modeled attention communication but",
            "favorably omitting Q/K/V HBM service, also obtains "
            f"{cross['h3_rom_storage_speedup_min']:.3f}x-"
            f"{cross['h3_rom_storage_speedup_max']:.3f}x.",
            "",
            "## Real-time interpretation",
            "",
            "Vendor systems demonstrate real-time or interactive generation: RTFM",
            "reports interactive rates on one H100,",
            "WorldPlay reports 24 fps, and Matrix-Game reports up to 40 fps at",
            "720p. EVOKE reports 36 frames in 2.11 seconds, about 17.1 generated",
            "frames/s for a 24-fps stream. These are differently scoped vendor",
            "results, not an apples-to-apples benchmark. They do not identify the",
            "runtime bottleneck and therefore neither validate nor refute the isolated",
            "immutable-weight screen.",
            "",
            "For the wide-block models, the productive acceleration targets are",
            "fewer denoiser calls, smaller current chunks, greater spatial/temporal",
            "compression, sparse/local attention, lower-precision compute, exact",
            "history-state reuse, local KV placement, faster VAE decode, and",
            "pipeline overlap. A fixed-weight compute fabric might still raise the",
            "compute roof, but that is a separate compute-in-ROM implementation",
            "claim; it cannot be credited from immutable ROM bandwidth alone.",
            "",
            "## Decision and next evidence gate",
            "",
            "OpenTallas should not claim an Atlas video-generation speedup today.",
            "Atlas and RTFM should be marked candidates awaiting disclosure or",
            "measurement. A model advances to a full ROM study only after the",
            "following are pinned:",
            "",
            "1. the exact output element/chunk and dominant-matrix query rows;",
            "2. active weight bytes and number of calls per interactive response;",
            "3. exact cache validity across denoising steps and world updates;",
            "4. K/V reads/writes and attention materialization per call;",
            "5. sequence/tensor parallel collectives and physical cache placement;",
            "6. measured end-to-end latency with VAE and serving overhead.",
            "",
            "The immediate open implementation target remains the 144-row Oasis",
            "causal-frame-state experiment. Among released recent models, LingBot is",
            "the best validation target for the opposite result: it can prove that",
            "a correct KV cache does not imply a weight-bound decoder.",
            "",
            "## Reproduction",
            "",
            "    make world-model-landscape",
            "    PYTHONPATH=src pytest -q tests/test_world_model_landscape_study.py",
            "",
            "Inputs: the hash-pinned local recent-model inventory, study config, existing",
            "Oasis/H3 result, and leading-node hardware envelope linked below.",
            "",
            "- [Recent-model inventory](../../data/world-model/recent-world-models-2026-09.json)",
            "- [Study config](../../configs/studies/world_model_landscape_rom.json)",
            "- [Existing Oasis/H3 study](../world-model/REPORT.md)",
            "- [Leading-node hardware envelope](../../configs/hardware/leading_node_market.json)",
            "- [Compute-in-ROM semantics](../../docs/COMPUTE_IN_ROM_MECHANISM.md)",
            "- [World Labs Atlas](https://www.worldlabs.ai/blog/atlas)",
            "- [World Labs RTFM](https://www.worldlabs.ai/blog/rtfm)",
            "- [EVOKE pinned source](https://github.com/AlayaLab/Evoke/tree/4d588f8711793982bfb6db07f70c0dc6e3dc9066)",
            "- [AlayaWorld pinned source](https://github.com/AlayaLab/AlayaWorld/tree/ea03cfbb2e4c4e9102ed8ea8562e0b5370ca9b79)",
            "- [LingBot-World-Infinity pinned source](https://github.com/Robbyant/lingbot-world-v2/tree/2648877f763a06cc743bcd919936da4d25f12e7b)",
            "- [HY-WorldPlay pinned source](https://github.com/Tencent-Hunyuan/HY-WorldPlay/tree/1588e1336e842b03b0a7860c654ebd7c46bb065e)",
            "- [Matrix-Game 3.0 pinned source](https://github.com/SkyworkAI/Matrix-Game/tree/71c3cd7f741311f8100f6cf9cde942b6c1378d11/Matrix-Game-3)",
            "- [Cosmos 3 pinned source](https://github.com/NVIDIA/cosmos/tree/9aa98e5a0773a5558f07d2699e640858f7ca8827)",
            "- [Cosmos 3 technical report](https://research.nvidia.com/labs/cosmos-lab/cosmos3/technical-report.pdf)",
            "",
        ]
    )
    return "\n".join(lines)


def build() -> tuple[dict[str, Any], str, str]:
    config, config_identity = _load_config()
    _validate_config(config)
    _inventory_path, inventory, inventory_identity = _load_pinned_json(
        config["inventory"], label="inventory"
    )
    _hardware_path, hardware, hardware_identity = _load_pinned_json(
        config["hardware_config"], label="hardware config"
    )
    _existing_path, existing, existing_identity = _load_pinned_json(
        config["existing_world_model_study"],
        label="existing world-model study",
    )
    _validate_inventory(
        inventory,
        expected_date=config["as_of_date"],
        expected_rows=set(config["row_sweep"]),
    )

    runner_path = Path(__file__).resolve()
    world_model_path = ROOT / "src/opentallas/world_model.py"
    schema_path = ROOT / "src/opentallas/schema.py"
    producer_identity = {
        "runner": {
            "path": str(runner_path.relative_to(ROOT)),
            "sha256": _sha256_bytes(runner_path.read_bytes()),
        },
        "analytical_module": {
            "path": str(world_model_path.relative_to(ROOT)),
            "sha256": _sha256_bytes(world_model_path.read_bytes()),
        },
        "schema_module": {
            "path": str(schema_path.relative_to(ROOT)),
            "sha256": _sha256_bytes(schema_path.read_bytes()),
        },
    }

    rom = _find_architecture(
        hardware,
        config["comparison_architectures"]["rom"],
        expected_kind="rom",
    )
    gpu = _find_architecture(
        hardware,
        config["comparison_architectures"]["gpu"],
        expected_kind="gpu",
    )
    same_hbm_rate = _same_compute_hbm_rate(rom)
    rom_weight_rate = _rom_weight_rate(rom)
    gpu_hbm_rate = _gpu_hbm_rate(gpu)

    hardware_formats: list[dict[str, Any]] = []
    sweeps_by_label: dict[str, list[dict[str, Any]]] = {}
    label_by_format = {
        "bf16_x_bf16": "BF16",
        "fp8_e4m3_x_fp8_e4m3": "FP8",
    }
    for format_input in config["numeric_format_sweeps"]:
        compute_format = format_input["compute_format"]
        label = label_by_format[compute_format]
        weight_bytes = format_input["weight_bytes_per_parameter"]
        rom_compute = _phase_compute_rate(rom, compute_format)
        gpu_compute = _phase_compute_rate(gpu, compute_format)
        format_result = {
            "label": label,
            "compute_format": compute_format,
            "weight_bytes_per_parameter": weight_bytes,
            "rom_phase_compute_ops_s": rom_compute,
            "same_compute_hbm_weight_bytes_s": same_hbm_rate,
            "rom_weight_bytes_s": rom_weight_rate,
            "same_compute_hbm_ridge_rows": (
                weight_bytes * rom_compute / (2.0 * same_hbm_rate)
            ),
            "rom_ridge_rows": (weight_bytes * rom_compute / (2.0 * rom_weight_rate)),
            "gpu_phase_compute_ops_s": gpu_compute,
            "gpu_hbm_weight_bytes_s": gpu_hbm_rate,
            "gpu_hbm_ridge_rows": (weight_bytes * gpu_compute / (2.0 * gpu_hbm_rate)),
            "rom_over_gpu_compute_rate": rom_compute / gpu_compute,
            "bandwidth_storage_attribution_ceiling": (rom_weight_rate / same_hbm_rate),
        }
        hardware_formats.append(format_result)
        format_rows: list[dict[str, Any]] = []
        for rows in config["row_sweep"]:
            screen = linear_row_storage_roofline(
                rows_per_call=rows,
                active_matrix_parameters=config["active_matrix_parameters_normalizer"],
                calls=config["calls_normalizer"],
                weight_bytes_per_parameter=weight_bytes,
                compute_ops_s=rom_compute,
                hbm_weight_bytes_s=same_hbm_rate,
                rom_weight_bytes_s=rom_weight_rate,
            )
            screen.update(
                _actual_architecture_screen(
                    rows=rows,
                    active_parameters=config["active_matrix_parameters_normalizer"],
                    calls=config["calls_normalizer"],
                    weight_bytes=weight_bytes,
                    gpu_compute=gpu_compute,
                    gpu_hbm=gpu_hbm_rate,
                    rom_compute=rom_compute,
                    rom_weight=rom_weight_rate,
                )
            )
            format_rows.append(screen)
        sweeps_by_label[label] = format_rows

    bf16_hardware = next(item for item in hardware_formats if item["label"] == "BF16")
    bf16_rows = {item["rows_per_call"]: item for item in sweeps_by_label["BF16"]}
    model_screens = []
    for model in inventory["models"]:
        rows = model["current_rows_per_call"]
        if rows is None:
            continue
        screen = dict(
            bf16_rows.get(rows)
            or linear_row_storage_roofline(
                rows_per_call=rows,
                active_matrix_parameters=config["active_matrix_parameters_normalizer"],
                calls=config["calls_normalizer"],
                weight_bytes_per_parameter=2.0,
                compute_ops_s=bf16_hardware["rom_phase_compute_ops_s"],
                hbm_weight_bytes_s=same_hbm_rate,
                rom_weight_bytes_s=rom_weight_rate,
            )
        )
        screen.update(
            {
                "model": model["model"],
                "rows_over_same_compute_hbm_ridge": (
                    rows / bf16_hardware["same_compute_hbm_ridge_rows"]
                ),
                "classification": _classification(screen),
            }
        )
        model_screens.append(screen)

    thresholds: dict[str, Any] = {}
    ridge = bf16_hardware["same_compute_hbm_ridge_rows"]
    attribution_ceiling = bf16_hardware["bandwidth_storage_attribution_ceiling"]
    for target in config["target_storage_attribution_thresholds"]:
        if not 1.0 < target <= attribution_ceiling:
            raise RuntimeError(
                f"storage-attribution target {target} is outside (1, ceiling]"
            )
        roofline_boundary = ridge / target
        zero_cost_boundary = ridge / (target - 1.0)
        thresholds[str(target)] = {
            "metric": config["threshold_metric"],
            "continuous_roofline_boundary_rows": roofline_boundary,
            "largest_integer_row_meeting_roofline_target": math.floor(
                roofline_boundary
            ),
            "continuous_zero_cost_additive_boundary_rows": zero_cost_boundary,
            "largest_integer_row_meeting_zero_cost_additive_target": math.floor(
                zero_cost_boundary
            ),
        }

    atlas_conditions = {
        "any_roofline_benefit_continuous_upper_boundary_rows": ridge,
        "largest_integer_row_with_any_roofline_benefit": math.ceil(ridge) - 1,
        "standard_1_1x_continuous_boundary_rows": thresholds["1.1"][
            "continuous_roofline_boundary_rows"
        ],
        "standard_1_1x_largest_integer_row": thresholds["1.1"][
            "largest_integer_row_meeting_roofline_target"
        ],
        "standard_2x_continuous_boundary_rows": thresholds["2.0"][
            "continuous_roofline_boundary_rows"
        ],
        "standard_2x_largest_integer_row": thresholds["2.0"][
            "largest_integer_row_meeting_roofline_target"
        ],
        "interpretation": (
            "Generic dominant-matrix row boundaries only; Atlas query geometry "
            "is unpublished and remains numerically null."
        ),
    }

    token_control = linear_row_storage_roofline(
        rows_per_call=1,
        active_matrix_parameters=config["active_matrix_parameters_normalizer"],
        calls=config["calls_normalizer"],
        weight_bytes_per_parameter=2.0,
        compute_ops_s=bf16_hardware["rom_phase_compute_ops_s"],
        hbm_weight_bytes_s=same_hbm_rate,
        rom_weight_bytes_s=rom_weight_rate,
    )

    result = {
        "schema_version": 2,
        "study_id": config["study_id"],
        "as_of_date": config["as_of_date"],
        "comparison_contract": config["comparison_contract"],
        "result_contracts": {
            "storage_attribution": (
                "Same ROM-wafer compute and pipeline; only immutable-weight "
                "service changes between the profile's per-stage HBM and ROM paths."
            ),
            "actual_architecture_ratio_not_storage_attribution": (
                "B300 HBM roofline time divided by ROM-wafer roofline time using "
                "each architecture's own compute and immutable-weight rates."
            ),
        },
        "equations": {
            "linear_operations": "2 * calls * active_parameters * rows_per_call",
            "weight_read_bytes": (
                "calls * active_parameters * weight_bytes_per_parameter"
            ),
            "linear_arithmetic_intensity": (
                "2 * rows_per_call / weight_bytes_per_parameter"
            ),
            "hbm_ridge_rows": (
                "weight_bytes_per_parameter * phase_compute_ops_s / "
                "(2 * hbm_weight_bytes_s)"
            ),
            "roofline_storage_attribution": (
                "max(compute_s,hbm_weight_s) / max(compute_s,rom_weight_s)"
            ),
        },
        "hardware_formats": hardware_formats,
        "thresholds": thresholds,
        "row_sweep": sweeps_by_label["BF16"],
        "fp8_row_sweep": sweeps_by_label["FP8"],
        "model_screens": model_screens,
        "generic_token_decode_control": token_control,
        "atlas_conditions": atlas_conditions,
        "inventory_models": inventory["models"],
        "existing_world_model_study": {
            **existing_identity,
            "central_oasis_cached_rom_storage_speedup": existing["findings"][
                "central_oasis_w32_cached_rom_storage_speedup_local_cache"
            ],
            "h3_rom_storage_speedup_min": existing["findings"][
                "h3_rom_storage_speedup_min"
            ],
            "h3_rom_storage_speedup_max": existing["findings"][
                "h3_rom_storage_speedup_max"
            ],
        },
        "input_identity": {
            "config": config_identity,
            "inventory": inventory_identity,
            "hardware": hardware_identity,
            "existing_world_model_study": existing_identity,
        },
        "producer": producer_identity,
        "evidence_boundary": [
            "No audited recent model was executed by OpenTallas.",
            "Atlas and RTFM disclose no model size, latent query geometry, "
            "denoising schedule, cache tensor inventory, latency, or exact hardware.",
            "Four surveyed row counts are source-derived favorable current-block "
            "lower bounds; EVOKE's temporal factor and H3's text-row component "
            "are explicit assumptions. None is a complete FLOP, KV, attention, "
            "communication, or VAE model.",
            "The zero-cost-ROM result is a storage-only upper endpoint, not a "
            "prediction.",
            "The actual B300-versus-ROM architecture ratio changes compute as "
            "well as storage and is not storage attribution.",
            "Atlas and RTFM are dated mutable-page observations without retained "
            "snapshots; the open implementations use commit and file pins.",
            "OpenTallas has no video ABI/compiler/runtime/RTL or fabricated ROM "
            "implementation for any audited model.",
        ],
    }

    csv_buffer = io.StringIO()
    fields = [
        "format_label",
        "compute_format",
        "rows_per_call",
        "arithmetic_intensity_ops_per_weight_byte",
        "compute_service_s",
        "hbm_weight_service_s",
        "rom_weight_service_s",
        "hbm_binding_term",
        "rom_binding_term",
        "roofline_storage_attribution",
        "additive_storage_attribution",
        "zero_cost_rom_additive_upper_bound",
        "actual_architecture_ratio_not_storage_attribution",
        "gpu_actual_binding_term",
        "rom_actual_binding_term",
    ]
    writer = csv.DictWriter(csv_buffer, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    format_field = {item["label"]: item["compute_format"] for item in hardware_formats}
    for label, rows in (
        ("BF16", result["row_sweep"]),
        ("FP8", result["fp8_row_sweep"]),
    ):
        for row in rows:
            writer.writerow(
                {
                    **{key: row[key] for key in fields[2:]},
                    "format_label": label,
                    "compute_format": format_field[label],
                }
            )

    return result, _report(result), csv_buffer.getvalue()


def main() -> int:
    result, report, sweep = build()
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    (OUTPUT_ROOT / "analytical.json").write_text(
        json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
    )
    (OUTPUT_ROOT / "REPORT.md").write_text(report)
    (OUTPUT_ROOT / "row_sweep.csv").write_text(sweep)
    print(f"wrote {OUTPUT_ROOT.relative_to(ROOT)}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
