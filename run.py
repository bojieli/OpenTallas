#!/usr/bin/env python3
"""Run the reproducible mixed-model, per-model-context operating-point study."""

from __future__ import annotations

import argparse
import csv
from dataclasses import asdict
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from opentallas.analytical import AnalyticalSimulator, OperatingPoint
from opentallas.config import load_architectures, load_model_dir
from opentallas.schema import HardwareProfile, ModelProfile, SimulationRequest, SpeculationProfile


LONG_CONTEXTS = (200_000, 1_000_000)
QWEN_CONTROL_CONTEXTS = (8_192,)
REQUIRED_BATCHES = (1, 8, 32, 64, 128)
SWEEP_BATCHES = tuple(range(1, 257))
SCENARIOS = {
    "no_speculation": SpeculationProfile(),
    # Acceptance must eventually come from a serving trace. This midpoint is
    # applied to both architectures and its serial draft cost is explicit.
    "speculative_midpoint": SpeculationProfile(
        draft_tokens=5,
        acceptance_probability=0.70,
        draft_cost_fraction=0.08,
    ),
}


def _contexts_for(model: ModelProfile) -> tuple[int, ...]:
    if model.metadata.get("adapter") == "qwen3":
        return QWEN_CONTROL_CONTEXTS
    return LONG_CONTEXTS


def _scenarios_for(model: ModelProfile) -> dict[str, SpeculationProfile]:
    # The pinned Qwen checkpoint has no attached draft module. An external
    # draft would be a different system and requires its own evidence-backed
    # profile, so only ordinary decode is reported for this control workload.
    if model.metadata.get("adapter") == "qwen3":
        return {"no_speculation": SCENARIOS["no_speculation"]}
    return SCENARIOS


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _finite(value: float) -> float | None:
    return value if math.isfinite(value) else None


def _compact(point: OperatingPoint, scenario: str) -> dict[str, Any]:
    return {
        "scenario": scenario,
        "model": point.model,
        "context_tokens": point.context_tokens,
        "batch_size": point.batch_size,
        "architecture": point.architecture,
        "architecture_kind": point.architecture_kind,
        "feasible": point.feasible,
        "infeasible_reasons": list(point.infeasible_reasons),
        "stages": point.stages,
        "max_concurrent_users": point.max_concurrent_users,
        "aggregate_tokens_s": _finite(point.aggregate_tokens_s),
        "per_user_tokens_s": _finite(point.per_user_tokens_s),
        "amortized_capex_per_million_tokens": _finite(
            point.amortized_capex_per_million_tokens
        ),
        "electricity_cost_per_million_tokens": _finite(
            point.electricity_cost_per_million_tokens
        ),
        "partial_tco_per_million_tokens": _finite(point.partial_tco_per_million_tokens),
        "power_w": point.power_w,
        "step_interval_s": _finite(point.step_interval_s),
        "binding_constraint": point.binding_constraint,
        "rho_one": point.rho_one,
        "expert_coverage": point.metrics["C1_expert_coverage"],
        "kv_read_bytes_per_user_token": point.metrics["C2_kv_read_bytes_per_user_token"],
        "kv_storage_bytes_per_user": point.metrics["C7_C8_kv_storage_bytes_per_user"],
        "resident_users_required": point.metrics["C7_C8_resident_users_required"],
        "max_batch_per_stage": point.metrics["C7_C8_max_batch_per_stage"],
        "stage_balance_efficiency": point.metrics["C11_stage_balance_efficiency"],
    }


def _best(points: list[OperatingPoint], key: str, maximize: bool) -> OperatingPoint | None:
    feasible = [point for point in points if point.feasible]
    if not feasible:
        return None
    return (max if maximize else min)(feasible, key=lambda point: getattr(point, key))


def _point_ref(point: OperatingPoint | None) -> dict[str, Any] | None:
    return None if point is None else _compact(point, "")


def _balanced(points: list[OperatingPoint]) -> OperatingPoint | None:
    """Choose the latency/throughput knee using a normalized geometric mean."""

    feasible = [point for point in points if point.feasible]
    if not feasible:
        return None
    best_speed = max(point.per_user_tokens_s for point in feasible)
    best_throughput = max(point.aggregate_tokens_s for point in feasible)
    return max(
        feasible,
        key=lambda point: math.sqrt(
            (point.per_user_tokens_s / best_speed)
            * (point.aggregate_tokens_s / best_throughput)
        ),
    )


