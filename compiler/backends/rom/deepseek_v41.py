"""DeepSeek-V4.1-Flash immutable-ROM lowering for a two-wafer logical device.

Physical boundary
-----------------

The V4 wafer product (:mod:`compiler.backends.rom.deepseek_v4`) is one
wafer-scale logical device presented to the host as one ABI node.  V4.1-Flash
does not fit one: 307.5 GB of weights against a 192 GiB wafer ROM.  The primary
target is therefore **two** wafer-scale logical devices --
``TopologyClass.WAFER_LOGICAL_DEVICE`` with ``max_nodes 2`` -- carrying one
deployment, one session, one event and transaction namespace and one
submission, joined by the ``inter_wafer`` link class at the package boundary.

Everything else about the silicon is the V4 product unchanged, and is imported
rather than restated: the 8x6 stitched reticle grid derived from the published
wafer-scale area, the 16 MiB tile, the 256 tiles per reticle field, the 4,096 B
ROM row, the SRAM and HBM attachment, and the spare-row/spare-column repair
inventory.  A V4.1 module that re-derived that geometry would be a second place
for it to drift.

What is new, and why each piece is derived rather than written down
------------------------------------------------------------------

*   **A stage axis on the placer.**  :class:`_TwoWaferPlacer` is the V4
    ``_WaferPlacer`` with one cursor per wafer instead of one for the machine.
    Which wafer a region lands on comes from :func:`deepseek_v41_stage_plan`,
    which partitions the *layer runs* of the neutral graph, not a written-down
    layer index.

*   **The shared-cache placement rule (plan section 6.1).**  CSA2 gives some
    layers a global KV cache that later layers read.  The rule is: every reader
    of a shared cache sits on the stage that owns it.  The stage plan derives
    the owner/reader groups from the graph's own ``state_reads`` and
    ``state_writes`` and refuses any cut that would split one, so the rule holds
    by construction; ``shared_state_locality`` in
    :mod:`compiler.backends.rom.common.check` then proves it from the emitted
    descriptors, independently of anything here.

*   **The partition itself.**  A contiguous minimax partition of the per-run ROM
    inventory, subject to the sharing groups.  For the released 40-layer model
    with its four CSA2 owners this lands on layers 0-19 and 20-39 with the head
    and embedding on the second wafer -- the partition plan section 3.1 names --
    but it is computed from the graph every build, so a different layer count,
    expert count or owner set moves it instead of silently mismatching.

*   **The cross-wafer payload.**  Derived from the tensors that actually cross
    the cut: the per-token bytes of every tensor a kernel on one stage produces
    and a kernel on the next stage reads.  For the released model that is the
    four mHC residual streams at BF16, 4 x 5,120 x 2 = 40,960 B, which is the
    ``cross_stage_payload_bytes_per_user_step`` the roofline already prices.
    Nothing here asserts that number.

*   **One inter-wafer step per token.**  A ``LINK.REMOTE_DMA`` on route class
    ``inter_wafer``, naming both endpoints, issued inside the layer loop of the
    first run of each later stage.  It is a remote DMA and not the on-wafer
    ``LINK.SEND`` because the two are different traffic on different fabric: the
    unicast is a tile-to-tile hop inside one stitched device, and this is an
    endpoint-initiated transfer across a package boundary, whose direction the
    LINK engine resolves from ``source_node``/``destination_node`` against the
    admitted topology's ``local_node_id``.

*   **The Engram tables.**  Plan section 3.4 puts them in wafer-edge HBM as a
    load-once, read-only resident region, and that is where this backend places
    them: :func:`resident_hbm_region` derives the set structurally, the bytes
    are planned as ``residency="hbm"`` regions of the same region plan, and the
    emitted objects are ``StorageClass.HBM`` with the same ``READ | IMMUTABLE``
    permissions a ROM object carries.  They are therefore counted **once**.
    Before this they were declared in the capability's
    ``memory.hbm.resident_region_bytes`` *and* placed in the ROM image, which
    for the released model is 202,758,032,400 bytes paid for twice -- enough on
    its own to take the image from 72.4% of the two-wafer ROM to 121.6% of it.

    Moving them was a contract change in three places, not a backend edit, and
    none of the three lost a rule:
    :mod:`compiler.backends.rom.common.inverse` now proves a resident region
    under the identical tiling, reconstruction, digest, padding and
    placement-uniqueness rules and substitutes only the storage class, and
    additionally proves no object backs both stores;
    :mod:`compiler.backends.rom.common.check`'s ``resident_hbm_region`` rule
    now also requires -- on a machine whose capability prices a resident
    region -- that the table objects be HBM objects owned by a resident region
    of the plan, and that the reserve fit what the capability declares; and
    :mod:`compiler.backends.rom.common.image` plans, places and digest-binds
    the resident regions beside the ROM ones while keeping them out of
    ``rom_bytes``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from compiler.ir.v3.kernel_ir import KernelGraph, Symbolic, Tensor
from runtime.abi3.capability import Capability
from runtime.abi3.constants import (
    DTYPE_BITS,
    Feature,
    Link,
    NO_NODE,
    NodeClass,
    ParticipantScope,
    StorageClass,
    TopologyClass,
)
from runtime.abi3.deployment import Deployment
from runtime.abi3.descriptors import CollectiveOp

from .common.image import (
    DTYPE_BY_NAME,
    DefectRecord,
    ResidentHbmPolicy,
    RomCoordinate,
    RomImagePlan,
    RomLayoutPolicy,
)
from .common.program import (
    GraphAnalysis,
    LayerRun,
    LinkStep,
    RomLowering,
    RomTargetPolicy,
    WEIGHT_ROLES,
    analyze,
)
from .deepseek_v4 import (
    HBM_BYTES,
    MAX_RETICLES,
    RETICLE_COLUMNS,
    RETICLE_ROWS,
    ROM_ROW_BYTES,
    SRAM_BYTES,
    TILES_PER_RETICLE,
    TILE_ROM_BYTES,
    _route_table_digest,
    deepseek_v4_layout_policy,
    wafer_geometry,
)
from .deepseek_v4 import NUMERIC_CONTRACTS as V4_NUMERIC_CONTRACTS

PRODUCT = "deepseek-v4.1-flash-rom"
TARGET_ID = "deepseek-v4.1-flash-rom-wafer-2"
BACKEND = "rom.wafer_logical_device"

#: Wafer-scale logical devices this product compiles for.  Two, from the
#: analytical layer's own answer for this model at the mandatory context:
#: ``results/iso-node/leading_node_market/analytical.json``, ``wafer_stages``
#: for ``DeepSeek-V4.1-Flash-engram-host`` on the central N4-class envelope.
#: It is a parameter of every entry point below, not a constant folded into
#: one: a third wafer is a capability and a partition, not a rewrite.
STAGE_COUNT = 2

#: Link classes.  The three the V4 wafer declares -- intra-reticle mesh,
#: stitched inter-reticle mesh, HBM-attachment ring -- plus ``inter_wafer``,
#: the class the roofline prices at an assumed 5 us hop swept 1 to 10 us.  A
#: one-stage build declares three, because a machine with one wafer has no
#: inter-wafer hop to declare.
INTRA_WAFER_LINK_CLASSES = 3
INTER_WAFER_ROUTE_CLASS = INTRA_WAFER_LINK_CLASSES


def link_class_count(stage_count: int = STAGE_COUNT) -> int:
    """Link classes a ``stage_count``-wafer machine has."""
    return INTRA_WAFER_LINK_CLASSES + (1 if int(stage_count) > 1 else 0)


#: Compatibility the two-wafer capability advertises.  The V4 wafer vector plus
#: bit 8: a wafer-class node that sits on a fabric between nodes needs the
#: inter-chip endpoint bit as well as the wafer bit, and
#: ``Capability._validate_fabric`` refuses a record that claims one without the
#: other.
CAPABILITY_FEATURES = (
    Feature.HOST_QUEUE_ABI,
    Feature.DEPLOYMENT_DESCRIPTOR_ABI,
    Feature.DETERMINISTIC_MICROSEQUENCER,
    Feature.BF16_TENSOR,
    Feature.FP8_E4M3FN_TENSOR,
    Feature.MXFP4_E2M1_E8M0,
    Feature.TRANSACTIONAL_STATE,
    Feature.ON_DEVICE_SELECTION,
    Feature.INTER_CHIP_ENDPOINT,
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
    Feature.INTER_CHIP_ENDPOINT,
    Feature.WAFER_ENDPOINT,
)

#: The four contracts AM-E10 adds, spelled as
#: ``compiler.frontends.v3.deepseek_v41.contract_for`` spells them.  They are
#: listed here rather than imported so that publishing this capability does not
#: depend on a front end that reads a released configuration; the front end's
#: ``CONTRACT_BASE_BY_SOURCE_KIND`` is the source of the names and
#: ``tests/test_deepseek_v41_rom_backend.py`` confronts the two.
V41_NUMERIC_CONTRACTS = (
    "candidate_mask_v1",
    "engram_gate_fp32_v1",
    "fp4_e2m1_s16_e4m3_to_fp8_v1",
    "ngram_hash_u32_v1",
)

NUMERIC_CONTRACTS = tuple(sorted(set(V4_NUMERIC_CONTRACTS) | set(V41_NUMERIC_CONTRACTS)))


class DeepSeekV41RomError(ValueError):
    """Raised when the V4.1 graph will not fit the two-wafer boundary."""


# ---------------------------------------------------------------------------
# Stage plan: which wafer holds which layer run, and what crosses between them
# ---------------------------------------------------------------------------
def _dims(tensor: Tensor) -> tuple[int, ...]:
    """Declared extents, with a symbolic axis counted as one element.

    A cross-stage payload is quoted per token, so the token axis contributes
    one.  Every other axis is a real extent and contributes itself.
    """
    out: list[int] = []
    for dim in tensor.shape:
        out.append(1 if isinstance(dim, Symbolic) else int(dim))
    return tuple(out)


def _tensor_bytes_per_token(tensor: Tensor) -> int:
    """Bytes one token of ``tensor`` occupies on the wire.

    The width comes from ``DTYPE_BY_NAME``, the ROM image planner's own dtype
    table, so a wafer payload and a ROM region agree on what a code costs.  A
    dtype that table does not carry is refused by name rather than guessed at:
    AM-E10's ``fp4_e2m1_s16_e4m3`` is E2M1 elements with one E4M3 scale per 16
    and is not four bits, so inventing a width here would price a cross-wafer
    transfer wrongly and silently.
    """
    elements = 1
    for dim in _dims(tensor):
        elements *= max(dim, 0)
    code = DTYPE_BY_NAME.get(tensor.dtype)
    if code is None:
        raise DeepSeekV41RomError(
            f"tensor {tensor.tensor_id!r} has dtype {tensor.dtype!r}, which "
            "compiler/backends/rom/common/image.py's DTYPE_BY_NAME does not "
            "carry, so the bytes it moves across a wafer boundary cannot be "
            "derived; add the width there, not here"
        )
    return (elements * DTYPE_BITS[code] + 7) // 8


@dataclass(frozen=True, slots=True)
class StagePlan:
    """The two-wafer pipeline policy of plan section 6.2, derived per build."""

    stage_count: int
    #: Layer-run index -> stage.  Every run of the graph appears.
    stage_of_run: Mapping[int, int]
    #: Stage that holds the prologue and epilogue weights: the embedding and
    #: the head.  Plan section 6.2 puts them in the last wafer's slack.
    global_stage: int
    layers_by_stage: tuple[tuple[int, ...], ...]
    runs_by_stage: tuple[tuple[int, ...], ...]
    rom_bytes_by_stage: tuple[int, ...]
    #: ``state_id -> (owner run, tuple of reader runs)`` for every state a run
    #: other than its writer reads.  These are the shared caches of 6.1.
    shared_states: Mapping[str, tuple[int, tuple[int, ...]]]
    #: Bytes one token moves from stage ``k`` to stage ``k+1``, and the tensors
    #: it is made of.
    cross_stage_bytes: tuple[int, ...]
    cross_stage_tensors: tuple[tuple[str, ...], ...]
    #: Bytes one token moves from the prologue's stage into the stage that holds
    #: the first layer run, when they differ.  It is reported rather than
    #: carried by a LINK step because the prologue is not inside a layer loop.
    prologue_crossing_bytes: int
    prologue_crossing_tensors: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "cross_stage_bytes": list(self.cross_stage_bytes),
            "cross_stage_tensors": [list(names) for names in self.cross_stage_tensors],
            "global_stage": self.global_stage,
            "layers_by_stage": [list(layers) for layers in self.layers_by_stage],
            "prologue_crossing_bytes": self.prologue_crossing_bytes,
            "prologue_crossing_tensors": list(self.prologue_crossing_tensors),
            "rom_bytes_by_stage": list(self.rom_bytes_by_stage),
            "runs_by_stage": [list(runs) for runs in self.runs_by_stage],
            "shared_states": {
                state: {"owner_run": owner, "reader_runs": list(readers)}
                for state, (owner, readers) in sorted(self.shared_states.items())
            },
            "stage_count": self.stage_count,
            "stage_of_run": {str(run): stage for run, stage in sorted(self.stage_of_run.items())},
        }


def _run_of_kernel(analysis: GraphAnalysis) -> dict[int, int]:
    """Kernel index -> the layer run that executes it."""
    out: dict[int, int] = {}
    for run in analysis.runs:
        for column in run.body:
            for kernel in column:
                out[kernel.index] = run.index
    return out


def _run_weight_bytes(analysis: GraphAnalysis, tensors: Mapping[str, Tensor]) -> dict[int, int]:
    """Checkpoint bytes each layer run's weights occupy, counted once each."""
    out: dict[int, int] = {}
    for run in analysis.runs:
        seen: set[str] = set()
        total = 0
        for column in run.body:
            for kernel in column:
                for name in kernel.inputs:
                    tensor = tensors.get(name)
                    if tensor is None or tensor.role not in WEIGHT_ROLES:
                        continue
                    for candidate in (name, tensor.scale_tensor_id):
                        if not candidate or candidate in seen:
                            continue
                        scaled = tensors.get(candidate)
                        if scaled is None or scaled.binding is None:
                            continue
                        seen.add(candidate)
                        total += int(scaled.binding.bytes)
        out[run.index] = total
    return out


