"""DeepSeek vector engine conformance: COMPRESS, INDEX_SCORE and MHC.

Each case builds a real ABI 3.0 deployment through :class:`DeploymentBuilder`,
admits it through the independent verifier, executes it on the functional device
and compares the bytes the device wrote against the exact scalar reference in
``runtime/reference/``.  The references decode with :class:`fractions.Fraction`
and import no host math library, so an equality here is a bit-exactness claim
against an oracle, not against a second copy of the same NumPy code.

Two of the references are frozen at the released DeepSeek-V4-Flash profile and
refuse any other shape: ``hc_pre_bf16`` and ``hc_head_bf16`` accept only one to
four tokens of four 4,096-wide BF16 streams.  Those two cases therefore run at
the full 16,384-wide profile, with sparse operands so the exact rational
reference stays inside a few seconds.  The remaining references accept general
bounded shapes and are exercised small.
"""

from __future__ import annotations

import numpy as np
import pytest

from runtime.abi3.builder import DeploymentBuilder
from runtime.abi3.capability import Capability
from runtime.abi3.constants import (
    CompletionStatus,
    Control,
    DType,
    Feature,
    Major,
    NO_ID,
    Permission,
    ReductionOrder,
    StorageClass,
    TopologyClass,
    TrapClass,
    Vector,
)
from runtime.abi3.deployment import ObjectSource
from runtime.abi3.descriptors import Phase, Symbol
from runtime.reference.compression import compress_project_bf16
from runtime.reference.compression_pool import (
    F32_NEGATIVE_INFINITY,
    compress_pool_f32,
)
from runtime.reference.compression_state import (
    compress_state_update_f32,
    zero_compression_state_f32,
)
from runtime.reference.hc_head import hc_head_bf16
from runtime.reference.formats import (
    binary32_product_add,
    decode_bf16,
    decode_binary32,
)
from runtime.reference.hyper_connection import (
    HC_MULTIPLIER,
    HIDDEN_SIZE,
    FLATTENED_WIDTH,
    MIX_PARAMETER_COUNT,
    NORMALIZATION_EPSILON_BINARY32,
    SINKHORN_ITERATIONS,
    hc_pre_bf16,
)
from runtime.reference.index_score import (
    INDEX_SCORE_SCALE_BINARY32,
    index_score_bf16,
)
from runtime.reference.vector import hc_post_bf16
from runtime.sim.device import Device
from runtime.sim.engines.deepseek_vector import (
    COMPRESS_POOL,
    COMPRESS_PROJECT,
    COMPRESS_STATE_UPDATE,
    HC_HEAD,
    HC_POST,
    HC_PRE,
    _numba,
    _ordered_product_add,
    _ordered_product_add_numba,
    _ordered_product_add_numpy,
    ordered_product_add_implementation_identity,
    reset_ordered_product_add_observations,
)

# Importing the engine module registers its (family, subopcode) handlers.
import runtime.sim.engines.deepseek_vector  # noqa: F401


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def widen(codes: np.ndarray) -> np.ndarray:
    return (np.asarray(codes, dtype=np.uint16).astype(np.uint32) << 16).view(np.float32)


def narrow(values: np.ndarray) -> np.ndarray:
    bits = np.ascontiguousarray(values, dtype=np.float32).view(np.uint32)
    upper = bits >> np.uint32(16)
    discarded = bits & np.uint32(0xFFFF)
    increment = (discarded > np.uint32(0x8000)) | (
        (discarded == np.uint32(0x8000)) & ((upper & np.uint32(1)) != 0)
    )
    return (upper + increment.astype(np.uint32)).astype(np.uint16)


def bf16_uniform(rng, shape, scale: float = 1.0) -> np.ndarray:
    return narrow(rng.uniform(-scale, scale, size=shape).astype(np.float32))


def codes32(values: np.ndarray) -> np.ndarray:
    return np.ascontiguousarray(values, dtype=np.float32).view(np.uint32)


def nested(array: np.ndarray) -> list:
    """A plain nested list of Python ints, which the references require."""
    return np.asarray(array).astype(object).tolist()


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
            "max_event_id": 511,
            "max_state_resources": 16,
            "max_outstanding_per_queue": 8,
            "max_context_positions": 4096,
            "max_expert_ids": 1024,
            "max_topk": 64,
            "max_vocabulary": 1 << 17,
            "max_sessions": 4,
            "max_nodes": 1,
        },
        numeric_contracts=(
            "deepseek_v4_compress_project_binary32_v1",
            "deepseek_v4_compress_pool_binary32_v1",
            "deepseek_v4_index_score_bf16_v1",
            "opentallas.deepseek_v4_hc_pre_numeric.v1",
        ),
        engines={"vector": {"lanes": 8, "queues": 1}},
        memory={"sram": {"bytes": 1 << 28}},
        technology_view="engine-conformance",
    )
    cap.validate()
    return cap