def render_report(result: dict[str, Any]) -> str:
    lines = [
        "# Standard analytical simulation report",
        "",
        "> **Legacy/superseded technology comparison.** This single-midpoint",
        "> B200/B300 study is retained for model-general regression and provenance.",
        "> Current product comparisons are in `results/iso-node/` and must not be",
        "> combined with the figures below.",
        "",
        "> This report is generated. Hardware results are conditional on the explicit",
        "> architecture assumptions; checkpoint sizes and model topology are measured/published.",
        "",
        "## Measured model inputs and derived KV traffic",
        "",
        "| Model | Released storage | Active dense / routed | Target-decode dense / routed | Draft / other resident | Context | KV read/user/token | KV store/user | ρ₁ | ROM stages |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for model in result["model_summaries"]:
        for context in model["contexts"]:
            lines.append(
                f"| {model['model']} | {model['checkpoint_bytes']/1e9:.3f} GB | "
                f"{model['dense_active_parameters']/1e9:.2f} / "
                f"{model['routed_active_parameters']/1e9:.2f} B | "
                f"{model['dense_weight_bytes']/1e9:.3f} / {model['routed_weight_bytes']/1e9:.3f} GB | "
                f"{(model['draft_dense_weight_bytes'] + model['draft_routed_weight_bytes'])/1e9:.3f} / "
                f"{model['resident_only_weight_bytes']/1e9:.3f} GB | "
                f"{context['context_tokens']:,} | {context['kv_read_bytes_per_user_token']/1e9:.4f} GB | "
                f"{context['kv_storage_bytes_per_user']/1e9:.4f} GB | {context['rho_one']:.2f} | "
                f"{context['rom_stages']} |"
            )
    lines.extend([
        "",
        "## Numeric format contract",
        "",
        "Storage width is not used as a proxy for arithmetic precision. In particular,",
        "DeepSeek routed experts store MXFP4 weights but multiply them by FP8 activations.",
        "The compatible B200/B300 roof is therefore FP8-rate, not the larger pure-FP4 peak.",
        "",
        "| Model | Dense/shared matrix format | Routed expert matrix format | Evidence status |",
        "|---|---|---|---|",
    ])
    for model in result["model_summaries"]:
        lines.append(
            f"| {model['model']} | {model['dense_compute_format']} | "
            f"{model['routed_compute_format'] or 'not applicable'} | "
            f"{model['compute_precision_status']} |"
        )
    lines.extend([
        "",
        "## Required operating points",
        "",
        "The table uses the no-speculation scenario. `GPU` is the fastest feasible B200/B300",
        "configuration at the same active microbatch; ratios above 1 favor ROM. ROM batch",
        "is per pipeline stage, so its resident session count is batch × stages.",
        "",
        "| Model | Context | Batch/stage | ROM residents | ROM user tok/s | Fastest GPU | GPU user tok/s | Speed ratio | Cheapest partial-TCO GPU | Partial-TCO ratio | ROM bind |",
        "|---|---:|---:|---:|---:|---|---:|---:|---|---:|---|",
    ])
    for row in result["comparisons"]:
        if row["scenario"] != "no_speculation" or row["batch_size"] not in REQUIRED_BATCHES:
            continue
        rom_tps = row.get("rom_per_user_tokens_s")
        gpu_tps = row.get("gpu_per_user_tokens_s")
        lines.append(
            "| {model} | {context_tokens:,} | {batch_size} | {resident:,.0f} | {rom} | {gpu_arch} | {gpu} | {speed} | {cheapest} | {cost} | {bind} |".format(
                **row,
                resident=row["rom_resident_users_required"],
                rom="—" if rom_tps is None else f"{rom_tps:,.1f}",
                gpu="—" if gpu_tps is None else f"{gpu_tps:,.1f}",
                speed="—" if row.get("speed_ratio") is None else f"{row['speed_ratio']:.2f}×",
                cheapest=row.get("cheapest_gpu_arch") or "infeasible",
                cost=(
                    "—"
                    if row.get("partial_tco_ratio_vs_cheapest_gpu") is None
                    else f"{row['partial_tco_ratio_vs_cheapest_gpu']:.2f}×"
                ),
                bind=row.get("rom_binding_constraint", "—"),
            )
        )
    lines.extend([
        "",
        "## Same-microbatch B200 versus B300 family view",
        "",
        "This isolates GPU generation from cluster-size selection. Each family column is",
        "the fastest feasible x1/x2/x4/x8/x16 point at the same active microbatch. Ratios above",
        "1 favor ROM; this view does not match the ROM pipeline's larger resident population.",
        "",
        "| Model | Context | Batch/stage | ROM user tok/s | Best B200 user tok/s | ROM/B200 | Best B300 user tok/s | ROM/B300 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ])
    for row in result["comparisons"]:
        if row["scenario"] != "no_speculation" or row["batch_size"] not in (1, 8, 64):
            continue
        rom_tps = row.get("rom_per_user_tokens_s")
        b200_tps = row.get("fastest_b200_per_user_tokens_s")
        b300_tps = row.get("fastest_b300_per_user_tokens_s")
        b200_ratio = row.get("speed_ratio_vs_b200")
        b300_ratio = row.get("speed_ratio_vs_b300")
        lines.append(
            f"| {row['model']} | {row['context_tokens']:,} | {row['batch_size']} | "
            f"{'—' if rom_tps is None else f'{rom_tps:,.1f}'} | "
            f"{'—' if b200_tps is None else f'{b200_tps:,.1f}'} | "
            f"{'—' if b200_ratio is None else f'{b200_ratio:.2f}×'} | "
            f"{'—' if b300_tps is None else f'{b300_tps:,.1f}'} | "
            f"{'—' if b300_ratio is None else f'{b300_ratio:.2f}×'} |"
        )
    lines.extend([
        "",
        "## Assumed speculative-decoding midpoint",
        "",
        "This is a sensitivity case, not a measured serving result: five draft tokens,",
        "70% independent acceptance probability, and serial draft work per candidate equal",
        "to 8% of one target-decode compute pass are assumed for both ROM and GPU. Gain is speculative/no-speculation",
        "per-user throughput at the same batch. The GPU column uses the fastest feasible",
        "B200/B300 configuration in each scenario; ratios above 1 favor ROM.",
        "Qwen3-8B is omitted because its pinned checkpoint has no attached draft module;",
        "no external-draft performance is assumed.",
        "",
        "| Model | Context | Batch/stage | ROM no-spec | ROM speculative | ROM gain | GPU no-spec | GPU speculative | GPU gain | Speculative ROM/GPU |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ])
    comparison_index = {
        (
            row["model"],
            row["context_tokens"],
            row["batch_size"],
            row["scenario"],
        ): row
        for row in result["comparisons"]
    }
    for model in result["model_summaries"]:
        for context in model["contexts"]:
            for batch in (1, 8, 64):
                key = (model["model"], context["context_tokens"], batch)
                baseline = comparison_index[(*key, "no_speculation")]
                speculative = comparison_index.get((*key, "speculative_midpoint"))
                if speculative is None:
                    continue
                rom_baseline = baseline.get("rom_per_user_tokens_s")
                rom_speculative = speculative.get("rom_per_user_tokens_s")
                gpu_baseline = baseline.get("gpu_per_user_tokens_s")
                gpu_speculative = speculative.get("gpu_per_user_tokens_s")
                rom_gain = (
                    rom_speculative / rom_baseline
                    if rom_speculative is not None and rom_baseline
                    else None
                )
                gpu_gain = (
                    gpu_speculative / gpu_baseline
                    if gpu_speculative is not None and gpu_baseline
                    else None
                )
                ratio = speculative.get("speed_ratio")

                def rate(value: float | None) -> str:
                    return "—" if value is None else f"{value:,.1f}"

                def gain(value: float | None) -> str:
                    return "—" if value is None else f"{value:.2f}×"

                lines.append(
                    f"| {key[0]} | {key[1]:,} | {key[2]} | {rate(rom_baseline)} | "
                    f"{rate(rom_speculative)} | {gain(rom_gain)} | {rate(gpu_baseline)} | "
                    f"{rate(gpu_speculative)} | {gain(gpu_gain)} | {gain(ratio)} |"
                )
    lines.extend([
        "",
        "## Resident-concurrency-matched B200/B300 comparison",
        "",
        "A ROM pipeline holds one microbatch at every stage. Here each GPU is simulated",
        "at the resulting total resident-session count, and the smallest feasible 1/2/4/8/16",
        "configuration is shown. This is the capacity-matched service comparison.",
        "",
        "| Model | Context | ROM B/stage | Resident sessions | ROM user tok/s | Smallest B200 | user tok/s | Smallest B300 | user tok/s | Partial-TCO ratio vs cheapest GPU |",
        "|---|---:|---:|---:|---:|---|---:|---|---:|---:|",
    ])
    for row in result["concurrency_matches"]:
        key = (row["model"], row["context_tokens"], row["batch_per_stage"])
        rom_point = row["rom"]
        b200 = row["smallest_b200"]
        b300 = row["smallest_b300"]
        b200_text = b200["architecture"] if b200 else "infeasible"
        b200_tps = f"{b200['per_user_tokens_s']:,.1f}" if b200 else "—"
        b300_text = b300["architecture"] if b300 else "infeasible"
        b300_tps = f"{b300['per_user_tokens_s']:,.1f}" if b300 else "—"
        rom_tps = f"{rom_point['per_user_tokens_s']:,.1f}" if rom_point["feasible"] else "—"
        cost_ratio = row["partial_tco_ratio_vs_cheapest_gpu"]
        lines.append(
            f"| {key[0]} | {key[1]:,} | {key[2]} | {row['resident_sessions']:,} | {rom_tps} | "
            f"{b200_text} | {b200_tps} | {b300_text} | {b300_tps} | "
            f"{'—' if cost_ratio is None else f'{cost_ratio:.2f}×'} |"
        )
    lines.extend([
        "",
        "## Batch optima and speed-superiority bands",
        "",
        "A speed-superiority batch beats the fastest per-user GPU point at *any* batch,",
        "not merely the GPU at the same batch. Bands are evaluated on the dense 1..256 sweep;",
        "all optima are searched exhaustively over integer batches through local capacity.",
        "",
        "Balanced maximizes the geometric mean of normalized per-user speed and aggregate",
        "throughput. Cost is partial TCO: hardware/NRE amortization plus active electricity;",
        "it excludes staffing, financing, networking, floor space, maintenance, and spares.",
        "",
        "| Model | Context | Scenario | ROM latency B | ROM balanced B | ROM throughput B | ROM partial-TCO B | GPU latency arch/B | GPU balanced arch/B | GPU throughput arch/B | GPU partial-TCO arch/B | ROM superiority batches |",
        "|---|---:|---|---:|---:|---:|---:|---|---|---|---|---|",
    ])
    for row in result["optima"]:
        lines.append(
            f"| {row['model']} | {row['context_tokens']:,} | {row['scenario']} | "
            f"{row.get('rom_latency_optimal_batch', '—')} | {row.get('rom_balanced_optimal_batch', '—')} | "
            f"{row.get('rom_throughput_optimal_batch', '—')} | {row.get('rom_partial_tco_optimal_batch', '—')} | "
            f"{row.get('gpu_latency_optimum_label', '—')} | {row.get('gpu_balanced_optimum_label', '—')} | "
            f"{row.get('gpu_throughput_optimum_label', '—')} | "
            f"{row.get('gpu_partial_tco_optimum_label', '—')} | "
            f"{row.get('rom_speed_superiority_band', 'none')} |"
        )
    lines.extend([
        "",
        "## Interpretation boundary",
        "",
        "- The curves verify accounting and reveal which constraint binds under each input set.",
        "- They do **not** verify the assumed ROM density, 100 TB/s read path, format-specific MAC",
        "  roofs, wafer yield, package HBM capacity, or cost. Sensitivity and circuit/NoC",
        "  work must survive before any go decision.",
        "- GPU marketing peaks are derated explicitly; production traces remain necessary to",
        "  replace engaged-bandwidth, collective, and speculative-acceptance assumptions.",
        "- Kimi K3 uses an optimized FP8 latent MLA cache. The reference BF16 expanded cache",
        "  is a pessimistic sensitivity case, not silently mixed into this table.",
        "- Qwen3-8B uses a conservative assumed BF16 full-GQA KV cache at 8K and no",
        "  speculative scenario. It is a dense control, not an additional product target.",
        "",
    ])
    return "\n".join(lines)


def render_qwen_addendum(result: dict[str, Any]) -> str:
    summary = next(
        model for model in result["model_summaries"] if model["model"] == "Qwen3-8B"
    )
    rows = [
        row
        for row in result["comparisons"]
        if row["model"] == "Qwen3-8B" and row["scenario"] == "no_speculation"
    ]
    optimum = next(
        row
        for row in result["optima"]
        if row["model"] == "Qwen3-8B" and row["scenario"] == "no_speculation"
    )
    context = summary["contexts"][0]
    lines = [
        "# Qwen3-8B / 8K analytical addendum",
        "",
        "> Generated from the same equations and hardware assumptions as `REPORT.md`.",
        "> It is a dense control result, not a recommendation to make Qwen3-8B a product target.",
        "",
        "## Evidence and workload contract",
        "",
        f"- Official checkpoint: `{summary['source_repo']}@{summary['source_revision']}`.",
        f"- Measured all-BF16 storage: {summary['checkpoint_bytes']:,} bytes; ordinary decode",
        f"  streams {summary['dense_weight_bytes']:,} bytes and keeps the",
        f"  {summary['resident_only_weight_bytes']:,}-byte input embedding as a lookup-resident table.",
        f"- Derived decode-active parameter count: {summary['active_parameters']:,}; the untied LM head",
        "  remains ordinary full-matrix decode traffic.",
        f"- Published topology: 36 dense layers, 32 query heads, 8 KV heads, 128 head dimension.",
        f"- Study context: {context['context_tokens']:,} tokens. The conservative assumed BF16 GQA",
        f"  cache reads/stores {context['kv_storage_bytes_per_user']:,.0f} bytes per resident session.",
        "- No speculative scenario is applied because the pinned checkpoint has no attached draft module.",
        "- B200/B300 x1 and x2 analytical profiles are included alongside x4/x8/x16; only x8 is",
        "  a published DGX device count, and every non-x8 cluster is a stated normalization.",
        "",
        "## Required operating points",
        "",
        "Ratios above 1 favor ROM. Speed uses the fastest feasible same-batch GPU; partial TCO",
        "uses the cheapest feasible same-batch GPU and remains an incomplete cost proxy.",
        "",
        "| Batch | ROM user tok/s | Fastest GPU | GPU user tok/s | ROM/GPU speed | Cheapest GPU | GPU/ROM partial TCO | ROM bind |",
        "|---:|---:|---|---:|---:|---|---:|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['batch_size']} | {row['rom_per_user_tokens_s']:,.1f} | "
            f"{row['gpu_arch']} | {row['gpu_per_user_tokens_s']:,.1f} | "
            f"{row['speed_ratio']:.2f}× | {row['cheapest_gpu_arch']} | "
            f"{row['partial_tco_ratio_vs_cheapest_gpu']:.2f}× | "
            f"{row['rom_binding_constraint']} |"
        )
    lines.extend(
        [
            "",
            "## Capacity-bound optima and conclusion",
            "",
            f"- ROM latency/balanced optimum: B{optimum['rom_latency_optimal_batch']}/"
            f"B{optimum['rom_balanced_optimal_batch']}; ROM aggregate-throughput optimum: "
            f"B{optimum['rom_throughput_optimal_batch']}; ROM partial-TCO optimum: "
            f"B{optimum['rom_partial_tco_optimal_batch']}.",
            f"- GPU latency optimum: {optimum['gpu_latency_optimum_label']}; balanced: "
            f"{optimum['gpu_balanced_optimum_label']}; aggregate throughput: "
            f"{optimum['gpu_throughput_optimum_label']}; partial TCO: "
            f"{optimum['gpu_partial_tco_optimum_label']}.",
            f"- ROM exceeds the fastest GPU's global per-user-speed optimum only at batch "
            f"{optimum['rom_speed_superiority_band']}. At B8 and above, the modeled ROM HBM "
            "beachfront binds and both speed and partial TCO favor GPU.",
            f"- One {summary['checkpoint_bytes'] / 160e9 * 100:.2f}%-occupied ROM stage is a useful "
            "dense/GQA verification control, but poor fixed-weight capacity utilization and the "
            "single-batch speed island do not support elevating Qwen3-8B into the target list.",
            "",
        ]
    )
    return "\n".join(lines)


def run_standard(output_dir: Path) -> dict[str, Any]:
    model_dir = ROOT / "configs" / "models"
    hardware_path = ROOT / "configs" / "hardware" / "architectures.json"
    models = load_model_dir(model_dir)
    gpus, rom, hardware_metadata = load_architectures(hardware_path)
    simulator = AnalyticalSimulator(HardwareProfile(gpu=gpus[0], rom=rom))
    all_arches = [*gpus, rom]
    points: dict[tuple[str, int, str, int, str], OperatingPoint] = {}
    csv_rows: list[dict[str, Any]] = []
    for model in models:
        for context in _contexts_for(model):
            for scenario_name, speculation in _scenarios_for(model).items():
                for batch in SWEEP_BATCHES:
                    request = SimulationRequest(
                        context_tokens=context,
                        batch_size=batch,
                        speculation=speculation,
                    )
                    for arch in all_arches:
                        point = simulator.simulate(model, arch, request)
                        points[(model.name, context, scenario_name, batch, arch.name)] = point
                        csv_rows.append(_compact(point, scenario_name))

    # Keep the committed sweep file compact, but optimize over every integer batch
    # through each architecture's local capacity. Only the exact endpoint is added
    # to the CSV; optimum point records in analytical.json make the exhaustive
    # search auditable without multiplying the artifact size.
    optimization_points: dict[
        tuple[str, int, str, str], list[OperatingPoint]
    ] = {}
    for model in models:
        for context in _contexts_for(model):
            for scenario_name, speculation in _scenarios_for(model).items():
                for arch in all_arches:
                    candidates = [
                        points[(model.name, context, scenario_name, batch, arch.name)]
                        for batch in SWEEP_BATCHES
                    ]
                    capacity_batch = int(
                        candidates[0].metrics["C7_C8_max_batch_per_stage"]
                    )
                    endpoint = None
                    for batch in range(max(SWEEP_BATCHES) + 1, capacity_batch + 1):
                        request = SimulationRequest(
                            context_tokens=context,
                            batch_size=batch,
                            speculation=speculation,
                        )
                        endpoint = simulator.simulate(model, arch, request)
                        candidates.append(endpoint)
                    if endpoint is not None:
                        points[
                            (
                                model.name,
                                context,
                                scenario_name,
                                capacity_batch,
                                arch.name,
                            )
                        ] = endpoint
                        csv_rows.append(_compact(endpoint, scenario_name))
                    optimization_points[
                        (model.name, context, scenario_name, arch.name)
                    ] = candidates

    required: list[dict[str, Any]] = []
    comparisons: list[dict[str, Any]] = []
    optima: list[dict[str, Any]] = []
    for model in models:
        for context in _contexts_for(model):
            for scenario_name in _scenarios_for(model):
                rom_points = optimization_points[
                    (model.name, context, scenario_name, rom.name)
                ]
                gpu_points = [
                    point
                    for gpu in gpus
                    for point in optimization_points[
                        (model.name, context, scenario_name, gpu.name)
                    ]
                ]
                gpu_best_user = _best(gpu_points, "per_user_tokens_s", True)
                gpu_balanced = _balanced(gpu_points)
                gpu_throughput = _best(gpu_points, "aggregate_tokens_s", True)
                gpu_cost = _best(gpu_points, "partial_tco_per_million_tokens", False)
                rom_latency = _best(rom_points, "per_user_tokens_s", True)
                rom_balanced = _balanced(rom_points)
                rom_throughput = _best(rom_points, "aggregate_tokens_s", True)
                rom_cost = _best(rom_points, "partial_tco_per_million_tokens", False)
                superior = [
                    point.batch_size
                    for point in rom_points
                    if point.feasible
                    and point.batch_size in SWEEP_BATCHES
                    and gpu_best_user is not None
                    and point.per_user_tokens_s > gpu_best_user.per_user_tokens_s
                ]
                if superior:
                    band = f"{min(superior)}-{max(superior)}"
                else:
                    band = "none"
                optima.append({
                    "model": model.name,
                    "context_tokens": context,
                    "scenario": scenario_name,
                    "rom_throughput_optimal_batch": None if rom_throughput is None else rom_throughput.batch_size,
                    "rom_partial_tco_optimal_batch": (
                        None if rom_cost is None else rom_cost.batch_size
                    ),
                    "rom_latency_optimal_batch": None if rom_latency is None else rom_latency.batch_size,
                    "rom_balanced_optimal_batch": None if rom_balanced is None else rom_balanced.batch_size,
                    "rom_latency_optimum": _point_ref(rom_latency),
                    "rom_balanced_optimum": _point_ref(rom_balanced),
                    "rom_throughput_optimum": _point_ref(rom_throughput),
                    "rom_partial_tco_optimum": _point_ref(rom_cost),
                    "gpu_best_per_user": _point_ref(gpu_best_user),
                    "gpu_balanced_optimum": _point_ref(gpu_balanced),
                    "gpu_throughput_optimum": _point_ref(gpu_throughput),
                    "gpu_partial_tco_optimum": _point_ref(gpu_cost),
                    "gpu_best_per_user_tokens_s": 0 if gpu_best_user is None else gpu_best_user.per_user_tokens_s,
                    "gpu_latency_optimum_label": (
                        "—" if gpu_best_user is None else f"{gpu_best_user.architecture}/B{gpu_best_user.batch_size}"
                    ),
                    "gpu_balanced_optimum_label": (
                        "—" if gpu_balanced is None else f"{gpu_balanced.architecture}/B{gpu_balanced.batch_size}"
                    ),
                    "gpu_throughput_optimum_label": (
                        "—"
                        if gpu_throughput is None
                        else f"{gpu_throughput.architecture}/B{gpu_throughput.batch_size}"
                    ),
                    "gpu_partial_tco_optimum_label": (
                        "—"
                        if gpu_cost is None
                        else f"{gpu_cost.architecture}/B{gpu_cost.batch_size}"
                    ),
                    "rom_speed_superiority_band": band,
                })
                for batch in REQUIRED_BATCHES:
                    rom_point = points[(model.name, context, scenario_name, batch, rom.name)]
                    same_batch_gpus = [
                        points[(model.name, context, scenario_name, batch, gpu.name)] for gpu in gpus
                    ]
                    # Compare to the fastest feasible GPU at the same per-user batch.
                    gpu_point = _best(same_batch_gpus, "per_user_tokens_s", True)
                    fastest_b200 = _best(
                        [point for point in same_batch_gpus if "B200" in point.architecture],
                        "per_user_tokens_s",
                        True,
                    )
                    fastest_b300 = _best(
                        [point for point in same_batch_gpus if "B300" in point.architecture],
                        "per_user_tokens_s",
                        True,
                    )
                    required.append(_compact(rom_point, scenario_name))
                    required.extend(_compact(point, scenario_name) for point in same_batch_gpus)
                    speed_ratio = (
                        rom_point.per_user_tokens_s / gpu_point.per_user_tokens_s
                        if rom_point.feasible and gpu_point is not None and gpu_point.per_user_tokens_s
                        else None
                    )
                    partial_tco_ratio = (
                        gpu_point.partial_tco_per_million_tokens
                        / rom_point.partial_tco_per_million_tokens
                        if rom_point.feasible
                        and gpu_point is not None
                        and rom_point.partial_tco_per_million_tokens
                        else None
                    )
                    cheapest_gpu = _best(
                        same_batch_gpus, "partial_tco_per_million_tokens", False
                    )
                    cheapest_partial_tco_ratio = (
                        cheapest_gpu.partial_tco_per_million_tokens
                        / rom_point.partial_tco_per_million_tokens
                        if rom_point.feasible
                        and cheapest_gpu is not None
                        and rom_point.partial_tco_per_million_tokens
                        else None
                    )
                    comparisons.append({
                        "model": model.name,
                        "context_tokens": context,
                        "scenario": scenario_name,
                        "batch_size": batch,
                        "rom_per_user_tokens_s": rom_point.per_user_tokens_s if rom_point.feasible else None,
                        "rom_partial_tco_per_million_tokens": (
                            rom_point.partial_tco_per_million_tokens
                            if rom_point.feasible
                            else None
                        ),
                        "rom_binding_constraint": rom_point.binding_constraint,
                        "rom_resident_users_required": rom_point.metrics["C7_C8_resident_users_required"],
                        "gpu_arch": None if gpu_point is None else gpu_point.architecture,
                        "gpu_per_user_tokens_s": None if gpu_point is None else gpu_point.per_user_tokens_s,
                        "gpu_partial_tco_per_million_tokens": (
                            None if gpu_point is None else gpu_point.partial_tco_per_million_tokens
                        ),
                        "speed_ratio": speed_ratio,
                        "fastest_b200_arch": (
                            None if fastest_b200 is None else fastest_b200.architecture
                        ),
                        "fastest_b200_per_user_tokens_s": (
                            None if fastest_b200 is None else fastest_b200.per_user_tokens_s
                        ),
                        "speed_ratio_vs_b200": (
                            rom_point.per_user_tokens_s / fastest_b200.per_user_tokens_s
                            if rom_point.feasible
                            and fastest_b200 is not None
                            and fastest_b200.per_user_tokens_s
                            else None
                        ),
                        "fastest_b300_arch": (
                            None if fastest_b300 is None else fastest_b300.architecture
                        ),
                        "fastest_b300_per_user_tokens_s": (
                            None if fastest_b300 is None else fastest_b300.per_user_tokens_s
                        ),
                        "speed_ratio_vs_b300": (
                            rom_point.per_user_tokens_s / fastest_b300.per_user_tokens_s
                            if rom_point.feasible
                            and fastest_b300 is not None
                            and fastest_b300.per_user_tokens_s
                            else None
                        ),
                        "partial_tco_ratio": partial_tco_ratio,
                        "cheapest_gpu_arch": None if cheapest_gpu is None else cheapest_gpu.architecture,
                        "cheapest_gpu_partial_tco_per_million_tokens": (
                            None
                            if cheapest_gpu is None
                            else cheapest_gpu.partial_tco_per_million_tokens
                        ),
                        "partial_tco_ratio_vs_cheapest_gpu": (
                            cheapest_partial_tco_ratio
                        ),
                    })

    # Capacity-match the service population, not merely the active microbatch.
    concurrency_matches: list[dict[str, Any]] = []
    for model in models:
        for context in _contexts_for(model):
            for batch in (1, 8, 64):
                rom_point = points[(model.name, context, "no_speculation", batch, rom.name)]
                resident = int(rom_point.metrics["C7_C8_resident_users_required"])
                request = SimulationRequest(context_tokens=context, batch_size=resident)
                gpu_at_resident = [simulator.simulate(model, gpu, request) for gpu in gpus]

                def smallest_family(family: str) -> OperatingPoint | None:
                    candidates = [
                        point for point in gpu_at_resident
                        if family in point.architecture and point.feasible
                    ]
                    return (
                        min(candidates, key=lambda point: int(point.architecture.rsplit("x", 1)[1]))
                        if candidates
                        else None
                    )

                cheapest = _best(
                    gpu_at_resident, "partial_tco_per_million_tokens", False
                )
                partial_tco_ratio = (
                    cheapest.partial_tco_per_million_tokens
                    / rom_point.partial_tco_per_million_tokens
                    if rom_point.feasible
                    and cheapest is not None
                    and rom_point.partial_tco_per_million_tokens
                    else None
                )
                concurrency_matches.append({
                    "model": model.name,
                    "context_tokens": context,
                    "batch_per_stage": batch,
                    "resident_sessions": resident,
                    "rom": _compact(rom_point, "no_speculation"),
                    "smallest_b200": _point_ref(smallest_family("B200")),
                    "smallest_b300": _point_ref(smallest_family("B300")),
                    "cheapest_gpu": _point_ref(cheapest),
                    "partial_tco_ratio_vs_cheapest_gpu": partial_tco_ratio,
                })

    model_summaries = []
    for model in models:
        dense_active_parameters = max(
            0.0, min(model.active_parameters, model.dense_parameters)
        )
        contexts = []
        for context in _contexts_for(model):
            point = points[(model.name, context, "no_speculation", 1, rom.name)]
            contexts.append({
                "context_tokens": context,
                "kv_read_bytes_per_user_token": point.metrics["C2_kv_read_bytes_per_user_token"],
                "kv_storage_bytes_per_user": point.metrics["C7_C8_kv_storage_bytes_per_user"],
                "rho_one": point.rho_one,
                "rom_stages": point.stages,
            })
        model_summaries.append({
            "model": model.name,
            "source_repo": model.source_repo,
            "source_revision": model.source_revision,
            "total_parameters": model.total_parameters,
            "active_parameters": model.active_parameters,
            "dense_active_parameters": dense_active_parameters,
            "routed_active_parameters": (
                model.active_parameters - dense_active_parameters
            ),
            "checkpoint_bytes": model.checkpoint_bytes,
            "dense_weight_bytes": model.dense_weight_bytes,
            "routed_weight_bytes": model.routed_weight_bytes,
            "draft_dense_weight_bytes": model.draft_dense_weight_bytes,
            "draft_routed_weight_bytes": model.draft_routed_weight_bytes,
            "resident_only_weight_bytes": model.resident_only_weight_bytes,
            "dense_compute_format": model.dense_compute_format,
            "routed_compute_format": model.routed_compute_format,
            "compute_precision_status": model.metadata.get(
                "compute_precision_status", "unspecified"
            ),
            "contexts": contexts,
        })
    result = {
        "schema_version": 4,
        "inputs": {
            "contexts_by_model": {
                model.name: list(_contexts_for(model)) for model in models
            },
            "required_batches": list(REQUIRED_BATCHES),
            "sweep_batches": [min(SWEEP_BATCHES), max(SWEEP_BATCHES)],
            "optimization_policy": (
                "exhaustive_integer_batches_through_each_architecture_capacity; "
                "sweep_csv_retains_dense_1_through_256_plus_capacity_endpoints"
            ),
            "scenarios": {name: asdict(spec) for name, spec in SCENARIOS.items()},
            "scenarios_by_model": {
                model.name: list(_scenarios_for(model)) for model in models
            },
            "hardware_sha256": _sha256(hardware_path),
            "model_sha256": {path.name: _sha256(path) for path in sorted(model_dir.glob("*.json"))},
            "hardware_metadata": hardware_metadata,
        },
        "required_points": required,
        "comparisons": comparisons,
        "optima": optima,
        "concurrency_matches": concurrency_matches,
        "model_summaries": model_summaries,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "analytical.json").write_text(
        json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    with (output_dir / "sweep.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=list(csv_rows[0]), lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(csv_rows)
    (output_dir / "REPORT.md").write_text(render_report(result), encoding="utf-8")
    (output_dir / "QWEN3_8B_ADDENDUM.md").write_text(
        render_qwen_addendum(result), encoding="utf-8"
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--standard", action="store_true", help="run the fixed verification matrix")
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "standard")
    args = parser.parse_args()
    if not args.standard:
        parser.error("currently supported mode: --standard")
    result = run_standard(args.output)
    print(f"wrote {args.output / 'analytical.json'}")
    print(f"wrote {args.output / 'sweep.csv'}")
    print(f"wrote {args.output / 'REPORT.md'}")
    print(f"wrote {args.output / 'QWEN3_8B_ADDENDUM.md'}")
    print(f"evaluated {len(result['required_points'])} required architecture points")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
