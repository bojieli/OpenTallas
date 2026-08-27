#!/usr/bin/env python3
"""One-factor sensitivity, compound bounds, and claimed-tier feasibility audit."""

from __future__ import annotations

import argparse
import csv
from dataclasses import replace
import json
import math
from pathlib import Path
import sys
from typing import Callable

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from opentallas.analytical import AnalyticalSimulator
from opentallas.config import load_architectures, load_model_dir
from opentallas.schema import ArchitectureProfile, HardwareProfile, ModelProfile, SimulationRequest


def _replace_compute_roofs(
    arch: ArchitectureProfile, low_precision_peak_ops_s: float
) -> ArchitectureProfile:
    ratio = (
        arch.higher_precision_peak_ops_s_per_device
        / arch.peak_ops_s_per_device
    )
    return replace(
        arch,
        peak_ops_s_per_device=low_precision_peak_ops_s,
        higher_precision_peak_ops_s_per_device=low_precision_peak_ops_s * ratio,
    )


def _replace_kv(model: ModelProfile, mode: str, value: float) -> ModelProfile:
    groups = []
    for group in model.attention_groups:
        if mode == "index_multiplier" and group.kind == "compressed_sparse":
            group = replace(group, index_entry_bytes=group.index_entry_bytes * value)
        elif mode == "main_multiplier" and group.kind != "recurrent":
            group = replace(group, entry_bytes=group.entry_bytes * value)
        elif mode == "recurrent_multiplier" and group.kind == "recurrent":
            group = replace(
                group,
                recurrent_state_bytes=group.recurrent_state_bytes * value,
                recurrent_write_bytes=(
                    None if group.recurrent_write_bytes is None else group.recurrent_write_bytes * value
                ),
            )
        groups.append(group)
    return replace(model, attention_groups=tuple(groups))


def _uniform_mxfp4(model: ModelProfile) -> ModelProfile:
    bytes_per_parameter = 0.5 + 1 / 32
    if model.metadata.get("adapter") == "qwen3":
        # Every released Qwen3-8B tensor is BF16, so all storage categories can
        # be scaled exactly for this encoding sensitivity without guessing the
        # parameter distribution among embeddings, layers, and the LM head.
        scale = bytes_per_parameter / 2
        return replace(
            model,
            checkpoint_bytes=model.checkpoint_bytes * scale,
            dense_weight_bytes=model.dense_weight_bytes * scale,
            routed_weight_bytes=0,
            draft_dense_weight_bytes=0,
            draft_routed_weight_bytes=0,
            resident_only_weight_bytes=model.resident_only_weight_bytes * scale,
            layer_dense_weight_bytes=tuple(
                value * scale for value in model.layer_dense_weight_bytes
            ),
            layer_routed_weight_bytes=tuple(0 for _ in model.layer_routed_weight_bytes),
            metadata={
                **model.metadata,
                "weight_encoding_sensitivity": "uniform MXFP4 + E8M0/32",
            },
        )
    dense_params = model.dense_parameters
    routed_params = model.routed_parameters
    dense = dense_params * bytes_per_parameter
    routed = routed_params * bytes_per_parameter
    dense_scale = dense / model.dense_weight_bytes if model.dense_weight_bytes else 0.0
    routed_scale = routed / model.routed_weight_bytes if model.routed_weight_bytes else 0.0
    return replace(
        model,
        checkpoint_bytes=(
            dense
            + routed
            + model.draft_dense_weight_bytes
            + model.draft_routed_weight_bytes
            + model.resident_only_weight_bytes
        ),
        dense_weight_bytes=dense,
        routed_weight_bytes=routed,
        layer_dense_weight_bytes=tuple(
            value * dense_scale for value in model.layer_dense_weight_bytes
        ),
        layer_routed_weight_bytes=tuple(
            value * routed_scale for value in model.layer_routed_weight_bytes
        ),
        metadata={**model.metadata, "weight_encoding_sensitivity": "uniform MXFP4 + E8M0/32"},
    )