class Build:
    """A minimal single-transaction VECTOR deployment."""

    def __init__(self) -> None:
        self.capability = capability()
        self.builder = DeploymentBuilder(
            target_id="deepseek-vector-test",
            model_id="deepseek-vector-test",
            backend="test",
            capability=self.capability,
        )
        self.builder.topology(
            topology_class=TopologyClass.SINGLE_CHIP,
            node_count=1,
            hbm_bytes_per_node=1 << 28,
            sram_bytes_per_node=1 << 28,
        )
        self._initial: dict[int, bytes] = {}

    def scratch(self, nbytes: int) -> int:
        return self.builder.memory_object(
            storage_class=StorageClass.SRAM,
            size_bytes=nbytes,
            source=ObjectSource.zeros(nbytes),
            permissions=int(Permission.READ | Permission.WRITE),
        )

    def object_of(self, values: np.ndarray) -> int:
        data = np.ascontiguousarray(values).tobytes()
        oid = self.scratch(len(data))
        self._initial[oid] = data
        return oid

    def input_view(self, values: np.ndarray, dtype: DType) -> int:
        return self.builder.tensor_view(
            object_id=self.object_of(values),
            dtype=dtype,
            dims=list(values.shape),
            permissions=int(Permission.READ),
        )

    def output_view(self, dims, dtype: DType) -> int:
        itemsize = 2 if dtype == DType.BF16 else 4
        count = int(np.prod(dims))
        return self.builder.tensor_view(
            object_id=self.scratch(count * itemsize),
            dtype=dtype,
            dims=list(dims),
            permissions=int(Permission.READ | Permission.WRITE),
        )

    def finish(self) -> Device:
        self.builder.emit(Major.CONTROL, Control.COMPLETE)
        self.builder.entrypoint(
            entrypoint_id=0, first_instruction=0, phase=Phase.PREFILL
        )
        device = Device(self.builder.finish(), self.capability)
        for oid, data in self._initial.items():
            device.memory[oid].write(0, data)
        return device


def run(device: Device, symbols=None):
    return device.run_transaction(
        device.create_session(), entrypoint_id=0, symbols=symbols or {}
    )


def read(device: Device, view_id: int, symbols=None) -> np.ndarray:
    view = device.views.resolve(view_id, {}, symbols or {})
    return np.array(device.views.read_array(view))


def emit(
    build: Build,
    sub: Vector,
    *,
    inputs,
    outputs,
    aux,
    numeric_profile_id: int = NO_ID,
) -> None:
    # A tile mapping is required for admission: a deployment without one cannot
    # be timed. These unit tests do not depend on its contents.
    schedules = build.__dict__.setdefault("_default_schedules", {})
    schedule = schedules.get(int(Major.VECTOR))
    if schedule is None:
        schedule = build.builder.schedule(
            engine_family=Major.VECTOR,
            tile_rows=1,
            tile_cols=1,
            tile_depth=1,
            bank_mask=0b1,
            max_outstanding=1,
        )
        schedules[int(Major.VECTOR)] = schedule
    operator = build.builder.operator(
        engine_family=Major.VECTOR,
        engine_sub=int(sub),
        inputs=list(inputs),
        outputs=list(outputs),
        aux=list(aux),
        numeric_profile_id=numeric_profile_id,
        schedule_id=schedule,
    )
    build.builder.emit(Major.VECTOR, int(sub), descriptor_id=operator)


# ---------------------------------------------------------------------------
# VECTOR.COMPRESS -- COMPRESS_PROJECT
# ---------------------------------------------------------------------------
def test_accelerated_ordered_product_is_bit_exact_and_k_serial():
    if _ordered_product_add_numba is None:
        pytest.skip("the optional numba DeepSeek simulator extra is not installed")

    rng = np.random.default_rng(0xA3)
    # 2 * 4 * 64 * 2048 reaches the deterministic acceleration threshold.
    # The leading dimensions also prove that only independent row/output
    # coordinates are flattened; K retains its original increasing order.
    rows = widen(bf16_uniform(rng, (2, 4, 2048), scale=4.0))
    weights = widen(bf16_uniform(rng, (64, 2048), scale=4.0))
    # Preserve the portable implementation's whole-column signed-zero skip.
    rows[..., 7] = np.float32(-0.0)
    rows[..., 101] = np.float32(0.0)

    reset_ordered_product_add_observations()
    expected = _ordered_product_add_numpy(rows, weights)
    produced = _ordered_product_add(rows, weights)

    assert produced.shape == (2, 4, 64)
    assert np.array_equal(codes32(produced), codes32(expected))
    identity = ordered_product_add_implementation_identity()
    assert identity["numba_available"] is True
    assert identity["accelerated_kernel"] == "numba_fastmath_false_k_serial_v1"
    assert identity["executed"]["numba_calls"] == 1
    assert identity["executed"]["numpy_calls"] == 0

    previous_threads = _numba.get_num_threads()
    try:
        for threads in sorted({1, min(4, previous_threads)}):
            _numba.set_num_threads(threads)
            threaded = _ordered_product_add_numba(
                rows.reshape(-1, rows.shape[-1]), weights
            ).reshape(produced.shape)
            assert np.array_equal(codes32(threaded), codes32(expected))
    finally:
        _numba.set_num_threads(previous_threads)


def test_accelerated_ordered_product_matches_independent_scalar_fma():
    if _ordered_product_add_numba is None:
        pytest.skip("the optional numba DeepSeek simulator extra is not installed")

    rng = np.random.default_rng(0xB3)
    row_codes = bf16_uniform(rng, (3, 19), scale=2.0)
    rows = widen(row_codes)
    weights = rng.uniform(-2.0, 2.0, size=(5, 19)).astype(np.float32)
    produced = codes32(_ordered_product_add_numba(rows, weights))

    expected = np.empty((3, 5), dtype=np.uint32)
    weight_codes = codes32(weights)
    for row in range(3):
        for output in range(5):
            accumulator = 0
            for index in range(19):
                left = decode_bf16(int(row_codes[row, index])).value
                right = decode_binary32(int(weight_codes[output, index])).value
                assert left is not None and right is not None
                accumulator = binary32_product_add(accumulator, left, right)
            expected[row, output] = accumulator

    assert np.array_equal(produced, expected)


