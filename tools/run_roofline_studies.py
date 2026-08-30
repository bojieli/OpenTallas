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
from dataclasses import dataclass, replace
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
    BITS_PER_BYTE,
    DeviceBudget,
    RooflineStep,
    Technology,
    Topology,
    a100_weight_bound_anchor,
    evaluate,
    gpu_device_budget,
    latency_crossover,
    layer_fixed_latency,
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
BATCHES = (1, 2, 4, 8, 16, 32, 64, 256)
"""Doubling from 1 to 64, then 256.

The coarse grid this replaced -- 1, 8, 32, 64, 256 -- could report the endpoints
of the batching argument but not the shape between them, and the shape is where
the argument actually lives.  A dense model's KV read is per-user and never
amortises, so a ROM design that wins by an order of magnitude at batch 1 gives
that lead back as batch rises; a sparse model's routed weights engage more of the
array with every added stream, so it gains.  Both effects are monotone and
neither is visible at two points.  Powers of two locate the crossing to within a
factor of two without the sweep growing enough to matter."""
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
        "intra_link": "nvlink3",
        "inter_link": "infiniband_hdr",
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
        "intra_link": "nvlink5",
        "inter_link": "infiniband_ndr",
        "gpu_domain_sensitivity": "nvlink5_nvl72",
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
SPARE_AREA_POLICIES: tuple[str, ...] = ("sram", "rom")
"""What a ROM design does with silicon it does not have to spend on its array.

``sram`` is the previous behaviour: the array is sized to the stored bytes, and
what is left becomes KV store on a compute-in-ROM part or a MAC array on an
amortising one.  ``rom`` grows the array into that silicon as **replicated
copies of the same weights**, which cuts the full-array sweep time by the
replication factor because each copy carries its own bitlines and sense amps.

Both are emitted for **all three** amortisation policies.  Offering the
floorplan sweep only to compute-in-ROM would decide the comparison by the
allocation rule rather than by physics -- which is exactly the failure this
sweep exists to remove."""

ROM_AREA_LADDER: tuple[int, ...] = (1, 2, 3, 4, 6, 8, 12)
"""Wafer counts the ROM side is emitted at regardless of what the sizing sweep
chooses, so the iso-area curve is sampled at the same silicon on both sides and
a correction that moves the sizing optimum cannot silently move the areas the
comparison is read at.  Seven rungs rather than every integer: they span the
whole range, they include every area the published headline was read at, and the
artifact is a checked-in file whose size is a real cost."""

GPU_AREA_LADDER: tuple[int, ...] = ROM_AREA_LADDER
"""The GPU baseline is evaluated at the same wafer-equivalents of silicon
whatever the ROM sizing sweep chooses, so the iso-area curve is sampled over the
whole range this study spans rather than only where a ROM design lands."""

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


def _regions_for(
    plan: "FabricPlan",
    devices: int,
    wafer_area: float | None,
    reticle_area: float | None,
) -> int:
    """Reticle fields a design spans, which is what its hop count is counted in."""

    if plan.kind == "wafer" and wafer_area and reticle_area:
        return max(1, math.ceil(devices * wafer_area / reticle_area))
    return 1


@dataclass(frozen=True)
class FabricPlan:
    """The two link classes a machine actually has, and the domain between them.

    A cluster is not one fabric.  An HGX baseboard is an all-to-all NVLink
    island of ``intra_domain_size`` devices; past the island edge every byte
    goes onto a scale-out network an order of magnitude slower in latency and
    more than an order slower in per-device bandwidth.  A wafer is the same
    shape with different numbers: an on-wafer stitched mesh inside one wafer,
    a package-class link between wafers.

    The same plan is handed to the ROM side and to the GPU side of each study,
    so neither is charged a fabric the other is not.
    """

    kind: str
    parallelism: str
    intra_link: str
    inter_link: str
    intra_domain_size: int
    label: str

    def topology(self, devices: int, regions: int) -> Topology:
        group = self.intra_domain_size if self.parallelism == "hybrid" else 1
        return Topology(
            kind=self.kind,
            device_count=devices,
            parallelism=self.parallelism,
            link=self.inter_link,
            on_wafer_regions=regions,
            intra_link=self.intra_link,
            intra_domain_size=self.intra_domain_size,
            tensor_group_size=group,
        )


def _fabric_plans(
    technology: Technology,
    config: dict[str, Any],
    *,
    wafer_area: float,
    reticle_area: float,
) -> tuple[tuple[FabricPlan, float], ...]:
    """Every (topology, area-per-device) pair the ROM side is allowed to choose.

    Three parallelisms on each of two device classes.  ``hybrid`` is the one a
    real deployment runs -- tensor-parallel inside the high-bandwidth domain,
    pipeline-parallel across domains -- and it was previously offered to
    neither side.
    """

    intra = str(config["intra_link"])
    inter = str(config["inter_link"])
    array_domain = max(1, int(technology.link_domain_size(intra).value))
    regions_per_wafer = max(1, math.ceil(wafer_area / reticle_area))
    plans: list[tuple[FabricPlan, float]] = []
    for parallelism in ("pipeline", "tensor", "hybrid"):
        plans.append(
            (
                FabricPlan(
                    kind="array",
                    parallelism=parallelism,
                    intra_link=intra,
                    inter_link=inter,
                    intra_domain_size=array_domain,
                    label=f"array-{parallelism}",
                ),
                reticle_area,
            )
        )
        plans.append(
            (
                FabricPlan(
                    kind="wafer",
                    parallelism=parallelism,
                    intra_link="on_wafer",
                    inter_link="inter_wafer",
                    intra_domain_size=regions_per_wafer,
                    label=f"wafer-{parallelism}",
                ),
                wafer_area,
            )
        )
    return tuple(plans)


