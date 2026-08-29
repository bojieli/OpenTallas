"""Shared ABI 3.0 deployment builder.

Every backend -- Qwen HBM, DeepSeek HBM cluster, Qwen ROM, DeepSeek wafer ROM --
emits its deployment through this one builder.  That is the structural guarantee
behind the program's comparability requirement: a "target" is a set of
descriptors produced by one encoder, not a separate code path with its own
record format.  A backend that needs a construct this builder cannot express
must extend the shared ABI through a versioned change, not privately.

The builder owns descriptor identity, event identity, loop-body patching and
the digest binding order.  It performs no model reasoning and no placement.
"""

from __future__ import annotations

from dataclasses import dataclass, field as dc_field
from typing import Any, Iterable, Mapping, Sequence

from .capability import Capability
from .constants import (
    DType,
    DTYPE_BITS,
    Feature,
    IntegrityMode,
    NO_ID,
    NO_NODE,
    Ordering,
    Permission,
    ReductionOrder,
    RoundingMode,
    Scope,
    StateClass,
    StorageClass,
    TopologyClass,
    Control,
    Major,
    feature_vector,
)
from .crc import sha256
from .deployment import Deployment, DescriptorTable, ObjectSource, Segment
from .descriptors import (
    Comparison,
    CollectiveOp,
    Descriptor,
    ExtendedDescriptorType,
    LayoutClass,
    MAX_DYNAMIC_TERMS,
    MAX_RANK,
    Phase,
    PredicateKind,
    SelectionMode,
    SelectorKind,
    Symbol,
    encode_entrypoint_table,
)
from .layout import RecordError
from .records import Instruction, build_program


#: Reduction order each named numeric contract fixes.
#:
#: The contract is the authority on how its accumulation associates, so the
#: builder must not default a field the contract already decides.  Amendment A8
#: of the operator conventions records the case that forced this: the frozen
#: RMSNorm kernels reduce a row with a balanced tree, but the builder defaulted
#: every numeric descriptor to ``SEQUENTIAL_ASCENDING``, so every RMSNorm
#: descriptor in every target declared an order its own kernel does not
#: execute.  A contract absent from this table keeps the ascending default.
NUMERIC_CONTRACT_REDUCTION_ORDER: Mapping[str, ReductionOrder] = {
    # Contraction: one ordered, one blocked, both exact, both declared.
    "bf16_bf16_fp32_sequential_rne_v1": ReductionOrder.SEQUENTIAL_ASCENDING,
    "bf16_bf16_fp32_blocked_rne_v1": ReductionOrder.BLOCKED_ASCENDING,
    # RMSNorm: the row sum is a balanced tree in every frozen implementation.
    "qwen3_rmsnorm_fp32_bf16_v1": ReductionOrder.PAIRWISE_TREE,
    "deepseek_rmsnorm_binary32_v1": ReductionOrder.PAIRWISE_TREE,
    "runtime.reference.normalization.rms_norm_bf16": ReductionOrder.PAIRWISE_TREE,
    "runtime.tensor_accelerator.rmsnorm.rms_norm_bf16": ReductionOrder.PAIRWISE_TREE,
}


class BuildError(ValueError):
    """Raised when a backend asks for something the ABI cannot express."""


@dataclass(slots=True)
class DynamicTerm:
    """``selector_value * element_stride`` added to a tensor view's offset."""

    kind: int
    index: int
    stride: int

    @staticmethod
    def loop(loop_descriptor_id: int, stride: int) -> "DynamicTerm":
        return DynamicTerm(int(SelectorKind.LOOP_INDUCTION), loop_descriptor_id, stride)

    @staticmethod
    def symbol(symbol: Symbol, stride: int) -> "DynamicTerm":
        return DynamicTerm(int(SelectorKind.RUNTIME_SYMBOL), int(symbol), stride)