def test_accelerated_ordered_product_preserves_subnormal_and_signed_zero_edges():
    if _ordered_product_add_numba is None:
        pytest.skip("the optional numba DeepSeek simulator extra is not installed")

    row_codes = np.asarray(
        [
            [
                0x0001,
                0x8001,
                0x007F,
                0x807F,
                0x0080,
                0x8080,
                0x3F80,
                0xBF80,
                0x4000,
                0xC000,
                0x0000,
                0x8000,
            ]
        ],
        dtype=np.uint16,
    )
    weight_codes = np.asarray(
        [
            [
                0x3F800000,
                0xBF800000,
                0x40000000,
                0xC0000000,
                0x00800000,
                0x80800000,
                0x00000001,
                0x80000001,
                0x3F000000,
                0xBF000000,
                0x00000000,
                0x80000000,
            ]
        ],
        dtype=np.uint32,
    )
    produced = codes32(
        _ordered_product_add_numba(widen(row_codes), weight_codes.view(np.float32))
    )[0, 0]
    expected = 0
    for left_code, right_code in zip(row_codes[0], weight_codes[0], strict=True):
        left = decode_bf16(int(left_code)).value
        right = decode_binary32(int(right_code)).value
        assert left is not None and right is not None
        expected = binary32_product_add(expected, left, right)

    assert int(produced) == expected


def build_compress_project(hidden, kv_weight, gate_weight, *, outputs=None):
    build = Build()
    batch, span, _ = hidden.shape
    features = kv_weight.shape[0]
    numeric = build.builder.numeric(
        contract="deepseek_v4_compress_project_binary32_v1",
        input_dtype=DType.BF16,
        output_dtype=DType.FP32,
        reduction_order=ReductionOrder.SEQUENTIAL_ASCENDING,
    )
    out = build.output_view(
        outputs if outputs is not None else (batch, span, 2, features), DType.FP32
    )
    emit(
        build,
        Vector.COMPRESS,
        inputs=[
            build.input_view(hidden, DType.BF16),
            build.input_view(kv_weight, DType.BF16),
            build.input_view(gate_weight, DType.BF16),
        ],
        outputs=[out],
        aux=[COMPRESS_PROJECT],
        numeric_profile_id=numeric,
    )
    return build, out


def test_compress_project_matches_the_exact_reference():
    rng = np.random.default_rng(17)
    hidden = bf16_uniform(rng, (1, 3, 8))
    kv_weight = bf16_uniform(rng, (4, 8))
    gate_weight = bf16_uniform(rng, (4, 8))

    build, out = build_compress_project(hidden, kv_weight, gate_weight)
    device = build.finish()
    result = run(device)
    assert result.status == CompletionStatus.SUCCESS, result.message

    expected = compress_project_bf16(
        nested(hidden), nested(kv_weight), nested(gate_weight)
    )
    produced = codes32(read(device, out))
    assert np.array_equal(produced[:, :, 0, :], np.asarray(expected.kv, dtype=np.uint32))
    assert np.array_equal(
        produced[:, :, 1, :], np.asarray(expected.scores, dtype=np.uint32)
    )
    assert result.counters["vector.compress_rows"] == 3


def test_compress_project_refuses_an_output_that_is_not_the_packed_pair():
    rng = np.random.default_rng(18)
    hidden = bf16_uniform(rng, (1, 2, 8))
    kv_weight = bf16_uniform(rng, (4, 8))
    gate_weight = bf16_uniform(rng, (4, 8))
    build, _ = build_compress_project(
        hidden, kv_weight, gate_weight, outputs=(1, 2, 3, 4)
    )
    result = run(build.finish())
    assert result.status == CompletionStatus.FAILED
    assert result.trap_class == int(TrapClass.DESCRIPTOR_OR_ADDRESS)
    assert "packed KV-then-gate result" in result.message


def test_compress_refuses_an_unknown_sub_case():
    rng = np.random.default_rng(19)
    hidden = bf16_uniform(rng, (1, 2, 8))
    build = Build()
    emit(
        build,
        Vector.COMPRESS,
        inputs=[build.input_view(hidden, DType.BF16)],
        outputs=[build.output_view((1, 2, 8), DType.FP32)],
        aux=[7],
    )
    result = run(build.finish())
    assert result.status == CompletionStatus.FAILED
    assert result.trap_class == int(TrapClass.DESCRIPTOR_OR_ADDRESS)
    assert "sub-case" in result.message


# ---------------------------------------------------------------------------
# VECTOR.COMPRESS -- COMPRESS_POOL
# ---------------------------------------------------------------------------
POOL_RATIO = 4
POOL_HEAD_DIM = 128
POOL_AXIS = 2 * POOL_RATIO


def overlap_pool_operands(rng, groups: int = 2):
    """A ratio-four pool block carrying the released overlap sentinel."""
    kv = rng.uniform(-2.0, 2.0, size=(1, groups, POOL_AXIS, POOL_HEAD_DIM)).astype(
        np.float32
    )
    scores = rng.uniform(-3.0, 3.0, size=kv.shape).astype(np.float32)
    # Pool group zero receives four zero-KV / negative-infinity-score rows.
    kv[0, 0, :POOL_RATIO, :] = np.float32(0.0)
    score_bits = codes32(scores).copy()
    score_bits[0, 0, :POOL_RATIO, :] = np.uint32(F32_NEGATIVE_INFINITY)
    return kv, score_bits.view(np.float32)


