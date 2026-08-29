"""Qwen3-8B immutable-ROM lowering for a conventional single chip.

Physical boundary
-----------------

``TopologyClass.SINGLE_CHIP``: one reticle-bounded accelerator chip/package.
There is no stage pipeline, no wafer fabric and no second die.  All 36 decoder
layers are simultaneously resident in mask ROM; nothing is "loaded" per layer.

The on-chip partition: role-striped banks, not per-layer images
--------------------------------------------------------------

The retained builder (``compiler/qwen3/deployment.py``) emitted 36 per-layer ROM
image files.  This backend deliberately does **not** inherit that split, and the
reason is a floorplan reason rather than a file-management one.

The 36-file split was an artifact of the ABI 2.5 *stage pipeline*, where one
physical stage held one layer's weights at a time and the image file was the
unit of residency.  On a conventional single chip nothing is ever swapped, so
"one image per layer" names no physical object.  What does name a physical
object is the ROM **bank**: a macro array with its own row decoder, sense path,
column multiplexer and redundancy.  So the partition this backend emits is

    one ROM bank per weight *role*, striped across the 36 layers,

which the region planner produces mechanically as one region per
(layer-run, body position, operand slot).  For the released Qwen3-8B graph that
is 14 banks: 11 per-layer roles (q/k/v/o projections, q/k head norms, the two
RMSNorm weights, and gate/up/down) plus the embedding table, the final norm and
the untied LM head.

Three consequences follow, and they are the justification:

1.  **Operand concurrency.**  One decoder layer reads seven large operands
    (q, k, v, o, gate, up, down).  Under a per-layer partition all seven live in
    one array and their reads serialise behind one row decoder and one sense
    amplifier bank.  Under role striping each operand stream has its own bank,
    so the datapath can hold one operand open while the next bank precharges.
    The tensor-lane count, not the ROM, then sets the roof.

2.  **Array regularity and area.**  Role striping gives 36 identical row groups
    inside one array per role, so a role bank is a single rectangular macro with
    one row-decoder depth (36 x per-layer rows) and one column width.  A
    per-layer partition gives 36 differently shaped arrays whose periphery --
    decoders, sense amps, repair muxes -- is replicated 36 times.  Periphery is
    the part of a ROM macro that does not scale with density, so replicating it
    36 times is the expensive choice on a reticle-bounded die.

3.  **Repair sharing.**  Row and column redundancy is provisioned per array.
    With role striping, one spare row set covers that role for every layer;
    with a per-layer split each of the 36 arrays needs its own spare inventory,
    and a defect in layer 7's array cannot be repaired from layer 8's unused
    spares.  :func:`compiler.backends.rom.common.image.plan_repair_map` prices
    exactly this.

The layer index becomes the high bits of the ROM row address inside a role
bank.  In ABI 3.0 terms that is one tensor view carrying
``DynamicTerm.loop(layer_loop, per_layer_elements)``, which is what makes the
program 36x smaller than the kernel list.

Reticle-area accounting
-----------------------

:func:`qwen3_area_accounting` records what the mandated single-chip boundary
costs, from the anchors in ``configs/hardware/technology_inputs.json``.  It is
reported, never asserted: the ABI-level check this backend *does* enforce is
that the planned ROM bytes fit the ROM capacity the capability declares.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from compiler.ir.v3.kernel_ir import KernelGraph
from runtime.abi3.capability import Capability
from runtime.abi3.constants import Feature, StorageClass, TopologyClass
from runtime.abi3.deployment import Deployment

from .common.image import (
    DefectRecord,
    RomCoordinate,
    RomImagePlan,
    RomLayoutPolicy,
)
from .common.program import RomLowering, RomTargetPolicy

PRODUCT = "qwen3-8b-rom"
TARGET_ID = "qwen3-8b-rom-single-chip"
BACKEND = "rom.single_chip"

#: Declared ROM capacity of the single Qwen ROM chip.  16 GiB holds the pinned
#: 16,381,470,720-byte checkpoint plus alignment padding and leaves the rest for
#: integrity and repair reserve.
ROM_CAPACITY_BYTES = 1 << 34
#: On-die SRAM for activations, accumulators and the vocabulary reduction.
SRAM_BYTES = 128 << 20
#: External HBM for the 36-layer KV state, token buffers and activation spill.
HBM_BYTES = 96 << 30

#: ROM macro row.  A region base is a row address, so alignment == row.
ROM_ROW_BYTES = 4096
#: Bytes one ROM bank may hold.  Role banks are per-operand, and the largest
#: Qwen role bank (gate/up/down over 36 layers) is about 3.6 GB.
BANK_BYTES = 1 << 33

#: Maximum reticle field a single conventional exposure covers, 26 mm x 33 mm.
RETICLE_FIELD_MM2 = 26.0 * 33.0
#: ROM share of that field and the usable fraction after periphery, repair
#: reserve and fragmentation, from the "central" leading-node envelope in
#: ``configs/hardware/technology_inputs.json``.
ROM_AREA_FRACTION = 0.48
USABLE_ROM_FRACTION = 0.86
#: Published density anchors, in bytes per mm^2.
FABRICATED_28NM_BYTES_MM2 = 8.928e6 / 8.0
PUBLISHED_3D_METAL_BYTES_MM2 = 20.7e6

NUMERIC_CONTRACTS = (
    "bf16_add_rne_v1",
    "bf16_bf16_fp32_sequential_rne_v1",
    "bf16_byte_preserving_state_v1",
    "bf16_payload_lookup_v1",
    "exact_index_select_v1",
    "exact_token_append_eos_v1",
    "greedy_lowest_token_id_argmax_v1",
    "qwen3_gqa_fp32_softmax_bf16_v1",
    "qwen3_rmsnorm_fp32_bf16_v1",
    "qwen3_rope_fp32_bf16_v1",
    "qwen3_silu_mul_bf16_v1",
)

FEATURES = (
    Feature.HOST_QUEUE_ABI,
    Feature.DEPLOYMENT_DESCRIPTOR_ABI,
    Feature.DETERMINISTIC_MICROSEQUENCER,
    Feature.BF16_TENSOR,
    Feature.TRANSACTIONAL_STATE,
    Feature.ON_DEVICE_SELECTION,
    Feature.INTEGRITY_RETRY,
)


class Qwen3RomError(ValueError):
    """Raised when the Qwen graph will not fit the single-chip ROM boundary."""


def qwen3_rom_capability(
    *,
    max_context_positions: int = 8192,
    vocabulary_size: int = 151936,
    rom_bytes: int = ROM_CAPACITY_BYTES,
) -> Capability:
    """The exact limits of the Qwen ROM chip this backend compiles for."""
    capability = Capability(
        capability_id="",
        topology_class=int(TopologyClass.SINGLE_CHIP),
        features=tuple(int(f) for f in FEATURES),
        limits={
            "max_instructions": 4096,
            "max_descriptors": 16384,
            "max_loop_depth": 4,
            "max_loop_trip": 4096,
            "max_retired_work": 1 << 24,
            "max_events": 256,
            "max_outstanding_per_queue": 16,
            "max_context_positions": max_context_positions,
            "max_expert_ids": 1,
            "max_topk": 1,
            "max_vocabulary": vocabulary_size,
            "max_sessions": 8,
            "max_nodes": 1,
        },
        numeric_contracts=NUMERIC_CONTRACTS,
        engines={
            "tensor": {"lanes": 512, "queues": 2},
            "vector": {"lanes": 256, "queues": 2},
            "attention": {"lanes": 128, "queues": 1},
            "dma": {"queues": 2},
            "reduction": {"lanes": 128, "queues": 1},
            "selection": {"queues": 1},
            "state": {"queues": 1},
        },
        memory={
            "rom": {"bytes": rom_bytes, "banks": 16},
            "sram": {"bytes": SRAM_BYTES, "banks": 32},
            "hbm": {"bytes": HBM_BYTES},
        },
        technology_view="single_chip_rom_declared_v1",
    )
    capability.validate()
    return capability


def qwen3_layout_policy(*, alignment_bytes: int = ROM_ROW_BYTES) -> RomLayoutPolicy:
    return RomLayoutPolicy(
        alignment_bytes=alignment_bytes,
        row_bytes=ROM_ROW_BYTES,
        resource_bytes=BANK_BYTES,
        spare_row_fraction=0.01,
        minimum_spare_rows=8,
        spare_columns_per_bank=8,
        base_address=0,
    )


def _place_region(key: str, role: str, index: int, size_bytes: int) -> RomCoordinate:
    """One ROM bank per region: role striping is the bank partition."""
    return RomCoordinate(node_id=0, reticle=0, tile=0, bank=index)


def qwen3_area_accounting(rom_bytes: int) -> dict[str, Any]:
    """What the mandated single-chip boundary demands of ROM density.

    Reported, never asserted.  The compiler's ABI-level obligation is capacity
    against the declared capability; whether a reticle-bounded die can hold that
    capacity at a given node is a foundry gate, and the published anchors here
    say plainly that it is not closed.
    """
    usable_mm2 = RETICLE_FIELD_MM2 * ROM_AREA_FRACTION * USABLE_ROM_FRACTION
    required = rom_bytes / usable_mm2 if usable_mm2 else 0.0
    return {
        "closes_against_fabricated_28nm_anchor": required
        <= FABRICATED_28NM_BYTES_MM2,
        "closes_against_published_3d_metal_evaluation": required
        <= PUBLISHED_3D_METAL_BYTES_MM2,
        "evidence": (
            "reticle field 26x33 mm; ROM area fraction and usable fraction from the "
            "'central' leading-node envelope in configs/hardware/"
            "technology_inputs.json; density anchors are the fabricated 28 nm "
            "8.928 Mbit/mm^2 macro and the published 3D-metal ROM evaluation"
        ),
        "fabricated_28nm_bytes_per_mm2": FABRICATED_28NM_BYTES_MM2,
        "published_3d_metal_bytes_per_mm2": PUBLISHED_3D_METAL_BYTES_MM2,
        "reticle_field_mm2": RETICLE_FIELD_MM2,
        "required_usable_density_bytes_per_mm2": required,
        "rom_bytes": rom_bytes,
        "status": "declared_input_not_a_closed_physical_result",
        "usable_rom_area_mm2": usable_mm2,
    }


def _topology(builder, plan: RomImagePlan) -> int:
    repair = plan.repair_map
    return builder.topology(
        topology_class=TopologyClass.SINGLE_CHIP,
        node_count=1,
        reticle_count=1,
        tiles_per_reticle=1,
        local_node_id=0,
        local_reticle_id=0,
        local_tile_id=0,
        link_class_count=0,
        active_resource_count=len(repair.active_resources),
        quarantined_resource_count=len(repair.quarantine),
        hbm_bytes_per_node=HBM_BYTES,
        sram_bytes_per_node=SRAM_BYTES,
        link_count=0,
        route_group_count=0,
        epoch=1,
        bisection_link_count=0,
        active_resource_digest=repair.active_resource_digest,
        quarantine_digest=repair.quarantine_digest,
        health_digest=repair.health_digest,
        key="topology",
    )


def qwen3_rom_policy(
    *,
    defects: Sequence[DefectRecord] = (),
    alignment_bytes: int = ROM_ROW_BYTES,
    sram_budget_bytes: int = SRAM_BYTES,
    notes: Mapping[str, Any] | None = None,
) -> RomTargetPolicy:
    return RomTargetPolicy(
        product=PRODUCT,
        target_id=TARGET_ID,
        backend=BACKEND,
        topology_class=TopologyClass.SINGLE_CHIP,
        layout=qwen3_layout_policy(alignment_bytes=alignment_bytes),
        sram_budget_bytes=sram_budget_bytes,
        tile_rows=128,
        tile_cols=128,
        tile_depth=128,
        defects=tuple(defects),
        features=FEATURES,
        place_region=_place_region,
        emit_topology=_topology,
        link_plan=None,
        notes={
            "partition": "role_striped_rom_banks",
            "partition_rationale": (
                "one ROM bank per weight role striped across layers; the 36 "
                "per-layer images of the ABI 2.5 stage pipeline name no object on "
                "a conventional single chip"
            ),
            "physical_chip_count": 1,
            **dict(notes or {}),
        },
    )


def build_qwen3_rom_deployment(
    graph: KernelGraph,
    *,
    capability: Capability | None = None,
    defects: Sequence[DefectRecord] = (),
    weight_storage_class: StorageClass = StorageClass.ROM,
    alignment_bytes: int = ROM_ROW_BYTES,
    notes: Mapping[str, Any] | None = None,
) -> tuple[Deployment, RomImagePlan]:
    """Lower ``graph`` onto the conventional single-chip Qwen ROM target."""
    capability = capability or qwen3_rom_capability()
    policy = qwen3_rom_policy(
        defects=defects, alignment_bytes=alignment_bytes, notes=notes
    )
    lowering = RomLowering(
        graph, capability, policy, weight_storage_class=weight_storage_class
    )
    plan = lowering.plan_regions()
    declared = int(capability.memory["rom"]["bytes"])
    if plan.rom_bytes > declared:
        raise Qwen3RomError(
            f"the Qwen ROM image needs {plan.rom_bytes} bytes but the single-chip "
            f"capability declares {declared}; a second chip is not an option for "
            "this product"
        )
    lowering.builder.notes["rom_area_accounting"] = qwen3_area_accounting(
        plan.rom_bytes
    )
    lowering.builder.notes["rom_capacity"] = {
        "declared_rom_bytes": declared,
        "largest_bank_bytes": plan.largest_region_bytes,
        "planned_rom_bytes": plan.rom_bytes,
        "rom_bank_count": plan.resource_count,
    }
    return lowering.build(), plan


__all__ = [
    "BACKEND",
    "PRODUCT",
    "Qwen3RomError",
    "ROM_CAPACITY_BYTES",
    "TARGET_ID",
    "build_qwen3_rom_deployment",
    "qwen3_area_accounting",
    "qwen3_layout_policy",
    "qwen3_rom_capability",
    "qwen3_rom_policy",
]
