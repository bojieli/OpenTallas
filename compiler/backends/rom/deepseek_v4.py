"""DeepSeek-V4-Flash immutable-ROM lowering for a wafer-scale logical device.

Physical boundary
-----------------

``TopologyClass.WAFER_LOGICAL_DEVICE`` is mandatory for this product, not a
capacity escape.  The compiled artifact is a reticle/tile ROM assembly on a
stitched on-wafer fabric with distributed HBM attachment, presented to the host
as **one** device: one deployment, one session, one event and transaction
namespace, one submission.  It is explicitly not a host-orchestrated collection
of ROM chips and not an off-package stage pipeline.

Wafer geometry, derived rather than inherited
---------------------------------------------

The historical ``spec/ARCHITECTURE.md`` proxy -- an 8x8 reticle grid and 4,096
tiles per stage -- is historical evidence and is *not* used here.  This backend
derives its own grid:

* the square usable field of a 300 mm wafer is taken from the published
  wafer-scale area in ``configs/hardware/technology_inputs.json``
  (46,225 mm^2, i.e. a 215 mm square);
* a reticle field is one conventional 26 mm x 33 mm exposure;
* the grid is therefore ``floor(215/26) = 8`` columns by ``floor(215/33) = 6``
  rows = **48 stitched reticle fields**, covering 41,184 mm^2 (89.1% of the
  square).  Note this is 8x6, not the historical 8x8.

A **tile** is the placement resource: one ROM bank complex plus its format
decode, MAC lanes, activation SRAM, switch endpoint and repair/BIST logic.  Tile
ROM capacity is declared (:data:`TILE_ROM_BYTES`) and chosen so that the largest
indivisible routed region -- one expert's three matrices, 12.75 MiB of MXFP4
payload plus E8M0 block scales -- fits one tile, which is what lets expert
dispatch enable exactly the tiles holding the selected experts.  Reticle and
tile counts in the emitted TOPOLOGY descriptor are then computed from the actual
region plan, never asserted.

What ABI 3.0 can and cannot carry
---------------------------------

The frozen TOPOLOGY payload carries counts, the local coordinate, an epoch and
four digests; it has no room for a per-tile coordinate array.  So the full
coordinate table -- every region's shard list of ``(node, reticle, tile, bank,
region offset, bytes, tile address)`` -- lives in the region plan, which the
deployment manifest binds by digest and which the topology descriptor's
``route_table_digest`` and ``active_resource_digest`` name.  That is a reported
contract shape, not a workaround: the bytes are still authenticated.
"""

from __future__ import annotations

import hashlib
from typing import Any, Mapping, Sequence

from compiler.ir.v3.kernel_ir import KernelGraph
from runtime.abi3.capability import Capability, canonical_json
from runtime.abi3.constants import (
    Feature,
    Link,
    ParticipantScope,
    StorageClass,
    TopologyClass,
)
from runtime.abi3.deployment import Deployment
from runtime.abi3.descriptors import CollectiveOp

from .common.image import (
    DefectRecord,
    RomCoordinate,
    RomImagePlan,
    RomLayoutPolicy,
)
from .common.program import LayerRun, LinkStep, RomLowering, RomTargetPolicy

PRODUCT = "deepseek-v4-flash-rom"
TARGET_ID = "deepseek-v4-flash-rom-wafer"
BACKEND = "rom.wafer_logical_device"

#: Published wafer-scale area and the square field it implies.
WAFER_AREA_MM2 = 46225.0
WAFER_SIDE_MM = 215.0
#: One conventional reticle exposure.
RETICLE_WIDTH_MM = 26.0
RETICLE_HEIGHT_MM = 33.0
RETICLE_FIELD_MM2 = RETICLE_WIDTH_MM * RETICLE_HEIGHT_MM