def test_compress_pool_matches_the_exact_reference():
    rng = np.random.default_rng(23)
    kv, scores = overlap_pool_operands(rng)
    build = Build()
    out = build.output_view((1, kv.shape[1], POOL_HEAD_DIM), DType.FP32)
    emit(
        build,
        Vector.COMPRESS,
        inputs=[
            build.input_view(kv, DType.FP32),
            build.input_view(scores, DType.FP32),
        ],
        outputs=[out],
        aux=[COMPRESS_POOL, POOL_RATIO],
    )
    device = build.finish()
    result = run(device)
    assert result.status == CompletionStatus.SUCCESS, result.message

    expected = compress_pool_f32(
        nested(codes32(kv)), nested(codes32(scores)), ratio=POOL_RATIO
    )
    assert np.array_equal(
        codes32(read(device, out)),
        np.asarray(expected.pooled_f32_codes, dtype=np.uint32),
    )
    assert result.counters["vector.compress_rows"] == kv.shape[1]


def test_compress_pool_refuses_a_pooling_axis_the_ratio_does_not_declare():
    rng = np.random.default_rng(24)
    kv = rng.uniform(-1.0, 1.0, size=(1, 1, 6, POOL_HEAD_DIM)).astype(np.float32)
    build = Build()
    emit(
        build,
        Vector.COMPRESS,
        inputs=[
            build.input_view(kv, DType.FP32),
            build.input_view(kv.copy(), DType.FP32),
        ],
        outputs=[build.output_view((1, 1, POOL_HEAD_DIM), DType.FP32)],
        aux=[COMPRESS_POOL, POOL_RATIO],
    )
    result = run(build.finish())
    assert result.status == CompletionStatus.FAILED
    assert result.trap_class == int(TrapClass.DESCRIPTOR_OR_ADDRESS)
    assert "pools 8 candidates" in result.message


# ---------------------------------------------------------------------------
# VECTOR.COMPRESS -- COMPRESS_STATE_UPDATE
# ---------------------------------------------------------------------------
def test_compress_state_update_matches_the_exact_reference():
    rng = np.random.default_rng(29)
    span = 2 * POOL_RATIO
    width = 2 * POOL_HEAD_DIM
    kv = rng.uniform(-2.0, 2.0, size=(1, span, width)).astype(np.float32)
    scores = rng.uniform(-2.0, 2.0, size=(1, span, width)).astype(np.float32)
    ape = rng.uniform(-1.0, 1.0, size=(POOL_RATIO, width)).astype(np.float32)
    projected = np.stack((kv, scores), axis=2)

    build = Build()
    groups = span // POOL_RATIO
    dims = (1, groups, POOL_AXIS, POOL_HEAD_DIM)
    kv_out = build.output_view(dims, DType.FP32)
    score_out = build.output_view(dims, DType.FP32)
    emit(
        build,
        Vector.COMPRESS,
        inputs=[
            build.input_view(projected, DType.FP32),
            NO_ID,
            build.input_view(ape, DType.FP32),
        ],
        outputs=[kv_out, score_out],
        aux=[COMPRESS_STATE_UPDATE, POOL_RATIO, int(Symbol.POSITION_START)],
    )
    device = build.finish()
    result = run(device, symbols={int(Symbol.POSITION_START): 0})
    assert result.status == CompletionStatus.SUCCESS, result.message

    state = zero_compression_state_f32(
        ratio=POOL_RATIO, batch_capacity=1, head_dim=POOL_HEAD_DIM
    )
    expected = compress_state_update_f32(
        state,
        nested(codes32(kv)),
        nested(codes32(scores)),
        nested(codes32(ape)),
        session_ids=["0" * 64],
        start_pos=0,
    )
    assert expected.should_compress
    assert expected.pool_inputs is not None
    assert np.array_equal(
        codes32(read(device, kv_out)),
        np.asarray(expected.pool_inputs.kv_f32_codes, dtype=np.uint32),
    )
    assert np.array_equal(
        codes32(read(device, score_out)),
        np.asarray(expected.pool_inputs.score_f32_codes, dtype=np.uint32),
    )


def test_compress_state_update_refuses_the_decode_phase():
    rng = np.random.default_rng(31)
    span = POOL_RATIO
    width = 2 * POOL_HEAD_DIM
    projected = rng.uniform(-1.0, 1.0, size=(1, span, 2, width)).astype(np.float32)
    ape = rng.uniform(-1.0, 1.0, size=(POOL_RATIO, width)).astype(np.float32)
    build = Build()
    dims = (1, 1, POOL_AXIS, POOL_HEAD_DIM)
    emit(
        build,
        Vector.COMPRESS,
        inputs=[
            build.input_view(projected, DType.FP32),
            NO_ID,
            build.input_view(ape, DType.FP32),
        ],
        outputs=[
            build.output_view(dims, DType.FP32),
            build.output_view(dims, DType.FP32),
        ],
        aux=[COMPRESS_STATE_UPDATE, POOL_RATIO, int(Symbol.POSITION_START)],
    )
    result = run(build.finish(), symbols={int(Symbol.POSITION_START): 8})
    assert result.status == CompletionStatus.FAILED
    assert result.trap_class == int(TrapClass.CAPABILITY_OR_RESOURCE)
    assert "decode path" in result.message


# ---------------------------------------------------------------------------
# VECTOR.INDEX_SCORE
# ---------------------------------------------------------------------------
def build_index_score(query, keys, weights, *, out_dims=None, scale=None):
    build = Build()
    batch, span, heads, _ = query.shape
    candidates = keys.shape[1]
    numeric = build.builder.numeric(
        contract="deepseek_v4_index_score_bf16_v1",
        input_dtype=DType.BF16,
        output_dtype=DType.BF16,
        scale_bits=INDEX_SCORE_SCALE_BINARY32 if scale is None else scale,
    )
    out = build.output_view(
        out_dims if out_dims is not None else (batch, span, candidates), DType.BF16
    )
    emit(
        build,
        Vector.INDEX_SCORE,
        inputs=[
            build.input_view(query, DType.BF16),
            build.input_view(keys, DType.BF16),
            build.input_view(weights, DType.BF16),
        ],
        outputs=[out],
        aux=[],
        numeric_profile_id=numeric,
    )
    return build, out