def _global_weight_bytes(analysis: GraphAnalysis, tensors: Mapping[str, Tensor]) -> int:
    seen: set[str] = set()
    total = 0
    for kernel in (*analysis.prologue, *analysis.epilogue):
        for name in kernel.inputs:
            tensor = tensors.get(name)
            if tensor is None or tensor.role not in WEIGHT_ROLES:
                continue
            for candidate in (name, tensor.scale_tensor_id):
                if not candidate or candidate in seen:
                    continue
                scaled = tensors.get(candidate)
                if scaled is None or scaled.binding is None:
                    continue
                seen.add(candidate)
                total += int(scaled.binding.bytes)
    return total


def _shared_states(
    graph: KernelGraph, run_of: Mapping[int, int]
) -> dict[str, tuple[int, tuple[int, ...]]]:
    """Every state resource a run other than its writer reads.

    This is the CSA2 sharing relation of plan section 6.1, read off the neutral
    graph's own effects rather than off a layer-mode table: the owner is the run
    whose kernels write the resource, the readers are the runs whose kernels
    read it, and a resource read only by its owner is not shared.
    """
    writers: dict[str, set[int]] = {}
    readers: dict[str, set[int]] = {}
    for kernel in graph.kernels:
        run = run_of.get(kernel.index)
        if run is None:
            continue
        for state_id in kernel.state_writes:
            writers.setdefault(state_id, set()).add(run)
        for state_id in kernel.state_reads:
            readers.setdefault(state_id, set()).add(run)
    shared: dict[str, tuple[int, tuple[int, ...]]] = {}
    for state_id, owning in sorted(writers.items()):
        reading = readers.get(state_id, set())
        if len(owning) > 1:
            raise DeepSeekV41RomError(
                f"state resource {state_id!r} is written by layer runs "
                f"{sorted(owning)}; a shared cache has exactly one owner and no "
                "contiguous wafer partition can place two"
            )
        owner = next(iter(owning))
        outside = tuple(sorted(reading - {owner}))
        if outside:
            shared[state_id] = (owner, outside)
    return shared


