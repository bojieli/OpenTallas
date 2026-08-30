"""ATTENTION and SELECTION engine conformance.

Each test builds a real ABI 3.0 deployment through :class:`DeploymentBuilder`,
admits it through the independent verifier, and executes it on the functional
device.  Nothing here calls an engine with hand-made Python state: if the
descriptors cannot express the case, the case is not executable on the device
either, and that is exactly what these tests are for.
"""

from __future__ import annotations

import numpy as np

from runtime.abi3.builder import DeploymentBuilder, DynamicTerm
from runtime.abi3.capability import Capability
from runtime.abi3.constants import (
    Attention,
    CompletionStatus,
    Control,
    DType,
    Feature,
    Major,
    NO_ID,
    Permission,
    Selection,
    StorageClass,
    TopologyClass,
    TrapClass,
)
from runtime.abi3.deployment import ObjectSource
from runtime.abi3.descriptors import Phase, SelectionMode, Symbol
from runtime.abi3.records import EosReason
from runtime.reference.sparse_attention import (
    SPARSE_ATTENTION_SCALE_BINARY32,
    sparse_attention_bf16,
)
from runtime.sim.device import Device
from runtime.tensor_accelerator.attention import (
    HEAD_DIM,
    KEY_VALUE_HEADS,
    QUERY_HEADS,
    SCALE_BF16_CODE,
    gqa_causal_attention_bf16,
    make_kv_snapshot,
    prepare_kv_append,
)

# Importing an engine module registers its (family, subopcode) handlers.
import runtime.sim.engines.attention as engine_attention  # noqa: F401
import runtime.sim.engines.selection  # noqa: F401
from runtime.tensor_accelerator import sparse_attention as sparse_attention_kernel


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def widen(codes: np.ndarray) -> np.ndarray:
    """BF16 architectural bit patterns to binary32 values."""
    return (np.asarray(codes, dtype=np.uint16).astype(np.uint32) << 16).view(
        np.float32
    )


def _default_schedule(build, family) -> int:
    """A tile mapping every engine operator needs for admission.

    The verifier refuses a deployment whose operator carries none, because it
    cannot be timed. These unit tests do not depend on the schedule's contents.
    """
    schedules = build.__dict__.setdefault("_default_schedules", {})
    schedule = schedules.get(int(family))
    if schedule is None:
        schedule = build.builder.schedule(
            engine_family=family,
            tile_rows=1,
            tile_cols=1,
            tile_depth=1,
            bank_mask=0b1,
            max_outstanding=1,
        )
        schedules[int(family)] = schedule
    return schedule



def narrow(values: np.ndarray) -> np.ndarray:
    """Binary32 values to BF16 bit patterns, round-to-nearest-even."""
    bits = np.ascontiguousarray(values, dtype=np.float32).view(np.uint32)
    upper = bits >> np.uint32(16)
    discarded = bits & np.uint32(0xFFFF)
    increment = (discarded > np.uint32(0x8000)) | (
        (discarded == np.uint32(0x8000)) & ((upper & np.uint32(1)) != 0)
    )
    return (upper + increment.astype(np.uint32)).astype(np.uint16)


def bf16_uniform(rng: np.random.Generator, shape, scale: float = 1.0) -> np.ndarray:
    return narrow(rng.uniform(-scale, scale, size=shape).astype(np.float32))


def capability() -> Capability:
    cap = Capability(
        capability_id="",
        topology_class=int(TopologyClass.SINGLE_CHIP),
        features=tuple(
            int(f)
            for f in (
                Feature.HOST_QUEUE_ABI,
                Feature.DEPLOYMENT_DESCRIPTOR_ABI,
                Feature.DETERMINISTIC_MICROSEQUENCER,
                Feature.BF16_TENSOR,
                Feature.TRANSACTIONAL_STATE,
                Feature.ON_DEVICE_SELECTION,
            )
        ),
        limits={
            "max_instructions": 4096,
            "max_descriptors": 4096,
            "max_loop_depth": 4,
            "max_loop_trip": 1 << 16,
            "max_retired_work": 1 << 24,
            "max_events": 256,
            "max_outstanding_per_queue": 8,
            "max_context_positions": 4096,
            "max_expert_ids": 1024,
            "max_topk": 64,
            "max_vocabulary": 1 << 17,
            "max_sessions": 4,
            "max_nodes": 1,
        },
        numeric_contracts=("qwen3_gqa_fp32_softmax_bf16_v1",),
        engines={"attention": {"queues": 1}, "selection": {"queues": 1}},
        memory={"sram": {"bytes": 1 << 26}},
        technology_view="engine-conformance",
    )
    cap.validate()
    return cap