def test_index_score_matches_the_exact_reference():
    rng = np.random.default_rng(37)
    query = bf16_uniform(rng, (1, 2, 4, 8))
    keys = bf16_uniform(rng, (1, 5, 8))
    weights = bf16_uniform(rng, (1, 2, 4), scale=4.0)

    build, out = build_index_score(query, keys, weights)
    device = build.finish()
    result = run(device)
    assert result.status == CompletionStatus.SUCCESS, result.message

    expected = index_score_bf16(nested(query), nested(keys), nested(weights))
    produced = read(device, out)
    assert np.array_equal(produced, np.asarray(expected.values, dtype=np.uint16))
    # A vacuous all-zero comparison would prove nothing.
    assert int(np.count_nonzero(produced)) > 0


def test_index_score_uses_single_rounded_product_add():
    query = np.zeros((1, 1, 4, 2), dtype=np.uint16)
    query[0, 0, 0] = np.array([0x2A7E, 0x1B83], dtype=np.uint16)
    keys = np.array([[[0x17C0, 0x1A83]]], dtype=np.uint16)
    weights = np.zeros((1, 1, 4), dtype=np.uint16)
    weights[0, 0, 0] = 0x3F80

    build, out = build_index_score(
        query, keys, weights, scale=0x3F800000
    )
    device = build.finish()
    result = run(device)
    assert result.status == CompletionStatus.SUCCESS, result.message

    expected = index_score_bf16(
        nested(query), nested(keys), nested(weights), scale_binary32=0x3F800000
    )
    produced = read(device, out)
    assert np.array_equal(produced, np.asarray(expected.values, dtype=np.uint16))
    assert int(produced[0, 0, 0]) == 0x02BF


def test_index_score_publishes_every_saturation_boundary():
    cases = []

    scaled_query = np.zeros((1, 1, 4, 1), dtype=np.uint16)
    scaled_query[0, 0, 0, 0] = 0x3F80
    scaled_weights = np.zeros((1, 1, 4), dtype=np.uint16)
    scaled_weights[0, 0, 0] = 0x7F7F
    cases.append((
        scaled_query,
        np.array([[[0x3F80]]], dtype=np.uint16),
        scaled_weights,
        0x40000000,
    ))

    qk_query = np.zeros((1, 1, 4, 2), dtype=np.uint16)
    qk_query[0, 0, 0] = np.array([0x7F7F, 0x7B00], dtype=np.uint16)
    qk_weights = np.zeros((1, 1, 4), dtype=np.uint16)
    qk_weights[0, 0, 0] = 0x3F80
    cases.append((
        qk_query,
        np.array([[[0x3F80, 0x3F80]]], dtype=np.uint16),
        qk_weights,
        0x3F800000,
    ))

    weighted_query = np.zeros((1, 1, 4, 1), dtype=np.uint16)
    weighted_query[0, 0, 0, 0] = 0x7F7E
    weighted_weights = np.zeros((1, 1, 4), dtype=np.uint16)
    weighted_weights[0, 0, 0] = 0x3F81
    cases.append((
        weighted_query,
        np.array([[[0x3F80]]], dtype=np.uint16),
        weighted_weights,
        0x3F800000,
    ))

    output_query = np.zeros((1, 1, 4, 1), dtype=np.uint16)
    output_query[0, 0, 0, 0] = 0x7F7F
    output_query[0, 0, 1, 0] = 0x7B00
    output_weights = np.zeros((1, 1, 4), dtype=np.uint16)
    output_weights[0, 0, :2] = 0x3F80
    cases.append((
        output_query,
        np.array([[[0x3F80]]], dtype=np.uint16),
        output_weights,
        0x3F800000,
    ))

    for query, keys, weights, scale in cases:
        build, out = build_index_score(query, keys, weights, scale=scale)
        device = build.finish()
        completion = run(device)
        assert completion.status == CompletionStatus.SUCCESS, completion.message
        expected = index_score_bf16(
            nested(query),
            nested(keys),
            nested(weights),
            scale_binary32=scale,
        )
        expected_saturations = (
            expected.qk_saturated_element_count
            + expected.scaled_weight_saturated_element_count
            + expected.weighted_score_saturated_element_count
            + expected.output_saturated_element_count
        )
        assert expected_saturations == 1
        assert completion.counters["vector.saturations"] == expected_saturations
        assert np.array_equal(
            read(device, out), np.asarray(expected.values, dtype=np.uint16)
        )


def test_index_score_refuses_a_key_that_disagrees_with_the_query():
    rng = np.random.default_rng(41)
    query = bf16_uniform(rng, (1, 2, 4, 8))
    keys = bf16_uniform(rng, (1, 5, 6))
    weights = bf16_uniform(rng, (1, 2, 4))
    build, _ = build_index_score(query, keys, weights, out_dims=(1, 2, 5))
    result = run(build.finish())
    assert result.status == CompletionStatus.FAILED
    assert result.trap_class == int(TrapClass.DESCRIPTOR_OR_ADDRESS)
    assert "head dimension" in result.message