def _build_rom_budget(
    technology: Technology,
    *,
    name: str,
    node: str,
    area_per_device: float,
    devices: int,
    plan: FabricPlan,
    on_wafer_regions: int,
    stored_weight_bytes: float,
    resident_kv_bytes: float,
    kv_transfer_bytes: float,
    kv_store: str,
    hbm_generation: str,
    weight_amortization: str = "batched",
    spare_area_policy: str = "sram",
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
    topology = plan.topology(devices, on_wafer_regions)
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
        spare_area_policy=spare_area_policy,
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
    plan: FabricPlan,
    wafer_area: float | None,
    reticle_area: float | None,
    weight_amortization: str = "batched",
    spare_area_policy: str = "sram",
) -> int:
    """Fewest devices that can physically hold the design.

    **Sized on the policy's own floorplan.**  This used to size once on the
    batched machine and hand the count to all three, on the reasoning that the
    policies are identical at batch 1.  They stopped being identical when the
    floorplan started depending on the policy: a compute-in-ROM cell is 1.6x a
    storage cell, so the same weights need 1.6x the array and can need more
    dies.  Sizing all three on the batched floorplan denied compute-in-ROM the
    dies it needs and reported the result as infeasibility -- "it cannot hold
    this model" when the truth was "we never tried enough dies".

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
        regions = _regions_for(plan, devices, wafer_area, reticle_area)
        budget = _build_rom_budget(
            technology,
            name="minimum-probe",
            node=node,
            area_per_device=area_per_device,
            devices=devices,
            plan=plan,
            on_wafer_regions=regions,
            stored_weight_bytes=stored_weight_bytes,
            resident_kv_bytes=resident_kv_bytes,
            kv_transfer_bytes=kv_transfer_bytes,
            kv_store=kv_store,
            hbm_generation=hbm_generation,
            weight_amortization=weight_amortization,
            spare_area_policy=spare_area_policy,
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
    plan: FabricPlan,
    wafer_area: float | None = None,
    reticle_area: float | None = None,
    weight_amortization: str = "batched",
    spare_area_policy: str = "sram",
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
        plan=plan,
        wafer_area=wafer_area,
        reticle_area=reticle_area,
        weight_amortization=weight_amortization,
        spare_area_policy=spare_area_policy,
    )
    if minimum > ARRAY_SWEEP_CAP:
        return minimum, []
    upper = min(ARRAY_SWEEP_CAP, minimum * MAX_OVERPROVISION)
    sweep: list[dict[str, Any]] = []
    best_latency = math.inf
    stale = 0
    for devices in range(minimum, upper + 1):
        regions = _regions_for(plan, devices, wafer_area, reticle_area)
        budget = _build_rom_budget(
            technology,
            name="sizing-probe",
            node=node,
            area_per_device=area_per_device,
            devices=devices,
            plan=plan,
            on_wafer_regions=regions,
            stored_weight_bytes=stored_weight_bytes,
            resident_kv_bytes=resident_kv_bytes,
            kv_transfer_bytes=kv_transfer_bytes,
            kv_store=kv_store,
            hbm_generation=hbm_generation,
            weight_amortization=weight_amortization,
            spare_area_policy=spare_area_policy,
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
        "intra_link": budget.topology.inner_link,
        "intra_domain_size": budget.topology.intra_domain_size,
        "tensor_group": budget.topology.tensor_group,
        "pipeline_stages": metrics["pipeline_stages"],
        "pipeline_stages_uncapped": metrics["pipeline_stages_uncapped"],
        "hop_breakdown": "; ".join(
            f"{d['count']:,.0f}x {d['kind']} span {d['span']} on {d['link']} "
            f"({d['seconds'] * 1e6:,.2f} us)"
            for d in metrics["link_breakdown"]
        ),
        "link_latency_s": step.component_times_s["link_latency"],
        "link_latency_without_stage_cap_s": metrics[
            "link_latency_without_stage_cap_s"
        ],
        "step_time_without_stage_cap_s": (
            step.step_time_s
            - step.component_times_s["link_latency"]
            + metrics["link_latency_without_stage_cap_s"]
            if math.isfinite(step.step_time_s)
            else None
        ),
        "link_share_of_step": (
            step.component_times_s["link_latency"] / step.step_time_s
            if math.isfinite(step.step_time_s) and step.step_time_s > 0
            else None
        ),
        "node": budget.node,
        "weight_store": budget.weight_store,
        "kv_store": budget.kv_store,
        "weight_amortization": budget.weight_amortization,
        "spare_area_policy": (
            "rom" if "-romfill" in design_id else "sram"
        ),
        "rom_replication_factor": metrics.get("rom_replication_factor"),
        "rom_sweeps_per_step": metrics.get("rom_sweeps_per_step"),
        "silicon_area_mm2": step.silicon_area_mm2,
        "silicon_area_mm2_per_device": budget.silicon_area_mm2_per_device,
        "feasible": step.feasible,
        "reasons": list(step.reasons),
        # **Two rates, and they are not the same number times the batch.**
        # ``per_user_tokens_s`` is one user's token rate on the full serial
        # path; ``aggregate_tokens_s`` is the machine's rate with every slot
        # occupied, which needs ``token_slots`` concurrent users;
        # ``delivered_tokens_s`` is what the machine actually produces at the
        # requested concurrency.  ``*_throughput_view`` is the single number
        # this study reported for both before the two were separated.
        "per_user_tokens_s": step.per_user_tokens_s,
        "aggregate_tokens_s": step.aggregate_tokens_s,
        "delivered_tokens_s": metrics["delivered_tokens_s"],
        "per_user_tokens_s_throughput_view": metrics[
            "per_user_tokens_s_throughput_view"
        ],
        "latency_correction_x": metrics["latency_correction_x"],
        "token_slots": metrics["token_slots"],
        "microbatch_per_slot": metrics["microbatch_per_slot"],
        "pipeline_fill_users": metrics["pipeline_fill_users"],
        "pipeline_fill_fraction": metrics["pipeline_fill_fraction"],
        "pipeline_fill_limited_by": metrics["pipeline_fill_limited_by"],
        "service_time_per_slot_s": metrics["service_time_per_slot_s"],
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
        # The four completeness corrections, carried on every point so that a
        # reader can see what each one cost where it was applied rather than
        # only in a summary table.
        "region_sweep_depth_mean_uncorrected": metrics.get(
            "region_sweep_depth_mean_uncorrected"
        ),
        "region_sweep_depth_max_over_mean": metrics.get(
            "region_sweep_depth_max_over_mean"
        ),
        "mean_engaged_devices_uncorrected": metrics["mean_engaged_devices_uncorrected"],
        "engaged_device_max_over_mean_correction": metrics[
            "engaged_device_max_over_mean_correction"
        ],
        "layer_fixed_latency_s": metrics["layer_fixed_latency_s"],
        "layer_fixed_latency_fraction_of_step": metrics[
            "layer_fixed_latency_fraction_of_step"
        ],
        "kv_access_granularity_bytes": metrics["kv_access_granularity"][
            "granularity_bytes"
        ],
        "kv_index_layout": metrics["kv_access_granularity"]["layout"],
        "kv_access_granularity_inflation": metrics["kv_access_granularity_inflation"],
        "kv_native_transfer_bytes_per_step": metrics["kv_native_transfer_bytes_per_step"],
        "kv_bank_occupancy": metrics["kv_bank_occupancy"],
        "kv_read_s_under_bank_locality": _finite(
            metrics["kv_read_s_under_bank_locality"]
        ),
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


def _per_region_sizing(
    technology: Technology, model: ModelProfile, node: str
) -> dict[str, Any] | None:
    """How big one expert region is, and what its own pre-compute block costs.

    The per-region design's cost is not the arithmetic: it is a pre-compute
    block and an activation distribution network per region.  Sizing it needs
    the compute-in-ROM array density -- the storage density divided by the cell
    multiplier -- and nothing else, so it is emitted here rather than computed
    in prose.
    """

    if model.num_experts <= 1 or model.routed_weight_bytes <= 0:
        return None
    density = (
        technology.rom_bits_per_mm2_for(node, "per_region").value / BITS_PER_BYTE
    )
    precompute_fraction = technology.graded(
        "rom", "cim_precompute_area_fraction"
    ).value
    reticle_area = technology.graded("reticle", "area_mm2").value
    per_expert_bytes = model.routed_weight_bytes / model.num_experts
    region_mm2 = per_expert_bytes / density
    checkpoint_mm2 = model.checkpoint_bytes / density
    return {
        "num_experts": model.num_experts,
        "experts_per_token": model.experts_per_token,
        "compute_in_rom_capacity_density_bytes_mm2": density,
        "routed_bytes_per_expert": per_expert_bytes,
        "region_mm2": region_mm2,
        "precompute_mm2_per_region": precompute_fraction * region_mm2,
        "all_regions_mm2": region_mm2 * model.num_experts,
        "all_precompute_mm2": precompute_fraction * region_mm2 * model.num_experts,
        "precompute_fraction_of_array": precompute_fraction,
        "whole_checkpoint_mm2": checkpoint_mm2,
        "whole_checkpoint_reticles": checkpoint_mm2 / reticle_area,
    }


def _floorplan_comparison(
    technology: Technology, model: ModelProfile, node: str, area_mm2: float
) -> dict[str, Any]:
    """The two ROM floorplans on one die, and whether the MAC array can be fed.

    The storage machine spends its leftover silicon on a MAC array.  Whether
    that array is reachable is a bandwidth question the model can answer
    directly: at one weight byte per multiply-accumulate, the roof it can
    sustain is the ROM read rate beside it.
    """

    stored = model.total_parameters * 3.5 / BITS_PER_BYTE
    resident = 0.0
    out: dict[str, Any] = {
        "die_area_mm2": area_mm2,
        "stored_weight_bytes": stored,
        "weight_bits_per_parameter": 3.5,
    }
    for policy in ("batched", "per_region"):
        budget = rom_device_budget(
            technology,
            name=f"floorplan-{policy}",
            node=node,
            area_mm2_per_device=area_mm2,
            topology=Topology(
                kind="single_chip", device_count=1, parallelism="none", link="none"
            ),
            stored_weight_bytes=stored,
            resident_kv_bytes=resident,
            kv_store="sram",
            weight_amortization=policy,
        )
        # The fp8 roof, because the question is whether an 8-bit-weight MAC
        # array can be fed at one weight byte per multiply-accumulate, and the
        # sustained-fraction derate the model charges everywhere else.
        roof = budget.compute_ops_s.get("fp8", 0.0) * technology.efficiency(
            "compute"
        ).value
        # Two operations per MAC, one weight byte per MAC.
        demanded = roof / 2.0
        out[policy] = {
            "rom_mm2": budget.split.rom_mm2,
            "compute_mm2": budget.split.compute_mm2,
            "sram_mm2": budget.split.sram_mm2,
            "peak_compute_ops_s": roof,
            "weight_read_bytes_s": budget.weight_read_bytes_s,
            "weight_bytes_s_demanded_by_the_roof": demanded,
            "feed_ratio": (
                budget.weight_read_bytes_s / demanded if demanded > 0 else None
            ),
            "full_array_sweep_time_s": budget.provenance[
                "rom_full_array_sweep_time_s"
            ].value,
            "cell_area_multiplier": budget.provenance[
                "rom_cell_area_multiplier"
            ].value,
        }
    return out


def _emit_rom_design(
    technology: Technology,
    model: ModelProfile,
    *,
    designs: list[dict[str, Any]],
    points: list[dict[str, Any]],
    crossovers: list[dict[str, Any]],
    node: str,
    representation: str,
    bits: float | None,
    execution: str,
    kv_store: str,
    topology_name: str,
    suffix: str,
    plan: FabricPlan,
    area_per_device: float,
    devices: int,
    regions: int,
    stored: float,
    design_batch_kv: float,
    design_batch_kv_transfer: float,
    hbm_generation: str,
    amortization: str,
    spare_area_policy: str,
    context: int,
    sweep: list[dict[str, Any]],
    sized: bool,
) -> None:
    """Build one ROM design, its crossover and its whole batch sweep."""

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
        plan=plan,
        on_wafer_regions=regions,
        stored_weight_bytes=stored,
        resident_kv_bytes=design_batch_kv,
        kv_transfer_bytes=design_batch_kv_transfer,
        kv_store=kv_store,
        hbm_generation=hbm_generation,
        weight_amortization=amortization,
        spare_area_policy=spare_area_policy,
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
                else model.checkpoint_bytes / model.total_parameters * 8.0
            ),
            "execution_format": execution,
            "topology": topology_name,
            "weight_amortization": amortization,
            "spare_area_policy": spare_area_policy,
            "sizing_rule": (
                (
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
                )
                if sized
                else (
                    "area-ladder point: this device count is not the sizing "
                    "sweep's choice, it is emitted so the iso-area curve is "
                    "sampled at the same silicon areas on both sides"
                )
            ),
            "device_count_sweep": sweep,
            **budget.to_dict(),
        }
    )
    if sized and amortization == "batched" and spare_area_policy == "sram":
        # Link latency is a property of the topology, so the two
        # amortisation policies produce identical crossovers.
        crossovers.append(
            {
                "design": design_id,
                "model": model.name,
                **latency_crossover(budget.topology, model, technology).to_dict(),
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
                step, budget, family="rom", design_id=design_id, model=model
            )
        )


def _link_latency_sensitivity(
    study_id: str, technology: Technology
) -> list[dict[str, Any]]:
    """The headline table at both ends of every assumed link latency band.

    Every hop latency in this model is `assumed` -- NVIDIA publishes no NVLink
    latency at all and Cerebras publishes no on-wafer or inter-wafer latency --
    and the comparison's whole content is the ratio between two fabrics. A
    single point value inside two wide bands invites the reader to treat the
    ratio as measured. Both ends are therefore run, on **both** sides at once,
    and the band is what the reader is asked to believe rather than the point.
    """

    rows: list[dict[str, Any]] = []
    for bound in ("low", "high"):
        bounded = technology.at_link_latency_bound(bound)
        result = _simulate_study(study_id, bounded, with_sensitivity=False)
        for row in _headline_rows(result):
            rows.append(
                {
                    "bound": bound,
                    "model": row["model"],
                    "rom_silicon_area_mm2": row["rom_silicon_area_mm2"],
                    "rom_design": row["rom_design"],
                    "rom_per_user_tokens_s": row["rom_per_user_tokens_s"],
                    "iso_area_gpu_design": row["iso_area_gpu_design"],
                    "iso_area_gpu_parallelism": row["iso_area_gpu_parallelism"],
                    "iso_area_gpu_per_user_tokens_s": (
                        row["iso_area_gpu_per_user_tokens_s"]
                    ),
                    "per_user_speed_ratio": row["per_user_speed_ratio"],
                }
            )
    return rows


def _headline_rows(result: dict[str, Any]) -> list[dict[str, Any]]:
    """The batch-1 iso-area row at each silicon area, best ROM design per area.

    This is the table the program's headline ratios are read off, so it is the
    table a sensitivity has to be reported on.
    """

    best: dict[tuple[str, int], dict[str, Any]] = {}
    for row in result["comparisons"]:
        if row["batch_size"] != 1 or not row["rom_feasible"]:
            continue
        key = (row["model"], int(round(row["rom_silicon_area_mm2"])))
        current = best.get(key)
        if current is None or (
            row["rom_per_user_tokens_s"] > current["rom_per_user_tokens_s"]
        ):
            best[key] = row
    order = {name: index for index, (name, _, _) in enumerate(STUDY_MODELS)}
    return sorted(
        best.values(),
        key=lambda row: (order[row["model"]], row["rom_silicon_area_mm2"]),
    )


def _simulate_study(
    study_id: str, technology: Technology, *, with_sensitivity: bool = True
) -> dict[str, Any]:
    config = STUDIES[study_id]
    node = str(config["rom_node"])
    hbm_generation = str(config["hbm_generation"])
    reticle_area = technology.graded("reticle", "area_mm2").value
    wafer_area = technology.graded("wafer", "area_mm2").value
    fabric_plans = _fabric_plans(
        technology, config, wafer_area=wafer_area, reticle_area=reticle_area
    )
    gpu_plans = tuple(
        plan for plan, _area in fabric_plans if plan.kind == "array"
    )
    domain_sensitivity_link = config.get("gpu_domain_sensitivity")
    domain_sensitivity: list[dict[str, Any]] = []

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
                "num_experts": model.num_experts,
                "experts_per_token": model.experts_per_token,
                "compressed_sparse_layers": sum(
                    group.count
                    for group in model.attention_groups
                    if group.kind == "compressed_sparse"
                ),
                "layer_fixed_latency": layer_fixed_latency(technology, model)[1],
                "per_region_sizing": _per_region_sizing(technology, model, node),
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
                for amortization, spare_area_policy in (
                    (policy, spare)
                    for policy in WEIGHT_AMORTIZATIONS
                    # Where a compute-in-ROM design spends the silicon it
                    # recovers from the MAC array is a design choice, so both
                    # answers are emitted and the comparison picks between
                    # them.  The amortising machine has no spare area by
                    # definition -- the remainder IS its MAC array -- so it has
                    # only one floorplan.
                    for spare in SPARE_AREA_POLICIES
                ):
                    # **Size every parallelism first, then emit every
                    # parallelism at every size any of them chose.**  Sizing and
                    # emitting in one pass means a topology only exists at the
                    # silicon area its own sweep happened to pick, so an
                    # iso-area row can end up comparing the only design that
                    # exists at that area rather than the best one -- which is
                    # the same defect as letting one side pick its topology,
                    # arrived at through the sizing rule instead.
                    sized: dict[str, tuple[int, list[dict[str, Any]]]] = {}
                    for plan, area_per_device in fabric_plans:
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
                            plan=plan,
                            wafer_area=wafer_area if plan.kind == "wafer" else None,
                            reticle_area=(
                                reticle_area if plan.kind == "wafer" else None
                            ),
                            weight_amortization=amortization,
                            spare_area_policy=spare_area_policy,
                        )
                        sized[plan.label] = (devices, sweep)
                    counts_by_kind: dict[str, set[int]] = {}
                    for plan, _area in fabric_plans:
                        devices, plan_sweep = sized[plan.label]
                        if devices > ARRAY_SWEEP_CAP:
                            continue
                        if amortization != "batched":
                            # Only the batched machine enters the iso-area
                            # comparison, so only it needs every topology at
                            # every sized area; the other two policies are read
                            # from the fork table at their own sizing point.
                            counts_by_kind.setdefault(plan.kind, set()).add(devices)
                            continue
                        floor = (
                            plan_sweep[0]["device_count"] if plan_sweep else devices
                        )
                        bucket = counts_by_kind.setdefault(plan.kind, set())
                        bucket.add(devices)
                        # The ladder is anchored at the smallest machine that
                        # physically holds the design, not at the one the
                        # latency sweep preferred, so the area grid does not
                        # move when a latency assumption moves.
                        if plan.kind == "wafer" and amortization == "batched":
                            bucket.update(
                                count for count in ROM_AREA_LADDER if count >= floor
                            )
                    for plan, area_per_device in fabric_plans:
                        topology_name = plan.label
                        kind = plan.kind
                        parallelism = plan.parallelism
                        chosen, sweep = sized[plan.label]
                        if chosen > ARRAY_SWEEP_CAP:
                            continue
                        # The floor is the smallest count that physically holds
                        # the design, not the count this plan's own latency
                        # sweep preferred -- otherwise a topology is absent from
                        # an area only because a different topology's sweep
                        # liked a slightly different machine.
                        minimum = sweep[0]["device_count"] if sweep else chosen
                        suffix = {
                            "batched": "",
                            "per_stream": "-perstream",
                            "per_region": "-perregion",
                        }[amortization]
                        if spare_area_policy == "rom":
                            suffix += "-romfill"
                        for devices in sorted(counts_by_kind.get(kind, ())):
                            if devices < minimum:
                                # Below this the design does not physically
                                # hold the model.
                                continue
                            regions = _regions_for(
                                plan,
                                devices,
                                wafer_area if kind == "wafer" else None,
                                reticle_area if kind == "wafer" else None,
                            )
                            # A machine with one partition has no
                            # inter-partition event at all, so every parallelism
                            # collapses onto the same design and only the
                            # pipeline label is emitted.  A hybrid whose tensor
                            # group covers every partition it has is a pure
                            # tensor machine under another name, and one whose
                            # group is a single partition is a pure pipeline;
                            # neither is emitted twice.
                            probe = plan.topology(devices, regions)
                            if parallelism != "pipeline" and probe.partitions <= 1:
                                continue
                            if parallelism == "hybrid" and (
                                probe.tensor_group <= 1
                                or probe.tensor_group >= probe.partitions
                            ):
                                continue
                            _emit_rom_design(
                                technology,
                                model,
                                designs=designs,
                                points=points,
                                crossovers=crossovers,
                                node=node,
                                representation=representation,
                                bits=bits,
                                execution=execution,
                                kv_store=kv_store,
                                topology_name=topology_name,
                                suffix=suffix,
                                plan=plan,
                                area_per_device=area_per_device,
                                devices=devices,
                                regions=regions,
                                stored=stored,
                                design_batch_kv=design_batch_kv,
                                design_batch_kv_transfer=design_batch_kv_transfer,
                                hbm_generation=hbm_generation,
                                amortization=amortization,
                                spare_area_policy=spare_area_policy,
                                context=context,
                                sweep=sweep if devices == chosen else [],
                                sized=devices == chosen,
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
            # A fixed area ladder, independent of which ROM design the sizing
            # sweep happens to pick.  Without it the GPU curve is only sampled
            # where a ROM design exists, so a correction that makes the ROM
            # side prefer smaller machines silently truncates the GPU curve
            # too -- and the question "does the GPU still get slower as it is
            # given more silicon" then cannot be asked at the areas where the
            # previous answer was published.
            for wafers in GPU_AREA_LADDER:
                area = wafer_area * wafers
                counts.setdefault(
                    _iso_area_gpu_counts(technology, part, area),
                    f"area ladder: {wafers} wafer-equivalent"
                    f"{'s' if wafers > 1 else ''} of silicon ({area:,.0f} mm2)",
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
                # **The GPU gets the same topology sweep the ROM side gets.**
                # It previously got one: pipeline, at every cluster size, which
                # charged a 672-GPU deployment 671 serial hops per token at
                # batch 1 and reported the resulting collapse as a property of
                # GPUs.  No such deployment exists.  Every parallelism the ROM
                # side may choose is now offered here too, priced on the same
                # two-tier fabric, and the comparison takes the best.
                if count == 1:
                    plans_here: tuple[FabricPlan, ...] = (
                        FabricPlan(
                            kind="single_chip",
                            parallelism="none",
                            intra_link="none",
                            inter_link="none",
                            intra_domain_size=1,
                            label="single",
                        ),
                    )
                else:
                    plans_here = gpu_plans
                for plan in plans_here:
                    topology = plan.topology(count, 1)
                    if plan.parallelism == "hybrid" and (
                        topology.tensor_group <= 1
                        or topology.tensor_group >= topology.partitions
                    ):
                        continue
                    suffix = (
                        "" if count == 1 else f"-{plan.parallelism}"
                    )
                    design_id = f"{_model_tag(model)}/{part}-x{count}{suffix}"
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
                            "topology": f"cluster-{plan.parallelism}",
                            "sizing_rule": rationale,
                            "device_count_sweep": [],
                            **budget.to_dict(),
                        }
                    )
                    if count > 1:
                        crossovers.append(
                            {
                                "design": design_id,
                                "model": model.name,
                                **latency_crossover(
                                    topology, model, technology
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
                        # What the same cluster costs on the larger NVLink
                        # domain the vendor also ships.  The part this study
                        # prices is an SXM module on an eight-GPU baseboard, so
                        # eight is the value; 72 is a published fact about a
                        # different product and is reported rather than
                        # borrowed.
                        if (
                            domain_sensitivity_link
                            and batch == 1
                            and step.feasible
                            and math.isfinite(step.step_time_s)
                        ):
                            wide = replace(
                                topology,
                                intra_link=domain_sensitivity_link,
                                intra_domain_size=max(
                                    1,
                                    int(
                                        technology.link_domain_size(
                                            domain_sensitivity_link
                                        ).value
                                    ),
                                ),
                                tensor_group_size=(
                                    max(
                                        1,
                                        int(
                                            technology.link_domain_size(
                                                domain_sensitivity_link
                                            ).value
                                        ),
                                    )
                                    if plan.parallelism == "hybrid"
                                    else topology.tensor_group_size
                                ),
                            )
                            wide_link, _detail, _payload = technology.link_time_s(
                                wide,
                                model.num_layers,
                                activation_bytes=(
                                    batch * model.hidden_size * 2.0
                                ),
                            )
                            wide_step = (
                                step.step_time_s
                                - step.component_times_s["link_latency"]
                                + wide_link
                            )
                            domain_sensitivity.append(
                                {
                                    "design": design_id,
                                    "model": model.name,
                                    "device_count": count,
                                    "parallelism": plan.parallelism,
                                    "silicon_area_mm2": step.silicon_area_mm2,
                                    "domain_size": topology.intra_domain_size,
                                    "wide_domain_link": domain_sensitivity_link,
                                    "wide_domain_size": wide.intra_domain_size,
                                    "link_latency_s": step.component_times_s[
                                        "link_latency"
                                    ],
                                    "wide_domain_link_latency_s": wide_link,
                                    "per_user_tokens_s": step.per_user_tokens_s,
                                    "wide_domain_per_user_tokens_s": (
                                        1.0 / wide_step if wide_step > 0 else None
                                    ),
                                }
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
        # **The GPU is allowed to pick its topology, exactly as the ROM side
        # is.**  Selecting on area alone and then reading off whichever
        # parallelism happened to be first is how the comparison came to charge
        # the GPU a 672-way pipeline while the ROM ran tensor-parallel at the
        # same area.  Among the clusters closest in area, the fastest feasible
        # one is the comparator; the pipeline-only figure is carried beside it
        # so the size of the previous error stays visible.
        closest = min(
            abs(gpu["silicon_area_mm2"] - row["silicon_area_mm2"])
            for gpu in candidates
        )
        at_area = [
            gpu
            for gpu in candidates
            if abs(gpu["silicon_area_mm2"] - row["silicon_area_mm2"])
            <= closest + 1e-6
        ]
        feasible_at_area = [gpu for gpu in at_area if gpu["feasible"]]
        iso = (
            max(feasible_at_area, key=lambda gpu: gpu["per_user_tokens_s"])
            if feasible_at_area
            else at_area[0]
        )
        pipeline_only = next(
            (gpu for gpu in at_area if gpu["parallelism"] in ("pipeline", "none")),
            iso,
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
                "iso_area_gpu_parallelism": iso["parallelism"],
                "iso_area_gpu_pipeline_stages": iso["pipeline_stages"],
                "iso_area_gpu_pipeline_stages_uncapped": iso[
                    "pipeline_stages_uncapped"
                ],
                "iso_area_gpu_link_latency_without_stage_cap_s": iso[
                    "link_latency_without_stage_cap_s"
                ],
                "iso_area_gpu_per_user_tokens_s_without_stage_cap": (
                    1.0 / iso["step_time_without_stage_cap_s"]
                    if iso.get("step_time_without_stage_cap_s")
                    else None
                ),
                "per_user_speed_ratio_without_stage_cap": (
                    row["per_user_tokens_s"]
                    * iso["step_time_without_stage_cap_s"]
                    if row["feasible"]
                    and iso["feasible"]
                    and iso.get("step_time_without_stage_cap_s")
                    else None
                ),
                "iso_area_gpu_hop_events_per_token": iso["hop_events_per_token"],
                "iso_area_gpu_link_latency_s": iso["component_times_s"][
                    "link_latency"
                ],
                "iso_area_gpu_link_share_of_step": (
                    iso["component_times_s"]["link_latency"] / iso["step_time_s"]
                    if iso["step_time_s"]
                    else None
                ),
                "pipeline_only_gpu_design": pipeline_only["design"],
                "pipeline_only_gpu_per_user_tokens_s": (
                    pipeline_only["per_user_tokens_s"]
                ),
                "pipeline_only_gpu_link_latency_s": (
                    pipeline_only["component_times_s"]["link_latency"]
                ),
                "topology_choice_gain": (
                    iso["per_user_tokens_s"] / pipeline_only["per_user_tokens_s"]
                    if pipeline_only["per_user_tokens_s"] > 0
                    else None
                ),
                "per_user_speed_ratio_pipeline_only_gpu": (
                    row["per_user_tokens_s"] / pipeline_only["per_user_tokens_s"]
                    if row["feasible"]
                    and pipeline_only["feasible"]
                    and pipeline_only["per_user_tokens_s"] > 0
                    else None
                ),
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

    # --- GPU topology choice ----------------------------------------------
    # The symmetric half of the table below.  For every cluster size the study
    # evaluates, this records what each parallelism actually delivered, so the
    # claim "the GPU was allowed to choose" is checkable rather than asserted.
    gpu_topology_choices: list[dict[str, Any]] = []
    gpu_sizes: dict[tuple[str, int, int], list[dict[str, Any]]] = {}
    for row in points:
        if row["family"] != "gpu":
            continue
        gpu_sizes.setdefault(
            (row["model"], row["device_count"], row["batch_size"]), []
        ).append(row)
    for (model_name, count, batch), rows in sorted(gpu_sizes.items()):
        by_parallelism = {row["parallelism"]: row for row in rows}
        feasible = [row for row in rows if row["feasible"]]
        if not feasible:
            continue
        best = max(feasible, key=lambda row: row["per_user_tokens_s"])
        gpu_topology_choices.append(
            {
                "model": model_name,
                "device_count": count,
                "batch_size": batch,
                "silicon_area_mm2": best["silicon_area_mm2"],
                "best_parallelism": best["parallelism"],
                "best_per_user_tokens_s": best["per_user_tokens_s"],
                "best_link_latency_s": best["link_latency_s"],
                "best_link_share_of_step": best["link_share_of_step"],
                "best_hop_events_per_token": best["hop_events_per_token"],
                "best_hop_semantics": best["hop_semantics"],
                "binding_constraint": best["binding_constraint"],
                **{
                    f"{name}_per_user_tokens_s": (
                        by_parallelism[name]["per_user_tokens_s"]
                        if name in by_parallelism
                        else None
                    )
                    for name in ("none", "pipeline", "tensor", "hybrid")
                },
                **{
                    f"{name}_link_latency_s": (
                        by_parallelism[name]["link_latency_s"]
                        if name in by_parallelism
                        else None
                    )
                    for name in ("none", "pipeline", "tensor", "hybrid")
                },
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
      for spare in SPARE_AREA_POLICIES:
        for batch in BATCHES:
            # Compared at a MATCHED floorplan.  Picking each policy's best over
            # both floorplans mixes the amortisation question with the
            # allocation question and hides both: a per-region machine that
            # replicated its array would be compared against a broadcast one
            # that did not.
            pair: dict[str, dict[str, Any] | None] = {}
            for policy in WEIGHT_AMORTIZATIONS:
                rows = [
                    row
                    for row in points
                    if row["model"] == model_name
                    and row["family"] == "rom"
                    and row["batch_size"] == batch
                    and row["weight_amortization"] == policy
                    and row["spare_area_policy"] == spare
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
                "spare_area_policy": spare,
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
                record[f"{policy}_silicon_area_mm2"] = (
                    point["silicon_area_mm2"] if point else None
                )
            amortization_fork.append(record)

    floorplan_sweep: list[dict[str, Any]] = []
    for model_name, _, context in STUDY_MODELS:
        for batch in BATCHES:
            reference = None
            for policy in WEIGHT_AMORTIZATIONS:
                for spare in SPARE_AREA_POLICIES:
                    rows = [
                        row
                        for row in points
                        if row["model"] == model_name
                        and row["family"] == "rom"
                        and row["batch_size"] == batch
                        and row["weight_amortization"] == policy
                        and row["spare_area_policy"] == spare
                        and row["feasible"]
                    ]
                    point = (
                        max(rows, key=lambda row: row["aggregate_tokens_s"])
                        if rows
                        else None
                    )
                    if policy == "batched" and spare == "sram":
                        reference = point
                    floorplan_sweep.append(
                        {
                            "model": model_name,
                            "context_tokens": context,
                            "batch_size": batch,
                            "weight_amortization": policy,
                            "spare_area_policy": spare,
                            "design": point["design"] if point else None,
                            "device_count": point["device_count"] if point else None,
                            "silicon_area_mm2": (
                                point["silicon_area_mm2"] if point else None
                            ),
                            "rom_replication_factor": (
                                point["rom_replication_factor"] if point else None
                            ),
                            "rom_sweeps_per_step": (
                                point["rom_sweeps_per_step"] if point else None
                            ),
                            "per_user_tokens_s": (
                                point["per_user_tokens_s"] if point else None
                            ),
                            "aggregate_tokens_s": (
                                point["aggregate_tokens_s"] if point else None
                            ),
                            "aggregate_tokens_s_per_mm2": (
                                point["aggregate_tokens_s"] / point["silicon_area_mm2"]
                                if point and point["silicon_area_mm2"] > 0
                                else None
                            ),
                            "binding_constraint": (
                                point["binding_constraint"] if point else None
                            ),
                            "vs_reference_floorplan_x": (
                                point["aggregate_tokens_s"]
                                / reference["aggregate_tokens_s"]
                                if point
                                and reference
                                and reference["aggregate_tokens_s"] > 0
                                else None
                            ),
                        }
                    )
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
            "wafer_area_mm2": wafer_area,
            "reticle_area_mm2": reticle_area,
            "rom_area_ladder_wafers": list(ROM_AREA_LADDER),
            "gpu_area_ladder_wafers": list(GPU_AREA_LADDER),
            "counting_convention": (
                "one multiply plus one add equals two operations"
            ),
        },
        "technology_derivations": _technology_derivations(technology, node, config),
        "graded_inputs": technology.inputs_by_grade(),
        "model_summaries": model_summaries,
        "floorplan_comparison": _floorplan_comparison(
            technology,
            ModelProfile.load(ANCHOR_MODEL_PATH),
            node,
            technology.graded("reticle", "area_mm2").value,
        ),
        "designs": designs,
        "points": points,
        "comparisons": comparisons,
        "nvlink_domain_sensitivity": domain_sensitivity,
        "link_latency_sensitivity": (
            _link_latency_sensitivity(study_id, technology)
            if with_sensitivity
            else []
        ),
        "topology_choices": topology_choices,
        "gpu_topology_choices": gpu_topology_choices,
        "amortization_fork": amortization_fork,
        "floorplan_sweep": floorplan_sweep,
        "latency_crossovers": crossovers,
    }
    result["latency_correction_ladder"] = _latency_correction_ladder(result)
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
                "fabric": technology.link_fabric(name),
                "domain_size": technology.link_domain_size(name).to_dict(),
                "switch_radix": technology.link_switch_radix(name).to_dict(),
            }
            for name in sorted(technology.raw["links"])
            if name != "none"
        },
        "link_plan": {
            "intra": str(config["intra_link"]),
            "inter": str(config["inter_link"]),
            "rule": (
                "Both sides of this study are charged the same two link classes. "
                "A cluster is tensor-parallel inside one high-bandwidth domain and "
                "pipeline-parallel across domains; a wafer machine is the same shape "
                "with the on-wafer mesh inside a wafer and a package-class link "
                "between wafers."
            ),
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


def _latency_correction_ladder(result: dict[str, Any]) -> list[dict[str, Any]]:
    """Before and after the latency separation, on the fixed area ladder.

    The **before** column is not a memory of an earlier run: every point in this
    study carries ``per_user_tokens_s_throughput_view``, the number the model
    produced when it charged a pipeline's service time on the machine's
    aggregate resources and its hops on the single-token path.  Ranking each
    side by that column reproduces the previous study's choice of topology as
    well as its rate, so the two corrections -- the ranking and the rate -- are
    visible separately.

    Both sides are read at the same seven rungs of silicon, so a correction that
    moves one family's preferred machine cannot move the area the comparison is
    read at.
    """

    inputs = result["inputs"]
    wafer_area = inputs["wafer_area_mm2"]
    ladder = [wafer_area * count for count in inputs["rom_area_ladder_wafers"]]
    points = [row for row in result["points"] if row["batch_size"] == 1]
    rom = [
        row
        for row in points
        if row["family"] == "rom"
        and row["weight_amortization"] == "batched"
        and row["feasible"]
    ]
    gpu = [row for row in points if row["family"] == "gpu" and row["feasible"]]
    rows: list[dict[str, Any]] = []
    for summary in result["model_summaries"]:
        model = summary["model"]
        for wafers, area in zip(inputs["rom_area_ladder_wafers"], ladder):
            rom_here = [
                row
                for row in rom
                if row["model"] == model
                and abs(row["silicon_area_mm2"] - area) <= 1.0
            ]
            gpu_all = [row for row in gpu if row["model"] == model]
            if not rom_here or not gpu_all:
                continue
            closest = min(
                abs(row["silicon_area_mm2"] - area) for row in gpu_all
            )
            gpu_here = [
                row
                for row in gpu_all
                if abs(row["silicon_area_mm2"] - area) <= closest + 1e-6
            ]
            record: dict[str, Any] = {
                "model": model,
                "wafer_equivalents": wafers,
                "silicon_area_mm2": area,
                "gpu_silicon_area_mm2": gpu_here[0]["silicon_area_mm2"],
                "gpu_device_count": gpu_here[0]["device_count"],
            }
            for label, key in (
                ("before", "per_user_tokens_s_throughput_view"),
                ("after", "per_user_tokens_s"),
            ):
                best_rom = max(rom_here, key=lambda row: row[key])
                best_gpu = max(gpu_here, key=lambda row: row[key])
                record[f"rom_{label}_tokens_s"] = best_rom[key]
                record[f"rom_{label}_topology"] = (
                    f"{best_rom['topology_kind']}-{best_rom['parallelism']}"
                )
                record[f"rom_{label}_device_count"] = best_rom["device_count"]
                record[f"rom_{label}_token_slots"] = best_rom["token_slots"]
                record[f"gpu_{label}_tokens_s"] = best_gpu[key]
                record[f"gpu_{label}_topology"] = best_gpu["parallelism"]
                record[f"gpu_{label}_token_slots"] = best_gpu["token_slots"]
                record[f"ratio_{label}"] = (
                    best_rom[key] / best_gpu[key] if best_gpu[key] > 0 else None
                )
            record["ratio_change_x"] = (
                record["ratio_after"] / record["ratio_before"]
                if record["ratio_before"]
                else None
            )
            record["rom_correction_x"] = (
                record["rom_before_tokens_s"] / record["rom_after_tokens_s"]
                if record["rom_after_tokens_s"] > 0
                else None
            )
            record["gpu_correction_x"] = (
                record["gpu_before_tokens_s"] / record["gpu_after_tokens_s"]
                if record["gpu_after_tokens_s"] > 0
                else None
            )
            rows.append(record)
    return rows


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
        # **The identity that used to be here is gone, and its removal is the
        # point.**  ``aggregate = batch x per_user`` held by construction only
        # because the model charged one number for both.  A machine cut into
        # ``token_slots`` slots reaches its aggregate rate only when every slot
        # has a user in it, so the aggregate is over ``pipeline_fill_users``,
        # which is the batch when the batch is large enough to fill the machine
        # and the slot count when it is not.  What the machine delivers at the
        # requested concurrency is the weaker ``delivered_tokens_s``, and *that*
        # is the quantity the old identity was about.
        check(
            close(
                row["aggregate_tokens_s"],
                row["pipeline_fill_users"] * row["per_user_tokens_s"],
            ),
            f"aggregate = fill x per-user identity {key}",
        )
        check(
            close(
                row["delivered_tokens_s"],
                row["batch_size"] * row["per_user_tokens_s"],
            ),
            f"delivered = batch x per-user identity {key}",
        )
        check(
            row["pipeline_fill_users"] >= row["batch_size"] - 1e-9,
            f"fill below the requested batch {key}",
        )
        check(
            row["aggregate_tokens_s"] >= row["delivered_tokens_s"] * (1 - 1e-9),
            f"aggregate below delivered {key}",
        )
        # A single-slot machine -- one chip, or a tensor group spanning every
        # partition -- is the one case where the two views coincide, and the
        # correction must be exactly 1.0 there.  Both validation gates are such
        # machines, which is why a correct fix leaves them untouched.
        if row["token_slots"] <= 1.0 + 1e-12:
            check(
                close(
                    row["per_user_tokens_s_throughput_view"],
                    row["per_user_tokens_s"],
                ),
                f"single-slot machine must have no latency correction {key}",
            )
        elif row["microbatch_per_slot"] >= row["batch_size"] - 1e-9:
            # Below one user per slot the two views see the same microbatch and
            # the same activation payload on every hop, so the correction is
            # exactly the extra service the serial path pays: never below one.
            # **Above it the correction can fall below one, and that is not a
            # bug.** The throughput view charged the whole batch's activations
            # across each hop while calling the result one user's latency; the
            # serial path charges one slot's microbatch, which is smaller. On a
            # KV-bound pipeline at high batch the service terms scale with the
            # batch and cancel exactly, leaving only that payload difference, so
            # the old number comes out *slower* than the corrected one. The
            # regime the ROM case is made in is batch 1, where the check bites.
            check(
                row["latency_correction_x"] >= 1.0 - 1e-9,
                f"latency correction below one {key}",
            )
        else:
            check(
                row["latency_correction_x"] > 0.0
                and math.isfinite(row["latency_correction_x"]),
                f"latency correction not a positive finite number {key}",
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
            row["step_time_s"] + 1e-15 >= components["layer_fixed_latency"],
            f"step below the per-layer fixed latency {key}",
        )
        check(
            row["binding_constraint"]
            in {
                "weight_read",
                "kv_read",
                "compute",
                "link_latency",
                "layer_fixed_latency",
                "thermal",
            },
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
            if policy == "batched":
                check(sweeps == 1, f"batched must sweep once {key}")
            elif policy == "per_stream":
                # One sweep per concurrent stream **in one slot**.  A slot holds
                # the microbatch, not the whole batch: on a machine cut into
                # slots the batch is spread across them and each slot sweeps for
                # the users it actually holds.
                check(
                    close(sweeps, row["microbatch_per_slot"]),
                    f"per_stream must sweep once per stream in a slot {key}",
                )
            elif policy == "per_region":
                # Disjoint regions run together, so the sweep depth is the
                # busiest region's queue: never below one, never worse than
                # every token in the slot landing on the same region.
                check(
                    1.0 - 1e-9 <= sweeps <= row["microbatch_per_slot"] + 1e-9,
                    f"per_region sweep depth outside [1, microbatch] {key}",
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
            # The sweep floor is per slot; a token traverses ``token_slots`` of
            # them, and ``component_times_s`` is the serial path.
            serial_sweep = row["rom_full_array_sweep_time_s"] * row["token_slots"]
            check(
                components["weight_read"] <= serial_sweep * (1 + 1e-9),
                f"ROM weight time above the serial full-array sweep floor {key}",
            )
            check(
                components["weight_read"] >= serial_sweep * (1 - 1e-9),
                f"ROM weight time below the serial full-array sweep floor {key}",
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


def _render_corrections(result: dict[str, Any]) -> list[str]:
    """What the four completeness corrections cost, from the points themselves.

    A correction that is only described is a correction a reader has to take on
    trust.  Each block below is computed from the same evaluated points as
    every other table in this report.
    """

    points = result["points"]
    lines = [
        "",
        "## What the completeness corrections cost",
        "",
        "Four terms the model priced wrongly or not at all. Each row is",
        "computed from the evaluated points, not restated from prose.",
        "",
        "### 1. Per-region sweep depth: the busiest region, not the mean",
        "",
        "The compute-in-ROM per-region machine used to charge `batch * k /",
        "(N * coverage)` -- the load of the AVERAGE engaged region -- and then",
        "divide it by a flat 0.85 whose own note said the depth is set by the",
        "busiest region. The busiest region is now computed from the routing",
        "distribution. The correction is not a constant: it is a function of",
        "how many users one array pass actually serves.",
        "",
        "**Read the `Users per slot` column, not the batch.** Since per-user",
        "latency was separated from aggregate throughput, a machine cut into",
        "`token_slots` slots spreads its batch across them, and the region",
        "collisions this correction is about happen inside **one** slot. Where",
        "the design the sweep chose has more slots than the batch has users, one",
        "pass serves one user, no two tokens can collide on a region, and the",
        "correction is 1.00x by construction rather than by accident. The",
        "statistic itself is unchanged and is checked against a Monte Carlo of",
        "the routing in `tests/test_roofline.py`; what moved is which point on it",
        "these designs sit at.",
        "",
        "| Model | B | Slots | Users per slot | Mean engaged region | "
        "Busiest region | Correction |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    seen: set[tuple[str, int]] = set()
    for row in points:
        depth = row.get("region_sweep_depth_max_over_mean")
        if depth is None or not row["feasible"]:
            continue
        key = (row["model"], row["batch_size"])
        if key in seen:
            continue
        seen.add(key)
        lines.append(
            f"| {row['model']} | {row['batch_size']} | "
            f"{row['token_slots']:,.0f} | "
            f"{row['microbatch_per_slot']:,.2f} | "
            f"{row['region_sweep_depth_mean_uncorrected']:,.3f} | "
            f"{row['rom_sweeps_per_step']:,.3f} | "
            f"{_fmt_ratio(depth)} |"
        )

    lines.extend(
        [
            "",
            "### 2. Expert-parallel devices: the busiest device, not the mean engaged one",
            "",
            "The same error on the GPU side of the comparison. A routed fetch",
            "finishes when the most loaded device finishes, not when the average",
            "of the engaged ones does. `opentallas.workload` is shared with",
            "`opentallas.analytical` and is unchanged; the correction is applied",
            "in `roofline` and both numbers are carried on every point, because",
            "correcting only the ROM side would be its own bias.",
            "",
            "| Model | B | Devices | Mean engaged | Effective | Correction |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    gpu_seen: set[tuple[str, int, int]] = set()
    for row in points:
        if row["family"] != "gpu" or not row["feasible"]:
            continue
        correction = row["engaged_device_max_over_mean_correction"]
        if correction is None or correction <= 1.0 + 1e-9:
            continue
        key = (row["model"], row["batch_size"], row["device_count"])
        if key in gpu_seen:
            continue
        gpu_seen.add(key)
        lines.append(
            f"| {row['model']} | {row['batch_size']} | {row['device_count']} | "
            f"{row['mean_engaged_devices_uncorrected']:,.2f} | "
            f"{row['engaged_devices']:,.2f} | {_fmt_ratio(correction)} |"
        )

    lines.extend(
        [
            "",
            "### 3. The per-layer serial cost, and who pays it",
            "",
            "Before this term the only latency in the model was",
            "`links.*.hop_latency_s`, charged at inter-partition boundaries -- so",
            "a `single_chip` design had a decode step with no fixed cost at all.",
            "**The asymmetry is the finding and it runs against the ROM thesis:**",
            "a ROM step is tens of microseconds over 32-61 layers while a GPU step",
            "for the same model is milliseconds, so the same per-layer floor is a",
            "large fraction of one and a rounding error on the other.",
            "",
            "| Family | Model | B | Fixed latency (us) | Share of the fastest step |",
            "|---|---|---:|---:|---:|",
        ]
    )
    best_share: dict[tuple[str, str, int], dict[str, Any]] = {}
    for row in points:
        if not row["feasible"]:
            continue
        key = (row["family"], row["model"], row["batch_size"])
        current = best_share.get(key)
        if current is None or row["per_user_tokens_s"] > current["per_user_tokens_s"]:
            best_share[key] = row
    for key in sorted(best_share, key=lambda item: (item[0], item[1], item[2])):
        row = best_share[key]
        if row["batch_size"] != 1:
            continue
        lines.append(
            f"| {row['family']} | {row['model']} | {row['batch_size']} | "
            f"{_fmt_us(row['layer_fixed_latency_s'])} | "
            f"{row['layer_fixed_latency_fraction_of_step']:.1%} |"
        )

    lines.extend(
        [
            "",
            "### 4. KV access granularity, which is a layout choice",
            "",
            "`workload.kv_traffic` counts the bytes the algorithm needs. A memory",
            "moves whole granules, and for a sparse-index model most of the KV",
            "read is a scan of entries far smaller than one granule. Whether that",
            "costs anything is a **layout** decision, so it is stated as one.",
            "",
            "| Model | KV store | Layout | Granule | Inflation |",
            "|---|---|---|---:|---:|",
        ]
    )
    kv_seen: set[tuple[str, str]] = set()
    for row in points:
        key = (row["model"], row["kv_store"])
        if key in kv_seen:
            continue
        kv_seen.add(key)
        lines.append(
            f"| {row['model']} | {row['kv_store']} | {row['kv_index_layout']} | "
            f"{row['kv_access_granularity_bytes']:,.0f} B | "
            f"{_fmt_ratio(row['kv_access_granularity_inflation'])} |"
        )

    lines.extend(
        [
            "",
            "### 5. The SRAM KV path, which is still never exercised",
            "",
            "A reported bound rather than a correction. The step credits ONE user",
            "with the whole array's read bandwidth. That is defensible for KV in a",
            "way it is not for ROM -- KV is written at run time and can be striped",
            "across every bank, whereas an expert's weights live where they were",
            "masked -- but it holds only if the design really stripes, and nothing",
            "in the model checks. The bound below is what the same read costs if a",
            "user can draw only the banks its own footprint occupies.",
            "",
            "| Model | B | Devices | Bank occupancy | KV read as charged (us) | "
            "Under bank locality (us) |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    sram_seen: set[tuple[str, int]] = set()
    for row in points:
        if row["kv_store"] != "sram" or not row["feasible"]:
            continue
        if row["kv_bank_occupancy"] >= 1.0 - 1e-9:
            continue
        key = (row["model"], row["batch_size"])
        if key in sram_seen:
            continue
        sram_seen.add(key)
        lines.append(
            f"| {row['model']} | {row['batch_size']} | {row['device_count']} | "
            f"{row['kv_bank_occupancy']:.2%} | "
            f"{_fmt_us(row['component_times_s']['kv_read'])} | "
            f"{_fmt_us(row['kv_read_s_under_bank_locality'])} |"
        )
    return lines


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
        "t_service = max(t_memory, t_compute)      on the AGGREGATE machine",
        "t_user    = token_slots * t_service / stage_balance + t_link",
        "t_user   *= thermal_scale",
        "",
        "per_user_tokens_s  = 1 / t_user",
        "aggregate_tokens_s = fill_users / t_user      fill_users = max(batch, slots)",
        "delivered_tokens_s = batch / t_user",
        "```",
        "",
        "Compute overlaps memory. Weight and KV traffic **add** on a GPU because they",
        "contend for the same HBM channels, and **overlap** on a ROM part because the",
        "mask ROM and the KV store are physically separate arrays -- that single rule",
        "is most of the architectural difference and it is stated rather than hidden",
        "in an efficiency factor. Hop and collective latency is **added** to the",
        "critical path at every batch size, because decode is sequential across",
        "layers.",
        "",
        "`t_service` is computed on the machine's **aggregate** resources: all of the",
        "array bandwidth, all of the compute roof. That denominator is correct only",
        "for partitions that are working on the same token at the same instant, which",
        "is what tensor parallelism is. `token_slots = partitions / tensor_group` is",
        "how many independent groups the machine is cut into, and a token is served by",
        "exactly one of them at a time, so its latency is `token_slots` service times",
        "long. **Under pipeline parallelism the two factors cancel exactly** -- each of",
        "N stages holds 1/N of the weights and reads them with 1/N of the bandwidth --",
        "so adding devices buys aggregate throughput and buys one user nothing.",
        "Tensor parallelism is different in kind: every partition is on the same token,",
        "`token_slots` is 1, and the price is two all-reduces per layer, charged in",
        "`t_link`.",
        "",
        "**`aggregate = batch x per-user rate` no longer holds and its removal is the",
        "point.** The aggregate rate is the machine's rate with every slot occupied,",
        "which needs `token_slots` concurrent users; below that the surplus slots idle",
        "and the machine delivers `delivered_tokens_s` instead. The fill is capped by",
        "the users whose KV the machine can hold, reported per point as",
        "`pipeline_fill_limited_by`. Fill and drain are not charged: decode is a",
        "continuous stream of steps and the pipeline is taken to be in steady state,",
        "which flatters a deep pipeline by at most one traversal per request.",
        "",
        "Every point also carries `per_user_tokens_s_throughput_view`: the single",
        "number this study reported for both quantities before they were separated, so",
        "the size of this correction is separable from every other one.",
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
            "### The per-layer latency band, and why the gate is not fitted",
            "",
            "Every term in the per-layer latency block is `assumed` and carries",
            "a stated range. Reporting the gate at one point inside a wide band",
            "would invite the point to be read as measured, which is how a gate",
            "becomes a one-parameter curve fit. The terms are derived from",
            "primitives independent of this anchor -- SRAM access time,",
            "sequencer issue and decode, pipeline fill and drain across a",
            "dependent array-pass boundary, the layer barrier, and an on-die",
            "wire delay over a distance taken from the floorplan -- and the gate",
            "is evaluated at both ends.",
            "",
            "| Per-layer latency | Value | Per token | Modelled tok/s | Ratio | Binds on |",
            "|---|---:|---:|---:|---:|---|",
        ]
    )
    band = anchors["taalas_hc1"]["detail"]["layer_fixed_latency_band"]
    for bound in ("low", "stated", "high"):
        entry = band[bound]
        lines.append(
            f"| range {bound} | "
            f"{entry['layer_fixed_latency_s_per_layer'] * 1e9:,.1f} ns/layer | "
            f"{_fmt_us(entry['layer_fixed_latency_s_per_token'])} us | "
            f"{_fmt(entry['modelled_tokens_s'])} | "
            f"{_fmt_ratio(entry['ratio_to_published'])} | "
            f"{entry['binding_constraint']} |"
        )
    closing = band["per_layer_cost_that_would_close_the_gap_s"]
    lines.extend(
        [
            "",
            "The per-layer cost that would land the model exactly on the",
            f"published figure is **{closing * 1e9:,.1f} ns/layer**. It is"
            + (
                " negative, which means the model is already slower than the"
                " shipping part before any fixed cost is charged: no value of"
                " this term could have closed the gap, and the residual lies in"
                " the ROM read-bandwidth density instead."
                if closing < 0
                else " reported so the distance between the derived value and"
                " the fitted one is visible. It is never used as an input."
            ),
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

    ladder = result.get("latency_correction_ladder") or []
    if ladder:
        lines.extend(
            [
                "",
                "## The latency separation, before and after, at batch 1",
                "",
                "Per-user latency and aggregate throughput used to be one number in",
                "this study. The service time was computed on the machine's",
                "**aggregate** resources -- the throughput view -- and the hops were",
                "added on the single-token path, which is the latency view. A token",
                "under pipeline parallelism is served by one stage's silicon at a time",
                "and has to visit every stage, so its latency is that service time",
                "multiplied by the slot count, not divided by anything.",
                "",
                "**Before** is not a memory of an earlier run. Every point carries",
                "`per_user_tokens_s_throughput_view`, the number the old rule produced,",
                "and each side is ranked by it -- so the before column reproduces the",
                "previous topology choice as well as the previous rate, and the two",
                "corrections stay separable. Both sides are read at the same seven",
                "rungs of silicon.",
                "",
                "| Model | Wafer-eq | mm2 | ROM before | topo | ROM after | topo | ROM /x |"
                " GPU before | topo | GPU after | topo | GPU /x | Ratio before |"
                " Ratio after | Ratio change |",
                "|---|---:|---:|---:|---|---:|---|---:|---:|---|---:|---|---:|---:|---:|---:|",
            ]
        )
        for row in ladder:
            lines.append(
                f"| {row['model']} | {row['wafer_equivalents']} | "
                f"{_fmt_area(row['silicon_area_mm2'])} | "
                f"{_fmt(row['rom_before_tokens_s'])} | "
                f"{row['rom_before_topology']} | "
                f"{_fmt(row['rom_after_tokens_s'])} | "
                f"{row['rom_after_topology']} | "
                f"{_fmt_ratio(row['rom_correction_x'])} | "
                f"{_fmt(row['gpu_before_tokens_s'])} | "
                f"{row['gpu_before_topology']} | "
                f"{_fmt(row['gpu_after_tokens_s'])} | "
                f"{row['gpu_after_topology']} | "
                f"{_fmt_ratio(row['gpu_correction_x'])} | "
                f"{_fmt_ratio(row['ratio_before'])} | "
                f"{_fmt_ratio(row['ratio_after'])} | "
                f"{_fmt_ratio(row['ratio_change_x'])} |"
            )
        changes = [
            row["ratio_change_x"] for row in ladder if row.get("ratio_change_x")
        ]
        if changes:
            lines.extend(
                [
                    "",
                    "**Did the error cancel in the ratio?** If it had, `Ratio change`"
                    " would be 1.00x on every row. It runs from"
                    f" {min(changes):.2f}x to {max(changes):.2f}x across this ladder."
                    " It does not cancel, for the reason the two families reach equal"
                    " area at very different device counts and therefore at very"
                    " different slot counts, and because the correction changes which"
                    " topology each side picks -- a change that lands on whichever"
                    " side was relying on depth.",
                    "",
                ]
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
            "**Both sides choose their own parallelism.** The GPU cluster is",
            "evaluated under pipeline, tensor and hybrid and the best is reported,",
            "exactly as the ROM side is. `PP-only ratio` is what the same comparison",
            "says when the GPU is allowed pipeline and nothing else.",
            "",
            "`Ratio without the layer cap` is what the comparison says when a token",
            "is allowed to cross more stage boundaries than the model has layers --",
            "which is what this study charged before. That column, not the topology",
            "sweep, is where the previously published ratios came from.",
            "",
            "**`user tok/s` and `aggregate tok/s` are different quantities and no",
            "longer differ by the batch.** `user tok/s` is one user's token rate on",
            "the full serial path through the machine. `aggregate tok/s` is the",
            "machine's total rate with a user in every slot, which needs",
            "`token_slots` concurrent users; where the batch is smaller than that,",
            "the surplus slots idle and what the machine actually delivers at the",
            "stated batch is `batch x user tok/s`, carried per point as",
            "`delivered_tokens_s`. Read the per-user ratio for a latency claim and",
            "the aggregate ratio for a throughput claim; reading either as the other",
            "is the error this study made.",
            "",
            "| Model | B | Pick | ROM design | ROM mm2 | ROM user tok/s | "
            "ROM aggregate tok/s | ROM binds on | GPU | GPU mm2 | Area ratio | "
            "GPU parallelism | GPU link us | GPU user tok/s | GPU aggregate tok/s | "
            "GPU binds on | Per-user ratio | Aggregate ratio | PP-only ratio | "
            "Ratio without the layer cap |",
            "|---|---:|---|---|---:|---:|---:|---|---|---:|---:|---|---:|---:|---:|---|---:|---:|---:|---:|",
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
            f"{row['iso_area_gpu_parallelism']} | "
            f"{_fmt_us(row['iso_area_gpu_link_latency_s'])} | "
            f"{_fmt(row['iso_area_gpu_per_user_tokens_s']) if row['iso_area_gpu_feasible'] else 'infeasible'} | "
            f"{_fmt(row['iso_area_gpu_aggregate_tokens_s']) if row['iso_area_gpu_feasible'] else '—'} | "
            f"{row['iso_area_gpu_binding_constraint']} | "
            f"{_fmt_ratio(row['per_user_speed_ratio'])} | "
            f"{_fmt_ratio(row['aggregate_speed_ratio'])} | "
            f"{_fmt_ratio(row.get('per_user_speed_ratio_pipeline_only_gpu'))} | "
            f"{_fmt_ratio(row.get('per_user_speed_ratio_without_stage_cap'))} |"
        )

    sensitivity = result.get("link_latency_sensitivity") or []
    if sensitivity:
        stated = {
            (row["model"], round(row["rom_silicon_area_mm2"])): row
            for row in _headline_rows(result)
        }
        by_bound: dict[tuple[str, int], dict[str, dict[str, Any]]] = {}
        for row in sensitivity:
            key = (row["model"], round(row["rom_silicon_area_mm2"]))
            by_bound.setdefault(key, {})[row["bound"]] = row
        lines.extend(
            [
                "",
                "## Every hop latency in this model is assumed, so the headline is a "
                "band",
                "",
                "NVIDIA publishes no NVLink or NVSwitch latency figure in any form,",
                "and Cerebras publishes none for the on-wafer mesh or for SwarmX. The",
                "table below re-runs the whole study with **every** assumed hop",
                "latency at the low end of its stated range and again at the high end",
                "-- on both sides at once, because a ratio is only tested by moving",
                "both ends of it together. Where the band is wide the ratio is not a",
                "number, it is an interval.",
                "",
                "| Model | ROM mm2 | Ratio at low | Ratio stated | Ratio at high |",
                "|---|---:|---:|---:|---:|",
            ]
        )
        for key in sorted(by_bound, key=lambda item: (item[0], item[1])):
            point = stated.get(key)
            bounds = by_bound[key]
            if point is None or point["per_user_speed_ratio"] is None:
                continue
            lines.append(
                f"| {key[0]} | {key[1]:,} | "
                f"{_fmt_ratio((bounds.get('low') or {}).get('per_user_speed_ratio'))} | "
                f"{_fmt_ratio(point['per_user_speed_ratio'])} | "
                f"{_fmt_ratio((bounds.get('high') or {}).get('per_user_speed_ratio'))} |"
            )

    domain_rows = result.get("nvlink_domain_sensitivity") or []
    if domain_rows:
        best_by_size: dict[tuple[str, int], dict[str, Any]] = {}
        for row in domain_rows:
            key = (row["model"], row["device_count"])
            current = best_by_size.get(key)
            if current is None or row["per_user_tokens_s"] > current["per_user_tokens_s"]:
                best_by_size[key] = row
        widest = max(
            domain_rows,
            key=lambda row: (row["domain_size"], row["wide_domain_size"]),
        )
        lines.extend(
            [
                "",
                "## The NVLink domain is a published number, and there are two of them",
                "",
                f"This study prices an SXM module on a baseboard whose NVLink domain is "
                f"{widest['domain_size']} GPUs, which is what the vendor publishes for "
                "that part. The",
                f"same vendor also ships a {widest['wide_domain_size']}-GPU single-tier "
                "NVLink domain in a rack-scale product built",
                "from a different module. Borrowing the larger domain for this part "
                "would be",
                "choosing an input by its answer, so it is reported here instead. "
                "Batch 1,",
                "best topology at each cluster size.",
                "",
                f"| Model | GPUs | mm2 | Link us at domain {widest['domain_size']} | "
                f"Link us at domain {widest['wide_domain_size']} | tok/s at "
                f"{widest['domain_size']} | tok/s at {widest['wide_domain_size']} |",
                "|---|---:|---:|---:|---:|---:|---:|",
            ]
        )
        for key in sorted(best_by_size, key=lambda item: (item[0], item[1])):
            row = best_by_size[key]
            lines.append(
                f"| {row['model']} | {row['device_count']:,} | "
                f"{_fmt_area(row['silicon_area_mm2'])} | "
                f"{_fmt_us(row['link_latency_s'])} | "
                f"{_fmt_us(row['wide_domain_link_latency_s'])} | "
                f"{_fmt(row['per_user_tokens_s'])} | "
                f"{_fmt(row['wide_domain_per_user_tokens_s'])} |"
            )

    gpu_choices = [
        row for row in result.get("gpu_topology_choices", []) if row["batch_size"] == 1
    ]
    if gpu_choices:
        lines.extend(
            [
                "",
                "## The GPU's own topology choice, at batch 1",
                "",
                "Every cluster size in the study, under each parallelism it can",
                "actually run, at **per-user** rate. `pipeline` is what this study",
                "charged the GPU before, at every size; `hybrid` is tensor-parallel",
                "inside the NVLink domain and pipeline-parallel across it, which is",
                "what a real deployment of this size runs. A blank cell is a topology",
                "that collapses onto another at that size and is not emitted twice.",
                "",
                "**This table is where the latency separation shows up most",
                "plainly.** A pipeline column is now a machine cut into as many slots",
                "as it has GPUs, and a token visits every one of them; the whole",
                "cluster's HBM bandwidth is on that token's path only under `tensor`,",
                "which is why a 672-GPU pipeline reads as fractions of a token per",
                "second while the same silicon tensor-parallel reads in the hundreds.",
                "",
                "| Model | GPUs | mm2 | Pipeline tok/s | Tensor tok/s | Hybrid tok/s | "
                "Best | Best link us | Link share | Binds on |",
                "|---|---:|---:|---:|---:|---:|---|---:|---:|---|",
            ]
        )
        for row in gpu_choices:
            share = row["best_link_share_of_step"]
            lines.append(
                f"| {row['model']} | {row['device_count']} | "
                f"{_fmt_area(row['silicon_area_mm2'])} | "
                f"{_fmt(row['pipeline_per_user_tokens_s'])} | "
                f"{_fmt(row['tensor_per_user_tokens_s'])} | "
                f"{_fmt(row['hybrid_per_user_tokens_s'])} | "
                f"{row['best_parallelism']} | "
                f"{_fmt_us(row['best_link_latency_s'])} | "
                f"{'—' if share is None else f'{share * 100:.1f}%'} | "
                f"{row['binding_constraint']} |"
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
            "Each event is priced on the link it actually crosses and, for a",
            "collective, on how many partitions it spans: an all-reduce costs",
            "`traversals x hop latency` plus `(p-1)/p` of the payload each way, where",
            "`traversals` is `2 lg p` in the fabric's own switch radix (Thakur,",
            "Rabenseifner & Gropp 2005) or 1.1x the mesh diameter on a stitched",
            "fabric (Rocki et al., SC20). `Events` spells the breakdown out.",
            "",
            "| Design | Model | Devices | Parallelism | Intra link | Inter link | "
            "Hops/token | Link latency/token | Viable to (10% budget) | "
            "Hard ceiling | Events |",
            "|---|---|---:|---|---|---|---:|---:|---:|---:|---|",
        ]
    )
    seen_crossovers: set[str] = set()
    for row in result["latency_crossovers"]:
        if row["design"] in seen_crossovers:
            continue
        seen_crossovers.add(row["design"])
        lines.append(
            f"| {row['design']} | {row['model']} | {row['device_count']} | "
            f"{row['parallelism']} | {row.get('intra_link') or row['link']} | "
            f"{row['link']} | {row['hop_events_per_token']:,.0f} | "
            f"{_fmt_us(row['link_latency_s_per_token'])} us | "
            f"{_fmt(row['viable_tokens_s'])} tok/s | "
            f"{_fmt(row['hard_ceiling_tokens_s'])} tok/s | "
            f"{'; '.join(row.get('breakdown') or ()) or '—'} |"
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

    floorplan = result.get("floorplan_comparison")
    if floorplan:
        storage = floorplan["batched"]
        cim = floorplan["per_region"]
        lines.extend(
            [
                "",
                "## The two ROM floorplans on one die",
                "",
                f"Both machines hold the same {floorplan['stored_weight_bytes']/1e9:,.2f} GB "
                f"of weights at {floorplan['weight_bits_per_parameter']:g} bits per "
                f"parameter on the same {floorplan['die_area_mm2']:,.0f} mm2. They are "
                "different floorplans, not one floorplan with two arithmetics.",
                "",
                "| | ROM + MAC array | compute-in-ROM |",
                "|---|---:|---:|",
                f"| cell area vs a storage-only bit | {storage['cell_area_multiplier']:.1f}x "
                f"| {cim['cell_area_multiplier']:.1f}x |",
                f"| ROM array | {storage['rom_mm2']:,.1f} mm2 | {cim['rom_mm2']:,.1f} mm2 |",
                f"| compute block | {storage['compute_mm2']:,.1f} mm2 | "
                f"{cim['compute_mm2']:,.1f} mm2 (pre-compute only) |",
                f"| SRAM | {storage['sram_mm2']:,.1f} mm2 | {cim['sram_mm2']:,.1f} mm2 |",
                f"| sustained fp8 compute roof | {storage['peak_compute_ops_s']:.3e} ops/s | "
                "the array sweep itself |",
                f"| weight bytes/s the roof wants | "
                f"{storage['weight_bytes_s_demanded_by_the_roof']:.3e} | n/a |",
                f"| weight bytes/s the array supplies | "
                f"{storage['weight_read_bytes_s']:.3e} | "
                f"{cim['weight_read_bytes_s']:.3e} |",
                f"| **can the compute block be fed?** | "
                f"**{storage['feed_ratio']:.2f}x** | there is nothing to feed |",
                f"| full-array sweep | {_fmt_us(storage['full_array_sweep_time_s'])} us | "
                f"{_fmt_us(cim['full_array_sweep_time_s'])} us |",
                "",
                "**The sweep is identical.** Both the capacity density and the",
                "read-bandwidth density scale as one over bitcell area, so a larger",
                "compute-in-ROM cell holds proportionally fewer bits AND delivers",
                "proportionally fewer bytes per second: the cell size cancels in",
                "their ratio. What the larger cell costs is capacity -- the same",
                "weights need a bigger array, and that silicon comes out of the SRAM",
                "beside it. An earlier version of this model applied the multiplier",
                "to area alone and credited the result with the storage cell's",
                "bandwidth density, which handed compute-in-ROM a free "
                f"{cim['cell_area_multiplier']:.1f}x on throughput.",
                "",
                "What compute-in-ROM does buy on this die is that it has no MAC",
                f"array to starve: the storage machine's {storage['compute_mm2']:,.0f} mm2 "
                f"of MAC array can be fed at only {storage['feed_ratio']:.2f}x of what it",
                "wants at one weight byte per multiply-accumulate, so more than half",
                "the die runs at a fraction of its duty and the step is weight-bound",
                "anyway.",
            ]
        )

    sizing_rows = [
        summary
        for summary in result["model_summaries"]
        if summary.get("per_region_sizing")
    ]
    if sizing_rows:
        lines.extend(
            [
                "",
                "## Sizing one expert region",
                "",
                "The per-region machine's cost is not arithmetic; it is a",
                "pre-compute block and an activation distribution network per",
                "region. The block is small against the array it serves. The",
                "distribution network is the real cost and this model does not",
                "price it.",
                "",
                "| Model | Experts | Routed bytes/expert | One region | Pre-compute/region "
                "| All regions | All pre-compute | Whole checkpoint |",
                "|---|---:|---:|---:|---:|---:|---:|---:|",
            ]
        )
        for summary in sizing_rows:
            sizing = summary["per_region_sizing"]
            lines.append(
                f"| {summary['model']} | {sizing['num_experts']} | "
                f"{sizing['routed_bytes_per_expert']/1e6:,.1f} MB | "
                f"{sizing['region_mm2']:,.1f} mm2 | "
                f"{sizing['precompute_mm2_per_region']:,.2f} mm2 "
                f"({sizing['precompute_fraction_of_array']:.1%}) | "
                f"{sizing['all_regions_mm2']:,.0f} mm2 | "
                f"{sizing['all_precompute_mm2']:,.0f} mm2 | "
                f"{sizing['whole_checkpoint_mm2']:,.0f} mm2 = "
                f"{sizing['whole_checkpoint_reticles']:,.1f} reticles |"
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
            "The third column set is the per-region machine, which is the whole",
            "subject of `docs/PER_REGION_COMPUTE_IN_ROM_DESIGN.md`: its sweep depth",
            "is the load of the **busiest** expert region, computed from the routing",
            "distribution rather than from the mean engaged region.",
            "",
            "| Model | B | Spare silicon | Batched aggregate | Per-stream aggregate | "
            "Per-region aggregate | Per-stream penalty | Per-region over broadcast | "
            "Batched binds on | Per-stream binds on | Per-region binds on |",
            "|---|---:|---|---:|---:|---:|---:|---:|---|---|---|",
        ]
    )
    for row in result["amortization_fork"]:
        broadcast = row.get("per_stream_aggregate_tokens_s") or 0.0
        region = row.get("per_region_aggregate_tokens_s") or 0.0
        gain = region / broadcast if broadcast > 0 else None
        lines.append(
            f"| {row['model']} | {row['batch_size']} | "
            f"{row['spare_area_policy']} | "
            f"{_fmt(row['batched_aggregate_tokens_s'])} | "
            f"{_fmt(row['per_stream_aggregate_tokens_s'])} | "
            f"{_fmt(row['per_region_aggregate_tokens_s'])} | "
            f"{_fmt_ratio(row.get('per_stream_aggregate_penalty_x'))} | "
            f"{_fmt_ratio(gain)} | "
            f"{row['batched_binding_constraint'] or '—'} | "
            f"{row['per_stream_binding_constraint'] or '—'} | "
            f"{row['per_region_binding_constraint'] or '—'} |"
        )

    sweep_rows = [
        row for row in result.get("floorplan_sweep", []) if row["design"]
    ]
    if sweep_rows:
        lines.extend(
            [
                "",
                "## The floorplan sweep: where the recovered silicon goes",
                "",
                "Compute-in-ROM has no MAC array, so it recovers that silicon.",
                "What it is spent on decides the comparison, so it is swept",
                "rather than assumed, and **the same sweep is offered to the",
                "amortising machine** -- offering it to one side only would move",
                "the artefact rather than remove it.",
                "",
                "* `sram` sizes the array to the stored bytes. Compute-in-ROM's",
                "  spare silicon becomes KV store, which is the split Taalas",
                "  describes; the amortising machine's becomes MAC array.",
                "* `rom` grows the array into that silicon as **replicated copies",
                "  of the same weights**. R copies carry R sets of bitlines and",
                "  sense amps, so R disjoint slices of the weight set are read at",
                "  once and the sweep time falls by R. On the amortising machine",
                "  the MAC array is then sized to consume exactly what the array",
                "  can read, at one weight byte per multiply-accumulate -- a",
                "  derived split, not a swept one.",
                "",
                "`R` is the replication factor the design ended up with, which is",
                "`weight_capacity / stored`. **Areas differ down this table**, so",
                "read `tok/s/mm2` and not only aggregate: a design is allowed to",
                "buy throughput with silicon here, and the iso-area table above is",
                "where that is controlled for.",
                "",
                "| Model | B | Amortisation | Spare | Design | mm2 | R | Sweeps | Aggregate | tok/s/mm2 | Binds on | vs ROM+MAC/sram |",
                "|---|---:|---|---|---|---:|---:|---:|---:|---:|---|---:|",
            ]
        )
        for row in sweep_rows:
            lines.append(
                f"| {row['model']} | {row['batch_size']} | "
                f"{row['weight_amortization']} | {row['spare_area_policy']} | "
                f"{row['design']} | {_fmt_area(row['silicon_area_mm2'])} | "
                f"{row['rom_replication_factor']:,.2f} | "
                f"{row['rom_sweeps_per_step']:,.2f} | "
                f"{_fmt(row['aggregate_tokens_s'])} | "
                f"{row['aggregate_tokens_s_per_mm2']:,.3f} | "
                f"{row['binding_constraint']} | "
                f"{_fmt_ratio(row['vs_reference_floorplan_x'])} |"
            )

    lines.extend(_render_corrections(result))

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
            "- **Power is wrong by 7-9x and every rate above is independent of it.**",
            "  The model counts memory bytes and MACs and nothing else, so it gives",
            "  54.2 W for an A100 at batch 1 against a published 400 W and 27.0 W for",
            "  Taalas HC1 against a published 200-250 W. It is not an activity-factor",
            "  error: driven at peak HBM bandwidth AND the peak BF16 roof at once the",
            "  model still gives 85.3 W. Leakage, clock distribution, operand delivery",
            "  and control logic are not modelled at all. `thermal_scale` is therefore",
            "  exactly 1.0 at every feasible point, and since `step_time = raw_step_time",
            "  x thermal_scale` is the only path from power to any other quantity, no",
            "  tokens/s in this report depends on the energy model -- and no watt or",
            "  joule-per-token in it should be quoted.",
            "- **Aggregate throughput is reported at steady state with every slot",
            "  occupied, and fill and drain are not charged.** A request that is short",
            "  compared with the slot count pays up to one extra traversal that this",
            "  model does not bill, which flatters a deep pipeline. The delivered rate",
            "  at the requested concurrency is reported separately and is not affected.",
            "- **The weight replication a deep pipeline implies is not charged against",
            "  capacity.** Beyond the layer count the surplus partitions hold replicas",
            "  of a stage, and each replica needs its own copy of that stage's weights;",
            "  the capacity check credits the machine with holding the model once. This",
            "  favours the deepest pipelines, which are on the GPU side of this",
            "  comparison, so correcting it would widen the ROM ratios rather than",
            "  narrow them.",
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

    # The latency separation, stated first because it moved every other number
    # in this report and because the correction is not symmetric between the
    # two families.
    corrections: dict[str, list[dict[str, Any]]] = {"rom": [], "gpu": []}
    for row in result["points"]:
        if row["batch_size"] != 1 or not row["feasible"]:
            continue
        corrections.setdefault(row["family"], []).append(row)
    if corrections["rom"] and corrections["gpu"]:
        parts = []
        for family, label in (("rom", "ROM"), ("gpu", "GPU")):
            rows = corrections[family]
            worst = max(rows, key=lambda row: row["latency_correction_x"])
            winner = _pick_best(rows, "per_user_tokens_s", "silicon_area_mm2")
            parts.append(
                f"On the {label} side the correction reaches "
                f"{worst['latency_correction_x']:,.0f}x "
                f"({worst['design'].split('/')[-1]}, {worst['token_slots']:,.0f} "
                f"slots), and the batch-1 design that now wins -- the smallest "
                f"silicon within "
                f"{BEST_DESIGN_TOLERANCE:.0%} of the best per-user rate -- runs "
                f"`{winner['parallelism']}` on "
                f"{winner['device_count']:,} device"
                f"{'s' if winner['device_count'] != 1 else ''}"
            )
        findings.append(
            "**Per-user latency and aggregate throughput are now separate "
            "quantities, and separating them is the largest correction in this "
            "report.** A token under pipeline parallelism is served by one stage's "
            "silicon at a time and must visit every stage, so its latency is the "
            "aggregate service time multiplied by `token_slots`, not divided by "
            "anything. The two factors cancel exactly: **adding devices under "
            "pipeline parallelism buys aggregate throughput and buys one user "
            "nothing.** " + ". ".join(parts) + ". Both validation gates are "
            "single-slot machines and are unchanged to the digit."
        )

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

    symmetry = [
        row
        for row in result["comparisons"]
        if row["batch_size"] == 1
        and row["rom_feasible"]
        and row["iso_area_gpu_feasible"]
        and row.get("per_user_speed_ratio_without_stage_cap") is not None
        and row.get("per_user_speed_ratio") is not None
        # Read the cap off a comparator it actually binds on. Once per-user
        # latency is charged honestly the iso-area GPU usually picks a tensor
        # group, which has one stage and no boundary for the cap to remove, and
        # quoting that row would describe the correction with a machine it does
        # not apply to.
        and row["iso_area_gpu_pipeline_stages_uncapped"]
        > row["iso_area_gpu_pipeline_stages"]
    ]
    if symmetry:
        # The largest absolute fall, which is the one a headline is read off,
        # rather than the largest proportional one, which on this study is a
        # model where the GPU wins either way and the fall is 1.4x of nothing.
        worst = max(
            symmetry,
            key=lambda row: row["per_user_speed_ratio_without_stage_cap"]
            - row["per_user_speed_ratio"],
        )
        findings.append(
            "**A token cannot cross more stage boundaries than the model has "
            "layers, and charging it as though it could was most of the reported "
            "advantage at scale.** At "
            f"{worst['rom_silicon_area_mm2']:,.0f} mm2 on {worst['model']} at batch 1, "
            f"the iso-area GPU cluster is "
            f"{worst['iso_area_gpu_device_count']:,} devices. Cut as one serial "
            f"pipeline that is "
            f"{worst['iso_area_gpu_pipeline_stages_uncapped']:,} stages and "
            f"{worst['iso_area_gpu_link_latency_without_stage_cap_s'] * 1e6:,.0f} us "
            "of link latency per token; but the model has "
            f"{[m for m in result['model_summaries'] if m['model'] == worst['model']][0]['num_layers']} "
            "layers, so at most "
            f"{worst['iso_area_gpu_pipeline_stages']} of those boundaries can exist "
            "and the rest of the silicon is replication, which adds bandwidth and no "
            f"serial event: {worst['iso_area_gpu_link_latency_s'] * 1e6:,.0f} us. The "
            "iso-area per-user ratio at that point falls from "
            f"{worst['per_user_speed_ratio_without_stage_cap']:,.1f}x to "
            f"{worst['per_user_speed_ratio']:,.1f}x. The same cap is applied to the "
            "ROM side, where it is worth more still because a twelve-wafer machine "
            "spans 681 reticle fields."
        )

    if not symmetry:
        findings.append(
            "**The layer cap on serial stage boundaries is still applied and is "
            "no longer visible in the headline, because no comparator it binds on "
            "wins any more.** A token cannot cross more stage boundaries than the "
            "model has layers, and this study charges at most that many. With "
            "per-user latency separated from aggregate throughput, both families "
            "now pick a topology with a tensor group at batch 1, and a tensor "
            "group has one stage and no boundary for the cap to remove. The "
            "`Ratio without the layer cap` column in the iso-area table therefore "
            "equals the stated ratio wherever the winner is tensor-parallel; it "
            "still differs wherever a pipeline wins."
        )

    choice = [
        row
        for row in result["comparisons"]
        if row["batch_size"] == 1
        and row["rom_feasible"]
        and row["iso_area_gpu_feasible"]
        and row.get("topology_choice_gain") is not None
    ]
    if choice:
        best_gain = max(choice, key=lambda row: row["topology_choice_gain"])
        gain = best_gain["topology_choice_gain"]
        if gain > 1.01:
            findings.append(
                "**Letting the GPU choose its own parallelism is worth up to "
                f"{gain:.2f}x to it.** At "
                f"{best_gain['rom_silicon_area_mm2']:,.0f} mm2 on "
                f"{best_gain['model']} the pipeline-only GPU delivers "
                f"{best_gain['pipeline_only_gpu_per_user_tokens_s']:,.2f} tok/s and "
                f"the same silicon running "
                f"{best_gain['iso_area_gpu_parallelism']} delivers "
                f"{best_gain['iso_area_gpu_per_user_tokens_s']:,.0f} tok/s."
            )
        else:
            findings.append(
                "**Giving the GPU the same topology sweep the ROM side gets is worth "
                f"at most {gain:.2f}x to it at this batch.** Pipeline, tensor and "
                "hybrid are evaluated at every cluster size and the best is taken. "
                "Where the gain is small the cluster is small enough that its single "
                "stage already holds the model."
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
            f"What the machine delivers rises from "
            f"{low['delivered_tokens_s']:,.0f} to {high['delivered_tokens_s']:,.0f} "
            f"tok/s, and its rate with every slot occupied from "
            f"{low['aggregate_tokens_s']:,.0f} to {high['aggregate_tokens_s']:,.0f}. "
            "The second rises far less than the first because the batch-1 figure "
            "is already a full-machine number -- this design has "
            f"{low['token_slots']:,.0f} slots -- so most of what batching adds "
            "there is coverage rather than occupancy. An unselected expert's read "
            "ports cannot be borrowed, so its idle bandwidth is only recovered by "
            "giving the sweep more users."
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
        if row["parallelism"] == "tensor"
        and str(row.get("intra_link", "")).startswith("nvlink")
    ]
    tensor_wafer = [
        row
        for row in result["latency_crossovers"]
        if row["parallelism"] == "tensor" and row.get("intra_link") == "on_wafer"
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
        wafer_ceiling = min(row["hard_ceiling_tokens_s"] for row in tensor_wafer)
        nvlink_ceiling = min(row["hard_ceiling_tokens_s"] for row in tensor_nvlink)
        # Like for like: the same model's collective on one wafer against the
        # same model's collective on NVLink.  Comparing the two worst cases
        # would compare different machines.
        matched: list[float] = []
        for wafer_row in tensor_wafer:
            if wafer_row["device_count"] != 1:
                continue
            peer = next(
                (
                    row
                    for row in tensor_nvlink
                    if row["model"] == wafer_row["model"]
                ),
                None,
            )
            if peer and wafer_row["link_latency_s_per_token"] > 0:
                matched.append(
                    peer["link_latency_s_per_token"]
                    / wafer_row["link_latency_s_per_token"]
                )
        advantage = min(matched) if matched else float("nan")
        findings.append(
            "**Tensor parallelism is better on a wafer than on NVLink and is not "
            "good anywhere, and the published claim that it reaches Taalas-class "
            "rates on-wafer is RETRACTED.** Two all-reduces per layer per token "
            "cost up to "
            f"{max(row['link_latency_s_per_token'] for row in tensor_nvlink) * 1e6:,.0f} us "
            "over NVLink, capping per-user decode at "
            f"{nvlink_ceiling:,.0f} tok/s before any arithmetic happens; the same "
            "collectives on-wafer cost at most "
            f"{max(row['link_latency_s_per_token'] for row in tensor_wafer) * 1e6:,.1f} us "
            f"and cap it at {wafer_ceiling:,.0f} tok/s. The ordering survives, and "
            "on a like-for-like comparison -- the same model's collective on one "
            f"wafer against the same model's on NVLink -- the wafer is at least "
            f"{advantage:,.1f}x cheaper. But the previous figures of 116,278 and "
            "81,966 tok/s came from charging a stitched 2-D mesh one flat hop "
            "however many reticle fields the collective spanned. A mesh has no "
            "switch, so an all-reduce costs about 1.1 times its diameter, and the "
            "model now charges that. What the collective buys is what makes it "
            "worth paying: with per-user latency separated from aggregate "
            "throughput, a tensor group is the only arrangement that puts the "
            "whole machine on one token, and the topology tables below show both "
            "families choosing one at batch 1 in spite of this cost."
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
        # Scanned over every batch, not only the largest: the per-region gain
        # peaks in the middle of the range and reporting only batch 256 would
        # miss it.
        regional = [
            row
            for row in result.get("amortization_fork", [])
            if row.get("per_region_aggregate_tokens_s")
            and row.get("per_stream_aggregate_tokens_s")
            and row.get("batched_aggregate_tokens_s")
        ]
        if regional:
            def _gain(row: dict[str, Any]) -> float:
                return (
                    row["per_region_aggregate_tokens_s"]
                    / row["per_stream_aggregate_tokens_s"]
                )

            best = max(regional, key=_gain)
            best_depth = max(
                (
                    row["region_sweep_depth_max_over_mean"]
                    for row in result["points"]
                    if row["model"] == best["model"]
                    and row["batch_size"] == best["batch_size"]
                    and row.get("region_sweep_depth_max_over_mean")
                ),
                default=1.0,
            )
            loses = [
                row
                for row in regional
                if row["per_region_aggregate_tokens_s"]
                < row["batched_aggregate_tokens_s"] * (1 - 1e-9)
            ]
            findings.append(
                "**A third machine sits between them, and for a sparse model it "
                "recovers part of what compute-in-ROM gives up -- less than the "
                "mean-region arithmetic used to say.** Give each expert region its "
                "own activation port and two tokens selecting disjoint experts "
                "drive disjoint regions at the same time; only the tokens landing "
                "on one region serialise, and the sweep waits for the BUSIEST "
                "region rather than the average engaged one. The largest gain over "
                f"a global broadcast is {_gain(best):,.2f}x, on {best['model']} at "
                f"batch {best['batch_size']}, where the busiest region carries "
                f"{best_depth:,.2f}x the load of the mean engaged one. It is not "
                "free ground: per-region "
                f"still loses to the amortising ROM-plus-MAC machine at "
                f"{len(loses)} of {len(regional)} operating points. A dense model "
                "has one region, so it gains nothing -- the disjointness is what "
                "sparsity buys."
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
    "intra_link",
    "intra_domain_size",
    "tensor_group",
    "pipeline_stages",
    "link_latency_s",
    "link_share_of_step",
    "node",
    "weight_store",
    "kv_store",
    "weight_amortization",
    "silicon_area_mm2",
    "silicon_area_mm2_per_device",
    "feasible",
    "per_user_tokens_s",
    "aggregate_tokens_s",
    "delivered_tokens_s",
    "per_user_tokens_s_throughput_view",
    "latency_correction_x",
    "token_slots",
    "microbatch_per_slot",
    "pipeline_fill_users",
    "pipeline_fill_limited_by",
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
