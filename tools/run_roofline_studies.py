#!/usr/bin/env python3
"""Run the area-constrained roofline studies and render their report.

Every number emitted here comes from ``opentallas.roofline`` evaluating
``configs/hardware/technology.json`` against the released model profiles.  No
figure in the generated report is hand-computed, and the two validation gates
run inside the study so a methodology drift shows up in the artifact rather than
only in the test suite.

Two studies are produced, each iso-node and each iso-area:

* ``n6_vs_a100``  -- reticle-class ROM silicon at TSMC N6 against NVIDIA A100
  80GB at N7.  This is the pairing the Taalas HC1 anchor validates: 815 mm2 at
  N6 against 826 mm2 at N7, essentially the same die one node apart.
* ``n5_vs_b200``  -- ROM silicon at N5 against NVIDIA B200 at 4NP, counted per
  two-die package so the areas match.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from opentallas.roofline import (  # noqa: E402
    DeviceBudget,
    RooflineStep,
    Technology,
    Topology,
    a100_weight_bound_anchor,
    evaluate,
    gpu_device_budget,
    latency_crossover,
    max_hbm_stacks_per_device,
    rom_device_budget,
    taalas_hc1_anchor,
)
from opentallas.schema import ModelProfile  # noqa: E402
from opentallas.workload import kv_traffic  # noqa: E402


TECHNOLOGY_PATH = ROOT / "configs" / "hardware" / "technology.json"
OUTPUT_ROOT = ROOT / "results" / "roofline"
ARTIFACTS = ("analytical.json", "sweep.csv", "REPORT.md")

ANCHOR_MODEL_PATH = (
    ROOT / "configs" / "models" / "anchors" / "llama-3.1-8b.json"
)
"""The anchor model lives under ``anchors/`` rather than beside the study
models because ``configs/models/*.json`` is globbed by the legacy standard run
and by the NoC sweep, which evaluate every profile they find at contexts this
model cannot serve. It is a validation fixture, not a study target."""

# Model, its study context, and why that context.
STUDY_MODELS: tuple[tuple[str, Path, int], ...] = (
    (
        "Qwen3-8B",
        ROOT / "configs" / "models" / "qwen3-8b.json",
        8_192,
    ),
    (
        "DeepSeek-V4-Flash-0731",
        ROOT / "configs" / "models" / "deepseek-v4-flash-0731.json",
        200_000,
    ),
    (
        "DeepSeek-V4-Pro-0813",
        ROOT / "configs" / "models" / "deepseek-v4-pro-0813.json",
        1_000_000,
    ),
)
BATCHES = (1, 8, 32, 64, 256)
DESIGN_BATCH = 1
"""SRAM area is silicon area, so an SRAM-KV design is sized at batch 1 -- the
minimum machine -- and the study then reports the batch at which its KV capacity
runs out.  HBM capacity is bought in stacks rather than in die area, so an
HBM-KV design is instead provisioned for the largest study batch, subject to the
die-edge beachfront check."""
PROVISION_BATCH = max(BATCHES)

STUDIES: dict[str, dict[str, Any]] = {
    "n6_vs_a100": {
        "rom_node": "N6",
        "gpu_parts": ("a100_sxm_80gb",),
        "hbm_generation": "hbm2e",
        "contract": (
            "Reticle-class mask-ROM silicon at TSMC N6 against NVIDIA A100 80GB at "
            "N7, compared at equal silicon area with the area stated on both sides. "
            "This is the pairing the Taalas HC1 anchor validates: 815 mm2 at N6 "
            "against 826 mm2 at N7, essentially the same die one node apart."
        ),
    },
    "n5_vs_b200": {
        "rom_node": "N5",
        "gpu_parts": ("b200_sxm",),
        "hbm_generation": "hbm3e",
        "contract": (
            "Mask-ROM silicon at TSMC N5 against NVIDIA B200 at 4NP, compared at "
            "equal silicon area. Blackwell is a two-die package, so B200 is counted "
            "per package at 1,600 mm2 of silicon."
        ),
    },
}

# The policy list has exactly one definition, in the model.  This file used
# to keep its own copy, and a second restatement of one list is how the two
# come apart -- the third policy was added to the model and silently not
# studied here.
from opentallas.roofline import WEIGHT_AMORTIZATIONS  # noqa: E402
"""The unresolved architectural fork from docs/ISO_AREA_COMPARISON_AND_THE_TAALAS_ANCHOR.md.
``batched`` is ROM-as-storage feeding a separate MAC array, where one sweep
serves the whole batch. ``per_stream`` is compute-in-ROM, where a cell both
stores and multiplies, so each concurrent stream needs its own pass and
aggregate per-die throughput collapses onto per-user throughput. They are
identical at batch 1, which is exactly why the Taalas anchor cannot settle the
question. Both are evaluated; the main tables show ``batched`` and the fork
section shows the difference."""
ARRAY_SWEEP_CAP = 400
SWEEP_PATIENCE = 8
"""Stop the device sweep once eight consecutive larger machines fail to beat the
best latency found so far.  Adding devices adds compute area but also adds a
serial hop, so the curve has one minimum."""
DEVICE_SIZING_TOLERANCE = 0.02
"""A design point is the smallest device count within 2% of the best latency the
sweep found.  Without this a model is handed a whole wafer to buy the last 1% of
a rate it already had on four chips."""
BEST_DESIGN_TOLERANCE = 0.05
"""When the topology-choice table names a winner it takes the smallest silicon
area within 5% of the best per-user rate, so a topology cannot win by simply
being handed more silicon."""
MAX_OVERPROVISION = 4
"""A design may spend at most four times the device count its stored weights and
resident KV actually demand.  Beyond that it is a different machine and belongs
in the comparison as one, not as a sizing choice; without this bound the
latency-minimising sweep will hand an 8B model twenty-one wafers to buy the last
few percent of KV bandwidth."""


def _rom_sweep_time_s(technology: Technology, node: str) -> float:
    """The ROM full-array sweep time, which is the ROM path's hard floor.

    HBM is provisioned against this: there is no point buying KV bandwidth that
    would beat a floor the weight path cannot beat anyway.
    """

    capacity_bytes_per_mm2 = technology.rom_bits_per_mm2(node).value / 8.0
    bandwidth = (
        technology.rom_read_bytes_s_per_mm2(node).value
        * technology.efficiency("rom_read_bandwidth").value
    )
    return capacity_bytes_per_mm2 / bandwidth


def _model_tag(model: ModelProfile) -> str:
    """Short, stable tag so design identifiers do not collide across models."""

    return model.name.split("-0")[0].replace("DeepSeek-V4-", "DSV4-")


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _finite(value: float) -> float | None:
    return value if math.isfinite(value) else None


def _representations(model: ModelProfile) -> tuple[tuple[str, float | None], ...]:
    """Stored representations offered to a mask-ROM design.

    Mask ROM freezes the representation at manufacture, so it is a design
    variable rather than an inherited constant.  ``None`` means the released
    checkpoint's own packing.  An FP8 variant is offered only where it is
    actually smaller than the release: DeepSeek V4 ships MXFP4 routed experts at
    roughly 4.5 bits per parameter, so re-encoding it to FP8 would nearly double
    the ROM array.
    """

    native_bits = model.checkpoint_bytes / model.total_parameters * 8.0
    options: list[tuple[str, float | None]] = [("native", None)]
    if native_bits > 8.5:
        options.append(("fp8", 8.0))
    return tuple(options)


def _execution_format(technology: Technology, bits: float | None, model: ModelProfile) -> str:
    """Canonical datapath a model-specific ROM part would build for a representation.

    A part that stores 8-bit weights builds an 8-bit datapath; one that stores
    4-to-5-bit weights against 8-bit activations builds a w4a8 datapath.  The
    released checkpoint's arithmetic is not automatically what the ASIC executes.
    """

    if bits is None:
        bits = model.checkpoint_bytes / model.total_parameters * 8.0
    if bits <= 6.0:
        return "w4a8"
    if bits <= 8.5:
        return "fp8"
    return "bf16"


def _rom_stored_bytes(model: ModelProfile, bits: float | None) -> float:
    if bits is None:
        return model.checkpoint_bytes
    return model.total_parameters * bits / 8.0


def _hbm_stacks_for(
    technology: Technology,
    *,
    generation: str,
    resident_kv_bytes: float,
    kv_transfer_bytes: float,
    sweep_time_s: float,
    die_area_mm2: float,
    devices: int,
) -> int:
    """Stacks per device, provisioned for KV capacity *and* KV bandwidth.

    Weights live in ROM on these designs, so HBM carries only the mutable KV.
    The stated provisioning rule is: enough stacks that neither KV capacity nor
    KV bandwidth binds before the ROM full-array sweep does, capped by what the
    die edge can physically attach at the beachfront utilisation shipping GPUs
    achieve.  When the cap bites, KV bandwidth or capacity binds -- and that is
    a physical result about die perimeter, not a modelling shortcut.
    """

    capacity = technology.hbm(generation, "stack_capacity_bytes").value
    usable = capacity * technology.efficiency("hbm_capacity").value
    bandwidth = (
        technology.hbm(generation, "stack_bandwidth_bytes_s").value
        * technology.efficiency("hbm_bandwidth").value
    )
    for_capacity = math.ceil(resident_kv_bytes / max(1, devices) / usable)
    for_bandwidth = (
        math.ceil(kv_transfer_bytes / max(1, devices) / (sweep_time_s * bandwidth))
        if sweep_time_s > 0
        else 0
    )
    limit = max_hbm_stacks_per_device(
        technology, generation=generation, die_area_mm2=die_area_mm2
    )
    return max(1, min(limit, max(for_capacity, for_bandwidth)))


# --------------------------------------------------------------------------
# design construction
# --------------------------------------------------------------------------


def _build_rom_budget(
    technology: Technology,
    *,
    name: str,
    node: str,
    area_per_device: float,
    devices: int,
    parallelism: str,
    link: str,
    kind: str,
    on_wafer_regions: int,
    stored_weight_bytes: float,
    resident_kv_bytes: float,
    kv_transfer_bytes: float,
    kv_store: str,
    hbm_generation: str,
    weight_amortization: str = "batched",
) -> DeviceBudget:
    stacks = 0
    if kv_store == "hbm":
        stacks = _hbm_stacks_for(
            technology,
            generation=hbm_generation,
            resident_kv_bytes=resident_kv_bytes,
            kv_transfer_bytes=kv_transfer_bytes,
            sweep_time_s=_rom_sweep_time_s(technology, node),
            die_area_mm2=area_per_device,
            devices=devices,
        )
    topology = Topology(
        kind=kind,
        device_count=devices,
        parallelism=parallelism,
        link=link,
        on_wafer_regions=on_wafer_regions,
    )
    return rom_device_budget(
        technology,
        name=name,
        node=node,
        area_mm2_per_device=area_per_device,
        topology=topology,
        stored_weight_bytes=stored_weight_bytes,
        resident_kv_bytes=resident_kv_bytes if kv_store == "sram" else 0.0,
        kv_store=kv_store,
        hbm_stacks=stacks,
        hbm_generation=hbm_generation,
        weight_amortization=weight_amortization,
    )


def _minimum_devices(
    technology: Technology,
    *,
    node: str,
    area_per_device: float,
    stored_weight_bytes: float,
    resident_kv_bytes: float,
    kv_transfer_bytes: float,
    kv_store: str,
    hbm_generation: str,
    parallelism: str,
    link: str,
    kind: str,
    wafer_area: float | None,
    reticle_area: float | None,
) -> int:
    """Fewest devices that can physically hold the design.

    ROM area is fixed by the stored weights and SRAM area by the resident KV, so
    the remainder available for compute is what device count actually buys.  For
    an HBM-KV design the die edge is a second, independent floor: a machine that
    cannot attach enough stacks to hold the provisioning batch's KV needs more
    dies, however much compute area it already has.
    """

    usable_stack = (
        technology.hbm(hbm_generation, "stack_capacity_bytes").value
        * technology.efficiency("hbm_capacity").value
    )
    for devices in range(1, ARRAY_SWEEP_CAP + 1):
        regions = 1
        if kind == "wafer" and wafer_area and reticle_area:
            regions = max(1, math.ceil(devices * wafer_area / reticle_area))
        budget = _build_rom_budget(
            technology,
            name="minimum-probe",
            node=node,
            area_per_device=area_per_device,
            devices=devices,
            parallelism=parallelism,
            link=link,
            kind=kind,
            on_wafer_regions=regions,
            stored_weight_bytes=stored_weight_bytes,
            resident_kv_bytes=resident_kv_bytes,
            kv_transfer_bytes=kv_transfer_bytes,
            kv_store=kv_store,
            hbm_generation=hbm_generation,
        )
        if budget.reasons or budget.split.compute_mm2 <= 0:
            continue
        if budget.weight_capacity_bytes + 1.0 < stored_weight_bytes:
            continue
        if kv_store == "hbm":
            attachable = (
                max_hbm_stacks_per_device(
                    technology,
                    generation=hbm_generation,
                    die_area_mm2=area_per_device,
                )
                * devices
                * usable_stack
            )
            if attachable + 1.0 < resident_kv_bytes:
                continue
        elif budget.kv_capacity_bytes + 1.0 < resident_kv_bytes:
            continue
        return devices
    return ARRAY_SWEEP_CAP + 1


def _size_array(
    technology: Technology,
    model: ModelProfile,
    *,
    node: str,
    area_per_device: float,
    stored_weight_bytes: float,
    resident_kv_bytes: float,
    kv_transfer_bytes: float,
    kv_store: str,
    hbm_generation: str,
    context_tokens: int,
    execution_format: str,
    weight_bits: float | None,
    parallelism: str,
    link: str,
    kind: str,
    wafer_area: float | None = None,
    reticle_area: float | None = None,
) -> tuple[int, list[dict[str, Any]]]:
    """Choose the device count that minimises per-user token latency at batch 1.

    Adding devices adds compute area and SRAM area but leaves total ROM area --
    and therefore the ROM full-array sweep time -- unchanged, because ROM area
    is set by the stored weights.  It also adds one serial hop per device under
    pipeline parallelism.  The optimum is therefore where compute stops being
    the binding term, and beyond it the interconnect takes over: the sweep below
    is exactly the wafer-versus-array trade, resolved rather than asserted.
    """

    minimum = _minimum_devices(
        technology,
        node=node,
        area_per_device=area_per_device,
        stored_weight_bytes=stored_weight_bytes,
        resident_kv_bytes=resident_kv_bytes,
        kv_transfer_bytes=kv_transfer_bytes,
        kv_store=kv_store,
        hbm_generation=hbm_generation,
        parallelism=parallelism,
        link=link,
        kind=kind,
        wafer_area=wafer_area,
        reticle_area=reticle_area,
    )
    if minimum > ARRAY_SWEEP_CAP:
        return minimum, []
    upper = min(ARRAY_SWEEP_CAP, minimum * MAX_OVERPROVISION)
    sweep: list[dict[str, Any]] = []
    best_latency = math.inf
    stale = 0
    for devices in range(minimum, upper + 1):
        regions = 1
        if kind == "wafer" and wafer_area and reticle_area:
            regions = max(1, math.ceil(devices * wafer_area / reticle_area))
        budget = _build_rom_budget(
            technology,
            name="sizing-probe",
            node=node,
            area_per_device=area_per_device,
            devices=devices,
            parallelism=parallelism,
            link=link,
            kind=kind,
            on_wafer_regions=regions,
            stored_weight_bytes=stored_weight_bytes,
            resident_kv_bytes=resident_kv_bytes,
            kv_transfer_bytes=kv_transfer_bytes,
            kv_store=kv_store,
            hbm_generation=hbm_generation,
        )
        step = evaluate(
            budget,
            model,
            context_tokens=context_tokens,
            batch_size=DESIGN_BATCH,
            technology=technology,
            weight_bits_per_parameter=weight_bits,
            execution_format=execution_format,
        )
        latency = step.step_time_s if step.feasible else math.inf
        sweep.append(
            {
                "device_count": devices,
                "silicon_area_mm2": budget.silicon_area_mm2_total,
                "compute_mm2_per_device": budget.split.compute_mm2,
                "feasible": step.feasible,
                "per_user_tokens_s": step.per_user_tokens_s,
                "step_time_s": _finite(step.step_time_s),
                "binding_constraint": step.binding_constraint,
                "component_times_s": dict(step.component_times_s),
            }
        )
        if latency < best_latency * (1.0 - 1e-12):
            best_latency = latency
            stale = 0
        else:
            stale += 1
            if stale >= SWEEP_PATIENCE and math.isfinite(best_latency):
                break
    # Buying more silicon than the latency actually rewards is the failure this
    # model exists to catch, so the design point is the SMALLEST device count
    # within DEVICE_SIZING_TOLERANCE of the best latency in the sweep, not the
    # fastest point in it.
    threshold = best_latency * (1.0 + DEVICE_SIZING_TOLERANCE)
    for entry in sweep:
        if entry["feasible"] and entry["step_time_s"] is not None:
            if entry["step_time_s"] <= threshold:
                return entry["device_count"], sweep
    return minimum, sweep


# --------------------------------------------------------------------------
# study
# --------------------------------------------------------------------------


def _step_row(
    step: RooflineStep,
    budget: DeviceBudget,
    *,
    family: str,
    design_id: str,
    model: ModelProfile,
) -> dict[str, Any]:
    metrics = step.metrics
    return {
        "family": family,
        "design": design_id,
        "model": step.model,
        "context_tokens": step.context_tokens,
        "batch_size": step.batch_size,
        "device_count": budget.topology.device_count,
        "topology_kind": budget.topology.kind,
        "parallelism": budget.topology.parallelism,
        "link": budget.topology.link,
        "node": budget.node,
        "weight_store": budget.weight_store,
        "kv_store": budget.kv_store,
        "weight_amortization": budget.weight_amortization,
        "rom_sweeps_per_step": metrics.get("rom_sweeps_per_step"),
        "silicon_area_mm2": step.silicon_area_mm2,
        "silicon_area_mm2_per_device": budget.silicon_area_mm2_per_device,
        "feasible": step.feasible,
        "reasons": list(step.reasons),
        "per_user_tokens_s": step.per_user_tokens_s,
        "aggregate_tokens_s": step.aggregate_tokens_s,
        "step_time_s": _finite(step.step_time_s),
        "binding_constraint": step.binding_constraint,
        "component_times_s": dict(step.component_times_s),
        "power_w": step.power_w,
        "thermal_scale": step.thermal_scale,
        "stored_weight_bytes": metrics["stored_weight_bytes"],
        "engaged_weight_bytes": metrics["engaged_weight_bytes"],
        "engaged_weight_fraction": metrics["engaged_weight_fraction"],
        "expert_coverage": metrics["expert_coverage"],
        "engaged_devices": metrics["engaged_devices"],
        "effective_weight_read_bytes_s": metrics["effective_weight_read_bytes_s"],
        "peak_weight_read_bytes_s": metrics["peak_weight_read_bytes_s"],
        "kv_transfer_bytes_per_step": metrics["kv_transfer_bytes_per_step"],
        "resident_kv_bytes": metrics["resident_kv_bytes"],
        "max_resident_users": metrics["max_resident_users"],
        "weight_capacity_bytes": metrics["weight_capacity_bytes"],
        "kv_capacity_bytes": metrics["kv_capacity_bytes"],
        "weight_to_kv_read_ratio": _finite(metrics["weight_to_kv_read_ratio"]),
        "execution_format": metrics["execution_format"],
        "hop_events_per_token": metrics["hop_events_per_token"],
        "hop_semantics": metrics["hop_semantics"],
        "operations_by_canonical_format": dict(
            metrics["operations_by_canonical_format"]
        ),
        "area_fractions": budget.split.fractions(),
        "rom_full_array_sweep_time_s": metrics.get("rom_full_array_sweep_time_s"),
        "rom_sweep_ceiling_tokens_s": metrics.get("rom_sweep_ceiling_tokens_s"),
        "overlap_rule": metrics["overlap_rule"],
    }


def _iso_area_gpu_counts(
    technology: Technology, part: str, target_area_mm2: float
) -> int:
    spec = technology.reference_part(part)
    area = float(spec["die_area_mm2"]["value"])
    return max(1, int(round(target_area_mm2 / area)))


def _minimum_gpu_count(
    technology: Technology,
    part: str,
    *,
    stored_weight_bytes: float,
    resident_kv_bytes: float,
) -> int:
    spec = technology.reference_part(part)
    capacity = float(spec["hbm_capacity_bytes"]["value"])
    usable = capacity * technology.efficiency("hbm_capacity").value
    needed = stored_weight_bytes + resident_kv_bytes
    return max(1, math.ceil(needed / usable))


def _simulate_study(study_id: str, technology: Technology) -> dict[str, Any]:
    config = STUDIES[study_id]
    node = str(config["rom_node"])
    hbm_generation = str(config["hbm_generation"])
    reticle_area = technology.graded("reticle", "area_mm2").value
    wafer_area = technology.graded("wafer", "area_mm2").value

    points: list[dict[str, Any]] = []
    designs: list[dict[str, Any]] = []
    comparisons: list[dict[str, Any]] = []
    crossovers: list[dict[str, Any]] = []
    model_summaries: list[dict[str, Any]] = []

    for model_name, model_path, context in STUDY_MODELS:
        model = ModelProfile.load(model_path)
        kv = kv_traffic(model, context)
        model_summaries.append(
            {
                "model": model.name,
                "source_repo": model.source_repo,
                "source_revision": model.source_revision,
                "context_tokens": context,
                "num_layers": model.num_layers,
                "hidden_size": model.hidden_size,
                "total_parameters": model.total_parameters,
                "active_parameters": model.active_parameters,
                "checkpoint_bytes": model.checkpoint_bytes,
                "native_bits_per_parameter": (
                    model.checkpoint_bytes / model.total_parameters * 8.0
                ),
                "kv_read_bytes_per_user_token": kv.read_bytes,
                "kv_write_bytes_per_user_token": kv.write_bytes,
                "kv_storage_bytes_per_user": kv.storage_bytes_per_user,
                "weight_to_kv_read_ratio_b1": (
                    model.dense_weight_bytes
                    + model.routed_weight_bytes * model.routed_fraction_per_token
                )
                / kv.read_bytes,
            }
        )

        for representation, bits in _representations(model):
            stored = _rom_stored_bytes(model, bits)
            execution = _execution_format(technology, bits, model)
            for kv_store in ("sram", "hbm"):
                provision_batch = (
                    DESIGN_BATCH if kv_store == "sram" else PROVISION_BATCH
                )
                design_batch_kv = kv.storage_bytes_per_user * provision_batch
                design_batch_kv_transfer = (
                    kv.read_bytes + kv.write_bytes
                ) * provision_batch
                for (
                    topology_name,
                    kind,
                    parallelism,
                    area_per_device,
                ), amortization in (
                    (topology, policy)
                    for topology in (
                        ("array-pipeline", "array", "pipeline", reticle_area),
                        ("array-tensor", "array", "tensor", reticle_area),
                        ("wafer-pipeline", "wafer", "pipeline", wafer_area),
                        ("wafer-tensor", "wafer", "tensor", wafer_area),
                    )
                    for policy in WEIGHT_AMORTIZATIONS
                ):
                    link = "nvlink" if kind == "array" else "on_wafer"
                    # Sizing is done once, on the batched machine, at batch 1
                    # where the two policies are identical by construction.
                    devices, sweep = _size_array(
                        technology,
                        model,
                        node=node,
                        area_per_device=area_per_device,
                        stored_weight_bytes=stored,
                        resident_kv_bytes=design_batch_kv,
                        kv_transfer_bytes=design_batch_kv_transfer,
                        kv_store=kv_store,
                        hbm_generation=hbm_generation,
                        context_tokens=context,
                        execution_format=execution,
                        weight_bits=bits,
                        parallelism=parallelism,
                        link=link,
                        kind=kind,
                        wafer_area=wafer_area if kind == "wafer" else None,
                        reticle_area=reticle_area if kind == "wafer" else None,
                    )
                    if devices > ARRAY_SWEEP_CAP:
                        continue
                    regions = 1
                    if kind == "wafer":
                        regions = max(
                            1, math.ceil(devices * wafer_area / reticle_area)
                        )
                    # A single device has no partition boundary, so a topology
                    # that only differs by its parallelism collapses onto the
                    # pipeline case and is not emitted twice.
                    if parallelism == "tensor" and (
                        devices == 1 and kind == "array"
                    ):
                        continue
                    suffix = {
                        "batched": "",
                        "per_stream": "-perstream",
                        "per_region": "-perregion",
                    }[amortization]
                    design_id = (
                        f"{_model_tag(model)}/ROM-{node}-{representation}-"
                        f"{kv_store.upper()}KV-{topology_name}-x{devices}{suffix}"
                    )
                    budget = _build_rom_budget(
                        technology,
                        name=design_id,
                        node=node,
                        area_per_device=area_per_device,
                        devices=devices,
                        parallelism=parallelism,
                        link=link,
                        kind=kind,
                        on_wafer_regions=regions,
                        stored_weight_bytes=stored,
                        resident_kv_bytes=design_batch_kv,
                        kv_transfer_bytes=design_batch_kv_transfer,
                        kv_store=kv_store,
                        hbm_generation=hbm_generation,
                        weight_amortization=amortization,
                    )
                    designs.append(
                        {
                            "design": design_id,
                            "family": "rom",
                            "model": model.name,
                            "representation": representation,
                            "stored_bits_per_parameter": (
                                bits
                                if bits is not None
                                else model.checkpoint_bytes
                                / model.total_parameters
                                * 8.0
                            ),
                            "execution_format": execution,
                            "topology": topology_name,
                            "weight_amortization": amortization,
                            "sizing_rule": (
                                "smallest device count within "
                                f"{DEVICE_SIZING_TOLERANCE:.0%} of the best per-user "
                                f"latency at batch {DESIGN_BATCH}, bounded at "
                                f"{MAX_OVERPROVISION}x the minimum feasible count. "
                                f"SRAM-KV designs are sized at batch {DESIGN_BATCH} "
                                "because SRAM is silicon area; HBM-KV designs are "
                                f"provisioned for batch {PROVISION_BATCH} for both KV "
                                "capacity and enough KV bandwidth to keep KV off the "
                                "critical path ahead of the ROM sweep, capped by the "
                                "die-edge beachfront a shipping GPU achieves"
                            ),
                            "device_count_sweep": sweep,
                            **budget.to_dict(),
                        }
                    )
                    if amortization == "batched":
                        # Link latency is a property of the topology, so the two
                        # amortisation policies produce identical crossovers.
                        crossovers.append(
                            {
                                "design": design_id,
                                "model": model.name,
                                **latency_crossover(
                                    budget.topology, model, technology
                                ).to_dict(),
                            }
                        )
                    for batch in BATCHES:
                        step = evaluate(
                            budget,
                            model,
                            context_tokens=context,
                            batch_size=batch,
                            technology=technology,
                            weight_bits_per_parameter=bits,
                            execution_format=execution,
                        )
                        points.append(
                            _step_row(
                                step,
                                budget,
                                family="rom",
                                design_id=design_id,
                                model=model,
                            )
                        )

        # --- iso-area GPU baselines --------------------------------------
        rom_areas = sorted(
            {
                round(row["silicon_area_mm2"], 6)
                for row in points
                if row["model"] == model.name and row["family"] == "rom"
            }
        )
        for part in config["gpu_parts"]:
            # No execution-format override for a GPU: the part's own
            # native/emulated table decides what it can run, so A100's lack of
            # an FP8 unit shows up as BF16 emulation rather than as a study knob.
            counts: dict[int, str] = {}
            for area in rom_areas:
                counts.setdefault(
                    _iso_area_gpu_counts(technology, part, area),
                    f"iso-area with {area:,.0f} mm2 of ROM silicon",
                )
            minimum = _minimum_gpu_count(
                technology,
                part,
                stored_weight_bytes=model.checkpoint_bytes,
                resident_kv_bytes=kv.storage_bytes_per_user * PROVISION_BATCH,
            )
            counts.setdefault(
                minimum,
                "smallest cluster whose HBM holds the checkpoint plus the "
                f"batch-{PROVISION_BATCH} KV",
            )
            for count, rationale in sorted(counts.items()):
                topology = Topology(
                    kind="single_chip" if count == 1 else "array",
                    device_count=count,
                    parallelism="none" if count == 1 else "pipeline",
                    link="none" if count == 1 else "nvlink",
                )
                design_id = f"{_model_tag(model)}/{part}-x{count}"
                budget = gpu_device_budget(
                    technology, part=part, topology=topology, name=design_id
                )
                designs.append(
                    {
                        "design": design_id,
                        "family": "gpu",
                        "model": model.name,
                        "representation": "official_packed",
                        "stored_bits_per_parameter": (
                            model.checkpoint_bytes / model.total_parameters * 8.0
                        ),
                        "execution_format": "native where available, else "
                        + ", ".join(
                            f"{src}->{dst}"
                            for src, dst in sorted(budget.emulated_formats.items())
                        )
                        or "native",
                        "topology": "cluster",
                        "sizing_rule": rationale,
                        "device_count_sweep": [],
                        **budget.to_dict(),
                    }
                )
                for batch in BATCHES:
                    step = evaluate(
                        budget,
                        model,
                        context_tokens=context,
                        batch_size=batch,
                        technology=technology,
                    )
                    points.append(
                        _step_row(
                            step,
                            budget,
                            family="gpu",
                            design_id=design_id,
                            model=model,
                        )
                    )

    # --- iso-area comparisons -------------------------------------------
    gpu_rows = [row for row in points if row["family"] == "gpu"]
    for row in points:
        if row["family"] != "rom" or row["weight_amortization"] != "batched":
            continue
        candidates = [
            gpu
            for gpu in gpu_rows
            if gpu["model"] == row["model"] and gpu["batch_size"] == row["batch_size"]
        ]
        if not candidates:
            continue
        iso = min(
            candidates,
            key=lambda gpu: abs(
                gpu["silicon_area_mm2"] - row["silicon_area_mm2"]
            ),
        )
        feasible_gpus = [gpu for gpu in candidates if gpu["feasible"]]
        fastest = (
            max(feasible_gpus, key=lambda gpu: gpu["per_user_tokens_s"])
            if feasible_gpus
            else None
        )
        comparisons.append(
            {
                "model": row["model"],
                "context_tokens": row["context_tokens"],
                "batch_size": row["batch_size"],
                "rom_design": row["design"],
                "rom_silicon_area_mm2": row["silicon_area_mm2"],
                "rom_device_count": row["device_count"],
                "rom_feasible": row["feasible"],
                "rom_reasons": row["reasons"],
                "rom_per_user_tokens_s": row["per_user_tokens_s"],
                "rom_aggregate_tokens_s": row["aggregate_tokens_s"],
                "rom_binding_constraint": row["binding_constraint"],
                "iso_area_gpu_design": iso["design"],
                "iso_area_gpu_silicon_area_mm2": iso["silicon_area_mm2"],
                "iso_area_gpu_device_count": iso["device_count"],
                "iso_area_ratio": (
                    row["silicon_area_mm2"] / iso["silicon_area_mm2"]
                    if iso["silicon_area_mm2"] > 0
                    else None
                ),
                "iso_area_gpu_feasible": iso["feasible"],
                "iso_area_gpu_reasons": iso["reasons"],
                "iso_area_gpu_per_user_tokens_s": iso["per_user_tokens_s"],
                "iso_area_gpu_aggregate_tokens_s": iso["aggregate_tokens_s"],
                "iso_area_gpu_binding_constraint": iso["binding_constraint"],
                "per_user_speed_ratio": (
                    row["per_user_tokens_s"] / iso["per_user_tokens_s"]
                    if row["feasible"] and iso["feasible"] and iso["per_user_tokens_s"] > 0
                    else None
                ),
                "aggregate_speed_ratio": (
                    row["aggregate_tokens_s"] / iso["aggregate_tokens_s"]
                    if row["feasible"] and iso["feasible"] and iso["aggregate_tokens_s"] > 0
                    else None
                ),
                "fastest_feasible_gpu_design": (
                    fastest["design"] if fastest else None
                ),
                "fastest_feasible_gpu_silicon_area_mm2": (
                    fastest["silicon_area_mm2"] if fastest else None
                ),
                "fastest_feasible_gpu_per_user_tokens_s": (
                    fastest["per_user_tokens_s"] if fastest else None
                ),
            }
        )

    # --- topology choice --------------------------------------------------
    topology_choices: list[dict[str, Any]] = []
    for model_name, _, context in STUDY_MODELS:
        for batch in BATCHES:
            rows = [
                row
                for row in points
                if row["model"] == model_name
                and row["batch_size"] == batch
                and row["family"] == "rom"
                and row["weight_amortization"] == "batched"
                and row["feasible"]
            ]
            if not rows:
                topology_choices.append(
                    {
                        "model": model_name,
                        "context_tokens": context,
                        "batch_size": batch,
                        "best_design": None,
                        "best_per_user_tokens_s": None,
                        "array_best_per_user_tokens_s": None,
                        "wafer_best_per_user_tokens_s": None,
                        "array_or_wafer": "no feasible ROM design",
                    }
                )
                continue
            arrays = [row for row in rows if row["topology_kind"] == "array"]
            wafers = [row for row in rows if row["topology_kind"] == "wafer"]
            best = _pick_best(rows, "per_user_tokens_s", "silicon_area_mm2")
            array_best = (
                _pick_best(arrays, "per_user_tokens_s", "silicon_area_mm2")
                if arrays
                else None
            )
            wafer_best = (
                _pick_best(wafers, "per_user_tokens_s", "silicon_area_mm2")
                if wafers
                else None
            )
            topology_choices.append(
                {
                    "model": model_name,
                    "context_tokens": context,
                    "batch_size": batch,
                    "best_design": best["design"],
                    "best_per_user_tokens_s": best["per_user_tokens_s"],
                    "best_aggregate_tokens_s": best["aggregate_tokens_s"],
                    "best_silicon_area_mm2": best["silicon_area_mm2"],
                    "best_binding_constraint": best["binding_constraint"],
                    "best_tokens_s_per_mm2": (
                        best["per_user_tokens_s"] / best["silicon_area_mm2"]
                    ),
                    "array_best_design": array_best["design"] if array_best else None,
                    "array_best_silicon_area_mm2": (
                        array_best["silicon_area_mm2"] if array_best else None
                    ),
                    "wafer_best_silicon_area_mm2": (
                        wafer_best["silicon_area_mm2"] if wafer_best else None
                    ),
                    "array_best_per_user_tokens_s": (
                        array_best["per_user_tokens_s"] if array_best else None
                    ),
                    "wafer_best_design": wafer_best["design"] if wafer_best else None,
                    "wafer_best_per_user_tokens_s": (
                        wafer_best["per_user_tokens_s"] if wafer_best else None
                    ),
                    "array_or_wafer": best["topology_kind"],
                    "array_or_wafer_per_mm2": max(
                        rows,
                        key=lambda row: row["per_user_tokens_s"]
                        / row["silicon_area_mm2"],
                    )["topology_kind"],
                    "wafer_over_array_ratio": (
                        wafer_best["per_user_tokens_s"]
                        / array_best["per_user_tokens_s"]
                        if array_best
                        and wafer_best
                        and array_best["per_user_tokens_s"] > 0
                        else None
                    ),
                }
            )

    amortization_fork: list[dict[str, Any]] = []
    for model_name, _, context in STUDY_MODELS:
        for batch in BATCHES:
            pair: dict[str, dict[str, Any] | None] = {}
            for policy in WEIGHT_AMORTIZATIONS:
                rows = [
                    row
                    for row in points
                    if row["model"] == model_name
                    and row["family"] == "rom"
                    and row["batch_size"] == batch
                    and row["weight_amortization"] == policy
                    and row["feasible"]
                ]
                pair[policy] = (
                    max(rows, key=lambda row: row["aggregate_tokens_s"])
                    if rows
                    else None
                )
            batched = pair.get("batched")
            record: dict[str, Any] = {
                "model": model_name,
                "context_tokens": context,
                "batch_size": batch,
            }
            for policy, point in pair.items():
                record[f"{policy}_design"] = point["design"] if point else None
                record[f"{policy}_per_user_tokens_s"] = (
                    point["per_user_tokens_s"] if point else None
                )
                record[f"{policy}_aggregate_tokens_s"] = (
                    point["aggregate_tokens_s"] if point else None
                )
                record[f"{policy}_binding_constraint"] = (
                    point["binding_constraint"] if point else None
                )
                # How much aggregate throughput this policy gives up against
                # the amortising one.  1.0 means it gives up nothing.
                record[f"{policy}_aggregate_penalty_x"] = (
                    batched["aggregate_tokens_s"] / point["aggregate_tokens_s"]
                    if batched and point and point["aggregate_tokens_s"] > 0
                    else None
                )
            amortization_fork.append(record)
    result: dict[str, Any] = {
        "schema_version": 1,
        "study_id": study_id,
        "comparison_contract": config["contract"],
        "model": "src/opentallas/roofline.py",
        "inputs": {
            "technology_config": str(TECHNOLOGY_PATH.relative_to(ROOT)),
            "technology_sha256": _sha256(TECHNOLOGY_PATH),
            "models": {
                name: {
                    "path": str(path.relative_to(ROOT)),
                    "sha256": _sha256(path),
                    "context_tokens": context,
                }
                for name, path, context in STUDY_MODELS
            },
            "anchor_model": {
                "path": str(ANCHOR_MODEL_PATH.relative_to(ROOT)),
                "sha256": _sha256(ANCHOR_MODEL_PATH),
            },
            "batches": list(BATCHES),
            "rom_node": node,
            "gpu_parts": list(config["gpu_parts"]),
            "hbm_generation": hbm_generation,
            "design_batch": DESIGN_BATCH,
            "provision_batch": PROVISION_BATCH,
            "counting_convention": (
                "one multiply plus one add equals two operations"
            ),
        },
        "technology_derivations": _technology_derivations(technology, node, config),
        "graded_inputs": technology.inputs_by_grade(),
        "model_summaries": model_summaries,
        "designs": designs,
        "points": points,
        "comparisons": comparisons,
        "topology_choices": topology_choices,
        "amortization_fork": amortization_fork,
        "latency_crossovers": crossovers,
    }
    result["consistency_audit"] = _consistency_audit(result)
    return result


def _technology_derivations(
    technology: Technology, node: str, config: dict[str, Any]
) -> dict[str, Any]:
    formats = ("bf16", "fp8", "w4a8", "fp4", "fp32")
    rom_capacity = technology.rom_bits_per_mm2(node)
    rom_bandwidth = technology.rom_read_bytes_s_per_mm2(node)
    rom_eff = technology.efficiency("rom_read_bandwidth")
    sweep = (
        rom_capacity.value / 8.0 / (rom_bandwidth.value * rom_eff.value)
    )
    ideal_sweep = rom_capacity.value / 8.0 / rom_bandwidth.value
    return {
        "node": node,
        "sram_capacity_bits_per_mm2": technology.sram_bits_per_mm2(node).to_dict(),
        "rom_capacity_bits_per_mm2": rom_capacity.to_dict(),
        "rom_read_bytes_s_per_mm2": rom_bandwidth.to_dict(),
        "sram_read_bytes_s_per_mm2": technology.sram_read_bytes_s_per_mm2(
            node
        ).to_dict(),
        "compute_ops_s_per_mm2": {
            fmt: technology.compute_ops_s_per_mm2(node, fmt).to_dict()
            for fmt in formats
        },
        "rom_full_array_sweep_time_s": sweep,
        "rom_full_array_sweep_ceiling_tokens_s": 1.0 / sweep,
        "rom_full_array_sweep_time_s_before_derate": ideal_sweep,
        "rom_full_array_sweep_ceiling_tokens_s_before_derate": 1.0 / ideal_sweep,
        "rom_sweep_note": (
            "The ROM full-array sweep time is rom_capacity_density divided by "
            "rom_read_bandwidth_density. Both scale with the same published "
            "bitcell-area ratio under this derivation, so the sweep time -- and "
            "hence the ROM path's hard per-token ceiling -- is the SAME at every "
            "node. Process scaling buys a ROM design capacity, not per-token "
            "speed. No clock-frequency bonus is credited, which makes this the "
            "conservative reading."
        ),
        "efficiencies": {
            name: technology.efficiency(name).to_dict()
            for name in ("compute", "rom_read_bandwidth", "sram_read_bandwidth",
                         "hbm_bandwidth", "hbm_capacity", "stage_balance")
        },
        "links": {
            name: {
                "hop_latency_s": technology.link(name)[0].to_dict(),
                "bytes_s": technology.link(name)[1].to_dict(),
            }
            for name in ("on_wafer", "on_package", "nvlink", "ethernet")
        },
        "hbm": {
            field: technology.hbm(config["hbm_generation"], field).to_dict()
            for field in (
                "stack_capacity_bytes",
                "stack_bandwidth_bytes_s",
                "stack_beachfront_mm",
                "phy_area_mm2_per_stack",
            )
        },
    }


# --------------------------------------------------------------------------
# audit
# --------------------------------------------------------------------------


def _consistency_audit(result: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    checks = 0

    def check(condition: bool, message: str) -> None:
        nonlocal checks
        checks += 1
        if not condition:
            errors.append(message)

    def close(actual: float, expected: float, tol: float = 1e-9) -> bool:
        return math.isclose(actual, expected, rel_tol=tol, abs_tol=1e-12)

    seen: set[tuple[str, str, int]] = set()
    for row in result["points"]:
        key = (row["design"], row["model"], row["batch_size"])
        check(key not in seen, f"duplicate point {key}")
        seen.add(key)
        if not row["feasible"]:
            check(row["per_user_tokens_s"] == 0.0, f"infeasible per-user rate {key}")
            check(row["aggregate_tokens_s"] == 0.0, f"infeasible aggregate {key}")
            check(bool(row["reasons"]), f"infeasible without a reason {key}")
            continue
        check(row["step_time_s"] is not None and row["step_time_s"] > 0,
              f"non-positive step time {key}")
        check(
            close(row["per_user_tokens_s"], 1.0 / row["step_time_s"]),
            f"per-user rate identity {key}",
        )
        check(
            close(
                row["aggregate_tokens_s"],
                row["batch_size"] * row["per_user_tokens_s"],
            ),
            f"aggregate = batch x per-user identity {key}",
        )
        components = row["component_times_s"]
        service = max(
            components["weight_read"], components["kv_read"], components["compute"]
        )
        # The step time can never fall below the largest single service term
        # divided by the stage-balance derate, and never below the link latency.
        check(
            row["step_time_s"] + 1e-15 >= service,
            f"step below the largest component {key}",
        )
        check(
            row["step_time_s"] + 1e-15 >= components["link_latency"],
            f"step below link latency {key}",
        )
        check(
            row["binding_constraint"]
            in {"weight_read", "kv_read", "compute", "link_latency", "thermal"},
            f"unknown binding constraint {key}: {row['binding_constraint']}",
        )
        if row["binding_constraint"] != "thermal":
            check(
                components[row["binding_constraint"]]
                >= max(components.values()) - 1e-15,
                f"binding constraint is not the largest term {key}",
            )
        check(
            0.0 < row["engaged_weight_fraction"] <= 1.0 + 1e-12,
            f"engaged weight fraction out of range {key}",
        )
        # Under the compute-in-ROM policy the array is swept once per concurrent
        # stream, so the engaged bytes are that many array-fulls, not one.
        sweeps = row.get("rom_sweeps_per_step") or 1.0
        check(
            row["engaged_weight_bytes"]
            <= row["stored_weight_bytes"] * sweeps * (1 + 1e-9),
            f"engaged bytes exceed {sweeps:g} array sweeps {key}",
        )
        if row["family"] == "rom":
            # Check the property, not the formula.  Restating the model's
            # arithmetic here would make this a copy that can drift from it --
            # which is exactly how the policy list came apart.
            policy = row["weight_amortization"]
            batch = row["batch_size"]
            if policy == "batched":
                check(sweeps == 1, f"batched must sweep once {key}")
            elif policy == "per_stream":
                check(
                    sweeps == batch,
                    f"per_stream must sweep once per stream {key}",
                )
            elif policy == "per_region":
                # Disjoint regions run together, so the sweep depth is the
                # busiest region's queue: never below one, never worse than
                # every token landing on the same region.
                check(
                    1.0 - 1e-9 <= sweeps <= batch + 1e-9,
                    f"per_region sweep depth outside [1, batch] {key}",
                )
            else:
                check(False, f"unknown amortisation policy {policy!r} {key}")
        check(
            row["resident_kv_bytes"] <= row["kv_capacity_bytes"] + 1.0
            or row["kv_store"] == "hbm",
            f"resident KV exceeds capacity on a feasible point {key}",
        )
        check(row["power_w"] > 0, f"non-positive power {key}")
        check(
            row["thermal_scale"] >= 1.0 - 1e-12,
            f"thermal scale below one {key}",
        )
        fractions = row["area_fractions"]
        check(
            close(sum(fractions.values()), 1.0, tol=1e-9),
            f"area fractions do not sum to one {key}",
        )
        check(
            all(value >= -1e-12 for value in fractions.values()),
            f"negative area fraction {key}",
        )
        if row["family"] == "rom":
            check(
                row["rom_full_array_sweep_time_s"] is not None,
                f"ROM point without a sweep floor {key}",
            )
            check(
                components["weight_read"]
                <= row["rom_full_array_sweep_time_s"] * (1 + 1e-9),
                f"ROM weight time above the full-array sweep floor {key}",
            )
            check(
                components["weight_read"]
                >= row["rom_full_array_sweep_time_s"] * (1 - 1e-9),
                f"ROM weight time below the full-array sweep floor {key}",
            )

    for row in result["comparisons"]:
        checks += 1
        if row["rom_feasible"] and row["iso_area_gpu_feasible"]:
            if not close(
                row["per_user_speed_ratio"],
                row["rom_per_user_tokens_s"] / row["iso_area_gpu_per_user_tokens_s"],
            ):
                errors.append(f"speed-ratio identity {row['rom_design']}")

    expected_points = 0
    for design in result["designs"]:
        expected_points += len(BATCHES)
    check(
        len(result["points"]) == expected_points,
        f"point matrix incomplete: {len(result['points'])} != {expected_points}",
    )
    check(bool(result["designs"]), "study produced no designs")
    check(
        all(row["silicon_area_mm2"] > 0 for row in result["points"]),
        "a point has no stated silicon area",
    )
    return {
        "status": "pass" if not errors else "fail",
        "checks_evaluated": checks,
        "errors": errors,
        "scope": [
            "Generated arithmetic identities, area-accounting identities and the "
            "ROM full-array sweep floor only.",
            "A passing audit is not evidence for ROM macro timing, array read "
            "bandwidth at a leading node, NoC timing, package, power delivery, "
            "yield, or model accuracy.",
            "The two validation gates are reported separately and are the only "
            "checks against a shipping part.",
        ],
    }


# --------------------------------------------------------------------------
# anchors
# --------------------------------------------------------------------------


def run_anchors(technology: Technology) -> dict[str, Any]:
    model = ModelProfile.load(ANCHOR_MODEL_PATH)
    hc1 = taalas_hc1_anchor(technology, model)
    a100 = a100_weight_bound_anchor(technology, model)
    sensitivity = []
    for bits in (3.0, 3.5, 4.0, 5.0, 6.0):
        check = taalas_hc1_anchor(technology, model, weight_bits_per_parameter=bits)
        sensitivity.append(
            {
                "weight_bits_per_parameter": bits,
                "modelled_tokens_s": check.modelled_value,
                "ratio_to_published": check.ratio,
                "binding_constraint": check.detail["binding_constraint"],
            }
        )
    context_sensitivity = []
    for context in (1024, 1536, 2048):
        check = taalas_hc1_anchor(technology, model, context_tokens=context)
        context_sensitivity.append(
            {
                "context_tokens": context,
                "modelled_tokens_s": check.modelled_value,
                "ratio_to_published": check.ratio,
                "binding_constraint": check.detail["binding_constraint"],
            }
        )
    return {
        "taalas_hc1": hc1.to_dict(),
        "a100_weight_bound": a100.to_dict(),
        "taalas_hc1_weight_bits_sensitivity": sensitivity,
        "taalas_hc1_context_sensitivity": context_sensitivity,
        "gate_policy": (
            "The Taalas HC1 gate is evaluated with the achievable derates because "
            "17,000 tok/s is a product figure. The A100 gate is evaluated on the "
            "ideal roofline with every derate at 1.0 because it is pure arithmetic: "
            "published HBM bandwidth divided by checkpoint bytes."
        ),
    }


# --------------------------------------------------------------------------
# rendering
# --------------------------------------------------------------------------


def _fmt(value: float | None, spec: str = ",.1f") -> str:
    if value is None or not math.isfinite(value):
        return "—"
    return format(value, spec)


def _fmt_ratio(value: float | None) -> str:
    return "—" if value is None or not math.isfinite(value) else f"{value:.2f}x"


def _fmt_us(value: float | None) -> str:
    if value is None or not math.isfinite(value):
        return "—"
    return f"{value * 1e6:,.2f}"


def _fmt_area(value: float | None) -> str:
    return "—" if value is None else f"{value:,.0f}"


def render_report(result: dict[str, Any], anchors: dict[str, Any]) -> str:
    study_id = result["study_id"]
    derivations = result["technology_derivations"]
    node = derivations["node"]
    lines: list[str] = [
        f"# Area-constrained roofline: {study_id}",
        "",
        f"> {result['comparison_contract']}",
        "",
        "Every figure below is produced by `src/opentallas/roofline.py` from",
        "`configs/hardware/technology.json` and the released model profiles. Nothing",
        "here is hand-computed. Silicon area is the primary input; capacity,",
        "bandwidth and compute roof are derived from it.",
        "",
        "## What the model says",
        "",
        *(
            f"{index}. {item}"
            for index, item in enumerate(_findings(result), 1)
        ),
        "",
        "## The overlap and serialisation rule",
        "",
        "```",
        "t_memory  = t_weight + t_kv        weights and KV share one memory system",
        "t_memory  = max(t_weight, t_kv)    weights and KV are separate arrays",
        "t_service = max(t_memory, t_compute)",
        "t_token   = t_service / stage_balance + t_link",
        "t_token  *= thermal_scale",
        "```",
        "",
        "Compute overlaps memory. Weight and KV traffic **add** on a GPU because they",
        "contend for the same HBM channels, and **overlap** on a ROM part because the",
        "mask ROM and the KV store are physically separate arrays -- that single rule",
        "is most of the architectural difference and it is stated rather than hidden",
        "in an efficiency factor. Hop and collective latency is **added** to the",
        "critical path at every batch size, because decode is sequential across",
        "layers and a pipelined array supplies no parallelism at batch 1. Per-user",
        "latency is the full serial traversal, so `aggregate = batch x per-user rate`",
        "holds by construction.",
        "",
        "## Validation gates",
        "",
    ]

    hc1 = anchors["taalas_hc1"]
    a100 = anchors["a100_weight_bound"]
    requirements = hc1["detail"]["back_derived_requirements"]
    lines.extend(
        [
            "| Gate | Published | Modelled | Ratio | Tolerance | Result |",
            "|---|---:|---:|---:|---:|---|",
            f"| Taalas HC1, Llama-3.1-8B on {_fmt_area(hc1['detail']['die_area_mm2'])} mm2 at "
            f"{hc1['detail']['node']}, per user | {_fmt(hc1['published_value'])} tok/s | "
            f"{_fmt(hc1['modelled_value'])} tok/s | {_fmt_ratio(hc1['ratio'])} | "
            f"within {hc1['tolerance']:.0f}x | {'PASS' if hc1['passed'] else 'FAIL'} |",
            f"| A100 80GB weight-bound, Llama-3.1-8B FP8 batch 1 on "
            f"{_fmt_area(a100['detail']['die_area_mm2'])} mm2 | "
            f"{_fmt(a100['published_value'],',.2f')} tok/s | "
            f"{_fmt(a100['modelled_value'],',.2f')} tok/s | "
            f"{_fmt_ratio(a100['ratio'])} | within {a100['tolerance']*100:.0f}% | "
            f"{'PASS' if a100['passed'] else 'FAIL'} |",
            "",
            f"HC1 binds on `{hc1['detail']['binding_constraint']}`. Its component times are "
            + ", ".join(
                f"{name} {_fmt_us(value)} us"
                for name, value in hc1["detail"]["component_times_s"].items()
            )
            + ".",
            "",
            "The model **under**-predicts the shipping part by "
            f"{1.0 / hc1['ratio']:.2f}x. Rather than tune the densities until the anchor",
            "is hit, the gate back-derives what each input would have to be for the",
            "model to land exactly on 17,000 tok/s:",
            "",
            "| Derived input | This model | Required by the shipping part | Shortfall |",
            "|---|---:|---:|---:|",
            f"| ROM read bandwidth density (B/s/mm2) | "
            f"{requirements['derived_rom_read_bandwidth_density_bytes_s_mm2']:.3e} | "
            f"{requirements['required_rom_read_bandwidth_density_bytes_s_mm2']:.3e} | "
            f"{requirements['rom_density_shortfall_x']:.2f}x |",
            f"| Compute density (ops/s/mm2) | "
            f"{requirements['derived_compute_density_ops_s_mm2']:.3e} | "
            f"{requirements['required_compute_density_ops_s_mm2']:.3e} | "
            f"{requirements['compute_density_shortfall_x']:.2f}x |",
            "",
            "The compute density derived from A100's published dense roofs and die",
            "area is within "
            f"{abs(requirements['compute_density_shortfall_x'] - 1) * 100:.1f}% of what the "
            "shipping part must have. The ROM read-bandwidth density derived from a",
            "28 nm simulated ROM-CIM macro is the input that is short, and the",
            "required value is still below the SRAM read-bandwidth density derived",
            f"from Cerebras WSE-2 ({derivations['sram_read_bytes_s_per_mm2']['value']:.3e} "
            "B/s/mm2), so it is physically unremarkable. That is a falsifiable",
            "statement about one technology input, which is what a gate is for.",
            "",
            "### Anchor sensitivity",
            "",
            "| Stored bits/parameter | Modelled tok/s | Ratio | Binds on |",
            "|---:|---:|---:|---|",
        ]
    )
    for row in anchors["taalas_hc1_weight_bits_sensitivity"]:
        lines.append(
            f"| {row['weight_bits_per_parameter']:.1f} | "
            f"{_fmt(row['modelled_tokens_s'])} | {_fmt_ratio(row['ratio_to_published'])} | "
            f"{row['binding_constraint']} |"
        )
    lines.extend(
        [
            "",
            "| Anchor context | Modelled tok/s | Ratio | Binds on |",
            "|---:|---:|---:|---|",
        ]
    )
    for row in anchors["taalas_hc1_context_sensitivity"]:
        lines.append(
            f"| {row['context_tokens']:,} | {_fmt(row['modelled_tokens_s'])} | "
            f"{_fmt_ratio(row['ratio_to_published'])} | {row['binding_constraint']} |"
        )

    lines.extend(
        [
            "",
            f"## Derived technology at {node}",
            "",
            "These are outputs of the graded primitives, not inputs.",
            "",
            "| Quantity | Value | Grade |",
            "|---|---:|---|",
            f"| SRAM capacity density | "
            f"{derivations['sram_capacity_bits_per_mm2']['value'] / 8e6:,.3f} MB/mm2 | "
            f"{derivations['sram_capacity_bits_per_mm2']['grade']} |",
            f"| ROM capacity density | "
            f"{derivations['rom_capacity_bits_per_mm2']['value'] / 8e6:,.3f} MB/mm2 | "
            f"{derivations['rom_capacity_bits_per_mm2']['grade']} |",
            f"| ROM read bandwidth density | "
            f"{derivations['rom_read_bytes_s_per_mm2']['value'] / 1e9:,.1f} GB/s/mm2 | "
            f"{derivations['rom_read_bytes_s_per_mm2']['grade']} |",
            f"| SRAM read bandwidth density | "
            f"{derivations['sram_read_bytes_s_per_mm2']['value'] / 1e9:,.1f} GB/s/mm2 | "
            f"{derivations['sram_read_bytes_s_per_mm2']['grade']} |",
        ]
    )
    for fmt, entry in derivations["compute_ops_s_per_mm2"].items():
        lines.append(
            f"| Compute density, {fmt} | {entry['value'] / 1e12:,.3f} Tops/s/mm2 | "
            f"{entry['grade']} |"
        )
    lines.extend(
        [
            f"| ROM full-array sweep time | "
            f"{derivations['rom_full_array_sweep_time_s'] * 1e6:,.1f} us | derived |",
            f"| ROM per-token ceiling from that sweep | "
            f"{derivations['rom_full_array_sweep_ceiling_tokens_s']:,.0f} tok/s | derived |",
            f"| ROM per-token ceiling before the read derate | "
            f"{derivations['rom_full_array_sweep_ceiling_tokens_s_before_derate']:,.0f} "
            "tok/s | derived |",
            "",
            derivations["rom_sweep_note"],
            "",
            "## Models and their work",
            "",
            "| Model | Context | Params | Checkpoint | Native bits/param | KV read/token | "
            "KV/user | W:KV at B=1 |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for summary in result["model_summaries"]:
        lines.append(
            f"| {summary['model']} | {summary['context_tokens']:,} | "
            f"{summary['total_parameters'] / 1e9:,.0f} B | "
            f"{summary['checkpoint_bytes'] / 1e9:,.1f} GB | "
            f"{summary['native_bits_per_parameter']:.2f} | "
            f"{summary['kv_read_bytes_per_user_token'] / 1e9:,.3f} GB | "
            f"{summary['kv_storage_bytes_per_user'] / 1e9:,.3f} GB | "
            f"{summary['weight_to_kv_read_ratio_b1']:,.1f} |"
        )

    lines.extend(
        [
            "",
            "## Iso-area comparison",
            "",
            "Two ROM designs per operating point -- the **fastest** and the",
            "**smallest silicon that serves the point at all** -- each against the GPU",
            "cluster of the closest equal silicon area. **The area is stated on both",
            "sides.** Where one row appears, the two coincide.",
            "",
            "| Model | B | Pick | ROM design | ROM mm2 | ROM user tok/s | "
            "ROM aggregate tok/s | ROM binds on | GPU | GPU mm2 | Area ratio | "
            "GPU user tok/s | GPU aggregate tok/s | GPU binds on | Per-user ratio | "
            "Aggregate ratio |",
            "|---|---:|---|---|---:|---:|---:|---|---|---:|---:|---:|---:|---|---:|---:|",
        ]
    )
    best_rows = _best_comparisons(result)
    for row in best_rows:
        lines.append(
            f"| {row['model']} | {row['batch_size']} | {row.get('selection', '—')} | "
            f"{row['rom_design']} | "
            f"{_fmt_area(row['rom_silicon_area_mm2'])} | "
            f"{_fmt(row['rom_per_user_tokens_s']) if row['rom_feasible'] else 'infeasible'} | "
            f"{_fmt(row['rom_aggregate_tokens_s']) if row['rom_feasible'] else '—'} | "
            f"{row['rom_binding_constraint']} | {row['iso_area_gpu_design']} | "
            f"{_fmt_area(row['iso_area_gpu_silicon_area_mm2'])} | "
            f"{_fmt_ratio(row['iso_area_ratio'])} | "
            f"{_fmt(row['iso_area_gpu_per_user_tokens_s']) if row['iso_area_gpu_feasible'] else 'infeasible'} | "
            f"{_fmt(row['iso_area_gpu_aggregate_tokens_s']) if row['iso_area_gpu_feasible'] else '—'} | "
            f"{row['iso_area_gpu_binding_constraint']} | "
            f"{_fmt_ratio(row['per_user_speed_ratio'])} | "
            f"{_fmt_ratio(row['aggregate_speed_ratio'])} |"
        )

    lines.extend(
        [
            "",
            "## Array or wafer: the crossover, reported rather than assumed",
            "",
            "`Array viable to` is the per-user rate at which the topology's hops alone",
            "consume 10% of the token budget; `hard ceiling` is the rate at which they",
            "consume all of it. Below the first number the interconnect is a design",
            "cost; above the second the topology cannot deliver the rate at all.",
            "",
            "| Design | Model | Devices | Parallelism | Link | Hops/token | "
            "Link latency/token | Viable to (10% budget) | Hard ceiling |",
            "|---|---|---:|---|---|---:|---:|---:|---:|",
        ]
    )
    seen_crossovers: set[str] = set()
    for row in result["latency_crossovers"]:
        if row["design"] in seen_crossovers:
            continue
        seen_crossovers.add(row["design"])
        lines.append(
            f"| {row['design']} | {row['model']} | {row['device_count']} | "
            f"{row['parallelism']} | {row['link']} | {row['hop_events_per_token']:,.0f} | "
            f"{_fmt_us(row['link_latency_s_per_token'])} us | "
            f"{_fmt(row['viable_tokens_s'])} tok/s | "
            f"{_fmt(row['hard_ceiling_tokens_s'])} tok/s |"
        )

    lines.extend(
        [
            "",
            "## Topology choice at each operating point",
            "",
            "Selection rule: the smallest silicon area within 5% of the best",
            "per-user rate at that point, so a topology cannot win by simply being",
            "given more silicon.",
            "",
            "| Model | B | Winner on rate | Winner per mm2 | Best design | "
            "Best mm2 | Best user tok/s | tok/s per mm2 | Best array tok/s (mm2) | "
            "Best wafer tok/s (mm2) | Wafer/array | Binds on |",
            "|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|---|",
        ]
    )
    for row in result["topology_choices"]:
        lines.append(
            f"| {row['model']} | {row['batch_size']} | {row['array_or_wafer']} | "
            f"{row.get('array_or_wafer_per_mm2') or '—'} | "
            f"{row.get('best_design') or '—'} | "
            f"{_fmt_area(row.get('best_silicon_area_mm2'))} | "
            f"{_fmt(row.get('best_per_user_tokens_s'))} | "
            f"{_fmt(row.get('best_tokens_s_per_mm2'), ',.3f')} | "
            f"{_fmt(row.get('array_best_per_user_tokens_s'))} "
            f"({_fmt_area(row.get('array_best_silicon_area_mm2'))}) | "
            f"{_fmt(row.get('wafer_best_per_user_tokens_s'))} "
            f"({_fmt_area(row.get('wafer_best_silicon_area_mm2'))}) | "
            f"{_fmt_ratio(row.get('wafer_over_array_ratio'))} | "
            f"{row.get('best_binding_constraint') or '—'} |"
        )

    lines.extend(
        [
            "",
            "## The batch-amortisation fork, reported rather than resolved",
            "",
            "`docs/ISO_AREA_COMPARISON_AND_THE_TAALAS_ANCHOR.md` names an open",
            "question the anchor cannot settle. If a ROM cell both stores its bits",
            "and performs the multiply for them -- compute-in-ROM, as Taalas",
            "describes HC1 -- then a second concurrent stream needs a second pass",
            "through the fabric, and **aggregate per-die throughput equals per-user",
            "throughput at every batch**. If instead the ROM is storage feeding a",
            "separate MAC array, one sweep serves the whole batch exactly as one HBM",
            "fetch does on a GPU. The two are *identical at batch 1*, which is",
            "precisely why the published 16,960 tok/s figure cannot distinguish",
            "them, and why it must not be used to justify a high-batch claim.",
            "",
            "Every other table in this report uses the batched (ROM-as-storage)",
            "machine; `-perstream` is compute-in-ROM with a global activation "
            "broadcast and `-perregion` gives each expert region its own port",
            "variant.",
            "",
            "| Model | B | Batched user tok/s | Batched aggregate | Per-stream user tok/s | "
            "Per-stream aggregate | Aggregate penalty | Batched binds on | "
            "Per-stream binds on |",
            "|---|---:|---:|---:|---:|---:|---:|---|---|",
        ]
    )
    for row in result["amortization_fork"]:
        lines.append(
            f"| {row['model']} | {row['batch_size']} | "
            f"{_fmt(row['batched_per_user_tokens_s'])} | "
            f"{_fmt(row['batched_aggregate_tokens_s'])} | "
            f"{_fmt(row['per_stream_per_user_tokens_s'])} | "
            f"{_fmt(row['per_stream_aggregate_tokens_s'])} | "
            f"{_fmt_ratio(row.get('per_stream_aggregate_penalty_x'))} | "
            f"{row['batched_binding_constraint'] or '—'} | "
            f"{row['per_stream_binding_constraint'] or '—'} |"
        )

    lines.extend(
        [
            "",
            "## Sparse-MoE engagement on a ROM machine",
            "",
            "Expected distinct experts touched by a batch is `1 - (1 - k/N)^B`, so the",
            "bytes a step engages grow with batch while the ROM full-array sweep time",
            "does not: an unselected expert's read ports cannot be borrowed, and a",
            "selected one is read once however many batch members chose it. **MoE",
            "sparsity on a ROM machine therefore converts into aggregate throughput,",
            "not into lower per-token latency** -- which is the opposite of what it does",
            "on an HBM machine, where bandwidth is global and sparsity directly",
            "reduces the bytes fetched.",
            "",
            "| Model | B | Expert coverage | Engaged weight bytes | Engaged fraction | "
            "Effective ROM read | Peak ROM read | Per-user tok/s | Aggregate tok/s |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in _engagement_rows(result):
        lines.append(
            f"| {row['model']} | {row['batch_size']} | "
            f"{row['expert_coverage'] * 100:,.2f}% | "
            f"{row['engaged_weight_bytes'] / 1e9:,.1f} GB | "
            f"{row['engaged_weight_fraction'] * 100:,.2f}% | "
            f"{row['effective_weight_read_bytes_s'] / 1e12:,.2f} TB/s | "
            f"{row['peak_weight_read_bytes_s'] / 1e12:,.2f} TB/s | "
            f"{_fmt(row['per_user_tokens_s'])} | {_fmt(row['aggregate_tokens_s'])} |"
        )

    lines.extend(
        [
            "",
            "## Binding constraint census",
            "",
            "| Family | Binding constraint | Points |",
            "|---|---|---:|",
        ]
    )
    census: dict[tuple[str, str], int] = {}
    for row in result["points"]:
        key = (row["family"], row["binding_constraint"] if row["feasible"] else "infeasible")
        census[key] = census.get(key, 0) + 1
    for (family, binding), count in sorted(census.items()):
        lines.append(f"| {family} | {binding} | {count} |")

    infeasible: dict[tuple[str, str], int] = {}
    for row in result["points"]:
        if row["feasible"]:
            continue
        for reason in row["reasons"]:
            infeasible[(row["family"], reason.split(":", 1)[0])] = (
                infeasible.get((row["family"], reason.split(":", 1)[0]), 0) + 1
            )
    if infeasible:
        lines.extend(
            [
                "",
                "Why the infeasible points are infeasible:",
                "",
                "| Family | Reason class | Points |",
                "|---|---|---:|",
            ]
        )
        for (family, reason), count in sorted(infeasible.items()):
            lines.append(f"| {family} | {reason} | {count} |")

    audit = result["consistency_audit"]
    lines.extend(
        [
            "",
            "## Mechanical consistency audit",
            "",
            f"**{audit['status'].upper()}** over {audit['checks_evaluated']:,} checks.",
            "",
        ]
    )
    if audit["errors"]:
        lines.extend(f"- ERROR: {message}" for message in audit["errors"][:50])
        lines.append("")
    lines.extend(f"- {item}" for item in audit["scope"])

    graded = result["graded_inputs"]
    lines.extend(
        [
            "",
            "## Evidence ledger",
            "",
            "| Grade | Inputs |",
            "|---|---:|",
        ]
    )
    for grade in ("measured", "published", "derived", "assumed"):
        lines.append(f"| {grade} | {len(graded.get(grade, []))} |")
    lines.extend(
        [
            "",
            "Every `assumed` input, in full, because an ungraded assumption is the",
            "failure mode this program exists to prevent:",
            "",
        ]
    )
    lines.extend(f"- `{path}`" for path in graded.get("assumed", []))

    lines.extend(
        [
            "",
            "## Interpretation boundary",
            "",
            "- No mask-ROM macro has been fabricated at a leading node for this",
            "  program. The ROM capacity density rests on an assumed cell-area ratio",
            "  against a published SRAM bitcell, and the ROM read bandwidth density on",
            "  a *simulated* 28 nm ROM-CIM macro scaled by published bitcell areas.",
            "  Both are named in the evidence ledger above.",
            "- Compute density is charged at a published GPU's whole-die roof per mm2,",
            "  applied to a modelled design's compute-only area. Newer parts are",
            "  denser than the A100 anchor, so this understates a 2026 design.",
            "- Hop latencies are floors. They ignore switch contention, per-hop",
            "  payload queueing beyond the modelled serialisation, and pipeline fill",
            "  at batch 1. Each of those makes an array worse, never better, so the",
            "  reported array crossovers are upper bounds.",
            "- Power is a dynamic-activity lower bound: leakage, clock distribution",
            "  and idle logic are not modelled, so `thermal` binding is under-reported.",
            "- Prefill, speculative decoding and cost are out of scope for this model.",
            "",
        ]
    )
    return "\n".join(lines)


def _pick_best(rows: list[dict[str, Any]], rate_key: str, area_key: str):
    """Smallest silicon area within 5% of the best per-user rate.

    Selecting on rate alone hands an 8B model a 46,225 mm2 wafer to buy the last
    few percent of a rate it already had on four reticle chips.  The rule is
    stated here and applied everywhere the report says "best".
    """

    feasible = [row for row in rows if row.get(rate_key)]
    if not feasible:
        return rows[0] if rows else None
    best_rate = max(row[rate_key] for row in feasible)
    threshold = best_rate * (1.0 - BEST_DESIGN_TOLERANCE)
    within = [row for row in feasible if row[rate_key] >= threshold]
    return min(within, key=lambda row: (row[area_key], -row[rate_key]))


def _findings(result: dict[str, Any]) -> list[str]:
    """Headline results, every number pulled from the study rather than typed."""

    derivations = result["technology_derivations"]
    node = derivations["node"]
    findings: list[str] = [
        "**The ROM path has a hard per-token ceiling that is a technology "
        "constant, not a design choice.** The full-array sweep time is the ROM "
        "capacity density divided by its read-bandwidth density, so it does not "
        "depend on model size, batch, or expert coverage: "
        f"{derivations['rom_full_array_sweep_time_s'] * 1e6:,.1f} us, or "
        f"{derivations['rom_full_array_sweep_ceiling_tokens_s']:,.0f} tok/s per user. "
        "Under this derivation both densities scale with the same published "
        "bitcell-area ratio, so that ceiling is the same at every node: process "
        "scaling buys a ROM design capacity, not per-token speed.",
    ]

    batch_one = [
        row
        for row in result["comparisons"]
        if row["batch_size"] == 1
        and row["rom_feasible"]
        and row["iso_area_gpu_feasible"]
        and row["per_user_speed_ratio"] is not None
    ]
    if batch_one:
        top = max(batch_one, key=lambda row: row["per_user_speed_ratio"])
        findings.append(
            "**The ROM advantage is a batch-1, per-user advantage, and it is "
            f"large.** At equal area the best batch-1 point is {top['model']} on "
            f"{top['rom_silicon_area_mm2']:,.0f} mm2 of ROM silicon at "
            f"{top['rom_per_user_tokens_s']:,.0f} tok/s per user, against "
            f"{top['iso_area_gpu_silicon_area_mm2']:,.0f} mm2 of "
            f"{top['iso_area_gpu_design'].split('/')[-1]} at "
            f"{top['iso_area_gpu_per_user_tokens_s']:,.0f} tok/s: "
            f"**{top['per_user_speed_ratio']:,.0f}x**. Both sides bind on "
            f"`{top['rom_binding_constraint']}`, and the whole difference is that "
            "one reads its weights from HBM and the other from an on-die array."
            if top["rom_binding_constraint"]
            == top["iso_area_gpu_binding_constraint"]
            else f"**{top['per_user_speed_ratio']:,.0f}x**. The GPU binds on "
            f"`{top['iso_area_gpu_binding_constraint']}` and the ROM part on "
            f"`{top['rom_binding_constraint']}`."
        )

    high_batch = [
        row
        for row in result["comparisons"]
        if row["batch_size"] == max(BATCHES)
        and row["rom_feasible"]
        and row["iso_area_gpu_feasible"]
        and row["aggregate_speed_ratio"] is not None
    ]
    if high_batch:
        worst = min(high_batch, key=lambda row: row["aggregate_speed_ratio"])
        best = max(high_batch, key=lambda row: row["aggregate_speed_ratio"])
        findings.append(
            "**The advantage erodes with batch, and the erosion is a KV effect.** "
            f"At batch {max(BATCHES)} the aggregate ratio at equal area spans "
            f"{worst['aggregate_speed_ratio']:.2f}x ({worst['model']}, ROM binding on "
            f"`{worst['rom_binding_constraint']}`) to "
            f"{best['aggregate_speed_ratio']:.2f}x ({best['model']}, ROM binding on "
            f"`{best['rom_binding_constraint']}`). Weight traffic is what ROM "
            "removes; KV traffic it does not, and KV traffic is what grows with "
            "batch."
        )

    engagement = _engagement_rows(result)
    for low in [
        row
        for row in engagement
        if row["expert_coverage"] < 0.1 and row["batch_size"] == 1
    ]:
        high = next(
            (
                row
                for row in engagement
                if row["model"] == low["model"]
                and row["batch_size"] == max(BATCHES)
            ),
            None,
        )
        if high is None:
            continue
        findings.append(
            "**Sparse MoE buys aggregate throughput on a ROM machine, not "
            f"latency.** {low['model']} engages "
            f"{low['engaged_weight_fraction'] * 100:.1f}% of its ROM array at batch 1 "
            f"and {high['engaged_weight_fraction'] * 100:.1f}% at batch "
            f"{high['batch_size']}, while the weight-read time is identical at both. "
            f"Aggregate throughput rises from {low['aggregate_tokens_s']:,.0f} to "
            f"{high['aggregate_tokens_s']:,.0f} tok/s on the same machine. An "
            "unselected expert's read ports cannot be borrowed, so its idle "
            "bandwidth is only recovered by giving the sweep more users."
        )
        break

    wafer_wins = sum(
        1
        for row in result["topology_choices"]
        if row.get("array_or_wafer") == "wafer"
    )
    array_wins = sum(
        1
        for row in result["topology_choices"]
        if row.get("array_or_wafer") == "array"
    )
    tensor_nvlink = [
        row
        for row in result["latency_crossovers"]
        if row["parallelism"] == "tensor" and row["link"] == "nvlink"
    ]
    tensor_wafer = [
        row
        for row in result["latency_crossovers"]
        if row["parallelism"] == "tensor" and row["link"] == "on_wafer"
    ]
    wafer_per_mm2 = sum(
        1
        for row in result["topology_choices"]
        if row.get("array_or_wafer_per_mm2") == "wafer"
    )
    array_per_mm2 = sum(
        1
        for row in result["topology_choices"]
        if row.get("array_or_wafer_per_mm2") == "array"
    )
    if tensor_nvlink and tensor_wafer:
        findings.append(
            "**Tensor parallelism is a latency argument for wafer-scale, and it is "
            "the sharpest one.** Two all-reduces per layer per token cost up to "
            f"{max(row['link_latency_s_per_token'] for row in tensor_nvlink) * 1e6:,.0f} us "
            "over NVLink, capping per-user decode at "
            f"{min(row['hard_ceiling_tokens_s'] for row in tensor_nvlink):,.0f} tok/s "
            "before any arithmetic happens; the same collectives on-wafer cost at "
            f"most {max(row['link_latency_s_per_token'] for row in tensor_wafer) * 1e6:,.1f} us "
            "and cap it at "
            f"{min(row['hard_ceiling_tokens_s'] for row in tensor_wafer):,.0f} tok/s."
        )
    findings.append(
        "**Which topology wins depends entirely on what is being maximised, and "
        "the study reports both rather than choosing.** On per-user rate at equal "
        f"area a wafer wins {wafer_wins} of {len(result['topology_choices'])} "
        f"operating points and an array {array_wins}; on tokens per second per "
        f"square millimetre the same points go {array_per_mm2} to the array and "
        f"{wafer_per_mm2} to the wafer. A wafer is not faster per unit silicon -- "
        "it is faster because it is more silicon, plus a hop latency an array "
        "cannot match."
    )

    feasible = sum(1 for row in result["points"] if row["feasible"])
    kv_bound = sum(
        1
        for row in result["points"]
        if row["feasible"] and row["binding_constraint"] == "kv_read"
    )
    findings.append(
        "**A wafer has less die edge per unit area than the same area of separate "
        "dies, and that is an argument against it.** Perimeter grows as the square "
        "root of area, so HBM beachfront -- and therefore KV bandwidth -- does not "
        "scale with wafer area the way compute and ROM capacity do. This model "
        "charges both sides the same edge utilisation a shipping GPU achieves, and "
        f"the consequence shows up wherever a design binds on `kv_read`: {kv_bound} "
        f"of {feasible} feasible points."
    )

    fork = [
        row
        for row in result.get("amortization_fork", [])
        if row.get("per_stream_aggregate_penalty_x") is not None
        and row["batch_size"] == max(BATCHES)
    ]
    if fork:
        worst = max(fork, key=lambda row: row["per_stream_aggregate_penalty_x"])
        findings.append(
            "**The largest open question is not in this model's inputs but in the "
            "architecture, and the anchor cannot settle it.** If a ROM cell both "
            "stores and multiplies, each concurrent stream needs its own pass and "
            "aggregate per-die throughput never exceeds the per-user rate. At batch "
            f"{max(BATCHES)} that costs up to "
            f"{worst['per_stream_aggregate_penalty_x']:,.1f}x of aggregate "
            f"throughput ({worst['model']}). The machines are identical at batch 1, "
            "which is where the published anchor sits, so no amount of validation "
            "against it resolves the fork."
        )
        regional = [
            row
            for row in fork
            if row.get("per_region_aggregate_penalty_x") is not None
        ]
        if regional:
            best = min(regional, key=lambda row: row["per_region_aggregate_penalty_x"])
            findings.append(
                "**A third machine sits between them, and for a sparse model it "
                "recovers most of what compute-in-ROM gives up.** Give each expert "
                "region its own activation port and two tokens selecting disjoint "
                "experts drive disjoint regions at the same time; only the tokens "
                "landing on one region serialise. At batch "
                f"{max(BATCHES)} that closes the gap to "
                f"{best['per_region_aggregate_penalty_x']:,.2f}x of the amortising "
                f"machine ({best['model']}), against "
                f"{worst['per_stream_aggregate_penalty_x']:,.1f}x for a global "
                "activation broadcast. A dense model has one region, so it gains "
                "nothing — the disjointness is what sparsity buys."
            )

    findings.append(
        "**Every number here is conditional on the assumed inputs listed in the "
        "evidence ledger below.** The ROM cell-area ratio and the ROM read "
        "bandwidth density are the two that move the answer most, and neither has "
        f"been measured at {node}."
    )
    return findings


def _engagement_rows(result: dict[str, Any]) -> list[dict[str, Any]]:
    """One ROM row per (model, batch) chosen consistently, to expose engagement.

    The design is held fixed across the batch sweep -- the smallest feasible
    HBM-KV array at batch 1 -- so the table shows what the *batch* does rather
    than what a different machine does.
    """

    rows: list[dict[str, Any]] = []
    order = {name: index for index, (name, _, _) in enumerate(STUDY_MODELS)}
    for model_name in order:
        candidates = [
            row
            for row in result["points"]
            if row["model"] == model_name
            and row["family"] == "rom"
            and row["weight_amortization"] == "batched"
            and row["kv_store"] == "hbm"
            and row["batch_size"] == 1
            and row["feasible"]
        ]
        if not candidates:
            continue
        design = min(candidates, key=lambda row: row["silicon_area_mm2"])["design"]
        for row in result["points"]:
            if row["design"] == design and row["model"] == model_name:
                rows.append(row)
    return sorted(rows, key=lambda row: (order[row["model"]], row["batch_size"]))


def _best_comparisons(result: dict[str, Any]) -> list[dict[str, Any]]:
    """Two rows per (model, batch): the fastest ROM design and the smallest one.

    Reporting only the fastest lets a topology win by being handed more silicon;
    reporting only the smallest hides the rate a bigger machine actually buys.
    Both are emitted, each against its own equal-area GPU cluster, which is what
    "state the area on both sides" is for.
    """

    grouped: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for row in result["comparisons"]:
        grouped.setdefault((row["model"], row["batch_size"]), []).append(row)
    chosen: list[dict[str, Any]] = []
    for rows in grouped.values():
        feasible = [row for row in rows if row["rom_feasible"]]
        if not feasible:
            chosen.append({**rows[0], "selection": "no feasible ROM design"})
            continue
        fastest = max(feasible, key=lambda row: row["rom_per_user_tokens_s"])
        smallest = min(
            feasible,
            key=lambda row: (
                row["rom_silicon_area_mm2"],
                -row["rom_per_user_tokens_s"],
            ),
        )
        chosen.append({**fastest, "selection": "fastest"})
        if smallest["rom_design"] != fastest["rom_design"]:
            chosen.append({**smallest, "selection": "smallest silicon"})
    order = {name: index for index, (name, _, _) in enumerate(STUDY_MODELS)}
    return sorted(
        chosen,
        key=lambda row: (
            order[row["model"]],
            row["batch_size"],
            row.get("selection", ""),
        ),
    )


CSV_FIELDS = (
    "family",
    "design",
    "model",
    "context_tokens",
    "batch_size",
    "device_count",
    "topology_kind",
    "parallelism",
    "link",
    "node",
    "weight_store",
    "kv_store",
    "weight_amortization",
    "silicon_area_mm2",
    "silicon_area_mm2_per_device",
    "feasible",
    "per_user_tokens_s",
    "aggregate_tokens_s",
    "step_time_s",
    "binding_constraint",
    "power_w",
    "thermal_scale",
    "stored_weight_bytes",
    "engaged_weight_bytes",
    "engaged_weight_fraction",
    "expert_coverage",
    "resident_kv_bytes",
    "max_resident_users",
    "weight_to_kv_read_ratio",
    "execution_format",
    "hop_events_per_token",
    "rom_sweep_ceiling_tokens_s",
)


def render_csv(result: dict[str, Any]) -> str:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=CSV_FIELDS, lineterminator="\n")
    writer.writeheader()
    for row in result["points"]:
        writer.writerow({field: row.get(field) for field in CSV_FIELDS})
    return output.getvalue()


def run_all(
    output_root: Path = OUTPUT_ROOT, *, force: bool = False
) -> dict[str, dict[str, Any]]:
    technology = Technology.load(TECHNOLOGY_PATH)
    anchors = run_anchors(technology)
    results: dict[str, dict[str, Any]] = {}
    planned: list[tuple[Path, str]] = []
    for study_id in STUDIES:
        result = _simulate_study(study_id, technology)
        result["validation_gates"] = anchors
        results[study_id] = result
        destination = output_root / study_id
        planned.append(
            (
                destination / "analytical.json",
                json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n",
            )
        )
        planned.append((destination / "sweep.csv", render_csv(result)))
        planned.append(
            (
                destination / "REPORT.md",
                render_report(result, anchors).rstrip() + "\n",
            )
        )

    existing = [path for path, _ in planned if path.exists()]
    if existing and not force:
        raise SystemExit(
            "refusing to overwrite existing study artifacts without --force:\n  "
            + "\n  ".join(str(path) for path in existing)
        )
    for path, payload in planned:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(payload, encoding="utf-8", newline="")
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT_ROOT)
    parser.add_argument(
        "--force",
        action="store_true",
        help="overwrite existing artifacts under the output directory",
    )
    args = parser.parse_args(argv)
    results = run_all(args.output, force=args.force)
    for study_id, result in results.items():
        audit = result["consistency_audit"]
        print(
            f"{study_id}: {len(result['points'])} points, audit "
            f"{audit['status']} ({audit['checks_evaluated']} checks)"
        )
        print((args.output / study_id / "REPORT.md").resolve())
    gates = next(iter(results.values()))["validation_gates"]
    for name in ("taalas_hc1", "a100_weight_bound"):
        gate = gates[name]
        print(
            f"gate {name}: modelled {gate['modelled_value']:,.2f} vs published "
            f"{gate['published_value']:,.2f} ({gate['ratio']:.3f}x) "
            f"{'PASS' if gate['passed'] else 'FAIL'}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