# ---------------------------------------------------------------------------
# VECTOR.MHC -- HYPER_CONNECT_POST
# ---------------------------------------------------------------------------
def test_mhc_post_matches_the_exact_reference():
    rng = np.random.default_rng(43)
    batch, span, hidden = 1, 2, 6
    multiplier = HC_MULTIPLIER
    branch = bf16_uniform(rng, (batch, span, hidden))
    residual = bf16_uniform(rng, (batch, span, multiplier, hidden))
    post = rng.uniform(0.0, 2.0, size=(batch, span, multiplier)).astype(np.float32)
    comb = rng.uniform(0.0, 1.0, size=(batch, span, multiplier, multiplier)).astype(
        np.float32
    )

    build = Build()
    out = build.output_view((batch, span, multiplier, hidden), DType.BF16)
    emit(
        build,
        Vector.MHC,
        inputs=[
            build.input_view(branch, DType.BF16),
            build.input_view(residual, DType.BF16),
            build.input_view(post, DType.FP32),
            build.input_view(comb, DType.FP32),
        ],
        outputs=[out],
        aux=[HC_POST, NO_ID, multiplier],
    )
    device = build.finish()
    result = run(device)
    assert result.status == CompletionStatus.SUCCESS, result.message

    expected = hc_post_bf16(
        nested(branch),
        nested(residual),
        nested(codes32(post)),
        nested(codes32(comb)),
        hc_multiplier=multiplier,
    )
    produced = read(device, out)
    assert np.array_equal(produced, np.asarray(expected.output_codes, dtype=np.uint16))
    assert int(np.count_nonzero(produced)) > 0
    assert result.counters["vector.mhc_sites"] == batch * span


def test_mhc_post_publishes_output_saturation():
    branch = np.array([[[0x7F7F]]], dtype=np.uint16)
    residual = np.zeros((1, 1, HC_MULTIPLIER, 1), dtype=np.uint16)
    post = np.array(
        [[[0x3F808000, 0, 0, 0]]], dtype=np.uint32
    ).view(np.float32)
    comb = np.zeros(
        (1, 1, HC_MULTIPLIER, HC_MULTIPLIER), dtype=np.float32
    )
    build = Build()
    out = build.output_view((1, 1, HC_MULTIPLIER, 1), DType.BF16)
    emit(
        build,
        Vector.MHC,
        inputs=[
            build.input_view(branch, DType.BF16),
            build.input_view(residual, DType.BF16),
            build.input_view(post, DType.FP32),
            build.input_view(comb, DType.FP32),
        ],
        outputs=[out],
        aux=[HC_POST, NO_ID, HC_MULTIPLIER],
    )
    device = build.finish()
    completion = run(device)
    assert completion.status == CompletionStatus.SUCCESS, completion.message
    expected = hc_post_bf16(
        nested(branch),
        nested(residual),
        nested(codes32(post)),
        nested(codes32(comb)),
        hc_multiplier=HC_MULTIPLIER,
    )
    assert expected.output_saturation_count == 1
    assert completion.counters["vector.saturations"] == 1
    assert np.array_equal(
        read(device, out), np.asarray(expected.output_codes, dtype=np.uint16)
    )


def test_mhc_post_refuses_a_residual_that_disagrees_with_the_branch():
    rng = np.random.default_rng(47)
    branch = bf16_uniform(rng, (1, 2, 6))
    residual = bf16_uniform(rng, (1, 2, HC_MULTIPLIER, 5))
    post = rng.uniform(0.0, 1.0, size=(1, 2, HC_MULTIPLIER)).astype(np.float32)
    comb = rng.uniform(0.0, 1.0, size=(1, 2, HC_MULTIPLIER, HC_MULTIPLIER)).astype(
        np.float32
    )
    build = Build()
    emit(
        build,
        Vector.MHC,
        inputs=[
            build.input_view(branch, DType.BF16),
            build.input_view(residual, DType.BF16),
            build.input_view(post, DType.FP32),
            build.input_view(comb, DType.FP32),
        ],
        outputs=[build.output_view((1, 2, HC_MULTIPLIER, 5), DType.BF16)],
        aux=[HC_POST, NO_ID, HC_MULTIPLIER],
    )
    result = run(build.finish())
    assert result.status == CompletionStatus.FAILED
    assert result.trap_class == int(TrapClass.DESCRIPTOR_OR_ADDRESS)
    assert "the branch declares" in result.message


# ---------------------------------------------------------------------------
# VECTOR.MHC -- HYPER_CONNECT_PRE and HYPER_CONNECT_HEAD
# ---------------------------------------------------------------------------
def frozen_hc_operands(seed: int, rows: int, *, active: int = 6):
    """One sparse token at the frozen ``[T, 4, 4096]`` hyper-connection profile.

    The frozen reference refuses any other shape, and a dense 24x16,384 exact
    rational projection is not a unit-test-sized computation.  Sparsity is not a
    weakening of the case: the reference skips zero inputs and zero weights
    because adding an exact zero product cannot change the accumulator, so this
    exercises the same arithmetic on fewer terms.
    """
    rng = np.random.default_rng(seed)
    columns = rng.choice(HIDDEN_SIZE, size=active, replace=False)
    hidden = np.zeros((1, HC_MULTIPLIER, HIDDEN_SIZE), dtype=np.uint16)
    for stream in range(HC_MULTIPLIER):
        hidden[0, stream, columns] = bf16_uniform(rng, (active,), scale=2.0)
    projection = np.zeros((rows, FLATTENED_WIDTH), dtype=np.float32)
    for stream in range(HC_MULTIPLIER):
        offset = stream * HIDDEN_SIZE
        projection[:, offset + columns] = rng.uniform(
            -0.25, 0.25, size=(rows, active)
        ).astype(np.float32)
    return hidden, projection


