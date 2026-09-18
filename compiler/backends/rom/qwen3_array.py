"""Qwen3-8B immutable-ROM lowering for an ``N``-node pipelined ROM array.

This is the sibling of :mod:`compiler.backends.rom.qwen3`, the single-chip
backend, and it exists because the analytical design sweep already names the
point: ``Qwen3-8B/ROM-N5-native-SRAMKV-array-pipeline-x8-romfill`` in
``results/roofline/n5_vs_b200/analytical.json``, published as the design-target
capability records
``configs/hardware/abi3_capability/n5_design_target/rom_qwen3_n5_design_target_qwen3-8b__rom-n5-native-sramkv-array-pipeline-x{6,7,8}-romfill__*.json``.
Those records are *machines* for a collapsed single logical device -- they force
``topology_class`` to ``SINGLE_CHIP`` and say so in their own note -- so until
now the design point had no deployment target at all.  This module is that
target.

**Why the partition is a pipeline and not tensor parallelism.**  The design
point's own name says ``array-pipeline``, and the reason is the model: Qwen3-8B
is dense, so there is no expert axis to own.  The two partitions a dense decoder
admits are a layer pipeline, which needs no new view geometry because a stage
owns whole layers, and tensor parallelism, which shards the contraction or the
output axis of every projection and needs both a sharded-output view and a
data-bearing all-gather that the ABI's LINK engine implements but this
lowering's region machinery does not yet present.  The pipeline is what the
design priced and what the existing region placer expresses, so it is what this
module builds.  Column-sharded dense compute with activation all-gathers is the
recorded follow-on -- the same WP-D2 the DeepSeek-V4 array backend records --
and its absence is stated in ``notes["partition"]`` rather than implied.

**What the pipeline costs and what it buys.**  It buys ROM per node: the
single-chip product needs the whole 16,381,470,720-byte checkpoint resident on
one die, and a stage of an ``N``-node pipeline needs only its own layers, so the
declared per-node ROM here is a quarter of the single chip's.  It costs decode
latency: one token walks the chain, so at batch one exactly one stage is busy at
a time and the array's token rate is the single chip's, not ``N`` times it.  That
is a property of pipeline parallelism at batch one and not of this lowering;
``notes["pipeline"]`` states it as a limitation rather than leaving a reader to
infer a speed-up that is not there.

**Arithmetic is unchanged, and that is checkable.**  The stages exchange the
residual stream by ``LINK.REMOTE_DMA``, a byte movement under no numeric
contract, and no collective reduces anything.  So this deployment computes the
same function as the single-chip one, kernel for kernel, and its emitted token
must be bit-identical to the single-chip token on the same prompt.  A
disagreement is a defect in this backend, never a numeric difference to be
explained -- which is exactly the property the DeepSeek array comparison does
*not* have, because there an expert all-reduce reassociates a sum.

**The partitioner is shared, not copied.**  :func:`deepseek_v41_stage_plan` in
:mod:`compiler.backends.rom.deepseek_v41` is a contiguous minimax partition of a
graph's layer runs subject to the shared-cache rule, and nothing in it is
V4.1-specific: it reads the neutral graph's own runs, weight bindings and state
effects.  Qwen3 declares no shared KV cache, so the legality constraint is
vacuous here and the partition is pure minimax; importing it keeps one
partitioner rather than two that can come apart.  Its refusals are re-raised
with this product's error type so a caller sees which product refused.

Nothing here is a claim about area.  The per-node ROM bytes the build needs are
recorded in ``notes["array_placement"]`` beside the single chip's, and the
single-chip backend's own density accounting -- reported, never asserted -- is
what prices them.
"""

from __future__ import annotations

import hashlib
from typing import Any, Mapping, Sequence