class Build:
    """A minimal single-transaction deployment builder for engine tests."""

    def __init__(self, name: str = "engine-test") -> None:
        self.capability = capability()
        self.builder = DeploymentBuilder(
            target_id=name, model_id=name, backend="test", capability=self.capability
        )
        self.builder.topology(
            topology_class=TopologyClass.SINGLE_CHIP,
            node_count=1,
            hbm_bytes_per_node=1 << 26,
            sram_bytes_per_node=1 << 26,
        )
        self._initial: dict[int, bytes] = {}

    def object_of(self, values: np.ndarray) -> int:
        data = np.ascontiguousarray(values).tobytes()
        oid = self.scratch(len(data))
        self._initial[oid] = data
        return oid

    def scratch(self, nbytes: int) -> int:
        return self.builder.memory_object(
            storage_class=StorageClass.SRAM,
            size_bytes=nbytes,
            source=ObjectSource.zeros(nbytes),
            permissions=int(Permission.READ | Permission.WRITE),
        )

    def view(self, oid: int, dtype: DType, dims, *, writable: bool = False, **kw):
        return self.builder.tensor_view(
            object_id=oid,
            dtype=dtype,
            dims=list(dims),
            permissions=int(Permission.READ | Permission.WRITE)
            if writable
            else int(Permission.READ),
            **kw,
        )

    def finish(self, *, policy_id: int = NO_ID) -> Device:
        self.builder.emit(Major.CONTROL, Control.COMPLETE)
        self.builder.entrypoint(
            entrypoint_id=0,
            first_instruction=0,
            phase=Phase.PREFILL,
            generation_policy_id=policy_id,
        )
        device = Device(self.builder.finish(), self.capability)
        for oid, data in self._initial.items():
            device.memory[oid].write(0, data)
        return device


def read(device: Device, view_id: int, symbols=None) -> np.ndarray:
    view = device.views.resolve(view_id, {}, symbols or {})
    return np.array(device.views.read_array(view))


def attention_numeric(build: Build, scale_bits: int) -> int:
    return build.builder.numeric(
        contract="qwen3_gqa_fp32_softmax_bf16_v1",
        input_dtype=DType.BF16,
        output_dtype=DType.BF16,
        scale_bits=scale_bits,
    )


def fp32_bits(value: float) -> int:
    return int(np.float32(value).view(np.uint32))


def reference_attention(
    q: np.ndarray,
    k: np.ndarray,
    v: np.ndarray,
    scale: float,
    visible,
) -> np.ndarray:
    """Independent binary32 attention: no BF16 rounding, no shared code."""
    qf, kf, vf = widen(q), widen(k), widen(v)
    span, heads, dim = qf.shape
    group = heads // kf.shape[1]
    out = np.zeros((span, heads, dim), dtype=np.float64)
    for token in range(span):
        rows = np.asarray(visible(token), dtype=np.int64)
        for head in range(heads):
            kv_head = head // group
            scores = (
                kf[rows, kv_head, :].astype(np.float64)
                @ qf[token, head].astype(np.float64)
            ) * float(scale)
            shifted = scores - scores.max()
            weights = np.exp(shifted)
            weights /= weights.sum()
            out[token, head] = weights @ vf[rows, kv_head, :].astype(np.float64)
    return out


# ---------------------------------------------------------------------------
# ATTENTION
# ---------------------------------------------------------------------------
def build_attention(
    *,
    sub: int,
    q: np.ndarray,
    k: np.ndarray,
    v: np.ndarray,
    extra: np.ndarray | None = None,
    extra_dtype: DType = DType.U32,
    scale_bits: int,
    aux=(),
):
    build = Build()
    span, heads, dim = q.shape
    q_view = build.view(build.object_of(q), DType.BF16, q.shape)
    k_view = build.view(build.object_of(k), DType.BF16, k.shape)
    v_view = build.view(build.object_of(v), DType.BF16, v.shape)
    inputs = [q_view, k_view, v_view]
    if extra is not None:
        inputs.append(
            build.view(build.object_of(extra), extra_dtype, extra.shape)
        )
    out_view = build.view(
        build.scratch(span * heads * dim * 2), DType.BF16, q.shape, writable=True
    )
    op = build.builder.operator(
        schedule_id=_default_schedule(build, Major.ATTENTION),
        engine_family=Major.ATTENTION,
        engine_sub=sub,
        inputs=inputs,
        outputs=[out_view],
        aux=list(aux),
        numeric_profile_id=attention_numeric(build, scale_bits),
    )
    build.builder.emit(Major.ATTENTION, sub, descriptor_id=op)
    return build, out_view


