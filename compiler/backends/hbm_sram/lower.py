"""Lower a neutral Tensor Kernel IR v3 graph onto the shared HBM/SRAM chip.

This module is the ABI 3.0 emitter for the conventional accelerator.  It is
deliberately model-blind: there is no model name, no layer count, no head count
and no branch on model identity anywhere in it.  What varies between the Qwen
deployment and the DeepSeek deployment is the *graph* it is handed, the
*checkpoint bindings* inside that graph and the *topology* of the capability it
compiles against.  One node or thirty-two, dense or mixture-of-experts, 8,000
tokens or 200,000: same code path.

Everything is emitted through :class:`runtime.abi3.builder.DeploymentBuilder`,
every opcode comes from :func:`compiler.ir.v3.lowering.engine_for`, and every
operand slot follows ``TA-ABI3-OPCONV-1``.  No private descriptor, no private
opcode, no locally invented slot meaning.

Where the work lives
--------------------
ADR-003 section 5.1 requires compact control flow and section 6.2 defines the
SCHEDULE descriptor as carrying "engine queue, tile mapping, bank/port use, NoC
path, issue window, and resource bound".  Those two together fix the split this
emitter implements:

*Program loops* express what genuinely varies -- **layers** and **token
blocks**.  A forward step is one loop over the layers of a band whose body is
one engine instruction per kernel, wrapped where the token count is symbolic in
a block loop bound by ``Symbol.SPAN_TOKENS``.

*Schedule descriptors* express how one engine instruction is decomposed on the
hardware -- ``tile_rows``, ``tile_cols``, ``tile_depth``, ``bank_mask``,
``port_mask``, ``issue_window``, ``max_outstanding``.  The functional engine
executes the whole contraction named by one operator; the cycle model reads the
same descriptor and costs the tiles, the bank conflicts and the DMA traffic.

Making tiles into program loops instead would retire on the order of 258,000
engine dispatches for one Qwen forward step -- roughly the ABI 2.5 failure this
ABI exists to remove -- while hiding nothing extra, since the tiling is fully
readable out of the descriptor table either way.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping, Sequence

from compiler.ir.v3.kernel_ir import Kernel, KernelGraph, Symbolic, Tensor
from compiler.ir.v3.lowering import engine_for
from runtime.abi3.builder import BuildError, DeploymentBuilder, DynamicTerm
from runtime.abi3.capability import Capability
from runtime.abi3.constants import (
    Control,
    Dma,
    CounterGroup,
    DType,
    Feature,
    IntegrityMode,
    Link,
    Major,
    NO_ID,
    Ordering,
    Permission,
    ReductionOrder,
    Selection,
    State,
    StateClass,
    StorageClass,
    TopologyClass,
    counter_id,
)
from runtime.abi3.crc import sha256
from runtime.abi3.deployment import Deployment, ObjectSource, Segment
from runtime.abi3.descriptors import (
    CollectiveOp,
    Comparison,
    LayoutClass,
    MAX_DYNAMIC_TERMS,
    Phase,
    PredicateKind,
    SelectionMode,
    SelectorKind,
    Symbol,
)

from .plan import (
    KernelPlan,
    _extent_value as _static_extent,
    as_kernel_graph,
    OperandPlan,
    PhysicalPlan,
    PlanError,
    TileConfig,
    build_plan,
    bytes_for,
    dtype_of,
    matrix_shape,
    position_inputs,
    round_up as _round_up,
)

BACKEND_ID = "hbm-sram-abi3"

#: TA-ABI3-OPCONV-1 amendment A7.  The strictly sequential contract is the
#: scalar oracle used for numeric qualification; execution operators declare the
#: blocked contract, which is what a lane array actually does and what an
#: implementation can run at model scale.  Every substitution this table makes
#: is recorded in the deployment notes -- a report that says only "exact" is
#: incomplete, so the artifact names which contract it means.
EXECUTION_CONTRACT: Mapping[str, str] = {
    "bf16_bf16_fp32_sequential_rne_v1": "bf16_bf16_fp32_blocked_rne_v1",
}

#: Which counter namespace observes which engine family.
_COUNTER_GROUP: Mapping[int, CounterGroup] = {
    int(Major.DMA): CounterGroup.MEMORY,
    int(Major.TENSOR): CounterGroup.TENSOR,
    int(Major.VECTOR): CounterGroup.VECTOR_REDUCTION,
    int(Major.ATTENTION): CounterGroup.ATTENTION,
    int(Major.ROUTE): CounterGroup.ROUTE_EXPERT,
    int(Major.REDUCTION): CounterGroup.VECTOR_REDUCTION,
    int(Major.SELECTION): CounterGroup.SELECTION_EOS,
    int(Major.STATE): CounterGroup.STATE,
    int(Major.LINK): CounterGroup.COMMUNICATION,
}

#: Feature bits implied by an element type the program actually uses.
_DTYPE_FEATURE: Mapping[int, Feature] = {
    int(DType.BF16): Feature.BF16_TENSOR,
    int(DType.FP8_E4M3FN): Feature.FP8_E4M3FN_TENSOR,
    int(DType.FP8_E5M2): Feature.FP8_E4M3FN_TENSOR,
    int(DType.MXFP4_E2M1): Feature.MXFP4_E2M1_E8M0,
    int(DType.E8M0_SCALE): Feature.MXFP4_E2M1_E8M0,
}

#: Cluster traffic class -> (LINK subopcode, collective, route class).
#: TA-HBM-3.0 section 3.6's ordered traffic classes, one virtual channel each.
_LINK_OP: Mapping[str, tuple[Link, CollectiveOp, int]] = {
    "expert_dispatch": (Link.SCATTER, CollectiveOp.CONCAT, 0),
    "sparse_gather": (Link.GATHER, CollectiveOp.ALL_GATHER, 1),
    "activation_transfer": (Link.COLLECTIVE, CollectiveOp.ALL_GATHER, 2),
    "reduction": (Link.COLLECTIVE, CollectiveOp.SUM, 3),
    "coordinated_commit": (Link.BARRIER, CollectiveOp.SUM, 4),
}

#: SRAM regions each engine family streams through; the union becomes the
#: schedule's bank mask, which is the cycle model's bank-conflict input.
_ENGINE_REGIONS: Mapping[int, tuple[str, ...]] = {
    int(Major.TENSOR): (
        "sram.activation_stage",
        "sram.weight_stage",
        "sram.accumulator",
    ),
    int(Major.DMA): ("sram.activation_stage", "sram.weight_stage"),
    int(Major.VECTOR): ("sram.vector_stream",),
    int(Major.REDUCTION): ("sram.vector_stream", "sram.accumulator"),
    int(Major.ATTENTION): ("sram.attention_working",),
    int(Major.ROUTE): ("sram.route_index",),
    int(Major.SELECTION): ("sram.vector_stream",),
    int(Major.STATE): ("sram.state_stage",),
    int(Major.LINK): ("sram.link_stage",),
}

_STATE_CLASS: Mapping[str, StateClass] = {
    "kv_cache": StateClass.KV_CACHE,
    "compressed_kv": StateClass.COMPRESSED_KV,
    "token_ring": StateClass.TOKEN_RING,
    "position_cursor": StateClass.POSITION_CURSOR,
    "route_history": StateClass.ROUTE_HISTORY,
    "scratch": StateClass.SCRATCH,
}

_TRANSACTION_KINDS = frozenset({"STATE_PREPARE", "STATE_COMMIT", "STATE_READ"})

#: Element types that address something rather than carry a value.
_INDEX_DTYPES = frozenset({"u32", "i32", "u64", "i64"})


class LoweringError(ValueError):
    """Raised when a graph cannot be expressed in ABI 3.0 on this chip."""


#: The most recent lowering, retained for differential harnesses.
#:
#: A deployment is deliberately opaque -- it names objects, not tensors, because
#: that is what a device consumes.  A harness comparing per-layer activations
#: against a reference needs the other direction: which arena holds which
#: tensor.  That mapping is the *plan's*, so it is exposed here rather than
#: pushed into the artifact, which would put a debugging concern into the wire
#: format.  It is diagnostic state: nothing in the build reads it, and two
#: builds are byte-identical whether or not anything looks at it.
_LAST_LOWERING: "_Emitter | None" = None


def last_lowering() -> "_Emitter":
    """The most recent lowering, for a harness that must locate a tensor."""
    if _LAST_LOWERING is None:
        raise LoweringError("no deployment has been lowered in this process")
    return _LAST_LOWERING


def arena_object_of(tensor_id: str) -> int:
    """The memory object holding ``tensor_id`` in the most recent lowering."""
    lowering = last_lowering()
    key = lowering.plan.activation_keys.get(tensor_id)
    if key is None:
        raise LoweringError(f"{tensor_id!r} has no activation placement")
    slot = lowering.plan.arena_of_key.get(key)
    if slot is None:
        raise LoweringError(f"{tensor_id!r} is not held in an arena")
    return lowering._arena_object[slot]


def lower_to_abi3(
    graph: KernelGraph | Mapping[str, Any] | str,
    capability: Capability,
    *,
    topology: TopologyClass | int | None = None,
    plan: PhysicalPlan | None = None,
    tile: TileConfig | None = None,
    deployment_id: int = 1,
    generation: int = 1,
    target_id: str | None = None,
    backend: str = BACKEND_ID,
) -> Deployment:
    """Lower ``graph`` onto ``capability`` and return the ABI 3.0 deployment.

    ``graph`` may be a :class:`KernelGraph`, a published JSON body, or a path to
    one, so a campaign driver can hand over the artifact it already has.
    """
    graph = as_kernel_graph(graph)
    plan = plan or build_plan(graph, capability, topology=topology, tile=tile)
    emitter = _Emitter(
        graph, capability, plan, deployment_id, generation, target_id, backend
    )
    deployment = emitter.run()
    global _LAST_LOWERING
    _LAST_LOWERING = emitter
    return deployment


def lower_with_plan(
    graph: KernelGraph | Mapping[str, Any] | str,
    capability: Capability,
    *,
    topology: TopologyClass | int | None = None,
    tile: TileConfig | None = None,
    **kwargs: Any,
) -> tuple[Deployment, PhysicalPlan]:
    """Convenience wrapper returning both artifacts."""
    graph = as_kernel_graph(graph)
    plan = build_plan(graph, capability, topology=topology, tile=tile)
    return lower_to_abi3(graph, capability, plan=plan, **kwargs), plan


class _Emitter:
    """One deterministic lowering run."""

    def __init__(
        self,
        graph: KernelGraph,
        capability: Capability,
        plan: PhysicalPlan,
        deployment_id: int,
        generation: int,
        target_id: str | None,
        backend: str,
    ) -> None:
        self.graph = graph
        self.capability = capability
        self.plan = plan
        self.node_count = plan.topology.node_count
        self.tensors = {t.tensor_id: t for t in graph.tensors}
        self.kernels = {k.index: k for k in graph.kernels}
        self.span_max = plan.span_max
        self.builder = DeploymentBuilder(
            target_id=target_id
            or f"{backend}-{TopologyClass(plan.topology.topology_class).name.lower()}",
            model_id=graph.model_id,
            backend=backend,
            capability=capability,
            deployment_id=deployment_id,
            generation=generation,
        )
        # Descriptor caches.  Every key is a tuple of primitives and every miss
        # allocates in emission order, so two runs over the same inputs produce
        # identical descriptor IDs and therefore identical bytes.
        self._numeric: dict[tuple, int] = {}
        self._schedule: dict[tuple, int] = {}
        self._counter: dict[int, int] = {}
        self._views: dict[tuple, int] = {}
        self._waits: dict[tuple, int] = {}
        self._predicates: dict[tuple, int] = {}
        self._weight_object: dict[str, int] = {}
        self._generated_object: dict[str, int] = {}
        self._arena_object: dict[str, int] = {}
        self._sram_object: dict[str, int] = {}
        self._host_object: dict[str, int] = {}
        self._state_objects: dict[str, tuple[int, int]] = {}
        self._state_descriptor: dict[str, int] = {}
        self._event_of_tensor: dict[str, int] = {}
        self._substitutions: dict[str, str] = {}
        self._layer_loop: int | None = None
        self._link_instructions = 0
        self._hoisted: set[str] = set()
        self._transaction_source: dict[tuple[str, str], int] = {}
        self.token_ring_tensor: str | None = None
        self.token_input_tensor: str | None = None
        self._position_inputs = frozenset(position_inputs(graph))
        self.token_ring_object: int = NO_ID
        self.commit_token_object: int = NO_ID

    # -- entry point -----------------------------------------------------
    def run(self) -> Deployment:
        builder = self.builder
        self._declare_topology()
        self._declare_objects()
        self._declare_states()

        self._hoisted = self._compute_hoisted()
        prepared, committed = self._state_transaction_sites()
        for physical_id in sorted(self._state_descriptor):
            if physical_id not in prepared:
                builder.emit(
                    Major.STATE,
                    State.PREPARE,
                    descriptor_id=self._state_descriptor[physical_id],
                    source_operation_id=self._transaction_source.get(
                        ("STATE_PREPARE", physical_id), NO_ID
                    ),
                )

        for unit in self.plan.units:
            if unit.kind == "kernel":
                self._emit_kernel(self.plan.kernel_plan(unit.index))
                continue
            band = self.plan.band(unit.index)
            body = [self.plan.kernel_plan(i) for i in band.body_kernels]
            if band.layer_count > 1:
                loop = builder.loop_control(
                    lower_bound=0,
                    upper_bound=band.layer_count,
                    step=1,
                    counter_class_id=self._counter_class(int(Major.CONTROL)),
                    key=f"loop.band{band.band_id}",
                )
                builder.open_loop(loop)
                self._layer_loop = loop
                for kernel_plan in body:
                    self._emit_kernel(kernel_plan)
                builder.close_loop()
                self._layer_loop = None
            else:
                for kernel_plan in body:
                    self._emit_kernel(kernel_plan)

        # A cluster commits its state as one coordinated transaction: the
        # barrier is the point at which every node agrees the step happened.
        if self.node_count > 1:
            self._emit_link("coordinated_commit", "commit", None, wait=None)
        for physical_id in sorted(self._state_descriptor):
            if physical_id not in committed:
                builder.emit(
                    Major.STATE,
                    State.COMMIT,
                    descriptor_id=self._state_descriptor[physical_id],
                    source_operation_id=self._transaction_source.get(
                        ("STATE_COMMIT", physical_id), NO_ID
                    ),
                )

        builder.emit(Major.CONTROL, Control.COMPLETE)
        self._declare_entrypoints()
        builder.source_identity = {
            "graph_id": self.graph.graph_id,
            "model_id": self.graph.model_id,
            "plan_id": self.plan.plan_id,
            "capability_digest": self.capability.digest,
            "topology_class": int(self.plan.topology.topology_class),
            "node_count": self.node_count,
        }
        builder.notes.update(
            {
                "backend": "hbm_sram",
                "bands": [
                    {
                        "band_id": b.band_id,
                        "first_layer": b.first_layer,
                        "layer_count": b.layer_count,
                        "degraded": b.degraded,
                    }
                    for b in self.plan.bands
                ],
                "link_instructions": self._link_instructions,
                "numeric_contract_substitutions": dict(
                    sorted(self._substitutions.items())
                ),
                "derived_position_inputs": sorted(self._position_inputs),
                "plan_warnings": list(self.plan.warnings),
                "sram_regions": [
                    {
                        "region_id": r.region_id,
                        "offset": r.offset,
                        "size_bytes": r.size_bytes,
                        "bank_mask": r.bank_mask,
                    }
                    for r in self.plan.sram_regions
                ],
                "token_block_rows": self.plan.proofs.get("token_block_rows", 0),
            }
        )
        return builder.finish()

    def _address(self, key: str) -> tuple[int, int]:
        """The planned base address and home channel for one object."""
        placement = self.plan.hbm_map.get(key)
        if placement is None:
            raise LoweringError(
                f"object {key!r} has no address in the plan's HBM map; the "
                "cycle model cannot place an object that names no address"
            )
        return placement.base_address, placement.channel

    # -- declarations ----------------------------------------------------
    def _declare_topology(self) -> None:
        topology = self.plan.topology
        link = dict(self.capability.link)
        self.builder.topology(
            topology_class=TopologyClass(topology.topology_class),
            node_count=topology.node_count,
            local_node_id=0,
            link_class_count=len(topology.link_classes),
            active_resource_count=topology.node_count,
            hbm_bytes_per_node=topology.hbm_bytes_per_node,
            sram_bytes_per_node=topology.sram_bytes_per_node,
            link_count=topology.peers_per_node,
            route_group_count=int(link.get("route_groups", 0)),
            bisection_link_count=int(link.get("bisection_links", 0)),
            route_table_digest=sha256(",".join(topology.link_classes).encode("ascii")),
            key="topology",
        )
        if self.node_count > 1:
            self.builder.require(Feature.INTER_CHIP_ENDPOINT)

    def _declare_objects(self) -> None:
        builder = self.builder
        for group in self.plan.weight_groups:
            segments = tuple(
                Segment(
                    path=s.path, offset=s.file_offset, bytes=s.bytes, sha256=s.sha256
                )
                for s in group.segments
            )
            digest = sha256(
                b"".join(bytes.fromhex(s.sha256) for s in group.segments if s.sha256)
            )
            base, channel = self._address(f"weight.{group.group_id}")
            self._weight_object[group.group_id] = builder.memory_object(
                storage_class=StorageClass.HBM,
                size_bytes=group.size_bytes,
                source=ObjectSource(
                    kind="segments", size_bytes=group.size_bytes, segments=segments
                ),
                permissions=int(Permission.READ | Permission.IMMUTABLE),
                base_address=base,
                bank_or_tile=channel,
                alignment_log2=12,
                integrity_mode=IntegrityMode.CRC_AND_ECC,
                content_digest=digest,
                key=f"obj.weight.{group.group_id}",
            )

        for constant in self.plan.generated_constants:
            base, channel = self._address(f"generated.{constant.tensor_id}")
            self._generated_object[constant.tensor_id] = builder.memory_object(
                storage_class=StorageClass.HBM,
                size_bytes=constant.size_bytes,
                source=ObjectSource.generated(
                    constant.generator,
                    constant.parameters,
                    constant.size_bytes,
                    constant.digest,
                ),
                permissions=int(Permission.READ | Permission.IMMUTABLE),
                base_address=base,
                bank_or_tile=channel,
                alignment_log2=12,
                integrity_mode=IntegrityMode.CRC32C,
                content_digest=bytes.fromhex(constant.digest),
                key=f"obj.generated.{constant.tensor_id}",
            )

        for slot in self.plan.arena_slots:
            base, channel = self._address(f"arena.{slot.slot_id}")
            self._arena_object[slot.slot_id] = builder.memory_object(
                storage_class=StorageClass.HBM,
                size_bytes=slot.size_bytes,
                source=ObjectSource.zeros(slot.size_bytes),
                permissions=int(Permission.READ | Permission.WRITE),
                base_address=base,
                bank_or_tile=channel,
                alignment_log2=12,
                key=f"obj.arena.{slot.slot_id}",
            )

        # The scratchpad allocation is declared object by object, with its base
        # address and first bank, so the bank plan is readable out of the
        # descriptor table rather than living only in the compiler.
        for region in self.plan.sram_regions:
            self._sram_object[region.region_id] = builder.memory_object(
                storage_class=StorageClass.SRAM,
                size_bytes=region.size_bytes,
                source=ObjectSource.zeros(region.size_bytes),
                permissions=int(Permission.READ | Permission.WRITE),
                base_address=region.offset,
                bank_or_tile=region.bank_first,
                alignment_log2=7,
                key=f"obj.{region.region_id}",
            )

        for kernel in self.graph.kernels:
            if kernel.kind == "TOKEN_APPEND" and kernel.outputs:
                self.token_ring_tensor = kernel.outputs[0]
            if kernel.kind == "EMBEDDING_LOOKUP":
                # The tokens a generation loop reads are the tokens it appends.
                # Placing the embedding's index input and the selection ring in
                # one buffer is what closes that loop in memory: the host writes
                # the prompt once, the device appends each selected token to the
                # same ring, and the next step's lookup reads it without a copy
                # or a second host window.
                for name in kernel.inputs:
                    tensor = self.tensors.get(name)
                    if (
                        tensor is not None
                        and tensor.role == "input"
                        and tensor.dtype in _INDEX_DTYPES
                    ):
                        self.token_input_tensor = name
        # A host request window is addressed from POSITION_START and is a whole
        # request wide, so it must reach one request past the last admissible
        # start.  The ring additionally holds the prompt and every appended
        # token of the session.
        window_rows = (
            int(self.capability.limits["max_context_positions"]) + self.span_max
        )
        ring_element = 4
        if self.token_ring_tensor is not None:
            ring_element = max(
                bytes_for(1, self.tensors[self.token_ring_tensor].dtype), 1
            )
        ring_bytes = window_rows * ring_element

        ring_key = None
        for key in sorted(self.plan.host_objects):
            tensor_id = key.split(".", 2)[2] if key.count(".") >= 2 else key
            if tensor_id in (self.token_ring_tensor, self.token_input_tensor):
                ring_key = ring_key or key
        for key in sorted(self.plan.host_objects):
            spec = self.plan.host_objects[key]
            tensor_id = key.split(".", 2)[2] if key.count(".") >= 2 else key
            if (
                tensor_id in (self.token_ring_tensor, self.token_input_tensor)
                and key != ring_key
            ):
                continue  # shares the ring created for its partner
            size = int(spec["size_bytes"])
            if tensor_id in (self.token_ring_tensor, self.token_input_tensor):
                size = ring_bytes
            else:
                tensor = self.tensors.get(tensor_id)
                if (
                    tensor is not None
                    and tensor.shape
                    and isinstance(tensor.shape[0], Symbolic)
                ):
                    rows = max(int(spec["rows"]), 1)
                    size = (size // rows) * window_rows
            base, _ = self._address(f"host.{key}")
            self._host_object[key] = builder.memory_object(
                storage_class=StorageClass.HOST,
                size_bytes=size,
                source=ObjectSource.zeros(size),
                permissions=int(
                    Permission.READ | Permission.WRITE | Permission.HOST_VISIBLE
                ),
                base_address=base,
                alignment_log2=12,
                key=f"obj.host.{key}",
            )
            if tensor_id in (self.token_ring_tensor, self.token_input_tensor):
                self.token_ring_object = self._host_object[key]
        for key in sorted(self.plan.host_objects):
            tensor_id = key.split(".", 2)[2] if key.count(".") >= 2 else key
            if tensor_id in (self.token_ring_tensor, self.token_input_tensor):
                self._host_object[key] = self.token_ring_object

        if self.token_ring_object == NO_ID:
            self.token_ring_object = builder.memory_object(
                storage_class=StorageClass.HOST,
                size_bytes=ring_bytes,
                source=ObjectSource.zeros(ring_bytes),
                permissions=int(
                    Permission.READ | Permission.WRITE | Permission.HOST_VISIBLE
                ),
                key="obj.token_ring",
            )

        if self.node_count > 1:
            span = int(self.plan.proofs.get("hbm_address_span", 0))
            self.commit_token_object = builder.memory_object(
                storage_class=StorageClass.HBM,
                size_bytes=64,
                source=ObjectSource.zeros(64),
                permissions=int(Permission.READ | Permission.WRITE),
                base_address=_round_up(span, 4096),
                bank_or_tile=0,
                alignment_log2=12,
                key="obj.commit_token",
            )

    def _declare_states(self) -> None:
        builder = self.builder
        for state in self.plan.states:
            size = state.size_bytes
            committed_base, committed_channel = self._address(
                f"state.{state.physical_id}.committed"
            )
            committed = builder.memory_object(
                storage_class=StorageClass.STATE,
                size_bytes=size,
                source=ObjectSource.zeros(size),
                permissions=int(Permission.READ | Permission.STATE_COMMIT),
                base_address=committed_base,
                bank_or_tile=committed_channel,
                alignment_log2=12,
                key=f"obj.{state.physical_id}.committed",
            )
            prepared_base, prepared_channel = self._address(
                f"state.{state.physical_id}.prepared"
            )
            prepared = builder.memory_object(
                storage_class=StorageClass.STATE,
                size_bytes=size,
                source=ObjectSource.zeros(size),
                permissions=int(Permission.READ | Permission.STATE_PREPARE),
                base_address=prepared_base,
                bank_or_tile=prepared_channel,
                alignment_log2=12,
                key=f"obj.{state.physical_id}.prepared",
            )
            self._state_objects[state.physical_id] = (committed, prepared)
            view = builder.tensor_view(
                object_id=prepared,
                dtype=dtype_of(state.dtype),
                dims=[state.capacity_rows * len(state.members), state.row_elements],
                permissions=int(Permission.READ | Permission.WRITE),
                key=f"view.{state.physical_id}",
            )
            self._state_descriptor[state.physical_id] = builder.state(
                state_class=_STATE_CLASS.get(state.state_class, StateClass.SCRATCH),
                committed_object_id=committed,
                prepared_object_id=prepared,
                row_bytes=state.row_bytes,
                capacity_rows=state.capacity_rows * len(state.members),
                element_dtype=dtype_of(state.dtype),
                view_descriptor_id=view,
                counter_class_id=self._counter_class(int(Major.STATE)),
                key=f"state.{state.physical_id}",
            )

    def _state_transaction_sites(self) -> tuple[set[str], set[str]]:
        """Physical states whose prepare/commit the graph places explicitly.

        A graph that declares one transaction per layer, over resources the
        planner merged into one, cannot keep those transactions inside the layer
        loop: the loop would prepare the same physical resource once per
        iteration, which is a double prepare rather than 36 transactions.  Such
        a resource is hoisted -- prepared once before the body and committed
        once after it -- which is the transaction the merged resource actually
        has.  A resource that was not merged keeps the graph's own placement.
        """
        prepared: set[str] = set()
        committed: set[str] = set()
        for kernel in self.graph.kernels:
            if kernel.kind not in ("STATE_PREPARE", "STATE_COMMIT"):
                continue
            for physical_id in self._physical_states(kernel):
                if physical_id in self._hoisted:
                    continue
                if kernel.kind == "STATE_PREPARE":
                    prepared.add(physical_id)
                else:
                    committed.add(physical_id)
        return prepared, committed

    def _physical_states(self, kernel: Kernel) -> list[str]:
        out: list[str] = []
        for name in (*kernel.state_writes, *kernel.state_reads):
            mapping = self.plan.state_of_resource.get(name)
            if mapping and mapping[0] not in out:
                out.append(mapping[0])
        return out

    def _compute_hoisted(self) -> set[str]:
        """Physical states whose transaction must be hoisted out of a loop.

        Also records which graph kernel declared each hoisted transaction, so
        the hoisted instruction still names its source operation and the kernel
        stays traceable to an instruction.
        """
        hoisted: set[str] = set()
        for kernel in self.graph.kernels:
            if kernel.kind not in ("STATE_PREPARE", "STATE_COMMIT"):
                continue
            plan = self.plan._kernel_index.get(kernel.index)
            band = (
                self.plan.band(plan.band_id)
                if plan is not None and plan.band_id is not None
                else None
            )
            iterated = band is not None and band.layer_count > 1
            for physical_id in self._physical_states(kernel):
                self._transaction_source.setdefault(
                    (kernel.kind, physical_id), kernel.index
                )
                if iterated or len(self.plan.state(physical_id).members) > 1:
                    hoisted.add(physical_id)
        return hoisted

    def _declare_entrypoints(self) -> None:
        builder = self.builder
        policy_id = NO_ID
        if any(k.kind == "TOKEN_APPEND" for k in self.graph.kernels):
            body = dict(self.graph.generation_policy)
            eos = tuple(int(t) for t in body.get("eos_token_ids", ()))[:8]
            vocabulary = int(body.get("vocabulary_size", 0)) or self._vocabulary()
            if vocabulary > self.capability.limits["max_vocabulary"]:
                raise LoweringError(
                    f"vocabulary {vocabulary} exceeds the capability bound "
                    f"{self.capability.limits['max_vocabulary']}"
                )
            policy_id = builder.generation_policy(
                eos_token_ids=eos,
                max_new_tokens=int(body.get("max_new_tokens", 512)),
                vocabulary_size=vocabulary,
                token_ring_object_id=self.token_ring_object,
                selection_mode=SelectionMode.GREEDY_ARGMAX_LOWEST_ID,
                counter_class_id=self._counter_class(int(Major.SELECTION)),
                key="policy",
            )
        for entrypoint_id, phase in enumerate((Phase.PREFILL, Phase.DECODE)):
            builder.entrypoint(
                entrypoint_id=entrypoint_id,
                first_instruction=0,
                phase=phase,
                generation_policy_id=policy_id,
            )

    def _vocabulary(self) -> int:
        best = 0
        for kernel in self.graph.kernels:
            if kernel.kind != "ARGMAX" or not kernel.inputs:
                continue
            _, cols, _ = matrix_shape(self.tensors[kernel.inputs[0]], self.span_max)
            best = max(best, cols)
        return best or 1

    # -- descriptor helpers ----------------------------------------------
    def _counter_class(self, family: int) -> int:
        if family in self._counter:
            return self._counter[family]
        group = _COUNTER_GROUP.get(family, CounterGroup.INSTRUCTION)
        cid = self.builder.counter_class(
            int(group),
            [counter_id(group, 1), counter_id(group, 2), counter_id(group, 3)],
            key=f"ctr.{int(group)}",
        )
        self._counter[family] = cid
        return cid

    def _numeric_profile(
        self,
        contract: str,
        in_dtype: DType,
        out_dtype: DType,
        second: DType,
        *,
        scale_bits: int = 0,
        epsilon_bits: int = 0,
    ) -> int:
        key = (contract, int(in_dtype), int(out_dtype), int(second), scale_bits, epsilon_bits)
        if key in self._numeric:
            return self._numeric[key]
        nid = self.builder.numeric(
            contract=contract,
            input_dtype=in_dtype,
            output_dtype=out_dtype,
            second_input_dtype=second,
            accumulator_dtype=DType.FP32,
            reduction_order=_reduction_order(contract),
            scale_bits=scale_bits,
            epsilon_bits=epsilon_bits,
            key=f"num.{len(self._numeric)}",
        )
        self._numeric[key] = nid
        return nid

    def _schedule_for(self, plan: KernelPlan) -> int:
        """The tile mapping, bank/port use, issue window and resource bound.

        These numbers are the cycle model's direct input, so they are derived
        from the real extents and the real bank plan.  A zeroed tile mapping
        would produce a meaningless timing result, which is why the planner
        chooses divisor tiles rather than leaving the field at zero.
        """
        family = plan.engine_family
        mask, ports = self._bank_and_port_mask(family)
        key = (family, plan.tile_rows, plan.tile_cols, plan.tile_depth, mask, ports)
        if key in self._schedule:
            return self._schedule[key]
        name = Major(family).name.lower()
        engine = dict(self.capability.engines.get(name, {}))
        queues = int(engine.get("queues", 1))
        lanes = int(engine.get("lanes", 1))
        sid = self.builder.schedule(
            engine_family=Major(family),
            queue_index=0,
            issue_window=queues,
            tile_rows=plan.tile_rows,
            tile_cols=plan.tile_cols,
            tile_depth=plan.tile_depth,
            bank_mask=mask,
            port_mask=ports,
            noc_route_class=0,
            resource_bound=lanes,
            max_outstanding=int(self.capability.limits["max_outstanding_per_queue"]),
            priority=0,
            key=f"sched.{len(self._schedule)}",
        )
        self._schedule[key] = sid
        return sid

    def _bank_and_port_mask(self, family: int) -> tuple[int, int]:
        wanted = _ENGINE_REGIONS.get(family, ())
        mask = 0
        ports = 0
        for region in self.plan.sram_regions:
            if region.region_id in wanted:
                mask |= region.bank_mask
                ports |= region.port_mask
        return mask, ports

    def _wait_set(self, events: Iterable[int]) -> int:
        unique = tuple(sorted({e for e in events if e != NO_ID}))
        if not unique:
            return NO_ID
        unique = unique[:12]
        if unique in self._waits:
            return self._waits[unique]
        wid = self.builder.wait_set(list(unique), key=f"wait.{len(self._waits)}")
        self._waits[unique] = wid
        return wid

    def _phase_predicate(self, phases: Sequence[str]) -> int:
        if len(phases) != 1:
            return NO_ID
        phase = Phase.PREFILL if phases[0] == "prefill" else Phase.DECODE
        key = ("phase", int(phase))
        if key in self._predicates:
            return self._predicates[key]
        pid = self.builder.predicate(
            kind=PredicateKind.PHASE_IS,
            comparison=Comparison.EQ,
            selector_kind=SelectorKind.RUNTIME_SYMBOL,
            selector_index=int(Symbol.PHASE),
            immediate=int(phase),
            key=f"pred.phase.{phase.name.lower()}",
        )
        self._predicates[key] = pid
        return pid

    def _view(
        self,
        *,
        object_id: int,
        dtype: DType,
        dims: Sequence[int],
        strides: Sequence[int],
        element_offset: int = 0,
        dynamic: Sequence[DynamicTerm] = (),
        writable: bool = False,
        scale_object_id: int = NO_ID,
        scale_block_elements: int = 0,
    ) -> int:
        layout = (
            LayoutClass.BLOCK_SCALED if scale_object_id != NO_ID else LayoutClass.DENSE
        )
        key = (
            object_id,
            int(dtype),
            tuple(int(d) for d in dims),
            tuple(int(s) for s in strides),
            int(element_offset),
            tuple((t.kind, t.index, t.stride) for t in dynamic),
            bool(writable),
            scale_object_id,
            scale_block_elements,
        )
        if key in self._views:
            return self._views[key]
        if len(dynamic) > MAX_DYNAMIC_TERMS:
            raise LoweringError(
                f"a tensor view needs {len(dynamic)} dynamic index terms but the "
                f"frozen ABI 3.0 view admits {MAX_DYNAMIC_TERMS}"
            )
        vid = self.builder.tensor_view(
            object_id=object_id,
            dtype=dtype,
            dims=list(dims),
            strides=list(strides),
            element_offset=element_offset,
            dynamic=list(dynamic),
            layout_class=layout,
            scale_object_id=scale_object_id,
            scale_block_elements=scale_block_elements,
            permissions=int(
                Permission.READ | Permission.WRITE if writable else Permission.READ
            ),
            key=f"view.{len(self._views)}",
        )
        self._views[key] = vid
        return vid

    # -- operand views ---------------------------------------------------
    def _object_for(self, operand: OperandPlan) -> tuple[int, int]:
        """Return ``(object id, base element offset)`` for one operand."""
        if operand.residence == "weight":
            placement = self.plan.placement(operand.tensor_id)
            return self._weight_object[placement.group_id], placement.element_offset
        generated = self._generated_object.get(operand.tensor_id)
        if generated is not None:
            return generated, 0
        if operand.residence == "host":
            return self._host_object[operand.key], 0
        slot = self.plan.arena_of_key.get(operand.key)
        if slot is None:
            raise LoweringError(
                f"activation {operand.tensor_id} has no arena slot; the plan is "
                "incomplete"
            )
        return self._arena_object[slot], 0

    def _scale_binding(self, operand: OperandPlan) -> tuple[int, int]:
        """Amendment A8 block-scale addressing, when the tensor declares one."""
        tensor = self.tensors[operand.tensor_id]
        if not tensor.scale_tensor_id:
            return NO_ID, 0
        placement = self.plan._weight_index.get(tensor.scale_tensor_id)
        if placement is None:
            return NO_ID, 0
        block = tensor.scale_block_elements
        if block <= 0 or operand.cols % block:
            raise LoweringError(
                f"tensor {operand.tensor_id}: block-scale addressing requires "
                f"K % scale_block_elements == 0, got {operand.cols} % {block}"
            )
        return self._weight_object[placement.group_id], block

    def _operand_view(
        self,
        plan: KernelPlan,
        operand: OperandPlan,
        loops: Mapping[str, int],
        *,
        writable: bool,
    ) -> int:
        tensor = self.tensors[operand.tensor_id]
        dtype = dtype_of(operand.dtype)
        self._require_dtype(dtype)

        # TA-ABI3-OPCONV-1 section 8: the ring output carries a dynamic term
        # bound to GENERATION_INDEX so one descriptor serves every decode step.
        if operand.tensor_id == self.token_ring_tensor and operand.direction == "out":
            # The ring is one buffer holding the prompt and everything the
            # loop appends, so the selected token goes at the first free
            # position -- ``POSITION_END`` -- and not at the generation
            # counter, which would overwrite the prompt on the first step.
            return self._view(
                object_id=self.token_ring_object,
                dtype=dtype,
                dims=[1],
                strides=[1],
                dynamic=[DynamicTerm.symbol(Symbol.POSITION_END, 1)],
                writable=True,
            )
        kernel = self.kernels[plan.index]
        writes_state = operand.direction == "out" and bool(kernel.state_writes)
        generated = self._generated_object.get(operand.tensor_id)
        if generated is not None and operand.tensor_id in self._position_inputs:
            return self._position_view(plan, operand, loops, generated)
        if operand.residence == "state" or writes_state:
            # A declared state effect is the authority: a kernel that writes a
            # state resource writes into that resource's prepared image, even
            # when the graph names the result as an ordinary activation.  A read
            # still reads the committed image.
            return self._state_view(
                plan, operand, loops, writable=writable or writes_state
            )
        if plan.engine_family == int(Major.SELECTION):
            return self._selection_view(operand, writable=writable)

        object_id, base = self._object_for(operand)
        scale_object, scale_block = self._scale_binding(operand)
        contraction_operand = plan.contraction and (
            (operand.direction == "in" and operand.slot in (0, 1))
            or (operand.direction == "out" and operand.slot == 0)
        )
        contraction_weight = (
            plan.contraction and operand.direction == "in" and operand.slot == 1
        )
        if contraction_operand:
            # TA-ABI3-OPCONV-1 section 2 states a contraction's operands as
            # matrices: ``[rows, K]``, ``[N, K]`` and ``[rows, N]``.  A
            # checkpoint stored ``[K, N]`` is presented n-major by swapping the
            # view's strides, never by a relayout pass.
            if contraction_weight and operand.transposed:
                strides = [1, operand.cols]
                node_stride = plan.shard_columns
            elif contraction_weight:
                strides = [operand.cols, 1]
                node_stride = plan.shard_columns * operand.cols
            else:
                strides = [operand.cols, 1]
                node_stride = plan.shard_columns
            dims = [max(operand.tile_rows, 1), max(operand.tile_cols, 1)]
            row_stride = dims[0] * strides[0]
        else:
            # Everything else keeps the rank the graph declared.  An engine that
            # reads ``[.., heads, dim]`` or one gain per reduction element
            # rejects a view whose axes have been folded into a matrix, so the
            # folding is confined to the contraction operands that ask for it.
            dims, strides, row_stride = self._declared_view(plan, operand)
            node_stride = plan.shard_columns

        terms: list[DynamicTerm] = []
        for term in operand.terms:
            if term == "layer":
                loop = loops.get("layer")
                placement = self.plan.placement(operand.tensor_id)
                if loop is None or not placement.layer_stride_elements:
                    continue
                terms.append(DynamicTerm.loop(loop, placement.layer_stride_elements))
            elif term == "row":
                loop = loops.get("row")
                if loop is None:
                    continue
                terms.append(DynamicTerm.loop(loop, row_stride))
            elif term == "node":
                if self.node_count <= 1:
                    continue
                terms.append(DynamicTerm.symbol(Symbol.NODE_ID, node_stride))
        # A host input window is staged for *this* request and read from its
        # start: the host writes the prompt for a prefill and the one selected
        # token for a decode step at element zero.  Offsetting the read by
        # POSITION_START would look for the token where nothing was written.
        return self._view(
            object_id=object_id,
            dtype=dtype,
            dims=dims,
            strides=strides,
            element_offset=base,
            dynamic=terms,
            writable=writable,
            scale_object_id=scale_object,
            scale_block_elements=scale_block,
        )

    def _position_view(
        self,
        plan: KernelPlan,
        operand: OperandPlan,
        loops: Mapping[str, int],
        object_id: int,
    ) -> int:
        """The request's positions, as many as the movement addresses.

        An index vector holds exactly one index per row the movement touches,
        and which index depends on what the movement addresses.  A *scatter*
        addresses rows of the KV window, so its indices are absolute positions:
        ``POSITION_START`` plus the token block.  A *gather* addresses rows of
        the span it reads, so its indices are span-relative; selecting the final
        row is ``SPAN_LAST_INDEX``, which is the whole reason that symbol
        exists -- a view offsets by ``selector * stride`` and cannot compute
        ``span - 1`` for itself.
        """
        is_gather = plan.engine_family == int(Major.DMA) and plan.engine_sub == int(
            Dma.GATHER
        )
        source = next(
            (o for o in plan.operands if o.direction == "in" and o is not operand),
            None,
        )
        if is_gather:
            addressed = next(
                (o for o in plan.operands if o.direction == "out"), None
            )
        else:
            addressed = source
        # An index is absolute when what it addresses is indexed by position --
        # a rotary table spans every admissible position -- and span-relative
        # when what it addresses is indexed by the request's own rows.
        span_domain = True
        subject = source if is_gather else addressed
        if subject is not None:
            tensor = self.tensors.get(subject.tensor_id)
            span_domain = bool(
                tensor is not None
                and tensor.shape
                and isinstance(tensor.shape[0], Symbolic)
            )
        if not is_gather:
            span_domain = False  # a scatter addresses the state's own rows
        count = 1
        if addressed is not None:
            dims, _, _ = self._declared_view(plan, addressed)
            count = max(dims[0], 1)
        terms: list[DynamicTerm] = []
        row_loop = loops.get("row") if "row" in operand.terms else None
        if is_gather and span_domain:
            # Selecting rows of the request itself: the final row is
            # ``SPAN_LAST_INDEX``, which is the reason that symbol exists -- a
            # view offsets by ``selector * stride`` and cannot compute
            # ``span - 1`` for itself.
            if count == 1 and row_loop is None:
                terms.append(DynamicTerm.symbol(Symbol.SPAN_LAST_INDEX, 1))
            elif row_loop is not None:
                terms.append(DynamicTerm.loop(row_loop, count))
        else:
            terms.append(DynamicTerm.symbol(Symbol.POSITION_START, 1))
            if row_loop is not None:
                terms.append(DynamicTerm.loop(row_loop, count))
        return self._view(
            object_id=object_id,
            dtype=dtype_of(operand.dtype),
            dims=[count],
            strides=[1],
            dynamic=terms,
        )

    def _declared_view(
        self, plan: KernelPlan, operand: OperandPlan
    ) -> tuple[list[int], list[int], int]:
        """Dims, strides and row-term stride for a view of the declared rank."""
        tensor = self.tensors[operand.tensor_id]
        extents: list[int] = []
        for axis in tensor.shape:
            value, _ = _static_extent(axis, self.span_max)
            extents.append(max(int(value), 1))
        if not extents:
            extents = [1]
        lead_symbolic = bool(tensor.shape) and isinstance(tensor.shape[0], Symbolic)
        if lead_symbolic:
            extents[0] = _round_up(extents[0], plan.block_rows)
        strides = [1] * len(extents)
        running = 1
        for axis in range(len(extents) - 1, -1, -1):
            strides[axis] = running
            running *= extents[axis]
        dims = list(extents)
        if lead_symbolic and "row" in operand.terms:
            dims[0] = plan.block_rows
        row_stride = dims[0] * strides[0]
        dims, strides = self._broadcast_to_principal(plan, operand, dims, strides)
        return dims, strides, row_stride

    def _broadcast_to_principal(
        self,
        plan: KernelPlan,
        operand: OperandPlan,
        dims: list[int],
        strides: list[int],
    ) -> tuple[list[int], list[int]]:
        """Align a lower-rank operand to the principal operand by broadcasting.

        A rotary coefficient table holds one row per *token*, while the tensor
        it rotates holds one row per ``(token, head)``: every head of a token
        shares the same coefficients.  The ABI expresses that with a zero stride
        on the inserted axis, so one row is read many times and nothing is
        copied or duplicated -- which is the whole point of describing operands
        with strides rather than materialising them.

        The rule is positional and model-blind: when an input has exactly one
        axis fewer than the operation's principal operand and agrees with it on
        the leading axis, the missing middle axes are inserted with stride zero.
        """
        if operand.direction != "in" or operand.slot == 0 or len(dims) < 2:
            return dims, strides
        principal = self._principal_extents(plan)
        if principal is None or len(principal) != len(dims) + 1:
            return dims, strides
        if principal[0] != dims[0] or len(principal) < 3:
            return dims, strides
        inserted = list(principal[1:-1])
        return (
            [dims[0], *inserted, dims[-1]],
            [strides[0], *([0] * len(inserted)), strides[-1]],
        )

    def _principal_extents(self, plan: KernelPlan) -> tuple[int, ...] | None:
        """The declared extents of the operation's first input, block-scoped."""
        first = next(
            (o for o in plan.operands if o.direction == "in" and o.slot == 0), None
        )
        if first is None:
            return None
        tensor = self.tensors.get(first.tensor_id)
        if tensor is None or not tensor.shape:
            return None
        extents = []
        for axis in tensor.shape:
            value, _ = _static_extent(axis, self.span_max)
            extents.append(max(int(value), 1))
        if isinstance(tensor.shape[0], Symbolic) and "row" in first.terms:
            extents[0] = plan.block_rows
        return tuple(extents)

    def _selection_view(self, operand: OperandPlan, *, writable: bool) -> int:
        """TA-ABI3-OPCONV-1 section 8: selection operands are one-dimensional."""
        object_id, base = self._object_for(operand)
        elements = 1 if operand.direction == "out" else operand.cols
        return self._view(
            object_id=object_id,
            dtype=dtype_of(operand.dtype),
            dims=[max(elements, 1)],
            strides=[1],
            element_offset=base,
            writable=writable,
        )

    def _state_view(
        self,
        plan: KernelPlan,
        operand: OperandPlan,
        loops: Mapping[str, int],
        *,
        writable: bool,
    ) -> int:
        """A window on the merged state resource, moved by the layer loop.

        A 36-layer model declares 36 KV resources but one loop body can name
        only one state descriptor, so the planner merges a band's resources into
        one physical resource and the layer induction variable selects the
        window.  Attention reads the whole context, so the window is the full
        capacity rather than a token block.
        """
        mapping, column = self._bind_state(plan, operand)
        if mapping is None:
            raise LoweringError(
                f"state operand {operand.tensor_id} of kernel {plan.kernel_id} is "
                "not bound to any declared state resource"
            )
        physical_id, member = mapping[0], int(mapping[1])
        state = self.plan.state(physical_id)
        _committed, prepared = self._state_objects[physical_id]
        window = state.capacity_rows * state.row_elements
        # The window keeps the rank the graph declared -- ``[context, heads,
        # head_dim]`` for a KV history -- so an engine that reads heads finds an
        # axis for them.  Only the leading axis becomes the resource's capacity
        # and the leading stride the fused row width, which is what turns a
        # half of a ``key_then_value`` row into a view rather than a copy.
        tensor = self.tensors.get(operand.tensor_id)
        extents = []
        if tensor is not None:
            for axis in tensor.shape:
                value, _ = _static_extent(axis, self.span_max)
                extents.append(max(int(value), 1))
        if len(extents) < 2:
            width = min(
                self._state_row_width(operand.tensor_id) or state.row_elements,
                state.row_elements - column,
            )
            extents = [state.capacity_rows, max(width, 1)]
        else:
            extents[0] = state.capacity_rows
            width = 1
            for extent in extents[1:]:
                width *= extent
            if width > state.row_elements - column:
                # The tensor's per-position width does not fit the plane this
                # resource reserves for it.  Presenting the declared rank anyway
                # would read past the row; fall back to the plane the resource
                # actually holds and let the engine reject a shape it cannot
                # use, rather than emitting a view that runs off the object.
                extents = [
                    state.capacity_rows, max(state.row_elements - column, 1)
                ]
        strides = [1] * len(extents)
        running = 1
        for axis in range(len(extents) - 1, 0, -1):
            strides[axis] = running
            running *= extents[axis]
        strides[0] = state.row_elements
        terms: list[DynamicTerm] = []
        offset = member * window + column
        loop = loops.get("layer")
        if len(state.members) > 1 and loop is not None:
            terms.append(DynamicTerm.loop(loop, window))
            offset = column
        # Both reads and writes name the *prepared* image.  A transaction reads
        # what it has just appended -- attention over a prefill span attends the
        # very rows the append wrote -- and the committed image is the durability
        # record the commit publishes, not the buffer execution runs against.
        # Reading the committed image mid-transaction would attend to a context
        # that does not yet contain the current tokens.
        return self._view(
            object_id=prepared,
            dtype=dtype_of(state.dtype),
            dims=extents,
            strides=strides,
            element_offset=offset,
            dynamic=terms,
            writable=writable,
        )

    def _state_row_width(self, tensor_id: str) -> int:
        """Elements one position contributes: the product of the non-position axes."""
        tensor = self.tensors.get(tensor_id)
        if tensor is None or len(tensor.shape) < 2:
            return 0
        width = 1
        for axis in tensor.shape[1:]:
            value, _ = _static_extent(axis, self.span_max)
            width *= max(value, 1)
        return width

    def _bind_state(
        self, plan: KernelPlan, operand: OperandPlan
    ) -> tuple[Sequence[Any] | None, int]:
        """Resolve a state operand to ``(resource, column offset in the row)``.

        A resource's row may be a *fused* record -- a key half and a value half
        of one KV row, say -- in which case several operands name windows of one
        resource and their column offsets accumulate in operand order.  When the
        kernel declares as many resources as it has state operands, the binding
        is positional instead.
        """
        direct = self.plan.state_of_tensor.get(operand.tensor_id)
        if direct is not None and len(direct) > 2:
            # The plan recorded this write's plane within the fused row.
            return list(direct[:2]), int(direct[2])
        kernel = self.kernels[plan.index]
        names = list(
            kernel.state_writes if operand.direction == "out" else kernel.state_reads
        ) or list((*kernel.state_writes, *kernel.state_reads))
        peers = [
            o
            for o in plan.operands
            if o.direction == operand.direction
            and (
                o.residence == "state"
                or (o.direction == "out" and kernel.state_writes)
            )
        ]
        position = peers.index(operand) if operand in peers else 0
        if direct is not None:
            mapping = direct
            index = next(
                (
                    i
                    for i, n in enumerate(names)
                    if list(self.plan.state_of_resource.get(n, ())) == list(direct)
                ),
                position,
            )
        elif names:
            index = min(position, len(names) - 1)
            mapping = self.plan.state_of_resource.get(names[index])
        else:
            return None, 0
        column = 0
        for peer in peers[:position]:
            peer_names_index = min(peers.index(peer), len(names) - 1) if names else 0
            peer_mapping = self.plan.state_of_tensor.get(peer.tensor_id)
            if peer_mapping is None and names:
                peer_mapping = self.plan.state_of_resource.get(names[peer_names_index])
            if peer_mapping is not None and list(peer_mapping) == list(mapping):
                column += self._state_row_width(peer.tensor_id)
        return mapping, column

    def _require_dtype(self, dtype: DType) -> None:
        feature = _DTYPE_FEATURE.get(int(dtype))
        if feature is not None:
            self.builder.require(feature)

    # -- kernel emission --------------------------------------------------
    def _emit_kernel(self, plan: KernelPlan) -> None:
        kernel = self.kernels[plan.index]
        if kernel.kind in _TRANSACTION_KINDS:
            self._emit_state_kernel(plan, kernel)
            return

        if self._is_fused_state_append(plan, kernel):
            self._emit_state_append(plan, kernel)
            return

        builder = self.builder
        loops = self._open_loops(plan)
        inputs = [
            self._operand_view(plan, o, loops, writable=False)
            for o in plan.operands
            if o.direction == "in"
        ]
        outputs = [
            self._operand_view(plan, o, loops, writable=True)
            for o in plan.operands
            if o.direction == "out"
        ]
        operator = builder.operator(
            engine_family=Major(plan.engine_family),
            engine_sub=plan.engine_sub,
            inputs=inputs,
            outputs=outputs,
            aux=list(plan.aux),
            numeric_profile_id=self._kernel_numeric(plan),
            schedule_id=self._schedule_for(plan),
            counter_class_id=self._counter_class(plan.engine_family),
            source_kernel_id=plan.index,
            key=f"op.k{plan.index}",
        )
        event = builder.new_event()
        builder.emit(
            Major(plan.engine_family),
            plan.engine_sub,
            descriptor_id=operator,
            wait_set_id=self._wait_set(self._producer_events(kernel)),
            signal_event_id=event,
            predicate_id=self._phase_predicate(plan.phases),
            source_operation_id=plan.index,
        )
        self._close_loops(loops, ["row"])
        event = self._maybe_link(plan, event)
        for name in kernel.outputs:
            self._event_of_tensor[name] = event

    def _is_fused_state_append(self, plan: KernelPlan, kernel: Kernel) -> bool:
        """True when a state write concatenates several sources into one row.

        A KV append names a key and a value but writes one fused row.  The
        engine's convention for the opcode it lowers to takes one source and one
        destination of the same shape, so the concatenation is expressed as one
        write per source into its own column range -- the ``key_then_value`` row
        layout, stated in offsets rather than in a copy.
        """
        if not kernel.state_writes or len(kernel.outputs) != 1:
            return False
        sources = [o for o in plan.operands if o.direction == "in"]
        if len(sources) < 2:
            return False
        row = self._state_row_width(kernel.outputs[0])
        widths = [self._state_row_width(o.tensor_id) for o in sources]
        return bool(row) and all(widths) and sum(widths) == row

    def _emit_state_append(self, plan: KernelPlan, kernel: Kernel) -> None:
        """Emit one write per source into its column range of the state row."""
        builder = self.builder
        loops = self._open_loops(plan)
        numeric = self._kernel_numeric(plan)
        schedule = self._schedule_for(plan)
        counter = self._counter_class(plan.engine_family)
        predicate = self._phase_predicate(plan.phases)
        column = 0
        event = NO_ID
        for slot, operand in enumerate(
            o for o in plan.operands if o.direction == "in"
        ):
            source = self._operand_view(plan, operand, loops, writable=False)
            dims, strides, row_stride = self._declared_view(plan, operand)
            destination = self._state_window(
                plan, kernel, loops, column=column, dims=dims, row_stride=row_stride
            )
            operator = builder.operator(
                engine_family=Major(plan.engine_family),
                engine_sub=plan.engine_sub,
                inputs=[source],
                outputs=[destination],
                aux=list(plan.aux),
                numeric_profile_id=numeric,
                schedule_id=schedule,
                counter_class_id=counter,
                source_kernel_id=plan.index,
                key=f"op.k{plan.index}.part{slot}",
            )
            event = builder.new_event()
            builder.emit(
                Major(plan.engine_family),
                plan.engine_sub,
                descriptor_id=operator,
                wait_set_id=self._wait_set(self._producer_events(kernel)),
                signal_event_id=event,
                predicate_id=predicate,
                source_operation_id=plan.index,
            )
            column += self._state_row_width(operand.tensor_id)
        self._close_loops(loops, ["row"])
        for name in kernel.outputs:
            self._event_of_tensor[name] = event

    def _state_window(
        self,
        plan: KernelPlan,
        kernel: Kernel,
        loops: Mapping[str, int],
        *,
        column: int,
        dims: Sequence[int],
        row_stride: int,
    ) -> int:
        """A write window on the state row, shaped like the source it receives."""
        mapping = self.plan.state_of_tensor.get(kernel.outputs[0])
        if mapping is None:
            for name in kernel.state_writes:
                mapping = self.plan.state_of_resource.get(name)
                if mapping is not None:
                    break
        if mapping is None:
            raise LoweringError(
                f"kernel {plan.kernel_id} declares a state write that binds no "
                "declared resource"
            )
        physical_id, member = mapping[0], int(mapping[1])
        state = self.plan.state(physical_id)
        _, prepared = self._state_objects[physical_id]
        window = state.capacity_rows * state.row_elements
        strides = [1] * len(dims)
        running = 1
        for axis in range(len(dims) - 1, 0, -1):
            strides[axis] = running
            running *= dims[axis]
        strides[0] = state.row_elements
        terms: list[DynamicTerm] = []
        offset = member * window + column
        loop = loops.get("layer")
        if len(state.members) > 1 and loop is not None:
            terms.append(DynamicTerm.loop(loop, window))
            offset = column
        row_loop = loops.get("row")
        if row_loop is not None:
            terms.append(
                DynamicTerm.loop(row_loop, dims[0] * state.row_elements)
            )
        return self._view(
            object_id=prepared,
            dtype=dtype_of(state.dtype),
            dims=list(dims),
            strides=strides,
            element_offset=offset,
            dynamic=terms,
            writable=True,
        )

    def _emit_state_kernel(self, plan: KernelPlan, kernel: Kernel) -> None:
        physical: list[str] = []
        for name in (*kernel.state_writes, *kernel.state_reads):
            mapping = self.plan.state_of_resource.get(name)
            if mapping and mapping[0] not in physical:
                physical.append(mapping[0])
        sub = {
            "STATE_PREPARE": State.PREPARE,
            "STATE_COMMIT": State.COMMIT,
            "STATE_READ": State.READ,
        }[kernel.kind]
        for physical_id in physical:
            if kernel.kind != "STATE_READ" and physical_id in self._hoisted:
                continue  # hoisted out of the loop; see _state_transaction_sites
            self.builder.emit(
                Major.STATE,
                sub,
                descriptor_id=self._state_descriptor[physical_id],
                source_operation_id=plan.index,
            )

    def _open_loops(self, plan: KernelPlan) -> dict[str, int]:
        """Open this kernel's token-block loop and return the live loops.

        Layers are carried by the enclosing band loop and tiles by the schedule
        descriptor, so the only per-kernel loop is the token block -- the one
        extent that is a runtime symbol rather than a static shape.
        """
        loops: dict[str, int] = {}
        if self._layer_loop is not None:
            loops["layer"] = self._layer_loop
        spec = plan.row_loop
        if spec is None:
            return loops
        loop = self.builder.loop_control(
            lower_bound=0,
            upper_bound=spec.trip * spec.divisor,
            step=spec.divisor,
            max_iterations=spec.trip,
            bound_symbol=Symbol.SPAN_TOKENS,
            bound_divisor=spec.divisor,
            counter_class_id=self._counter_class(plan.engine_family),
            key=f"loop.{spec.loop_key}",
        )
        self.builder.open_loop(loop)
        loops["row"] = loop
        return loops

    def _close_loops(self, loops: Mapping[str, int], keys: Sequence[str]) -> None:
        for key in keys:
            if key in loops:
                self.builder.close_loop()

    def _kernel_numeric(self, plan: KernelPlan) -> int:
        kernel = self.kernels[plan.index]
        inputs = [o for o in plan.operands if o.direction == "in"]
        outputs = [o for o in plan.operands if o.direction == "out"]
        in_dtype = dtype_of(inputs[0].dtype) if inputs else DType.BF16
        second = dtype_of(inputs[1].dtype) if len(inputs) > 1 else in_dtype
        out_dtype = dtype_of(outputs[0].dtype) if outputs else in_dtype
        contract = EXECUTION_CONTRACT.get(plan.numeric_contract, plan.numeric_contract)
        if contract != plan.numeric_contract:
            self._substitutions[plan.numeric_contract] = contract
        return self._numeric_profile(
            contract,
            in_dtype,
            out_dtype,
            second,
            scale_bits=_binary32_bits(
                kernel.attributes, ("scale_bits", "scale_bf16_code", "scale")
            ),
            epsilon_bits=_binary32_bits(
                kernel.attributes, ("epsilon_bits", "epsilon")
            ),
        )

    def _producer_events(self, kernel: Kernel) -> list[int]:
        return [
            self._event_of_tensor[name]
            for name in kernel.inputs
            if name in self._event_of_tensor
        ]

    # -- cluster traffic ---------------------------------------------------
    def _maybe_link(self, plan: KernelPlan, event: int) -> int:
        if self.node_count <= 1 or not plan.link_class:
            return event
        return self._emit_link(plan.link_class, f"k{plan.index}", plan, wait=event)

    def _emit_link(
        self,
        link_class: str,
        tag: str,
        plan: KernelPlan | None,
        *,
        wait: int | None,
    ) -> int:
        builder = self.builder
        sub, collective, route_class = _LINK_OP[link_class]
        if plan is not None:
            operand = next((o for o in plan.operands if o.direction == "out"), None)
            if operand is None:
                return wait if wait is not None else NO_ID
            object_id, _ = self._object_for(operand)
            extent = bytes_for(
                max(operand.rows, 1) * max(plan.shard_columns, 1), operand.dtype
            )
        else:
            object_id = self.commit_token_object
            extent = 8
        event = builder.new_event()
        comm = builder.communication(
            collective_op=collective,
            local_object_id=object_id,
            group_id=route_class,
            route_class=route_class,
            byte_extent=extent,
            credit_bound=self.plan.topology.credit_bound,
            retry_bound=self.plan.topology.retry_bound,
            completion_event_id=event,
            counter_class_id=self._counter_class(int(Major.LINK)),
            participant_count=self.node_count,
            chunk_bytes=self.plan.topology.chunk_bytes,
            ordering=Ordering.ACQUIRE_RELEASE,
            integrity_mode=IntegrityMode.CRC32C,
            virtual_channel=route_class % max(self.plan.topology.virtual_channels, 1),
            reduction_numeric_id=(
                self._numeric_profile(
                    "bf16_ordered_sum_fp32_v1", DType.BF16, DType.BF16, DType.BF16
                )
                if collective is CollectiveOp.SUM
                else NO_ID
            ),
            key=f"comm.{link_class}.{tag}",
        )
        builder.require(Feature.INTER_CHIP_ENDPOINT)
        builder.emit(
            Major.LINK,
            sub,
            descriptor_id=comm,
            wait_set_id=self._wait_set([wait]) if wait is not None else NO_ID,
            signal_event_id=event,
            source_operation_id=plan.index if plan is not None else NO_ID,
        )
        self._link_instructions += 1
        return event