def _cut_is_legal(
    cut: int, shared: Mapping[str, tuple[int, tuple[int, ...]]]
) -> bool:
    """Whether the boundary *before* run ``cut`` splits no sharing group."""
    for owner, readers in shared.values():
        group = (owner, *readers)
        if min(group) < cut <= max(group):
            return False
    return True


def deepseek_v41_stage_plan(
    graph: KernelGraph,
    *,
    stage_count: int = STAGE_COUNT,
    analysis: GraphAnalysis | None = None,
) -> StagePlan:
    """Partition ``graph``'s layer runs across ``stage_count`` wafers.

    The partition is contiguous (a pipeline stage is a span of layers, not a
    scatter), minimax on ROM bytes (the two wafers are the same silicon, so the
    one that holds more decides the build), and legal under 6.1 (no cut inside
    a shared-cache owner/reader group).  The prologue and epilogue weights --
    the embedding table and the BF16 head -- go to the last stage, which is what
    plan section 6.2 means by "wafer 2's slack".

    A graph whose sharing groups admit no legal contiguous partition is refused
    here rather than placed wrongly: that is a property of the model, and the
    only honest answer is to say which group blocks which cut.
    """
    stage_count = int(stage_count)
    if stage_count < 1:
        raise DeepSeekV41RomError(f"a machine needs at least one wafer; {stage_count} asked")
    analysis = analysis if analysis is not None else analyze(graph)
    runs = analysis.runs
    if not runs:
        raise DeepSeekV41RomError(
            "the graph declares no layer run, so it has no pipeline to partition"
        )
    if stage_count > len(runs):
        raise DeepSeekV41RomError(
            f"{stage_count} wafers cannot each hold a layer run: the graph has "
            f"{len(runs)} run(s)"
        )
    tensors = {tensor.tensor_id: tensor for tensor in graph.tensors}
    run_of = _run_of_kernel(analysis)
    shared = _shared_states(graph, run_of)
    weight_bytes = _run_weight_bytes(analysis, tensors)
    global_bytes = _global_weight_bytes(analysis, tensors)
    global_stage = stage_count - 1

    # Contiguous minimax over legal cuts.  The run count is the layer-run count
    # of one model -- tens, not thousands -- so the exhaustive search over cut
    # tuples is both exact and cheap, and an exact answer is worth more here
    # than a greedy one: the two stages are one deployment and the larger one
    # is the whole machine's ROM requirement.
    counts = len(runs)

    def stage_totals(cuts: Sequence[int]) -> list[int]:
        edges = (0, *cuts, counts)
        totals: list[int] = []
        for stage in range(stage_count):
            span = range(edges[stage], edges[stage + 1])
            total = sum(weight_bytes[runs[index].index] for index in span)
            if stage == global_stage:
                total += global_bytes
            totals.append(total)
        return totals

    best: tuple[int, tuple[int, ...]] | None = None

    def search(stage: int, start: int, chosen: list[int]) -> None:
        nonlocal best
        if stage == stage_count - 1:
            if start > counts - 1:
                return
            totals = stage_totals(chosen)
            candidate = (max(totals), tuple(chosen))
            if best is None or candidate < best:
                best = candidate
            return
        for cut in range(start + 1, counts - (stage_count - stage - 2)):
            if not _cut_is_legal(cut, shared):
                continue
            chosen.append(cut)
            search(stage + 1, cut, chosen)
            chosen.pop()

    search(0, 0, [])
    if best is None:
        blocking = sorted(
            f"{state} (owner run {owner}, reader runs {list(readers)})"
            for state, (owner, readers) in shared.items()
        )
        raise DeepSeekV41RomError(
            f"no contiguous {stage_count}-stage partition of {counts} layer runs "
            "leaves every shared cache on one wafer; the groups that span every "
            "candidate cut are:\n  " + "\n  ".join(blocking)
        )
    _worst, cuts = best
    edges = (0, *cuts, counts)
    stage_of_run: dict[int, int] = {}
    runs_by_stage: list[tuple[int, ...]] = []
    layers_by_stage: list[tuple[int, ...]] = []
    for stage in range(stage_count):
        span = [runs[index] for index in range(edges[stage], edges[stage + 1])]
        runs_by_stage.append(tuple(run.index for run in span))
        layers: list[int] = []
        for run in span:
            stage_of_run[run.index] = stage
            layers.extend(run.layers)
        layers_by_stage.append(tuple(sorted(layers)))
    totals = stage_totals(cuts)

    stage_of_kernel = {
        index: stage_of_run[run] for index, run in run_of.items()
    }
    producer = {
        name: kernel for kernel in graph.kernels for name in kernel.outputs
    }
    crossing_names: list[set[str]] = [set() for _ in range(max(stage_count - 1, 0))]
    prologue_names: set[str] = set()
    prologue_indices = {kernel.index for kernel in analysis.prologue}
    for kernel in graph.kernels:
        consumer_stage = stage_of_kernel.get(kernel.index)
        if consumer_stage is None:
            continue
        for name in kernel.inputs:
            tensor = tensors.get(name)
            if tensor is None or tensor.role in WEIGHT_ROLES:
                continue
            source = producer.get(name)
            if source is None:
                continue
            if source.index in prologue_indices:
                if global_stage != consumer_stage:
                    prologue_names.add(name)
                continue
            producer_stage = stage_of_kernel.get(source.index)
            if producer_stage is None or producer_stage >= consumer_stage:
                continue
            for boundary in range(producer_stage, consumer_stage):
                crossing_names[boundary].add(name)
    cross_bytes = tuple(
        sum(_tensor_bytes_per_token(tensors[name]) for name in sorted(names))
        for names in crossing_names
    )
    cross_tensors = tuple(tuple(sorted(names)) for names in crossing_names)
    return StagePlan(
        stage_count=stage_count,
        stage_of_run=dict(sorted(stage_of_run.items())),
        global_stage=global_stage,
        layers_by_stage=tuple(layers_by_stage),
        runs_by_stage=tuple(runs_by_stage),
        rom_bytes_by_stage=tuple(totals),
        shared_states=dict(sorted(shared.items())),
        cross_stage_bytes=cross_bytes,
        cross_stage_tensors=cross_tensors,
        prologue_crossing_bytes=sum(
            _tensor_bytes_per_token(tensors[name]) for name in sorted(prologue_names)
        ),
        prologue_crossing_tensors=tuple(sorted(prologue_names)),
    )