class DeploymentBuilder:
    """Accumulates descriptors, objects and instructions for one deployment."""

    def __init__(
        self,
        *,
        target_id: str,
        model_id: str,
        backend: str,
        capability: Capability,
        topology_class: int | None = None,
        deployment_id: int = 1,
        generation: int = 1,
    ) -> None:
        self.target_id = target_id
        self.model_id = model_id
        self.backend = backend
        self.capability = capability
        self.topology_class = (
            capability.topology_class if topology_class is None else topology_class
        )
        self.deployment_id = deployment_id
        self.generation = generation
        self.table = DescriptorTable()
        self.objects: dict[int, ObjectSource] = {}
        self.instructions: list[Instruction] = []
        self.entrypoints: list[dict[str, int]] = []
        self.features: set[int] = set()
        self.source_identity: dict[str, Any] = {}
        self.notes: dict[str, Any] = {}
        self._next_event = 0
        self._loop_stack: list[tuple[int, int]] = []  # (descriptor id, setup index)
        self._topology_digest = bytes(32)
        self._names: dict[str, int] = {}

    # -- identity --------------------------------------------------------
    def name(self, key: str, descriptor_id: int) -> int:
        """Record a human-readable alias for a descriptor (diagnostics only)."""
        self._names[key] = descriptor_id
        return descriptor_id

    def lookup(self, key: str) -> int:
        try:
            return self._names[key]
        except KeyError:
            raise BuildError(f"no descriptor named {key!r}") from None

    def has(self, key: str) -> bool:
        return key in self._names

    def require(self, *features: Feature) -> None:
        for feature in features:
            self.features.add(int(feature))

    def new_event(self) -> int:
        event = self._next_event
        self._next_event += 1
        return event

    # -- descriptors -----------------------------------------------------
    def memory_object(
        self,
        *,
        storage_class: StorageClass,
        size_bytes: int,
        source: ObjectSource,
        permissions: int,
        node_id: int = NO_NODE,
        bank_or_tile: int = 0xFFFF,
        base_address: int = 0,
        alignment_log2: int = 6,
        integrity_mode: IntegrityMode = IntegrityMode.CRC32C,
        content_digest: bytes = bytes(32),
        replica_group_id: int = NO_ID,
        key: str | None = None,
    ) -> int:
        if source.size_bytes != size_bytes:
            raise BuildError(
                f"object source is {source.size_bytes} bytes, descriptor says "
                f"{size_bytes}"
            )
        descriptor = Descriptor(
            descriptor_id=NO_ID,
            descriptor_type=ExtendedDescriptorType.MEMORY_OBJECT,
            payload={
                "storage_class": int(storage_class),
                "integrity_mode": int(integrity_mode),
                "alignment_log2": alignment_log2,
                "node_id": node_id,
                "bank_or_tile": bank_or_tile,
                "base_address": base_address,
                "size_bytes": size_bytes,
                "replica_group_id": replica_group_id,
                "content_digest": content_digest,
            },
            permissions=permissions,
        )
        oid = self.table.add(descriptor)
        self.objects[oid] = source
        return self.name(key, oid) if key else oid

    def tensor_view(
        self,
        *,
        object_id: int,
        dtype: DType,
        dims: Sequence[int],
        strides: Sequence[int] | None = None,
        element_offset: int = 0,
        dynamic: Sequence[DynamicTerm] = (),
        layout_class: LayoutClass = LayoutClass.DENSE,
        scale_object_id: int = NO_ID,
        scale_block_elements: int = 0,
        edge_mask_id: int = NO_ID,
        permissions: int = int(Permission.READ),
        key: str | None = None,
    ) -> int:
        rank = len(dims)
        if not 1 <= rank <= MAX_RANK:
            raise BuildError(f"tensor view rank {rank} is out of range 1..{MAX_RANK}")
        if len(dynamic) > MAX_DYNAMIC_TERMS:
            raise BuildError(
                f"{len(dynamic)} dynamic terms exceed the maximum {MAX_DYNAMIC_TERMS}"
            )
        if strides is None:
            strides = _row_major_strides(dims)
        if len(strides) != rank:
            raise BuildError("stride count must equal the rank")
        payload: dict[str, Any] = {
            "dtype": int(dtype),
            "rank": rank,
            "layout_class": int(layout_class),
            "dynamic_term_count": len(dynamic),
            "scale_object_id": scale_object_id,
            "scale_block_elements": scale_block_elements,
            "edge_mask_id": edge_mask_id,
            "element_offset": element_offset,
        }
        for axis in range(MAX_RANK):
            payload[f"dim{axis}"] = dims[axis] if axis < rank else 0
            payload[f"stride{axis}"] = strides[axis] if axis < rank else 0
        for slot in range(MAX_DYNAMIC_TERMS):
            term = dynamic[slot] if slot < len(dynamic) else DynamicTerm(0, 0, 0)
            payload[f"term{slot}_kind"] = term.kind
            payload[f"term{slot}_index"] = term.index
            payload[f"term{slot}_stride"] = term.stride
        descriptor = Descriptor(
            descriptor_id=NO_ID,
            descriptor_type=ExtendedDescriptorType.TENSOR_VIEW,
            payload=payload,
            primary_object_id=object_id,
            secondary_object_id=scale_object_id,
            permissions=permissions,
        )
        vid = self.table.add(descriptor)
        return self.name(key, vid) if key else vid

    @staticmethod
    def _reduction_order(
        contract: str, requested: ReductionOrder | None
    ) -> ReductionOrder:
        """The reduction order a numeric descriptor must declare.

        A named contract fixes its own association, so an unstated order is
        taken from the contract rather than defaulted, and a stated order that
        contradicts the contract is refused instead of being encoded.
        """
        fixed = NUMERIC_CONTRACT_REDUCTION_ORDER.get(contract)
        if requested is None:
            if fixed is not None:
                return fixed
            return ReductionOrder.SEQUENTIAL_ASCENDING
        if fixed is not None and int(requested) != int(fixed):
            raise BuildError(
                f"numeric contract {contract!r} accumulates under "
                f"{ReductionOrder(fixed).name}, but the descriptor declares "
                f"{ReductionOrder(int(requested)).name}"
            )
        return ReductionOrder(int(requested))

    def numeric(
        self,
        *,
        contract: str,
        input_dtype: DType,
        output_dtype: DType,
        accumulator_dtype: DType = DType.FP32,
        second_input_dtype: DType | None = None,
        rounding: RoundingMode = RoundingMode.NEAREST_EVEN,
        reduction_order: ReductionOrder | None = None,
        saturate: bool = False,
        nan_policy: int = 0,
        epsilon_bits: int = 0,
        scale_bits: int = 0,
        flags: int = 0,
        key: str | None = None,
    ) -> int:
        if second_input_dtype is None:
            second_input_dtype = input_dtype
        reduction_order = self._reduction_order(contract, reduction_order)
        descriptor = Descriptor(
            descriptor_id=NO_ID,
            descriptor_type=ExtendedDescriptorType.NUMERIC,
            payload={
                "input_dtype": int(input_dtype),
                "second_input_dtype": int(second_input_dtype),
                "accumulator_dtype": int(accumulator_dtype),
                "output_dtype": int(output_dtype),
                "rounding_mode": int(rounding),
                "reduction_order": int(reduction_order),
                "saturate": int(bool(saturate)),
                "nan_policy": nan_policy,
                "epsilon_bits": epsilon_bits,
                "scale_bits": scale_bits,
                "flags": flags,
                "contract_digest": sha256(contract.encode("ascii")),
            },
            permissions=int(Permission.READ | Permission.IMMUTABLE),
        )
        nid = self.table.add(descriptor)
        self.notes.setdefault("numeric_contracts", {})[str(nid)] = contract
        return self.name(key, nid) if key else nid

    def schedule(
        self,
        *,
        engine_family: Major,
        queue_index: int = 0,
        issue_window: int = 1,
        tile_rows: int = 0,
        tile_cols: int = 0,
        tile_depth: int = 0,
        bank_mask: int = 0,
        port_mask: int = 0,
        noc_route_class: int = 0,
        resource_bound: int = 1,
        max_outstanding: int = 1,
        priority: int = 0,
        key: str | None = None,
    ) -> int:
        descriptor = Descriptor(
            descriptor_id=NO_ID,
            descriptor_type=ExtendedDescriptorType.SCHEDULE,
            payload={
                "engine_family": int(engine_family),
                "queue_index": queue_index,
                "issue_window": issue_window,
                "tile_rows": tile_rows,
                "tile_cols": tile_cols,
                "tile_depth": tile_depth,
                "bank_mask": bank_mask,
                "port_mask": port_mask,
                "noc_route_class": noc_route_class,
                "resource_bound": resource_bound,
                "max_outstanding": max_outstanding,
                "priority": priority,
            },
            permissions=int(Permission.READ | Permission.IMMUTABLE),
        )
        sid = self.table.add(descriptor)
        return self.name(key, sid) if key else sid

    def topology(
        self,
        *,
        topology_class: TopologyClass,
        node_count: int = 1,
        reticle_count: int = 0,
        tiles_per_reticle: int = 0,
        local_node_id: int = 0,
        local_reticle_id: int = 0,
        local_tile_id: int = 0,
        link_class_count: int = 0,
        active_resource_count: int = 1,
        quarantined_resource_count: int = 0,
        hbm_bytes_per_node: int = 0,
        sram_bytes_per_node: int = 0,
        link_count: int = 0,
        route_group_count: int = 0,
        epoch: int = 1,
        bisection_link_count: int = 0,
        active_resource_digest: bytes = bytes(32),
        quarantine_digest: bytes = bytes(32),
        route_table_digest: bytes = bytes(32),
        health_digest: bytes = bytes(32),
        key: str | None = None,
    ) -> int:
        payload = {
            "topology_class": int(topology_class),
            "node_count": node_count,
            "reticle_count": reticle_count,
            "tiles_per_reticle": tiles_per_reticle,
            "local_node_id": local_node_id,
            "local_reticle_id": local_reticle_id,
            "local_tile_id": local_tile_id,
            "link_class_count": link_class_count,
            "active_resource_count": active_resource_count,
            "quarantined_resource_count": quarantined_resource_count,
            "hbm_bytes_per_node": hbm_bytes_per_node,
            "sram_bytes_per_node": sram_bytes_per_node,
            "link_count": link_count,
            "route_group_count": route_group_count,
            "epoch": epoch,
            "bisection_link_count": bisection_link_count,
            "active_resource_digest": active_resource_digest,
            "quarantine_digest": quarantine_digest,
            "route_table_digest": route_table_digest,
            "health_digest": health_digest,
        }
        descriptor = Descriptor(
            descriptor_id=NO_ID,
            descriptor_type=ExtendedDescriptorType.TOPOLOGY,
            payload=payload,
            permissions=int(Permission.READ | Permission.IMMUTABLE),
        )
        tid = self.table.add(descriptor)
        # The program header binds the admitted topology and health epoch.
        self._topology_digest = sha256(descriptor.encode())
        return self.name(key, tid) if key else tid

    def communication(
        self,
        *,
        collective_op: CollectiveOp,
        local_object_id: int,
        remote_object_id: int = NO_ID,
        source_node: int = NO_NODE,
        destination_node: int = NO_NODE,
        group_id: int = NO_ID,
        route_class: int = 0,
        local_offset: int = 0,
        remote_offset: int = 0,
        byte_extent: int = 0,
        credit_bound: int = 8,
        retry_bound: int = 3,
        timeout_class: int = 1,
        completion_event_id: int = NO_ID,
        reduction_numeric_id: int = NO_ID,
        counter_class_id: int = NO_ID,
        participant_count: int = 2,
        chunk_bytes: int = 4096,
        ordering: Ordering = Ordering.RELEASE,
        integrity_mode: IntegrityMode = IntegrityMode.CRC32C,
        virtual_channel: int = 0,
        key: str | None = None,
    ) -> int:
        descriptor = Descriptor(
            descriptor_id=NO_ID,
            descriptor_type=ExtendedDescriptorType.COMMUNICATION,
            payload={
                "collective_op": int(collective_op),
                "ordering": int(ordering),
                "integrity_mode": int(integrity_mode),
                "virtual_channel": virtual_channel,
                "source_node": source_node,
                "destination_node": destination_node,
                "group_id": group_id,
                "route_class": route_class,
                "local_object_id": local_object_id,
                "remote_object_id": remote_object_id,
                "local_offset": local_offset,
                "remote_offset": remote_offset,
                "byte_extent": byte_extent,
                "credit_bound": credit_bound,
                "retry_bound": retry_bound,
                "timeout_class": timeout_class,
                "completion_event_id": completion_event_id,
                "reduction_numeric_id": reduction_numeric_id,
                "counter_class_id": counter_class_id,
                "participant_count": participant_count,
                "chunk_bytes": chunk_bytes,
            },
            primary_object_id=local_object_id,
            secondary_object_id=remote_object_id,
            permissions=int(Permission.READ | Permission.WRITE | Permission.REMOTE),
        )
        cid = self.table.add(descriptor)
        return self.name(key, cid) if key else cid

    def state(
        self,
        *,
        state_class: StateClass,
        committed_object_id: int,
        prepared_object_id: int,
        row_bytes: int,
        capacity_rows: int,
        element_dtype: DType,
        view_descriptor_id: int = NO_ID,
        session_binding_id: int = 0,
        initial_cursor_rows: int = 0,
        counter_class_id: int = NO_ID,
        node_id: int = 0,
        initial_digest: bytes = bytes(32),
        key: str | None = None,
    ) -> int:
        descriptor = Descriptor(
            descriptor_id=NO_ID,
            descriptor_type=ExtendedDescriptorType.STATE,
            payload={
                "state_class": int(state_class),
                "commit_policy": 0,
                "element_dtype": int(element_dtype),
                "session_binding_id": session_binding_id,
                "committed_object_id": committed_object_id,
                "prepared_object_id": prepared_object_id,
                "row_bytes": row_bytes,
                "capacity_rows": capacity_rows,
                "initial_cursor_rows": initial_cursor_rows,
                "generation_bits": 64,
                "counter_class_id": counter_class_id,
                "view_descriptor_id": view_descriptor_id,
                "node_id": node_id,
                "initial_digest": initial_digest,
            },
            primary_object_id=committed_object_id,
            secondary_object_id=prepared_object_id,
            permissions=int(
                Permission.READ | Permission.STATE_PREPARE | Permission.STATE_COMMIT
            ),
        )
        self.require(Feature.TRANSACTIONAL_STATE)
        sid = self.table.add(descriptor)
        return self.name(key, sid) if key else sid

    def wait_set(
        self,
        producers: Sequence[int],
        *,
        condition: int = 0,
        ordering: Ordering = Ordering.ACQUIRE,
        scope: Scope = Scope.ENGINE,
        timeout_class: int = 1,
        required_count: int = 0,
        key: str | None = None,
    ) -> int:
        if not producers:
            raise BuildError("a wait set must name at least one producer")
        if len(producers) > 12:
            raise BuildError("a wait set admits at most 12 producers")
        payload: dict[str, Any] = {
            "condition": condition,
            "ordering": int(ordering),
            "scope": int(scope),
            "producer_count": len(producers),
            "timeout_class": timeout_class,
            "required_count": required_count or len(producers),
        }
        for slot in range(12):
            payload[f"producer_{slot}"] = (
                producers[slot] if slot < len(producers) else NO_ID
            )
        descriptor = Descriptor(
            descriptor_id=NO_ID,
            descriptor_type=ExtendedDescriptorType.EVENT_WAIT_SET,
            payload=payload,
            permissions=int(Permission.READ | Permission.IMMUTABLE),
        )
        wid = self.table.add(descriptor)
        return self.name(key, wid) if key else wid

    def loop_control(
        self,
        *,
        lower_bound: int,
        upper_bound: int,
        step: int = 1,
        max_iterations: int | None = None,
        bound_symbol: Symbol | None = None,
        bound_divisor: int = 1,
        predicate_id: int = NO_ID,
        counter_class_id: int = NO_ID,
        key: str | None = None,
    ) -> int:
        if bound_symbol is None:
            selector = SelectorKind.CONSTANT
            symbol_id = NO_ID
            trip = (upper_bound - lower_bound + step - 1) // step
            declared = max_iterations if max_iterations is not None else trip
        else:
            selector = SelectorKind.RUNTIME_SYMBOL
            symbol_id = int(bound_symbol)
            if max_iterations is None:
                raise BuildError(
                    "a symbol-bounded loop must declare max_iterations so the "
                    "verifier can prove a finite work bound"
                )
            declared = max_iterations
        descriptor = Descriptor(
            descriptor_id=NO_ID,
            descriptor_type=ExtendedDescriptorType.LOOP_CONTROL,
            payload={
                "loop_index": len(self._loop_stack),
                "bound_selector_kind": int(selector),
                "lower_bound": lower_bound,
                "upper_bound": upper_bound,
                "step": step,
                "max_iterations": declared,
                "predicate_id": predicate_id,
                "bound_symbol_id": symbol_id,
                "body_start": 0,
                "body_end": 0,
                "counter_class_id": counter_class_id,
                "bound_divisor": bound_divisor,
            },
            permissions=int(Permission.READ | Permission.IMMUTABLE),
        )
        lid = self.table.add(descriptor)
        return self.name(key, lid) if key else lid

    def operator(
        self,
        *,
        engine_family: Major,
        engine_sub: int,
        inputs: Sequence[int] = (),
        outputs: Sequence[int] = (),
        aux: Sequence[int] = (),
        numeric_profile_id: int = NO_ID,
        schedule_id: int = NO_ID,
        counter_class_id: int = NO_ID,
        source_graph_operation_id: int = NO_ID,
        source_kernel_id: int = NO_ID,
        flags: int = 0,
        key: str | None = None,
    ) -> int:
        if len(inputs) > 4:
            raise BuildError("an operator admits at most four input views")
        if len(outputs) > 2:
            raise BuildError("an operator admits at most two output views")
        if len(aux) > 4:
            raise BuildError("an operator admits at most four auxiliary IDs")
        payload: dict[str, Any] = {
            "engine_family": int(engine_family),
            "engine_sub": int(engine_sub),
            "flags": flags,
            "source_graph_operation_id": source_graph_operation_id,
            "source_kernel_id": source_kernel_id,
            "counter_class_id": counter_class_id,
            "numeric_profile_id": numeric_profile_id,
            "schedule_id": schedule_id,
        }
        for slot in range(4):
            payload[f"input_view_{slot}"] = inputs[slot] if slot < len(inputs) else NO_ID
        for slot in range(2):
            payload[f"output_view_{slot}"] = (
                outputs[slot] if slot < len(outputs) else NO_ID
            )
        for slot in range(4):
            payload[f"aux_id_{slot}"] = aux[slot] if slot < len(aux) else NO_ID
        descriptor = Descriptor(
            descriptor_id=NO_ID,
            descriptor_type=ExtendedDescriptorType.OPERATOR,
            payload=payload,
            numeric_profile_id=numeric_profile_id,
            schedule_id=schedule_id,
            permissions=int(Permission.READ | Permission.EXECUTE),
        )
        oid = self.table.add(descriptor)
        return self.name(key, oid) if key else oid

    def generation_policy(
        self,
        *,
        eos_token_ids: Sequence[int],
        max_new_tokens: int,
        vocabulary_size: int,
        token_ring_object_id: int,
        selection_mode: SelectionMode = SelectionMode.GREEDY_ARGMAX_LOWEST_ID,
        counter_class_id: int = NO_ID,
        key: str | None = None,
    ) -> int:
        if len(eos_token_ids) > 8:
            raise BuildError("at most eight EOS token IDs are representable")
        payload: dict[str, Any] = {
            "selection_mode": int(selection_mode),
            "tie_rule": 0,
            "eos_count": len(eos_token_ids),
            "max_new_tokens": max_new_tokens,
            "vocabulary_size": vocabulary_size,
            "token_ring_object_id": token_ring_object_id,
            "rng_seed_lo": 0,
            "rng_seed_hi": 0,
            "counter_class_id": counter_class_id,
        }
        for slot in range(8):
            payload[f"eos_token_{slot}"] = (
                eos_token_ids[slot] if slot < len(eos_token_ids) else NO_ID
            )
        descriptor = Descriptor(
            descriptor_id=NO_ID,
            descriptor_type=ExtendedDescriptorType.GENERATION_POLICY,
            payload=payload,
            primary_object_id=token_ring_object_id,
            permissions=int(Permission.READ | Permission.IMMUTABLE),
        )
        self.require(Feature.ON_DEVICE_SELECTION)
        gid = self.table.add(descriptor)
        return self.name(key, gid) if key else gid

    def counter_class(
        self, group: int, counters: Sequence[int], *, key: str | None = None
    ) -> int:
        if len(counters) > 12:
            raise BuildError("a counter class holds at most twelve counters")
        payload: dict[str, Any] = {"group": group, "event_count": len(counters)}
        for slot in range(12):
            payload[f"counter_{slot}"] = counters[slot] if slot < len(counters) else NO_ID
        descriptor = Descriptor(
            descriptor_id=NO_ID,
            descriptor_type=ExtendedDescriptorType.COUNTER_CLASS,
            payload=payload,
            permissions=int(Permission.READ | Permission.IMMUTABLE),
        )
        cid = self.table.add(descriptor)
        return self.name(key, cid) if key else cid

    def predicate(
        self,
        *,
        kind: PredicateKind,
        comparison: Comparison = Comparison.EQ,
        selector_kind: SelectorKind = SelectorKind.RUNTIME_SYMBOL,
        selector_index: int = 0,
        immediate: int = 0,
        object_id: int = NO_ID,
        element_index: int = 0,
        key: str | None = None,
    ) -> int:
        descriptor = Descriptor(
            descriptor_id=NO_ID,
            descriptor_type=ExtendedDescriptorType.PREDICATE,
            payload={
                "predicate_kind": int(kind),
                "comparison": int(comparison),
                "selector_kind": int(selector_kind),
                "selector_index": selector_index,
                "immediate": immediate,
                "object_id": object_id,
                "element_index": element_index,
            },
            permissions=int(Permission.READ | Permission.IMMUTABLE),
        )
        pid = self.table.add(descriptor)
        return self.name(key, pid) if key else pid

    # -- instructions ----------------------------------------------------
    def emit(
        self,
        major: Major,
        sub: int,
        *,
        descriptor_id: int = NO_ID,
        control_id: int = NO_ID,
        wait_set_id: int = NO_ID,
        signal_event_id: int = NO_ID,
        predicate_id: int = NO_ID,
        source_operation_id: int = NO_ID,
        flags: int = 0,
        invert_predicate: bool = False,
    ) -> int:
        from .constants import InstructionFlag

        if predicate_id != NO_ID:
            flags |= int(InstructionFlag.PREDICATED)
            if invert_predicate:
                flags |= int(InstructionFlag.PREDICATE_INVERT)
        if wait_set_id != NO_ID:
            flags |= int(InstructionFlag.WAIT_ACQUIRE)
        if signal_event_id != NO_ID:
            flags |= int(InstructionFlag.SIGNAL_RELEASE)
        index = len(self.instructions)
        self.instructions.append(
            Instruction(
                major=int(major),
                sub=int(sub),
                flags=flags,
                predicate_id=predicate_id,
                descriptor_id=descriptor_id,
                wait_set_id=wait_set_id,
                signal_event_id=signal_event_id,
                control_id=control_id,
                source_operation_id=source_operation_id,
            )
        )
        return index

    def open_loop(self, loop_descriptor_id: int, **kwargs: Any) -> int:
        """Emit LOOP_SETUP and record the open loop for body patching."""
        index = self.emit(
            Major.CONTROL, Control.LOOP_SETUP, control_id=loop_descriptor_id, **kwargs
        )
        self._loop_stack.append((loop_descriptor_id, index))
        return index

    def close_loop(self) -> int:
        """Emit LOOP_NEXT, patching the loop descriptor's body extent."""
        if not self._loop_stack:
            raise BuildError("close_loop with no open loop")
        loop_id, setup_index = self._loop_stack.pop()
        index = self.emit(Major.CONTROL, Control.LOOP_NEXT, control_id=loop_id)
        descriptor = self.table[loop_id]
        descriptor.payload["body_start"] = setup_index + 1
        descriptor.payload["body_end"] = index
        # Re-encode the patched descriptor in place so the table digest is final.
        self.table._records[loop_id] = descriptor.encode()  # noqa: SLF001
        return index

    def entrypoint(
        self,
        *,
        entrypoint_id: int,
        first_instruction: int,
        phase: Phase,
        generation_policy_id: int = NO_ID,
    ) -> None:
        self.entrypoints.append(
            {
                "entrypoint_id": entrypoint_id,
                "first_instruction": first_instruction,
                "phase": int(phase),
                "generation_policy_id": generation_policy_id,
            }
        )

    # -- finalisation ----------------------------------------------------
    def finish(
        self, *, watchdog_class: int = 1, max_retired_work: int | None = None
    ) -> Deployment:
        if self._loop_stack:
            raise BuildError(f"{len(self._loop_stack)} loop(s) left open")
        if not self.entrypoints:
            raise BuildError("deployment declares no entrypoint")
        entry_descriptor = Descriptor(
            descriptor_id=NO_ID,
            descriptor_type=ExtendedDescriptorType.ENTRYPOINT_TABLE,
            payload={},
            raw_payload=encode_entrypoint_table(self.entrypoints),
            permissions=int(Permission.READ | Permission.IMMUTABLE),
        )
        entry_id = self.table.add(entry_descriptor)
        self.require(
            Feature.HOST_QUEUE_ABI,
            Feature.DEPLOYMENT_DESCRIPTOR_ABI,
            Feature.DETERMINISTIC_MICROSEQUENCER,
        )
        if max_retired_work is None:
            max_retired_work = self._proved_work()
        features = feature_vector(sorted(self.features))
        deployment = Deployment(
            deployment_id=self.deployment_id,
            generation=self.generation,
            target_id=self.target_id,
            model_id=self.model_id,
            backend=self.backend,
            topology_class=int(self.topology_class),
            capability_digest=self.capability.digest,
            table=self.table,
            program=b"",
            objects=dict(self.objects),
            entrypoints=tuple(self.entrypoints),
            required_features=features,
            source_identity=dict(self.source_identity),
            notes=dict(self.notes),
        )
        # The program header binds the manifest digest, and the manifest names
        # the program body digest, so the program is built in two passes: an
        # empty-program manifest fixes every non-program digest, then the real
        # header is stamped and the manifest recomputed with the final body.
        deployment.program = build_program(
            self.instructions,
            entrypoint_count=len(self.entrypoints),
            required_features=features,
            deployment_digest=bytes(32),
            descriptor_table_digest=self.table.digest,
            topology_digest=self._topology_digest,
            max_retired_work=max_retired_work,
            watchdog_class=watchdog_class,
            entrypoint_table_descriptor=entry_id,
        )
        manifest_digest = deployment.deployment_digest
        deployment.program = build_program(
            self.instructions,
            entrypoint_count=len(self.entrypoints),
            required_features=features,
            deployment_digest=manifest_digest,
            descriptor_table_digest=self.table.digest,
            topology_digest=self._topology_digest,
            max_retired_work=max_retired_work,
            watchdog_class=watchdog_class,
            entrypoint_table_descriptor=entry_id,
        )
        return deployment

    def _proved_work(self) -> int:
        """Re-derive the retired-work bound the verifier will prove.

        This runs on programs that may be deliberately malformed -- the
        conformance suite builds illegal deployments so the *verifier* can
        reject them with a specific diagnosis.  So an unbalanced loop here is
        counted conservatively rather than raised: crashing in the builder
        would replace the verifier's precise error with a stack trace and hide
        which proof actually failed.
        """
        work = 0
        multiplier = 1
        stack: list[tuple[int, int]] = []
        for instruction in self.instructions:
            if instruction.major == Major.CONTROL:
                if instruction.sub == Control.LOOP_SETUP:
                    trip = 1
                    if 0 <= instruction.control_id < len(self.table):
                        descriptor = self.table[instruction.control_id]
                        if descriptor.descriptor_type == int(
                            ExtendedDescriptorType.LOOP_CONTROL
                        ):
                            trip = max(descriptor.payload["max_iterations"], 1)
                    stack.append((instruction.control_id, trip))
                    multiplier *= trip
                    continue
                if instruction.sub == Control.LOOP_NEXT:
                    work += multiplier
                    if stack:
                        _, trip = stack.pop()
                        multiplier //= trip
                    continue
            work += multiplier
        return work


def _row_major_strides(dims: Sequence[int]) -> list[int]:
    strides = [0] * len(dims)
    running = 1
    for axis in range(len(dims) - 1, -1, -1):
        strides[axis] = running
        running *= dims[axis]
    return strides