from compiler.backends.hbm_sram.capability import CLUSTER_32_LINK
from compiler.ir.v3.kernel_ir import KernelGraph
from compiler.qwen3.constants import SESSION_CONTEXT_CAPACITY, TOKEN_BLOCK_ROWS
from runtime.abi3.capability import Capability
from runtime.abi3.constants import (
    Feature,
    Link,
    NodeClass,
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
from .common.program import (
    LayerRun,
    LinkStep,
    RomLowering,
    RomTargetPolicy,
    analyze,
)
from .deepseek_v41 import (
    DeepSeekV41RomError,
    StagePlan,
    deepseek_v41_stage_plan,
    region_stage,
)
from .deepseek_v41_array import (
    LINK_CLASS_INTER_DOMAIN,
    cluster_n_link,
    technology_domain_size,
)
from .qwen3 import (
    BANK_BYTES,
    HBM_BYTES,
    NUMERIC_CONTRACTS,
    ROM_CAPACITY_BYTES,
    ROM_ROW_BYTES,
    SRAM_BYTES,
    qwen3_area_accounting,
)

PRODUCT = "qwen3-8b-rom-array"
TARGET_ID = "qwen3-8b-rom-array-pipeline"
BACKEND = "rom.cluster_n_pipeline"

#: Nodes in the array.  Eight is the design point the analytical sweep priced
#: (``ROM-N5-native-SRAMKV-array-pipeline-x8-romfill``); x6 and x7 are published
#: beside it, so the count is a parameter everywhere and this is only the
#: default.
NODE_COUNT = 8

#: Devices in one high-bandwidth domain, read from ``configs/hardware/
#: technology.json`` rather than chosen here -- the same field the roofline read
#: to build the design point this target stands in for.
DOMAIN_SIZE = technology_domain_size()

#: ROM one node carries.  A QUARTER of the single chip's 16 GiB, and that is the
#: pipeline's whole structural benefit: a stage holds its own layers, not the
#: model.  The build proves the busiest stage fits this rather than assuming it,
#: and records what every stage actually needs.
NODE_ROM_BYTES = ROM_CAPACITY_BYTES // 4

#: Route class of an inter-stage hop, and the number of classes the topology
#: declares.  Class 0 is node-local traffic; class 1 is the pipeline chain.
PIPELINE_ROUTE_CLASS = 1
LINK_CLASS_COUNT = 2

CAPABILITY_FEATURES = (
    Feature.HOST_QUEUE_ABI,
    Feature.DEPLOYMENT_DESCRIPTOR_ABI,
    Feature.DETERMINISTIC_MICROSEQUENCER,
    Feature.BF16_TENSOR,
    Feature.TRANSACTIONAL_STATE,
    Feature.ON_DEVICE_SELECTION,
    Feature.INTEGRITY_RETRY,
    # Bit 8.  Mandatory on CLUSTER_N: the class exists to say that the nodes are
    # separate devices with a fabric between them.
    Feature.INTER_CHIP_ENDPOINT,
)

PROGRAM_FEATURES = (
    Feature.HOST_QUEUE_ABI,
    Feature.DEPLOYMENT_DESCRIPTOR_ABI,
    Feature.DETERMINISTIC_MICROSEQUENCER,
    Feature.BF16_TENSOR,
    Feature.ON_DEVICE_SELECTION,
    Feature.INTER_CHIP_ENDPOINT,
)

#: The single chip's engine mix, unchanged -- a node IS the Qwen ROM chip, which
#: is what makes this a packaging comparison -- plus the LINK engine the chain
#: needs.  A pipeline hop is one queue's worth of traffic per token, so the link
#: engine is the smallest one the cluster profiles declare.
ARRAY_ENGINES: Mapping[str, Mapping[str, int]] = {
    "tensor": {"lanes": 512, "queues": 2},
    "vector": {"lanes": 256, "queues": 2},
    "attention": {"lanes": 128, "queues": 1},
    "dma": {"queues": 2},
    "reduction": {"lanes": 128, "queues": 1},
    "selection": {"queues": 1},
    "state": {"queues": 1},
    "link": {"lanes": 8, "queues": 4},
}


def _layer_count(graph: KernelGraph) -> int:
    """Decoder layers in the graph, from the kernels' own layer numbers."""
    layers = {int(k.layer) for k in graph.kernels if k.layer is not None}
    return len(layers)


class Qwen3ArrayRomError(ValueError):
    """Raised when the Qwen graph will not pipeline onto the declared array."""


# ---------------------------------------------------------------------------
# Geometry
# ---------------------------------------------------------------------------
def qwen3_array_geometry(
    *,
    node_count: int = NODE_COUNT,
    domain_size: int = DOMAIN_SIZE,
    node_rom_bytes: int = NODE_ROM_BYTES,
) -> dict[str, Any]:
    """The declared array geometry, and the fabric partition it must satisfy.

    ``Capability._validate_fabric`` requires ``domains * domain_size ==
    max_nodes`` exactly, so a node count that does not fill whole domains is
    refused here with the arithmetic rather than at capability validation with
    none.  A machine smaller than one domain declares the domain it occupies:
    four nodes inside an eight-device domain are one four-device domain, not
    half of one, because the capability field names what the deployment sits on.
    """
    node_count = int(node_count)
    if node_count < 2:
        raise Qwen3ArrayRomError(
            f"an array needs at least two nodes; {node_count} asked. One node is "
            "the SINGLE_CHIP product in compiler.backends.rom.qwen3"
        )
    if node_count == 32:
        raise Qwen3ArrayRomError(
            "32 nodes is CLUSTER_32, a frozen class four shipped capability "
            "records name; a Qwen array of exactly 32 nodes cannot be expressed "
            "as CLUSTER_N"
        )
    effective_domain = min(int(domain_size), node_count)
    if node_count % effective_domain:
        raise Qwen3ArrayRomError(
            f"{node_count} nodes do not partition into {effective_domain}-device "
            "domains; the declared fabric needs domains * domain_size == nodes"
        )
    domains = node_count // effective_domain
    return {
        "node_count": node_count,
        "domain_size": effective_domain,
        "domains": domains,
        "declared_domain_size_of_the_technology_record": int(domain_size),
        "node_rom_bytes": int(node_rom_bytes),
        "array_rom_bytes": int(node_rom_bytes) * node_count,
        "single_chip_rom_bytes": ROM_CAPACITY_BYTES,
        "hbm_bytes_per_node": HBM_BYTES,
        "sram_bytes_per_node": SRAM_BYTES,
        "partition": "layer_pipeline_contiguous_minimax",
        "evidence": (
            "node count is the analytical design point's device count; a node is "
            "the single-chip Qwen ROM die with its engine mix unchanged, so only "
            "the count, the fabric and the ROM each node carries differ"
        ),
    }


# ---------------------------------------------------------------------------
# Placement
# ---------------------------------------------------------------------------
class _PipelinePlacer:
    """Role striping inside a node; the stage plan chooses the node.

    The single-chip backend gives each region its own ROM bank, because a bank
    is the physical object a weight role reads through.  That is unchanged here
    and is the reason the placer keeps a bank cursor PER NODE: bank numbering
    restarts on every node, so a stage's fifth region is its fifth bank rather
    than the machine's, and a node's bank inventory is what its own regions need.
    """

    def __init__(self, *, stage_plan: StagePlan, node_count: int) -> None:
        self.stage_plan = stage_plan
        self.node_count = int(node_count)
        self.next_bank: dict[int, int] = {}
        self.bytes_by_node: dict[int, int] = {}

    def __call__(
        self, key: str, role: str, index: int, size_bytes: int
    ) -> RomCoordinate:
        try:
            node = region_stage(key, self.stage_plan)
        except DeepSeekV41RomError as exc:
            raise Qwen3ArrayRomError(str(exc)) from None
        if not 0 <= node < self.node_count:
            raise Qwen3ArrayRomError(
                f"the stage plan places region {key!r} on node {node}, outside "
                f"the {self.node_count}-node array"
            )
        bank = self.next_bank.get(node, 0)
        self.next_bank[node] = bank + 1
        self.bytes_by_node[node] = self.bytes_by_node.get(node, 0) + int(size_bytes)
        return RomCoordinate(node_id=node, reticle=0, tile=0, bank=bank)


def _advance_bank(coordinate: RomCoordinate) -> RomCoordinate:
    """A region larger than one bank spills to the next bank of its own node."""
    return RomCoordinate(
        node_id=coordinate.node_id,
        reticle=coordinate.reticle,
        tile=coordinate.tile,
        bank=coordinate.bank + 1,
    )


def qwen3_array_layout_policy(
    placer: _PipelinePlacer, *, alignment_bytes: int = ROM_ROW_BYTES
) -> RomLayoutPolicy:
    """The single chip's ROM geometry, with a per-node bank walker."""
    return RomLayoutPolicy(
        alignment_bytes=alignment_bytes,
        row_bytes=min(ROM_ROW_BYTES, alignment_bytes),
        resource_bytes=BANK_BYTES,
        spare_row_fraction=0.01,
        minimum_spare_rows=8,
        spare_columns_per_bank=8,
        base_address=0,
        advance_resource=_advance_bank,
    )


# ---------------------------------------------------------------------------
# Capability
# ---------------------------------------------------------------------------
def qwen3_array_rom_capability(
    *,
    node_count: int = NODE_COUNT,
    domain_size: int = DOMAIN_SIZE,
    node_rom_bytes: int = NODE_ROM_BYTES,
    max_context_positions: int = SESSION_CONTEXT_CAPACITY,
    vocabulary_size: int = 151936,
) -> Capability:
    """The exact limits of the ``N``-node pipelined Qwen ROM array.

    ``memory.rom.bytes`` is the WHOLE MACHINE, following the two-wafer V4.1
    record: the schedule checker charges the deployment's ROM objects against
    one budget and the deployment is one program over every stage.  The per-node
    boundary is enforced separately, against the region plan, by
    :func:`build_qwen3_array_rom_deployment`, which is the check that actually
    means something physically.
    """
    geometry = qwen3_array_geometry(
        node_count=node_count,
        domain_size=domain_size,
        node_rom_bytes=node_rom_bytes,
    )
    nodes = geometry["node_count"]
    capability = Capability(
        capability_id="",
        topology_class=int(TopologyClass.CLUSTER_N),
        features=tuple(int(f) for f in CAPABILITY_FEATURES),
        limits={
            "max_instructions": 4096,
            "max_descriptors": 16384,
            "max_loop_depth": 4,
            "max_loop_trip": 4096,
            "max_retired_work": 1 << 24,
            "max_events": 256,
            "max_event_id": 1023,
            "max_outstanding_per_queue": 16,
            "max_context_positions": int(max_context_positions),
            "max_expert_ids": 1,
            "max_topk": 1,
            "max_vocabulary": int(vocabulary_size),
            "max_sessions": 8,
            "max_nodes": nodes,
            "max_state_resources": 16,
        },
        numeric_contracts=NUMERIC_CONTRACTS,
        engines={name: dict(spec) for name, spec in ARRAY_ENGINES.items()},
        memory={
            "rom": {
                "bytes": geometry["array_rom_bytes"],
                # One bank per weight role per stage, the single chip's own
                # partition applied inside a node.
                "banks": 16,
            },
            "sram": {"bytes": SRAM_BYTES, "banks": 32},
            "hbm": {"bytes": HBM_BYTES},
        },
        link=cluster_n_link(node_count=nodes, domain_count=geometry["domains"]),
        fabric={
            # A reticle-bounded die, not a wafer logical device: a node is the
            # single-chip Qwen ROM chip and has no internal fabric to declare.
            "node_class": int(NodeClass.DIE),
            "cluster": {
                "domain_size": geometry["domain_size"],
                "domains": geometry["domains"],
                # A single-level fabric has no inter-domain hop to price, and
                # ``Capability._validate_fabric`` refuses a class id for one that
                # does not exist.  Every published Qwen array point (x6, x7, x8)
                # fits inside one high-bandwidth domain, so this is zero there
                # and becomes the inter-domain class only if a larger count ever
                # spans domains.
                "inter_domain_class": (
                    LINK_CLASS_INTER_DOMAIN if geometry["domains"] > 1 else 0
                ),
            },
        },
        technology_view=f"rom_array_pipeline_{nodes}_declared_v1",
    )
    capability.validate()
    return capability


#: Published profiles, read by ``tools/publish_abi3_capabilities.py`` so the
#: committed capability record has one source of truth rather than two.  x6, x7
#: and x8 are the three array-pipeline points the analytical sweep publishes.
PROFILES = {
    "rom-qwen3-array-x6": lambda: qwen3_array_rom_capability(node_count=6),
    "rom-qwen3-array-x7": lambda: qwen3_array_rom_capability(node_count=7),
    "rom-qwen3-array-x8": lambda: qwen3_array_rom_capability(node_count=8),
}


# ---------------------------------------------------------------------------
# Topology and fabric
# ---------------------------------------------------------------------------
def _route_table_digest(plan: RomImagePlan) -> bytes:
    """Covers which node holds which region: the array's own routing input."""
    digest = hashlib.sha256()
    for region in plan.regions:
        digest.update(region.key.encode())
        for shard in region.shards:
            digest.update(bytes(str(shard.to_list()), "ascii"))
    return digest.digest()


def _array_topology_factory(
    *, node_count: int, domain_count: int, epoch: int, link: Mapping[str, int]
):
    def emit(builder, plan: RomImagePlan) -> int:
        repair = plan.repair_map
        nodes = sorted(
            {shard.coordinate.node_id for r in plan.regions for shard in r.shards}
        )
        if nodes and (nodes[0] < 0 or nodes[-1] >= node_count):
            raise Qwen3ArrayRomError(
                f"the region plan places regions on nodes {nodes[0]}..{nodes[-1]} "
                f"but the array declares {node_count}"
            )
        if len(nodes) != node_count:
            raise Qwen3ArrayRomError(
                f"the region plan uses {len(nodes)} of {node_count} nodes "
                f"({nodes}); a stage that holds no weight is not a stage"
            )
        # ``active_resource_count`` is a per-device prefix, as it is on the
        # two-wafer record: the busiest node is what it has to cover, and the
        # machine's whole active set is authenticated by the digest beside it.
        by_node: dict[int, int] = {}
        for resource in repair.active_resources:
            by_node[resource[0]] = by_node.get(resource[0], 0) + 1
        return builder.topology(
            topology_class=TopologyClass.CLUSTER_N,
            node_count=node_count,
            reticle_count=0,
            tiles_per_reticle=0,
            local_node_id=0,
            local_reticle_id=0,
            local_tile_id=0,
            link_class_count=LINK_CLASS_COUNT,
            active_resource_count=max(by_node.values(), default=0),
            quarantined_resource_count=len(repair.quarantine),
            hbm_bytes_per_node=HBM_BYTES,
            sram_bytes_per_node=SRAM_BYTES,
            link_count=node_count * int(link.get("endpoints_per_node", 8)),
            route_group_count=domain_count,
            epoch=epoch,
            bisection_link_count=int(link.get("bisection_links", 0)),
            active_resource_digest=repair.active_resource_digest,
            quarantine_digest=repair.quarantine_digest,
            route_table_digest=_route_table_digest(plan),
            health_digest=repair.health_digest,
            key="topology",
        )

    return emit


def _pipeline_link_plan_factory(*, stage_plan: StagePlan):
    """The one chain hop the LOCAL node initiates, once per token.

    A dense decoder stage has no on-node collective to issue -- no expert
    dispatch, no sparse index gather, no expert reduction -- so the whole
    on-fabric critical path of this product is the chain hop, and this plan is
    four lines where the DeepSeek wafer's is five steps.

    **Why one step and not ``N-1``.**  An ABI 3.0 deployment is written from ONE
    node's point of view: the TOPOLOGY descriptor carries a single
    ``local_node_id``, and ``LINK.REMOTE_DMA`` refuses a transfer that names
    neither the local node as source nor as destination -- "an endpoint cannot
    initiate a transfer it is not part of", which is the LINK engine's own rule
    and the right one.  A four-stage chain has three hops, and two of them join
    two nodes that are both remote from the local one, so they are not this
    program's instructions to issue.  They are the SAME instruction executed on
    the stage that owns them, exactly as the node-sharded expert bank's one
    ``base_address`` is the same number on every node: one program, ``N``
    copies, each issuing its own hop.  The chain's whole per-token traffic --
    ``node_count - 1`` hops of this size -- is recorded in
    ``notes["pipeline"]`` so nothing is left implicit, and the two-wafer V4.1
    product emits exactly this one step for exactly this reason (it has one
    boundary, so the question never arose there).

    The step is a push from the local node to its chain successor, at the first
    body position of the first layer run: the residual the previous stage
    produced has to be resident before this stage's first kernel reads it.
    """

    def plan(run: LayerRun, kinds: Sequence[str]) -> list[LinkStep]:
        stage = stage_plan.stage_of_run.get(run.index)
        if stage is None:
            raise Qwen3ArrayRomError(
                f"layer run {run.index} is not placed by the stage plan"
            )
        if stage != 0 or stage_plan.stage_count < 2:
            return []
        by_stage = stage_plan.runs_by_stage[stage]
        if not by_stage or by_stage[-1] != run.index:
            return []
        extent = stage_plan.cross_stage_bytes[0]
        if extent <= 0:
            raise Qwen3ArrayRomError(
                "no tensor crosses the boundary out of stage 0; a pipeline stage "
                "that sends nothing is not a stage"
            )
        return [
            LinkStep(
                position=0,
                where="after",
                link_sub=int(Link.REMOTE_DMA),
                collective_op=int(CollectiveOp.POINT_TO_POINT),
                label="pipeline_residual_hop",
                participant_scope=ParticipantScope.NODE,
                participant_count=2,
                # The local node and its chain successor.  ``local_node_id`` is
                # zero, so a push out of this stage is 0 -> 1 and the engine
                # resolves it as a push rather than refusing it.
                source_node=0,
                destination_node=1,
                byte_extent=int(extent),
                route_class=PIPELINE_ROUTE_CLASS,
                virtual_channel=0,
            )
        ]

    return plan


# ---------------------------------------------------------------------------
# Product entry points
# ---------------------------------------------------------------------------
def qwen3_array_rom_policy(
    graph: KernelGraph,
    *,
    node_count: int = NODE_COUNT,
    domain_size: int = DOMAIN_SIZE,
    node_rom_bytes: int = NODE_ROM_BYTES,
    defects: Sequence[DefectRecord] = (),
    alignment_bytes: int = ROM_ROW_BYTES,
    sram_budget_bytes: int = SRAM_BYTES,
    epoch: int = 1,
    notes: Mapping[str, Any] | None = None,
    target_id: str = TARGET_ID,
) -> tuple[RomTargetPolicy, StagePlan, dict[str, Any]]:
    geometry = qwen3_array_geometry(
        node_count=node_count, domain_size=domain_size, node_rom_bytes=node_rom_bytes
    )
    nodes = geometry["node_count"]
    # A stack of structurally identical decoder layers detects as ONE layer run,
    # which is right for a single chip and unusable for a pipeline: a stage owns
    # whole runs.  So the run length is capped at the layers one stage carries,
    # which turns the single run into exactly ``nodes`` of them, and the SAME
    # analysis is handed to the partitioner and to the lowering -- two analyses
    # of one graph with different caps would partition runs the lowering does
    # not emit.
    layers = _layer_count(graph)
    if layers < nodes:
        raise Qwen3ArrayRomError(
            f"the graph declares {layers} decoder layer(s) and the array declares "
            f"{nodes} nodes; a pipeline stage that holds no layer is not a stage"
        )
    cap = -(-layers // nodes)
    analysis = analyze(graph, max_layers_per_run=cap)
    try:
        stage_plan = deepseek_v41_stage_plan(
            graph, stage_count=nodes, analysis=analysis
        )
    except DeepSeekV41RomError as exc:
        raise Qwen3ArrayRomError(
            f"the Qwen graph does not pipeline across {nodes} nodes: {exc}"
        ) from None
    placer = _PipelinePlacer(stage_plan=stage_plan, node_count=nodes)
    link = cluster_n_link(node_count=nodes, domain_count=geometry["domains"])
    policy = RomTargetPolicy(
        product=PRODUCT,
        target_id=target_id,
        backend=BACKEND,
        topology_class=TopologyClass.CLUSTER_N,
        layout=qwen3_array_layout_policy(placer, alignment_bytes=alignment_bytes),
        sram_budget_bytes=sram_budget_bytes,
        token_block_rows=TOKEN_BLOCK_ROWS,
        tile_rows=128,
        tile_cols=128,
        tile_depth=128,
        max_layers_per_run=cap,
        defects=tuple(defects),
        features=PROGRAM_FEATURES,
        place_region=placer,
        emit_topology=_array_topology_factory(
            node_count=nodes,
            domain_count=geometry["domains"],
            epoch=epoch,
            link=link,
        ),
        link_plan=_pipeline_link_plan_factory(stage_plan=stage_plan),
        notes={
            "partition": "layer_pipeline_contiguous_minimax_dense_no_sharding",
            "partition_rationale": (
                "Qwen3-8B is dense, so there is no expert axis to own; a stage "
                "holds whole layer runs and the residual stream crosses each "
                "boundary once per token. Tensor parallelism -- column-sharded "
                "projections with activation all-gathers, the DeepSeek array "
                "plan's WP-D2 -- is the recorded follow-on and is NOT in this "
                "backend"
            ),
            "pipeline": {
                "layers": layers,
                "max_layers_per_run": cap,
                "batch_one_concurrency": (
                    "one stage is busy at a time, so the array's token rate at "
                    "batch one is the single chip's and not node_count times it; "
                    "the pipeline buys ROM per node, not decode latency"
                ),
                "cross_stage_bytes_per_token": list(stage_plan.cross_stage_bytes),
                "chain_hops_per_token": max(nodes - 1, 0),
                "hops_this_program_issues": 1 if nodes > 1 else 0,
                "why_one_hop": (
                    "a deployment is written from one local node's viewpoint, so "
                    "the program issues the hop that node initiates; the other "
                    "stages issue the same instruction on their own copy"
                ),
                "prologue_crossing_bytes": stage_plan.prologue_crossing_bytes,
                "stage_count": nodes,
            },
            "arithmetic": (
                "identical to the single-chip lowering: the stages exchange bytes "
                "under LINK.REMOTE_DMA and no collective reduces anything, so the "
                "emitted token must be bit-identical to the single chip's on the "
                "same prompt"
            ),
            "physical_chip_count": nodes,
            **dict(notes or {}),
        },
    )
    return policy, stage_plan, geometry


def build_qwen3_array_rom_deployment(
    graph: KernelGraph,
    *,
    capability: Capability | None = None,
    node_count: int = NODE_COUNT,
    domain_size: int = DOMAIN_SIZE,
    node_rom_bytes: int = NODE_ROM_BYTES,
    defects: Sequence[DefectRecord] = (),
    weight_storage_class: StorageClass = StorageClass.ROM,
    alignment_bytes: int = ROM_ROW_BYTES,
    deployment_id: int = 1,
    generation: int = 1,
    epoch: int = 1,
    notes: Mapping[str, Any] | None = None,
    target_id: str = TARGET_ID,
) -> tuple[Deployment, RomImagePlan]:
    """Lower ``graph`` onto the ``N``-node pipelined Qwen ROM array."""
    capability = capability or qwen3_array_rom_capability(
        node_count=node_count, domain_size=domain_size, node_rom_bytes=node_rom_bytes
    )
    declared_nodes = int(capability.limits.get("max_nodes", 0))
    if declared_nodes != int(node_count):
        raise Qwen3ArrayRomError(
            f"the capability declares {declared_nodes} nodes and this build asks "
            f"for {node_count}; a deployment binds the machine it was admitted "
            "against"
        )
    policy, stage_plan, geometry = qwen3_array_rom_policy(
        graph,
        node_count=node_count,
        domain_size=domain_size,
        node_rom_bytes=node_rom_bytes,
        defects=defects,
        alignment_bytes=alignment_bytes,
        epoch=epoch,
        notes=notes,
        target_id=target_id,
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

    # The per-node boundary is the check that means something physically: the
    # machine budget can be met by a plan that puts everything on one node.
    by_node: dict[int, int] = {}
    for region in plan.regions:
        for shard in region.shards:
            node = shard.coordinate.node_id
            by_node[node] = by_node.get(node, 0) + int(shard.bytes)
    busiest = max(by_node.values(), default=0)
    if busiest > int(node_rom_bytes):
        heaviest = sorted(by_node.items(), key=lambda item: -item[1])[:3]
        raise Qwen3ArrayRomError(
            f"the busiest pipeline stage needs {busiest} ROM bytes and a node "
            f"declares {node_rom_bytes}; the heaviest stages are "
            + ", ".join(f"node {n}: {b}" for n, b in heaviest)
        )
    declared_machine = int(capability.memory["rom"]["bytes"])
    if plan.rom_bytes > declared_machine:
        raise Qwen3ArrayRomError(
            f"the Qwen array ROM image needs {plan.rom_bytes} bytes but the "
            f"{geometry['node_count']}-node capability declares {declared_machine}"
        )
    lowering.builder.notes["array_placement"] = {
        "declared_node_rom_bytes": int(node_rom_bytes),
        "geometry": geometry,
        "rom_bytes_by_node": {str(n): b for n, b in sorted(by_node.items())},
        "busiest_node_rom_bytes": busiest,
        "single_chip_rom_bytes_for_the_same_graph": plan.rom_bytes,
        "node_rom_fraction_of_single_chip": (
            round(busiest / plan.rom_bytes, 6) if plan.rom_bytes else None
        ),
        "area_accounting_of_one_node": qwen3_area_accounting(busiest),
    }
    lowering.builder.notes["stage_plan"] = stage_plan.to_dict()
    lowering.builder.notes["rom_capacity"] = {
        "declared_machine_rom_bytes": declared_machine,
        "largest_bank_bytes": plan.largest_region_bytes,
        "planned_rom_bytes": plan.rom_bytes,
        "rom_bank_count": plan.resource_count,
    }
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
    """The shared backend entry point: one neutral graph in, one deployment out."""
    if topology is not None and int(topology) != int(TopologyClass.CLUSTER_N):
        raise Qwen3ArrayRomError(
            f"the Qwen ROM array is CLUSTER_N; topology class {int(topology)} was "
            "requested"
        )
    kwargs.setdefault("node_count", int(capability.limits.get("max_nodes", NODE_COUNT)))
    deployment, _plan = build_qwen3_array_rom_deployment(
        graph,
        capability=capability,
        deployment_id=deployment_id,
        generation=generation,
        **kwargs,
    )
    return deployment


__all__ = [
    "BACKEND",
    "DOMAIN_SIZE",
    "NODE_COUNT",
    "NODE_ROM_BYTES",
    "PRODUCT",
    "PROFILES",
    "Qwen3ArrayRomError",
    "TARGET_ID",
    "build_qwen3_array_rom_deployment",
    "lower_to_abi3",
    "qwen3_array_geometry",
    "qwen3_array_layout_policy",
    "qwen3_array_rom_capability",
    "qwen3_array_rom_policy",
]