# ---------------------------------------------------------------------------
# Placement
# ---------------------------------------------------------------------------
#: The region-key grammar :meth:`RomLowering.plan_regions` emits.  ``place_region``
#: is handed a key, a role, a request index and a size, and the stage axis needs
#: the layer run, which only the key carries.  Reading it is a stated contract
#: between the two modules, not a guess: a key this grammar does not cover is
#: refused rather than placed on a default wafer.
_LAYER_KEY_PREFIX = "rom.r"
_GLOBAL_KEY_PREFIX = "rom.global."


def region_stage(key: str, plan: StagePlan) -> int:
    """Which wafer the region named ``key`` belongs to."""
    if key.startswith(_GLOBAL_KEY_PREFIX):
        return plan.global_stage
    if key.startswith(_LAYER_KEY_PREFIX):
        head, _, _ = key[len(_LAYER_KEY_PREFIX) :].partition(".")
        if head.isdigit():
            run = int(head)
            try:
                return plan.stage_of_run[run]
            except KeyError:
                raise DeepSeekV41RomError(
                    f"ROM region {key!r} names layer run {run}, which the stage "
                    f"plan does not place (it places {sorted(plan.stage_of_run)})"
                ) from None
    raise DeepSeekV41RomError(
        f"ROM region key {key!r} is neither {_GLOBAL_KEY_PREFIX}* nor "
        f"{_LAYER_KEY_PREFIX}<run>.*; the two-wafer placer cannot tell which "
        "wafer it belongs to"
    )