def test_gqa_reproduces_the_frozen_qwen3_kernel_bit_exactly():
    rng = np.random.default_rng(11)
    span, context = 2, 5
    q = bf16_uniform(rng, (span, QUERY_HEADS, HEAD_DIM))
    k = bf16_uniform(rng, (context, KEY_VALUE_HEADS, HEAD_DIM))
    v = bf16_uniform(rng, (context, KEY_VALUE_HEADS, HEAD_DIM))
    scale_bits = int(np.uint32(SCALE_BF16_CODE) << np.uint32(16))

    build, out_view = build_attention(
        sub=int(Attention.GQA), q=q, k=k, v=v, scale_bits=scale_bits
    )
    device = build.finish()
    result = device.run_transaction(
        device.create_session(), entrypoint_id=0, symbols={}
    )
    assert result.status == CompletionStatus.SUCCESS, result.message

    snapshot = make_kv_snapshot(
        resource_id="kv",
        generation=0,
        capacity=64,
        key_values=k[: context - span],
        value_values=v[: context - span],
    )
    prepared = prepare_kv_append(
        snapshot,
        transaction_id=1,
        expected_generation=0,
        position_start=context - span,
        key_values=k[context - span :],
        value_values=v[context - span :],
    )
    expected = gqa_causal_attention_bf16(q, snapshot, prepared)
    assert np.array_equal(read(device, out_view), expected.output_values)

    counters = result.counters
    assert counters["attention.heads"] == span * QUERY_HEADS
    assert counters["attention.context_positions"] == (context - 1) + context
    assert (
        counters["attention.score_multiplications"]
        == span * QUERY_HEADS * context * HEAD_DIM
    )
    assert (
        counters["attention.value_multiplications"]
        == counters["attention.score_multiplications"]
    )
    assert "attention.sparse_indices" not in counters


def test_gqa_matches_an_independent_binary32_attention():
    rng = np.random.default_rng(3)
    span, q_heads, kv_heads, dim, context = 3, 4, 2, 8, 6
    q = bf16_uniform(rng, (span, q_heads, dim))
    k = bf16_uniform(rng, (context, kv_heads, dim))
    v = bf16_uniform(rng, (context, kv_heads, dim))
    scale = 0.5
    build, out_view = build_attention(
        sub=int(Attention.GQA), q=q, k=k, v=v, scale_bits=fp32_bits(scale)
    )
    device = build.finish()
    result = device.run_transaction(
        device.create_session(), entrypoint_id=0, symbols={}
    )
    assert result.status == CompletionStatus.SUCCESS, result.message
    base = context - span
    expected = reference_attention(
        q, k, v, scale, lambda token: np.arange(base + token + 1)
    )
    assert np.allclose(widen(read(device, out_view)), expected, atol=0.02, rtol=0.02)


def test_gqa_output_does_not_depend_on_the_contraction_pass_length(monkeypatch):
    """The driver contracts a block of query rows at a time; that is scheduling.

    Both contractions reduce over an axis the query row does not index -- the
    head dimension for the scores, the bounded context for the values -- so
    every query row is an independent output row and the pass length cannot
    reach any element's reduction.  Shortening the pass to a single token, the
    way the driver worked before it batched, must therefore reproduce the
    batched answer bit for bit, and retire exactly the same counters.
    """
    rng = np.random.default_rng(0x9E11)
    span, q_heads, kv_heads, dim, context = 40, 8, 2, 32, 40

    def spread(shape):
        """Operands whose products span enough binades that the order of the
        reduction is observable; a one-binade operand set would sum the same in
        any order and let a reordered contraction pass unnoticed."""
        magnitude = rng.uniform(1.0, 2.0, size=shape) * 2.0 ** rng.integers(
            -4, 5, size=shape
        )
        return narrow(
            (rng.choice([-1.0, 1.0], size=shape) * magnitude).astype(np.float32)
        )

    q = spread((span, q_heads, dim))
    k = spread((context, kv_heads, dim))
    v = spread((context, kv_heads, dim))

    def run():
        build, out_view = build_attention(
            sub=int(Attention.GQA), q=q, k=k, v=v, scale_bits=fp32_bits(0.25)
        )
        device = build.finish()
        result = device.run_transaction(
            device.create_session(), entrypoint_id=0, symbols={}
        )
        assert result.status == CompletionStatus.SUCCESS, result.message
        return read(device, out_view), dict(result.counters)

    expected_values, expected_counters = run()
    group = q_heads // kv_heads
    pass_lengths = set()
    for max_rows in (group, 3 * group, 7 * group, 13 * group, 1 << 20):
        monkeypatch.setattr(engine_attention, "_MAX_BLOCK_ROWS", max_rows)
        pass_length = engine_attention._token_block(span, context, group)
        pass_lengths.add(pass_length)
        values, counters = run()
        assert np.array_equal(values, expected_values), pass_length
        assert counters == expected_counters, pass_length
    # The sweep is only meaningful if it really spanned one token per pass to
    # the whole span in one pass: a vacuous sweep must not report a pass.
    assert 1 in pass_lengths and span in pass_lengths
    assert len(pass_lengths) >= 4


def test_gqa_is_causal_by_absolute_position():
    rng = np.random.default_rng(5)
    span, q_heads, kv_heads, dim, context = 1, 2, 1, 4, 4
    q = bf16_uniform(rng, (span, q_heads, dim))
    k = bf16_uniform(rng, (context, kv_heads, dim))
    v = bf16_uniform(rng, (context, kv_heads, dim))

    def run(keys, values, symbols):
        build, out_view = build_attention(
            sub=int(Attention.GQA),
            q=q,
            k=keys,
            v=values,
            scale_bits=fp32_bits(0.25),
            aux=[NO_ID, NO_ID, NO_ID, int(Symbol.POSITION_START)],
        )
        device = build.finish()
        result = device.run_transaction(
            device.create_session(), entrypoint_id=0, symbols=symbols
        )
        assert result.status == CompletionStatus.SUCCESS, result.message
        return read(device, out_view), result

    symbols = {int(Symbol.POSITION_START): 1}
    first, result = run(k, v, symbols)
    poisoned_k = k.copy()
    poisoned_v = v.copy()
    poisoned_k[2:] = narrow(np.full((2, kv_heads, dim), 7.5, dtype=np.float32))
    poisoned_v[2:] = narrow(np.full((2, kv_heads, dim), -7.5, dtype=np.float32))
    second, _ = run(poisoned_k, poisoned_v, symbols)
    assert np.array_equal(first, second)
    # Query 0 sits at absolute position 1, so exactly two positions are visible.
    assert result.counters["attention.context_positions"] == 2


