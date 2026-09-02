#!/usr/bin/env python3
"""Generate the pinned Oasis causal-state and MiniMax-H3 ROM study."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from opentallas.schema import ArchitectureProfile  # noqa: E402
from opentallas.world_model import (  # noqa: E402
    H3Spec,
    OasisSpec,
    VideoWorkload,
    evaluate_video_workload,
    h3_clip_workload,
    oasis_frame_workload,
)


CONFIG_PATH = ROOT / "configs/studies/world_model_rom.json"
OUTPUT_ROOT = ROOT / "results/world-model"
CSV_FIELDS = (
    "study_slice",
    "model",
    "scenario",
    "architecture",
    "window_frames",
    "cache_mode",
    "clip_duration_s",
    "denoise_calls",
    "attention_density",
    "noc_critical_cut_fraction",
    "cache_remote_fraction",
    "rom_row_reuse",
    "tensor_operations",
    "weight_read_bytes",
    "mutable_hbm_bytes",
    "rom_latency_s",
    "same_compute_hbm_latency_s",
    "rom_storage_speedup",
    "generated_rate_fps",
    "real_time_factor",
    "main_compute_service_s",
    "main_immutable_service_s",
    "main_mutable_service_s",
    "main_storage_service_s",
    "main_noc_serialization_floor_s",
    "main_largest_modeled_term",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _load_pinned(entry: dict[str, Any]) -> tuple[Path, dict[str, Any]]:
    path = ROOT / entry["path"]
    actual = _sha256(path)
    if actual != entry["sha256"]:
        raise RuntimeError(
            f"input drift for {entry['path']}: expected {entry['sha256']}, "
            f"got {actual}"
        )
    return path, _load_json(path)


def _profile_map(hardware: dict[str, Any]) -> dict[str, ArchitectureProfile]:
    entries = hardware["wafer_architectures"] + hardware["gpu_architectures"]
    return {
        entry["name"]: ArchitectureProfile.from_dict(entry) for entry in entries
    }


def _assumed_value(entry: dict[str, Any]) -> Any:
    return entry["value"]


def _row_reuse(value: str | int) -> int | None:
    return None if value == "whole_call" else int(value)


def _phase_summary(phase: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "phase",
        "tensor_operations",
        "weight_read_bytes",
        "mutable_hbm_bytes",
        "rom_array_service_bytes",
        "critical_cut_bytes",
        "compute_service_s",
        "weight_service_s",
        "mutable_service_s",
        "storage_service_s",
        "noc_serialization_floor_s",
        "core_service_s",
        "phase_latency_s",
        "binding_core_term",
        "binding_storage_term",
        "largest_modeled_term",
    )
    return {key: phase[key] for key in keys}


def _evaluation_summary(
    evaluated: dict[str, Any], workload: VideoWorkload
) -> dict[str, Any]:
    result = {
        key: evaluated[key]
        for key in (
            "model",
            "scenario",
            "unit",
            "architecture",
            "storage_policy",
            "target_interval_s",
            "latency_s",
            "real_time_factor",
            "meets_target_interval",
            "units_per_s",
            "noc_critical_cut_fraction",
            "cache_remote_fraction",
            "rom_row_reuse",
            "effective_compute_ops_s",
            "effective_weight_bytes_s",
            "effective_mutable_bytes_s",
            "effective_wafer_bisection_bytes_s",
        )
    }
    if "generated_fps" in evaluated:
        result["generated_fps"] = evaluated["generated_fps"]
    if "generated_video_fps" in evaluated:
        result["generated_video_fps"] = evaluated["generated_video_fps"]
    result.update(
        {
            "tensor_operations": workload.tensor_operations,
            "weight_read_bytes": workload.weight_read_bytes,
            "mutable_hbm_bytes": workload.mutable_hbm_bytes,
            "noc_tensor_injected_bytes": workload.noc_tensor_injected_bytes,
            "noc_cache_injected_bytes": workload.noc_cache_injected_bytes,
            "metadata": workload.metadata,
            "phases": [_phase_summary(phase) for phase in evaluated["phases"]],
        }
    )
    return result


def _evaluate(
    workload: VideoWorkload,
    arch: ArchitectureProfile,
    *,
    policy: str,
    noc_cut: float,
    cache_remote: float = 0.0,
    row_reuse: int | None = None,
) -> dict[str, Any]:
    evaluated = evaluate_video_workload(
        workload,
        arch,
        storage_policy=policy,  # type: ignore[arg-type]
        noc_critical_cut_fraction=noc_cut,
        cache_remote_fraction=cache_remote,
        rom_row_reuse=row_reuse,
    )
    return _evaluation_summary(evaluated, workload)


def _main_phase(point: dict[str, Any]) -> dict[str, Any]:
    return point["phases"][0]


def _comparison(
    workload: VideoWorkload,
    rom_point: dict[str, Any],
    hbm_point: dict[str, Any],
) -> dict[str, Any]:
    return {
        "model": workload.model,
        "scenario": workload.scenario,
        "unit": workload.unit,
        "architecture": rom_point["architecture"],
        "window_frames": workload.metadata.get("window_frames"),
        "cache_mode": workload.metadata.get("cache_mode"),
        "clip_duration_s": workload.metadata.get("clip_duration_s"),
        "denoise_calls": workload.metadata.get("denoise_calls"),
        "attention_density": workload.metadata.get("attention_density"),
        "noc_critical_cut_fraction": rom_point["noc_critical_cut_fraction"],
        "cache_remote_fraction": rom_point["cache_remote_fraction"],
        "rom_row_reuse": rom_point["rom_row_reuse"],
        "tensor_operations": workload.tensor_operations,
        "weight_read_bytes": workload.weight_read_bytes,
        "mutable_hbm_bytes": workload.mutable_hbm_bytes,
        "rom_latency_s": rom_point["latency_s"],
        "same_compute_hbm_latency_s": hbm_point["latency_s"],
        "rom_storage_speedup": hbm_point["latency_s"] / rom_point["latency_s"],
        "rom_generated_rate_fps": rom_point.get(
            "generated_fps", rom_point.get("generated_video_fps")
        ),
        "rom_real_time_factor": rom_point["real_time_factor"],
        "rom_main_phase": _main_phase(rom_point),
        "same_compute_hbm_main_phase": _main_phase(hbm_point),
    }


def _csv_row(study_slice: str, item: dict[str, Any]) -> dict[str, Any]:
    main = item["rom_main_phase"]
    return {
        "study_slice": study_slice,
        "model": item["model"],
        "scenario": item["scenario"],
        "architecture": item["architecture"],
        "window_frames": item["window_frames"],
        "cache_mode": item["cache_mode"],
        "clip_duration_s": item["clip_duration_s"],
        "denoise_calls": item["denoise_calls"],
        "attention_density": item["attention_density"],
        "noc_critical_cut_fraction": item["noc_critical_cut_fraction"],
        "cache_remote_fraction": item["cache_remote_fraction"],
        "rom_row_reuse": item["rom_row_reuse"],
        "tensor_operations": item["tensor_operations"],
        "weight_read_bytes": item["weight_read_bytes"],
        "mutable_hbm_bytes": item["mutable_hbm_bytes"],
        "rom_latency_s": item["rom_latency_s"],
        "same_compute_hbm_latency_s": item["same_compute_hbm_latency_s"],
        "rom_storage_speedup": item["rom_storage_speedup"],
        "generated_rate_fps": item["rom_generated_rate_fps"],
        "real_time_factor": item["rom_real_time_factor"],
        "main_compute_service_s": main["compute_service_s"],
        "main_immutable_service_s": main["weight_service_s"],
        "main_mutable_service_s": main["mutable_service_s"],
        "main_storage_service_s": main["storage_service_s"],
        "main_noc_serialization_floor_s": main[
            "noc_serialization_floor_s"
        ],
        "main_largest_modeled_term": main["largest_modeled_term"],
    }


def _assert_inventory(oasis: OasisSpec, h3: H3Spec, oi: dict, hi: dict) -> None:
    derived = oi["code_derived_inventory"]
    expected_oasis = {
        "dit_frame_row_parameters": oasis.dit_frame_row_parameters,
        "dit_parameters": oasis.dit_parameters,
        "dit_token_row_parameters": oasis.dit_token_row_parameters,
        "dit_weight_bytes_bf16_equivalent": oasis.dit_weight_bytes,
        "static_dit_plus_complete_vae_bytes_bf16_equivalent": (
            oasis.static_model_parameters
            * oasis.runtime_weight_bytes_per_parameter
        ),
        "static_dit_plus_complete_vae_parameters": oasis.static_model_parameters,
        "vae_decoder_parameters": oasis.vae_decoder_parameters,
        "vae_decoder_weight_bytes_bf16_equivalent": (
            oasis.vae_decoder_weight_bytes
        ),
    }
    if expected_oasis != derived:
        raise RuntimeError(
            f"Oasis inventory/formula mismatch: {expected_oasis!r} != {derived!r}"
        )
    active = hi["active_inference_inventory"]
    if h3.main_matrix_parameters != active["main_matrix_parameters"]:
        raise RuntimeError("H3 main-matrix inventory/formula mismatch")
    categories = (
        active["main_adaln_precomputable_bytes"]
        + active["main_attention_bytes"]
        + active["main_mlp_bytes"]
        + active["main_norm_and_other_bytes"]
        + active["token_refiner_bytes"]
        + active["other_io_time_final_bytes"]
    )
    if categories != active["full_transformer_weight_bytes"]:
        raise RuntimeError("H3 inventory categories do not close to total bytes")
    if (
        categories - active["main_adaln_precomputable_bytes"]
        != active["active_transformer_weight_bytes_per_call"]
    ):
        raise RuntimeError("H3 active inference inventory does not close")


def _assert_source_pin_alignment(
    config: dict[str, Any], oasis_inventory: dict, h3_inventory: dict
) -> None:
    """Refuse a config whose displayed source pins disagree with its inputs."""

    fields = ("repo", "revision", "huggingface_repo", "huggingface_revision")
    for label, inventory in (
        ("oasis", oasis_inventory),
        ("minimax_h3", h3_inventory),
    ):
        configured = {key: config["source_pins"][label].get(key) for key in fields}
        authenticated = {key: inventory.get(key) for key in fields}
        if configured != authenticated:
            raise RuntimeError(
                f"{label} source-pin mismatch: {configured!r} != {authenticated!r}"
            )


def build(config_path: Path = CONFIG_PATH) -> dict[str, Any]:
    config = _load_json(config_path)
    hardware_path, hardware = _load_pinned(config["inputs"]["hardware"])
    oasis_path, oasis_inventory = _load_pinned(
        config["inputs"]["oasis_inventory"]
    )
    h3_path, h3_inventory = _load_pinned(config["inputs"]["h3_inventory"])
    _assert_source_pin_alignment(config, oasis_inventory, h3_inventory)
    profiles = _profile_map(hardware)

    oasis_arch = oasis_inventory["architecture"]
    oasis = OasisSpec(
        output_height=oasis_arch["output_height"],
        output_width=oasis_arch["output_width"],
        vae_patch_size=oasis_arch["vae_patch_size"],
        dit_patch_size=oasis_arch["dit_patch_size"],
        latent_channels=oasis_arch["latent_channels"],
        hidden_size=oasis_arch["hidden_size"],
        layers=oasis_arch["layers"],
        heads=oasis_arch["heads"],
        mlp_ratio=oasis_arch["mlp_ratio"],
        max_frames=oasis_arch["max_frames"],
        action_dim=oasis_arch["action_dim"],
        diffusion_steps=oasis_arch[
            "diffusion_forward_calls_per_generated_frame"
        ],
        context_timestep=oasis_arch["context_timestep"],
        runtime_weight_bytes_per_parameter=_assumed_value(
            config["assumptions"]["oasis"][
                "runtime_weight_bytes_per_parameter"
            ]
        ),
        vae_encoder_layers=oasis_arch["vae_encoder_layers"],
        vae_decoder_layers=oasis_arch["vae_decoder_layers"],
    )
    h3_arch = h3_inventory["architecture"]
    h3_active = h3_inventory["active_inference_inventory"]
    h3 = H3Spec(
        hidden_size=h3_arch["hidden_size"],
        layers=h3_arch["num_layers"],
        attention_inner_dim=h3_arch["attention_inner_dim"],
        ffn_hidden_size=h3_arch["ffn_dim"],
        denoise_calls=_assumed_value(
            config["assumptions"]["h3"]["base_denoise_calls"]
        ),
        active_transformer_weight_bytes=h3_active[
            "active_transformer_weight_bytes_per_call"
        ],
        full_transformer_weight_bytes=h3_active[
            "full_transformer_weight_bytes"
        ],
        text_tokens=_assumed_value(
            config["assumptions"]["h3"]["text_tokens"]
        ),
        video_tokens_per_latent_frame=(1344 // 32) * (768 // 32),
        sequence_parallel_degree=_assumed_value(
            config["assumptions"]["h3"]["sequence_parallel_degree"]
        ),
    )
    _assert_inventory(oasis, h3, oasis_inventory, h3_inventory)

    selected_gpu = config["inputs"]["hardware"]["selected_gpu_profiles"]
    selected_rom = config["inputs"]["hardware"]["selected_rom_profiles"]
    b300_x1 = profiles[selected_gpu[0]]
    b300_x8 = profiles[selected_gpu[1]]
    rom_profiles = [profiles[name] for name in selected_rom]
    central = next(profile for profile in rom_profiles if "central" in profile.name)
    noc_cut = _assumed_value(
        config["assumptions"]["noc"]["baseline_critical_cut_fraction"]
    )
    target_fps = _assumed_value(
        config["assumptions"]["oasis"]["target_fps"]
    )
    cache_fill = _assumed_value(
        config["assumptions"]["oasis"]["cache_fill_passes"]
    )

    baseline_points: list[dict[str, Any]] = []
    rom_attribution: list[dict[str, Any]] = []
    sweep_rows: list[dict[str, Any]] = []
    oasis_workloads: dict[tuple[int, str], VideoWorkload] = {}
    oasis_point_map: dict[tuple[int, str, str, str], dict[str, Any]] = {}

    for window in config["assumptions"]["oasis"]["window_frames"]:
        for mode in ("reference_recompute", "causal_kv_cache"):
            workload = oasis_frame_workload(
                oasis,
                window_frames=window,
                cache_mode=mode,
                cache_fill_passes=cache_fill,
                target_fps=target_fps,
            )
            oasis_workloads[(window, mode)] = workload
            gpu_point = _evaluate(
                workload,
                b300_x1,
                policy="gpu_hbm",
                noc_cut=noc_cut,
            )
            baseline_points.append(gpu_point)
            oasis_point_map[(window, mode, b300_x1.name, "gpu_hbm")] = gpu_point
            for rom_arch in rom_profiles:
                rom_point = _evaluate(
                    workload,
                    rom_arch,
                    policy="rom",
                    noc_cut=noc_cut,
                )
                hbm_point = _evaluate(
                    workload,
                    rom_arch,
                    policy="same_compute_hbm",
                    noc_cut=noc_cut,
                )
                baseline_points.extend((rom_point, hbm_point))
                oasis_point_map[(window, mode, rom_arch.name, "rom")] = rom_point
                oasis_point_map[
                    (window, mode, rom_arch.name, "same_compute_hbm")
                ] = hbm_point
                compared = _comparison(workload, rom_point, hbm_point)
                rom_attribution.append(compared)
                sweep_rows.append(_csv_row("baseline", compared))

    cache_effects: list[dict[str, Any]] = []
    targets = [(b300_x1.name, "gpu_hbm")]
    targets.extend(
        (arch.name, policy)
        for arch in rom_profiles
        for policy in ("rom", "same_compute_hbm")
    )
    for window in config["assumptions"]["oasis"]["window_frames"]:
        for architecture, policy in targets:
            reference = oasis_point_map[
                (window, "reference_recompute", architecture, policy)
            ]
            cached = oasis_point_map[
                (window, "causal_kv_cache", architecture, policy)
            ]
            cache_effects.append(
                {
                    "window_frames": window,
                    "architecture": architecture,
                    "storage_policy": policy,
                    "reference_latency_s": reference["latency_s"],
                    "cached_latency_s": cached["latency_s"],
                    "causal_cache_speedup": (
                        reference["latency_s"] / cached["latency_s"]
                    ),
                }
            )

    h3_workloads: dict[tuple[str, str], VideoWorkload] = {}
    h3_point_map: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    h3_variants = (
        ("base_dense", 1.0, h3.denoise_calls),
        (
            "accelerated_best_case",
            _assumed_value(
                config["assumptions"]["h3"][
                    "accelerated_attention_density"
                ]
            ),
            _assumed_value(
                config["assumptions"]["h3"]["accelerated_denoise_calls"]
            ),
        ),
    )
    for case in h3_inventory["sequence_cases"]:
        for variant, density, calls in h3_variants:
            workload = h3_clip_workload(
                h3,
                label=f"{case['label']}-{variant}",
                output_frames=case["output_frames"],
                latent_video_frames=case["latent_video_frames"],
                audio_tokens=case["audio_tokens"],
                attention_density=density,
                denoise_calls=calls,
            )
            h3_workloads[(case["label"], variant)] = workload
            gpu_point = _evaluate(
                workload,
                b300_x8,
                policy="gpu_hbm",
                noc_cut=noc_cut,
            )
            baseline_points.append(gpu_point)
            h3_point_map[(case["label"], variant, b300_x8.name, "gpu_hbm")] = (
                gpu_point
            )
            for rom_arch in rom_profiles:
                rom_point = _evaluate(
                    workload,
                    rom_arch,
                    policy="rom",
                    noc_cut=noc_cut,
                )
                hbm_point = _evaluate(
                    workload,
                    rom_arch,
                    policy="same_compute_hbm",
                    noc_cut=noc_cut,
                )
                baseline_points.extend((rom_point, hbm_point))
                h3_point_map[(case["label"], variant, rom_arch.name, "rom")] = (
                    rom_point
                )
                h3_point_map[
                    (case["label"], variant, rom_arch.name, "same_compute_hbm")
                ] = hbm_point
                compared = _comparison(workload, rom_point, hbm_point)
                rom_attribution.append(compared)
                sweep_rows.append(_csv_row("baseline", compared))

    oasis_sensitivity: list[dict[str, Any]] = []
    cached_w32 = oasis_workloads[(32, "causal_kv_cache")]
    for remote in config["assumptions"]["noc"][
        "cache_remote_fraction_sweep"
    ]["values"]:
        hbm_point = _evaluate(
            cached_w32,
            central,
            policy="same_compute_hbm",
            noc_cut=noc_cut,
            cache_remote=remote,
        )
        for reuse_value in config["assumptions"]["rom_row_reuse"]["sweep"]:
            rom_point = _evaluate(
                cached_w32,
                central,
                policy="rom",
                noc_cut=noc_cut,
                cache_remote=remote,
                row_reuse=_row_reuse(reuse_value),
            )
            compared = _comparison(cached_w32, rom_point, hbm_point)
            oasis_sensitivity.append(compared)
            sweep_rows.append(_csv_row("oasis_cache_placement_row_reuse", compared))

    noc_sensitivity: list[dict[str, Any]] = []
    for mode in ("reference_recompute", "causal_kv_cache"):
        workload = oasis_workloads[(32, mode)]
        for cut in config["assumptions"]["noc"][
            "critical_cut_fraction_sweep"
        ]["values"]:
            rom_point = _evaluate(
                workload,
                central,
                policy="rom",
                noc_cut=cut,
            )
            hbm_point = _evaluate(
                workload,
                central,
                policy="same_compute_hbm",
                noc_cut=cut,
            )
            compared = _comparison(workload, rom_point, hbm_point)
            noc_sensitivity.append(compared)
            sweep_rows.append(_csv_row("oasis_noc_cut", compared))

    h3_sensitivity: list[dict[str, Any]] = []
    for case in h3_inventory["sequence_cases"]:
        for variant, _, _ in h3_variants:
            workload = h3_workloads[(case["label"], variant)]
            hbm_point = _evaluate(
                workload,
                central,
                policy="same_compute_hbm",
                noc_cut=noc_cut,
            )
            for reuse_value in config["assumptions"]["rom_row_reuse"]["sweep"]:
                rom_point = _evaluate(
                    workload,
                    central,
                    policy="rom",
                    noc_cut=noc_cut,
                    row_reuse=_row_reuse(reuse_value),
                )
                compared = _comparison(workload, rom_point, hbm_point)
                h3_sensitivity.append(compared)
                sweep_rows.append(_csv_row("h3_row_reuse", compared))

    central_cached_attr = next(
        item
        for item in rom_attribution
        if item["model"].startswith("Oasis")
        and item["scenario"] == "causal_kv_cache-W32"
        and item["architecture"] == central.name
    )
    central_reference_attr = next(
        item
        for item in rom_attribution
        if item["model"].startswith("Oasis")
        and item["scenario"] == "reference_recompute-W32"
        and item["architecture"] == central.name
    )
    local_per_stream = next(
        item
        for item in oasis_sensitivity
        if item["cache_remote_fraction"] == 0.0
        and item["rom_row_reuse"] == 1
    )
    remote_whole_call = next(
        item
        for item in oasis_sensitivity
        if item["cache_remote_fraction"] == 1.0
        and item["rom_row_reuse"] == "whole_call"
    )
    central_cache_effect = next(
        item
        for item in cache_effects
        if item["window_frames"] == 32
        and item["architecture"] == central.name
        and item["storage_policy"] == "rom"
    )
    h3_storage_values = [
        item["rom_storage_speedup"]
        for item in rom_attribution
        if item["model"] == "MiniMax-H3"
    ]

    h3_b300_model = h3_point_map[
        ("5.17s", "base_dense", b300_x8.name, "gpu_hbm")
    ]
    oasis_b300_model = oasis_point_map[
        (32, "reference_recompute", b300_x1.name, "gpu_hbm")
    ]
    h3_published = config["calibration_points"]["h3_b300"]
    calibration = {
        "h3_b300": {
            "published_latency_s": h3_published["latency_s"],
            "modeled_transformer_only_latency_s": h3_b300_model["latency_s"],
            "modeled_to_published_latency_ratio": (
                h3_b300_model["latency_s"] / h3_published["latency_s"]
            ),
            "required_aggregate_ops_s": (
                h3_b300_model["tensor_operations"] / h3_published["latency_s"]
            ),
            "required_fraction_of_raw_bf16_roof": (
                h3_b300_model["tensor_operations"]
                / h3_published["latency_s"]
                / (
                    b300_x8.device_count
                    * b300_x8.compute_roof("bf16_x_bf16")
                )
            ),
            "source": h3_published["source"],
            "interpretation": (
                "sanity check only; it does not fit or rescale the ROM model"
            ),
        },
        "oasis": {
            "published_demo_fps": config["calibration_points"]["oasis_demo"][
                "reported_fps"
            ],
            "modeled_public_code_b300_x1_tensor_path_fps": oasis_b300_model[
                "generated_fps"
            ],
            "source": config["calibration_points"]["oasis_demo"]["source"],
            "interpretation": (
                "not a numerical calibration: the demo checkpoint, hardware, and "
                "proprietary runtime are not identified well enough"
            ),
        },
        "fast_h3_b200": config["calibration_points"]["fast_h3_b200"],
    }

    capacity = []
    oasis_static_bytes = (
        oasis.static_model_parameters * oasis.runtime_weight_bytes_per_parameter
    )
    for profile in rom_profiles:
        for model, required in (
            ("Oasis DiT + complete VAE BF16-equivalent", oasis_static_bytes),
            ("MiniMax-H3 complete transformer payload", h3.full_transformer_weight_bytes),
        ):
            capacity.append(
                {
                    "architecture": profile.name,
                    "model": model,
                    "required_bytes": required,
                    "available_bytes_one_stage": profile.weight_capacity_bytes_per_device,
                    "fits_one_stage": required
                    <= profile.weight_capacity_bytes_per_device,
                    "capacity_margin": (
                        profile.weight_capacity_bytes_per_device / required
                    ),
                }
            )

    result = {
        "schema_version": 1,
        "study_id": config["study_id"],
        "producer": {
            "runner": {
                "path": "tools/run_world_model_study.py",
                "sha256": _sha256(Path(__file__).resolve()),
            },
            "analytical_module": {
                "path": "src/opentallas/world_model.py",
                "sha256": _sha256(ROOT / "src/opentallas/world_model.py"),
            },
            "schema_module": {
                "path": "src/opentallas/schema.py",
                "sha256": _sha256(ROOT / "src/opentallas/schema.py"),
            },
        },
        "input_identity": {
            "study_config": {
                "path": str(config_path.resolve().relative_to(ROOT)),
                "sha256": _sha256(config_path),
            },
            "hardware": {
                "path": str(hardware_path.relative_to(ROOT)),
                "sha256": _sha256(hardware_path),
            },
            "oasis_inventory": {
                "path": str(oasis_path.relative_to(ROOT)),
                "sha256": _sha256(oasis_path),
            },
            "h3_inventory": {
                "path": str(h3_path.relative_to(ROOT)),
                "sha256": _sha256(h3_path),
            },
            "source_pins": config["source_pins"],
        },
        "comparison_contract": config["comparison_contract"],
        "equations": {
            "operations": "one fused multiply-add = two operations",
            "oasis_full_attention_per_call": (
                "4*L*D*(F*S^2 + S*F*(F+1)/2), with causal temporal attention"
            ),
            "oasis_cached_temporal_kv_bytes": (
                "2(K,V)*L*F*S*D*2 BF16 bytes"
            ),
            "h3_linear_operations_per_call": "2*N*P_main_matrix",
            "h3_attention_operations_per_call": "4*L*N^2*I_attention",
            "phase_time": (
                "max(compute, shared-storage or max(ROM,mutable-HBM)) + "
                "critical-cut NoC serialization; phases serialize"
            ),
            "rom_storage_speedup": (
                "same-compute-HBM latency / ROM latency; this is not ROM versus GPU"
            ),
        },
        "derived_inventory": {
            "oasis": {
                "dit_parameters": oasis.dit_parameters,
                "dit_token_row_parameters": oasis.dit_token_row_parameters,
                "dit_frame_row_parameters": oasis.dit_frame_row_parameters,
                "vae_decoder_parameters": oasis.vae_decoder_parameters,
                "static_model_parameters": oasis.static_model_parameters,
                "static_model_bytes_bf16_equivalent": oasis_static_bytes,
                "spatial_tokens_per_frame": oasis.spatial_tokens_per_frame,
                "temporal_kv_bytes_at_32_frames": oasis.temporal_kv_bytes(32),
            },
            "h3": {
                "main_matrix_parameters": h3.main_matrix_parameters,
                "full_transformer_weight_bytes": h3.full_transformer_weight_bytes,
                "active_transformer_weight_bytes_per_call": (
                    h3.active_transformer_weight_bytes
                ),
                "adaln_precomputed_bytes": (
                    h3.full_transformer_weight_bytes
                    - h3.active_transformer_weight_bytes
                ),
            },
        },
        "capacity": capacity,
        "baseline_points": baseline_points,
        "rom_attribution": rom_attribution,
        "oasis_cache_effects": cache_effects,
        "sensitivities": {
            "oasis_cache_placement_and_row_reuse": oasis_sensitivity,
            "oasis_noc_critical_cut": noc_sensitivity,
            "h3_row_reuse": h3_sensitivity,
        },
        "calibration": calibration,
        "findings": {
            "central_oasis_w32_cache_algorithmic_speedup": central_cache_effect[
                "causal_cache_speedup"
            ],
            "central_oasis_w32_reference_rom_storage_speedup": (
                central_reference_attr["rom_storage_speedup"]
            ),
            "central_oasis_w32_cached_rom_storage_speedup_local_cache": (
                central_cached_attr["rom_storage_speedup"]
            ),
            "central_oasis_w32_cached_rom_storage_speedup_remote_cache": (
                remote_whole_call["rom_storage_speedup"]
            ),
            "central_oasis_w32_cached_rom_storage_speedup_per_stream_proxy": (
                local_per_stream["rom_storage_speedup"]
            ),
            "central_oasis_w32_cached_tensor_path_fps": (
                central_cached_attr["rom_generated_rate_fps"]
            ),
            "h3_rom_storage_speedup_min": min(h3_storage_values),
            "h3_rom_storage_speedup_max": max(h3_storage_values),
            "interpretation": (
                "Causal caching is the large Oasis algorithmic gain. ROM is a "
                "conditional secondary gain only under batched weight service and "
                "local temporal state; full-window Oasis and H3 are compute/NoC "
                "dominated."
            ),
        },
        "sweep_rows": sweep_rows,
        "evidence_boundary": [
            "Analytical and deterministic only: no Oasis/H3 checkpoint execution, compiler lowering, cycle simulation, RTL, physical design, or fabricated ROM measurement.",
            "The causal Oasis cache is a derived transformation. Exactness still requires implementation and latent-output comparison through timestep changes and sliding-window rollover.",
            "The tensor-operation model omits norms, softmax, nonlinearities, RoPE, scheduler work, kernel launches, host/control paths, codecs, and I/O.",
            "Transient H3 Q/K/V traffic is retained as a byte floor in workload metadata but deliberately excluded from HBM service, making H3 favorable.",
            "Service for the precomputed H3 AdaLN output table is also unpriced, making the H3 control favorable.",
            "The accelerated H3 control applies its 10% residual attention density to both attention arithmetic and modeled attention NoC, an intentionally favorable lower bound rather than a reproduction of the FastH3 graph.",
            "The NoC term is a critical-cut serialization floor from assumed placement fractions; it omits propagation, routing contention, multicast realization, and endpoint overhead.",
            "The integer ROM row-reuse sweep is a service-byte proxy. It does not establish the timing, port count, or activation concurrency of digital compute-in-ROM.",
            "OpenTallas currently has no video/world-model ABI, compiler path, scheduler, causal frame-state operator, or video RTL backend.",
        ],
    }
    return result


def _fmt_bytes(value: float) -> str:
    if value >= 1e12:
        return f"{value / 1e12:,.3f} TB"
    if value >= 1e9:
        return f"{value / 1e9:,.3f} GB"
    return f"{value / 1e6:,.3f} MB"


def _fmt_ops(value: float) -> str:
    if value >= 1e15:
        return f"{value / 1e15:,.3f} POP"
    return f"{value / 1e12:,.3f} TOP"


def _fmt_time(value: float, *, unit: str = "ms") -> str:
    if unit == "s":
        return f"{value:,.3f} s"
    return f"{value * 1e3:,.3f} ms"


def _fmt_x(value: float) -> str:
    return f"{value:,.3f}×"


def _find_attr(
    result: dict[str, Any], scenario: str, architecture: str
) -> dict[str, Any]:
    return next(
        item
        for item in result["rom_attribution"]
        if item["scenario"] == scenario and item["architecture"] == architecture
    )


def _find_point(
    result: dict[str, Any], scenario: str, architecture: str, policy: str
) -> dict[str, Any]:
    return next(
        item
        for item in result["baseline_points"]
        if item["scenario"] == scenario
        and item["architecture"] == architecture
        and item["storage_policy"] == policy
    )


def render_report(result: dict[str, Any]) -> str:
    central = "ROM-wafer-N4-class-HBM3e-central"
    findings = result["findings"]
    reference_work = _find_point(
        result, "reference_recompute-W32", central, "rom"
    )
    cached_work = _find_point(result, "causal_kv_cache-W32", central, "rom")
    cached_hbm = _find_point(
        result, "causal_kv_cache-W32", central, "same_compute_hbm"
    )
    h3_base = _find_attr(result, "5.17s-base_dense", central)
    h3_fast_long = _find_attr(
        result, "14.38s-accelerated_best_case", central
    )
    oasis_b300 = _find_point(
        result, "reference_recompute-W32", "NVIDIA-B300-x1", "gpu_hbm"
    )
    h3_conservative_capacity = next(
        item
        for item in result["capacity"]
        if item["architecture"] == "ROM-wafer-N4-class-HBM3e-conservative"
        and item["model"] == "MiniMax-H3 complete transformer payload"
    )

    lines = [
        "# Oasis causal frame state, MiniMax-H3, and immutable ROM",
        "",
        "> **Result class: deterministic analytical study, not video execution or",
        "> silicon evidence.** OpenTallas cannot currently compile or run either",
        "> model. Every absolute rate below is a tensor-path envelope with omitted",
        "> work; use the storage-attribution ratios to answer the ROM question.",
        "",
        "## Executive answer",
        "",
        "DiT is not fundamentally incompatible with ROM. The decisive quantity is",
        "how many activation rows reuse each immutable matrix service:",
        "",
        "- Released Oasis at a 32-frame window is prefill-like: each of 10 calls",
        "  applies the token matrices to 4,608 patch rows. Its central-envelope",
        f"  ROM-only gain is {_fmt_x(findings['central_oasis_w32_reference_rom_storage_speedup'])}.",
        "- A source-derived *candidate* causal temporal-KV transformation reduces",
        "  each call to the current frame's 144 patch rows. It cuts the central",
        f"  modeled frame interval by {_fmt_x(findings['central_oasis_w32_cache_algorithmic_speedup'])};",
        "  that is primarily an algorithmic cache gain, not a ROM gain.",
        "- Once caching removes the full-window recomputation, immutable weights",
        "  become material. With the optimistic current batched-ROM service law and",
        f"  spatially local KV, ROM contributes another {_fmt_x(findings['central_oasis_w32_cached_rom_storage_speedup_local_cache'])}",
        "  over the *same compute and NoC* with weights in HBM. If every cache byte",
        f"  crosses the global bisection, that falls to {_fmt_x(findings['central_oasis_w32_cached_rom_storage_speedup_remote_cache'])};",
        "  under a one-row/per-stream ROM service proxy it falls to",
        f"  {_fmt_x(findings['central_oasis_w32_cached_rom_storage_speedup_per_stream_proxy'])}.",
            "- A recent public full-clip model such as MiniMax-H3 is much",
            "  less favorable. Even after giving it the official",
        "  inference-only AdaLN precompute and a deliberately favorable four-call,",
        "  90%-sparse control, its ROM-storage attribution stays in",
        f"  {_fmt_x(findings['h3_rom_storage_speedup_min'])}–{_fmt_x(findings['h3_rom_storage_speedup_max'])}.",
        "  Dense full-clip arithmetic and sequence communication dominate; there is",
        "  no persistent autoregressive KV cache to turn it into decode.",
        "",
        "The user's prefill intuition is therefore correct for **ROM as immutable",
        "storage**: moving a matrix out of HBM adds little when thousands of rows",
        "already amortize one weight read. A hardwired compute-in-ROM datapath is a",
        "different physical claim; the row-reuse sweep shows that its activation",
        "ports and concurrency must be proved rather than inferred from ROM bandwidth.",
        "",
        "## Identity and evidence discipline",
        "",
        "| Input | Pinned identity | What is actually known |",
        "|---|---|---|",
        "| Oasis source | `etched-ai/open-oasis@f59deef2…` | Public Python architecture and schedule; checkpoint headers unavailable to this study |",
        "| Oasis weights | `Etched/oasis-500m@4ca7d2d…` | Repository revision pinned; payload not profiled |",
        "| MiniMax-H3 source | `MiniMax-AI/MiniMax-H3@d21241f…` | Vendor architecture/model card |",
        "| H3 FL2VA transformer | `MiniMaxAI/MiniMax-H3@42ed227…/FL2VA/transformer` | 535 public tensor headers across 13 shards; 66.280 GB transformer payload |",
        "| Diffusers H3 graph | `huggingface/diffusers@bda3386…` | Forward graph, packed sequence, and denoising schedule |",
        "| Hardware | `leading_node_market.json@8426951…` | Existing assumed/derived N4-class ROM envelopes and published/derived B300 profile |",
        "",
        "Local input and executable-source SHA-256 identities are in",
        "`analytical.json.input_identity` and `analytical.json.producer`; the",
        "inventories carry cited external file hashes, and the human source",
        "register is [SOURCES.md](../../docs/SOURCES.md).",
        "",
        "## Workload derivation",
        "",
        "One fused multiply-add is two operations. Norms, softmax, nonlinearities,",
        "RoPE, scheduler logic, kernel launches, codec work, and I/O are unpriced.",
        "",
        "```text",
        "Oasis full axial attention/call = 4 L D (F S² + S F(F+1)/2)",
        "Oasis temporal KV(F)            = 2 · L · F · S · D · 2 BF16 bytes",
        "H3 main linears/call            = 2 N Pmain",
        "H3 dense attention/call         = 4 L N² Iattn",
        "phase time                      = max(compute, storage) + NoC cut floor",
        "ROM attribution                 = Tsame-compute-HBM / TROM",
        "```",
        "",
        "For Oasis, `S=144`, `D=1,024`, and `L=16`. The released reference",
        "generator performs ten full-window calls. The cache candidate performs ten",
        "current-frame denoise calls plus one conservative cache-fill call at the",
        "fixed context timestep. The extra pass matters: the final denoise call does",
        "not leave a cache at the timestep used for subsequent context frames.",
        "",
        "| Workload | Rows/call | Calls | Tensor operations | Immutable reads | Mutable reads+writes |",
        "|---|---:|---:|---:|---:|---:|",
        f"| Oasis reference W32 | 4,608 | 10 DiT + 1 VAE | {_fmt_ops(reference_work['tensor_operations'])} | {_fmt_bytes(reference_work['weight_read_bytes'])} | {_fmt_bytes(reference_work['mutable_hbm_bytes'])} |",
        f"| Oasis causal cache W32 | 144 | 11 DiT + 1 VAE | {_fmt_ops(cached_work['tensor_operations'])} | {_fmt_bytes(cached_work['weight_read_bytes'])} | {_fmt_bytes(cached_work['mutable_hbm_bytes'])} |",
        f"| H3 dense 5.17 s | 38,222 | 49 transformer | {_fmt_ops(h3_base['tensor_operations'])} | {_fmt_bytes(h3_base['weight_read_bytes'])} | favorable zero-service assumption |",
        "",
        f"The persistent Oasis temporal cache is {_fmt_bytes(result['derived_inventory']['oasis']['temporal_kv_bytes_at_32_frames'])};",
        "31 past frames are read on each cached call. H3 instead materializes Q/K/V",
        "again on every bidirectional denoising call. The 5.17-second case has an",
        f"{_fmt_bytes(_find_point(result, '5.17s-base_dense', central, 'rom')['metadata']['qkv_materialization_floor_bytes'])}",
        "Q/K/V write-plus-read floor, which is deliberately *not* charged to its",
        "HBM time here.",
        "",
        "## What binds at the central W32 point",
        "",
        "All entries below are for the DiT phase; VAE decode is added in the total.",
        "NoC is serialized after the overlapped compute/storage core, so the largest",
        "single term and the total need not be the same concept.",
        "",
        "| Workload / storage | Compute | Weight | Mutable KV | Storage core | NoC floor | DiT total | Largest term |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for label, point in (
        ("Reference / ROM", reference_work),
        (
            "Reference / same-compute HBM",
            _find_point(result, "reference_recompute-W32", central, "same_compute_hbm"),
        ),
        ("Causal cache / ROM", cached_work),
        ("Causal cache / same-compute HBM", cached_hbm),
    ):
        phase = _main_phase(point)
        lines.append(
            f"| {label} | {_fmt_time(phase['compute_service_s'])} | "
            f"{_fmt_time(phase['weight_service_s'])} | "
            f"{_fmt_time(phase['mutable_service_s'])} | "
            f"{_fmt_time(phase['storage_service_s'])} | "
            f"{_fmt_time(phase['noc_serialization_floor_s'])} | "
            f"{_fmt_time(phase['phase_latency_s'])} | "
            f"{phase['largest_modeled_term']} |"
        )

    lines.extend(
        [
            "",
            "The released W32 path is communication/compute dominated and ignores",
            "where weights live. The cached path exposes a three-way balance:",
            "current-frame compute, mutable KV bandwidth, and placement-dependent",
            "communication. ROM helps only because HBM weight service becomes the",
            "largest counterfactual core term after recomputation is removed.",
            "",
            "## Window-length result",
            "",
            "| Window | Reference ROM | Cached ROM | Cache gain | Reference ROM attribution | Cached ROM attribution | B300 cached |",
            "|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for window in (1, 8, 16, 32):
        ref_attr = _find_attr(result, f"reference_recompute-W{window}", central)
        cache_attr = _find_attr(result, f"causal_kv_cache-W{window}", central)
        effect = next(
            item
            for item in result["oasis_cache_effects"]
            if item["window_frames"] == window
            and item["architecture"] == central
            and item["storage_policy"] == "rom"
        )
        gpu = _find_point(
            result,
            f"causal_kv_cache-W{window}",
            "NVIDIA-B300-x1",
            "gpu_hbm",
        )
        lines.append(
            f"| {window} | {_fmt_time(ref_attr['rom_latency_s'])} | "
            f"{_fmt_time(cache_attr['rom_latency_s'])} | "
            f"{_fmt_x(effect['causal_cache_speedup'])} | "
            f"{_fmt_x(ref_attr['rom_storage_speedup'])} | "
            f"{_fmt_x(cache_attr['rom_storage_speedup'])} | "
            f"{_fmt_time(gpu['latency_s'])} |"
        )
    lines.extend(
        [
            "",
            "At W1, the conservative cache-fill pass makes caching slower. As the",
            "window grows, the released path scales with all past patch rows while",
            "the cached path stays nearly flat. That is the causal-frame-state",
            "opportunity; ROM does not create it.",
            "",
            "## Global NoC critical-cut sensitivity",
            "",
            "This sweep keeps temporal KV local and varies the fraction of modeled",
            "attention injection serialized across the global bisection. Zero is an",
            "ideal placement floor; one is the deliberately pessimistic endpoint.",
            "",
            "| W32 path | Critical-cut fraction | Frame interval | ROM attribution | Largest main-phase term |",
            "|---|---:|---:|---:|---|",
        ]
    )
    for item in result["sensitivities"]["oasis_noc_critical_cut"]:
        label = (
            "Reference recompute"
            if item["scenario"] == "reference_recompute-W32"
            else "Causal cache"
        )
        lines.append(
            f"| {label} | {item['noc_critical_cut_fraction']:.0%} | "
            f"{_fmt_time(item['rom_latency_s'])} | "
            f"{_fmt_x(item['rom_storage_speedup'])} | "
            f"{item['rom_main_phase']['largest_modeled_term']} |"
        )

    lines.extend(
        [
            "",
            "The reference path remains at 1.000× ROM attribution throughout:",
            "removing weight traffic cannot shorten its compute/NoC critical path.",
            "The cached path exposes weight service, so its ROM attribution ranges",
            "from 4.286× at the ideal cut to 1.753× at the full-cut endpoint. A ROM",
            "claim without a placement and communication claim is therefore incomplete.",
            "",
            "## Cache placement and ROM service semantics",
            "",
            "This is the central W32 cached workload. `whole_call` is the optimistic",
            "OpenTallas batched ROM-as-storage interpretation: each distinct matrix",
            "is served once per call and all rows reuse it. Integer `R` means a",
            "matrix must be re-served after `R` rows. `R=1` approximates a per-stream",
            "fixed-weight traversal, but it is not a cycle model.",
            "",
            "| Cache crossing global cut | ROM row reuse | Frame interval | ROM attribution | Main ROM array bytes |",
            "|---:|---:|---:|---:|---:|",
        ]
    )
    for item in result["sensitivities"]["oasis_cache_placement_and_row_reuse"]:
        reuse = item["rom_row_reuse"]
        lines.append(
            f"| {item['cache_remote_fraction']:.0%} | {reuse} | "
            f"{_fmt_time(item['rom_latency_s'])} | "
            f"{_fmt_x(item['rom_storage_speedup'])} | "
            f"{_fmt_bytes(item['rom_main_phase']['rom_array_service_bytes'])} |"
        )

    lines.extend(
        [
            "",
            "The cache should therefore be sharded by spatial patch and retained",
            "beside each temporal-attention lane. Sending temporal K/V over the",
            "global bisection on every denoise call erases most of the storage gain.",
            "Likewise, the claim requires a physical activation-broadcast/reuse path;",
            "a ROM bitcell's bandwidth number alone does not prove whole-call reuse.",
            "",
            "## MiniMax-H3 control: why current clip DiTs are less favorable",
            "",
            "H3 is an intentionally strong control. The official transformer has",
            "66.280 GB of weights, but approximately 26.021 GB of AdaLN branches can",
            "be precomputed for a fixed inference schedule. The model therefore",
            "charges only 40.260 GB per transformer call—already giving H3 its",
            "vendor-described inference optimization. The 50 main blocks contain",
            "19.268B modeled matrix parameters.",
            f"The complete payload fits one conservative stage ({_fmt_bytes(h3_conservative_capacity['available_bytes_one_stage'])}",
            f"available, {h3_conservative_capacity['capacity_margin']:.3f}× margin), so this result neither hides",
            "a multi-stage capacity penalty nor invents a multi-stage ROM benefit.",
            "",
            "The accelerated control is deliberately more favorable than a literal",
            "FastH3 graph: its 10% residual density scales both attention arithmetic",
            "and modeled attention NoC, including text/audio paths that are not all",
            "sparse in the published method.",
            "",
            "| Clip / variant | Packed N | Calls | Tensor operations | Attention share | Weight reads | QKV floor (not charged) | Central ROM time | Output fps | ROM attribution |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for label in ("5.17s", "10.12s", "14.38s"):
        for variant in ("base_dense", "accelerated_best_case"):
            scenario = f"{label}-{variant}"
            attr = _find_attr(result, scenario, central)
            point = _find_point(result, scenario, central, "rom")
            meta = point["metadata"]
            lines.append(
                f"| {label} / {variant} | {meta['sequence_tokens']:,} | "
                f"{meta['denoise_calls']} | {_fmt_ops(point['tensor_operations'])} | "
                f"{meta['attention_operation_share']:.1%} | "
                f"{_fmt_bytes(point['weight_read_bytes'])} | "
                f"{_fmt_bytes(meta['qkv_materialization_floor_bytes'])} | "
                f"{_fmt_time(attr['rom_latency_s'], unit='s')} | "
                f"{attr['rom_generated_rate_fps']:,.2f} | "
                f"{_fmt_x(attr['rom_storage_speedup'])} |"
            )

    lines.extend(
        [
            "",
            "The 1.000× entries above assume every matrix is served once for the",
            "whole call. The following accelerated-case sensitivity asks what happens",
            "if a fixed-weight datapath must instead re-serve it for every activation",
            "row (`R=1`):",
            "",
            "| Accelerated clip | Whole-call time | Whole-call ROM attribution | R=1 time | R=1 ROM attribution | R=1 ROM array service |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for label in ("5.17s", "10.12s", "14.38s"):
        scenario = f"{label}-accelerated_best_case"
        whole_call = next(
            item
            for item in result["sensitivities"]["h3_row_reuse"]
            if item["scenario"] == scenario
            and item["rom_row_reuse"] == "whole_call"
        )
        per_row = next(
            item
            for item in result["sensitivities"]["h3_row_reuse"]
            if item["scenario"] == scenario and item["rom_row_reuse"] == 1
        )
        lines.append(
            f"| {label} | {_fmt_time(whole_call['rom_latency_s'], unit='s')} | "
            f"{_fmt_x(whole_call['rom_storage_speedup'])} | "
            f"{_fmt_time(per_row['rom_latency_s'], unit='s')} | "
            f"{_fmt_x(per_row['rom_storage_speedup'])} | "
            f"{_fmt_bytes(per_row['rom_main_phase']['rom_array_service_bytes'])} |"
        )

    h3_phase = h3_base["rom_main_phase"]
    fast_phase = h3_fast_long["rom_main_phase"]
    lines.extend(
        [
            "",
            "For dense 5.17-second H3, the central phase is",
            f"{_fmt_time(h3_phase['compute_service_s'], unit='s')} compute plus",
            f"{_fmt_time(h3_phase['noc_serialization_floor_s'], unit='s')} of modeled",
            "NoC floor, versus only",
            f"{_fmt_time(h3_phase['weight_service_s'])} of ROM service.",
            "For the deliberately favorable long-clip accelerated case, compute is",
            f"still {_fmt_time(fast_phase['compute_service_s'], unit='s')} and the",
            f"ROM service is {_fmt_time(fast_phase['weight_service_s'])}.",
            "Moving those weights into HBM cannot change the maximum.",
            "Under R=1, however, ROM becomes slower than the same-compute HBM",
            "counterfactual (0.286×–0.346× attribution in the accelerated",
            "cases). Thus H3 is not merely unable to exploit ROM-as-storage; a",
            "per-stream fixed-weight implementation can make service the bottleneck.",
            "",
            "H3's released full attention is bidirectional over the packed text,",
            "video, and audio sequence. Past positions change as the noisy clip",
            "changes, so Q/K/V from one denoising call cannot be installed as an",
            "autoregressive persistent cache. Approximate cross-step feature caches,",
            "step distillation, and sparse attention can accelerate H3, but those are",
            "algorithm/model changes—not benefits from immutable ROM storage.",
            "",
            "## Calibration and the meaning of real time",
            "",
        ]
    )
    cal = result["calibration"]
    lines.extend(
        [
            "The official SGLang benchmark reports 19.04 s for one warm BF16",
            "1344×768, 124-frame H3 request on 8×B300. This study's transformer-only",
            f"roof model gives {cal['h3_b300']['modeled_transformer_only_latency_s']:.2f} s,",
            f"or {cal['h3_b300']['modeled_to_published_latency_ratio']:.2f}× the",
            "published latency. That is a useful order-of-magnitude check, not a fit:",
            "the discrepancy is left visible and no ROM parameter is rescaled.",
            "",
            "FastH3 demonstrates the difference between playback throughput and an",
            "interactive world model. Its published 8×B200 median generates 345",
            "frames (14.38 s of playback) in 12.88 s, but the user still waits for a",
            "full clip and cannot inject a new action before each generated frame.",
            "Oasis must close a 50 ms action-to-next-frame loop continuously.",
            "",
            "The Oasis site reports 20 fps for its proprietary demo. The public-code",
            f"W32/B300 tensor-path model here gives {oasis_b300['generated_fps']:.2f} fps,",
            "but the demo checkpoint, exact hardware, runtime, and auxiliary work are",
            "not sufficiently identified to call that a validation. The cached",
            f"central value of {findings['central_oasis_w32_cached_tensor_path_fps']:,.1f} fps",
            "is a service-envelope diagnostic, **not** a prediction that an",
            "OpenTallas video system would run at that rate.",
            "",
            "## Cache correctness conditions",
            "",
            "The candidate cache is exact only if all of the following hold:",
            "",
            "1. Temporal attention remains strictly causal, so a past frame never",
            "   depends on the current frame.",
            "2. Past latent values, actions, and their context timestep stay fixed",
            "   across the denoising calls whose K/V are reused.",
            "3. Sliding-window rollover uses position-stable global indices or",
            "   correctly re-rotates cached keys; naively shifting RoPE indices is",
            "   not cache-safe.",
            "4. The completed frame receives the modeled extra pass at the fixed",
            "   context timestep before its layerwise temporal K/V are committed.",
            "5. Dynamic noising never mutates a cached past state without explicit",
            "   invalidation and refill.",
            "",
            "The public code satisfies the causal-attention premise but does not",
            "implement or validate this transformation. A byte/flop derivation is",
            "not an exactness proof.",
            "",
            "## What OpenTallas supports today",
            "",
            "OpenTallas currently supports neither model. There is no video/world-",
            "model ABI, 5-D latent layout, axial-attention lowering, diffusion",
            "scheduler, temporal-cache lifetime rule, action-conditioning operator,",
            "VAE backend, video compiler image, RTL execution, or cycle evidence.",
            "This study adds only a deterministic analytical workload model and",
            "checked artifacts. It does not turn the README's Oasis horizon into an",
            "implementation claim.",
            "",
            "## Highest-value gates",
            "",
            "1. Implement the layerwise temporal cache against the pinned Oasis code",
            "   and compare every latent bit/code through denoising and W32 rollover.",
            "2. Trace actual matrix calls, activation rows, transient bytes, and",
            "   kernel time for both released paths; replace the unpriced auxiliaries.",
            "3. Map the cache and axial attention onto a concrete floorplan and",
            "   measure which bytes cross each physical cut.",
            "4. Resolve the batched-ROM versus per-stream compute-in-ROM activation",
            "   service with RTL and placed/routed port/timing evidence.",
            "5. Profile the authenticated Oasis checkpoint and execute H3 to replace",
            "   code/header inventory with checkpoint- and runtime-derived evidence.",
            "",
            "## Reproduce",
            "",
            "```bash",
            "make world-model",
            "PYTHONPATH=src pytest -q tests/test_world_model_study.py",
            "```",
            "",
            "Inputs: [study config](../../configs/studies/world_model_rom.json),",
            "[Oasis inventory](../../data/inventory/oasis-500m-code.json),",
            "[H3 inventory](../../data/inventory/minimax-h3-transformer.json), and",
            "[analytical implementation](../../src/opentallas/world_model.py).",
            "",
            "## Evidence boundary",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in result["evidence_boundary"])
    lines.append("")
    return "\n".join(lines)


def render_csv(result: dict[str, Any]) -> str:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=CSV_FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(result["sweep_rows"])
    return output.getvalue()


def run(
    output_root: Path = OUTPUT_ROOT, config_path: Path = CONFIG_PATH
) -> dict[str, Any]:
    result = build(config_path)
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "analytical.json").write_text(
        json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    (output_root / "sweep.csv").write_text(
        render_csv(result), encoding="utf-8", newline=""
    )
    (output_root / "REPORT.md").write_text(
        render_report(result).rstrip() + "\n", encoding="utf-8"
    )
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=CONFIG_PATH)
    parser.add_argument("--output", type=Path, default=OUTPUT_ROOT)
    args = parser.parse_args(argv)
    run(args.output, args.config)
    print((args.output / "REPORT.md").resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
