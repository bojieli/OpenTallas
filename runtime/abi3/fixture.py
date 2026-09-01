"""Tiny deterministic ABI 3.0 conformance fixture.

This is the Phase-B artifact required by the master plan: one small program
lowered through *both* storage classes -- HBM and immutable ROM -- so that the
storage-class boundary can be exercised without a model.  Two clean builds must
be byte-identical, the independent verifier must admit both, and every corrupted
variant must be rejected.

The fixture is deliberately not a model: it exists to prove the ABI, the
builder, the digest binding and the verifier, so that model lowering can be
debugged against a known-good encoder.
"""

from __future__ import annotations

from .capability import Capability
from .constants import (
    Control,
    DType,
    Feature,
    Major,
    Permission,
    Reduction,
    Selection,
    State,
    StateClass,
    StorageClass,
    Tensor,
    TopologyClass,
    counter_id,
    CounterGroup,
)
from .builder import DeploymentBuilder, DynamicTerm
from .deployment import Deployment, ObjectSource
from .descriptors import Phase, SelectionMode, Symbol

FIXTURE_ROWS = 4
FIXTURE_COLS = 8
FIXTURE_TILES = 4
FIXTURE_VOCAB = 8


def fixture_capability(topology: TopologyClass = TopologyClass.SINGLE_CHIP) -> Capability:
    """A minimal capability that admits the fixture and nothing larger."""
    features = [
        Feature.HOST_QUEUE_ABI,
        Feature.DEPLOYMENT_DESCRIPTOR_ABI,
        Feature.DETERMINISTIC_MICROSEQUENCER,
        Feature.BF16_TENSOR,
        Feature.TRANSACTIONAL_STATE,
        Feature.ON_DEVICE_SELECTION,
    ]
    if topology == TopologyClass.CLUSTER_32:
        features.append(Feature.INTER_CHIP_ENDPOINT)
    if topology == TopologyClass.WAFER_LOGICAL_DEVICE:
        features.append(Feature.WAFER_ENDPOINT)
    capability = Capability(
        capability_id="",
        topology_class=int(topology),
        features=tuple(int(f) for f in features),
        limits={
            "max_instructions": 4096,
            "max_descriptors": 4096,
            "max_loop_depth": 4,
            "max_loop_trip": 1 << 20,
            "max_retired_work": 1 << 32,
            "max_events": 256,
            "max_event_id": 511,
            "max_state_resources": 16,
            "max_outstanding_per_queue": 8,
            "max_context_positions": 64,
            "max_expert_ids": 1024,
            "max_topk": 16,
            "max_vocabulary": FIXTURE_VOCAB,
            "max_sessions": 4,
            "max_nodes": 32 if topology == TopologyClass.CLUSTER_32 else 1,
        },
        numeric_contracts=(
            "bf16_bf16_fp32_sequential_rne_v1",
            "bf16_add_rne_v1",
            "exact_index_select_v1",
        ),
        engines={
            "tensor": {"lanes": 8, "queues": 1},
            "vector": {"lanes": 8, "queues": 1},
            "dma": {"queues": 1},
            "selection": {"queues": 1},
            "state": {"queues": 1},
        },
        memory={
            "sram": {"bytes": 1 << 16, "banks": 2},
            "hbm": {"bytes": 1 << 20},
            "rom": {"bytes": 1 << 20},
        },
        technology_view="fixture",
    )
    capability.validate()
    return capability


