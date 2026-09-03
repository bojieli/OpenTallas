"""DeepSeek-V4-Flash immutable-ROM lowering for a 32-node reticle-class array.

This is the sibling of :mod:`compiler.backends.rom.deepseek_v4`, the wafer
backend, and it exists for one experiment: the same neutral graph, the same ROM
tile, the same weight tier, on the **cluster fabric TA-DS-HBM already uses**
instead of a stitched wafer.  ``TopologyClass.CLUSTER_32`` is the topology of
the 32-node HBM cluster, and the capability this module publishes declares the
same node count, the same link record and the same engine lane mix as
``hbm_sram_cluster_32``; only the weight residence differs.  ADR-003 section
3.3 (amendment of 2026-09-03) admits the profile; the plan is
``docs/DEEPSEEK_V4_ROM_ARRAY_IMPLEMENTATION_PLAN.md``.

**Partition.**  Expert-parallel, exactly the 32-node HBM cluster's ownership
rule: global expert ``e`` is owned by node ``floor(e / experts_per_node)``,
eight consecutive experts per node for the released 256-expert checkpoint.  A
routed expert bank -- and its E8M0 block-scale bank -- is a **node-sharded**
ROM region: the plan places node ``k``'s expert range of every slot on node
``k``, the emitted object is one node-local image (A28 ``node_segments``), the
routed view presents ``E/32`` local experts against the global bound, and the
partial rows each node produces are summed across the cluster by a
**data-bearing** ``LINK.COLLECTIVE SUM`` before ``EXPERT_REDUCE`` reads them
(the route-class-3 expert all-reduce of
``DEEPSEEK_200K_SIMULATOR_EXECUTION_DESIGN.md`` section 7).

Dense, shared, attention, indexer, hyper-connection, embedding and vocabulary
weights are **replicated on every node**: placed once in the plan (node 0's
dense banks, so the inverse proof reconstructs each byte exactly once), emitted
as shared ``segments`` objects that every node materialises, and charged to
every node's ROM in the topology notes.  Column-sharded dense compute with
activation all-gathers -- the HBM cluster's own dense partition -- is the
recorded follow-on (plan WP-D2); the replicated form is the controlled variant
this backend ships, and it says so in ``notes["partition"]``.

**Physical placement.**  A node is ``EXPERT_BANKS + DENSE_BANKS`` ROM banks of
``BANK_BYTES``.  Expert shards fill the expert banks identically on every node
-- shard ``k`` of a sharded region lands on node ``k mod 32`` on that node's
first expert bank with room, and every node sees the same sequence of sharded
regions -- so the node-local address of a shard is the same number on every
node and the symmetric ``MEMORY_OBJECT`` descriptor's one ``base_address`` is
true everywhere.  The backend proves that after planning rather than assuming
it.  Dense regions fill node 0's dense banks and are physically present on
every node's dense banks at the same addresses.

Nothing here is a claim about area.  The per-node ROM bytes the build needs,
including the replicated dense bytes, are recorded in the topology notes with
the area they imply at the two graded densities the program carries, and the
iso-area rule of the plan's section 3.5 derives the comparator from them.
"""

from __future__ import annotations

import hashlib
from typing import Any, Mapping, Sequence

from compiler.backends.rom.common.image import (
    DefectRecord,
    RegionRequest,
    RomCoordinate,
    RomImagePlan,
    RomLayoutPolicy,
)
from compiler.backends.rom.common.program import (
    LayerRun,
    LinkStep,
    RomLowering,
    RomTargetPolicy,
)
from compiler.backends.rom.deepseek_v4 import (
    CAPABILITY_FEATURES as _WAFER_CAPABILITY_FEATURES,
    NUMERIC_CONTRACTS,
    PROGRAM_FEATURES as _WAFER_PROGRAM_FEATURES,
    PRODUCT,
    ROM_ROW_BYTES,
    _COLLECTIVE_REDUCTION_CONTRACT,
    _DISPATCH_KINDS,
    _GATHER_KINDS,
    _REDUCE_KINDS,
)
from compiler.backends.hbm_sram.capability import CLUSTER_32_LINK
from compiler.ir.v3.kernel_ir import KernelGraph
from runtime.abi3.capability import Capability
from runtime.abi3.constants import (
    Feature,
    Link,
    NO_ID,
    ParticipantScope,
    StorageClass,
    TopologyClass,
)
from runtime.abi3.deployment import Deployment
from runtime.abi3.descriptors import CollectiveOp

