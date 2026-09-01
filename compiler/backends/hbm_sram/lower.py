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

from dataclasses import replace
from typing import Any, Iterable, Mapping, Sequence

from compiler.backends.numeric_contracts import (
    EXECUTION_CONTRACT,
    reduction_order_for,
)
from compiler.ir.v3.kernel_ir import Kernel, KernelGraph, Symbolic, Tensor
from compiler.ir.v3.lowering import engine_for
from runtime.abi3.builder import BuildError, DeploymentBuilder, DynamicTerm
from runtime.abi3.capability import Capability
from runtime.abi3.constants import (
    Attention,
    Control,
    Reduction,
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
    Tensor as TensorOp,
    TopologyClass,
    Vector,
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
    RING_INDEX_PREFIX,
    _extent_value as _static_extent,
    as_kernel_graph,
    OperandPlan,
    PhysicalPlan,
    PlanError,
    TileConfig,
    build_plan,
    bytes_for,
    dtype_of,
    is_row_gather,
    matrix_shape,
    position_inputs,
    ring_modulus,
    round_up as _round_up,
    _abi_input_slots,
    condition_of,
    join_extent,
    join_extent_under,
    evaluate_comparison,
    phase_substitution,
    substitute_condition,
    RequestExtent,
    request_extent_of,
    kernel_condition,
    operand_present,
    predicate_conditions,
    symbol_condition,
    value_reads,
    writes_state_plane,
)

BACKEND_ID = "hbm-sram-abi3"

#: Neutral kinds whose operator convention states every request-sized operand
#: with a *leading* batch axis.  ``VECTOR.COMPRESS``'s three sub-cases are the
#: set: TA-ABI3-OPCONV-1 section 3 writes the projection ``[B,S,K] -> [B,S,2,N]``,
#: the state update ``[B,S,2,W] -> [B,G,P,D]`` and the pool ``[B,G,P,D] ->
#: [B,G,D]``.  The neutral IR has no batch -- ADR-003 section 15 makes a batch a
#: deployment property -- so each of those operands arrives one rank short.
_BATCH_LEADING = frozenset(
    {
        "COMPRESS_PROJECT",
        "COMPRESS_STATE_UPDATE",
        "COMPRESS_POOL",
        # ``VECTOR.INDEX_SCORE`` is the same shape of statement: in0 query
        # ``[B,S,Hd,D]``, in1 key ``[B,C,D]``, in2 head weights ``[B,S,Hd]``,
        # out0 scores ``[B,S,C]``.  The batch leads here too and for the same
        # reason it does in the state update -- the key operand's batch must
        # match the query's, so a token axis presented as the batch would put
        # one candidate set against every token.
        "INDEX_SCORE",
    }
)

#: Tensor roles the checkpoint supplies.  A block scale on one of these is a
#: placed weight; a block scale on anything else is produced at run time and
#: lives in the activation arena.
_WEIGHT_ROLES = frozenset({"weight", "constant"})

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

#: Input slots whose rank the operand convention states outright, so they are
#: never aligned to the principal operand by broadcasting.  ``ATTENTION.SPARSE``
#: is the case amendment A6 settles: its ``in2`` is a ``[span, slots]`` index
#: array read once per query row, not a per-head tensor, and the positional
#: broadcast rule -- one axis fewer than the principal, agreeing on the leading
#: axis -- describes it exactly and is wrong about it.  A convention that names
#: an operand's rank outranks a rule that infers one.
_DECLARED_RANK_SLOTS: Mapping[tuple[int, int], tuple[int, ...]] = {
    (int(Major.ATTENTION), int(Attention.SPARSE)): (2, 3),
    # ``VECTOR.INDEX_SCORE`` states every operand: in0 query ``[B,S,Hd,D]``,
    # in1 key ``[B,C,D]``, in2 head weights ``[B,S,Hd]``.  The head weights are
    # one axis short of the query and agree on the token axis, which is exactly
    # the shape the broadcast rule fires on -- and it is wrong here, because a
    # head weight is one number *per head*, not one row read once per head.
    (int(Major.VECTOR), int(Vector.INDEX_SCORE)): (1, 2),
}