def test_gqa_bounds_the_context_with_a_runtime_symbol():
    """A KV view spans its capacity; only the filled rows may be read."""
    rng = np.random.default_rng(23)
    span, q_heads, kv_heads, dim, capacity, filled = 1, 2, 1, 4, 6, 4
    q = bf16_uniform(rng, (span, q_heads, dim))
    k = bf16_uniform(rng, (capacity, kv_heads, dim))
    v = bf16_uniform(rng, (capacity, kv_heads, dim))
    # Rows beyond the filled length hold whatever the cache held before.
    k[filled:] = narrow(np.full((capacity - filled, kv_heads, dim), 9.0, np.float32))
    v[filled:] = narrow(np.full((capacity - filled, kv_heads, dim), -9.0, np.float32))

    build, bounded_view = build_attention(
        sub=int(Attention.GQA),
        q=q,
        k=k,
        v=v,
        scale_bits=fp32_bits(0.5),
        aux=[NO_ID, NO_ID, int(Symbol.CONTEXT_LENGTH)],
    )
    device = build.finish()
    bounded = device.run_transaction(
        device.create_session(),
        entrypoint_id=0,
        symbols={int(Symbol.CONTEXT_LENGTH): filled},
    )
    assert bounded.status == CompletionStatus.SUCCESS, bounded.message

    trimmed_build, trimmed_view = build_attention(
        sub=int(Attention.GQA),
        q=q,
        k=k[:filled],
        v=v[:filled],
        scale_bits=fp32_bits(0.5),
    )
    trimmed_device = trimmed_build.finish()
    trimmed = trimmed_device.run_transaction(
        trimmed_device.create_session(), entrypoint_id=0, symbols={}
    )
    assert trimmed.status == CompletionStatus.SUCCESS, trimmed.message
    assert np.array_equal(
        read(device, bounded_view), read(trimmed_device, trimmed_view)
    )
    assert bounded.counters["attention.context_positions"] == filled


def test_gqa_rejects_a_context_symbol_beyond_the_kv_view():
    rng = np.random.default_rng(29)
    q = bf16_uniform(rng, (1, 1, 4))
    k = bf16_uniform(rng, (3, 1, 4))
    v = bf16_uniform(rng, (3, 1, 4))
    build, _ = build_attention(
        sub=int(Attention.GQA),
        q=q,
        k=k,
        v=v,
        scale_bits=fp32_bits(0.5),
        aux=[NO_ID, NO_ID, int(Symbol.CONTEXT_LENGTH)],
    )
    device = build.finish()
    result = device.run_transaction(
        device.create_session(),
        entrypoint_id=0,
        symbols={int(Symbol.CONTEXT_LENGTH): 9},
    )
    assert result.status == CompletionStatus.FAILED
    assert result.trap_class == TrapClass.DESCRIPTOR_OR_ADDRESS


def test_dense_rejects_a_grouped_head_map():
    rng = np.random.default_rng(9)
    q = bf16_uniform(rng, (1, 4, 4))
    k = bf16_uniform(rng, (2, 2, 4))
    v = bf16_uniform(rng, (2, 2, 4))
    build, _ = build_attention(
        sub=int(Attention.DENSE), q=q, k=k, v=v, scale_bits=fp32_bits(0.5)
    )
    device = build.finish()
    result = device.run_transaction(
        device.create_session(), entrypoint_id=0, symbols={}
    )
    assert result.status == CompletionStatus.FAILED
    assert result.trap_class == TrapClass.DESCRIPTOR_OR_ADDRESS
    assert "ATTENTION.DENSE" in result.message


def test_dense_matches_an_independent_binary32_attention():
    rng = np.random.default_rng(21)
    span, heads, dim, context = 2, 2, 4, 3
    q = bf16_uniform(rng, (span, heads, dim))
    k = bf16_uniform(rng, (context, heads, dim))
    v = bf16_uniform(rng, (context, heads, dim))
    build, out_view = build_attention(
        sub=int(Attention.DENSE),
        q=q,
        k=k,
        v=v,
        scale_bits=fp32_bits(0.5),
        aux=[NO_ID, 1],  # full visibility
    )
    device = build.finish()
    result = device.run_transaction(
        device.create_session(), entrypoint_id=0, symbols={}
    )
    assert result.status == CompletionStatus.SUCCESS, result.message
    expected = reference_attention(
        q, k, v, 0.5, lambda token: np.arange(context)
    )
    assert np.allclose(widen(read(device, out_view)), expected, atol=0.02, rtol=0.02)
    assert result.counters["attention.context_positions"] == span * context