class _TwoWaferPlacer:
    """Sequential tile packing, one cursor per wafer.

    The V4 placer keeps one cumulative byte count for the machine, so region
    ``n`` starts where region ``n-1`` ended.  Two wafers are two ROM address
    spaces: each keeps its own cursor, and both start at tile zero.
    """

    def __init__(
        self,
        *,
        tile_rom_bytes: int,
        tiles_per_reticle: int,
        alignment: int,
        stage_plan: StagePlan,
    ) -> None:
        self.tile_rom_bytes = tile_rom_bytes
        self.tiles_per_reticle = tiles_per_reticle
        self.alignment = alignment
        self.stage_plan = stage_plan
        self.cumulative: dict[int, int] = {}

    def __call__(self, key: str, role: str, index: int, size_bytes: int) -> RomCoordinate:
        node = region_stage(key, self.stage_plan)
        used = self.cumulative.get(node, 0)
        tile = used // self.tile_rom_bytes
        aligned = (size_bytes + self.alignment - 1) // self.alignment * self.alignment
        self.cumulative[node] = used + aligned
        return RomCoordinate(
            node_id=node,
            reticle=tile // self.tiles_per_reticle,
            tile=tile,
            bank=0,
        )


def deepseek_v41_layout_policy(
    *,
    tile_rom_bytes: int = TILE_ROM_BYTES,
    tiles_per_reticle: int = TILES_PER_RETICLE,
    alignment_bytes: int = ROM_ROW_BYTES,
) -> RomLayoutPolicy:
    """The V4 wafer layout, unchanged, because the silicon is unchanged.

    The stage axis lives in :class:`_TwoWaferPlacer`, which chooses the *first*
    resource of a region.  The layout policy describes how a region that
    overflows one tile finds the next, and the V4 walker already keeps
    ``node_id`` while it advances, so a spilling region stays on its own wafer.
    Restating the row size, the spare inventory and the walker here would be a
    second place for the wafer's geometry to drift.
    """
    return deepseek_v4_layout_policy(
        tile_rom_bytes=tile_rom_bytes,
        tiles_per_reticle=tiles_per_reticle,
        alignment_bytes=alignment_bytes,
    )


# ---------------------------------------------------------------------------
# Capability
# ---------------------------------------------------------------------------
def deepseek_v41_rom_capability(
    *,
    stage_count: int = STAGE_COUNT,
    max_context_positions: int = 1048576,
    vocabulary_size: int = 129280,
    expert_count: int = 384,
    experts_per_token: int = 6,
    candidate_positions: int = 16384,
    resident_region_bytes: int = 202758032400,
    tile_rom_bytes: int = TILE_ROM_BYTES,
    tiles_per_reticle: int = TILES_PER_RETICLE,
    numeric_contracts: Sequence[str] = NUMERIC_CONTRACTS,
) -> Capability:
    """The exact limits of the two-wafer DeepSeek-V4.1-Flash accelerator.

    Every model-shaped argument is the released architecture pin
    ``compiler/frontends/v3/deepseek_v41.py`` confronts against the committed
    ``config.json``, and each is a parameter so that a different release moves
    the record instead of contradicting it:

    ``expert_count``          ``n_routed_experts`` = 384 (V4: 256).
    ``experts_per_token``     ``num_experts_per_tok`` = 6.  The shared expert is
                              a dense FP8 SwiGLU, not a routed selection, so the
                              routed top-k is six and not seven.
    ``candidate_positions``   ``candidate_topk_blocks * candidate_block_size``
                              = 2,048 x 8 = 16,384, the bound plan section 6.3
                              gives ``candidate_pool_bound``.
    ``max_context_positions`` ``max_position_embeddings`` = 1,048,576, the
                              architectural ceiling.
    ``resident_region_bytes`` ``sum(engram_num_embeddings) *
                              (engram_head_dim + engram_n_heads)`` =
                              768,022,850 x (256 + 8) = 202,758,032,400: the two
                              Engram tables' FP8 rows plus one E4M3 scale per
                              head per row.  Plan section 3.4 prices the same
                              region at 202.8 GB of a 1,440 GB store.

    ``memory.rom.bytes`` is the whole machine -- ``stage_count`` wafers of the
    V4 wafer's ROM -- because the schedule checker charges the deployment's ROM
    objects against one budget and the deployment is one program over both
    wafers.  ``memory.hbm.bytes`` is per device, as plan section 6.4 states it.
    """
    stage_count = int(stage_count)
    geometry = wafer_geometry(
        tile_rom_bytes=tile_rom_bytes, tiles_per_reticle=tiles_per_reticle
    )
    if resident_region_bytes > HBM_BYTES:
        raise DeepSeekV41RomError(
            f"the declared resident HBM region is {resident_region_bytes} bytes "
            f"and one wafer's HBM is {HBM_BYTES}"
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
            "max_event_id": 1023,
            "max_outstanding_per_queue": 32,
            "max_context_positions": max_context_positions,
            # The candidate pool CSA2's block selection publishes.  It is a
            # capability limit and not a number in a checker because
            # ``candidate_pool_bound`` has to read its bound from somewhere the
            # deployment is admitted against; a literal in the checker would be
            # the model constant mirrored into a predicate this plan forbids.
            "max_candidate_positions": candidate_positions,
            "max_expert_ids": expert_count,
            "max_topk": experts_per_token,
            "max_vocabulary": vocabulary_size,
            "max_sessions": 16,
            # Two wafer-scale logical accelerators, two ABI nodes, one
            # deployment.
            "max_nodes": stage_count,
            "max_state_resources": 16,
        },
        numeric_contracts=tuple(numeric_contracts),
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
                "bytes": geometry["wafer_rom_bytes"] * stage_count,
                "banks": geometry["max_reticles"] * tiles_per_reticle * stage_count,
            },
            "sram": {"bytes": SRAM_BYTES, "banks": 4096},
            "hbm": {
                "bytes": HBM_BYTES,
                "resident_region_bytes": resident_region_bytes,
            },
        },
        link={
            "class_count": link_class_count(stage_count),
            "reticle_columns": geometry["grid_columns"],
            "reticle_rows": geometry["grid_rows"],
            "tiles_per_reticle": tiles_per_reticle,
        },
        fabric={"node_class": int(NodeClass.WAFER)} if stage_count > 1 else {},
        technology_view="wafer_logical_device_declared_v1",
    )
    capability.validate()
    return capability