TARGET_ID = "deepseek-v4-flash-rom-array-32"
BACKEND = "rom.cluster_32"

#: Exactly the HBM cluster's node count: the controlled comparison holds it
#: fixed, and ``CLUSTER_32`` admits no other.
NODE_COUNT = 32

#: One ROM bank.  A node's expert store is ``EXPERT_BANKS`` of these and its
#: replicated dense store ``DENSE_BANKS`` more; the split is a placement
#: convention that keeps the expert cursor identical on every node.
BANK_BYTES = 256 << 20
EXPERT_BANKS = 24
DENSE_BANKS = 40
NODE_ROM_BYTES = (EXPERT_BANKS + DENSE_BANKS) * BANK_BYTES

#: Node-local SRAM and HBM.  The SRAM figure is a reticle-class share of the
#: wafer's declared 8 GiB.
SRAM_BYTES = 256 << 20

#: What an 815 mm2 die can physically attach: five HBM3e stacks, by the
#: die-edge beachfront rule of ``src/opentallas/roofline.py``
#: (``max_hbm_stacks_per_device``: 12 mm pitch, 0.60 edge utilisation) times
#: the 36 GB stack the leading-node study prices
#: (``configs/hardware/technology_inputs.json``).  The GPU comparator is
#: charged by the same rule.
HBM_STACKS_PER_NODE = 5
HBM3E_STACK_BYTES = 36_000_000_000
PHYSICAL_HBM_BYTES = HBM_STACKS_PER_NODE * HBM3E_STACK_BYTES

#: What this build *declares* per node, and why it is not the physical figure.
#: The ROM program allocates every state plane and live activation at the
#: IR's own horizon (1,048,576 positions), 1.08 TB for one session, and this
#: build replicates that live set on every node: the wafer's declared
#: distributed HBM absorbs it, no five-stack die does.  Clamping the IR's
#: symbolic maxima to a smaller context was tried and breaks the additive
#: window biases the IR bakes into them.  So the capability declares the
#: replicated live set -- 34 stacks' worth -- and says so in every note, and
#: the plan's WP-D2 (KV and activations sharded across the 32 nodes, the HBM
#: cluster's own partition) is what brings the node back to five stacks.  A
#: comparison that reads this capability's HBM as a die-edge quantity is
#: reading the wrong field.
REPLICATED_LIVE_STATE_BYTES = 1_200_000_000_000
HBM_BYTES = REPLICATED_LIVE_STATE_BYTES

#: The wafer's declared context, kept so the emitted program is the same
#: program at the same bounds; only the placement and the fabric differ.
MAX_CONTEXT_POSITIONS = 262_144

#: The two graded ROM densities the program carries, so the notes can state
#: the area the per-node bytes imply under each rather than asserting one.
#: ``wafer_geometry`` in the wafer backend derives the first (usable bytes per
#: mm2 of a reticle field at the central leading-node envelope); the roofline's
#: N5 array designs work at the second (bytes per mm2 of ROM array).
WAFER_BACKEND_USABLE_DENSITY_BYTES_MM2 = 12_126_427.78
ROOFLINE_N5_ROM_DENSITY_BYTES_MM2 = 8_770_000.0
RETICLE_AREA_MM2 = 815.0

SHARDED_ROLES = ("expert_bank", "expert_bank_scale")

#: Rows per token block.  See ``deepseek_v4_array_rom_policy``.
TOKEN_BLOCK_ROWS = 1024

CAPABILITY_FEATURES = tuple(
    Feature.INTER_CHIP_ENDPOINT if f is Feature.WAFER_ENDPOINT else f
    for f in _WAFER_CAPABILITY_FEATURES
)
PROGRAM_FEATURES = tuple(
    Feature.INTER_CHIP_ENDPOINT if f is Feature.WAFER_ENDPOINT else f
    for f in _WAFER_PROGRAM_FEATURES
)

#: The cluster chip's engine lane mix, verbatim, so that compute is the same
#: on both sides of the storage-class comparison.
CLUSTER_ENGINES: Mapping[str, Mapping[str, int]] = {
    "tensor": {"lanes": 256, "queues": 4},
    "vector": {"lanes": 128, "queues": 2},
    "attention": {"lanes": 64, "queues": 2},
    "route": {"lanes": 32, "queues": 1},
    "reduction": {"lanes": 128, "queues": 2},
    "dma": {"lanes": 8, "queues": 4},
    "link": {"lanes": 8, "queues": 4},
    "selection": {"lanes": 8, "queues": 1},
    "state": {"lanes": 8, "queues": 1},
}