def evaluate(
    simulator: AnalyticalSimulator,
    model: ModelProfile,
    gpus: list[ArchitectureProfile],
    rom: ArchitectureProfile,
    context: int,
    batch: int,
) -> dict:
    request = SimulationRequest(context_tokens=context, batch_size=batch)
    rom_point = simulator.simulate(model, rom, request)
    gpu_points = [simulator.simulate(model, gpu, request) for gpu in gpus]
    feasible = [point for point in gpu_points if point.feasible]
    fastest = max(feasible, key=lambda point: point.per_user_tokens_s) if feasible else None
    cheapest = (
        min(feasible, key=lambda point: point.partial_tco_per_million_tokens)
        if feasible
        else None
    )
    return {
        "rom": rom_point,
        "gpu_fastest": fastest,
        "gpu_cheapest": cheapest,
        "speed_ratio": (
            rom_point.per_user_tokens_s / fastest.per_user_tokens_s
            if rom_point.feasible and fastest is not None
            else math.nan
        ),
        "partial_tco_ratio_vs_cheapest_gpu": (
            cheapest.partial_tco_per_million_tokens
            / rom_point.partial_tco_per_million_tokens
            if rom_point.feasible and cheapest is not None
            else math.nan
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--standard", action="store_true")
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "sensitivity")
    args = parser.parse_args()
    if not args.standard:
        parser.error("use --standard")
    args.output.mkdir(parents=True, exist_ok=True)
    models = load_model_dir(ROOT / "configs" / "models")
    gpus, rom, _ = load_architectures(ROOT / "configs" / "hardware" / "architectures.json")
    simulator = AnalyticalSimulator(HardwareProfile(gpu=gpus[0], rom=rom))

    rom_factors: dict[str, tuple[float, float, Callable[[ArchitectureProfile, float], ArchitectureProfile]]] = {
        "ROM array bandwidth (B/s/wafer)": (30e12, 2e15, lambda x, v: replace(x, weight_bandwidth_bytes_s_per_device=v)),
        "ROM low-precision peak compute (op/s/wafer; higher-precision roof scales proportionally)": (0.5e15, 30e15, _replace_compute_roofs),
        "ROM capacity (bytes/wafer)": (128e9, 192e9, lambda x, v: replace(x, weight_capacity_bytes_per_device=v)),
        "ROM HBM bandwidth (B/s/wafer)": (4e12, 16e12, lambda x, v: replace(x, kv_bandwidth_bytes_s_per_device=v)),
        "ROM HBM capacity (bytes/wafer)": (192e9, 768e9, lambda x, v: replace(x, kv_capacity_bytes_per_device=v)),
        "ROM shared-KV reread amplification": (2.0, 1.0, lambda x, v: replace(x, kv_read_amplification=v)),
        "collective injection bandwidth (B/s)": (128e9, 1024e9, lambda x, v: replace(x, collective_bandwidth_bytes_s=v)),
        "collective floor (s/layer)": (1e-6, 50e-9, lambda x, v: replace(x, collective_latency_s_per_layer=v)),
        "pipeline efficiency": (0.65, 0.98, lambda x, v: replace(x, pipeline_efficiency=v)),
        "defect-repair efficiency": (0.75, 0.98, lambda x, v: replace(x, defect_repair_efficiency=v)),
        "load-balance efficiency": (0.60, 0.96, lambda x, v: replace(x, load_balance_efficiency=v)),
    }
    rows = []
    for model in models:
        anchors = (
            [(8_192, batch) for batch in (1, 8, 32, 64, 128)]
            if model.metadata.get("adapter") == "qwen3"
            else [
                (200_000, 1),
                (200_000, 8),
                (200_000, 32),
                (200_000, 64),
                (1_000_000, 1),
                (1_000_000, 8),
                (1_000_000, 64),
            ]
        )
        model_variants: list[tuple[str, ModelProfile, ModelProfile]] = [
            ("weight encoding: released vs uniform MXFP4", model, _uniform_mxfp4(model)),
        ]
        if model.metadata.get("adapter") == "deepseek_v4":
            model_variants.extend([
                ("index-cache bytes: FP4 to BF16", _replace_kv(model, "index_multiplier", 0.75), _replace_kv(model, "index_multiplier", 256 / 68)),
                ("main-KV bytes: production to BF16", model, _replace_kv(model, "main_multiplier", 1024 / 583)),
            ])
        elif model.metadata.get("adapter") == "kimi_k3":
            model_variants.extend([
                ("MLA cache: FP8 to BF16", model, _replace_kv(model, "main_multiplier", 2.0)),
                ("KDA recurrent-state traffic", _replace_kv(model, "recurrent_multiplier", 0.5), _replace_kv(model, "recurrent_multiplier", 2.0)),
            ])
        elif model.metadata.get("adapter") == "qwen3":
            model_variants.append(
                (
                    "Qwen GQA cache precision: assumed FP8 to BF16 baseline",
                    _replace_kv(model, "main_multiplier", 0.5),
                    model,
                )
            )
        else:  # pragma: no cover - generated profiles use a known adapter
            raise ValueError(f"unsupported adapter for sensitivity: {model.metadata}")
        for context, batch in anchors:
            baseline = evaluate(simulator, model, gpus, rom, context, batch)
            for factor, (low, high, transform) in rom_factors.items():
                for endpoint, value in (("pessimistic", low), ("optimistic", high)):
                    result = evaluate(simulator, model, gpus, transform(rom, value), context, batch)
                    rows.append({
                        "model": model.name,
                        "context_tokens": context,
                        "batch_size": batch,
                        "factor": factor,
                        "endpoint": endpoint,
                        "value": value,
                        "rom_per_user_tokens_s": result["rom"].per_user_tokens_s,
                        "speed_ratio_vs_fastest_gpu": result["speed_ratio"],
                        "partial_tco_ratio_vs_cheapest_gpu": result[
                            "partial_tco_ratio_vs_cheapest_gpu"
                        ],
                        "binding_constraint": result["rom"].binding_constraint,
                        "baseline_speed_ratio": baseline["speed_ratio"],
                    })
            for factor, low_model, high_model in model_variants:
                for endpoint, variant in (("endpoint_a", low_model), ("endpoint_b", high_model)):
                    result = evaluate(simulator, variant, gpus, rom, context, batch)
                    rows.append({
                        "model": model.name,
                        "context_tokens": context,
                        "batch_size": batch,
                        "factor": factor,
                        "endpoint": endpoint,
                        "value": variant.checkpoint_bytes,
                        "rom_per_user_tokens_s": result["rom"].per_user_tokens_s,
                        "speed_ratio_vs_fastest_gpu": result["speed_ratio"],
                        "partial_tco_ratio_vs_cheapest_gpu": result[
                            "partial_tco_ratio_vs_cheapest_gpu"
                        ],
                        "binding_constraint": result["rom"].binding_constraint,
                        "baseline_speed_ratio": baseline["speed_ratio"],
                    })
            for endpoint, amplification in (("ideal", 1.0), ("reread_stress", 4.0)):
                gpu_variant = [
                    replace(gpu, kv_read_amplification=amplification) for gpu in gpus
                ]
                result = evaluate(simulator, model, gpu_variant, rom, context, batch)
                rows.append({
                    "model": model.name,
                    "context_tokens": context,
                    "batch_size": batch,
                    "factor": "GPU shared-KV reread amplification",
                    "endpoint": endpoint,
                    "value": amplification,
                    "rom_per_user_tokens_s": result["rom"].per_user_tokens_s,
                    "speed_ratio_vs_fastest_gpu": result["speed_ratio"],
                    "partial_tco_ratio_vs_cheapest_gpu": result[
                        "partial_tco_ratio_vs_cheapest_gpu"
                    ],
                    "binding_constraint": result["rom"].binding_constraint,
                    "baseline_speed_ratio": baseline["speed_ratio"],
                })

    with (args.output / "tornado.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=list(rows[0]), lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)

    # Audit the Pro tiers quoted in the provisional brief. The grid reports the
    # minimum peak compute needed at each ROM bandwidth, holding other midpoint
    # assumptions (including the NoC-derived serialization term) fixed.
    pro = next(model for model in models if "Pro" in model.name)
    claims = [(1, 7000.0), (8, 5500.0), (32, 2250.0)]
    bandwidths = [0.1e15, 0.2e15, 0.5e15, 1e15, 2e15, 5e15, 10e15]
    computes = [1e15, 2e15, 5e15, 10e15, 20e15, 50e15, 100e15]
    claim_audit = []
    for batch, target in claims:
        # Theoretical ceiling with service resources made effectively infinite.
        ceiling_arch = replace(
            rom,
            weight_bandwidth_bytes_s_per_device=1e30,
            peak_ops_s_per_device=1e30,
            higher_precision_peak_ops_s_per_device=1e30,
            kv_bandwidth_bytes_s_per_device=1e30,
            cooling_limit_w_per_device=1e30,
        )
        ceiling = evaluate(simulator, pro, gpus, ceiling_arch, 200_000, batch)["rom"].per_user_tokens_s
        pareto = []
        for bandwidth in bandwidths:
            needed = None
            achieved = None
            best_on_row = None
            for compute in computes:
                candidate = replace(
                    rom,
                    weight_bandwidth_bytes_s_per_device=bandwidth,
                    peak_ops_s_per_device=compute,
                    higher_precision_peak_ops_s_per_device=(
                        compute
                        * rom.higher_precision_peak_ops_s_per_device
                        / rom.peak_ops_s_per_device
                    ),
                )
                point = evaluate(simulator, pro, gpus, candidate, 200_000, batch)["rom"]
                if point.feasible and (
                    best_on_row is None
                    or point.per_user_tokens_s > best_on_row.per_user_tokens_s
                ):
                    best_on_row = point
                if point.feasible and point.per_user_tokens_s >= target:
                    needed, achieved = compute, point.per_user_tokens_s
                    break
            pareto.append({
                "rom_bandwidth_bytes_s_per_wafer": bandwidth,
                "minimum_peak_ops_s_per_wafer_on_grid": needed,
                "achieved_per_user_tokens_s": achieved,
                "maximum_achieved_per_user_tokens_s_on_grid": (
                    None if best_on_row is None else best_on_row.per_user_tokens_s
                ),
                "binding_constraint_at_maximum": (
                    None if best_on_row is None else best_on_row.binding_constraint
                ),
                "peak_ops_s_per_wafer_at_maximum": (
                    None if best_on_row is None else computes[-1]
                ),
            })
        finite_rows = [
            item for item in pareto
            if item["maximum_achieved_per_user_tokens_s_on_grid"] is not None
        ]
        grid_best = max(
            finite_rows,
            key=lambda item: item["maximum_achieved_per_user_tokens_s_on_grid"],
            default=None,
        )
        claim_audit.append({
            "model": pro.name,
            "context_tokens": 200_000,
            "batch_size": batch,
            "brief_target_per_user_tokens_s": target,
            "collective_and_pipeline_ceiling_tokens_s": ceiling,
            "reachable_before_service_limits": ceiling >= target,
            "maximum_achieved_per_user_tokens_s_on_grid": (
                None if grid_best is None else grid_best["maximum_achieved_per_user_tokens_s_on_grid"]
            ),
            "binding_constraint_at_grid_maximum": (
                None if grid_best is None else grid_best["binding_constraint_at_maximum"]
            ),
            "grid_maximum_rom_bandwidth_bytes_s_per_wafer": (
                None if grid_best is None else grid_best["rom_bandwidth_bytes_s_per_wafer"]
            ),
            "grid_maximum_peak_ops_s_per_wafer": (
                None if grid_best is None else grid_best["peak_ops_s_per_wafer_at_maximum"]
            ),
            "resource_grid": pareto,
        })
    (args.output / "claim-audit.json").write_text(
        json.dumps(claim_audit, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    # Rank one-factor movement for the primary Pro/200k/B8 point.
    primary = [
        row for row in rows
        if row["model"] == pro.name and row["context_tokens"] == 200_000 and row["batch_size"] == 8
    ]
    ranges = {}
    for row in primary:
        ranges.setdefault(row["factor"], []).append(row["speed_ratio_vs_fastest_gpu"])
    ranked = sorted(
        ((factor, min(values), max(values), max(values) - min(values)) for factor, values in ranges.items()),
        key=lambda item: item[3],
        reverse=True,
    )
    lines = [
        "# Sensitivity and provisional-claim audit",
        "",
        "Primary ranking: DeepSeek V4 Pro, 200k context, batch 8. Ratio is ROM",
        "per-user speed divided by the fastest feasible B200/B300 configuration.",
        "",
        "| Rank | One-factor input | Low ratio | High ratio | Span |",
        "|---:|---|---:|---:|---:|",
    ]
    for rank, (factor, low, high, span) in enumerate(ranked, 1):
        lines.append(f"| {rank} | {factor} | {low:.3f}× | {high:.3f}× | {span:.3f}× |")
    lines.extend([
        "",
        "## Claimed Pro/200k tiers",
        "",
        "The table below asks what *per-wafer* array bandwidth and peak compute are",
        "needed while retaining midpoint capacity, HBM, NoC, derates, and six stages.",
        "",
        "| Batch | Brief target | Collective/pipeline ceiling | First grid point reaching target |",
        "|---:|---:|---:|---|",
    ])
    for claim in claim_audit:
        first = next(
            (
                item for item in claim["resource_grid"]
                if item["minimum_peak_ops_s_per_wafer_on_grid"] is not None
            ),
            None,
        )
        if first:
            required = (
                f"{first['rom_bandwidth_bytes_s_per_wafer'] / 1e15:.1f} PB/s + "
                f"{first['minimum_peak_ops_s_per_wafer_on_grid'] / 1e15:.0f} POP/s"
            )
        else:
            best = claim["maximum_achieved_per_user_tokens_s_on_grid"]
            bind = claim["binding_constraint_at_grid_maximum"]
            required = (
                "not reached; grid max "
                f"{best:,.0f} tok/s ({bind})"
                if best is not None
                else "not reached; no feasible grid point"
            )
        lines.append(
            f"| {claim['batch_size']} | {claim['brief_target_per_user_tokens_s']:,.0f} tok/s | "
            f"{claim['collective_and_pipeline_ceiling_tokens_s']:,.0f} tok/s | {required} |"
        )
    lines.extend([
        "",
        "The ceiling is not a silicon prediction: it removes weight, compute, KV, and",
        "thermal service time to isolate static collective, pipeline, and cross-stage delay.",
        "",
    ])
    (args.output / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {args.output / 'tornado.csv'}")
    print(f"wrote {args.output / 'claim-audit.json'}")
    print(f"wrote {args.output / 'REPORT.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