#: A declared reading of a payload wider than the value it carries:
#: ``(neutral dtype, presented type, presented elements per declared element)``.
#: The DeepSeek hash-route table is ``i64`` holding expert IDs bounded by 255,
#: and the graph states ``table_element_reading = low_u32_of_i64`` -- so the
#: value is the *first* of the two u32 words of each entry, multi-byte integers
#: being little-endian (wire format section 2).  Presenting it as a ``u32`` view
#: of stride two is that reading exactly, zero-copy: an engine performs no
#: conversion and refuses a lookup that asks it to, which is what it should do.
_ELEMENT_READING: Mapping[str, tuple[str, DType, int]] = {
    "low_u32_of_i64": ("i64", DType.U32, 2),
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

#: Neutral state-class name -> the frozen ABI 3.0 :class:`StateClass`.
#:
#: This table and ``compiler.backends.rom.common.program.STATE_CLASS_BY_NAME``
#: must agree: they describe one graph's resources to one wire format, and a
#: ROM-vs-HBM comparison in which the same resource is a ``KV_CACHE`` on one
#: side and a ``SCRATCH`` on the other is not a comparison.  It previously did
#: not: the lookup defaulted to ``SCRATCH`` for any name it did not hold, so
#: DeepSeek's ``kv_window`` and ``compressor_window`` -- fifteen of its nineteen
#: HBM state resources -- were declared ``SCRATCH`` while the ROM backend, whose
#: lookup refuses an unknown name, declared them ``KV_CACHE`` and
#: ``COMPRESSED_KV``.  Legal values, no trap, nothing refused.
_STATE_CLASS: Mapping[str, StateClass] = {
    "kv_cache": StateClass.KV_CACHE,
    "kv_window": StateClass.KV_CACHE,
    "compressed_kv": StateClass.COMPRESSED_KV,
    "compressor_window": StateClass.COMPRESSED_KV,
    "token_ring": StateClass.TOKEN_RING,
    "position_cursor": StateClass.POSITION_CURSOR,
    "route_history": StateClass.ROUTE_HISTORY,
    "scratch": StateClass.SCRATCH,
}

#: Neutral names that have no exact frozen class, and the value they borrow.
#: Recorded in the deployment manifest rather than hidden, because the registry
#: needs its own values through a versioned change a backend may not make.
_STATE_CLASS_ALIASES: Mapping[str, str] = {
    "compressor_window": "COMPRESSED_KV",
    "kv_window": "KV_CACHE",
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
        self._value_reads = value_reads(graph)
        # Amendment A3.  The neutral graph states three conditional shapes and
        # ABI 3.0 states one thing about an instruction -- ``predicate_id``
        # plus the ``PREDICATED``/``PREDICATE_INVERT`` flags against a
        # ``PREDICATE`` descriptor -- so each shape is mapped onto that, in the
        # same words the ROM lane maps them (``compiler/backends/rom/common/
        # program.py``, commit 48cd6ed): one convention, two backends.
        #
        #   ``execution_predicate``        the operator vanishes.
        #   ``conditional_outputs``        expressible only when *every* output
        #                                  is conditional on one value, which
        #                                  is then the operator's own predicate.
        #   ``operand_present_predicate``  a complementary pair of instructions
        #                                  and an unpredicated join.
        self._predicate_values, self._unrepresentable_predicates = (
            predicate_conditions(graph)
        )
        self._predicate_cache: dict[tuple[int, int, int], int] = {}
        self._predicated_operators: dict[str, str] = {}
        self._operand_alternatives: dict[str, str] = {}
        #: Tensor -> phase -> the A18 extent that phase's path writes.  A join
        #: whose operands sum over two runtime symbols has no single extent,
        #: and every view of its result -- the producer's and the consumer's --
        #: states the phase's own.
        self._phase_extent: dict[str, dict[str, RequestExtent]] = {}
        self._emitted_kernels: set[int] = set()
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
        #: Neutral state-class names this graph borrowed a frozen class for.
        self._state_class_aliases: dict[str, str] = {}
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
        #: Participant arrays for the cluster's all-gathers, one per distinct
        #: ``(dtype, element count)`` shape.  A site's array is dead the moment
        #: its unpack has run, and the program is sequential, so sites of the
        #: same shape share one.
        self._exchange_object: dict[tuple[str, int], int] = {}
        #: Traffic classes whose kernels turned out to be replicated, counted so
        #: that "this cluster performs no expert-dispatch transfer" is a fact
        #: the deployment states rather than one a reader has to infer.
        self._replicated_links: dict[str, int] = {}
        #: HBM cursor for objects the plan's address map does not name.
        self._extra_address: int = 0

    # -- entry point -----------------------------------------------------
    def run(self) -> Deployment:
        builder = self.builder
        self._prove_band_predicates_agree()
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
            self._emit_barrier("coordinated_commit", "commit", wait=None)
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
        self._prove_predicates_lowered()
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
                "replicated_link_sites": dict(sorted(self._replicated_links.items())),
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
        # Amendment A3.  What was predicated, on what condition, and what the
        # frozen predicate kinds could not state.  Published beside the program
        # rather than left to be inferred from ``instructions.predicated_off``.
        # Emitted only when non-empty: notes sit inside the deployment digest,
        # so a graph that declares no predicate says nothing here and its
        # manifest is byte-identical to the one it had before predicates
        # existed -- which is what keeps the Qwen digest a fixed point.
        predicates = self._predicate_report()
        if predicates:
            builder.notes["predicates"] = predicates
        # Same rule as the predicate report: emitted only when non-empty, so a
        # graph whose every state class is exact says nothing here and its
        # manifest is unchanged.
        if self._state_class_aliases:
            builder.notes["state_class_aliases"] = dict(
                sorted(self._state_class_aliases.items())
            )
        return builder.finish()

    def _predicate_report(self) -> dict[str, Any]:
        """What this lowering predicated, and what it could not state."""
        report: dict[str, Any] = {}
        if self._predicated_operators:
            report["predicated_operators"] = len(self._predicated_operators)
            report["predicated_conditions"] = {
                condition: sum(
                    1
                    for value in self._predicated_operators.values()
                    if value == condition
                )
                for condition in sorted(set(self._predicated_operators.values()))
            }
        if self._operand_alternatives:
            report["operand_alternative_paths"] = len(self._operand_alternatives)
            report["operand_alternative_conditions"] = {
                condition: sum(
                    1
                    for value in self._operand_alternatives.values()
                    if value == condition
                )
                for condition in sorted(set(self._operand_alternatives.values()))
            }
        if self._phase_extent:
            # Published beside the program for the same reason the predicate
            # report is: a join whose row space the *phase* decides is not
            # visible in any one descriptor, and a reader comparing the two
            # lanes needs to see that both split the same resource the same
            # way.  Each entry is the tensor and, per phase, the affine
            # function that phase's path declares.
            report["phase_split_extents"] = {
                name: {
                    phase: (
                        f"{extent.numerator}*"
                        f"{extent.symbol}/"
                        f"{extent.unit}+{extent.bias}"
                    )
                    for phase, extent in sorted(table.items())
                }
                for name, table in sorted(self._phase_extent.items())
            }
        if self._unrepresentable_predicates:
            report["unrepresentable_predicates"] = dict(
                sorted(self._unrepresentable_predicates.items())
            )
        return report

    def _prove_predicates_lowered(self) -> None:
        """Nothing the graph declared conditional was issued unconditionally.

        This is the check the whole section exists for.  A predicate that is
        declared and not lowered leaves no trace at runtime: the instruction
        issues where the source skips it, and either an engine refuses it or it
        computes against an operand the request does not have and nothing
        complains.  So the lowering proves, against the kernels it actually
        emitted, that every declared condition reached an instruction.
        """
        missing: list[str] = []
        for index in sorted(self._emitted_kernels):
            kernel = self.kernels[index]
            attributes = kernel.attributes
            declares = bool(
                attributes.get("execution_predicate")
                or attributes.get("conditional_outputs")
            )
            if declares and kernel.kernel_id not in self._predicated_operators:
                missing.append(f"{kernel.kernel_id} ({kernel.kind}): execution")
            if (
                attributes.get("operand_present_predicate")
                and kernel.kernel_id not in self._operand_alternatives
            ):
                missing.append(f"{kernel.kernel_id} ({kernel.kind}): operand")
        if missing:
            raise LoweringError(
                "these kernels declare a condition that reached no "
                f"instruction: {missing[:8]}.  A declared predicate that is "
                "not lowered is invisible -- the operator issues where the "
                "source skips it -- so the lowering refuses rather than "
                "emitting it"
            )

    def _prove_band_predicates_agree(self) -> None:
        """Every layer a band body stands for must state the same predicate.

        A band is emitted once and executed once per layer, so the body carries
        the *first* layer's kernel at each position.  The fold identity is
        structural -- kind, contract, operand roles, dtypes, weight extents --
        and says nothing about attributes, so two layers with different
        conditions could share a body and one layer's predicate would silently
        govern the other's execution.  Nothing downstream could see it: the
        program is admitted, every operand is in bounds, and the wrong layer is
        simply skipped or issued.  So it is checked here, where the fold is
        known, rather than assumed from the fact that the released stack
        alternates in step with its compression ratios.
        """
        by_layer: dict[int, list[Kernel]] = {}
        for kernel in self.graph.kernels:
            if kernel.layer is not None:
                by_layer.setdefault(kernel.layer, []).append(kernel)
        for band in self.plan.bands:
            if band.layer_count <= 1:
                continue
            columns: dict[int, list[Kernel]] = {}
            for step in range(band.layer_count):
                layer = band.first_layer + step * band.period
                for position, kernel in enumerate(by_layer.get(layer, [])):
                    columns.setdefault(position, []).append(kernel)
            for position, column in sorted(columns.items()):
                conditions = {
                    kernel_condition(self._predicate_values, k) for k in column
                }
                if len(conditions) > 1:
                    raise LoweringError(
                        f"band {band.band_id} position {position} folds layers "
                        f"{[k.kernel_id for k in column][:4]} whose execution "
                        f"predicates differ ({sorted(map(str, conditions))}); a "
                        "loop body states one predicate and would govern every "
                        "layer it stands for with it"
                    )
                operands = {
                    (operand_present(self._predicate_values, k) or (None, None))
                    for k in column
                }
                if len(operands) > 1:
                    raise LoweringError(
                        f"band {band.band_id} position {position} folds layers "
                        f"{[k.kernel_id for k in column][:4]} whose "
                        "conditionally present operands differ; one loop body "
                        "cannot state two alternative paths"
                    )

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

        self._extra_address = _round_up(
            int(self.plan.proofs.get("hbm_address_span", 0)), 4096
        )
        if self.node_count > 1:
            self.commit_token_object = builder.memory_object(
                storage_class=StorageClass.HBM,
                size_bytes=64,
                source=ObjectSource.zeros(64),
                permissions=int(Permission.READ | Permission.WRITE),
                base_address=self._extra_hbm(64),
                bank_or_tile=0,
                alignment_log2=12,
                key="obj.commit_token",
            )

    def _extra_hbm(self, size_bytes: int) -> int:
        """Reserve ``size_bytes`` of HBM past the plan's addressed span."""
        base = self._extra_address
        self._extra_address = _round_up(base + max(int(size_bytes), 1), 4096)
        return base

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
            state_class = _STATE_CLASS.get(state.state_class)
            if state_class is None:
                raise LoweringError(
                    f"state class {state.state_class!r} is not in the frozen "
                    "ABI 3.0 registry and has no documented alias; extend the "
                    "registry through a versioned change, never privately"
                )
            if state.state_class in _STATE_CLASS_ALIASES:
                self._state_class_aliases[state.state_class] = _STATE_CLASS_ALIASES[
                    state.state_class
                ]
            self._state_descriptor[state.physical_id] = builder.state(
                state_class=state_class,
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
                max_new_tokens=self._declared_new_token_budget(body),
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

    def _declared_new_token_budget(self, body: dict) -> int:
        """The decode budget the neutral IR declares, by the name it declares it.

        This read used to name ``max_new_tokens``, which the IR does not emit --
        it emits ``maximum_new_tokens`` -- so the lookup always missed and the
        deployment silently carried the 512 default. Nothing failed: the host
        driver's own budget is usually smaller, so the cap only bites on a long
        generation, and then it looks like the model stopped early. The ROM
        backend reads the right key, so the two lanes were also carrying
        different generation policies for the same IR, which is the divergence
        this program exists to prevent.

        There is no default now. A graph that appends tokens without declaring a
        budget is a graph whose decode length nobody chose, and guessing one here
        is how the first defect survived.
        """

        declared = body.get("maximum_new_tokens")
        if declared is None:
            raise LoweringError(
                "the generation policy declares no 'maximum_new_tokens'; a decode "
                "budget must be stated by the IR rather than defaulted by a backend"
            )
        budget = int(declared)
        limit = int(self.capability.limits["max_context_positions"])
        if budget > limit:
            raise LoweringError(
                f"generation policy admits {budget} new tokens but the capability "
                f"holds {limit} context positions"
            )
        return budget

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
        reduction_order: ReductionOrder,
        scale_bits: int = 0,
        epsilon_bits: int = 0,
    ) -> int:
        key = (
            contract,
            int(in_dtype),
            int(out_dtype),
            int(second),
            int(reduction_order),
            scale_bits,
            epsilon_bits,
        )
        if key in self._numeric:
            return self._numeric[key]
        nid = self.builder.numeric(
            contract=contract,
            input_dtype=in_dtype,
            output_dtype=out_dtype,
            second_input_dtype=second,
            accumulator_dtype=DType.FP32,
            reduction_order=reduction_order,
            scale_bits=scale_bits,
            epsilon_bits=epsilon_bits,
            key=f"num.{len(self._numeric)}",
        )
        self._numeric[key] = nid
        return nid

    def _schedule_for(self, plan: KernelPlan, family: int | None = None) -> int:
        """The tile mapping, bank/port use, issue window and resource bound.

        These numbers are the cycle model's direct input, so they are derived
        from the real extents and the real bank plan.  A zeroed tile mapping
        would produce a meaningless timing result, which is why the planner
        chooses divisor tiles rather than leaving the field at zero.
        """
        # A kernel whose neutral kind lowers to more than one engine -- a
        # sharded contraction, whose all-gather is a pack, a collective and an
        # unpack -- names the family its instructions actually carry, because a
        # SCHEDULE descriptor is typed by engine family and the verifier checks
        # the two agree.
        family = plan.engine_family if family is None else int(family)
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

    def _predicate_descriptor(self, condition: str) -> int:
        symbol, comparison, immediate = symbol_condition(condition)
        key = (int(symbol), int(comparison), int(immediate))
        cached = self._predicate_cache.get(key)
        if cached is not None:
            return cached
        pid = self.builder.predicate(
            kind=PredicateKind.COMPARE_SYMBOL,
            comparison=comparison,
            selector_kind=SelectorKind.RUNTIME_SYMBOL,
            selector_index=int(symbol),
            immediate=int(immediate),
            key=(
                f"pred.{symbol.name.lower()}."
                f"{comparison.name.lower()}.{immediate}"
            ),
        )
        self._predicate_cache[key] = pid
        return pid

    def _kernel_predicate(self, plan: KernelPlan) -> int:
        """This kernel's one predicate: its phase, or its declared condition.

        An instruction carries one ``predicate_id``, so a kernel that names a
        phase *and* a condition is a conjunction the ABI cannot state.  Nothing
        in either released graph does; a graph that did would be refused here
        rather than have one of the two silently dropped.
        """
        kernel = self.kernels[plan.index]
        condition = kernel_condition(self._predicate_values, kernel)
        phase = self._phase_predicate(plan.phases)
        if condition is None:
            return phase
        if phase != NO_ID:
            raise LoweringError(
                f"kernel {plan.kernel_id}: declares both the phase "
                f"{plan.phases[0]!r} and the condition {condition!r}; an "
                "ABI 3.0 instruction carries one predicate_id and there is no "
                "conjunction"
            )
        self._predicated_operators[kernel.kernel_id] = condition
        return self._predicate_descriptor(condition)

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
        scale_block_rows: int = 0,
        extent_axis: int = 0,
        extent_numerator: int = 1,
        extent_unit: int = 1,
        extent_bias: int = 0,
    ) -> int:
        layout = (
            LayoutClass.BLOCK_SCALED if scale_object_id != NO_ID else LayoutClass.DENSE
        )
        # Amendment A18 encodes a numerator and a unit of one as zero, so a
        # view that needs nothing the amendment added is byte-identical to the
        # same view written before it -- and the verifier refuses a literal
        # one, because that is a value the wire format does not assign.
        numerator = int(extent_numerator) if extent_numerator > 1 else 0
        unit = int(extent_unit) if extent_unit > 1 else 0
        bias = int(extent_bias)
        # The axis is not part of the affine function: a view may state the
        # identity function on an axis that is not the leading one, which is
        # exactly the compressor's ``[1, span, ...]`` batch row.  Every view
        # that needs nothing A18 added passes zero here and still encodes
        # byte-identically to the same view written before the amendment.
        axis = int(extent_axis)
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
            scale_block_rows,
            axis,
            numerator,
            unit,
            bias,
        )
        if key in self._views:
            return self._views[key]
        if len(dynamic) > MAX_DYNAMIC_TERMS:
            raise LoweringError(
                f"a tensor view needs {len(dynamic)} dynamic index terms but the "
                f"frozen ABI 3.0 view admits {MAX_DYNAMIC_TERMS}"
            )
        if writable and shares_an_axis(dims, strides):
            raise LoweringError(
                f"a writable view of dims {tuple(int(d) for d in dims)} declares "
                f"strides {tuple(int(s) for s in strides)}; an axis of stride "
                "zero may be read as a broadcast but never written, because "
                "every element of it is the same location"
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
            scale_block_rows=scale_block_rows,
            extent_axis=axis,
            extent_numerator=numerator,
            extent_unit=unit,
            extent_bias=bias,
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

    def _scale_binding(self, operand: OperandPlan) -> tuple[int, int, int]:
        """Block-scale addressing, when the tensor declares one.

        Amendment A15 states the block as two extents:
        ``scale_block_elements`` along the last axis and ``scale_block_rows``
        along the leading one.  The neutral IR names only the first, because
        the scale tensor's own declared shape carries the second -- a
        ``[1024, 4096]`` FP8 weight with a 128-element block whose scale is
        ``[8, 32]`` is scaled in 128 x 128 tiles, and ``1024 / 8`` says so.  A
        one-dimensional MXFP4 scale derives a row block of one and encodes the
        A8 case unchanged.
        """
        tensor = self.tensors[operand.tensor_id]
        scale_id = tensor.scale_tensor_id
        if not scale_id or scale_id not in self.tensors:
            return NO_ID, 0, 0
        block = int(tensor.scale_block_elements or 0)
        if block <= 0:
            return NO_ID, 0, 0
        placement = self.plan._weight_index.get(scale_id)
        if placement is None and self.tensors[scale_id].role in _WEIGHT_ROLES:
            return NO_ID, 0, 0
        if operand.cols % block:
            raise LoweringError(
                f"tensor {operand.tensor_id}: block-scale addressing requires "
                f"K % scale_block_elements == 0, got {operand.cols} % {block}"
            )
        row_block = self._scale_block_rows(tensor, operand)
        if placement is not None:
            self._check_scale_address(operand, placement, block, row_block)
            return self._weight_object[placement.group_id], block, row_block
        # A quantised *activation* carries its scale in the arena beside its
        # codes, and the view is the only place that can say so: the engine
        # derives the code offset from this view's own element offset, so a
        # scale nothing binds is a scale nothing applies.  Dropping it is
        # silent -- FP8 codes read as if every block scaled by one -- which is
        # why an activation scale the plan does place is bound here rather
        # than skipped for not being a weight.
        return self._arena_scale_object(operand, scale_id), block, row_block

    def _arena_scale_object(self, operand: OperandPlan, scale_id: str) -> int:
        """The arena object holding a quantised activation's block scales."""
        key = self.plan.activation_keys.get(scale_id)
        slot = self.plan.arena_of_key.get(key) if key is not None else None
        if slot is None:
            raise LoweringError(
                f"tensor {operand.tensor_id} declares block scale {scale_id}, "
                "which is neither a placed weight nor an arena activation, so "
                "no object holds it and the operand would be read as if every "
                "block scaled by one"
            )
        return self._arena_object[slot]

    def _check_scale_address(
        self,
        operand: OperandPlan,
        placement: Any,
        block: int,
        row_block: int,
    ) -> None:
        """Refuse a scale object the weight's own offset does not address.

        A block scale carries no descriptor.  Amendments A8 and A15 place the
        code for element ``(row, col)`` at ``(row // row_block) * (cols //
        block) + col // block`` *of the weight view's own row-major space*, so
        the engine reads the scale object at an offset it derives from the
        weight view and nowhere else.  The scale object's address space is
        therefore the weight object's divided by the block, and a placement
        that does not satisfy that is not a slower lowering -- it is a
        different tensor's codes read as this one's.

        The failure is silent by construction: a wrong offset that still lands
        inside the object decodes to finite E8M0 factors and produces a number.
        Only a placement far enough out to leave the object traps.  So the
        relation is checked here, where both placements are known, rather than
        left to whichever layer walks off the end first.
        """
        weight = self.plan._weight_index.get(operand.tensor_id)
        if weight is None:
            return
        cols = max(int(operand.cols), 1)
        rows_per_tile = max(int(row_block), 1)

        def codes(elements: int) -> int:
            return (int(elements) // cols // rows_per_tile) * (cols // int(block))

        expected_offset = codes(weight.element_offset)
        expected_stride = codes(weight.layer_stride_elements)
        if (
            placement.element_offset == expected_offset
            and placement.layer_stride_elements == expected_stride
        ):
            return
        raise LoweringError(
            f"tensor {operand.tensor_id}: its scale {placement.tensor_id} sits at "
            f"code {placement.element_offset} with layer stride "
            f"{placement.layer_stride_elements} in object "
            f"{placement.group_id}, but the weight sits at element "
            f"{weight.element_offset} with layer stride "
            f"{weight.layer_stride_elements} in object {weight.group_id}, which "
            f"a {rows_per_tile} x {block} block addresses as code "
            f"{expected_offset} with stride {expected_stride}; a block scale is "
            "addressed by the weight's own offset, so the two objects must be "
            "one address space apart by the block"
        )

    def _scale_block_rows(self, tensor: Tensor, operand: OperandPlan) -> int:
        """How many leading rows one of this tensor's scale codes covers."""
        scale = self.tensors.get(tensor.scale_tensor_id or "")
        if scale is None:
            return 1
        block = int(tensor.scale_block_elements or 0)
        def extent(value: Any) -> int:
            # A symbolic extent is the same symbol on both sides -- an
            # activation scaled per token declares ``[span, K/block]`` against
            # ``[span, K]`` -- so its maximum stands for it and the ratio comes
            # out one, which is the A8 case.
            if isinstance(value, Symbolic):
                return max(int(value.maximum or 1), 1)
            return max(int(value), 1)

        data_dims = [extent(d) for d in tensor.shape]
        scale_dims = [extent(d) for d in scale.shape]
        if not data_dims or not scale_dims:
            return 1
        width = data_dims[-1]
        if width % block or scale_dims[-1] != width // block:
            raise LoweringError(
                f"tensor {tensor.tensor_id}: a {block}-element scale block over "
                f"{width} columns needs a scale whose last axis is "
                f"{width // block}; {scale.tensor_id} declares {scale_dims}"
            )
        rows = 1
        for extent in data_dims[:-1]:
            rows *= extent
        scale_rows = 1
        for extent in scale_dims[:-1]:
            scale_rows *= extent
        if scale_rows <= 0 or rows % scale_rows:
            raise LoweringError(
                f"tensor {tensor.tensor_id} has {rows} rows and its scale "
                f"{scale.tensor_id} has {scale_rows}; a block scale covers a "
                "whole number of rows per code"
            )
        return max(rows // scale_rows, 1)

    def _operand_view(
        self,
        plan: KernelPlan,
        operand: OperandPlan,
        loops: Mapping[str, int],
        *,
        writable: bool,
        narrow: tuple[int, int] | None = None,
    ) -> int:
        tensor = self.tensors[operand.tensor_id]
        dtype = dtype_of(operand.dtype)
        reading = self._element_reading(plan, operand)
        if reading is not None:
            dtype = reading[0]
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
        writes_state = operand.direction == "out" and writes_state_plane(
            kernel, self.tensors, operand.tensor_id, self._value_reads
        )
        if plan.kind == "SELECT" and operand.direction == "in" and (
            operand.residence != "arena" or writes_state
        ):
            # A select is an element offset into the source, and only the arena
            # path below applies that offset.  A state or host view builds its
            # own extents, so it would present the *whole* source and silently
            # move the wrong plane.  Refuse instead: an offset that is dropped
            # is worse than a lowering that does not exist.
            raise LoweringError(
                f"kernel {plan.kernel_id}: SELECT reads {operand.tensor_id!r}, "
                f"which is {operand.residence}-resident; only an arena source "
                "carries the selected plane's element offset"
            )
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
        scale_object, scale_block, scale_rows = self._scale_binding(operand)
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
            row_stride = self._row_step(plan, operand) * strides[0]
            if contraction_weight and operand.bank:
                # A routed bank is ``[E, N, K]``.  The expert is the outermost
                # axis, so its stride is the whole matrix each expert holds --
                # whichever way that matrix itself is stored -- and the engine
                # selects along it at runtime rather than the program looping
                # over it.
                strides = [operand.rows // operand.bank * operand.cols, *strides]
                dims = [operand.bank, *dims]
        else:
            # Everything else keeps the rank the graph declared.  An engine that
            # reads ``[.., heads, dim]`` or one gain per reduction element
            # rejects a view whose axes have been folded into a matrix, so the
            # folding is confined to the contraction operands that ask for it.
            dims, strides, row_stride = self._declared_view(plan, operand)
            node_stride = plan.shard_columns

        if narrow is not None:
            # One axis shortened after the declared shape is built.  A17's
            # reduced join needs exactly this: the segments the join keeps are
            # a prefix of the destination's columns, so the reduced path is the
            # same buffer read with a shorter extent on the join axis and the
            # buffer's own row stride.
            axis, extent = narrow
            if not 0 <= axis < len(dims):
                raise LoweringError(
                    f"kernel {plan.kernel_id}: narrowing axis {axis} of a "
                    f"rank-{len(dims)} view"
                )
            dims = list(dims)
            dims[axis] = max(min(int(extent), int(dims[axis])), 1)
        numerator = int(operand.extent_numerator)
        dims, strides, numerator, row_stride = self._row_broadcast(
            plan, operand, dims, strides, numerator, row_stride
        )
        # The context axis, once a leading batch axis has displaced it.  Its
        # term steps by one whole block of that axis, which is what makes A18's
        # walk test recognise it -- the same derivation the row term satisfies,
        # in the candidate axis's own units.
        context_axis = -1
        context_stride = 0
        if operand.context_axis >= 0 and plan.context_loop is not None:
            context_axis = operand.context_axis + self._batch_axis(plan, operand)
            if not 0 <= context_axis < len(strides):
                raise LoweringError(
                    f"kernel {plan.kernel_id}: operand {operand.tensor_id} "
                    f"names context axis {operand.context_axis}, which is "
                    f"outside the rank-{len(strides)} view it is presented as"
                )
            context_stride = int(strides[context_axis]) * self._context_step(
                plan, operand
            )
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
            elif term == "context":
                loop = loops.get("context")
                if loop is None or context_axis < 0:
                    continue
                terms.append(DynamicTerm.loop(loop, context_stride))
            elif term == "node":
                if self.node_count <= 1:
                    continue
                terms.append(DynamicTerm.symbol(Symbol.NODE_ID, node_stride))
        # A host input window is staged for *this* request and read from its
        # start: the host writes the prompt for a prefill and the one selected
        # token for a decode step at element zero.  Offsetting the read by
        # POSITION_START would look for the token where nothing was written.
        walks_row = any(t == "row" for t in operand.terms) and any(
            term.kind == int(SelectorKind.LOOP_INDUCTION) for term in terms
        )
        walks_context = context_axis >= 0 and "context" in operand.terms
        offset = base + self._select_offset(plan, operand)
        if reading is not None:
            # Same bytes, narrower element: every stride and the base are
            # counted in the presented type, so both scale by the number of
            # presented elements one declared element holds.
            factor = reading[1]
            strides = [int(x) * factor for x in strides]
            offset *= factor
            terms = [
                DynamicTerm(term.kind, term.index, int(term.stride) * factor)
                for term in terms
            ]
        return self._view(
            object_id=object_id,
            dtype=dtype,
            dims=dims,
            strides=strides,
            element_offset=offset,
            dynamic=terms,
            writable=writable,
            scale_object_id=scale_object,
            scale_block_elements=scale_block,
            scale_block_rows=scale_rows,
            # A18's third admission rule: the function is declared only where
            # a term actually walks the axis it describes.  A row term that
            # was dropped because its loop is not open takes the declaration
            # with it, rather than leaving an extent nothing can resolve.
            # A18 names one axis.  When the operand has a context axis that is
            # the one: its kernel runs one token per dispatch, so the token
            # axis is a static one with nothing for the amendment to say, and
            # the candidate axis is the only extent the request moves.
            extent_axis=(
                context_axis
                if walks_context
                else (self._batch_axis(plan, operand) if walks_row else 0)
            ),
            extent_numerator=(
                operand.context_numerator
                if walks_context
                else (numerator if walks_row else 1)
            ),
            extent_unit=(
                operand.context_unit
                if walks_context
                else (operand.extent_unit if walks_row else 1)
            ),
            extent_bias=(
                operand.context_bias
                if walks_context
                else (operand.extent_bias if walks_row else 0)
            ),
        )

    def _element_reading(
        self, plan: KernelPlan, operand: OperandPlan
    ) -> tuple[DType, int] | None:
        """The presented element type of a payload the graph reads narrowly.

        Stated by the graph, never inferred: an ``i64`` tensor whose values fit
        in 32 bits is not automatically a ``u32`` view, because which half of
        each entry carries the value is a fact about the checkpoint and not
        about the range of its contents.
        """
        kernel = self.kernels[plan.index]
        name = str(kernel.attributes.get("table_element_reading", "") or "")
        entry = _ELEMENT_READING.get(name)
        if entry is None or operand.direction != "in" or operand.slot != 1:
            return None
        declared, presented, factor = entry
        if operand.dtype != declared:
            raise LoweringError(
                f"kernel {plan.kernel_id} declares element reading {name!r} for "
                f"a {declared} payload, but {operand.tensor_id!r} is "
                f"{operand.dtype}"
            )
        return presented, factor

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
        if is_gather or source is None:
            # A gather addresses the rows it writes.  So does an operation
            # whose *only* input is the position vector: ``ROUTE.WINDOW_INDEX``
            # takes one absolute position per query row and nothing else, so
            # the rows it addresses are the rows of its own output.  Reading
            # the count from a second input that does not exist left the view
            # holding a single position for a whole block of queries, which the
            # engine refuses -- it has one position per row or it has nothing
            # to build a window from.
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
        # How many positions one row of the movement advances.  It is one
        # wherever a movement touches consecutive rows; a *pooled* row stands
        # for several positions and the graph declares how many.  The
        # compressor's rotary gather is the case: one coefficient row per group
        # of four tokens, at the position of the group's first token.  An
        # element stride of four reaches exactly those rows of the coefficient
        # table, so the strided range needs no second table to materialise.
        position_stride = max(
            int(self.kernels[plan.index].attributes.get("position_stride", 1) or 1), 1
        )
        # Amendment A18: this vector holds one index per row the *addressed*
        # operand has, so it is clamped in that operand's own axis units -- a
        # compressor's row is a group of four tokens, and 104 tokens are 26 of
        # them, not 26 rows of a 128-row block.  Declared only where the loop
        # term walks the axis in that unit, which is the amendment's third
        # admission rule and is what ``count == step + bias`` tests: an
        # addressed operand whose extent is not the block is one no loop
        # resolves, and A18 refuses a declaration nothing resolves.
        numerator, unit, bias = 1, 1, 0
        step = count
        if addressed is not None:
            numerator = int(addressed.extent_numerator)
            unit = int(addressed.extent_unit)
            bias = int(addressed.extent_bias)
            step = self._row_step(plan, addressed)
        terms: list[DynamicTerm] = []
        row_loop = loops.get("row") if "row" in operand.terms else None
        if row_loop is None and count > 1 and operand.rows <= 1:
            # A range declared as its single base element -- the ``[1]`` form --
            # has no token axis of its own, so the planner gave it no row term.
            # It still addresses a whole block: the positions this movement
            # touches are ``POSITION_START + block*count + i``.  Taking the loop
            # from the movement rather than from the operand's declared shape is
            # what makes the two forms of the same range lower to the same view,
            # and it is also what makes amendment A13 clamp this view to the
            # rows the request has -- without it the index vector would be a
            # whole block wide against a partial final block of rows.
            row_loop = loops.get("row")
        declares = row_loop is not None and count == step + bias
        loop_stride = (step if declares else count) * position_stride
        if is_gather and span_domain:
            # Selecting rows of the request itself: the final row is
            # ``SPAN_LAST_INDEX``, which is the reason that symbol exists -- a
            # view offsets by ``selector * stride`` and cannot compute
            # ``span - 1`` for itself.
            if count == 1 and row_loop is None:
                terms.append(DynamicTerm.symbol(Symbol.SPAN_LAST_INDEX, 1))
            elif row_loop is not None:
                terms.append(DynamicTerm.loop(row_loop, loop_stride))
        else:
            terms.append(DynamicTerm.symbol(Symbol.POSITION_START, 1))
            if row_loop is not None:
                terms.append(DynamicTerm.loop(row_loop, loop_stride))
        # The object under this view is the ``arange_u32_v1`` table the planner
        # materialised, not the host window the graph declared, so its storage
        # type is the generator's.  An exporter that declared the range ``i32``
        # was describing a window that no longer exists, and an index view is
        # ``U32``: the engines that read one say so, and a signed index is not
        # an index.
        #
        # A write into a *circular* cache reads the ring table instead.  The
        # graph says so in ``cache_row``: a sliding window of ``W`` rows holds
        # absolute position ``p`` at row ``p % W``, and a view can offset an
        # index vector by a runtime symbol but cannot reduce one, so the
        # reduction is in the table rather than in the descriptor.
        modulus = ring_modulus(self.kernels[plan.index])
        if modulus:
            ring = self._generated_object.get(f"{RING_INDEX_PREFIX}{modulus}")
            if ring is None:
                raise LoweringError(
                    f"kernel {plan.kernel_id}: addresses a {modulus}-row ring "
                    "and the plan materialised no ring-index table for it"
                )
            object_id = ring
        walks = any(
            term.kind == int(SelectorKind.LOOP_INDUCTION) for term in terms
        )
        return self._view(
            object_id=object_id,
            dtype=DType.U32,
            dims=[count],
            strides=[position_stride],
            dynamic=terms,
            extent_numerator=numerator if (declares and walks) else 1,
            extent_unit=unit if (declares and walks) else 1,
            extent_bias=bias if (declares and walks) else 0,
        )

    @staticmethod
    def _context_step(plan: KernelPlan, operand: OperandPlan) -> int:
        """Elements of the context axis one iteration of its loop covers.

        The same function ``_row_step`` computes for the token axis, read
        against the context loop's own divisor: ``numerator * divisor / unit``.
        With one block over the whole declared capacity that is the capacity,
        which is what makes the single iteration cover all of it.
        """
        context = plan.context_loop
        if context is None:
            return 1
        scaled = int(operand.context_numerator) * int(context.divisor)
        unit = max(int(operand.context_unit), 1)
        return max(scaled // unit, 1)

    @staticmethod
    def _row_step(plan: KernelPlan, operand: OperandPlan) -> int:
        """Elements of the row axis one iteration of the block loop covers.

        Amendment A18: ``numerator * bound_divisor / unit``.  The *bias* is not
        part of it -- a 128-row committed window is present in every iteration
        and is not something an iteration advances by -- which is why the term
        stride and the declared extent are different numbers on a view that
        carries one, and why taking the stride from ``dim0`` was right only
        while every extent was the symbol's own value.
        """
        block = max(int(plan.block_rows), 1)
        scaled = int(operand.extent_numerator) * block
        unit = max(int(operand.extent_unit), 1)
        return max(scaled // unit, 1)

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
        row_stride = dims[0] * strides[0]
        if lead_symbolic and "row" in operand.terms:
            step = self._row_step(plan, operand)
            dims[0] = step + int(operand.extent_bias)
            row_stride = step * strides[0]
        dims, strides = self._drop_unit_row_axis(plan, operand, dims, strides)
        dims, strides = self._index_matrix(plan, operand, dims, strides)
        dims, strides = self._insert_broadcast_axis(plan, operand, dims, strides)
        dims, strides = self._drop_selected_axis(plan, operand, dims, strides)
        dims, strides = self._broadcast_to_principal(plan, operand, dims, strides)
        dims, strides = self._insert_batch_axis(plan, operand, dims, strides)
        dims, strides = self._lead_reduced_axis(plan, operand, dims, strides)
        dims = self._narrow_partial_quantiser(plan, operand, dims)
        return dims, strides, row_stride

    def _narrow_partial_quantiser(
        self, plan: KernelPlan, operand: OperandPlan, dims: list[int]
    ) -> list[int]:
        """Read only the part of a row a partial block quantiser converts.

        A quantiser whose code output is narrower than its source quantises a
        *prefix* of each row and leaves the rest alone: DeepSeek converts the
        448 non-rotary channels of a 512-wide KV vector to E4M3FN and keeps the
        64 rotary ones in BF16, because the rotary channels carry position and
        cannot afford the format.  ``VECTOR.CONVERT`` reads the source and the
        codes as one shape, so the narrowing has to live in the *view*: the
        same row stride, fewer elements of it.  Leaving it out presents a
        512-wide source against a 448-wide code output, which the engine
        refuses -- correctly, because the alternative is quantising the rotary
        channels by accident.

        The code output's own width is the authority; a declared
        ``quantized_width`` that disagrees with it is a contradiction in the
        graph, not a preference between two numbers.
        """
        if plan.kind != "QUANTIZE" or operand.direction != "in" or operand.slot != 0:
            return dims
        kernel = self.kernels[plan.index]
        if not kernel.outputs or not dims:
            return dims
        codes = self.tensors[kernel.outputs[0]]
        if not codes.shape:
            return dims
        width, _ = _static_extent(codes.shape[-1], self.span_max)
        width = int(width)
        if width == int(dims[-1]):
            return dims
        if not 0 < width < int(dims[-1]):
            raise LoweringError(
                f"kernel {plan.kernel_id}: the quantiser writes {width} codes "
                f"per {dims[-1]}-element row, which is not a prefix of it"
            )
        declared = kernel.attributes.get("quantized_width")
        if declared is not None and int(declared) != width:
            raise LoweringError(
                f"kernel {plan.kernel_id}: declares quantized_width "
                f"{int(declared)} and writes a {width}-wide code output"
            )
        return [*dims[:-1], width]

    def _lead_reduced_axis(
        self,
        plan: KernelPlan,
        operand: OperandPlan,
        dims: list[int],
        strides: list[int],
    ) -> tuple[list[int], list[int]]:
        """Present a reduction's contributions with the reduced axis leading.

        The ``REDUCTION`` family reduces ``input_view_0``'s leading axis.  A
        neutral reduction that names another axis -- the mHC branch reduction
        names axis 1, the four hyper-connection streams, because the graph is
        token-major -- describes the same elements in a different order, and a
        strided view is exactly how a machine whose operands are descriptions
        states that.  Moving the axis to the front costs nothing and copies
        nothing: the same object, the same offsets, the strides permuted.

        The planner already gave such a kernel a one-token block, because a
        stream-major leading axis is not the token axis and amendment A13's
        clamp therefore does not reach this view.  With one token per
        descriptor there is no partial final iteration to clamp.
        """
        if plan.engine_family != int(Major.REDUCTION):
            return dims, strides
        if operand.direction != "in" or operand.slot != 0:
            return dims, strides
        axis = int(
            self.kernels[plan.index].attributes.get("reduction_axis", 0) or 0
        )
        if axis == 0:
            return dims, strides
        if axis >= len(dims):
            raise LoweringError(
                f"kernel {plan.kernel_id}: reduction_axis {axis} is outside the "
                f"rank-{len(dims)} contributions operand"
            )
        return (
            [dims[axis], *dims[:axis], *dims[axis + 1 :]],
            [strides[axis], *strides[:axis], *strides[axis + 1 :]],
        )

    def _insert_broadcast_axis(
        self,
        plan: KernelPlan,
        operand: OperandPlan,
        dims: list[int],
        strides: list[int],
    ) -> tuple[list[int], list[int]]:
        """Read a ``BROADCAST`` source through one axis of stride zero.

        The neutral kernel says the result is its source with ``extent``
        inserted at ``axis``, every element of the new axis being the same
        element.  A stride of zero on that axis *is* that statement: the
        verifier bounds a view by ``(dim - 1) * stride``, so the axis reaches no
        further than the source does and costs no bytes, and the engine reads
        one row ``extent`` times instead of four copies of it.

        Only the source is widened.  The destination keeps its own declared
        strides, because a zero stride on a writable view would make every
        element of the axis the same *location* -- an aliasing write whose
        result is whichever copy landed last.  ``_view`` refuses that outright.
        """
        if plan.kind != "BROADCAST" or operand.direction != "in":
            return dims, strides
        attributes = self.kernels[plan.index].attributes
        axis = int(attributes["axis"])
        extent = int(attributes["extent"])
        if not 0 <= axis <= len(dims):
            raise LoweringError(
                f"kernel {plan.kernel_id}: BROADCAST axis {axis} is outside the "
                f"rank-{len(dims)} source"
            )
        return (
            [*dims[:axis], extent, *dims[axis:]],
            [*strides[:axis], 0, *strides[axis:]],
        )

    def _drop_selected_axis(
        self,
        plan: KernelPlan,
        operand: OperandPlan,
        dims: list[int],
        strides: list[int],
    ) -> tuple[list[int], list[int]]:
        """Read one plane of a ``SELECT`` source by dropping the named axis.

        The mirror of :meth:`_insert_broadcast_axis`.  A broadcast reads one
        source through an axis of stride zero; a select reads one plane of a
        source by dropping an axis and offsetting into it.  The offset itself is
        :meth:`_select_offset`, applied where the view's element offset is
        assembled, because ``_declared_view`` states shape and not placement.

        Only the source is narrowed.  The destination keeps the rank the graph
        declared, which is the source's rank minus one.
        """
        if plan.kind != "SELECT" or operand.direction != "in":
            return dims, strides
        axis = int(self.kernels[plan.index].attributes["axis"])
        if not 0 <= axis < len(dims):
            raise LoweringError(
                f"kernel {plan.kernel_id}: SELECT axis {axis} is outside the "
                f"rank-{len(dims)} source"
            )
        return (
            [*dims[:axis], *dims[axis + 1 :]],
            [*strides[:axis], *strides[axis + 1 :]],
        )

    def _select_offset(self, plan: KernelPlan, operand: OperandPlan) -> int:
        """Elements from the source's start to the selected plane."""
        if plan.kind != "SELECT" or operand.direction != "in":
            return 0
        attributes = self.kernels[plan.index].attributes
        axis = int(attributes["axis"])
        index = int(attributes["index"])
        tensor = self.tensors[operand.tensor_id]
        stride = 1
        for extent in tensor.shape[axis + 1 :]:
            value, _ = _static_extent(extent, self.span_max)
            stride *= max(int(value), 1)
        return index * stride

    def _insert_batch_axis(
        self,
        plan: KernelPlan,
        operand: OperandPlan,
        dims: list[int],
        strides: list[int],
    ) -> tuple[list[int], list[int]]:
        """Present a token-major operand under an operand row that states a batch.

        ``VECTOR.MHC``'s ``HYPER_CONNECT_POST`` sub-case states every operand as
        ``[batch, span, ...]``: it is qualified against
        ``runtime.reference.vector.hc_post_bf16``, whose signature carries a
        batch axis.  The neutral IR has no batch concept -- ADR-003 section 15
        gives it model semantics, and a batch is a deployment property -- so a
        token-major ``[tokens, ...]`` operand is one rank short of its row.

        The inserted axis goes *after* the token axis, not before it, and the
        difference is not cosmetic.  The operation is pointwise in the token
        index, so ``[tokens, 1, ...]`` and ``[1, tokens, ...]`` name the same
        elements in the same order and the engine's ``batch * span`` site count
        is ``tokens`` either way.  But amendment A13 clamps a view's *leading*
        extent on a block loop's partial final iteration, so a leading axis of
        one is never clamped and the view would present a whole 512-row block
        for a 104-token span.  Keeping the token axis leading keeps A13 exact.
        """
        if not dims:
            return dims, strides
        if plan.kind == "HYPER_CONNECT_POST":
            return [dims[0], 1, *dims[1:]], [strides[0], strides[0], *strides[1:]]
        if plan.kind in _BATCH_LEADING:
            # ``VECTOR.COMPRESS`` cannot take the axis second.  Its state
            # update reads ``[B, S, 2, W]`` and forms ``groups = span //
            # ratio`` across the *span* axis, so a token axis presented as the
            # batch would leave every group a single token and the operator
            # would refuse a 104-token span as containing no complete group of
            # four.  Its pool likewise names the pooling candidates on axis 2.
            # The batch therefore leads, as the convention writes it, and the
            # amendment that A13 could not state does the rest: A18 names the
            # axis the request determines, which is axis 1 here.
            #
            # Only an operand the request sizes takes the axis.  A projection
            # matrix and the position-embedding table are already the rank the
            # convention gives them, and prepending a batch to those would
            # present a rank the operator refuses.
            if self._request_sized(operand):
                # The batch's own stride is the whole operand -- one batch of
                # everything below it.  With an extent of one nothing addresses
                # through it, so the number is unreachable either way; writing
                # the consistent one is what lets the two lanes' descriptors be
                # compared element for element rather than argued about.
                return [1, *dims], [int(dims[0]) * int(strides[0]), *strides]
        return dims, strides

    def _request_sized(self, operand: OperandPlan) -> bool:
        """Does the graph size this operand's leading axis by the request?"""
        tensor = self.tensors.get(operand.tensor_id)
        if tensor is None or not tensor.shape:
            return False
        return isinstance(tensor.shape[0], Symbolic)

    def _batch_axis(self, plan: KernelPlan, operand: OperandPlan) -> int:
        """The axis A18 declares, once a leading batch axis has displaced it."""
        if plan.kind in _BATCH_LEADING and self._request_sized(operand):
            return 1
        return 0

    def _row_broadcast(
        self,
        plan: KernelPlan,
        operand: OperandPlan,
        dims: list[int],
        strides: list[int],
        numerator: int,
        row_stride: int,
    ) -> tuple[list[int], list[int], int, int]:
        """One factor per row of the value it scales, read once per column.

        ``VECTOR.SCALE``'s elementwise sub-case requires the factor's extents to
        *equal* the value's trailing extents -- there is no column-vector rule
        -- so a factor the graph states as one number per row is presented at
        the value's own shape with a stride of zero on every axis but the
        first.  Nothing is copied: a zero stride names one location, which is
        what makes this a broadcast rather than a materialised tensor.

        The routed expert product is the case.  The graph gives the weights as
        ``[span, k]`` and the values as ``[k * span, W]``, which are the same
        rows in the same order counted differently, so the folded trailing
        extent multiplies the operand's A18 numerator: one iteration of the
        token-block loop covers ``k`` times as many rows of this axis as it
        covers tokens.
        """
        if (
            int(plan.engine_family),
            int(plan.engine_sub),
        ) != (int(Major.VECTOR), int(Vector.SCALE)):
            return dims, strides, numerator, row_stride
        if operand.direction != "in" or operand.slot != 1:
            return dims, strides, numerator, row_stride
        principal = self._principal_extents(plan)
        if principal is None or len(principal) < 2 or tuple(dims) == principal[1:]:
            return dims, strides, numerator, row_stride
        folded = 1
        for extent in dims:
            folded *= max(int(extent), 1)
        if folded != principal[0]:
            return dims, strides, numerator, row_stride
        scale = folded // max(int(dims[0]), 1)
        out_dims = list(principal)
        out_strides = [1] + [0] * (len(principal) - 1)
        return out_dims, out_strides, numerator * scale, folded

    def _index_matrix(
        self,
        plan: KernelPlan,
        operand: OperandPlan,
        dims: list[int],
        strides: list[int],
    ) -> tuple[list[int], list[int]]:
        """Present a per-row selector as the ``[rows, k]`` matrix its row states.

        ``TENSOR.ROUTED_MATMUL`` reads ``k`` expert IDs per activation row and
        states the operand as a rank-2 matrix, so that one row selecting one
        expert and one row selecting several are the same descriptor with a
        different ``k``.  The released graph declares one ID per dispatched row
        and therefore a rank-1 tensor, which is the same numbers at the rank
        the convention does not use -- so the trailing axis of one is added
        here rather than the engine being asked to guess which rank it was
        handed.
        """
        if (
            int(plan.engine_family),
            int(plan.engine_sub),
        ) != (int(Major.TENSOR), int(TensorOp.ROUTED_MATMUL)):
            return dims, strides
        if operand.direction != "in" or operand.slot != 2 or len(dims) != 1:
            return dims, strides
        return [dims[0], 1], [max(strides[0], 1), 1]

    def _drop_unit_row_axis(
        self,
        plan: KernelPlan,
        operand: OperandPlan,
        dims: list[int],
        strides: list[int],
    ) -> tuple[list[int], list[int]]:
        """Present one token's row as the rows a within-row gather indexes.

        The per-token loop has already made the leading extent one, so the
        operand is ``[1, W]`` and the engine would index a single row.  What
        the operation indexes is ``W``, so the degenerate axis is dropped and
        the trailing one leads.  Nothing about the addressing changes: the
        loop term still advances by one whole row, which is what the extent it
        replaces was worth.
        """
        if not is_row_gather(self.kernels[plan.index], self.tensors):
            return dims, strides
        if len(dims) < 2 or dims[0] != 1:
            return dims, strides
        return dims[1:], strides[1:]

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
        if plan.engine_family == int(Major.REDUCTION):
            # A reduction states its own operand extents: ``EXPERT_SUM``'s
            # weight is one per reduced index and a base carries the output
            # shape, so neither is a lower-rank operand awaiting broadcast.
            return dims, strides
        if operand.slot in _DECLARED_RANK_SLOTS.get(
            (int(plan.engine_family), int(plan.engine_sub)), ()
        ):
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
            # Amendment A18: the principal's leading extent is what *its* own
            # affine function makes of one iteration, which is the block only
            # when that function is the symbol's own value.  Reading the raw
            # block here made a ``[6 * span, W]`` principal look 512 rows tall
            # and every alignment against it silently decline to fire.
            extents[0] = self._row_step(plan, first) + int(first.extent_bias)
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
        # The window keeps the rank and operator-row transformations the graph
        # declared -- ``[context, heads, head_dim]`` for a KV history, and a
        # leading unit batch for INDEX_SCORE's ``[B, C, D]`` key.  Its storage
        # strides differ from an arena view only at the row boundary: the
        # leading stride is the fused state's row width, which turns one plane
        # of a ``key_then_value`` row into a view rather than a copy.
        tensor = self.tensors.get(operand.tensor_id)
        extents: list[int] = []
        if tensor is not None:
            for axis in tensor.shape:
                value, _ = _static_extent(axis, self.span_max)
                extents.append(max(int(value), 1))
        lead_symbolic = bool(
            tensor is not None
            and tensor.shape
            and isinstance(tensor.shape[0], Symbolic)
        )
        if lead_symbolic:
            extents[0] = _round_up(extents[0], plan.block_rows)
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

        dims = list(extents)
        row_stride = dims[0] * strides[0]
        # Cache operators address state in absolute context coordinates, never
        # in the token block's request-local coordinates.  DMA.SCATTER's index
        # operand names absolute cache rows (or rows from a generated modulo
        # table for a ring), while ATTENTION receives CONTEXT_LENGTH separately
        # and uses it to bound the valid prefix of a capacity-sized KV view.
        # Applying the ordinary row block to either side both offsets the view
        # by the request loop and clamps it to the span: a decode at position 93
        # then either asks a one-row destination for row 93 or presents only one
        # KV row to attention over a 94-token context.  The ROM lowering already
        # keeps these cache views whole; do the same here.
        whole_cache_access = (
            plan.engine_family == int(Major.DMA)
            and plan.engine_sub == int(Dma.SCATTER)
            and operand.direction == "out"
        ) or (
            plan.engine_family == int(Major.ATTENTION)
            and operand.direction == "in"
        )
        if (
            lead_symbolic
            and "row" in operand.terms
            and not whole_cache_access
        ):
            step = self._row_step(plan, operand)
            dims[0] = step + int(operand.extent_bias)
            row_stride = step * strides[0]
        if operand.context_axis >= 0 and "context" in operand.terms:
            step = self._context_step(plan, operand)
            dims[operand.context_axis] = step + int(operand.context_bias)

        # Match the ordinary declared-view path after replacing only its
        # physical row stride.  In particular INDEX_SCORE inserts the leading
        # batch axis here; bypassing this sequence made a newly correct state
        # binding fail as rank two where the frozen operand row requires rank
        # three.
        dims, strides = self._drop_unit_row_axis(plan, operand, dims, strides)
        dims, strides = self._index_matrix(plan, operand, dims, strides)
        dims, strides = self._insert_broadcast_axis(plan, operand, dims, strides)
        dims, strides = self._drop_selected_axis(plan, operand, dims, strides)
        dims, strides = self._broadcast_to_principal(plan, operand, dims, strides)
        dims, strides = self._insert_batch_axis(plan, operand, dims, strides)
        dims, strides = self._lead_reduced_axis(plan, operand, dims, strides)
        dims = self._narrow_partial_quantiser(plan, operand, dims)

        terms: list[DynamicTerm] = []
        # The member is the *base* of this operand's own band inside the
        # resource, and the layer loop steps one window per iteration from
        # there.  It was previously dropped, which was harmless only while every
        # merged resource held exactly one band and the base was always zero;
        # a pooled resource (``_pool_states``) puts a later band at a non-zero
        # base and dropping it would address the first band's members instead --
        # legal offsets, no trap, another layer's KV history.
        offset = member * window + column
        loop = loops.get("layer")
        if len(state.members) > 1 and loop is not None:
            terms.append(DynamicTerm.loop(loop, window))
        row_loop = (
            loops.get("row")
            if "row" in operand.terms and not whole_cache_access
            else None
        )
        walks_row = row_loop is not None
        if row_loop is not None:
            terms.append(DynamicTerm.loop(row_loop, row_stride))
        context_axis = -1
        context_loop = (
            loops.get("context") if "context" in operand.terms else None
        )
        walks_context = context_loop is not None and operand.context_axis >= 0
        if walks_context:
            context_axis = operand.context_axis + self._batch_axis(plan, operand)
            if not 0 <= context_axis < len(strides):
                raise LoweringError(
                    f"kernel {plan.kernel_id}: state operand {operand.tensor_id} "
                    f"names context axis {operand.context_axis}, which is "
                    f"outside its presented rank {len(strides)}"
                )
            terms.append(
                DynamicTerm.loop(
                    context_loop,
                    int(strides[context_axis]) * self._context_step(plan, operand),
                )
            )
        # Both reads and writes name the *prepared* image.  A transaction reads
        # what it has just appended -- attention over a prefill span attends the
        # very rows the append wrote -- and the committed image is the durability
        # record the commit publishes, not the buffer execution runs against.
        # Reading the committed image mid-transaction would attend to a context
        # that does not yet contain the current tokens.
        return self._view(
            object_id=prepared,
            dtype=dtype_of(state.dtype),
            dims=dims,
            strides=strides,
            element_offset=offset,
            dynamic=terms,
            writable=writable,
            extent_axis=(
                context_axis
                if walks_context
                else (self._batch_axis(plan, operand) if walks_row else 0)
            ),
            extent_numerator=(
                int(operand.context_numerator)
                if walks_context
                else (int(operand.extent_numerator) if walks_row else 1)
            ),
            extent_unit=(
                int(operand.context_unit)
                if walks_context
                else (int(operand.extent_unit) if walks_row else 1)
            ),
            extent_bias=(
                int(operand.context_bias)
                if walks_context
                else (int(operand.extent_bias) if walks_row else 0)
            ),
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
        self._emitted_kernels.add(plan.index)
        if kernel.kind in _TRANSACTION_KINDS:
            self._emit_state_kernel(plan, kernel)
            return

        if self._is_fused_state_append(plan, kernel):
            self._emit_state_append(plan, kernel)
            return

        builder = self.builder
        loops = self._open_loops(plan)
        # Positional, not packed: an operand carries the ABI slot the operand
        # convention gives it, and a slot the convention requires to stay
        # ``NO_ID`` -- ``VECTOR.COMPRESS`` sub-case 2's projection matrix -- is
        # a hole its neighbours are placed either side of.
        in_operands = [o for o in plan.operands if o.direction == "in"]
        inputs = [NO_ID] * (max((o.slot for o in in_operands), default=-1) + 1)
        for operand in in_operands:
            inputs[operand.slot] = self._operand_view(
                plan, operand, loops, writable=False
            )
        outputs = [
            self._operand_view(plan, o, loops, writable=True)
            for o in plan.operands
            if o.direction == "out"
        ]
        if (int(plan.engine_family), int(plan.engine_sub)) == (
            int(Major.REDUCTION),
            int(Reduction.GROUPED_CONCAT),
        ):
            self._check_join_extent(plan, kernel)
        present = operand_present(self._predicate_values, kernel)
        if present is not None:
            event = self._emit_alternative_paths(
                plan, kernel, loops, inputs, outputs, absent=present[0],
                condition=present[1],
            )
            event = self._maybe_link(plan, event, loops)
            self._close_loops(loops, ["context", "row"])
            for name in kernel.outputs:
                self._event_of_tensor[name] = event
            return
        consumer_paths = self._phase_consumer_paths(plan, kernel)
        if consumer_paths is not None:
            event = self._emit_phase_consumer(
                plan, kernel, loops, inputs, outputs, consumer_paths
            )
            event = self._maybe_link(plan, event, loops)
            self._close_loops(loops, ["context", "row"])
            for name in kernel.outputs:
                self._event_of_tensor[name] = event
            return
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
            predicate_id=self._kernel_predicate(plan),
            source_operation_id=plan.index,
        )
        # The exchange is *inside* the token-block loop.  A COMMUNICATION
        # descriptor carries no dynamic index terms, so a collective addresses
        # one fixed buffer of one fixed extent; the only way to exchange a span
        # that a runtime symbol sizes is to exchange it one block at a time, and
        # the block is what the loop already iterates.
        event = self._maybe_link(plan, event, loops)
        self._close_loops(loops, ["context", "row"])
        for name in kernel.outputs:
            self._event_of_tensor[name] = event

    def _emit_alternative_paths(
        self,
        plan: KernelPlan,
        kernel: Kernel,
        loops: Mapping[str, int],
        inputs: Sequence[int],
        outputs: Sequence[int],
        *,
        absent: int,
        condition: str,
    ) -> int:
        """One operator, two complementary paths, one event.

        ``operand_present_predicate`` says the operator issues either way and
        one *operand* is there only under a condition.  ABI 3.0 predicates an
        instruction, not an operand, so the pair is the lowering: the full
        operand row under the condition, the reduced row under its inverse.
        The two paths cannot share an event -- ABI 3.0 events are
        single-assignment -- and a consumer cannot wait on the path that did
        not run, because a wait on an unsignalled event is a device fault.  So
        the pair is followed by an unpredicated ``CONTROL.NOP`` that publishes
        the event the *result* is ordered by: it is the join of the two paths,
        it retires whichever ran, and it keeps the consumer's dependency real
        rather than dropped.

        Two things change on the reduced path and both matter.  Its wait set
        drops the vanished operand's producer -- that producer is predicated
        off by the same condition and will never signal.  And, for a join, the
        output's extent drops that operand's contribution: A17 makes the
        output the sum of the inputs, so a path keeping the full extent would
        declare rows no operand supplies.

        Which slots may actually be emptied is not a guess, and it is no longer
        this function's to decide.  A slot the *graph* declares empty is an
        ``absent_operands`` statement checked at neutral admission against the
        frozen ``OPTIONAL_INPUT_SLOTS``, and ``_abi_input_slots`` has already
        placed it -- there is nothing conditional about it, which is the whole
        point of the static form.  What is left here is the conditional form,
        and it empties a slot only where the row reads it through
        ``optional_input`` and can join what remains:
        ``REDUCTION.GROUPED_CONCAT``.

        ``ROUTE.INDEX_TOPK``'s ``in0`` is the case that changed and the reduced
        path keeps binding it anyway.  Amendment A20 makes the slot optional, so
        A19's "every other frozen operand row is mandatory" no longer covers it
        and emptying it would now execute; it is still not what this path should
        do.  A19 defines the zero-candidate case *with* a score view -- the
        operator reads the view's shape, reads no value from it, and emits the
        joined window -- and the reduced path is exactly that case, so binding
        the view is the operand row the amendment describes rather than a second
        spelling of it. Emptying it would additionally move the span off the
        score view and onto ``out0``, which is a different derivation for a path
        whose only difference is meant to be a dropped ordering dependency.
        """
        builder = self.builder
        predicate = self._predicate_descriptor(condition)
        self._operand_alternatives[kernel.kernel_id] = condition
        slots = _abi_input_slots(kernel, plan.slot_order)
        abi_slot = next(
            (index for index, ir in enumerate(slots) if ir == absent), None
        )
        optional = (int(plan.engine_family), int(plan.engine_sub)) == (
            int(Major.REDUCTION),
            int(Reduction.GROUPED_CONCAT),
        )
        reduced_inputs = list(inputs)
        reduced_outputs = list(outputs)
        if optional:
            if abi_slot is None or abi_slot >= len(reduced_inputs):
                raise LoweringError(
                    f"kernel {plan.kernel_id}: names input {absent} as "
                    "conditionally present, and no ABI slot carries it"
                )
            reduced_inputs[abi_slot] = NO_ID
            reduced_outputs[0] = self._reduced_join_output(plan, kernel, loops, absent)

        def operator(row_in: Sequence[int], row_out: Sequence[int], key: str) -> int:
            return builder.operator(
                engine_family=Major(plan.engine_family),
                engine_sub=plan.engine_sub,
                inputs=list(row_in),
                outputs=list(row_out),
                aux=list(plan.aux),
                numeric_profile_id=self._kernel_numeric(plan),
                schedule_id=self._schedule_for(plan),
                counter_class_id=self._counter_class(plan.engine_family),
                source_kernel_id=plan.index,
                key=key,
            )

        family, sub = Major(plan.engine_family), plan.engine_sub
        present_paths = self._phase_present_paths(
            plan, kernel, loops, condition=condition, declared_output=(
                outputs[0] if outputs else NO_ID
            )
        )
        if present_paths is None:
            builder.emit(
                family,
                sub,
                descriptor_id=operator(inputs, outputs, f"op.k{plan.index}"),
                wait_set_id=self._wait_set(self._producer_events(kernel)),
                signal_event_id=builder.new_event(),
                predicate_id=predicate,
                source_operation_id=plan.index,
            )
        else:
            for phase, path_predicate, path_output in present_paths:
                builder.emit(
                    family,
                    sub,
                    descriptor_id=operator(
                        inputs,
                        [path_output, *outputs[1:]],
                        f"op.k{plan.index}.{phase}",
                    ),
                    wait_set_id=self._wait_set(self._producer_events(kernel)),
                    signal_event_id=builder.new_event(),
                    predicate_id=path_predicate,
                    source_operation_id=plan.index,
                )
        kept = [
            self._event_of_tensor[name]
            for index, name in enumerate(kernel.inputs)
            if index != absent and name in self._event_of_tensor
        ]
        builder.emit(
            family,
            sub,
            descriptor_id=operator(
                reduced_inputs, reduced_outputs, f"op.k{plan.index}.absent"
            ),
            wait_set_id=self._wait_set(kept),
            signal_event_id=builder.new_event(),
            predicate_id=predicate,
            invert_predicate=True,
            source_operation_id=plan.index,
        )
        join = builder.new_event()
        builder.emit(
            Major.CONTROL,
            Control.NOP,
            signal_event_id=join,
            source_operation_id=plan.index,
        )
        return join

    def _declared_join_axis(self, name: str) -> RequestExtent | None:
        """The A18 function the graph declares for one tensor's leading axis."""
        return request_extent_of(self.tensors[name], self.span_max)

    def _check_join_extent(self, plan: KernelPlan, kernel: Kernel) -> None:
        """Refuse a join whose declared output extent is not its operands' sum.

        A17 makes the output of a join the sum of its inputs and the engine
        checks exactly that, one dispatch after admission.  Until now the
        *reduced* path of a conditionally present operand was the only extent
        this backend derived; the full path took whatever symbol the exporter
        had put on the output tensor.  For DeepSeek's compressed attention join
        that symbol was ``attention_rows_ratioN`` -- the span's group count
        where the join carries the context's -- and it agreed with the operands
        in prefill, where the span *is* the context.  Every gate this program
        had run was a prefill, so nothing refused it and the first decode step
        failed at the engine instead, differently on each lane.
        """
        if int(kernel.attributes.get("axis", 0)) != 0:
            return
        if not kernel.outputs or not kernel.inputs:
            return
        declared = self._declared_join_axis(kernel.outputs[0])
        phases = kernel.attributes.get("phase_symbol_binding")
        names = list(kernel.inputs)
        if phases:
            for phase, pinned in sorted(dict(phases).items()):
                constants, aliases = phase_substitution(
                    pinned, f"kernel {plan.kernel_id} phase {phase!r}"
                )
                join_extent_under(
                    self.tensors, names, 0, self.span_max, constants, aliases
                )
            return
        derived, _static = join_extent_under(
            self.tensors, names, 0, self.span_max, {}, {}
        )
        if declared is None:
            if derived is not None:
                raise LoweringError(
                    f"kernel {plan.kernel_id}: the join's operands sum to a "
                    "request-determined extent and its output declares a "
                    "static one"
                )
            return
        if derived is None or (
            derived.symbol,
            int(derived.unit),
            int(derived.numerator),
            int(derived.bias),
        ) != (
            declared.symbol,
            int(declared.unit),
            int(declared.numerator),
            int(declared.bias),
        ):
            raise LoweringError(
                f"kernel {plan.kernel_id}: the output declares extent "
                f"{declared.numerator}*{declared.symbol}/{declared.unit}"
                f"+{declared.bias} and its operands sum to "
                + (
                    "a static extent"
                    if derived is None
                    else f"{derived.numerator}*{derived.symbol}/{derived.unit}"
                    f"+{derived.bias}"
                )
                + "; A17 makes the two the same number and the engine checks it"
            )

    def _phase_extent_view(
        self,
        plan: KernelPlan,
        operand: OperandPlan,
        loops: Mapping[str, int],
        extent: RequestExtent,
        *,
        writable: bool,
    ) -> int:
        """A view of ``operand`` whose leading axis states ``extent``.

        The extent is a function of ``CONTEXT_LENGTH``, so the term that walks
        it is the context loop's and the declared extent is one whole block of
        that loop plus the bias -- the same statement ``_declared_view`` makes
        for a row-blocked axis, in the context axis's own units.
        """
        context = plan.context_loop
        if context is None:
            raise LoweringError(
                f"kernel {plan.kernel_id}: a phase states a context-bound row "
                "space and no context loop resolves it"
            )
        step = extent.step(int(context.divisor))
        if step is None:
            raise LoweringError(
                f"kernel {plan.kernel_id}: a context block of {context.divisor} "
                f"symbol units is not a whole number of an axis counted as "
                f"{extent.numerator}/{extent.unit}"
            )
        return self._operand_view(
            plan,
            replace(
                operand,
                terms=("context",),
                context_axis=0,
                context_numerator=int(extent.numerator),
                context_unit=int(extent.unit),
                context_bias=int(extent.bias),
            ),
            loops,
            writable=writable,
            narrow=(0, step + int(extent.bias)),
        )

    def _phase_present_paths(
        self,
        plan: KernelPlan,
        kernel: Kernel,
        loops: Mapping[str, int],
        *,
        condition: str,
        declared_output: int,
    ) -> list[tuple[str, int, int]] | None:
        """One path per phase for a join whose sum spans two symbols.

        ``None`` when the kernel declares no phase binding, which is every join
        but DeepSeek's compressed attention view.  Otherwise the full operand
        row is emitted once per phase, each path carrying that phase's derived
        extent and that phase's rewriting of the operand's own presence
        condition.  The two are refused unless provably disjoint: each is
        evaluated under the other phase's pinned symbols and must read false
        there, because ABI 3.0 gives an instruction one predicate and a pair
        that overlapped would run twice over the same rows.
        """
        declared = kernel.attributes.get("phase_symbol_binding")
        if not declared:
            return None
        if int(kernel.attributes.get("axis", 0)) != 0:
            raise LoweringError(
                f"kernel {plan.kernel_id} declares a phase binding on a feature "
                "join; A18's extent axis is the token axis and a feature join "
                "does not move it"
            )
        base = symbol_condition(condition)
        out = next(o for o in plan.operands if o.direction == "out" and o.slot == 0)
        output_axis = self._declared_join_axis(kernel.outputs[0])
        names = list(kernel.inputs)
        paths: list[tuple[str, int, int]] = []
        triples: dict[str, tuple[Symbol, Comparison, int]] = {}
        pinned_by_phase: dict[str, dict[int, int]] = {}
        for phase, pinned in sorted(dict(declared).items()):
            constants, aliases = phase_substitution(
                pinned, f"kernel {plan.kernel_id} phase {phase!r}"
            )
            pinned_by_phase[phase] = constants
            moved = substitute_condition(base, constants, aliases)
            if moved is False:
                continue
            if moved is True:
                raise LoweringError(
                    f"kernel {plan.kernel_id}: phase {phase!r} decides the "
                    f"operand condition {condition!r} outright, so the reduced "
                    "path is unreachable there and the pair is not a pair"
                )
            extent, _static = join_extent_under(
                self.tensors, names, 0, self.span_max, constants, aliases
            )
            if extent is None:
                raise LoweringError(
                    f"kernel {plan.kernel_id}: in phase {phase!r} the join's "
                    "operands sum to a static extent, which no A18 term "
                    "resolves"
                )
            triples[phase] = moved
            if output_axis is not None and (
                extent.symbol,
                int(extent.unit),
                int(extent.numerator),
                int(extent.bias),
            ) == (
                output_axis.symbol,
                int(output_axis.unit),
                int(output_axis.numerator),
                int(output_axis.bias),
            ):
                # The declared symbol *is* this phase's sum, so the path keeps
                # the view the kernel already built.
                view = declared_output
            elif extent.symbol == "span_tokens":
                raise LoweringError(
                    f"kernel {plan.kernel_id}: phase {phase!r} sums to a "
                    "span-bound extent the output does not declare"
                )
            else:
                view = self._phase_extent_view(
                    plan, out, loops, extent, writable=True
                )
            self._phase_extent.setdefault(kernel.outputs[0], {})[str(phase)] = extent
            paths.append((str(phase), self._predicate_from_triple(moved), view))
        for phase, triple in triples.items():
            for other, constants in pinned_by_phase.items():
                if other == phase:
                    continue
                value = constants.get(int(triple[0]))
                if value is None:
                    continue
                if evaluate_comparison(triple[1], int(value), int(triple[2])):
                    raise LoweringError(
                        f"kernel {plan.kernel_id}: the {phase!r} path's "
                        f"condition still reads true under {other!r}'s pinned "
                        "symbols, so two paths would issue for one request"
                    )
        if len(paths) < 2:
            raise LoweringError(
                f"kernel {plan.kernel_id} declares a phase binding that leaves "
                f"{len(paths)} present paths; a split that does not split is a "
                "declaration nothing checks"
            )
        return paths

    def _predicate_from_triple(
        self, triple: tuple[Symbol, Comparison, int]
    ) -> int:
        symbol, comparison, immediate = triple
        key = (int(symbol), int(comparison), int(immediate))
        cached = self._predicate_cache.get(key)
        if cached is not None:
            return cached
        pid = self.builder.predicate(
            kind=PredicateKind.COMPARE_SYMBOL,
            comparison=comparison,
            selector_kind=SelectorKind.RUNTIME_SYMBOL,
            selector_index=int(symbol),
            immediate=int(immediate),
            key=(
                f"pred.{symbol.name.lower()}."
                f"{comparison.name.lower()}.{immediate}"
            ),
        )
        self._predicate_cache[key] = pid
        return pid

    def _phase_consumer_paths(
        self, plan: KernelPlan, kernel: Kernel
    ) -> dict[int, dict[str, RequestExtent]] | None:
        """Operands of this kernel whose extent the phase decides.

        A tensor produced by a phase-split join has no single A18 extent, and a
        view of it states that extent wherever it is read.  So the split does
        not stop at the producer: left unpropagated, sparse attention read the
        prefill function at decode -- 129 rows of a 137-row join -- and refused
        the rebased compressed indices its own selector had just produced.
        """
        if not self._phase_extent or not kernel.inputs:
            return None
        found: dict[int, dict[str, RequestExtent]] = {}
        for index, name in enumerate(kernel.inputs):
            phases = self._phase_extent.get(name)
            if phases is not None:
                found[index] = phases
        if not found:
            return None
        if kernel_condition(self._predicate_values, kernel) is not None:
            raise LoweringError(
                f"kernel {plan.kernel_id} reads a phase-split extent and "
                "declares a condition of its own; an ABI 3.0 instruction "
                "carries one predicate_id and there is no conjunction"
            )
        for name in kernel.outputs:
            if name in self._phase_extent:
                raise LoweringError(
                    f"kernel {plan.kernel_id} would propagate a phase-split "
                    "extent to its own output; this backend follows one hop "
                    "and refuses to guess the rest"
                )
        return found

    def _emit_phase_consumer(
        self,
        plan: KernelPlan,
        kernel: Kernel,
        loops: Mapping[str, int],
        inputs: Sequence[int],
        outputs: Sequence[int],
        paths: Mapping[int, Mapping[str, RequestExtent]],
    ) -> int:
        """One instruction per phase, each stating that phase's row space."""
        builder = self.builder
        slots = _abi_input_slots(kernel, plan.slot_order)
        phases = sorted({phase for table in paths.values() for phase in table})
        for table in paths.values():
            if sorted(table) != phases:
                raise LoweringError(
                    f"kernel {plan.kernel_id} reads two phase-split operands "
                    "that name different phases"
                )
        for phase in phases:
            row = list(inputs)
            for ir_slot, table in paths.items():
                abi_slot = next(
                    (i for i, ir in enumerate(slots) if ir == ir_slot), None
                )
                if abi_slot is None or abi_slot >= len(row):
                    raise LoweringError(
                        f"kernel {plan.kernel_id}: no ABI slot carries the "
                        f"phase-split operand {ir_slot}"
                    )
                extent = table[phase]
                if extent.symbol == "span_tokens":
                    continue  # the declared view already states this phase
                operand = next(
                    o
                    for o in plan.operands
                    if o.direction == "in" and o.slot == abi_slot
                )
                row[abi_slot] = self._phase_extent_view(
                    plan, operand, loops, extent, writable=False
                )
            builder.emit(
                Major(plan.engine_family),
                plan.engine_sub,
                descriptor_id=builder.operator(
                    engine_family=Major(plan.engine_family),
                    engine_sub=plan.engine_sub,
                    inputs=list(row),
                    outputs=list(outputs),
                    aux=list(plan.aux),
                    numeric_profile_id=self._kernel_numeric(plan),
                    schedule_id=self._schedule_for(plan),
                    counter_class_id=self._counter_class(plan.engine_family),
                    source_kernel_id=plan.index,
                    key=f"op.k{plan.index}.{phase}",
                ),
                wait_set_id=self._wait_set(self._producer_events(kernel)),
                signal_event_id=builder.new_event(),
                predicate_id=self._phase_predicate((phase,)),
                source_operation_id=plan.index,
            )
        join = builder.new_event()
        builder.emit(
            Major.CONTROL,
            Control.NOP,
            signal_event_id=join,
            source_operation_id=plan.index,
        )
        return join

    def _reduced_join_output(
        self,
        plan: KernelPlan,
        kernel: Kernel,
        loops: Mapping[str, int],
        absent: int,
    ) -> int:
        """``out0`` of the path where one join operand is absent."""
        axis = int(kernel.attributes.get("axis", 0))
        remaining = [
            name for index, name in enumerate(kernel.inputs) if index != absent
        ]
        extent, static = join_extent(self.tensors, remaining, axis, self.span_max)
        out = next(o for o in plan.operands if o.direction == "out" and o.slot == 0)
        if axis == 0:
            if extent is None:
                raise LoweringError(
                    f"kernel {plan.kernel_id}: with operand {absent} absent "
                    "the join has no request-determined extent, so its output "
                    "would present its declared maximum"
                )
            return self._operand_view(
                plan,
                replace(
                    out,
                    extent_numerator=extent.numerator,
                    extent_unit=extent.unit,
                    extent_bias=extent.bias,
                ),
                loops,
                writable=True,
            )
        # A17's feature join.  The kept segments are a prefix of the
        # destination's columns, so the reduced path is the same buffer with a
        # shorter extent on that axis.  A width the request still decides has
        # nowhere to be stated -- A18 gives a view one extent axis and the
        # token axis already holds it -- so that shape is refused rather than
        # given a maximum.
        if extent is not None:
            raise LoweringError(
                f"kernel {plan.kernel_id}: the reduced feature join still has "
                "a request-determined width, and amendment A18 gives a view "
                "one extent axis, which the token axis already holds"
            )
        return self._operand_view(
            plan, out, loops, writable=True, narrow=(axis, static)
        )

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
        self._close_loops(loops, ["context", "row"])
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
        # The member is the *base* of this operand's own band inside the
        # resource, and the layer loop steps one window per iteration from
        # there.  It was previously dropped, which was harmless only while every
        # merged resource held exactly one band and the base was always zero;
        # a pooled resource (``_pool_states``) puts a later band at a non-zero
        # base and dropping it would address the first band's members instead --
        # legal offsets, no trap, another layer's KV history.
        offset = member * window + column
        loop = loops.get("layer")
        if len(state.members) > 1 and loop is not None:
            terms.append(DynamicTerm.loop(loop, window))
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
            # A state read is one instruction and no operator descriptor, so
            # it takes the kernel's predicate directly.  This is the shape A18
            # names: the compressed-KV valid view leads with
            # ``context_groups_ratioN``, which is zero until the context holds
            # one whole group, and a zero-extent view is refused -- so the read
            # must not be issued rather than issued against nothing.
            self.builder.emit(
                Major.STATE,
                sub,
                descriptor_id=self._state_descriptor[physical_id],
                predicate_id=self._kernel_predicate(plan),
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
            # The induction variable counts *blocks*, not rows, so the step is
            # one.  Device._loop_trip already divides the symbol by
            # bound_divisor: trip = ceil(ceil(span / divisor) / step).  A step
            # of divisor divides twice, which yields one iteration at any span
            # -- correct only while the whole prompt fits in a single block,
            # and silently dropping every token past the first block above it.
            upper_bound=spec.trip,
            step=1,
            max_iterations=spec.trip,
            bound_symbol=Symbol.SPAN_TOKENS,
            bound_divisor=spec.divisor,
            counter_class_id=self._counter_class(plan.engine_family),
            key=f"loop.{spec.loop_key}",
        )
        self.builder.open_loop(loop)
        loops["row"] = loop
        context = plan.context_loop
        if context is not None:
            # Innermost, and it runs once.  Amendment A18 shortens an axis only
            # through a loop term that walks it, so an operand whose extent the
            # request decides needs a loop even when nothing about it iterates
            # -- one block over the whole declared capacity is that loop, and
            # the resolution it carries is the point of it.  The token loop
            # says the same thing about the token axis whenever a single block
            # covers the span.
            loop = self.builder.loop_control(
                lower_bound=0,
                upper_bound=context.trip,
                step=1,
                max_iterations=context.trip,
                bound_symbol=Symbol[context.symbol.upper()],
                bound_divisor=context.divisor,
                counter_class_id=self._counter_class(plan.engine_family),
                key=f"loop.{context.loop_key}",
            )
            self.builder.open_loop(loop)
            loops["context"] = loop
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
            reduction_order=reduction_order_for(
                contract, plan.kind, kernel.attributes
            ),
            scale_bits=_binary32_bits(
                kernel.attributes,
                # Every spelling the released exporters use for "the constant
                # this operation scales by".  An unrecognised one is not a
                # missed optimisation: the field stays zero, the engine refuses
                # an operator whose scale is not a positive finite binary32,
                # and the refusal names the operator rather than the attribute
                # that was never read -- so it fails a long way from its cause.
                # ``head_weight_scale_binary32`` is ``VECTOR.INDEX_SCORE``'s,
                # and its absence here is the same class of defect as
                # ``context_length`` missing from a symbol map.
                (
                    "scale_bits",
                    "score_scale_binary32",
                    "head_weight_scale_binary32",
                    "scale_bf16_code",
                    "scale",
                ),
            ),
            epsilon_bits=self._epsilon_bits(plan, kernel),
        )

    def _epsilon_bits(self, plan: KernelPlan, kernel: Kernel) -> int:
        """The numeric descriptor's epsilon, in the encoding its opcode reads.

        A NUMERIC descriptor's epsilon field is a binary32 pattern for every
        contract that adds the epsilon in binary32.  The released *unweighted*
        head RMSNorm is not one of them: it is qualified against
        ``runtime.reference.normalization.head_rms_norm_bf16``, which takes a
        BF16 epsilon code because the released kernel adds it to a BF16 mean,
        and the engine refuses any other encoding rather than guess which one a
        pattern is in.  So the narrowing belongs here, where the operand arity
        that distinguishes the two head-norm contracts is known.  The weighted
        head norm -- Qwen's, which passes a gain vector -- keeps binary32.
        """
        bits = _binary32_bits(kernel.attributes, ("epsilon_bits", "epsilon"))
        if plan.kind != "HEAD_RMS_NORM" or not bits:
            return bits
        if sum(1 for o in plan.operands if o.direction == "in") != 1:
            return bits
        return _narrow_bf16_rne(bits)

    def _producer_events(self, kernel: Kernel) -> list[int]:
        return [
            self._event_of_tensor[name]
            for name in kernel.inputs
            if name in self._event_of_tensor
        ]

    # -- cluster traffic ---------------------------------------------------
    def _maybe_link(
        self, plan: KernelPlan, event: int, loops: Mapping[str, int]
    ) -> int:
        """Emit this kernel's cluster traffic, if it has any.

        Two kinds of kernel declare a traffic class and they need opposite
        things.

        A **node-sharded contraction** really does have to move bytes: node *k*
        computed columns ``[k*S, (k+1)*S)`` of the result and nothing else, and
        every consumer wants the whole row.  That is an all-gather, and
        :meth:`_emit_all_gather` emits it as one.

        Every **other** class -- expert dispatch, sparse gather, the ordered
        sums -- names a kernel this plan *replicates*: every node holds the same
        operands and computes the same result, because the plan's only shard
        axis is a contraction's output columns.  Such a kernel moves nothing and
        waits for nothing: its inputs are node-local and so are its outputs.  So
        it emits no traffic, and the site is recorded in
        ``replicated_link_sites`` instead.

        Emitting a collective there would gather thirty-two identical buffers
        into a destination nothing reads, and emitting a barrier would cost the
        fabric's barrier messages for a synchronisation the dependency has
        already provided.  Either would put bytes and messages into a comparison
        that no operand needed, which is the failure this program exists to
        remove -- and the number of transfers a machine performs is one of the
        two numbers the whole comparison turns on.

        The gap this leaves is worth stating plainly: a 256-expert MoE whose
        experts are *not* distributed across the cluster has no expert-dispatch
        traffic, and that is a property of this plan's sharding, not of the
        model.  Declaring dispatch traffic that no operand needs would hide it.
        """
        if self.node_count <= 1 or not plan.link_class:
            return event
        out = next(
            (o for o in plan.operands if o.direction == "out" and o.slot == 0), None
        )
        sharded = (
            plan.contraction
            and out is not None
            and out.residence == "arena"
            and plan.shard_columns not in (0, out.cols)
        )
        if sharded:
            return self._emit_all_gather(plan, out, loops, event)
        self._replicated_links[plan.link_class] = (
            self._replicated_links.get(plan.link_class, 0) + 1
        )
        return event

    def _participant_array(self, elements: int, dtype: str) -> int:
        """The symmetric receive buffer of an ``elements``-element exchange.

        Every node holds the whole ``participant_count``-slot array and arrives
        at the collective with its own slot filled; the all-gather fills in the
        other thirty-one from the other thirty-one arenas.  That is the ordinary
        way an all-gather is posted, and it is what makes ``remote_offset +
        k * byte_extent`` name participant *k*'s contribution on a distributed
        device exactly as it does on a single one.
        """
        key = (dtype, int(elements))
        existing = self._exchange_object.get(key)
        if existing is not None:
            return existing
        size = bytes_for(elements, dtype)
        oid = self.builder.memory_object(
            storage_class=StorageClass.HBM,
            size_bytes=size,
            source=ObjectSource.zeros(size),
            # REMOTE is what exports the object to the fabric.  Nothing else in
            # the deployment carries it, so nothing else can be the endpoint of
            # a transfer -- which is the property that keeps a node's arena
            # private.
            permissions=int(Permission.READ | Permission.WRITE | Permission.REMOTE),
            base_address=self._extra_hbm(size),
            bank_or_tile=0,
            alignment_log2=12,
            key=f"obj.exchange.{dtype}.{elements}",
        )
        self._exchange_object[key] = oid
        return oid

    def _emit_all_gather(
        self,
        plan: KernelPlan,
        out: OperandPlan,
        loops: Mapping[str, int],
        wait: int,
    ) -> int:
        """Pack this node's column band, gather all thirty-two, unpack them.

        The contraction has written ``[B, S]`` into columns ``[k*S, (k+1)*S)``
        of node *k*'s own copy of a ``[rows, cols]`` activation buffer.  A
        column band is not a contiguous byte range -- its rows are ``cols``
        apart -- and a COMMUNICATION descriptor moves a byte extent, so the
        exchange is the three steps a real all-gather is:

        1. **pack**: the band into slot ``NODE_ID`` of a participant array laid
           out ``[node][B][S]``, where it *is* contiguous;
        2. **gather**: ``LINK.COLLECTIVE ALL_GATHER`` over the array, which
           reads slot *k* out of node *k*'s arena and lands all thirty-two slots
           in every node's copy;
        3. **unpack**: the gathered ``[node][B][S]`` back into the ``[B, cols]``
           block of the activation buffer, on every node.

        Both DMAs are stated as rank-3/rank-2 views whose *leading* axis is not
        the token axis.  That is deliberate: amendment A13 clamps a view's
        leading extent when a symbol-bounded block loop walks it, and the two
        endpoints of a transfer would then disagree on the final partial block
        -- the activation buffer's view would clamp to the rows the request has
        and the fixed-extent staging buffer's would not.  Presenting both sides
        column-major keeps the block whole on both, so the transfer always moves
        one whole block.  The rows past the span carry whatever the buffer held;
        they are never read, because every consumer's view is clamped.
        """
        builder = self.builder
        dtype = dtype_of(out.dtype)
        object_id, base = self._object_for(out)
        cols = max(out.cols, 1)
        shard = max(plan.shard_columns, 1)
        block = max(out.tile_rows, 1)
        nodes = self.node_count
        exchange = self._participant_array(nodes * block * shard, out.dtype)
        row_loop = loops.get("row") if "row" in out.terms else None
        row_term = (
            [DynamicTerm.loop(row_loop, cols * block)] if row_loop is not None else []
        )
        numeric = self._kernel_numeric(plan)
        schedule = self._schedule_for(plan, int(Major.DMA))
        counter = self._counter_class(int(Major.DMA))
        predicate = self._phase_predicate(plan.phases)

        pack_source = self._view(
            object_id=object_id,
            dtype=dtype,
            dims=[shard, block],
            strides=[1, cols],
            element_offset=base,
            dynamic=[DynamicTerm.symbol(Symbol.NODE_ID, shard), *row_term],
        )
        pack_destination = self._view(
            object_id=exchange,
            dtype=dtype,
            dims=[shard, block],
            strides=[1, shard],
            dynamic=[DynamicTerm.symbol(Symbol.NODE_ID, block * shard)],
            writable=True,
        )
        # Three events for the site, one per step, and none of them is
        # spare.  ADR-003 section 9 gives each engine a bounded submission and
        # *completion* queue and says nothing whatever about completion order,
        # so an engine's completions are unordered unless an event says
        # otherwise -- the microsequencer being in order sequences *issue*, not
        # completion.  Each step here therefore waits on its predecessor's
        # event: the collective on the pack, the unpack on the collective, and
        # every consumer of the result on the unpack.
        packed = builder.new_event()
        self._emit_move(
            plan, pack_source, pack_destination, numeric, schedule, counter,
            predicate, wait, packed, "pack",
        )

        _sub, _collective, route_class = _LINK_OP[plan.link_class]
        gathered = builder.new_event()
        comm = builder.communication(
            collective_op=CollectiveOp.ALL_GATHER,
            local_object_id=exchange,
            remote_object_id=exchange,
            local_offset=0,
            remote_offset=0,
            # The *per-participant* slot, never the whole payload.
            byte_extent=bytes_for(block * shard, out.dtype),
            # Every node participates: ``group_id`` selects a subset of the
            # participant set and this collective wants all of it.  The traffic
            # class is ``route_class`` and its virtual channel, which is what
            # TA-HBM-3.0 section 3.6 orders.
            group_id=NO_ID,
            route_class=route_class,
            credit_bound=self.plan.topology.credit_bound,
            retry_bound=self.plan.topology.retry_bound,
            completion_event_id=gathered,
            counter_class_id=self._counter_class(int(Major.LINK)),
            participant_count=nodes,
            chunk_bytes=self.plan.topology.chunk_bytes,
            ordering=Ordering.ACQUIRE_RELEASE,
            integrity_mode=IntegrityMode.CRC32C,
            virtual_channel=route_class % max(self.plan.topology.virtual_channels, 1),
            key=f"comm.{plan.link_class}.k{plan.index}",
        )
        builder.require(Feature.INTER_CHIP_ENDPOINT)
        builder.emit(
            Major.LINK,
            Link.COLLECTIVE,
            descriptor_id=comm,
            wait_set_id=self._wait_set([packed]),
            signal_event_id=gathered,
            predicate_id=predicate,
            source_operation_id=plan.index,
        )
        self._link_instructions += 1

        unpack_source = self._view(
            object_id=exchange,
            dtype=dtype,
            dims=[nodes, shard, block],
            strides=[block * shard, 1, shard],
        )
        unpack_destination = self._view(
            object_id=object_id,
            dtype=dtype,
            dims=[nodes, shard, block],
            strides=[shard, 1, cols],
            element_offset=base,
            dynamic=row_term,
            writable=True,
        )
        # The unpack is what actually writes the gathered rows into the
        # activation buffer, so it -- not the collective -- is what a consumer
        # must wait on.  Returning ``gathered`` here let a consumer on another
        # queue read the buffer while the unpack was still in flight, because
        # the collective signals before the unpack runs.  On the functional
        # device, which retires one instruction at a time, that was invisible;
        # on a machine with asynchronous engines it is a race.
        unpacked = builder.new_event()
        self._emit_move(
            plan, unpack_source, unpack_destination, numeric, schedule, counter,
            predicate, gathered, unpacked, "unpack",
        )
        return unpacked

    def _emit_move(
        self,
        plan: KernelPlan,
        source: int,
        destination: int,
        numeric: int,
        schedule: int,
        counter: int,
        predicate: int,
        wait: int,
        signal: int,
        tag: str,
    ) -> None:
        """One DMA.TRANSFER between two views, waiting on ``wait``."""
        operator = self.builder.operator(
            engine_family=Major.DMA,
            engine_sub=int(Dma.TRANSFER),
            inputs=[source],
            outputs=[destination],
            aux=[],
            numeric_profile_id=numeric,
            schedule_id=schedule,
            counter_class_id=counter,
            source_kernel_id=plan.index,
            key=f"op.k{plan.index}.{tag}",
        )
        self.builder.emit(
            Major.DMA,
            Dma.TRANSFER,
            descriptor_id=operator,
            wait_set_id=self._wait_set([wait]) if wait != NO_ID else NO_ID,
            signal_event_id=signal,
            predicate_id=predicate,
            source_operation_id=plan.index,
        )

    def _emit_barrier(
        self,
        link_class: str,
        tag: str,
        *,
        wait: int | None,
        source: int = NO_ID,
    ) -> int:
        """A costed, payload-free synchronisation of the whole participant set."""
        builder = self.builder
        _sub, collective, route_class = _LINK_OP[link_class]
        event = builder.new_event()
        comm = builder.communication(
            collective_op=collective,
            local_object_id=self.commit_token_object,
            remote_object_id=NO_ID,
            group_id=NO_ID,
            route_class=route_class,
            # A barrier carries no operand payload, and the engine refuses one
            # that claims to.
            byte_extent=0,
            credit_bound=self.plan.topology.credit_bound,
            retry_bound=self.plan.topology.retry_bound,
            completion_event_id=event,
            counter_class_id=self._counter_class(int(Major.LINK)),
            participant_count=self.node_count,
            chunk_bytes=self.plan.topology.chunk_bytes,
            ordering=Ordering.ACQUIRE_RELEASE,
            integrity_mode=IntegrityMode.CRC32C,
            virtual_channel=route_class % max(self.plan.topology.virtual_channels, 1),
            key=f"comm.{link_class}.{tag}",
        )
        builder.require(Feature.INTER_CHIP_ENDPOINT)
        builder.emit(
            Major.LINK,
            Link.BARRIER,
            descriptor_id=comm,
            wait_set_id=self._wait_set([wait]) if wait is not None else NO_ID,
            signal_event_id=event,
            source_operation_id=source,
        )
        self._link_instructions += 1
        return event


def shares_an_axis(
    dims: Sequence[int], strides: Sequence[int]
) -> bool:
    """True when some axis of extent above one has a stride of zero.

    Such an axis names the same elements repeatedly.  Read, that is a
    broadcast, and it is how ABI 3.0 expresses ``repeat`` without moving
    anything -- the verifier bounds a view by ``(dim - 1) * stride``, so the
    axis costs no bytes.  Written, it is an alias: every element of the axis is
    one location, and the value that survives is whichever store landed last.
    A backend must therefore never mark such a view writable.
    """
    return any(
        int(stride) == 0 and int(dim) > 1 for dim, stride in zip(dims, strides)
    )


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
        if key.endswith("_bits") or key.endswith("_binary32"):
            # A binary32 pattern, written as an integer or as the hexadecimal
            # string a frozen reference states it in.  Both name the same 32
            # bits; parsing the string here is what keeps the graph from having
            # to restate the constant a second way for a backend's benefit.
            if isinstance(value, str):
                return int(value, 0) & 0xFFFFFFFF
            return int(value) & 0xFFFFFFFF
        if key.endswith("_bf16_code"):
            return (int(value) & 0xFFFF) << 16
        if isinstance(value, bool):
            continue
        if isinstance(value, (int, float)):
            return int.from_bytes(struct.pack("<f", float(value)), "little")
    return 0


def _narrow_bf16_rne(bits: int) -> int:
    """Round a binary32 bit pattern to its BF16 code, ties to even."""
    code = (int(bits) >> 16) & 0xFFFF
    remainder = int(bits) & 0xFFFF
    if remainder > 0x8000 or (remainder == 0x8000 and code & 1):
        code = (code + 1) & 0xFFFF
    return code