def test_mhc_pre_matches_the_exact_reference_at_the_frozen_profile():
    rng = np.random.default_rng(53)
    hidden, projection = frozen_hc_operands(53, MIX_PARAMETER_COUNT)
    scale = np.array([0.25, 0.5, 0.75], dtype=np.float32)
    base = rng.uniform(-0.5, 0.5, size=MIX_PARAMETER_COUNT).astype(np.float32)

    build = Build()
    numeric = build.builder.numeric(
        contract="opentallas.deepseek_v4_hc_pre_numeric.v1",
        input_dtype=DType.BF16,
        output_dtype=DType.FP32,
        reduction_order=ReductionOrder.PAIRWISE_TREE,
        epsilon_bits=NORMALIZATION_EPSILON_BINARY32,
    )
    weight_out = build.output_view((1, 2, HC_MULTIPLIER), DType.FP32)
    comb_out = build.output_view((1, HC_MULTIPLIER, HC_MULTIPLIER), DType.FP32)
    emit(
        build,
        Vector.MHC,
        inputs=[
            build.input_view(hidden, DType.BF16),
            build.input_view(projection, DType.FP32),
            build.input_view(base, DType.FP32),
            build.input_view(scale, DType.FP32),
        ],
        outputs=[weight_out, comb_out],
        aux=[HC_PRE, SINKHORN_ITERATIONS, HC_MULTIPLIER],
        numeric_profile_id=numeric,
    )
    device = build.finish()
    result = run(device)
    assert result.status == CompletionStatus.SUCCESS, result.message

    expected = hc_pre_bf16(
        nested(hidden),
        nested(codes32(projection)),
        nested(codes32(scale)),
        nested(codes32(base)),
    )
    weights = codes32(read(device, weight_out))
    assert np.array_equal(
        weights[:, 0, :], np.asarray(expected.pre_binary32_codes, dtype=np.uint32)
    )
    assert np.array_equal(
        weights[:, 1, :], np.asarray(expected.post_binary32_codes, dtype=np.uint32)
    )
    comb = read(device, comb_out)
    assert np.array_equal(
        codes32(comb), np.asarray(expected.comb_binary32_codes, dtype=np.uint32)
    )
    # Not a vacuous comparison: the coefficients are distinct and the Sinkhorn
    # matrix is a real doubly normalised matrix, not an identity or a constant.
    assert len(set(weights.reshape(-1).tolist())) == 2 * HC_MULTIPLIER
    assert float(comb.min()) > 0.0 and float(comb.max()) < 1.0 + 1e-3
    assert len(set(comb.reshape(-1).tolist())) > HC_MULTIPLIER
    assert result.counters["vector.mhc_sites"] == 1


def test_mhc_head_matches_the_exact_reference_at_the_frozen_profile():
    rng = np.random.default_rng(59)
    hidden, projection = frozen_hc_operands(59, HC_MULTIPLIER)
    scale = np.array([0.5], dtype=np.float32)
    base = rng.uniform(-0.5, 0.5, size=HC_MULTIPLIER).astype(np.float32)

    build = Build()
    numeric = build.builder.numeric(
        contract="opentallas.deepseek_v4_hc_pre_numeric.v1",
        input_dtype=DType.BF16,
        output_dtype=DType.BF16,
        reduction_order=ReductionOrder.PAIRWISE_TREE,
        epsilon_bits=NORMALIZATION_EPSILON_BINARY32,
    )
    out = build.output_view((1, HIDDEN_SIZE), DType.BF16)
    emit(
        build,
        Vector.MHC,
        inputs=[
            build.input_view(hidden, DType.BF16),
            build.input_view(projection, DType.FP32),
            build.input_view(base, DType.FP32),
            build.input_view(scale, DType.FP32),
        ],
        outputs=[out],
        aux=[HC_HEAD, NO_ID, HC_MULTIPLIER],
        numeric_profile_id=numeric,
    )
    device = build.finish()
    result = run(device)
    assert result.status == CompletionStatus.SUCCESS, result.message

    expected = hc_head_bf16(
        nested(hidden),
        nested(codes32(projection)),
        nested(codes32(scale)),
        nested(codes32(base)),
    )
    produced = read(device, out)
    assert np.array_equal(
        produced, np.asarray(expected.output_bf16_codes, dtype=np.uint16)
    )
    assert int(np.count_nonzero(produced)) > 0


def test_mhc_refuses_an_epsilon_the_frozen_contract_does_not_declare():
    rng = np.random.default_rng(61)
    hidden = bf16_uniform(rng, (1, HC_MULTIPLIER, 8))
    projection = rng.uniform(-1.0, 1.0, size=(HC_MULTIPLIER, HC_MULTIPLIER * 8)).astype(
        np.float32
    )
    scale = np.array([0.5], dtype=np.float32)
    base = rng.uniform(-0.5, 0.5, size=HC_MULTIPLIER).astype(np.float32)
    build = Build()
    numeric = build.builder.numeric(
        contract="opentallas.deepseek_v4_hc_pre_numeric.v1",
        input_dtype=DType.BF16,
        output_dtype=DType.BF16,
        reduction_order=ReductionOrder.PAIRWISE_TREE,
        epsilon_bits=0x34000000,
    )
    emit(
        build,
        Vector.MHC,
        inputs=[
            build.input_view(hidden, DType.BF16),
            build.input_view(projection, DType.FP32),
            build.input_view(base, DType.FP32),
            build.input_view(scale, DType.FP32),
        ],
        outputs=[build.output_view((1, 8), DType.BF16)],
        aux=[HC_HEAD, NO_ID, HC_MULTIPLIER],
        numeric_profile_id=numeric,
    )
    result = run(build.finish())
    assert result.status == CompletionStatus.FAILED
    assert result.trap_class == int(TrapClass.NUMERIC_OR_EXCEPTIONAL_VALUE)
    assert "fixes it at" in result.message


