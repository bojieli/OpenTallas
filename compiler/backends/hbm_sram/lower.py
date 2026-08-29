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

from compiler.ir.v3.kernel_ir import Kernel, KernelGraph, Tensor
from compiler.ir.v3.lowering import engine_for
from runtime.abi3.builder import BuildError, DeploymentBuilder, DynamicTerm
from runtime.abi3.capability import Capability
from runtime.abi3.constants import (
    Control,
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
    OperandPlan,
    PhysicalPlan,
    PlanError,
    TileConfig,
    build_plan,
    bytes_for,
    dtype_of,
    matrix_shape,
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


class LoweringError(ValueError):
    """Raised when a graph cannot be expressed in ABI 3.0 on this chip."""


def lower_to_abi3(
    graph: KernelGraph,
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
    """Lower ``graph`` onto ``capability`` and return the ABI 3.0 deployment."""
    plan = plan or build_plan(graph, capability, topology=topology, tile=tile)
    return _Emitter(
        graph, capability, plan, deployment_id, generation, target_id, backend
    ).run()


def lower_with_plan(
    graph: KernelGraph,
    capability: Capability,
    *,
    topology: TopologyClass | int | None = None,
    tile: TileConfig | None = None,
    **kwargs: Any,
) -> tuple[Deployment, PhysicalPlan]:
    """Convenience wrapper returning both artifacts."""
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
        self._arena_object: dict[str, int] = {}
        self._sram_object: dict[str, int] = {}
        self._host_object: dict[str, int] = {}
        self._state_objects: dict[str, tuple[int, int]] = {}
        self._state_descriptor: dict[str, int] = {}
        self._event_of_tensor: dict[str, int] = {}
        self._substitutions: dict[str, str] = {}
        self._layer_loop: int | None = None
        self._link_instructions = 0
        self.token_ring_tensor: str | None = None
        self.token_ring_object: int = NO_ID
        self.commit_token_object: int = NO_ID

    # -- entry point -----------------------------------------------------
    def run(self) -> Deployment:
        builder = self.builder
        self._declare_topology()
        self._declare_objects()
        self._declare_states()

        prepared, committed = self._state_transaction_sites()
        for physical_id in sorted(self._state_descriptor):
            if physical_id not in prepared:
                builder.emit(
                    Major.STATE,
                    State.PREPARE,
                    descriptor_id=self._state_descriptor[physical_id],
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
            self._weight_object[group.group_id] = builder.memory_object(
                storage_class=StorageClass.HBM,
                size_bytes=group.size_bytes,
                source=ObjectSource(
                    kind="segments", size_bytes=group.size_bytes, segments=segments
                ),
                permissions=int(Permission.READ | Permission.IMMUTABLE),
                alignment_log2=12,
                integrity_mode=IntegrityMode.CRC_AND_ECC,
                content_digest=digest,
                key=f"obj.weight.{group.group_id}",
            )

        for slot in self.plan.arena_slots:
            self._arena_object[slot.slot_id] = builder.memory_object(
                storage_class=StorageClass.HBM,
                size_bytes=slot.size_bytes,
                source=ObjectSource.zeros(slot.size_bytes),
                permissions=int(Permission.READ | Permission.WRITE),
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
        ring_bytes = int(self.capability.limits["max_context_positions"]) * 4

        for key in sorted(self.plan.host_objects):
            spec = self.plan.host_objects[key]
            tensor_id = key.split(".", 2)[2] if key.count(".") >= 2 else key
            size = int(spec["size_bytes"])
            if tensor_id == self.token_ring_tensor:
                size = ring_bytes
            self._host_object[key] = builder.memory_object(
                storage_class=StorageClass.HOST,
                size_bytes=size,
                source=ObjectSource.zeros(size),
                permissions=int(
                    Permission.READ | Permission.WRITE | Permission.HOST_VISIBLE
                ),
                key=f"obj.host.{key}",
            )
            if tensor_id == self.token_ring_tensor:
                self.token_ring_object = self._host_object[key]

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
            self.commit_token_object = builder.memory_object(
                storage_class=StorageClass.HBM,
                size_bytes=64,
                source=ObjectSource.zeros(64),
                permissions=int(Permission.READ | Permission.WRITE),
                key="obj.commit_token",
            )

    def _declare_states(self) -> None:
        builder = self.builder
        for state in self.plan.states:
            size = state.size_bytes
            committed = builder.memory_object(
                storage_class=StorageClass.STATE,
                size_bytes=size,
                source=ObjectSource.zeros(size),
                permissions=int(Permission.READ | Permission.STATE_COMMIT),
                alignment_log2=12,
                key=f"obj.{state.physical_id}.committed",
            )
            prepared = builder.memory_object(
                storage_class=StorageClass.STATE,
                size_bytes=size,
                source=ObjectSource.zeros(size),
                permissions=int(Permission.READ | Permission.STATE_PREPARE),
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
        """Physical states whose prepare/commit the graph places explicitly."""
        prepared: set[str] = set()
        committed: set[str] = set()
        for kernel in self.graph.kernels:
            names = (*kernel.state_reads, *kernel.state_writes)
            physical = {
                self.plan.state_of_resource[n][0]
                for n in names
                if n in self.plan.state_of_resource
            }
            if kernel.kind == "STATE_PREPARE":
                prepared |= physical
            elif kernel.kind == "STATE_COMMIT":
                committed |= physical
        return prepared, committed

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
            return self._view(
                object_id=self.token_ring_object,
                dtype=DType.U32,
                dims=[1],
                strides=[1],
                dynamic=[DynamicTerm.symbol(Symbol.GENERATION_INDEX, 1)],
                writable=True,
            )
        if operand.residence == "state":
            return self._state_view(plan, operand, loops, writable=writable)
        if plan.engine_family == int(Major.SELECTION):
            return self._selection_view(operand, writable=writable)

        object_id, base = self._object_for(operand)
        scale_object, scale_block = self._scale_binding(operand)
        contraction_weight = (
            plan.contraction and operand.direction == "in" and operand.slot == 1
        )
        if contraction_weight:
            # Presented n-major as ``[N, K]``; a checkpoint stored ``[K, N]`` is
            # transposed by swapping strides, never by a relayout pass.
            if operand.transposed:
                strides = [1, operand.cols]
                node_stride = plan.shard_columns
            else:
                strides = [operand.cols, 1]
                node_stride = plan.shard_columns * operand.cols
        else:
            strides = [operand.cols, 1]
            node_stride = plan.shard_columns
        dims = [max(operand.tile_rows, 1), max(operand.tile_cols, 1)]

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
                terms.append(DynamicTerm.loop(loop, dims[0] * strides[0]))
            elif term == "node":
                if self.node_count <= 1:
                    continue
                terms.append(DynamicTerm.symbol(Symbol.NODE_ID, node_stride))
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
        mapping = self.plan.state_of_resource.get(operand.tensor_id)
        if mapping is None:
            # The tensor need not be named after the resource, so fall back to
            # position: the n-th state operand of a direction binds the n-th
            # resource the kernel declares in that direction.
            kernel = self.kernels[plan.index]
            peers = [
                o
                for o in plan.operands
                if o.residence == "state" and o.direction == operand.direction
            ]
            names = list(
                kernel.state_reads if operand.direction == "in" else kernel.state_writes
            ) or list((*kernel.state_writes, *kernel.state_reads))
            position = peers.index(operand) if operand in peers else 0
            if position < len(names):
                mapping = self.plan.state_of_resource.get(names[position])
        if mapping is None:
            raise LoweringError(
                f"state operand {operand.tensor_id} of kernel {plan.kernel_id} is "
                "not bound to any declared state resource"
            )
        physical_id, member = mapping[0], int(mapping[1])
        state = self.plan.state(physical_id)
        committed, prepared = self._state_objects[physical_id]
        window = state.capacity_rows * state.row_elements
        terms: list[DynamicTerm] = []
        offset = member * window
        loop = loops.get("layer")
        if len(state.members) > 1 and loop is not None:
            terms.append(DynamicTerm.loop(loop, window))
            offset = 0
        return self._view(
            object_id=prepared if writable else committed,
            dtype=dtype_of(state.dtype),
            dims=[state.capacity_rows, state.row_elements],
            strides=[state.row_elements, 1],
            element_offset=offset,
            dynamic=terms,
            writable=writable,
        )

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
            scale_bits=int(kernel.attributes.get("scale_bits", 0)),
            epsilon_bits=int(kernel.attributes.get("epsilon_bits", 0)),
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