# ---------------------------------------------------------------------------
# SPARSE (amendment A6: query / fused KV / index array / per-head sink)
# ---------------------------------------------------------------------------
def build_sparse(
    *,
    q: np.ndarray,
    kv: np.ndarray,
    indices: np.ndarray,
    sinks: np.ndarray,
    scale_bits: int = SPARSE_ATTENTION_SCALE_BINARY32,
    aux=(),
):
    """A conforming ATTENTION.SPARSE operator under amendment A6."""
    build = Build()
    span, heads, dim = q.shape
    q_view = build.view(build.object_of(q), DType.BF16, q.shape)
    kv_view = build.view(build.object_of(kv), DType.BF16, kv.shape)
    index_view = build.view(build.object_of(indices), DType.U32, indices.shape)
    sink_view = build.view(build.object_of(sinks), DType.FP32, sinks.shape)
    out_view = build.view(
        build.scratch(span * heads * dim * 2), DType.BF16, q.shape, writable=True
    )
    op = build.builder.operator(
        schedule_id=_default_schedule(build, Major.ATTENTION),
        engine_family=Major.ATTENTION,
        engine_sub=Attention.SPARSE,
        inputs=[q_view, kv_view, index_view, sink_view],
        outputs=[out_view],
        aux=list(aux),
        numeric_profile_id=attention_numeric(build, scale_bits),
    )
    build.builder.emit(Major.ATTENTION, Attention.SPARSE, descriptor_id=op)
    return build, out_view


def sparse_case(seed: int, span: int, heads: int, dim: int, rows: int):
    rng = np.random.default_rng(seed)
    q = bf16_uniform(rng, (span, heads, dim))
    kv = bf16_uniform(rng, (rows, dim))
    sinks = rng.uniform(-1.0, 1.0, size=heads).astype(np.float32)
    return q, kv, sinks


def test_sparse_reproduces_the_deepseek_reference_bit_exactly():
    q, kv, sinks = sparse_case(13, span=2, heads=2, dim=4, rows=6)
    # Ascending, tail-padded with 0xffffffff, as amendment A6 fixes it.
    indices = np.array([[0, 2, NO_ID], [1, 3, 5]], dtype=np.uint32)

    build, out_view = build_sparse(q=q, kv=kv, indices=indices, sinks=sinks)
    device = build.finish()
    result = device.run_transaction(
        device.create_session(), entrypoint_id=0, symbols={}
    )
    assert result.status == CompletionStatus.SUCCESS, result.message

    expected = sparse_attention_bf16(
        [q.tolist()],
        [kv.tolist()],
        [int(code) for code in sinks.view(np.uint32)],
        [[[0, 2, -1], [1, 3, 5]]],
        scale_binary32=SPARSE_ATTENTION_SCALE_BINARY32,
    )
    assert np.array_equal(
        read(device, out_view), np.asarray(expected.values[0], dtype=np.uint16)
    )

    counters = result.counters
    # Five rows were gathered; the padding slot is neither executed nor counted.
    assert counters["attention.sparse_indices"] == 5
    assert counters["attention.context_positions"] == 5
    assert counters["attention.heads"] == 2 * 2
    assert counters["attention.score_multiplications"] == 5 * 2 * 4
    assert (
        counters["attention.value_multiplications"]
        == counters["attention.score_multiplications"]
    )
    assert counters["attention.kv_bytes_read"] == 5 * 4 * 2


def test_sparse_counts_duplicate_selections_as_separate_rows():
    """A duplicate index is another logical read and another contribution."""
    q, kv, sinks = sparse_case(31, span=1, heads=1, dim=4, rows=4)
    indices = np.array([[1, 1, 2]], dtype=np.uint32)
    build, out_view = build_sparse(q=q, kv=kv, indices=indices, sinks=sinks)
    device = build.finish()
    result = device.run_transaction(
        device.create_session(), entrypoint_id=0, symbols={}
    )
    assert result.status == CompletionStatus.SUCCESS, result.message
    expected = sparse_attention_bf16(
        [q.tolist()],
        [kv.tolist()],
        [int(code) for code in sinks.view(np.uint32)],
        [[[1, 1, 2]]],
        scale_binary32=SPARSE_ATTENTION_SCALE_BINARY32,
    )
    assert np.array_equal(
        read(device, out_view), np.asarray(expected.values[0], dtype=np.uint16)
    )
    assert result.counters["attention.sparse_indices"] == 3