class DeepSeekV4ArrayError(ValueError):
    """Raised when the DeepSeek graph will not fit the 32-node array boundary."""


# ---------------------------------------------------------------------------
# Geometry
# ---------------------------------------------------------------------------
def array_geometry(
    *,
    node_count: int = NODE_COUNT,
    bank_bytes: int = BANK_BYTES,
    expert_banks: int = EXPERT_BANKS,
    dense_banks: int = DENSE_BANKS,
) -> dict[str, Any]:
    node_rom = (expert_banks + dense_banks) * bank_bytes
    return {
        "node_count": node_count,
        "bank_bytes": bank_bytes,
        "expert_banks_per_node": expert_banks,
        "dense_banks_per_node": dense_banks,
        "node_rom_bytes": node_rom,
        "array_rom_bytes": node_rom * node_count,
        "reticle_area_mm2": RETICLE_AREA_MM2,
        "hbm_bytes_per_node_declared": HBM_BYTES,
        "hbm_bytes_per_node_physical": PHYSICAL_HBM_BYTES,
        "hbm_stacks_per_node_physical": HBM_STACKS_PER_NODE,
        "hbm_stacks_per_node_implied_by_declaration": -(-HBM_BYTES // HBM3E_STACK_BYTES),
        "hbm_stack_bytes": HBM3E_STACK_BYTES,
        "hbm_rule": (
            "physical: five HBM3e stacks, the die-edge beachfront an 815 mm2 die "
            "attaches at 12 mm pitch and 0.60 edge utilisation, the same rule "
            "the GPU comparator is charged; declared: the replicated live set of "
            "one session at the IR's 1,048,576-position horizon, which no "
            "five-stack die holds"
        ),
        "live_state_boundary": (
            "live KV and activations are replicated per node in this build and "
            "declared at the IR horizon; a five-stack node needs them sharded "
            "across the 32 nodes (plan WP-D2) before the physical HBM figure "
            "applies"
        ),
        "partition": "expert_parallel_consecutive_ownership_dense_replicated",
        "evidence": (
            "node count equals the TA-DS-HBM cluster's; bank geometry is a "
            "placement convention, not a measured macro; per-node ROM bytes are "
            "what the build needs and the implied area is stated at two graded "
            "densities in the topology notes"
        ),
    }


# ---------------------------------------------------------------------------
# Placement
# ---------------------------------------------------------------------------
class _ArrayPlacer:
    """Consecutive expert ownership across nodes; dense on node 0's dense banks.

    ``place_region`` only supplies the hint; ``place_shard`` decides every
    shard.  A sharded region's shard ``k`` goes to node ``k mod N`` on the
    lowest expert bank of that node with room for one shard stride.  A dense
    region's shards go to node 0's lowest dense bank with any room, spilling
    forward bank by bank.  Both consult the walker's live cursor, so a full
    bank is never handed out.
    """

    def __init__(
        self,
        *,
        node_count: int,
        bank_bytes: int,
        expert_banks: int,
        dense_banks: int,
        alignment: int,
        sharded_roles: Sequence[str],
    ) -> None:
        self.node_count = node_count
        self.bank_bytes = bank_bytes
        self.expert_banks = expert_banks
        self.dense_banks = dense_banks
        self.alignment = alignment
        self.sharded_roles = tuple(sharded_roles)
        self.sharded_bytes = 0
        self.dense_bytes = 0

    # -- policy hooks -----------------------------------------------------
    def place_region(
        self, key: str, role: str, index: int, size_bytes: int
    ) -> RomCoordinate:
        if role in self.sharded_roles:
            self.sharded_bytes += size_bytes
            return RomCoordinate(node_id=0, reticle=0, tile=0, bank=0)
        self.dense_bytes += size_bytes
        return RomCoordinate(node_id=0, reticle=0, tile=0, bank=self.expert_banks)

    def shard_bytes(self, request: RegionRequest) -> int | None:
        if request.role not in self.sharded_roles:
            return None
        per_slot = len(request.members) // max(request.slot_count, 1)
        if per_slot % self.node_count:
            raise DeepSeekV4ArrayError(
                f"region {request.key!r} has {per_slot} members per slot, which "
                f"do not divide into {self.node_count} owners"
            )
        owned = per_slot // self.node_count
        member_bytes = request.members[0].bytes
        if any(m.bytes != member_bytes for m in request.members):
            raise DeepSeekV4ArrayError(
                f"region {request.key!r} members are not equal-sized; consecutive "
                "ownership needs one stride per owner"
            )
        # One owner's range per shard.  A shard smaller than the row alignment
        # (a tiny block-scale bank) still starts on an aligned address -- the
        # walker aligns every shard start -- so ownership is exact and only the
        # gap between shards is spent.  The product's 4 MiB experts and 256 KiB
        # scale banks are whole rows; the gap is a fixture-only cost.
        return owned * member_bytes

    def place_shard(
        self,
        request: RegionRequest,
        shard_index: int,
        cursor: Mapping[tuple[int, int, int, int], int],
    ) -> RomCoordinate:
        if request.role in self.sharded_roles:
            node = shard_index % self.node_count
            need = self.shard_bytes(request) or 1
            for bank in range(self.expert_banks):
                used = self._aligned(cursor.get((node, 0, 0, bank), 0))
                if used + need <= self.bank_bytes:
                    return RomCoordinate(node_id=node, reticle=0, tile=0, bank=bank)
            raise DeepSeekV4ArrayError(
                f"node {node} has no expert bank with {need} bytes of room for "
                f"region {request.key!r}; {self.expert_banks} banks of "
                f"{self.bank_bytes} bytes are full"
            )
        for bank in range(self.expert_banks, self.expert_banks + self.dense_banks):
            used = self._aligned(cursor.get((0, 0, 0, bank), 0))
            if used < self.bank_bytes:
                return RomCoordinate(node_id=0, reticle=0, tile=0, bank=bank)
        raise DeepSeekV4ArrayError(
            f"node 0 has no dense bank with room for region {request.key!r}; "
            f"{self.dense_banks} banks of {self.bank_bytes} bytes are full"
        )

    def _aligned(self, value: int) -> int:
        return (value + self.alignment - 1) // self.alignment * self.alignment


def _advance_bank(coordinate: RomCoordinate) -> RomCoordinate:
    """Never reached when ``place_shard`` is set; kept for the policy contract."""
    return RomCoordinate(
        node_id=coordinate.node_id,
        reticle=coordinate.reticle,
        tile=coordinate.tile,
        bank=coordinate.bank + 1,
    )


def deepseek_v4_array_layout_policy(
    placer: _ArrayPlacer, *, bank_bytes: int = BANK_BYTES, alignment_bytes: int = ROM_ROW_BYTES
) -> RomLayoutPolicy:
    # A region alignment must cover a whole ROM row.  The product alignment is
    # the 4 KiB row; a test that shrinks the alignment to fit tiny synthetic
    # experts shrinks the row with it, which is a fixture convenience and not
    # a physical claim.
    return RomLayoutPolicy(
        alignment_bytes=alignment_bytes,
        row_bytes=min(ROM_ROW_BYTES, alignment_bytes),
        resource_bytes=bank_bytes,
        spare_row_fraction=0.02,
        minimum_spare_rows=4,
        spare_columns_per_bank=8,
        base_address=0,
        advance_resource=_advance_bank,
        shard_bytes=placer.shard_bytes,
        place_shard=placer.place_shard,
    )


# ---------------------------------------------------------------------------
# Capability
# ---------------------------------------------------------------------------
def deepseek_v4_array_rom_capability(
    *,
    max_context_positions: int = MAX_CONTEXT_POSITIONS,
    vocabulary_size: int = 129280,
    expert_count: int = 256,
    experts_per_token: int = 6,
    node_count: int = NODE_COUNT,
    bank_bytes: int = BANK_BYTES,
    expert_banks: int = EXPERT_BANKS,
    dense_banks: int = DENSE_BANKS,
) -> Capability:
    """The exact limits of the 32-node ROM array.

    Topology class, node count, link record and engine lane mix are the HBM
    cluster's; limits and numeric contracts are the DeepSeek ROM program's;
    memory is per node.
    """
    if node_count != NODE_COUNT:
        raise DeepSeekV4ArrayError(
            f"CLUSTER_32 declares exactly {NODE_COUNT} nodes; {node_count} requested"
        )
    if expert_count % node_count:
        raise DeepSeekV4ArrayError(
            f"{expert_count} experts do not divide into {node_count} owners"
        )
    geometry = array_geometry(
        node_count=node_count,
        bank_bytes=bank_bytes,
        expert_banks=expert_banks,
        dense_banks=dense_banks,
    )
    capability = Capability(
        capability_id="",
        topology_class=int(TopologyClass.CLUSTER_32),
        features=tuple(int(f) for f in CAPABILITY_FEATURES),
        limits={
            "max_instructions": 8192,
            "max_descriptors": 65536,
            "max_loop_depth": 4,
            "max_loop_trip": 4096,
            "max_retired_work": 1 << 26,
            # The data-bearing reduction adds three events per routed body;
            # the cluster chip's 1,024-entry scoreboard is what the shared
            # RTL implements.
            "max_events": 1024,
            "max_event_id": 1023,
            "max_outstanding_per_queue": 32,
            "max_context_positions": max_context_positions,
            "max_expert_ids": expert_count,
            "max_topk": max(experts_per_token, 8),
            "max_vocabulary": vocabulary_size,
            "max_sessions": 16,
            "max_nodes": node_count,
            "max_state_resources": 16,
        },
        numeric_contracts=NUMERIC_CONTRACTS,
        engines={name: dict(spec) for name, spec in CLUSTER_ENGINES.items()},
        memory={
            "rom": {
                "bytes": geometry["node_rom_bytes"],
                "banks": expert_banks + dense_banks,
            },
            "sram": {"bytes": SRAM_BYTES, "banks": 32},
            "hbm": {
                "bytes": HBM_BYTES,
                "channels": 8,
                "burst_bytes": 64,
                # ``bytes`` is the replicated live set this build declares;
                # the two physical fields are the five-stack die-edge figure.
                # The array_geometry notes say which is which.
                "physical_stacks": HBM_STACKS_PER_NODE,
                "physical_bytes": PHYSICAL_HBM_BYTES,
            },
        },
        link=dict(CLUSTER_32_LINK),
        technology_view="rom_array_cluster_32_declared_v1",
    )
    capability.validate()
    return capability


PROFILES = {"rom-deepseek-v4-array-32": deepseek_v4_array_rom_capability}


# ---------------------------------------------------------------------------
# Topology and fabric
# ---------------------------------------------------------------------------
def _route_table_digest(plan: RomImagePlan) -> bytes:
    """Digest of the per-node shard table, the physical map the topology binds."""
    digest = hashlib.sha256()
    for region in plan.regions:
        digest.update(region.key.encode())
        for shard in region.shards:
            digest.update(bytes(str(shard.to_list()), "ascii"))
    return digest.digest()


def _array_topology_factory(*, node_count: int, epoch: int, link: Mapping[str, int]):
    def emit(builder, plan: RomImagePlan) -> int:
        repair = plan.repair_map
        nodes = sorted({shard.coordinate.node_id for r in plan.regions for shard in r.shards})
        if nodes and (nodes[0] < 0 or nodes[-1] >= node_count):
            raise DeepSeekV4ArrayError(
                f"the region plan places shards on nodes {nodes[0]}..{nodes[-1]} "
                f"but the array declares {node_count}"
            )
        endpoints = int(link.get("endpoints_per_node", 8))
        return builder.topology(
            topology_class=TopologyClass.CLUSTER_32,
            node_count=node_count,
            reticle_count=0,
            tiles_per_reticle=0,
            local_node_id=0,
            local_reticle_id=0,
            local_tile_id=0,
            # intra-domain NVLink-class, inter-domain scale-out, and the
            # reduction class the ROM traffic semantics reserve for collectives
            link_class_count=3,
            active_resource_count=len(repair.active_resources),
            quarantined_resource_count=len(repair.quarantine),
            hbm_bytes_per_node=HBM_BYTES,
            sram_bytes_per_node=SRAM_BYTES,
            link_count=node_count * endpoints,
            route_group_count=1,
            epoch=epoch,
            bisection_link_count=int(link.get("bisection_links", 0)),
            active_resource_digest=repair.active_resource_digest,
            quarantine_digest=repair.quarantine_digest,
            route_table_digest=_route_table_digest(plan),
            health_digest=repair.health_digest,
            key="topology",
        )

    return emit


def _array_link_plan_factory(*, chunk_bytes: int):
    """The cluster critical path for one compressed layer body.

    The same six services the wafer plan issues, ``NODE``-scoped over the whole
    cluster, with one difference that is the point of this backend: the expert
    reduction is **data-bearing**.  It is placed *before* the first reduction
    kernel and reduces the most recent ``ROUTED_MATMUL``'s output across the
    32 owners, so ``EXPERT_REDUCE`` on every node reads the full sum.
    """

    def plan(run: LayerRun, kinds: Sequence[str]) -> list[LinkStep]:
        steps: list[LinkStep] = [
            LinkStep(
                position=0,
                where="before",
                link_sub=int(Link.MULTICAST),
                collective_op=int(CollectiveOp.BROADCAST),
                label="activation_multicast",
                participant_scope=ParticipantScope.NODE,
                byte_extent=chunk_bytes,
                route_class=0,
                virtual_channel=0,
            )
        ]
        dispatch_at: int | None = None
        gather_at: int | None = None
        # One data-bearing reduction per routed group: the EXPERT_REDUCE that
        # consumes the group's last routed contraction.  A body may hold more
        # than one group (the released graph compresses two layers into one
        # body), and an EXPERT_REDUCE with no routed contraction ahead of it
        # (the hyper-connection reduction) is not a routed group.
        fed_reductions: list[int] = []
        pending_routed: int | None = None
        for position, kind in enumerate(kinds):
            if dispatch_at is None and kind in _DISPATCH_KINDS:
                dispatch_at = position
            if gather_at is None and kind in _GATHER_KINDS:
                gather_at = position
            if kind == "ROUTED_MATMUL":
                pending_routed = position
            elif kind == "EXPERT_REDUCE":
                if pending_routed is not None:
                    fed_reductions.append(position)
                pending_routed = None
        last = max(len(kinds) - 1, 0)
        if gather_at is None:
            gather_at = min(1, last)
        steps.append(
            LinkStep(
                position=gather_at,
                where="before",
                link_sub=int(Link.GATHER),
                collective_op=int(CollectiveOp.ALL_GATHER),
                label="sparse_index_gather",
                participant_scope=ParticipantScope.NODE,
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
                    participant_scope=ParticipantScope.NODE,
                    byte_extent=chunk_bytes,
                    route_class=2,
                    virtual_channel=2,
                )
            )
        if fed_reductions:
            for ordinal, position in enumerate(fed_reductions):
                steps.append(
                    LinkStep(
                        position=position,
                        where="before",
                        link_sub=int(Link.COLLECTIVE),
                        collective_op=int(CollectiveOp.SUM),
                        label=(
                            "expert_reduction"
                            if ordinal == 0
                            else f"expert_reduction_{ordinal}"
                        ),
                        participant_scope=ParticipantScope.NODE,
                        reduction_contract=_COLLECTIVE_REDUCTION_CONTRACT,
                        byte_extent=chunk_bytes,
                        # Route class 2 / VC 2 is what the ROM lowering's
                        # traffic semantics assign every COLLECTIVE (the
                        # wafer's expert reduction rides the same class).  The
                        # HBM cluster numbers its expert all-reduce "route
                        # class 3"; the meaning -- the owner-partial sum before
                        # EXPERT_REDUCE -- is the same and is what the checker
                        # proves.
                        route_class=2,
                        virtual_channel=2,
                        data_from_kind="ROUTED_MATMUL",
                    )
                )
        else:
            # A dense body has no owner partials to sum; the wafer plan still
            # issues its reduction service there as a traffic-modelling step,
            # and the checker derives one collective per band from the graph
            # anchors, so the array keeps the same fabric path.
            dense_reduce = next(
                (i for i, kind in enumerate(kinds) if kind in _REDUCE_KINDS), last
            )
            steps.append(
                LinkStep(
                    position=dense_reduce,
                    where="after",
                    link_sub=int(Link.COLLECTIVE),
                    collective_op=int(CollectiveOp.SUM),
                    label="expert_reduction",
                    participant_scope=ParticipantScope.NODE,
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
                participant_scope=ParticipantScope.NODE,
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
                participant_scope=ParticipantScope.NODE,
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
def deepseek_v4_array_rom_policy(
    *,
    defects: Sequence[DefectRecord] = (),
    node_count: int = NODE_COUNT,
    bank_bytes: int = BANK_BYTES,
    expert_banks: int = EXPERT_BANKS,
    dense_banks: int = DENSE_BANKS,
    alignment_bytes: int = ROM_ROW_BYTES,
    sram_budget_bytes: int = SRAM_BYTES,
    epoch: int = 1,
    chunk_bytes: int = 1 << 16,
    token_block_rows: int = TOKEN_BLOCK_ROWS,
    new_token_budget_cap: int | None = None,
    notes: Mapping[str, Any] | None = None,
) -> tuple[RomTargetPolicy, _ArrayPlacer]:
    placer = _ArrayPlacer(
        node_count=node_count,
        bank_bytes=bank_bytes,
        expert_banks=expert_banks,
        dense_banks=dense_banks,
        alignment=alignment_bytes,
        sharded_roles=SHARDED_ROLES,
    )
    geometry = array_geometry(
        node_count=node_count,
        bank_bytes=bank_bytes,
        expert_banks=expert_banks,
        dense_banks=dense_banks,
    )
    policy = RomTargetPolicy(
        product=PRODUCT,
        target_id=TARGET_ID,
        backend=BACKEND,
        topology_class=TopologyClass.CLUSTER_32,
        layout=deepseek_v4_array_layout_policy(
            placer, bank_bytes=bank_bytes, alignment_bytes=alignment_bytes
        ),
        sram_budget_bytes=sram_budget_bytes,
        # Token blocks bound the live activation window and, here, the
        # participant slot of the data-bearing expert all-reduce: one block of
        # partial rows per node per LINK step.  The wafer runs one block over
        # the whole declared context; a 32-way participant array of that
        # block would not fit a 32-bit view stride.
        token_block_rows=token_block_rows,
        tile_rows=128,
        tile_cols=128,
        tile_depth=256,
        defects=tuple(defects),
        features=PROGRAM_FEATURES,
        place_region=placer.place_region,
        emit_topology=_array_topology_factory(
            node_count=node_count, epoch=epoch, link=CLUSTER_32_LINK
        ),
        link_plan=_array_link_plan_factory(chunk_bytes=chunk_bytes),
        bank_shards=node_count,
        node_sharded_roles=SHARDED_ROLES,
        new_token_budget_cap=new_token_budget_cap,
        notes={
            "host_submission": "one submission targets the whole 32-node array",
            "partition": geometry["partition"],
            "physical_boundary": "cluster_32_reticle_class_rom_chips",
            "array_geometry": geometry,
            **dict(notes or {}),
        },
    )
    return policy, placer


def _prove_uniform_node_addresses(plan: RomImagePlan, node_count: int) -> None:
    """Every node's copy of a sharded region sits at one node-local address.

    The symmetric ``MEMORY_OBJECT`` descriptor carries one ``base_address`` and
    one ``bank_or_tile``; that is only true if shard ``k`` and shard ``k + N``
    (the next slot's range on the same node) and every other node's shard for
    the same slot sit at the same bank and address.  Checked, not assumed.
    """
    for region in plan.regions:
        if region.role not in SHARDED_ROLES:
            continue
        by_slot_shard: dict[int, set[tuple[int, int]]] = {}
        for index, shard in enumerate(region.shards):
            local = index // node_count
            by_slot_shard.setdefault(local, set()).add(
                (shard.coordinate.bank, shard.resource_address)
            )
            if shard.coordinate.node_id != index % node_count:
                raise DeepSeekV4ArrayError(
                    f"region {region.key!r} shard {index} sits on node "
                    f"{shard.coordinate.node_id}; consecutive ownership puts it on "
                    f"node {index % node_count}"
                )
        for local, places in by_slot_shard.items():
            if len(places) != 1:
                raise DeepSeekV4ArrayError(
                    f"region {region.key!r} local shard {local} sits at "
                    f"{sorted(places)} across nodes; the node-local address must be "
                    "the same on every node"
                )
        if region.pad_bytes:
            raise DeepSeekV4ArrayError(
                f"sharded region {region.key!r} carries {region.pad_bytes} pad "
                "bytes; a node-sharded region must be whole owner strides"
            )


def build_deepseek_v4_array_rom_deployment(
    graph: KernelGraph,
    *,
    capability: Capability | None = None,
    defects: Sequence[DefectRecord] = (),
    weight_storage_class: StorageClass = StorageClass.ROM,
    node_count: int = NODE_COUNT,
    bank_bytes: int = BANK_BYTES,
    expert_banks: int = EXPERT_BANKS,
    dense_banks: int = DENSE_BANKS,
    alignment_bytes: int = ROM_ROW_BYTES,
    epoch: int = 1,
    token_block_rows: int = TOKEN_BLOCK_ROWS,
    deployment_id: int = 1,
    generation: int = 1,
    notes: Mapping[str, Any] | None = None,
) -> tuple[Deployment, RomImagePlan]:
    """Lower ``graph`` onto the 32-node DeepSeek ROM array."""
    capability = capability or deepseek_v4_array_rom_capability(
        node_count=node_count,
        bank_bytes=bank_bytes,
        expert_banks=expert_banks,
        dense_banks=dense_banks,
    )
    if capability.topology_class != int(TopologyClass.CLUSTER_32):
        raise DeepSeekV4ArrayError(
            "the DeepSeek ROM array is a CLUSTER_32 target; a wafer or single-chip "
            "capability cannot host it"
        )
    if int(capability.limits["max_nodes"]) != node_count:
        raise DeepSeekV4ArrayError(
            f"capability admits {capability.limits['max_nodes']} nodes, build "
            f"asked for {node_count}"
        )
    policy, placer = deepseek_v4_array_rom_policy(
        defects=defects,
        node_count=node_count,
        bank_bytes=bank_bytes,
        expert_banks=expert_banks,
        dense_banks=dense_banks,
        alignment_bytes=alignment_bytes,
        epoch=epoch,
        token_block_rows=token_block_rows,
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
    _prove_uniform_node_addresses(plan, node_count)

    # Per-node bytes: node 0 physically holds the dense copy plus its expert
    # shards; every other node holds the same expert bytes plus a physical
    # replica of the dense copy.  The plan records node 0's copy once.
    per_node_sharded = sum(
        s.bytes for r in plan.regions if r.role in SHARDED_ROLES for s in r.shards
        if s.coordinate.node_id == 0
    )
    dense_bytes = sum(r.payload_bytes + r.pad_bytes for r in plan.regions if r.role not in SHARDED_ROLES)
    sharded_total = sum(r.payload_bytes + r.pad_bytes for r in plan.regions if r.role in SHARDED_ROLES)
    per_node = per_node_sharded + dense_bytes
    declared = int(capability.memory["rom"]["bytes"])
    if per_node > declared:
        raise DeepSeekV4ArrayError(
            f"one node needs {per_node} ROM bytes ({per_node_sharded} sharded + "
            f"{dense_bytes} replicated dense) but the capability declares {declared}"
        )
    geometry = array_geometry(
        node_count=node_count,
        bank_bytes=bank_bytes,
        expert_banks=expert_banks,
        dense_banks=dense_banks,
    )
    lowering.builder.notes["array_placement"] = {
        "node_count": node_count,
        "experts_per_node": int(capability.limits["max_expert_ids"]) // node_count,
        "sharded_region_count": sum(1 for r in plan.regions if r.role in SHARDED_ROLES),
        "sharded_rom_bytes_total": sharded_total,
        "sharded_rom_bytes_per_node": per_node_sharded,
        "replicated_dense_rom_bytes_per_node": dense_bytes,
        "rom_bytes_per_node": per_node,
        "rom_bytes_array_physical": per_node * node_count,
        "rom_bytes_plan_unique": plan.rom_bytes,
        "dense_replication_factor": node_count,
        "expert_banks_used_per_node": len(
            {
                s.coordinate.bank
                for r in plan.regions
                if r.role in SHARDED_ROLES
                for s in r.shards
                if s.coordinate.node_id == 0
            }
        ),
        "dense_banks_used": len(
            {
                s.coordinate.bank
                for r in plan.regions
                if r.role not in SHARDED_ROLES
                for s in r.shards
            }
        ),
        "implied_rom_area_mm2_per_node": {
            "at_wafer_backend_usable_density": per_node
            / WAFER_BACKEND_USABLE_DENSITY_BYTES_MM2,
            "at_roofline_n5_array_density": per_node / ROOFLINE_N5_ROM_DENSITY_BYTES_MM2,
            "reticle_area_mm2": RETICLE_AREA_MM2,
            "note": (
                "the replicated dense store is the price of expert-parallel "
                "ownership without column-sharded dense compute; the iso-area "
                "rule (plan section 3.5) derives the comparator from these bytes, "
                "not from 32 x 815 mm2"
            ),
        },
    }
    lowering.builder.notes["array_geometry"] = geometry
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
    if topology is not None and int(topology) != int(TopologyClass.CLUSTER_32):
        raise DeepSeekV4ArrayError(
            f"the DeepSeek ROM array is a CLUSTER_32 target; topology class "
            f"{int(topology)} was requested"
        )
    deployment, _plan = build_deepseek_v4_array_rom_deployment(
        graph,
        capability=capability,
        deployment_id=deployment_id,
        generation=generation,
        **kwargs,
    )
    return deployment


__all__ = [
    "BACKEND",
    "BANK_BYTES",
    "DENSE_BANKS",
    "DeepSeekV4ArrayError",
    "EXPERT_BANKS",
    "NODE_COUNT",
    "PROFILES",
    "TARGET_ID",
    "array_geometry",
    "build_deepseek_v4_array_rom_deployment",
    "deepseek_v4_array_rom_capability",
    "deepseek_v4_array_rom_policy",
    "lower_to_abi3",
]