RETICLE_COLUMNS = int(WAFER_SIDE_MM // RETICLE_WIDTH_MM)
RETICLE_ROWS = int(WAFER_SIDE_MM // RETICLE_HEIGHT_MM)
MAX_RETICLES = RETICLE_COLUMNS * RETICLE_ROWS

#: ROM bytes one tile owns.  16 MiB holds the largest indivisible routed region
#: (one expert: 3 x 4096 x 2048 MXFP4 values = 12,582,912 payload bytes plus
#: 786,432 E8M0 block-scale bytes) with row alignment and repair reserve.
TILE_ROM_BYTES = 16 << 20
#: Tiles per reticle field.
TILES_PER_RETICLE = 256

#: ROM share of a reticle field and the usable fraction after periphery and
#: repair reserve, from the "central" leading-node envelope in
#: ``configs/hardware/technology_inputs.json``.
ROM_AREA_FRACTION = 0.48
USABLE_ROM_FRACTION = 0.86
FABRICATED_28NM_BYTES_MM2 = 8.928e6 / 8.0
PUBLISHED_3D_METAL_BYTES_MM2 = 20.7e6

ROM_ROW_BYTES = 4096

#: On-wafer SRAM and distributed HBM the logical device presents.
SRAM_BYTES = 8 << 30
HBM_BYTES = 1536 << 30

#: Link classes: intra-reticle mesh, inter-reticle stitched mesh, and the
#: HBM-attachment ring at the wafer/package boundary.
LINK_CLASS_COUNT = 3

# Compatibility support advertised by the wafer capability is distinct from
# the feature vector required by one program.  STATE is unused by the direct
# live-buffer profile, while packet integrity is required automatically when
# the builder sees the wafer's actual COMMUNICATION descriptors.
CAPABILITY_FEATURES = (
    Feature.HOST_QUEUE_ABI,
    Feature.DEPLOYMENT_DESCRIPTOR_ABI,
    Feature.DETERMINISTIC_MICROSEQUENCER,
    Feature.BF16_TENSOR,
    Feature.FP8_E4M3FN_TENSOR,
    Feature.MXFP4_E2M1_E8M0,
    Feature.TRANSACTIONAL_STATE,
    Feature.ON_DEVICE_SELECTION,
    Feature.WAFER_ENDPOINT,
    Feature.INTEGRITY_RETRY,
)

PROGRAM_FEATURES = (
    Feature.HOST_QUEUE_ABI,
    Feature.DEPLOYMENT_DESCRIPTOR_ABI,
    Feature.DETERMINISTIC_MICROSEQUENCER,
    Feature.BF16_TENSOR,
    Feature.FP8_E4M3FN_TENSOR,
    Feature.MXFP4_E2M1_E8M0,
    Feature.ON_DEVICE_SELECTION,
    Feature.WAFER_ENDPOINT,
)

NUMERIC_CONTRACTS = (
    "bf16_add_rne_v1",
    "bf16_bf16_fp32_sequential_rne_v1",
    "bf16_byte_preserving_state_v1",
    "bf16_payload_lookup_v1",
    "deepseek_v4_compress_fp32_bf16_v1",
    "deepseek_v4_hyper_connect_fp32_bf16_v1",
    "deepseek_v4_router_fp32_sigmoid_v1",
    "deepseek_v4_sparse_attention_fp32_softmax_v1",
    "exact_index_select_v1",
    "exact_token_append_eos_v1",
    "fp8_e4m3fn_fp8_e4m3fn_fp32_sequential_rne_v1",
    "greedy_lowest_token_id_argmax_v1",
    "mxfp4_e2m1_fp8_e4m3fn_fp32_blocked_rne_v1",
)


class DeepSeekV4RomError(ValueError):
    """Raised when the DeepSeek graph will not fit the wafer boundary."""


# ---------------------------------------------------------------------------
# Geometry
# ---------------------------------------------------------------------------
def wafer_geometry(
    *,
    tile_rom_bytes: int = TILE_ROM_BYTES,
    tiles_per_reticle: int = TILES_PER_RETICLE,
) -> dict[str, Any]:
    """The wafer grid this backend compiles for, derived from public anchors."""
    usable_rom_mm2 = RETICLE_FIELD_MM2 * ROM_AREA_FRACTION * USABLE_ROM_FRACTION
    reticle_rom_bytes = tile_rom_bytes * tiles_per_reticle
    return {
        "evidence": (
            "wafer area from the published wafer-scale figure in "
            "configs/hardware/technology_inputs.json; reticle field is one "
            "conventional 26x33 mm exposure; the 8x8 reticle and 4,096-tile proxy "
            "in spec/ARCHITECTURE.md is historical evidence and is not inherited"
        ),
        "grid_columns": RETICLE_COLUMNS,
        "grid_rows": RETICLE_ROWS,
        "max_reticles": MAX_RETICLES,
        "reticle_field_mm2": RETICLE_FIELD_MM2,
        "reticle_rom_bytes": reticle_rom_bytes,
        "required_usable_density_bytes_per_mm2": reticle_rom_bytes / usable_rom_mm2,
        "stitched_area_mm2": MAX_RETICLES * RETICLE_FIELD_MM2,
        "tile_rom_bytes": tile_rom_bytes,
        "tiles_per_reticle": tiles_per_reticle,
        "usable_rom_area_mm2_per_reticle": usable_rom_mm2,
        "wafer_area_mm2": WAFER_AREA_MM2,
        "wafer_rom_bytes": reticle_rom_bytes * MAX_RETICLES,
    }


def _advance(tiles_per_reticle: int):
    def advance(coordinate: RomCoordinate) -> RomCoordinate:
        tile = coordinate.tile + 1
        return RomCoordinate(
            node_id=coordinate.node_id,
            reticle=tile // tiles_per_reticle,
            tile=tile,
            bank=0,
        )

    return advance


class _WaferPlacer:
    """Sequential tile packing: regions fill tiles, tiles fill reticles."""

    def __init__(self, *, tile_rom_bytes: int, tiles_per_reticle: int, alignment: int):
        self.tile_rom_bytes = tile_rom_bytes
        self.tiles_per_reticle = tiles_per_reticle
        self.alignment = alignment
        self.cumulative = 0

    def __call__(
        self, key: str, role: str, index: int, size_bytes: int
    ) -> RomCoordinate:
        tile = self.cumulative // self.tile_rom_bytes
        aligned = (size_bytes + self.alignment - 1) // self.alignment * self.alignment
        self.cumulative += aligned
        return RomCoordinate(
            node_id=0,
            reticle=tile // self.tiles_per_reticle,
            tile=tile,
            bank=0,
        )


def deepseek_v4_layout_policy(
    *,
    tile_rom_bytes: int = TILE_ROM_BYTES,
    tiles_per_reticle: int = TILES_PER_RETICLE,
    alignment_bytes: int = ROM_ROW_BYTES,
) -> RomLayoutPolicy:
    return RomLayoutPolicy(
        alignment_bytes=alignment_bytes,
        row_bytes=ROM_ROW_BYTES,
        resource_bytes=tile_rom_bytes,
        spare_row_fraction=0.02,
        minimum_spare_rows=4,
        spare_columns_per_bank=8,
        base_address=0,
        advance_resource=_advance(tiles_per_reticle),
    )


# ---------------------------------------------------------------------------
# Capability
# ---------------------------------------------------------------------------
def deepseek_v4_rom_capability(
    *,
    max_context_positions: int = 262144,
    vocabulary_size: int = 129280,
    expert_count: int = 256,
    experts_per_token: int = 6,
    tile_rom_bytes: int = TILE_ROM_BYTES,
    tiles_per_reticle: int = TILES_PER_RETICLE,
) -> Capability:
    """The exact limits of the wafer-scale logical accelerator."""
    geometry = wafer_geometry(
        tile_rom_bytes=tile_rom_bytes, tiles_per_reticle=tiles_per_reticle
    )
    capability = Capability(
        capability_id="",
        topology_class=int(TopologyClass.WAFER_LOGICAL_DEVICE),
        features=tuple(int(f) for f in CAPABILITY_FEATURES),
        limits={
            "max_instructions": 8192,
            "max_descriptors": 65536,
            "max_loop_depth": 4,
            "max_loop_trip": 4096,
            "max_retired_work": 1 << 26,
            "max_events": 512,
            # Shared RTL 3.0 implements a 1,024-entry event scoreboard.  This
            # program still admits at most 512 distinct IDs, but its legal ID
            # space matches the common microsequencer implementation.
            "max_event_id": 1023,
            "max_outstanding_per_queue": 32,
            "max_context_positions": max_context_positions,
            "max_expert_ids": expert_count,
            "max_topk": max(experts_per_token, 8),
            "max_vocabulary": vocabulary_size,
            "max_sessions": 16,
            # One wafer-scale logical accelerator is ONE ABI node.
            "max_nodes": 1,
            # A22: the state slot file the sequencer holds for a transaction.
            # This lane declares ten STATE resources.
            "max_state_resources": 16,
        },
        numeric_contracts=NUMERIC_CONTRACTS,
        engines={
            "tensor": {"lanes": 8192, "queues": 4},
            "vector": {"lanes": 4096, "queues": 4},
            "attention": {"lanes": 2048, "queues": 2},
            "route": {"lanes": 512, "queues": 2},
            "reduction": {"lanes": 2048, "queues": 2},
            "dma": {"queues": 4},
            "link": {"queues": 4},
            "selection": {"queues": 1},
            "state": {"queues": 2},
        },
        memory={
            "rom": {
                "bytes": geometry["wafer_rom_bytes"],
                "banks": geometry["max_reticles"] * tiles_per_reticle,
            },
            "sram": {"bytes": SRAM_BYTES, "banks": 4096},
            "hbm": {"bytes": HBM_BYTES},
        },
        link={
            "class_count": LINK_CLASS_COUNT,
            "reticle_columns": geometry["grid_columns"],
            "reticle_rows": geometry["grid_rows"],
            "tiles_per_reticle": tiles_per_reticle,
        },
        technology_view="wafer_logical_device_declared_v1",
    )
    capability.validate()
    return capability


#: Factories by published profile name.  See the note in
#: ``compiler/backends/rom/qwen3.py``: one source of truth per published
#: capability file, checked by ``tools/publish_abi3_capabilities.py --check``.
PROFILES = {"rom-deepseek-v4": deepseek_v4_rom_capability}


# ---------------------------------------------------------------------------
# Topology and fabric
# ---------------------------------------------------------------------------
def _route_table_digest(plan: RomImagePlan) -> bytes:
    """Bind the per-tile coordinate table the TOPOLOGY payload cannot hold."""
    body = {
        "schema": "opentallas.rom.wafer_route_table.v1",
        "shards": [
            [region.region_id, *shard.to_list()]
            for region in plan.regions
            for shard in region.shards
        ],
    }
    return hashlib.sha256(canonical_json(body)).digest()


def _wafer_topology_factory(
    *, tiles_per_reticle: int, tile_rom_bytes: int, epoch: int
):
    def emit(builder, plan: RomImagePlan) -> int:
        repair = plan.repair_map
        reticles = sorted(
            {shard.coordinate.reticle for r in plan.regions for shard in r.shards}
        )
        reticle_count = max(reticles) + 1 if reticles else 1
        if reticle_count > MAX_RETICLES:
            raise DeepSeekV4RomError(
                f"the region plan needs {reticle_count} reticle fields but the "
                f"wafer stitches {MAX_RETICLES}"
            )
        # Intra-reticle mesh plus the stitched inter-reticle mesh.  A 16x16 tile
        # mesh has 2*16*15 = 480 internal links; the reticle grid adds its own.
        side = int(round(tiles_per_reticle**0.5)) or 1
        intra = 2 * side * (side - 1) * reticle_count
        inter = (
            (RETICLE_COLUMNS - 1) * RETICLE_ROWS + RETICLE_COLUMNS * (RETICLE_ROWS - 1)
        ) * side
        return builder.topology(
            topology_class=TopologyClass.WAFER_LOGICAL_DEVICE,
            node_count=1,
            reticle_count=reticle_count,
            tiles_per_reticle=tiles_per_reticle,
            local_node_id=0,
            local_reticle_id=0,
            local_tile_id=0,
            link_class_count=LINK_CLASS_COUNT,
            active_resource_count=len(repair.active_resources),
            quarantined_resource_count=len(repair.quarantine),
            hbm_bytes_per_node=HBM_BYTES,
            sram_bytes_per_node=SRAM_BYTES,
            link_count=intra + inter,
            route_group_count=reticle_count,
            epoch=epoch,
            bisection_link_count=side * RETICLE_ROWS,
            active_resource_digest=repair.active_resource_digest,
            quarantine_digest=repair.quarantine_digest,
            route_table_digest=_route_table_digest(plan),
            health_digest=repair.health_digest,
            key="topology",
        )

    return emit


#: Route group a layer's on-fabric steps address.  ``route_group_count`` is the
#: reticle count, so group ``g`` is reticle ``g``'s tiles; the local endpoint is
#: ``local_reticle_id``, which the emitted topology sets to zero.
_LAYER_ROUTE_GROUP = 0

#: Numeric contract of the on-wafer expert all-reduce.  It is the graph's own
#: expert-reduction contract: the collective sums the same expert outputs the
#: EXPERT_REDUCE kernels sum, so it reduces under the same rule.
_COLLECTIVE_REDUCTION_CONTRACT = "dispatch_reduce_expert_outputs_bf16_v1"

#: Kinds that anchor an on-wafer collective.
_DISPATCH_KINDS = frozenset({"EXPERT_DISPATCH", "ROUTED_MATMUL"})
_GATHER_KINDS = frozenset(
    {"ATTENTION_SPARSE", "INDEX_TOPK", "INDEX_SCORE", "ATTENTION_GQA", "ATTENTION_DENSE"}
)
_REDUCE_KINDS = frozenset({"EXPERT_REDUCE", "PARTITION_SUM", "ORDERED_SUM"})


def _wafer_link_plan_factory(*, chunk_bytes: int):
    """The on-wafer critical path for one compressed layer body.

    Every step here is a LINK-family instruction against a COMMUNICATION
    descriptor with bounded credits, retries and timeout class.  Together they
    cover the six services the wafer contract requires: unicast, multicast,
    reduction, sparse gather, expert dispatch and a bounded barrier.  Nothing on
    this path is host-orchestrated: the authenticated device program issues all
    of it inside the layer loop.

    Every one of the five collectives is ``TILE``-scoped (amendment A14, wire
    format section 12.5).  The tile is this product's placement resource --
    :class:`_WaferPlacer` packs regions into tiles and tiles into reticles --
    and it is also the endpoint the wafer cycle model addresses
    (:class:`runtime.cycle.fabric.WaferFabric` counts its endpoints in tiles).
    Before A14 there was no way to say so: participants were counted in nodes,
    a ``WAFER_LOGICAL_DEVICE`` declares exactly one node, and every one of these
    five was therefore a collective over a single participant, which the LINK
    engine refuses as degenerate.

    Each one addresses **one reticle field's tiles**, through route group
    :data:`_LAYER_ROUTE_GROUP`.  The emitted topology already partitions the
    fabric that way -- ``route_group_count`` is the reticle count -- and the
    arithmetic says why: 156 GB of weights over 43 layers is about 3.6 GB a
    layer, and one reticle field is ``tiles_per_reticle * tile_rom_bytes`` =
    4 GiB, so a layer's weights occupy about one field.  The fabric a layer's
    activation, index gather, expert dispatch, expert reduction and barrier
    actually cross is therefore that field's tile mesh, and the fan-out is
    ``tiles_per_reticle``.  ``participant_count`` is derived from the admitted
    topology and the route group rather than asserted here.

    The residual unicast is not a collective: it is ``LINK.SEND`` between two
    tile endpoints, and it states those two endpoints itself.
    """

    def plan(run: LayerRun, kinds: Sequence[str]) -> list[LinkStep]:
        steps: list[LinkStep] = [
            LinkStep(
                position=0,
                where="before",
                link_sub=int(Link.MULTICAST),
                collective_op=int(CollectiveOp.BROADCAST),
                label="activation_multicast",
                participant_scope=ParticipantScope.TILE,
                group_id=_LAYER_ROUTE_GROUP,
                byte_extent=chunk_bytes,
                route_class=0,
                virtual_channel=0,
            )
        ]
        dispatch_at: int | None = None
        gather_at: int | None = None
        reduce_at: int | None = None
        for position, kind in enumerate(kinds):
            if dispatch_at is None and kind in _DISPATCH_KINDS:
                dispatch_at = position
            if gather_at is None and kind in _GATHER_KINDS:
                gather_at = position
            if kind in _REDUCE_KINDS:
                reduce_at = position
        last = max(len(kinds) - 1, 0)
        if gather_at is None:
            gather_at = min(1, last)
        if reduce_at is None:
            reduce_at = last
        steps.append(
            LinkStep(
                position=gather_at,
                where="before",
                link_sub=int(Link.GATHER),
                collective_op=int(CollectiveOp.ALL_GATHER),
                label="sparse_index_gather",
                participant_scope=ParticipantScope.TILE,
                group_id=_LAYER_ROUTE_GROUP,
                byte_extent=chunk_bytes,
                route_class=1,
                virtual_channel=1,
            )
        )
        if dispatch_at is not None:
            steps.append(
                LinkStep(
                    position=dispatch_at,
                    where="before",
                    link_sub=int(Link.SCATTER),
                    collective_op=int(CollectiveOp.CONCAT),
                    label="expert_dispatch",
                    participant_scope=ParticipantScope.TILE,
                    group_id=_LAYER_ROUTE_GROUP,
                    byte_extent=chunk_bytes,
                    route_class=2,
                    virtual_channel=2,
                )
            )
        steps.append(
            LinkStep(
                position=reduce_at,
                where="after",
                link_sub=int(Link.COLLECTIVE),
                collective_op=int(CollectiveOp.SUM),
                label="expert_reduction",
                participant_scope=ParticipantScope.TILE,
                group_id=_LAYER_ROUTE_GROUP,
                reduction_contract=_COLLECTIVE_REDUCTION_CONTRACT,
                byte_extent=chunk_bytes,
                route_class=2,
                virtual_channel=2,
            )
        )
        steps.append(
            LinkStep(
                position=last,
                where="after",
                link_sub=int(Link.SEND),
                collective_op=int(CollectiveOp.POINT_TO_POINT),
                label="residual_unicast",
                participant_scope=ParticipantScope.TILE,
                participant_count=2,
                byte_extent=chunk_bytes,
                route_class=0,
                virtual_channel=3,
            )
        )
        steps.append(
            LinkStep(
                position=last,
                where="after",
                link_sub=int(Link.BARRIER),
                collective_op=int(CollectiveOp.POINT_TO_POINT),
                label="layer_barrier",
                participant_scope=ParticipantScope.TILE,
                group_id=_LAYER_ROUTE_GROUP,
                byte_extent=0,
                route_class=1,
                virtual_channel=3,
            )
        )
        return steps

    return plan


# ---------------------------------------------------------------------------
# Product entry points
# ---------------------------------------------------------------------------
def deepseek_v4_rom_policy(
    *,
    defects: Sequence[DefectRecord] = (),
    tile_rom_bytes: int = TILE_ROM_BYTES,
    tiles_per_reticle: int = TILES_PER_RETICLE,
    alignment_bytes: int = ROM_ROW_BYTES,
    sram_budget_bytes: int = SRAM_BYTES,
    epoch: int = 1,
    chunk_bytes: int = 1 << 16,
    notes: Mapping[str, Any] | None = None,
) -> RomTargetPolicy:
    geometry = wafer_geometry(
        tile_rom_bytes=tile_rom_bytes, tiles_per_reticle=tiles_per_reticle
    )
    layout = deepseek_v4_layout_policy(
        tile_rom_bytes=tile_rom_bytes,
        tiles_per_reticle=tiles_per_reticle,
        alignment_bytes=alignment_bytes,
    )
    return RomTargetPolicy(
        product=PRODUCT,
        target_id=TARGET_ID,
        backend=BACKEND,
        topology_class=TopologyClass.WAFER_LOGICAL_DEVICE,
        layout=layout,
        sram_budget_bytes=sram_budget_bytes,
        tile_rows=128,
        tile_cols=128,
        tile_depth=256,
        defects=tuple(defects),
        features=PROGRAM_FEATURES,
        place_region=_WaferPlacer(
            tile_rom_bytes=tile_rom_bytes,
            tiles_per_reticle=tiles_per_reticle,
            alignment=alignment_bytes,
        ),
        emit_topology=_wafer_topology_factory(
            tiles_per_reticle=tiles_per_reticle,
            tile_rom_bytes=tile_rom_bytes,
            epoch=epoch,
        ),
        link_plan=_wafer_link_plan_factory(chunk_bytes=chunk_bytes),
        notes={
            "host_submission": "one submission targets the whole wafer",
            "partition": "expert_and_role_striped_tile_rom",
            "physical_boundary": "wafer_logical_device",
            "wafer_geometry": geometry,
            **dict(notes or {}),
        },
    )


def build_deepseek_v4_rom_deployment(
    graph: KernelGraph,
    *,
    capability: Capability | None = None,
    defects: Sequence[DefectRecord] = (),
    weight_storage_class: StorageClass = StorageClass.ROM,
    tile_rom_bytes: int = TILE_ROM_BYTES,
    tiles_per_reticle: int = TILES_PER_RETICLE,
    alignment_bytes: int = ROM_ROW_BYTES,
    epoch: int = 1,
    deployment_id: int = 1,
    generation: int = 1,
    notes: Mapping[str, Any] | None = None,
) -> tuple[Deployment, RomImagePlan]:
    """Lower ``graph`` onto the mandatory wafer-scale DeepSeek ROM target."""
    capability = capability or deepseek_v4_rom_capability(
        tile_rom_bytes=tile_rom_bytes, tiles_per_reticle=tiles_per_reticle
    )
    if capability.topology_class != int(TopologyClass.WAFER_LOGICAL_DEVICE):
        raise DeepSeekV4RomError(
            "DeepSeek-V4-Flash ROM is a mandatory wafer-scale logical device; a "
            "single-chip or cluster capability cannot host it"
        )
    policy = deepseek_v4_rom_policy(
        defects=defects,
        tile_rom_bytes=tile_rom_bytes,
        tiles_per_reticle=tiles_per_reticle,
        alignment_bytes=alignment_bytes,
        epoch=epoch,
        notes=notes,
    )
    lowering = RomLowering(
        graph,
        capability,
        policy,
        weight_storage_class=weight_storage_class,
        deployment_id=deployment_id,
        generation=generation,
    )
    plan = lowering.plan_regions()
    declared = int(capability.memory["rom"]["bytes"])
    if plan.rom_bytes > declared:
        raise DeepSeekV4RomError(
            f"the DeepSeek ROM image needs {plan.rom_bytes} bytes but the wafer "
            f"capability declares {declared}"
        )
    reticle_rom_bytes = tile_rom_bytes * tiles_per_reticle
    if plan.largest_member_bytes > reticle_rom_bytes:
        raise DeepSeekV4RomError(
            f"the largest indivisible ROM payload is {plan.largest_member_bytes} "
            f"bytes, more than one reticle field's {reticle_rom_bytes}; no legal "
            "wafer placement exists"
        )
    geometry = wafer_geometry(
        tile_rom_bytes=tile_rom_bytes, tiles_per_reticle=tiles_per_reticle
    )
    tiles_used = len({s.coordinate.tile for r in plan.regions for s in r.shards})
    reticles_used = len({s.coordinate.reticle for r in plan.regions for s in r.shards})
    lowering.builder.notes["wafer_placement"] = {
        "distributed_region_count": sum(
            1 for r in plan.regions if len(r.shards) > 1
        ),
        "largest_member_bytes": plan.largest_member_bytes,
        "largest_region_bytes": plan.largest_region_bytes,
        "tensor_parallel_member_count": plan.distributed_member_count,
        "max_reticles": geometry["max_reticles"],
        "planned_rom_bytes": plan.rom_bytes,
        "reticles_used": reticles_used,
        "tile_rom_bytes": tile_rom_bytes,
        "tiles_per_reticle": tiles_per_reticle,
        "tiles_used": tiles_used,
    }
    lowering.builder.notes["wafer_geometry"] = geometry
    return lowering.build(), plan


def lower_to_abi3(
    graph: KernelGraph,
    capability: Capability,
    *,
    topology: int | None = None,
    deployment_id: int = 1,
    generation: int = 1,
    **kwargs: Any,
) -> Deployment:
    """The shared backend entry point: one neutral graph in, one deployment out.

    ``topology`` is accepted and checked rather than ignored: the wafer-scale
    logical device is mandatory for this product, not an option.
    """
    if topology is not None and int(topology) != int(
        TopologyClass.WAFER_LOGICAL_DEVICE
    ):
        raise DeepSeekV4RomError(
            f"DeepSeek-V4-Flash ROM is a mandatory wafer-scale logical device; "
            f"topology class {int(topology)} was requested"
        )
    deployment, _plan = build_deepseek_v4_rom_deployment(
        graph,
        capability=capability,
        deployment_id=deployment_id,
        generation=generation,
        **kwargs,
    )
    return deployment


__all__ = [
    "BACKEND",
    "DeepSeekV4RomError",
    "MAX_RETICLES",
    "PRODUCT",
    "TARGET_ID",
    "TILES_PER_RETICLE",
    "TILE_ROM_BYTES",
    "build_deepseek_v4_rom_deployment",
    "lower_to_abi3",
    "deepseek_v4_layout_policy",
    "deepseek_v4_rom_capability",
    "deepseek_v4_rom_policy",
    "wafer_geometry",
]