def test_sparse_output_does_not_depend_on_the_query_row_tile(monkeypatch):
    """The engine drives a kernel that tiles query rows; that is scheduling.

    A sparse-attention query row resets the running maximum, the denominator
    and the output accumulator, so every row is an independent transaction and
    no tile length can reach any element's reduction -- not the ascending QK
    dot, not the ascending 64-lane AV accumulation, not the online rescale.
    Tiling one row at a time, which is the shape the exact reference executes,
    must therefore reproduce the batched answer bit for bit and retire exactly
    the same counters.
    """
    rng = np.random.default_rng(0x5A9E)
    span, heads, dim, rows, slots = 9, 3, 6, 20, 70
    # Operands spanning several binades: a one-binade operand set sums the same
    # in any order and would let a reordered reduction pass unnoticed.
    def spread(shape):
        magnitude = rng.uniform(1.0, 2.0, size=shape) * 2.0 ** rng.integers(
            -6, 7, size=shape
        )
        return narrow((rng.choice([-1.0, 1.0], size=shape) * magnitude).astype(np.float32))

    q = spread((span, heads, dim))
    kv = spread((rows, dim))
    sinks = rng.uniform(-2.5, 2.5, size=heads).astype(np.float32)
    indices = np.full((span, slots), NO_ID, dtype=np.uint32)
    for token in range(span):
        width = min(token + 2, slots, rows)
        indices[token, :width] = np.sort(
            rng.choice(rows, size=width, replace=False)
        ).astype(np.uint32)

    def run():
        build, out_view = build_sparse(q=q, kv=kv, indices=indices, sinks=sinks)
        device = build.finish()
        result = device.run_transaction(
            device.create_session(), entrypoint_id=0, symbols={}
        )
        assert result.status == CompletionStatus.SUCCESS, result.message
        return read(device, out_view), dict(result.counters)

    baseline_output, baseline_counters = run()
    # The reference answers for the same operands, so this pins the contract
    # and not merely the kernel's self-consistency.
    expected = sparse_attention_bf16(
        [q.tolist()],
        [kv.tolist()],
        [int(code) for code in sinks.view(np.uint32)],
        [[[-1 if slot == NO_ID else int(slot) for slot in row] for row in indices]],
        scale_binary32=SPARSE_ATTENTION_SCALE_BINARY32,
    )
    assert np.array_equal(
        baseline_output, np.asarray(expected.values[0], dtype=np.uint16)
    )

    observed = 0
    for budget in (1, 8, 1 << 8, 1 << 18):
        monkeypatch.setattr(sparse_attention_kernel, "_ROW_TILE_ELEMENTS", budget)
        output, counters = run()
        assert np.array_equal(output, baseline_output), budget
        assert counters == baseline_counters, budget
        observed += 1
    assert observed == 4


def test_sparse_refuses_a_dense_shaped_operand_set():
    """The pre-A6 mapping (q/k/v/mask) is refused, not reinterpreted."""
    rng = np.random.default_rng(37)
    q = bf16_uniform(rng, (2, 2, 4))
    k = bf16_uniform(rng, (6, 1, 4))
    v = bf16_uniform(rng, (6, 1, 4))
    indices = np.array([[0, 2, NO_ID], [1, 3, 5]], dtype=np.uint32)
    build, _ = build_attention(
        sub=int(Attention.SPARSE),
        q=q,
        k=k,
        v=v,
        extra=indices,
        scale_bits=fp32_bits(0.5),
    )
    device = build.finish()
    result = device.run_transaction(
        device.create_session(), entrypoint_id=0, symbols={}
    )
    assert result.status == CompletionStatus.FAILED
    assert result.trap_class == TrapClass.DESCRIPTOR_OR_ADDRESS
    assert "amendment A6" in result.message
    assert "fused BF16 KV" in result.message


def test_sparse_refuses_a_missing_attention_sink():
    """Without the per-head sink there is no denominator term to add."""
    q, kv, _ = sparse_case(41, span=1, heads=1, dim=4, rows=4)
    indices = np.array([[0, 1]], dtype=np.uint32)
    build = Build()
    span, heads, dim = q.shape
    q_view = build.view(build.object_of(q), DType.BF16, q.shape)
    kv_view = build.view(build.object_of(kv), DType.BF16, kv.shape)
    index_view = build.view(build.object_of(indices), DType.U32, indices.shape)
    out_view = build.view(
        build.scratch(span * heads * dim * 2), DType.BF16, q.shape, writable=True
    )
    op = build.builder.operator(
        schedule_id=_default_schedule(build, Major.ATTENTION),
        engine_family=Major.ATTENTION,
        engine_sub=Attention.SPARSE,
        inputs=[q_view, kv_view, index_view],
        outputs=[out_view],
        numeric_profile_id=attention_numeric(
            build, SPARSE_ATTENTION_SCALE_BINARY32
        ),
    )
    build.builder.emit(Major.ATTENTION, Attention.SPARSE, descriptor_id=op)
    device = build.finish()
    result = device.run_transaction(
        device.create_session(), entrypoint_id=0, symbols={}
    )
    assert result.status == CompletionStatus.FAILED
    assert result.trap_class == TrapClass.DESCRIPTOR_OR_ADDRESS
    assert "attention-sink" in result.message