#: Factories by published profile name.  One source of truth per published
#: capability file, checked by ``tools/publish_abi3_capabilities.py --check``.
PROFILES = {"rom-deepseek-v41-wafer-2": deepseek_v41_rom_capability}


# ---------------------------------------------------------------------------
# Topology and fabric
# ---------------------------------------------------------------------------
def _wafer_topology_factory(
    *, stage_count: int, tiles_per_reticle: int, epoch: int
):
    def emit(builder, plan: RomImagePlan) -> int:
        repair = plan.repair_map
        reticles = sorted(
            {shard.coordinate.reticle for r in plan.regions for shard in r.shards}
        )
        reticle_count = max(reticles) + 1 if reticles else 1
        if reticle_count > MAX_RETICLES:
            raise DeepSeekV41RomError(
                f"the region plan needs {reticle_count} reticle fields per wafer "
                f"but a wafer stitches {MAX_RETICLES}"
            )
        # Intra-reticle tile mesh and stitched inter-reticle mesh, per wafer,
        # plus one inter-wafer link per adjacent wafer pair: the pipeline is a
        # chain, so ``stage_count - 1`` hops.
        side = int(round(tiles_per_reticle**0.5)) or 1
        intra = 2 * side * (side - 1) * reticle_count
        inter = (
            (RETICLE_COLUMNS - 1) * RETICLE_ROWS + RETICLE_COLUMNS * (RETICLE_ROWS - 1)
        ) * side
        per_wafer = intra + inter
        # ``active_resource_count`` is a **per-device** prefix, like the
        # ``reticle_count`` and ``tiles_per_reticle`` beside it: the frozen
        # verifier bounds it by ``reticle_count * tiles_per_reticle``, which is
        # one wafer's endpoints, and a two-wafer machine that summed both
        # wafers' active tiles into it would describe a device twice its own
        # size.  The busiest wafer is the one the prefix has to cover; the
        # machine's whole active set is authenticated by
        # ``active_resource_digest``, and its per-wafer split is in the region
        # plan the manifest binds.
        by_node: dict[int, int] = {}
        for resource in repair.active_resources:
            by_node[resource[0]] = by_node.get(resource[0], 0) + 1
        active_prefix = max(by_node.values(), default=0)
        return builder.topology(
            topology_class=TopologyClass.WAFER_LOGICAL_DEVICE,
            node_count=stage_count,
            reticle_count=reticle_count,
            tiles_per_reticle=tiles_per_reticle,
            local_node_id=0,
            local_reticle_id=0,
            local_tile_id=0,
            link_class_count=link_class_count(stage_count),
            active_resource_count=active_prefix,
            quarantined_resource_count=len(repair.quarantine),
            hbm_bytes_per_node=HBM_BYTES,
            sram_bytes_per_node=SRAM_BYTES,
            link_count=per_wafer * stage_count + (stage_count - 1),
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


#: Route group a layer's on-fabric steps address, exactly as V4: group ``g`` is
#: reticle ``g``'s tiles and the local endpoint is ``local_reticle_id``, which
#: the emitted topology sets to zero.
_LAYER_ROUTE_GROUP = 0

_COLLECTIVE_REDUCTION_CONTRACT = "dispatch_reduce_expert_outputs_bf16_v1"

_DISPATCH_KINDS = frozenset({"EXPERT_DISPATCH", "ROUTED_MATMUL"})
_GATHER_KINDS = frozenset(
    {
        "ATTENTION_SPARSE",
        "INDEX_TOPK",
        "INDEX_SCORE",
        "ATTENTION_GQA",
        "ATTENTION_DENSE",
        # AM-E10.  A block maximum and a candidate mask are the V4.1 sparse
        # path's own index gather: the mask is what the later INDEX_TOPK scans.
        "BLOCK_MAX",
        "CANDIDATE_MASK",
    }
)
_REDUCE_KINDS = frozenset({"EXPERT_REDUCE", "PARTITION_SUM", "ORDERED_SUM"})


def _wafer_link_plan_factory(*, chunk_bytes: int, stage_plan: StagePlan):
    """The on-fabric critical path of one compressed layer body.

    The five on-wafer collectives and the residual unicast are the V4 wafer's,
    unchanged and for the V4 reasons: they are ``TILE``-scoped (A14), they
    address one reticle field's tile mesh through route group
    :data:`_LAYER_ROUTE_GROUP`, and their participant counts are derived from
    the admitted topology rather than asserted.

    What V4.1 adds is one step: the first layer run of every wafer after the
    first opens its body with a ``LINK.REMOTE_DMA`` that pulls the previous
    wafer's residual streams across the package boundary.  It is one step per
    token and it names both endpoints, because the LINK engine resolves a
    remote DMA's direction by comparing them with the admitted topology's local
    node.
    """

    def plan(run: LayerRun, kinds: Sequence[str]) -> list[LinkStep]:
        steps: list[LinkStep] = []
        stage = stage_plan.stage_of_run.get(run.index)
        if stage is None:
            raise DeepSeekV41RomError(
                f"layer run {run.index} is not placed by the stage plan"
            )
        first_of_stage = bool(
            stage_plan.runs_by_stage[stage]
            and stage_plan.runs_by_stage[stage][0] == run.index
        )
        if stage > 0 and first_of_stage:
            extent = stage_plan.cross_stage_bytes[stage - 1]
            if extent <= 0:
                raise DeepSeekV41RomError(
                    f"wafer {stage} opens at layer run {run.index} but no tensor "
                    f"crosses the boundary from wafer {stage - 1}; a pipeline "
                    "stage that receives nothing is not a stage"
                )
            steps.append(
                LinkStep(
                    position=0,
                    where="before",
                    link_sub=int(Link.REMOTE_DMA),
                    collective_op=int(CollectiveOp.POINT_TO_POINT),
                    label="inter_wafer_residual",
                    participant_scope=ParticipantScope.NODE,
                    participant_count=2,
                    source_node=stage - 1,
                    destination_node=stage,
                    byte_extent=extent,
                    route_class=INTER_WAFER_ROUTE_CLASS,
                    virtual_channel=0,
                )
            )
        steps.append(
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
        )
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
def deepseek_v41_rom_policy(
    *,
    stage_plan: StagePlan,
    defects: Sequence[DefectRecord] = (),
    tile_rom_bytes: int = TILE_ROM_BYTES,
    tiles_per_reticle: int = TILES_PER_RETICLE,
    alignment_bytes: int = ROM_ROW_BYTES,
    sram_budget_bytes: int = SRAM_BYTES,
    epoch: int = 1,
    chunk_bytes: int = 1 << 16,
    target_id: str = TARGET_ID,
    resident_hbm: ResidentHbmPolicy | None = None,
    notes: Mapping[str, Any] | None = None,
) -> RomTargetPolicy:
    geometry = wafer_geometry(
        tile_rom_bytes=tile_rom_bytes, tiles_per_reticle=tiles_per_reticle
    )
    layout = deepseek_v41_layout_policy(
        tile_rom_bytes=tile_rom_bytes,
        tiles_per_reticle=tiles_per_reticle,
        alignment_bytes=alignment_bytes,
    )
    return RomTargetPolicy(
        product=PRODUCT,
        target_id=target_id,
        backend=BACKEND,
        topology_class=TopologyClass.WAFER_LOGICAL_DEVICE,
        layout=layout,
        sram_budget_bytes=sram_budget_bytes,
        tile_rows=128,
        tile_cols=128,
        tile_depth=256,
        defects=tuple(defects),
        features=PROGRAM_FEATURES,
        place_region=_TwoWaferPlacer(
            tile_rom_bytes=tile_rom_bytes,
            tiles_per_reticle=tiles_per_reticle,
            alignment=alignment_bytes,
            stage_plan=stage_plan,
        ),
        emit_topology=_wafer_topology_factory(
            stage_count=stage_plan.stage_count,
            tiles_per_reticle=tiles_per_reticle,
            epoch=epoch,
        ),
        link_plan=_wafer_link_plan_factory(
            chunk_bytes=chunk_bytes, stage_plan=stage_plan
        ),
        resident_hbm=resident_hbm,
        notes={
            "host_submission": "one submission targets both wafers",
            "partition": "layer_pipelined_expert_and_role_striped_tile_rom",
            "physical_boundary": "two_wafer_logical_devices",
            "wafer_geometry": geometry,
            **dict(notes or {}),
        },
    )


def resident_hbm_region(graph: KernelGraph) -> dict[str, Any]:
    """The load-once wafer-edge HBM region of plan section 3.4.

    A resident lookup table is recognised structurally, not by name: it is a
    checkpoint-bound weight operand of an ``EMBEDDING_LOOKUP`` that belongs to a
    *layer*.  The prologue's token embedding has no layer and is an ordinary
    model weight; a table a layer reads every token -- the Engram row table and
    the compressed-id map -- is the resident region, and the two Engram modules
    are exactly the layered embedding lookups this model has.
    """
    tensors = {tensor.tensor_id: tensor for tensor in graph.tensors}
    members: list[dict[str, Any]] = []
    seen: set[str] = set()
    for kernel in graph.kernels:
        if kernel.kind != "EMBEDDING_LOOKUP" or kernel.layer is None:
            continue
        for name in kernel.inputs:
            tensor = tensors.get(name)
            if tensor is None or tensor.role not in WEIGHT_ROLES:
                continue
            for candidate in (name, tensor.scale_tensor_id):
                if not candidate or candidate in seen:
                    continue
                resident = tensors.get(candidate)
                if resident is None or resident.binding is None:
                    continue
                seen.add(candidate)
                members.append(
                    {
                        "bytes": int(resident.binding.bytes),
                        "layer": int(kernel.layer),
                        "tensor_id": candidate,
                    }
                )
    members.sort(key=lambda member: member["tensor_id"])
    return {
        "bytes": sum(member["bytes"] for member in members),
        "layers": sorted({member["layer"] for member in members}),
        "members": members,
        "policy": "load_once_read_only_no_commit_no_scatter",
        "rule": "checkpoint-bound weight of a layered EMBEDDING_LOOKUP",
        "table_count": len(members),
    }


def build_deepseek_v41_rom_deployment(
    graph: KernelGraph,
    *,
    capability: Capability | None = None,
    defects: Sequence[DefectRecord] = (),
    weight_storage_class: StorageClass = StorageClass.ROM,
    stage_count: int | None = None,
    tile_rom_bytes: int = TILE_ROM_BYTES,
    tiles_per_reticle: int = TILES_PER_RETICLE,
    alignment_bytes: int = ROM_ROW_BYTES,
    epoch: int = 1,
    deployment_id: int = 1,
    generation: int = 1,
    target_id: str = TARGET_ID,
    notes: Mapping[str, Any] | None = None,
) -> tuple[Deployment, RomImagePlan]:
    """Lower ``graph`` onto the mandatory two-wafer DeepSeek-V4.1 ROM target."""
    capability = capability or deepseek_v41_rom_capability(
        tile_rom_bytes=tile_rom_bytes, tiles_per_reticle=tiles_per_reticle
    )
    if capability.topology_class != int(TopologyClass.WAFER_LOGICAL_DEVICE):
        raise DeepSeekV41RomError(
            "DeepSeek-V4.1-Flash ROM is a mandatory wafer-scale logical device; a "
            "single-chip or cluster capability cannot host it"
        )
    declared_nodes = int(capability.limits["max_nodes"])
    if stage_count is None:
        stage_count = declared_nodes
    elif int(stage_count) != declared_nodes:
        raise DeepSeekV41RomError(
            f"the build asks for {int(stage_count)} wafer(s) and the capability "
            f"declares {declared_nodes}; the pipeline depth is the node count"
        )
    stage_plan = deepseek_v41_stage_plan(graph, stage_count=int(stage_count))
    resident = resident_hbm_region(graph)
    declared_resident = int(
        capability.memory.get("hbm", {}).get("resident_region_bytes", 0)
    )
    if resident["bytes"] > declared_resident:
        raise DeepSeekV41RomError(
            f"the load-once HBM region needs {resident['bytes']} bytes and the "
            f"capability declares a resident region of {declared_resident}"
        )
    policy = deepseek_v41_rom_policy(
        stage_plan=stage_plan,
        defects=defects,
        tile_rom_bytes=tile_rom_bytes,
        tiles_per_reticle=tiles_per_reticle,
        alignment_bytes=alignment_bytes,
        epoch=epoch,
        target_id=target_id,
        # Every wafer holds the same wafer-edge copy, which is what the
        # capability declares: ``resident_region_bytes`` is per node, and it is
        # the whole table rather than a share of it.  Replication is also what
        # makes every Engram lookup local on whichever stage reads it, so the
        # stage partition never has to place a reader away from its table.
        resident_hbm=ResidentHbmPolicy(
            tensors=frozenset(
                member["tensor_id"] for member in resident["members"]
            ),
            node_shards=1,
            node_id=NO_NODE,
            declared_bytes_per_node=declared_resident,
            alignment_bytes=alignment_bytes,
        ),
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
        raise DeepSeekV41RomError(
            f"the DeepSeek-V4.1 ROM image needs {plan.rom_bytes} bytes but the "
            f"two-wafer capability declares {declared}"
        )
    wafer_rom_bytes = tile_rom_bytes * tiles_per_reticle * MAX_RETICLES
    per_node: dict[int, int] = {}
    for region in plan.regions:
        for shard in region.shards:
            node = shard.coordinate.node_id
            per_node[node] = per_node.get(node, 0) + shard.bytes
    over = {node: used for node, used in per_node.items() if used > wafer_rom_bytes}
    if over:
        raise DeepSeekV41RomError(
            "the layer partition does not fit the wafers it names: "
            + ", ".join(
                f"wafer {node} holds {used} bytes of a {wafer_rom_bytes}-byte ROM"
                for node, used in sorted(over.items())
            )
        )
    if set(per_node) - set(range(stage_plan.stage_count)):
        raise DeepSeekV41RomError(
            f"the region plan places ROM on nodes {sorted(per_node)}, and the "
            f"machine has {stage_plan.stage_count}"
        )
    reticle_rom_bytes = tile_rom_bytes * tiles_per_reticle
    if plan.largest_member_bytes > reticle_rom_bytes:
        raise DeepSeekV41RomError(
            f"the largest indivisible ROM payload is {plan.largest_member_bytes} "
            f"bytes, more than one reticle field's {reticle_rom_bytes}; no legal "
            "wafer placement exists"
        )
    geometry = wafer_geometry(
        tile_rom_bytes=tile_rom_bytes, tiles_per_reticle=tiles_per_reticle
    )
    tiles_used = len(
        {(s.coordinate.node_id, s.coordinate.tile) for r in plan.regions for s in r.shards}
    )
    reticles_used = len(
        {
            (s.coordinate.node_id, s.coordinate.reticle)
            for r in plan.regions
            for s in r.shards
        }
    )
    lowering.builder.notes["wafer_placement"] = {
        "distributed_region_count": sum(1 for r in plan.regions if len(r.shards) > 1),
        "largest_member_bytes": plan.largest_member_bytes,
        "largest_region_bytes": plan.largest_region_bytes,
        "tensor_parallel_member_count": plan.distributed_member_count,
        "max_reticles_per_wafer": geometry["max_reticles"],
        "planned_rom_bytes": plan.rom_bytes,
        "reticles_used": reticles_used,
        # String keys, because this note is serialised into the manifest and a
        # JSON object's keys are strings there; an int-keyed dict would read
        # back differently from the way it was written.
        "rom_bytes_by_node": {str(node): used for node, used in sorted(per_node.items())},
        "tile_rom_bytes": tile_rom_bytes,
        "tiles_per_reticle": tiles_per_reticle,
        "tiles_used": tiles_used,
        "wafer_count": stage_plan.stage_count,
    }
    lowering.builder.notes["wafer_geometry"] = geometry
    lowering.builder.notes["stage_plan"] = stage_plan.to_dict()
    lowering.builder.notes["resident_hbm_region"] = {
        **resident,
        "declared_bytes_per_node": declared_resident,
        "placement": "replicated_wafer_edge_hbm",
        "planned_bytes": plan.resident_bytes,
        "planned_bytes_per_node": {
            str(node): used
            for node, used in plan.resident_bytes_per_node.items()
        },
        "planned_region_count": len(plan.resident_regions),
        "rom_bytes_without_it": plan.rom_bytes,
        "storage_class": StorageClass.HBM.name,
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
    """The shared backend entry point: one neutral graph in, one deployment out.

    ``topology`` is accepted and checked rather than ignored: the wafer-scale
    logical device is mandatory for this product, and two of them is the only
    shipped pipeline depth.
    """
    if topology is not None and int(topology) != int(TopologyClass.WAFER_LOGICAL_DEVICE):
        raise DeepSeekV41RomError(
            f"DeepSeek-V4.1-Flash ROM is a mandatory wafer-scale logical device; "
            f"topology class {int(topology)} was requested"
        )
    deployment, _plan = build_deepseek_v41_rom_deployment(
        graph,
        capability=capability,
        deployment_id=deployment_id,
        generation=generation,
        **kwargs,
    )
    return deployment


__all__ = [
    "BACKEND",
    "CAPABILITY_FEATURES",
    "DeepSeekV41RomError",
    "INTER_WAFER_ROUTE_CLASS",
    "NUMERIC_CONTRACTS",
    "PRODUCT",
    "PROFILES",
    "PROGRAM_FEATURES",
    "STAGE_COUNT",
    "StagePlan",
    "TARGET_ID",
    "V41_NUMERIC_CONTRACTS",
    "build_deepseek_v41_rom_deployment",
    "deepseek_v41_layout_policy",
    "deepseek_v41_rom_capability",
    "deepseek_v41_rom_policy",
    "deepseek_v41_stage_plan",
    "link_class_count",
    "lower_to_abi3",
    "region_stage",
    "resident_hbm_region",
]