def _binary32_bits(attributes: Mapping[str, Any], keys: Sequence[str]) -> int:
    """Read a numeric-descriptor constant as a binary32 bit pattern.

    A graph may state such a constant three ways: already as a bit pattern, as
    a BF16 code (the model's own storage form, which widens exactly by a
    sixteen-bit shift), or as a real number.  The descriptor field is a binary32
    pattern, so all three are converted here rather than at three call sites.
    """
    import struct

    for key in keys:
        if key not in attributes:
            continue
        value = attributes[key]
        if key.endswith("_bits"):
            return int(value) & 0xFFFFFFFF
        if key.endswith("_bf16_code"):
            return (int(value) & 0xFFFF) << 16
        if isinstance(value, bool):
            continue
        if isinstance(value, (int, float)):
            return int.from_bytes(struct.pack("<f", float(value)), "little")
    return 0


def _reduction_order(contract: str) -> ReductionOrder:
    """The association a numeric contract's name declares.

    Amendment A8: RMSNorm's row sum is a balanced tree, so declaring the
    builder's sequential default would contradict the frozen kernel.  Amendment
    A7: the execution contract is blocked, the qualification contract is
    strictly ascending.
    """
    lowered = contract.lower()
    if "rmsnorm" in lowered or "rms_norm" in lowered:
        return ReductionOrder.PAIRWISE_TREE
    if "blocked" in lowered:
        return ReductionOrder.BLOCKED_ASCENDING
    return ReductionOrder.SEQUENTIAL_ASCENDING