def test_mhc_refuses_an_hc_mult_that_contradicts_the_operands():
    rng = np.random.default_rng(67)
    hidden = bf16_uniform(rng, (1, HC_MULTIPLIER, 8))
    projection = rng.uniform(-1.0, 1.0, size=(HC_MULTIPLIER, HC_MULTIPLIER * 8)).astype(
        np.float32
    )
    scale = np.array([0.5], dtype=np.float32)
    base = rng.uniform(-0.5, 0.5, size=HC_MULTIPLIER).astype(np.float32)
    build = Build()
    numeric = build.builder.numeric(
        contract="opentallas.deepseek_v4_hc_pre_numeric.v1",
        input_dtype=DType.BF16,
        output_dtype=DType.BF16,
        reduction_order=ReductionOrder.PAIRWISE_TREE,
        epsilon_bits=NORMALIZATION_EPSILON_BINARY32,
    )
    emit(
        build,
        Vector.MHC,
        inputs=[
            build.input_view(hidden, DType.BF16),
            build.input_view(projection, DType.FP32),
            build.input_view(base, DType.FP32),
            build.input_view(scale, DType.FP32),
        ],
        outputs=[build.output_view((1, 8), DType.BF16)],
        aux=[HC_HEAD, NO_ID, HC_MULTIPLIER + 1],
        numeric_profile_id=numeric,
    )
    result = run(build.finish())
    assert result.status == CompletionStatus.FAILED
    assert result.trap_class == int(TrapClass.DESCRIPTOR_OR_ADDRESS)
    assert "hc_mult" in result.message


# ---------------------------------------------------------------------------
# The compressor-pool exponential
# ---------------------------------------------------------------------------
# ``_pool`` evaluates ``CR32(exp(x))`` once per pooled lane.  Reaching that
# through ``runtime.reference.transcendental.binary32_exp_general_rne`` one
# ``fractions.Fraction`` scalar at a time is the same defect OI-41 names in
# ``ATTENTION.SPARSE``, and it is 6.7 % of a DeepSeek prefill.  The engine now
# reaches it through ``exp_cr32``, which is the *same function* computed
# differently: a binary64 candidate, a two-sided perturbation that proves which
# binary32 it rounds to, and a referral to the exact reference for anything the
# proof does not settle.
#
# These two tests are what make that takeable: the vectorised form agrees with
# the scalar reference across the domain a pooling delta can hold, and the one
# input where the two disagree -- a non-finite delta, which the reference
# refuses and the vectorised form would answer -- still goes to the reference.
def test_the_pool_exponential_agrees_with_the_scalar_reference():
    """Same value as ``binary32_exp_general_rne``, over the pooling domain.

    A pooling delta is ``score - max(score)``, so it is non-positive.  The
    sweep covers every binary32 exponent field on that side of zero, a dense
    band through the magnitudes a softmax actually forms, and the underflow
    edge near -103.97 where the exponential leaves the binary32 range.
    """
    from runtime.reference.transcendental import binary32_exp_general_rne
    from runtime.sim.engines.deepseek_vector import _exponentials

    rng = np.random.default_rng(0x4558)
    sampled = [np.uint32(0x80000000), np.uint32(0x00000000)]
    for exponent in range(0, 255):
        significands = rng.integers(0, 1 << 23, 24, dtype=np.uint32)
        significands[0] = 0
        significands[1] = (1 << 23) - 1
        sampled.append(
            (np.uint32(1) << 31) | (np.uint32(exponent) << 23) | significands
        )
    for exponent in range(100, 134):  # 2**-27 .. 2**7, where the softmax lives
        sampled.append(
            (np.uint32(1) << 31)
            | (np.uint32(exponent) << 23)
            | np.arange(0, 1 << 23, 1 << 16, dtype=np.uint32)
        )
    codes = np.unique(np.concatenate([np.atleast_1d(part) for part in sampled]))
    values = codes.astype(np.uint32).view(np.float32)
    values = np.ascontiguousarray(values[np.isfinite(values) & (values <= 0)])

    observed = np.ascontiguousarray(_exponentials(values)).view(np.uint32)
    source = values.view(np.uint32)
    compared = 0
    for index in range(values.size):
        assert int(observed[index]) == binary32_exp_general_rne(int(source[index])), (
            float(values[index]),
            hex(int(observed[index])),
        )
        compared += 1
    assert compared > 5000, compared


def test_a_non_finite_pool_delta_still_reaches_the_exact_reference():
    """The vectorised exponential answers ``exp(-inf) = 0``; the reference refuses.

    A non-finite delta cannot come from a well-formed operand, so rather than
    decide what it means the engine keeps sending it to the scalar path -- the
    one that raised on it before.  Without that guard the fast path would
    silently accept an operand the contract rejects.
    """
    from runtime.reference.transcendental import TranscendentalReferenceError
    from runtime.sim.engines.deepseek_vector import _exponentials
    from runtime.tensor_accelerator.sparse_attention import exp_cr32

    delta = np.asarray([-np.inf, np.float32(-1.0)], dtype=np.float32)
    assert float(exp_cr32(delta)[0]) == 0.0
    try:
        _exponentials(delta)
    except Exception as exc:  # the reference's own refusal, whatever it spells
        assert isinstance(exc, TranscendentalReferenceError), exc
    else:  # pragma: no cover - a silent acceptance is the defect
        raise AssertionError("a non-finite pool delta was accepted")