def build_fixture(
    *,
    storage_class: StorageClass,
    capability: Capability | None = None,
    backend: str = "fixture",
    node_count: int = 1,
) -> Deployment:
    """Build the conformance fixture against ``storage_class``.

    The HBM and ROM builds differ only in the weight object's storage class and
    permissions.  Everything else -- program, views, numerics, schedule, state
    discipline, selection -- is identical, which is exactly the property the
    ROM-versus-HBM comparison protocol depends on.
    """
    capability = capability or fixture_capability()
    builder = DeploymentBuilder(
        target_id=f"fixture-{storage_class.name.lower()}",
        model_id="abi3-fixture",
        backend=backend,
        capability=capability,
    )
    builder.require(Feature.BF16_TENSOR)
    builder.topology(
        topology_class=TopologyClass(capability.topology_class),
        node_count=node_count,
        hbm_bytes_per_node=capability.memory["hbm"]["bytes"],
        sram_bytes_per_node=capability.memory["sram"]["bytes"],
        key="topology",
    )

    weight_elems = FIXTURE_TILES * FIXTURE_COLS * FIXTURE_COLS
    weight_bytes = weight_elems * 2
    weights = builder.memory_object(
        storage_class=storage_class,
        size_bytes=weight_bytes,
        source=ObjectSource.zeros(weight_bytes),
        permissions=int(Permission.READ | Permission.IMMUTABLE),
        key="obj.weights",
    )
    act_bytes = FIXTURE_ROWS * FIXTURE_COLS * 2
    activations = builder.memory_object(
        storage_class=StorageClass.SRAM,
        size_bytes=act_bytes * 2,
        source=ObjectSource.zeros(act_bytes * 2),
        permissions=int(Permission.READ | Permission.WRITE),
        key="obj.activations",
    )
    logits = builder.memory_object(
        storage_class=StorageClass.SRAM,
        size_bytes=FIXTURE_COLS * 2,
        source=ObjectSource.zeros(FIXTURE_COLS * 2),
        permissions=int(Permission.READ | Permission.WRITE),
        key="obj.logits",
    )
    # Slot 0 holds the freshly selected ID; slots 1.. are the output ring,
    # indexed by GENERATION_INDEX. The ring must therefore admit one entry per
    # reachable generation index, which the capability bounds at
    # max_context_positions -- the verifier proves exactly this and rejected an
    # earlier ring that was one element short.
    token_slots = 1 + capability.limits["max_context_positions"]
    tokens = builder.memory_object(
        storage_class=StorageClass.HOST,
        size_bytes=token_slots * 4,
        source=ObjectSource.zeros(token_slots * 4),
        permissions=int(Permission.READ | Permission.WRITE | Permission.HOST_VISIBLE),
        key="obj.tokens",
    )
    kv_committed = builder.memory_object(
        storage_class=StorageClass.STATE,
        size_bytes=64 * FIXTURE_COLS * 2,
        source=ObjectSource.zeros(64 * FIXTURE_COLS * 2),
        permissions=int(Permission.READ | Permission.STATE_COMMIT),
        key="obj.kv.committed",
    )
    kv_prepared = builder.memory_object(
        storage_class=StorageClass.STATE,
        size_bytes=64 * FIXTURE_COLS * 2,
        source=ObjectSource.zeros(64 * FIXTURE_COLS * 2),
        permissions=int(Permission.READ | Permission.STATE_PREPARE),
        key="obj.kv.prepared",
    )

    matmul_numeric = builder.numeric(
        contract="bf16_bf16_fp32_sequential_rne_v1",
        input_dtype=DType.BF16,
        output_dtype=DType.BF16,
        key="num.matmul",
    )
    select_numeric = builder.numeric(
        contract="exact_index_select_v1",
        input_dtype=DType.BF16,
        output_dtype=DType.U32,
        accumulator_dtype=DType.FP32,
        key="num.select",
    )
    # Every engine operator carries a schedule. Tile mapping is what turns an
    # operation into time in the cycle model, so an operator without one cannot
    # be timed -- and the model rightly refuses rather than assuming a shape.
    tensor_schedule = builder.schedule(
        engine_family=Major.TENSOR,
        tile_rows=FIXTURE_ROWS,
        tile_cols=FIXTURE_COLS,
        tile_depth=FIXTURE_COLS,
        bank_mask=0b11,
        max_outstanding=2,
        key="sched.tensor",
    )
    reduce_schedule = builder.schedule(
        engine_family=Major.REDUCTION,
        tile_rows=FIXTURE_ROWS,
        tile_cols=FIXTURE_COLS,
        tile_depth=1,
        bank_mask=0b01,
        key="sched.reduce",
    )
    select_schedule = builder.schedule(
        engine_family=Major.SELECTION,
        tile_rows=1,
        tile_cols=FIXTURE_COLS,
        tile_depth=1,
        bank_mask=0b01,
        key="sched.select",
    )

    tile_loop = builder.loop_control(
        lower_bound=0, upper_bound=FIXTURE_TILES, step=1, key="loop.tile"
    )

    activation_view = builder.tensor_view(
        object_id=activations,
        dtype=DType.BF16,
        dims=[FIXTURE_ROWS, FIXTURE_COLS],
        key="view.activations",
    )
    # The weight view is a function of the tile loop: one descriptor covers all
    # four tiles because the dynamic term moves the window (amendment A4).
    weight_view = builder.tensor_view(
        object_id=weights,
        dtype=DType.BF16,
        dims=[FIXTURE_COLS, FIXTURE_COLS],
        dynamic=[DynamicTerm.loop(tile_loop, FIXTURE_COLS * FIXTURE_COLS)],
        key="view.weights",
    )
    output_view = builder.tensor_view(
        object_id=activations,
        dtype=DType.BF16,
        dims=[FIXTURE_ROWS, FIXTURE_COLS],
        element_offset=FIXTURE_ROWS * FIXTURE_COLS,
        permissions=int(Permission.READ | Permission.WRITE),
        key="view.output",
    )
    logits_view = builder.tensor_view(
        object_id=logits,
        dtype=DType.BF16,
        dims=[FIXTURE_COLS],
        permissions=int(Permission.READ | Permission.WRITE),
        key="view.logits",
    )
    selected_view = builder.tensor_view(
        object_id=tokens,
        dtype=DType.U32,
        dims=[1],
        permissions=int(Permission.READ | Permission.WRITE),
        key="view.selected",
    )
    # The ring slot advances with the generation index, so one descriptor
    # serves every decode step (wire-format amendment A4).
    ring_view = builder.tensor_view(
        object_id=tokens,
        dtype=DType.U32,
        dims=[1],
        element_offset=1,
        dynamic=[DynamicTerm.symbol(Symbol.GENERATION_INDEX, 1)],
        permissions=int(Permission.READ | Permission.WRITE),
        key="view.ring",
    )
    kv_view = builder.tensor_view(
        object_id=kv_prepared,
        dtype=DType.BF16,
        dims=[64, FIXTURE_COLS],
        permissions=int(Permission.READ | Permission.WRITE),
        key="view.kv",
    )

    matmul_op = builder.operator(
        engine_family=Major.TENSOR,
        engine_sub=Tensor.MATMUL,
        inputs=[activation_view, weight_view],
        outputs=[output_view],
        numeric_profile_id=matmul_numeric,
        schedule_id=tensor_schedule,
        counter_class_id=builder.counter_class(
            int(CounterGroup.TENSOR),
            [counter_id(CounterGroup.TENSOR, 1), counter_id(CounterGroup.TENSOR, 2)],
            key="ctr.tensor",
        ),
        source_kernel_id=0,
        key="op.matmul",
    )
    reduce_op = builder.operator(
        engine_family=Major.REDUCTION,
        engine_sub=Reduction.ORDERED_SUM,
        inputs=[output_view],
        outputs=[logits_view],
        numeric_profile_id=matmul_numeric,
        schedule_id=reduce_schedule,
        source_kernel_id=1,
        key="op.reduce",
    )
    argmax_op = builder.operator(
        engine_family=Major.SELECTION,
        engine_sub=Selection.ARGMAX,
        inputs=[logits_view],
        outputs=[selected_view],
        numeric_profile_id=select_numeric,
        schedule_id=select_schedule,
        source_kernel_id=2,
        key="op.argmax",
    )
    append_op = builder.operator(
        engine_family=Major.SELECTION,
        engine_sub=Selection.TOKEN_APPEND,
        inputs=[selected_view],
        outputs=[ring_view],
        numeric_profile_id=select_numeric,
        schedule_id=select_schedule,
        source_kernel_id=3,
        key="op.append",
    )
    kv_state = builder.state(
        state_class=StateClass.KV_CACHE,
        committed_object_id=kv_committed,
        prepared_object_id=kv_prepared,
        row_bytes=FIXTURE_COLS * 2,
        capacity_rows=64,
        element_dtype=DType.BF16,
        view_descriptor_id=kv_view,
        key="state.kv",
    )
    policy = builder.generation_policy(
        eos_token_ids=[FIXTURE_VOCAB - 1],
        max_new_tokens=8,
        vocabulary_size=FIXTURE_VOCAB,
        token_ring_object_id=tokens,
        selection_mode=SelectionMode.GREEDY_ARGMAX_LOWEST_ID,
        key="policy",
    )

    # --- program ---------------------------------------------------------
    builder.emit(Major.STATE, State.PREPARE, descriptor_id=kv_state)
    builder.open_loop(tile_loop)
    matmul_event = builder.new_event()
    builder.emit(
        Major.TENSOR,
        Tensor.MATMUL,
        descriptor_id=matmul_op,
        signal_event_id=matmul_event,
        source_operation_id=0,
    )
    builder.close_loop()
    wait = builder.wait_set([matmul_event], key="wait.matmul")
    reduce_event = builder.new_event()
    builder.emit(
        Major.REDUCTION,
        Reduction.ORDERED_SUM,
        descriptor_id=reduce_op,
        wait_set_id=wait,
        signal_event_id=reduce_event,
        source_operation_id=1,
    )
    argmax_event = builder.new_event()
    builder.emit(
        Major.SELECTION,
        Selection.ARGMAX,
        descriptor_id=argmax_op,
        wait_set_id=builder.wait_set([reduce_event], key="wait.reduce"),
        signal_event_id=argmax_event,
        source_operation_id=2,
    )
    builder.emit(
        Major.SELECTION,
        Selection.TOKEN_APPEND,
        descriptor_id=append_op,
        wait_set_id=builder.wait_set([argmax_event], key="wait.argmax"),
        source_operation_id=3,
    )
    builder.emit(Major.STATE, State.COMMIT, descriptor_id=kv_state)
    builder.emit(Major.CONTROL, Control.COMPLETE)

    builder.entrypoint(
        entrypoint_id=0,
        first_instruction=0,
        phase=Phase.PREFILL,
        generation_policy_id=policy,
    )
    builder.entrypoint(
        entrypoint_id=1,
        first_instruction=0,
        phase=Phase.DECODE,
        generation_policy_id=policy,
    )
    builder.source_identity = {
        "fixture": "abi3-conformance-v1",
        "storage_class": storage_class.name,
    }
    return builder.finish()