def test_sparse_rejects_a_block_width_other_than_the_frozen_one():
    q, kv, sinks = sparse_case(43, span=1, heads=1, dim=4, rows=4)
    indices = np.array([[0, 1]], dtype=np.uint32)
    build, _ = build_sparse(
        q=q, kv=kv, indices=indices, sinks=sinks, aux=[NO_ID, 32]
    )
    device = build.finish()
    result = device.run_transaction(
        device.create_session(), entrypoint_id=0, symbols={}
    )
    assert result.status == CompletionStatus.FAILED
    assert result.trap_class == TrapClass.DESCRIPTOR_OR_ADDRESS
    assert "block width" in result.message


def test_sparse_rejects_interleaved_padding():
    q, kv, sinks = sparse_case(47, span=1, heads=1, dim=4, rows=4)
    indices = np.array([[0, NO_ID, 2]], dtype=np.uint32)
    build, _ = build_sparse(q=q, kv=kv, indices=indices, sinks=sinks)
    device = build.finish()
    result = device.run_transaction(
        device.create_session(), entrypoint_id=0, symbols={}
    )
    assert result.status == CompletionStatus.FAILED
    assert result.trap_class == TrapClass.DESCRIPTOR_OR_ADDRESS
    assert "trailing run" in result.message


def test_sparse_rejects_an_out_of_range_index():
    q, kv, sinks = sparse_case(17, span=1, heads=1, dim=4, rows=3)
    indices = np.array([[0, 9]], dtype=np.uint32)
    build, _ = build_sparse(q=q, kv=kv, indices=indices, sinks=sinks)
    device = build.finish()
    result = device.run_transaction(
        device.create_session(), entrypoint_id=0, symbols={}
    )
    assert result.status == CompletionStatus.FAILED
    assert result.trap_class == TrapClass.DESCRIPTOR_OR_ADDRESS
    assert "outside" in result.message


def test_sparse_bounds_the_kv_view_with_a_runtime_symbol():
    """A fused KV view spans its capacity; only the filled rows may be read."""
    q, kv, sinks = sparse_case(53, span=1, heads=1, dim=4, rows=6)
    kv[4:] = narrow(np.full((2, 4), 9.0, dtype=np.float32))
    indices = np.array([[0, 4]], dtype=np.uint32)
    build, _ = build_sparse(
        q=q,
        kv=kv,
        indices=indices,
        sinks=sinks,
        aux=[NO_ID, NO_ID, int(Symbol.CONTEXT_LENGTH)],
    )
    device = build.finish()
    result = device.run_transaction(
        device.create_session(),
        entrypoint_id=0,
        symbols={int(Symbol.CONTEXT_LENGTH): 4},
    )
    assert result.status == CompletionStatus.FAILED
    assert result.trap_class == TrapClass.DESCRIPTOR_OR_ADDRESS
    assert "outside" in result.message


def test_attention_rejects_a_non_positive_scale():
    rng = np.random.default_rng(19)
    q = bf16_uniform(rng, (1, 1, 4))
    k = bf16_uniform(rng, (2, 1, 4))
    v = bf16_uniform(rng, (2, 1, 4))
    build, _ = build_attention(
        sub=int(Attention.GQA), q=q, k=k, v=v, scale_bits=0
    )
    device = build.finish()
    result = device.run_transaction(
        device.create_session(), entrypoint_id=0, symbols={}
    )
    assert result.status == CompletionStatus.FAILED
    assert result.trap_class == TrapClass.DESCRIPTOR_OR_ADDRESS
    assert "scale" in result.message


# ---------------------------------------------------------------------------
# SELECTION
# ---------------------------------------------------------------------------
VOCABULARY = 8
EOS_TOKEN = 6


def build_selection(
    logits: np.ndarray,
    *,
    eos_tokens=(EOS_TOKEN,),
    max_new_tokens: int = 8,
    vocabulary: int = VOCABULARY,
    append: bool = True,
    token_override: np.ndarray | None = None,
):
    build = Build()
    logits_obj = build.object_of(logits)
    logits_view = build.view(logits_obj, DType.BF16, logits.shape)
    token_obj = (
        build.object_of(token_override)
        if token_override is not None
        else build.scratch(4)
    )
    token_view = build.view(token_obj, DType.U32, (1,), writable=True)
    ring_obj = build.scratch(4096 * 4)
    ring_view = build.view(
        ring_obj,
        DType.U32,
        (1,),
        writable=True,
        dynamic=[DynamicTerm.symbol(Symbol.GENERATION_INDEX, 1)],
    )
    numeric = build.builder.numeric(
        contract="exact_index_select_v1",
        input_dtype=DType.BF16,
        output_dtype=DType.U32,
    )
    policy = build.builder.generation_policy(
        eos_token_ids=list(eos_tokens),
        max_new_tokens=max_new_tokens,
        vocabulary_size=vocabulary,
        token_ring_object_id=ring_obj,
        selection_mode=SelectionMode.GREEDY_ARGMAX_LOWEST_ID,
    )
    if token_override is None:
        argmax_op = build.builder.operator(
            schedule_id=_default_schedule(build, Major.SELECTION),
            engine_family=Major.SELECTION,
            engine_sub=Selection.ARGMAX,
            inputs=[logits_view],
            outputs=[token_view],
            numeric_profile_id=numeric,
        )
        build.builder.emit(
            Major.SELECTION, Selection.ARGMAX, descriptor_id=argmax_op
        )
    if append:
        append_op = build.builder.operator(
            schedule_id=_default_schedule(build, Major.SELECTION),
            engine_family=Major.SELECTION,
            engine_sub=Selection.TOKEN_APPEND,
            inputs=[token_view],
            outputs=[ring_view],
            numeric_profile_id=numeric,
        )
        build.builder.emit(
            Major.SELECTION, Selection.TOKEN_APPEND, descriptor_id=append_op
        )
    # A generative entrypoint must contain a TOKEN_APPEND; an ARGMAX-only
    # program therefore binds its policy through the submission instead.
    device = build.finish(policy_id=policy if append else NO_ID)
    return device, policy, token_view, ring_view


def logits_of(values) -> np.ndarray:
    return narrow(np.asarray(values, dtype=np.float32))


def test_argmax_selects_the_lowest_token_id_among_the_maxima():
    logits = logits_of([1.0, 4.0, 2.0, 4.0, 4.0, 0.0, -1.0, 3.0])
    device, policy, token_view, _ = build_selection(logits, append=False)
    result = device.run_transaction(
        device.create_session(),
        entrypoint_id=0,
        symbols={},
        generation_policy_id=policy,
    )
    assert result.status == CompletionStatus.SUCCESS, result.message
    assert result.selected_token == 1
    assert int(read(device, token_view)[0]) == 1
    assert result.counters["selection.vocabulary_elements"] == VOCABULARY
    assert result.counters["selection.tie_multiplicity"] == 3
    assert result.counters["selection.tokens_selected"] == 1


def test_argmax_rejects_a_non_finite_logit():
    logits = logits_of([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0])
    logits[3] = np.uint16(0x7FC0)  # BF16 quiet NaN
    device, policy, _, _ = build_selection(logits, append=False)
    result = device.run_transaction(
        device.create_session(),
        entrypoint_id=0,
        symbols={},
        generation_policy_id=policy,
    )
    assert result.status == CompletionStatus.FAILED
    assert result.trap_class == TrapClass.NUMERIC_OR_EXCEPTIONAL_VALUE


def test_token_append_records_the_token_and_writes_the_ring():
    logits = logits_of([0.0, 0.0, 9.0, 0.0, 0.0, 0.0, 0.0, 0.0])
    device, policy, _, ring_view = build_selection(logits)
    session = device.create_session()
    result = device.run_transaction(
        session, entrypoint_id=0, symbols={}, generation_policy_id=policy
    )
    assert result.status == CompletionStatus.SUCCESS, result.message
    assert result.produced_tokens == (2,)
    assert session.generated == [2]
    assert not session.finished
    assert result.eos_reason == EosReason.NONE
    assert result.counters["selection.tokens_appended"] == 1
    assert int(read(device, ring_view, {int(Symbol.GENERATION_INDEX): 0})[0]) == 2


def test_token_append_rejects_an_out_of_vocabulary_token():
    override = np.array([VOCABULARY + 5], dtype=np.uint32)
    device, policy, _, _ = build_selection(
        logits_of([1.0] * VOCABULARY), token_override=override
    )
    result = device.run_transaction(
        device.create_session(),
        entrypoint_id=0,
        symbols={},
        generation_policy_id=policy,
    )
    assert result.status == CompletionStatus.FAILED
    assert result.trap_class == TrapClass.NUMERIC_OR_EXCEPTIONAL_VALUE
    assert result.counters["selection.invalid_tokens"] == 1
    assert "selection.tokens_appended" not in result.counters


def test_token_append_without_a_policy_is_a_fault():
    device, _, _, _ = build_selection(logits_of([1.0] * VOCABULARY))
    result = device.run_transaction(
        device.create_session(), entrypoint_id=0, symbols={}
    )
    assert result.status == CompletionStatus.FAILED
    assert result.trap_class == TrapClass.DESCRIPTOR_OR_ADDRESS
    assert "generation policy" in result.message


def test_eos_stops_the_session_and_refuses_a_post_eos_transaction():
    values = [0.0] * VOCABULARY
    values[EOS_TOKEN] = 5.0
    device, policy, _, _ = build_selection(logits_of(values))
    session = device.create_session()
    first = device.run_transaction(
        session, entrypoint_id=0, symbols={}, generation_policy_id=policy
    )
    assert first.status == CompletionStatus.SUCCESS, first.message
    assert first.selected_token == EOS_TOKEN
    assert first.eos_reason == EosReason.OFFICIAL_EOS
    assert first.counters["selection.eos_stops"] == 1
    assert session.finished

    second = device.run_transaction(
        session, entrypoint_id=0, symbols={}, generation_policy_id=policy
    )
    assert second.status == CompletionStatus.FAILED
    assert second.trap_class == TrapClass.STATE_TRANSACTION
    assert "post-EOS" in second.message
    assert second.produced_tokens == ()
