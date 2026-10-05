"""Conformance tests for the ABI 3.0 TENSOR and VECTOR engines.

Every numeric assertion compares the engine against an *independent* oracle:
either the exact ``fractions.Fraction`` scalar semantics in
``runtime/reference`` -- which decode, multiply and round without any host
floating-point mode -- or a straightforward NumPy computation that does not
share code with the engine.  Counter assertions check the frozen registry names
the engines are allowed to use.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Sequence

import numpy as np
import pytest

import runtime.sim.engines.tensor as tensor_engine  # noqa: F401  (registers)
import runtime.sim.engines.vector as vector_engine  # noqa: F401  (registers)
from runtime.abi3.builder import DeploymentBuilder
from runtime.abi3.constants import (
    NO_ID,
    Control,
    DType,
    Feature,
    Major,
    Permission,
    ReductionOrder,
    RoundingMode,
    StorageClass,
    Tensor,
    TopologyClass,
    Vector,
)
from runtime.abi3.deployment import Deployment, ObjectSource, Segment
from runtime.abi3.descriptors import LayoutClass, Phase, Symbol
from runtime.abi3.fixture import fixture_capability
from runtime.reference import formats as exact
from runtime.reference.hadamard import HADAMARD_WIDTH, hadamard_rotate_128_bf16
from runtime.reference.normalization import (
    HEAD_RMS_NORM_EPSILON_BF16,
    HEAD_RMS_NORM_WIDTH,
    head_rms_norm_bf16,
)
from runtime.reference.tensor_accelerator_rmsnorm import (
    EPSILON_CODE as QWEN_RMS_EPSILON_CODE,
    rms_norm_bf16 as exact_rms_norm,
)
from runtime.reference.tensor_accelerator_rope import rope_bf16 as exact_rope
from runtime.reference.sqrt_softplus import binary32_sqrt_softplus_rne
from runtime.reference.tensor_accelerator_elementwise import (
    bf16_add_rne as exact_bf16_add,
    qwen3_silu_mul_bf16 as exact_silu_mul,
)
from runtime.sim.counters import CounterSet
from runtime.sim.backend import CONTRACT_BLOCKED, get_backend
from runtime.sim.device import Device
from runtime.sim.engine import EngineContext, EngineError, dispatch
from runtime.sim.formats import narrow_bf16_rne, widen_bf16
from runtime.sim.memory import DeviceMemory, ViewResolver
from runtime.sim.performance import HostPerformanceObservations
from runtime.sim.weight_cache import DecodedWeightCache

READ = int(Permission.READ)
IMMUTABLE = int(Permission.READ | Permission.IMMUTABLE)
READ_WRITE = int(Permission.READ | Permission.WRITE)


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------
@dataclass
class Harness:
    """A minimal deployment plus the engine context that executes it."""

    root: Path
    builder: DeploymentBuilder
    files: int = 0
    memory: Any = None
    ctx: Any = None
    outputs: dict[int, tuple[int, tuple[int, ...], np.dtype]] = field(
        default_factory=dict
    )
    #: Output views whose storage packs two elements per byte.
    packed_outputs: set[int] = field(default_factory=set)

    @classmethod
    def create(cls, root: Path) -> "Harness":
        capability = fixture_capability()
        builder = DeploymentBuilder(
            target_id="engine-test",
            model_id="engine-test",
            backend="test",
            capability=capability,
        )
        builder.topology(topology_class=TopologyClass.SINGLE_CHIP, node_count=1)
        return cls(root=root, builder=builder)

    # -- objects ---------------------------------------------------------
    def constant(
        self,
        payload: bytes,
        storage_class: StorageClass = StorageClass.HBM,
        *,
        authenticated: bool = False,
    ) -> int:
        self.files += 1
        name = f"object{self.files}.bin"
        (self.root / name).write_bytes(payload)
        segment = Segment(
            name,
            0,
            len(payload),
            hashlib.sha256(payload).hexdigest() if authenticated else None,
        )
        source = ObjectSource("segments", len(payload), (segment,))
        return self.builder.memory_object(
            storage_class=storage_class,
            size_bytes=len(payload),
            source=source,
            permissions=IMMUTABLE,
            content_digest=(
                source.authenticated_content_digest()
                if authenticated
                else bytes(32)
            ),
        )

    def scratch(
        self, size_bytes: int, storage_class: StorageClass = StorageClass.SRAM
    ) -> int:
        return self.builder.memory_object(
            storage_class=storage_class,
            size_bytes=size_bytes,
            source=ObjectSource.zeros(size_bytes),
            permissions=READ_WRITE,
        )

    # -- views -----------------------------------------------------------
    def const_view(
        self,
        array: np.ndarray,
        dtype: DType,
        *,
        dims: Sequence[int] | None = None,
        storage_class: StorageClass = StorageClass.HBM,
        scale_object_id: int = NO_ID,
        scale_block_elements: int = 0,
        scale_block_rows: int = 0,
        authenticated: bool = False,
    ) -> int:
        payload = np.ascontiguousarray(array).tobytes()
        object_id = self.constant(
            payload, storage_class, authenticated=authenticated
        )
        return self.builder.tensor_view(
            object_id=object_id,
            dtype=dtype,
            dims=list(dims if dims is not None else array.shape),
            permissions=READ,
            layout_class=(
                LayoutClass.BLOCK_SCALED
                if scale_object_id != NO_ID
                else LayoutClass.DENSE
            ),
            scale_object_id=scale_object_id,
            scale_block_elements=scale_block_elements,
            scale_block_rows=scale_block_rows,
        )

    def output_view(
        self,
        dims: Sequence[int],
        dtype: DType,
        *,
        storage_class: StorageClass = StorageClass.SRAM,
    ) -> int:
        numpy_dtype = {
            DType.BF16: np.dtype(np.uint16),
            DType.FP32: np.dtype(np.float32),
            DType.U32: np.dtype(np.uint32),
            DType.U8: np.dtype(np.uint8),
            DType.E8M0_SCALE: np.dtype(np.uint8),
            DType.FP8_E4M3FN: np.dtype(np.uint8),
            DType.MXFP4_E2M1: np.dtype(np.uint8),
        }[dtype]
        count = int(np.prod(dims))
        # A 4-bit view packs two elements per byte, so its object is half the
        # size its element count would suggest.
        packed = dtype == DType.MXFP4_E2M1
        object_id = self.scratch(
            count // 2 if packed else count * numpy_dtype.itemsize, storage_class
        )
        view = self.builder.tensor_view(
            object_id=object_id,
            dtype=dtype,
            dims=list(dims),
            permissions=READ_WRITE,
        )
        self.outputs[view] = (object_id, tuple(int(d) for d in dims), numpy_dtype)
        if packed:
            self.packed_outputs.add(view)
        return view

    def numeric(self, **kwargs: Any) -> int:
        kwargs.setdefault("contract", "engine-test")
        return self.builder.numeric(**kwargs)

    def operator(self, **kwargs: Any) -> int:
        # The verifier requires every engine operator to carry a tile mapping,
        # since a deployment without one cannot be timed. These unit harnesses
        # do not care about the schedule's contents, so a default one is
        # supplied per engine family rather than repeated at every call site.
        if kwargs.get("schedule_id") in (None, NO_ID):
            family = kwargs["engine_family"]
            cached = getattr(self, "_default_schedules", None)
            if cached is None:
                cached = {}
                self._default_schedules = cached
            schedule = cached.get(int(family))
            if schedule is None:
                schedule = self.builder.schedule(
                    engine_family=family,
                    tile_rows=1,
                    tile_cols=1,
                    tile_depth=1,
                    bank_mask=0b1,
                    max_outstanding=1,
                )
                cached[int(family)] = schedule
            kwargs["schedule_id"] = schedule
        return self.builder.operator(**kwargs)

    # -- execution -------------------------------------------------------
    def bind(self) -> "Harness":
        deployment = Deployment(
            deployment_id=1,
            generation=1,
            target_id="engine-test",
            model_id="engine-test",
            backend="test",
            topology_class=int(TopologyClass.SINGLE_CHIP),
            capability_digest="",
            table=self.builder.table,
            program=b"",
            objects=dict(self.builder.objects),
            entrypoints=(),
            required_features=bytes(32),
            root=self.root,
        )
        self.memory = DeviceMemory(deployment, root=self.root)
        self.ctx = EngineContext(
            table=deployment.table,
            memory=self.memory,
            views=ViewResolver(deployment, self.memory),
            counters=CounterSet(),
            loops={},
            symbols={},
        )
        return self

    def run(self, family: Major, sub: int, operator_id: int) -> None:
        if self.ctx is None:
            self.bind()
        dispatch(self.ctx, int(family), int(sub), self.builder.table[operator_id])

    def result(self, view_id: int) -> np.ndarray:
        object_id, dims, numpy_dtype = self.outputs[view_id]
        count = int(np.prod(dims))
        if view_id in self.packed_outputs:
            # Unpack a 4-bit result low nibble first, which is the order
            # ``ViewResolver._read_sub_byte`` reads and ``_write_sub_byte``
            # writes.
            payload = self.memory[object_id].read(0, count // 2)
            packed = np.frombuffer(payload, dtype=np.uint8)
            nibbles = np.empty(count, dtype=np.uint8)
            nibbles[0::2] = packed & 0x0F
            nibbles[1::2] = packed >> 4
            return nibbles.reshape(dims)
        payload = self.memory[object_id].read(0, count * numpy_dtype.itemsize)
        return np.frombuffer(payload, dtype=numpy_dtype).reshape(dims)

    @property
    def counters(self) -> CounterSet:
        return self.ctx.counters


@pytest.fixture()
def harness(tmp_path: Path) -> Harness:
    return Harness.create(tmp_path)


# ---------------------------------------------------------------------------
# Data helpers and independent oracles
# ---------------------------------------------------------------------------
def bf16(values: np.ndarray) -> np.ndarray:
    codes, _ = narrow_bf16_rne(np.asarray(values, dtype=np.float32))
    return codes


def random_bf16(rng: np.random.Generator, shape: Sequence[int], scale: float = 1.0):
    return bf16(rng.standard_normal(tuple(shape)).astype(np.float32) * np.float32(scale))


def exact_value(code: int) -> Any:
    decoded = exact.decode_bf16(int(code))
    assert decoded.value is not None
    return decoded.value


def oracle_matmul(activations: np.ndarray, weights: np.ndarray) -> np.ndarray:
    """``[M,K] @ [N,K]^T`` under the exact scalar contract."""
    rows, _ = activations.shape
    cols, _ = weights.shape
    output = np.empty((rows, cols), dtype=np.uint16)
    for row in range(rows):
        left = [exact_value(code) for code in activations[row]]
        for col in range(cols):
            right = [exact_value(code) for code in weights[col]]
            accumulator = exact.binary32_ordered_dot(left, right)
            output[row, col] = exact.binary32_bits_to_bf16_rne(accumulator).code
    return output


def oracle_scaled_matmul(
    activations: np.ndarray, weight_values: Sequence[Sequence[Any]]
) -> np.ndarray:
    """Exact contraction of BF16 activations against exact weight values."""
    rows = activations.shape[0]
    cols = len(weight_values)
    output = np.empty((rows, cols), dtype=np.uint16)
    for row in range(rows):
        left = [exact_value(code) for code in activations[row]]
        for col in range(cols):
            accumulator = exact.binary32_ordered_dot(left, weight_values[col])
            output[row, col] = exact.binary32_bits_to_bf16_rne(accumulator).code
    return output


def matmul_numeric(harness: Harness, **overrides: Any) -> int:
    options: dict[str, Any] = {
        "contract": "bf16_bf16_fp32_sequential_rne_v1",
        "input_dtype": DType.BF16,
        "second_input_dtype": DType.BF16,
        "output_dtype": DType.BF16,
        "accumulator_dtype": DType.FP32,
    }
    options.update(overrides)
    return harness.builder.numeric(**options)


# ---------------------------------------------------------------------------
# TENSOR.MATMUL
# ---------------------------------------------------------------------------
def test_matmul_bf16_matches_exact_oracle(harness: Harness) -> None:
    rng = np.random.default_rng(7)
    activations = random_bf16(rng, (3, 8))
    weights = random_bf16(rng, (5, 8))
    numeric = matmul_numeric(harness)
    output = harness.output_view((3, 5), DType.BF16)
    operator = harness.operator(
        engine_family=Major.TENSOR,
        engine_sub=Tensor.MATMUL,
        inputs=[
            harness.const_view(activations, DType.BF16, storage_class=StorageClass.SRAM),
            harness.const_view(weights, DType.BF16, storage_class=StorageClass.ROM),
        ],
        outputs=[output],
        numeric_profile_id=numeric,
    )
    harness.run(Major.TENSOR, Tensor.MATMUL, operator)

    np.testing.assert_array_equal(
        harness.result(output), oracle_matmul(activations, weights)
    )
    counters = harness.counters
    assert counters["tensor.multiplications"] == 3 * 5 * 8
    assert counters["tensor.additions"] == 3 * 5 * 7
    assert counters["tensor.output_elements"] == 15
    assert counters["tensor.conversions"] == 15
    assert counters["rom.bytes_read"] == 5 * 8 * 2
    assert counters["sram.bytes_read"] == 3 * 8 * 2
    assert counters["sram.bytes_written"] == 15 * 2


def test_matmul_fp32_output_is_the_raw_accumulator(harness: Harness) -> None:
    rng = np.random.default_rng(11)
    activations = random_bf16(rng, (2, 16))
    weights = random_bf16(rng, (3, 16))
    numeric = matmul_numeric(harness, output_dtype=DType.FP32)
    output = harness.output_view((2, 3), DType.FP32)
    operator = harness.operator(
        engine_family=Major.TENSOR,
        engine_sub=Tensor.MATMUL,
        inputs=[
            harness.const_view(activations, DType.BF16),
            harness.const_view(weights, DType.BF16),
        ],
        outputs=[output],
        numeric_profile_id=numeric,
    )
    harness.run(Major.TENSOR, Tensor.MATMUL, operator)

    produced = harness.result(output)
    for row in range(2):
        left = [exact_value(code) for code in activations[row]]
        for col in range(3):
            right = [exact_value(code) for code in weights[col]]
            expected = exact.binary32_ordered_dot(left, right)
            assert int(produced[row, col].view(np.uint32)) == expected
    # A binary32 output crosses no format boundary.
    assert harness.counters["tensor.conversions"] == 0


def test_matmul_fp8_weights_use_their_block_scales(harness: Harness) -> None:
    rng = np.random.default_rng(3)
    depth, cols, rows, block = 32, 4, 2, 16
    activations = random_bf16(rng, (rows, depth), scale=0.5)
    weight_codes = rng.integers(0, 0x7E, size=(cols, depth), dtype=np.uint8)
    scale_codes = rng.integers(120, 130, size=(cols, depth // block), dtype=np.uint8)

    scale_object = harness.constant(scale_codes.tobytes())
    weight_view = harness.const_view(
        weight_codes,
        DType.FP8_E4M3FN,
        scale_object_id=scale_object,
        scale_block_elements=block,
    )
    numeric = matmul_numeric(harness, second_input_dtype=DType.FP8_E4M3FN)
    output = harness.output_view((rows, cols), DType.BF16)
    operator = harness.operator(
        engine_family=Major.TENSOR,
        engine_sub=Tensor.MATMUL,
        inputs=[harness.const_view(activations, DType.BF16), weight_view],
        outputs=[output],
        numeric_profile_id=numeric,
    )
    harness.run(Major.TENSOR, Tensor.MATMUL, operator)

    expected_weights = []
    for col in range(cols):
        row_values = []
        for index in range(depth):
            value = exact.decode_e4m3fn(int(weight_codes[col, index]))
            scale = exact.decode_e8m0(int(scale_codes[col, index // block]))
            assert value.value is not None and scale.value is not None
            row_values.append(value.value * scale.value)
        expected_weights.append(row_values)
    np.testing.assert_array_equal(
        harness.result(output), oracle_scaled_matmul(activations, expected_weights)
    )
    # Every scaled weight element costs one extra multiplication.
    assert harness.counters["tensor.multiplications"] == rows * cols * depth + cols * depth


def test_matmul_fp8_weights_use_a_two_dimensional_block_scale(harness: Harness) -> None:
    """Amendment A15: one scale code may cover a tile, not only a run.

    The released DeepSeek FP8 weights are scaled in 128 x 128 tiles --
    ``layers.0.attn.wq_a`` is ``[1024, 4096]`` with a 128-element block and
    ships 256 codes shaped ``[8, 32]`` -- which amendment A8's one-dimensional
    rule cannot address at all.  Here the same shape is checked at a size a
    test can enumerate: four output columns in two row blocks of two, and a
    scale of ``[2, 2]`` against a ``[4, 32]`` weight.
    """
    rng = np.random.default_rng(11)
    depth, cols, rows, block, row_block = 32, 4, 2, 16, 2
    activations = random_bf16(rng, (rows, depth), scale=0.5)
    weight_codes = rng.integers(0, 0x7E, size=(cols, depth), dtype=np.uint8)
    scale_codes = rng.integers(120, 130, size=(cols // row_block, depth // block),
                               dtype=np.uint8)

    scale_object = harness.constant(scale_codes.tobytes())
    weight_view = harness.const_view(
        weight_codes,
        DType.FP8_E4M3FN,
        scale_object_id=scale_object,
        scale_block_elements=block,
        scale_block_rows=row_block,
    )
    numeric = matmul_numeric(harness, second_input_dtype=DType.FP8_E4M3FN)
    output = harness.output_view((rows, cols), DType.BF16)
    operator = harness.operator(
        engine_family=Major.TENSOR,
        engine_sub=Tensor.MATMUL,
        inputs=[harness.const_view(activations, DType.BF16), weight_view],
        outputs=[output],
        numeric_profile_id=numeric,
    )
    harness.run(Major.TENSOR, Tensor.MATMUL, operator)

    expected_weights = []
    for col in range(cols):
        row_values = []
        for index in range(depth):
            value = exact.decode_e4m3fn(int(weight_codes[col, index]))
            scale = exact.decode_e8m0(
                int(scale_codes[col // row_block, index // block])
            )
            assert value.value is not None and scale.value is not None
            row_values.append(value.value * scale.value)
        expected_weights.append(row_values)
    np.testing.assert_array_equal(
        harness.result(output), oracle_scaled_matmul(activations, expected_weights)
    )


def test_a_unit_row_block_is_amendment_a8_exactly(harness: Harness) -> None:
    """A15 with ``scale_block_rows`` of one, and of zero, is A8's own rule.

    Zero is what every view written before the amendment carries, because the
    field's bytes were reserved and reserved bytes must be zero.  A15 defines
    zero to mean one, so all three spellings must produce the same numbers from
    the same codes -- otherwise every existing program would change meaning.
    """
    rng = np.random.default_rng(13)
    depth, cols, rows, block = 32, 4, 2, 16
    activations = random_bf16(rng, (rows, depth), scale=0.5)
    weight_codes = rng.integers(0, 0x7E, size=(cols, depth), dtype=np.uint8)
    scale_codes = rng.integers(120, 130, size=(cols, depth // block), dtype=np.uint8)
    numeric = matmul_numeric(harness, second_input_dtype=DType.FP8_E4M3FN)

    scale_object = harness.constant(scale_codes.tobytes())
    activation_view = harness.const_view(activations, DType.BF16)
    built = []
    for row_block in (0, 1):
        output = harness.output_view((rows, cols), DType.BF16)
        built.append(
            (
                output,
                harness.operator(
                    engine_family=Major.TENSOR,
                    engine_sub=Tensor.MATMUL,
                    inputs=[
                        activation_view,
                        harness.const_view(
                            weight_codes,
                            DType.FP8_E4M3FN,
                            scale_object_id=scale_object,
                            scale_block_elements=block,
                            scale_block_rows=row_block,
                        ),
                    ],
                    outputs=[output],
                    numeric_profile_id=numeric,
                ),
            )
        )
    results = []
    for output, operator in built:
        harness.run(Major.TENSOR, Tensor.MATMUL, operator)
        results.append(harness.result(output))
    np.testing.assert_array_equal(results[0], results[1])


def test_matmul_mxfp4_weights_use_their_block_scales(harness: Harness) -> None:
    rng = np.random.default_rng(5)
    depth, cols, rows, block = 32, 2, 2, 32
    activations = random_bf16(rng, (rows, depth), scale=0.25)
    nibbles = rng.integers(0, 16, size=(cols, depth), dtype=np.uint8)
    packed = (nibbles[:, 0::2] | (nibbles[:, 1::2] << 4)).astype(np.uint8)
    scale_codes = rng.integers(124, 130, size=(cols, depth // block), dtype=np.uint8)

    scale_object = harness.constant(scale_codes.tobytes())
    weight_object = harness.constant(packed.tobytes())
    weight_view = harness.builder.tensor_view(
        object_id=weight_object,
        dtype=DType.MXFP4_E2M1,
        dims=[cols, depth],
        permissions=READ,
        layout_class=LayoutClass.BLOCK_SCALED,
        scale_object_id=scale_object,
        scale_block_elements=block,
    )
    numeric = matmul_numeric(harness, second_input_dtype=DType.MXFP4_E2M1)
    output = harness.output_view((rows, cols), DType.BF16)
    operator = harness.operator(
        engine_family=Major.TENSOR,
        engine_sub=Tensor.MATMUL,
        inputs=[harness.const_view(activations, DType.BF16), weight_view],
        outputs=[output],
        numeric_profile_id=numeric,
    )
    harness.run(Major.TENSOR, Tensor.MATMUL, operator)

    expected_weights = []
    for col in range(cols):
        expected_weights.append(
            list(
                exact.decode_mxfp4_block(
                    [int(byte) for byte in packed[col]], int(scale_codes[col, 0])
                )
            )
        )
    np.testing.assert_array_equal(
        harness.result(output), oracle_scaled_matmul(activations, expected_weights)
    )


def test_matmul_rejects_a_reduction_order_it_does_not_implement(
    harness: Harness,
) -> None:
    rng = np.random.default_rng(1)
    numeric = matmul_numeric(harness, reduction_order=ReductionOrder.PAIRWISE_TREE)
    operator = harness.operator(
        engine_family=Major.TENSOR,
        engine_sub=Tensor.MATMUL,
        inputs=[
            harness.const_view(random_bf16(rng, (2, 4)), DType.BF16),
            harness.const_view(random_bf16(rng, (2, 4)), DType.BF16),
        ],
        outputs=[harness.output_view((2, 2), DType.BF16)],
        numeric_profile_id=numeric,
    )
    with pytest.raises(EngineError) as error:
        harness.run(Major.TENSOR, Tensor.MATMUL, operator)
    assert error.value.trap_class == 4
    assert "reduction order" in str(error.value)


def test_matmul_rejects_a_view_that_contradicts_its_numeric_profile(
    harness: Harness,
) -> None:
    rng = np.random.default_rng(2)
    numeric = matmul_numeric(harness, second_input_dtype=DType.FP8_E4M3FN)
    operator = harness.operator(
        engine_family=Major.TENSOR,
        engine_sub=Tensor.MATMUL,
        inputs=[
            harness.const_view(random_bf16(rng, (2, 4)), DType.BF16),
            harness.const_view(random_bf16(rng, (2, 4)), DType.BF16),
        ],
        outputs=[harness.output_view((2, 2), DType.BF16)],
        numeric_profile_id=numeric,
    )
    with pytest.raises(EngineError) as error:
        harness.run(Major.TENSOR, Tensor.MATMUL, operator)
    assert error.value.trap_class == 3


def test_matmul_rejects_mismatched_reduction_extents(harness: Harness) -> None:
    rng = np.random.default_rng(4)
    operator = harness.operator(
        engine_family=Major.TENSOR,
        engine_sub=Tensor.MATMUL,
        inputs=[
            harness.const_view(random_bf16(rng, (2, 4)), DType.BF16),
            harness.const_view(random_bf16(rng, (3, 5)), DType.BF16),
        ],
        outputs=[harness.output_view((2, 3), DType.BF16)],
        numeric_profile_id=matmul_numeric(harness),
    )
    with pytest.raises(EngineError, match="reduction extents differ"):
        harness.run(Major.TENSOR, Tensor.MATMUL, operator)


def test_matmul_rejects_a_non_finite_operand(harness: Harness) -> None:
    activations = np.array([[0x7F80, 0x0000, 0x0000, 0x0000]], dtype=np.uint16)
    rng = np.random.default_rng(6)
    operator = harness.operator(
        engine_family=Major.TENSOR,
        engine_sub=Tensor.MATMUL,
        inputs=[
            harness.const_view(activations, DType.BF16),
            harness.const_view(random_bf16(rng, (2, 4)), DType.BF16),
        ],
        outputs=[harness.output_view((1, 2), DType.BF16)],
        numeric_profile_id=matmul_numeric(harness),
    )
    with pytest.raises(EngineError) as error:
        harness.run(Major.TENSOR, Tensor.MATMUL, operator)
    assert error.value.trap_class == 6


# ---------------------------------------------------------------------------
# TENSOR.EMBED_LOOKUP
# ---------------------------------------------------------------------------
def test_embed_lookup_gathers_exact_rows(harness: Harness) -> None:
    rng = np.random.default_rng(9)
    table = random_bf16(rng, (16, 6))
    identifiers = np.array([3, 0, 15, 3], dtype=np.uint32)
    output = harness.output_view((4, 6), DType.BF16)
    operator = harness.operator(
        engine_family=Major.TENSOR,
        engine_sub=Tensor.EMBED_LOOKUP,
        inputs=[
            harness.const_view(identifiers, DType.U32, storage_class=StorageClass.HOST),
            harness.const_view(table, DType.BF16),
        ],
        outputs=[output],
    )
    harness.run(Major.TENSOR, Tensor.EMBED_LOOKUP, operator)

    np.testing.assert_array_equal(harness.result(output), table[identifiers])
    counters = harness.counters
    assert counters["tensor.embedding_rows"] == 4
    assert counters["tensor.output_elements"] == 24
    # Only the gathered rows are charged, not the whole table.
    assert counters["hbm.bytes_read"] == 4 * 6 * 2


def test_embed_lookup_rejects_an_out_of_range_token(harness: Harness) -> None:
    rng = np.random.default_rng(10)
    operator = harness.operator(
        engine_family=Major.TENSOR,
        engine_sub=Tensor.EMBED_LOOKUP,
        inputs=[
            harness.const_view(
                np.array([16], dtype=np.uint32), DType.U32, storage_class=StorageClass.HOST
            ),
            harness.const_view(random_bf16(rng, (16, 6)), DType.BF16),
        ],
        outputs=[harness.output_view((1, 6), DType.BF16)],
    )
    with pytest.raises(EngineError, match="token ID outside"):
        harness.run(Major.TENSOR, Tensor.EMBED_LOOKUP, operator)


# ---------------------------------------------------------------------------
# TENSOR.GROUPED_MATMUL
# ---------------------------------------------------------------------------
def test_grouped_matmul_contracts_each_row_segment(harness: Harness) -> None:
    rng = np.random.default_rng(13)
    rows, groups, cols, depth = 5, 3, 4, 8
    activations = random_bf16(rng, (rows, depth))
    weights = random_bf16(rng, (groups, cols, depth))
    counts = np.array([2, 0, 3], dtype=np.uint32)
    output = harness.output_view((rows, cols), DType.BF16)
    operator = harness.operator(
        engine_family=Major.TENSOR,
        engine_sub=Tensor.GROUPED_MATMUL,
        inputs=[
            harness.const_view(activations, DType.BF16),
            harness.const_view(weights, DType.BF16),
            harness.const_view(counts, DType.U32),
        ],
        outputs=[output],
        numeric_profile_id=matmul_numeric(harness),
    )
    harness.run(Major.TENSOR, Tensor.GROUPED_MATMUL, operator)

    expected = np.empty((rows, cols), dtype=np.uint16)
    expected[0:2] = oracle_matmul(activations[0:2], weights[0])
    expected[2:5] = oracle_matmul(activations[2:5], weights[2])
    np.testing.assert_array_equal(harness.result(output), expected)
    counters = harness.counters
    assert counters["tensor.grouped_launches"] == 2
    assert counters["tensor.multiplications"] == rows * cols * depth
    # Only the two launched groups' weights are read.
    assert counters["hbm.bytes_read"] == (
        rows * depth * 2 + counts.size * 4 + 2 * cols * depth * 2
    )


def test_grouped_matmul_rejects_counts_that_do_not_cover_the_rows(
    harness: Harness,
) -> None:
    rng = np.random.default_rng(14)
    operator = harness.operator(
        engine_family=Major.TENSOR,
        engine_sub=Tensor.GROUPED_MATMUL,
        inputs=[
            harness.const_view(random_bf16(rng, (5, 8)), DType.BF16),
            harness.const_view(random_bf16(rng, (3, 4, 8)), DType.BF16),
            harness.const_view(np.array([1, 1, 1], dtype=np.uint32), DType.U32),
        ],
        outputs=[harness.output_view((5, 4), DType.BF16)],
        numeric_profile_id=matmul_numeric(harness),
    )
    with pytest.raises(EngineError, match="group counts sum"):
        harness.run(Major.TENSOR, Tensor.GROUPED_MATMUL, operator)


# ---------------------------------------------------------------------------
# TENSOR.ROUTED_MATMUL
# ---------------------------------------------------------------------------
def test_routed_matmul_combines_slots_in_ascending_order(harness: Harness) -> None:
    rng = np.random.default_rng(17)
    rows, experts, cols, depth, topk = 3, 4, 2, 8, 2
    activations = random_bf16(rng, (rows, depth))
    weights = random_bf16(rng, (experts, cols, depth))
    identifiers = np.array([[0, 3], [1, 1], [2, 0]], dtype=np.uint32)
    routing = bf16(np.array([[0.75, 0.25], [0.5, 0.5], [1.0, 0.125]], dtype=np.float32))
    output = harness.output_view((rows, cols), DType.BF16)
    operator = harness.operator(
        engine_family=Major.TENSOR,
        engine_sub=Tensor.ROUTED_MATMUL,
        inputs=[
            harness.const_view(activations, DType.BF16),
            harness.const_view(weights, DType.BF16),
            harness.const_view(identifiers, DType.U32),
            harness.const_view(routing, DType.BF16),
        ],
        outputs=[output],
        numeric_profile_id=matmul_numeric(harness),
    )
    harness.bind()
    harness.ctx.device = type(
        "ObservedDevice", (), {"host_performance": HostPerformanceObservations()}
    )()
    harness.run(Major.TENSOR, Tensor.ROUTED_MATMUL, operator)

    expected = np.empty((rows, cols), dtype=np.uint16)
    for row in range(rows):
        left = [exact_value(code) for code in activations[row]]
        for col in range(cols):
            accumulator = 0
            for slot in range(topk):
                expert = int(identifiers[row, slot])
                right = [exact_value(code) for code in weights[expert, col]]
                partial = exact.binary32_ordered_dot(left, right)
                scaled = exact.binary32_multiply(
                    partial, exact.encode_binary32_rne(exact_value(routing[row, slot]))
                )
                accumulator = exact.binary32_add(accumulator, scaled)
            expected[row, col] = exact.binary32_bits_to_bf16_rne(accumulator).code
    np.testing.assert_array_equal(harness.result(output), expected)
    assert harness.counters["tensor.routed_launches"] == rows * topk
    observed = harness.ctx.device.host_performance.snapshot()
    totals = observed["totals"]
    assert totals["routed_operator_issues"] == 1
    assert totals["route_organization_passes"] == 1
    assert totals["route_unique_scans"] == topk
    assert totals["route_row_selection_scans"] == 6
    assert totals["routed_semantic_segments"] == 6
    assert totals["routed_physical_backend_calls"] == 6
    assert totals["routed_selected_rows"] == rows * topk
    assert totals["decoded_weight_materializations"] == 6
    assert totals["decoded_weight_source_bytes"] == 6 * cols * depth * 2
    assert totals["decoded_weight_result_bytes"] == 6 * cols * depth * 4
    assert totals["routed_weight_source_bytes"] == 6 * cols * depth * 2
    assert observed["durations"]["routed_operator_seconds"] > 0
    assert observed["durations"]["decoded_weight_materialization_seconds"] > 0


def test_routed_matmul_reads_only_the_experts_it_uses(harness: Harness) -> None:
    """The expert bank is read one slice at a time, never as a whole.

    ``ViewResolver.read_array`` is zero-copy only while the extent lies inside
    one mapped segment, and a released expert bank does not: DeepSeek-V4-Flash
    presents ``[256, 2048, 4096]`` -- 2.147 GB spanning many checkpoint
    segments -- so reading the *stack* to reach one expert of it fell to the
    gathering copy path at 14.4 s cold and 2.0-3.6 s warm per issue, to use at
    most six experts, 8.4 MB of 2,147 MB.  A 43-layer four-token prefill issues
    516 of them.

    Reading through the slice the engine already builds is a ~256x reduction on
    that path, and this states it as a property rather than as a timing: the
    element counts the resolver is asked for are each one expert's ``[N, K]``
    block, one per distinct expert the routing selected, and never the stack.
    """
    rng = np.random.default_rng(0x5241)
    rows, experts, cols, depth = 3, 8, 2, 8
    activations = random_bf16(rng, (rows, depth))
    weights = random_bf16(rng, (experts, cols, depth))
    identifiers = np.array([[0, 3], [1, 1], [2, 0]], dtype=np.uint32)
    output = harness.output_view((rows, cols), DType.BF16)
    operator = harness.operator(
        engine_family=Major.TENSOR,
        engine_sub=Tensor.ROUTED_MATMUL,
        inputs=[
            harness.const_view(activations, DType.BF16),
            harness.const_view(weights, DType.BF16),
            harness.const_view(identifiers, DType.U32),
        ],
        outputs=[output],
        numeric_profile_id=matmul_numeric(harness),
    )
    harness.bind()
    resolver = harness.ctx.views
    original = resolver.read_array
    requested: list[int] = []

    def recording(view):
        requested.append(int(view.element_count))
        return original(view)

    resolver.read_array = recording          # type: ignore[method-assign]
    try:
        harness.run(Major.TENSOR, Tensor.ROUTED_MATMUL, operator)
    finally:
        resolver.read_array = original       # type: ignore[method-assign]

    stack_elements = experts * cols * depth
    slice_elements = cols * depth
    assert stack_elements not in requested, requested
    # Five distinct experts are selected across the two slots -- 0, 3, 1, 2 --
    # and expert 0 twice, so four reads and not five: the per-issue cache means
    # a second slot selecting an expert does not re-read it.
    assert requested.count(slice_elements) == 4, requested
    assert sum(requested) < stack_elements


def test_routed_matmul_rejects_an_unknown_expert(harness: Harness) -> None:
    rng = np.random.default_rng(19)
    operator = harness.operator(
        engine_family=Major.TENSOR,
        engine_sub=Tensor.ROUTED_MATMUL,
        inputs=[
            harness.const_view(random_bf16(rng, (1, 8)), DType.BF16),
            harness.const_view(random_bf16(rng, (2, 2, 8)), DType.BF16),
            harness.const_view(np.array([[2]], dtype=np.uint32), DType.U32),
        ],
        outputs=[harness.output_view((1, 2), DType.BF16)],
        numeric_profile_id=matmul_numeric(harness),
    )
    with pytest.raises(EngineError, match="expert ID outside"):
        harness.run(Major.TENSOR, Tensor.ROUTED_MATMUL, operator)


def test_routed_matmul_computes_only_the_current_nodes_expert_shard(
    harness: Harness,
) -> None:
    """Global IDs are rebased into one consecutive node-local expert bank."""

    activations = bf16(
        np.array([[2.0, 3.0], [5.0, 7.0]], dtype=np.float32)
    )
    # NODE_ID 1 owns global experts 2 and 3.  Expert 2 selects x0 and expert 3
    # selects x1, making the owner contribution visible without a shared oracle.
    local_weights = bf16(
        np.array([[[1.0, 0.0]], [[0.0, 1.0]]], dtype=np.float32)
    )
    identifiers = np.array([[0, 3], [2, 1]], dtype=np.uint32)
    output = harness.output_view((2, 1), DType.BF16)
    operator = harness.operator(
        engine_family=Major.TENSOR,
        engine_sub=Tensor.ROUTED_MATMUL,
        inputs=[
            harness.const_view(activations, DType.BF16),
            harness.const_view(local_weights, DType.BF16),
            harness.const_view(identifiers, DType.U32),
        ],
        outputs=[output],
        aux=[4],
        numeric_profile_id=matmul_numeric(harness),
    )
    harness.bind()
    harness.ctx.node_memories = (harness.memory, harness.memory)
    harness.ctx.symbols[int(Symbol.NODE_ID)] = 1
    harness.run(Major.TENSOR, Tensor.ROUTED_MATMUL, operator)

    # Row 0's expert 0 is another node's and contributes zero; expert 3 owns
    # the second activation.  Row 1 is the converse for expert 2 / expert 1.
    np.testing.assert_array_equal(
        harness.result(output),
        bf16(np.array([[3.0], [5.0]], dtype=np.float32)),
    )
    assert harness.counters["tensor.routed_launches"] == 2
    assert harness.counters["tensor.multiplications"] == 2 * 1 * 2
    # Two length-2 contractions plus the two top-k partial combinations.
    assert harness.counters["tensor.additions"] == 2 * 1 * (2 - 1) + 2 * 1 * (2 - 1)


def _attach_weight_cache(
    harness: Harness, budget_bytes: int
) -> SimpleNamespace:
    observations = HostPerformanceObservations()
    source = harness.ctx.views.deployment
    deployment = SimpleNamespace(
        objects=source.objects,
        generation=1,
        deployment_digest=hashlib.sha256(b"engine-cache-test").digest(),
    )
    device = SimpleNamespace(
        deployment=deployment,
        host_performance=observations,
        decoded_weight_cache=DecodedWeightCache(
            budget_bytes=budget_bytes,
            working_reserve_bytes=0,
            node_count=harness.ctx.node_count,
            observations=observations,
        ),
    )
    harness.ctx.device = device
    return device


def _cached_routed_fixture(harness: Harness) -> tuple[int, int, int]:
    rng = np.random.default_rng(0xCA5E)
    rows, experts, cols, depth, block = 3, 4, 2, 8, 4
    activations = random_bf16(rng, (rows, depth), scale=0.25)
    weights = rng.integers(
        0, 0x7E, size=(experts, cols, depth), dtype=np.uint8
    )
    scales = rng.integers(
        120,
        130,
        size=(experts * cols, depth // block),
        dtype=np.uint8,
    )
    scale_object = harness.constant(scales.tobytes(), authenticated=True)
    weight_view = harness.const_view(
        weights,
        DType.FP8_E4M3FN,
        scale_object_id=scale_object,
        scale_block_elements=block,
        authenticated=True,
    )
    identifiers = np.array([[0, 3], [1, 1], [2, 0]], dtype=np.uint32)
    output = harness.output_view((rows, cols), DType.BF16)
    operator = harness.operator(
        engine_family=Major.TENSOR,
        engine_sub=Tensor.ROUTED_MATMUL,
        inputs=[
            harness.const_view(activations, DType.BF16),
            weight_view,
            harness.const_view(identifiers, DType.U32),
        ],
        outputs=[output],
        numeric_profile_id=matmul_numeric(
            harness,
            contract=CONTRACT_BLOCKED,
            second_input_dtype=DType.FP8_E4M3FN,
        ),
    )
    return operator, output, weight_view


def test_routed_decoded_weight_cache_is_architecturally_transparent(
    harness: Harness,
) -> None:
    operator, output, _weight_view = _cached_routed_fixture(harness)
    backend = get_backend()

    harness.bind()
    cache_off = _attach_weight_cache(harness, 0)
    backend.reset_executed_associations()
    for _ in range(2):
        harness.run(Major.TENSOR, Tensor.ROUTED_MATMUL, operator)
    output_off = np.array(harness.result(output), copy=True)
    counters_off = harness.counters.snapshot()
    aggregate_off = backend.executed_association_manifest()
    observed_off = cache_off.host_performance.snapshot()

    harness.bind()
    decoded_working_set = 4 * 2 * 8 * np.dtype(np.float32).itemsize
    cache_on = _attach_weight_cache(harness, decoded_working_set)
    backend.reset_executed_associations()
    for _ in range(2):
        harness.run(Major.TENSOR, Tensor.ROUTED_MATMUL, operator)
    output_on = np.array(harness.result(output), copy=True)
    counters_on = harness.counters.snapshot()
    aggregate_on = backend.executed_association_manifest()
    observed_on = cache_on.host_performance.snapshot()

    np.testing.assert_array_equal(output_on, output_off)
    assert counters_on == counters_off
    assert aggregate_on == aggregate_off
    assert (
        observed_on["ordered_executed_associations"]
        == observed_off["ordered_executed_associations"]
    )

    off = observed_off["totals"]
    on = observed_on["totals"]
    assert off["decoded_weight_materializations"] == 12
    assert off["decoded_weight_cache_bypasses"] == 12
    assert on["decoded_weight_materializations"] == 4
    assert on["decoded_weight_cache_misses"] == 4
    assert on["decoded_weight_cache_admissions"] == 4
    assert on["decoded_weight_cache_hits"] == 8
    assert on["routed_physical_backend_calls"] == 12
    assert on["routed_physical_backend_calls"] == off["routed_physical_backend_calls"]
    assert on["routed_weight_source_bytes"] == off["routed_weight_source_bytes"]
    assert on["decoded_weight_cache_live_bytes"] == decoded_working_set
    assert on["decoded_weight_cache_high_water_bytes"] == decoded_working_set


def test_routed_cache_key_refuses_mutable_or_unauthenticated_content(
    harness: Harness,
) -> None:
    _operator, _output, authenticated_view = _cached_routed_fixture(harness)
    unauthenticated_view = harness.const_view(
        np.ones((1, 2, 8), dtype=np.uint8), DType.FP8_E4M3FN
    )
    unauthenticated_scale = harness.constant(bytes([127, 127]))
    untrusted_scale_view = harness.const_view(
        np.ones((1, 2, 8), dtype=np.uint8),
        DType.FP8_E4M3FN,
        scale_object_id=unauthenticated_scale,
        scale_block_elements=8,
        authenticated=True,
    )
    mutable_object = harness.scratch(16, StorageClass.HBM)
    mutable_view = harness.builder.tensor_view(
        object_id=mutable_object,
        dtype=DType.FP8_E4M3FN,
        dims=[1, 2, 8],
        permissions=READ_WRITE,
    )

    harness.bind()
    device = _attach_weight_cache(harness, 1024)
    identity = get_backend().implementation_identity()

    authenticated = tensor_engine._slice_view(
        harness.ctx.view(authenticated_view), (2, 8), 0
    )
    key = tensor_engine._decoded_weight_cache_key(
        harness.ctx,
        authenticated,
        contract=CONTRACT_BLOCKED,
        backend_identity=identity,
    )
    assert key is not None

    second_slice = tensor_engine._slice_view(
        harness.ctx.view(authenticated_view), (2, 8), 1
    )
    offset_key = tensor_engine._decoded_weight_cache_key(
        harness.ctx,
        second_slice,
        contract=CONTRACT_BLOCKED,
        backend_identity=identity,
    )
    assert offset_key is not None and offset_key != key

    harness.ctx.symbols[int(Symbol.NODE_ID)] = 1
    node_key = tensor_engine._decoded_weight_cache_key(
        harness.ctx,
        authenticated,
        contract=CONTRACT_BLOCKED,
        backend_identity=identity,
    )
    assert node_key is not None and node_key != key
    harness.ctx.symbols[int(Symbol.NODE_ID)] = 0

    device.deployment.generation = 2
    generation_key = tensor_engine._decoded_weight_cache_key(
        harness.ctx,
        authenticated,
        contract=CONTRACT_BLOCKED,
        backend_identity=identity,
    )
    assert generation_key is not None and generation_key != key
    device.deployment.generation = 1

    contract_key = tensor_engine._decoded_weight_cache_key(
        harness.ctx,
        authenticated,
        contract="different-contract",
        backend_identity=identity,
    )
    assert contract_key is not None and contract_key != key
    backend_key = tensor_engine._decoded_weight_cache_key(
        harness.ctx,
        authenticated,
        contract=CONTRACT_BLOCKED,
        backend_identity={**identity, "test_identity_field": True},
    )
    assert backend_key is not None and backend_key != key

    for view_id in (unauthenticated_view, untrusted_scale_view, mutable_view):
        candidate = tensor_engine._slice_view(
            harness.ctx.view(view_id), (2, 8), 0
        )
        assert (
            tensor_engine._decoded_weight_cache_key(
                harness.ctx,
                candidate,
                contract=CONTRACT_BLOCKED,
                backend_identity=identity,
            )
            is None
        )


def test_routed_cache_failure_uses_the_unchanged_uncached_path(
    harness: Harness,
) -> None:
    operator, output, _weight_view = _cached_routed_fixture(harness)

    harness.bind()
    _attach_weight_cache(harness, 0)
    harness.run(Major.TENSOR, Tensor.ROUTED_MATMUL, operator)
    expected = np.array(harness.result(output), copy=True)
    expected_counters = harness.counters.snapshot()

    harness.bind()
    device = _attach_weight_cache(harness, 1024)

    class FailingCache:
        @staticmethod
        def probe(**_kwargs):
            raise RuntimeError("injected cache failure")

    device.decoded_weight_cache = FailingCache()
    harness.run(Major.TENSOR, Tensor.ROUTED_MATMUL, operator)
    np.testing.assert_array_equal(harness.result(output), expected)
    assert harness.counters.snapshot() == expected_counters
    assert device.host_performance.snapshot()["totals"][
        "decoded_weight_materializations"
    ] == 6


def test_routed_cache_preserves_late_poison_fault_and_output_atomicity(
    harness: Harness,
) -> None:
    rng = np.random.default_rng(0xFA017)
    rows, experts, cols, depth, block = 2, 2, 2, 8, 4
    weights = rng.integers(
        0, 0x7E, size=(experts, cols, depth), dtype=np.uint8
    )
    scales = np.full((experts * cols, depth // block), 127, dtype=np.uint8)
    scales[cols, 0] = 0xFF
    scale_object = harness.constant(scales.tobytes(), authenticated=True)
    weight_view = harness.const_view(
        weights,
        DType.FP8_E4M3FN,
        scale_object_id=scale_object,
        scale_block_elements=block,
        authenticated=True,
    )
    output = harness.output_view((rows, cols), DType.BF16)
    operator = harness.operator(
        engine_family=Major.TENSOR,
        engine_sub=Tensor.ROUTED_MATMUL,
        inputs=[
            harness.const_view(random_bf16(rng, (rows, depth)), DType.BF16),
            weight_view,
            harness.const_view(
                np.array([[0], [1]], dtype=np.uint32), DType.U32
            ),
        ],
        outputs=[output],
        numeric_profile_id=matmul_numeric(
            harness,
            second_input_dtype=DType.FP8_E4M3FN,
        ),
    )
    harness.bind()
    device = _attach_weight_cache(harness, experts * cols * depth * 4)

    with pytest.raises(EngineError, match="reserved E8M0 code"):
        harness.run(Major.TENSOR, Tensor.ROUTED_MATMUL, operator)
    np.testing.assert_array_equal(
        harness.result(output), np.zeros((rows, cols), dtype=np.uint16)
    )
    # Expert zero completed and entered the cache before expert one's scale
    # poisoned the instruction.  No partial accumulator reached device memory.
    assert device.host_performance.snapshot()["totals"][
        "decoded_weight_cache_admissions"
    ] == 1


# ---------------------------------------------------------------------------
# VECTOR.RMS_NORM and VECTOR.HEAD_RMS_NORM
# ---------------------------------------------------------------------------
def test_rms_norm_matches_the_exact_reference(harness: Harness) -> None:
    rng = np.random.default_rng(23)
    width = 128
    values = random_bf16(rng, (2, width))
    weights = random_bf16(rng, (width,), scale=0.5)
    numeric = harness.numeric(
        contract="qwen3_rmsnorm_fp32_bf16_v1",
        input_dtype=DType.BF16,
        output_dtype=DType.BF16,
        epsilon_bits=QWEN_RMS_EPSILON_CODE,
    )
    output = harness.output_view((2, width), DType.BF16)
    operator = harness.operator(
        engine_family=Major.VECTOR,
        engine_sub=Vector.RMS_NORM,
        inputs=[
            harness.const_view(values, DType.BF16),
            harness.const_view(weights, DType.BF16),
        ],
        outputs=[output],
        numeric_profile_id=numeric,
    )
    harness.run(Major.VECTOR, Vector.RMS_NORM, operator)

    expected = exact_rms_norm(
        [tuple(int(code) for code in row) for row in values],
        tuple(int(code) for code in weights),
    )
    np.testing.assert_array_equal(
        harness.result(output), np.asarray(expected.values, dtype=np.uint16)
    )
    assert harness.counters["vector.norm_rows"] == 2
    assert harness.counters["vector.elements"] == 2 * width


def test_rms_norm_requires_a_declared_epsilon(harness: Harness) -> None:
    rng = np.random.default_rng(24)
    numeric = harness.numeric(
        contract="qwen3_rmsnorm_fp32_bf16_v1",
        input_dtype=DType.BF16,
        output_dtype=DType.BF16,
    )
    operator = harness.operator(
        engine_family=Major.VECTOR,
        engine_sub=Vector.RMS_NORM,
        inputs=[
            harness.const_view(random_bf16(rng, (1, 8)), DType.BF16),
            harness.const_view(random_bf16(rng, (8,)), DType.BF16),
        ],
        outputs=[harness.output_view((1, 8), DType.BF16)],
        numeric_profile_id=numeric,
    )
    with pytest.raises(EngineError, match="declares no epsilon"):
        harness.run(Major.VECTOR, Vector.RMS_NORM, operator)


def test_head_rms_norm_normalises_each_head_row(harness: Harness) -> None:
    rng = np.random.default_rng(25)
    heads, head_dim = 3, 128
    values = random_bf16(rng, (2, heads, head_dim))
    weights = random_bf16(rng, (head_dim,), scale=0.5)
    numeric = harness.numeric(
        contract="qwen3_rmsnorm_fp32_bf16_v1",
        input_dtype=DType.BF16,
        output_dtype=DType.BF16,
        epsilon_bits=QWEN_RMS_EPSILON_CODE,
    )
    output = harness.output_view((2, heads, head_dim), DType.BF16)
    operator = harness.operator(
        engine_family=Major.VECTOR,
        engine_sub=Vector.HEAD_RMS_NORM,
        inputs=[
            harness.const_view(values, DType.BF16),
            harness.const_view(weights, DType.BF16),
        ],
        outputs=[output],
        numeric_profile_id=numeric,
    )
    harness.run(Major.VECTOR, Vector.HEAD_RMS_NORM, operator)

    expected = exact_rms_norm(
        [tuple(int(code) for code in row) for row in values.reshape(-1, head_dim)],
        tuple(int(code) for code in weights),
    )
    np.testing.assert_array_equal(
        harness.result(output).reshape(-1, head_dim),
        np.asarray(expected.values, dtype=np.uint16),
    )
    assert harness.counters["vector.norm_rows"] == 2 * heads


def test_unweighted_head_rms_norm_uses_the_bf16_domain_contract(
    harness: Harness,
) -> None:
    rng = np.random.default_rng(26)
    values = random_bf16(rng, (1, HEAD_RMS_NORM_WIDTH))
    numeric = harness.numeric(
        contract="deepseek_v4_head_rms_norm_bf16_v1",
        input_dtype=DType.BF16,
        output_dtype=DType.BF16,
        epsilon_bits=HEAD_RMS_NORM_EPSILON_BF16,
    )
    output = harness.output_view((1, HEAD_RMS_NORM_WIDTH), DType.BF16)
    operator = harness.operator(
        engine_family=Major.VECTOR,
        engine_sub=Vector.HEAD_RMS_NORM,
        inputs=[harness.const_view(values, DType.BF16)],
        outputs=[output],
        numeric_profile_id=numeric,
    )
    harness.run(Major.VECTOR, Vector.HEAD_RMS_NORM, operator)

    expected = head_rms_norm_bf16([tuple(int(code) for code in values[0])])
    np.testing.assert_array_equal(
        harness.result(output), np.asarray(expected.output_codes, dtype=np.uint16)
    )


# ---------------------------------------------------------------------------
# VECTOR.ROPE
# ---------------------------------------------------------------------------
def oracle_rope(values: np.ndarray, coefficients: np.ndarray) -> np.ndarray:
    """Exact RoPE from the independent scalar reference implementation."""
    width = values.shape[1]
    rows = [tuple(int(code) for code in row) for row in values]
    result = exact_rope(
        rows,
        rows,
        tuple(int(code) for code in coefficients[:width]),
        tuple(int(code) for code in coefficients[width:]),
    )
    return np.asarray(result.query_values, dtype=np.uint16)


def test_rope_matches_the_exact_two_product_contract(harness: Harness) -> None:
    rng = np.random.default_rng(29)
    width = 8
    values = random_bf16(rng, (2, width))
    coefficients = random_bf16(rng, (2 * width,), scale=0.5)
    numeric = harness.numeric(
        contract="qwen3_rope_fp32_bf16_v1",
        input_dtype=DType.BF16,
        output_dtype=DType.BF16,
    )
    output = harness.output_view((2, width), DType.BF16)
    operator = harness.operator(
        engine_family=Major.VECTOR,
        engine_sub=Vector.ROPE,
        inputs=[
            harness.const_view(values, DType.BF16),
            harness.const_view(coefficients, DType.BF16),
        ],
        outputs=[output],
        numeric_profile_id=numeric,
    )
    harness.run(Major.VECTOR, Vector.ROPE, operator)

    np.testing.assert_array_equal(
        harness.result(output), oracle_rope(values, coefficients)
    )
    assert harness.counters["vector.rope_pairs"] == 2 * (width // 2)


def test_rope_applies_one_coefficient_row_per_input_row(harness: Harness) -> None:
    rng = np.random.default_rng(31)
    width = 8
    values = random_bf16(rng, (3, width))
    coefficients = random_bf16(rng, (3, 2 * width), scale=0.5)
    numeric = harness.numeric(
        contract="qwen3_rope_fp32_bf16_v1",
        input_dtype=DType.BF16,
        output_dtype=DType.BF16,
    )
    output = harness.output_view((3, width), DType.BF16)
    operator = harness.operator(
        engine_family=Major.VECTOR,
        engine_sub=Vector.ROPE,
        inputs=[
            harness.const_view(values, DType.BF16),
            harness.const_view(coefficients, DType.BF16),
        ],
        outputs=[output],
        numeric_profile_id=numeric,
    )
    harness.run(Major.VECTOR, Vector.ROPE, operator)

    expected = np.concatenate(
        [
            oracle_rope(values[index : index + 1], coefficients[index])
            for index in range(3)
        ]
    )
    np.testing.assert_array_equal(harness.result(output), expected)


def oracle_partial_rope(
    values: np.ndarray, coefficients: np.ndarray, rotary: int, *, inverse: bool
) -> np.ndarray:
    """The suffix rotation written out directly, in Python, per element.

    Deliberately not the engine's formulation: this walks pairs one at a time
    with ``fractions``-free binary32 NumPy scalars, so it agrees with the engine
    only if both agree about which channels rotate, which channel each is paired
    with, and where the arithmetic rounds.
    """
    rows, width = values.shape
    prefix = width - rotary
    output = np.array(values, dtype=np.uint16, copy=True)
    for row in range(rows):
        coefficient_row = coefficients[row if coefficients.shape[0] > 1 else 0]
        for pair in range(rotary // 2):
            real = widen_bf16(values[row, prefix + 2 * pair : prefix + 2 * pair + 1])[0]
            imaginary = widen_bf16(
                values[row, prefix + 2 * pair + 1 : prefix + 2 * pair + 2]
            )[0]
            cosine = np.float32(coefficient_row[2 * pair])
            sine = np.float32(coefficient_row[rotary + 2 * pair])
            if inverse:
                sine = np.float32(-sine)
            real_output = np.float32(
                np.float32(real * cosine) - np.float32(imaginary * sine)
            )
            imaginary_output = np.float32(
                np.float32(real * sine) + np.float32(imaginary * cosine)
            )
            codes, _ = narrow_bf16_rne(
                np.array([real_output, imaginary_output], dtype=np.float32)
            )
            output[row, prefix + 2 * pair] = codes[0]
            output[row, prefix + 2 * pair + 1] = codes[1]
    return output


def partial_rope_operator(
    harness: Harness,
    values: np.ndarray,
    coefficients: np.ndarray,
    *,
    rotary: int,
    contract: str,
) -> tuple[int, int]:
    numeric = harness.numeric(
        contract=contract,
        input_dtype=DType.BF16,
        second_input_dtype=DType.FP32,
        output_dtype=DType.BF16,
    )
    output = harness.output_view(values.shape, DType.BF16)
    operator = harness.operator(
        engine_family=Major.VECTOR,
        engine_sub=Vector.ROPE,
        inputs=[
            harness.const_view(values, DType.BF16),
            harness.const_view(coefficients, DType.FP32),
        ],
        outputs=[output],
        aux=[rotary],
        numeric_profile_id=numeric,
    )
    return output, operator


@pytest.mark.parametrize("contract", ("rope_apply_bf16_v1", "rope_inverse_bf16_v1"))
def test_rope_rotates_only_the_suffix_aux0_declares(
    harness: Harness, contract: str
) -> None:
    """``aux_id_0`` is the rotary width the frozen operand row already names.

    The untouched prefix is the point: DeepSeek rotates 64 of a head's 512
    channels, and the channels it does not rotate are the *partners* the Qwen
    kernel would have paired them with, so a padded full-width table cannot
    stand in for a narrow one.
    """
    rng = np.random.default_rng(53)
    rows, width, rotary = 3, 16, 8
    values = random_bf16(rng, (rows, width))
    coefficients = rng.standard_normal((rows, 2 * rotary)).astype(np.float32)
    output, operator = partial_rope_operator(
        harness, values, coefficients, rotary=rotary, contract=contract
    )
    harness.run(Major.VECTOR, Vector.ROPE, operator)

    produced = harness.result(output)
    np.testing.assert_array_equal(
        produced,
        oracle_partial_rope(
            values, coefficients, rotary, inverse=contract.endswith("inverse_bf16_v1")
        ),
    )
    np.testing.assert_array_equal(
        produced[:, : width - rotary], values[:, : width - rotary]
    )
    assert harness.counters["vector.rope_pairs"] == rows * (rotary // 2)
    # One BF16 conversion per rotated value; the prefix crosses no boundary.
    assert harness.counters["vector.conversions"] == rows * rotary


def test_rope_broadcasts_one_partial_coefficient_row_over_every_row(
    harness: Harness,
) -> None:
    rng = np.random.default_rng(59)
    rows, width, rotary = 4, 16, 8
    values = random_bf16(rng, (rows, width))
    coefficients = rng.standard_normal((2 * rotary,)).astype(np.float32)
    output, operator = partial_rope_operator(
        harness,
        values,
        coefficients,
        rotary=rotary,
        contract="rope_apply_bf16_v1",
    )
    harness.run(Major.VECTOR, Vector.ROPE, operator)
    np.testing.assert_array_equal(
        harness.result(output),
        oracle_partial_rope(
            values, coefficients.reshape(1, -1), rotary, inverse=False
        ),
    )


def test_rope_ignores_aux0_under_the_whole_axis_contract(harness: Harness) -> None:
    """``qwen3_rope_fp32_bf16_v1`` rotates the whole axis and reads no width.

    Not a convenience: the ROM backend writes the head dimension into
    ``aux_id_0`` and the HBM/SRAM backend writes the coefficient row's width,
    which is twice it, and both deployments are correct because the whole-axis
    contract's rotation does not depend on the slot.  An engine that read it
    here would refuse one of them.  Where the rotation *is* partial the slot is
    read and checked, which is what the other tests in this section cover.
    """
    rng = np.random.default_rng(61)
    width = 8
    values = random_bf16(rng, (2, width))
    coefficients = random_bf16(rng, (2 * width,), scale=0.5)
    numeric = harness.numeric(
        contract="qwen3_rope_fp32_bf16_v1",
        input_dtype=DType.BF16,
        output_dtype=DType.BF16,
    )
    output = harness.output_view((2, width), DType.BF16)
    operator = harness.operator(
        engine_family=Major.VECTOR,
        engine_sub=Vector.ROPE,
        inputs=[
            harness.const_view(values, DType.BF16),
            harness.const_view(coefficients, DType.BF16),
        ],
        outputs=[output],
        aux=[2 * width],
        numeric_profile_id=numeric,
    )
    harness.run(Major.VECTOR, Vector.ROPE, operator)
    np.testing.assert_array_equal(
        harness.result(output), oracle_rope(values, coefficients)
    )


def test_rope_refuses_a_numeric_profile_naming_no_rotary_contract(
    harness: Harness,
) -> None:
    rng = np.random.default_rng(67)
    width = 8
    values = random_bf16(rng, (2, width))
    coefficients = random_bf16(rng, (2 * width,), scale=0.5)
    numeric = harness.numeric(
        contract="some_other_rope_v1",
        input_dtype=DType.BF16,
        output_dtype=DType.BF16,
    )
    operator = harness.operator(
        engine_family=Major.VECTOR,
        engine_sub=Vector.ROPE,
        inputs=[
            harness.const_view(values, DType.BF16),
            harness.const_view(coefficients, DType.BF16),
        ],
        outputs=[harness.output_view((2, width), DType.BF16)],
        numeric_profile_id=numeric,
    )
    with pytest.raises(EngineError, match="names no rotary contract"):
        harness.run(Major.VECTOR, Vector.ROPE, operator)


# ---------------------------------------------------------------------------
# VECTOR.ADD and VECTOR.SILU_MUL
# ---------------------------------------------------------------------------
def test_add_matches_the_exact_reference(harness: Harness) -> None:
    rng = np.random.default_rng(37)
    left = random_bf16(rng, (2, 6))
    right = random_bf16(rng, (2, 6))
    numeric = harness.numeric(
        contract="bf16_add_rne_v1", input_dtype=DType.BF16, output_dtype=DType.BF16
    )
    output = harness.output_view((2, 6), DType.BF16)
    operator = harness.operator(
        engine_family=Major.VECTOR,
        engine_sub=Vector.ADD,
        inputs=[
            harness.const_view(left, DType.BF16),
            harness.const_view(right, DType.BF16),
        ],
        outputs=[output],
        numeric_profile_id=numeric,
    )
    harness.run(Major.VECTOR, Vector.ADD, operator)

    expected = exact_bf16_add(
        [tuple(int(c) for c in row) for row in left],
        [tuple(int(c) for c in row) for row in right],
    )
    np.testing.assert_array_equal(
        harness.result(output), np.asarray(expected.values, dtype=np.uint16)
    )
    assert harness.counters["vector.conversions"] == 12


def test_silu_mul_matches_the_exact_reference_and_exposes_the_activation(
    harness: Harness,
) -> None:
    rng = np.random.default_rng(41)
    gate = random_bf16(rng, (2, 5), scale=2.0)
    up = random_bf16(rng, (2, 5))
    numeric = harness.numeric(
        contract="qwen3_silu_mul_bf16_v1",
        input_dtype=DType.BF16,
        output_dtype=DType.BF16,
    )
    output = harness.output_view((2, 5), DType.BF16)
    activation = harness.output_view((2, 5), DType.BF16)
    operator = harness.operator(
        engine_family=Major.VECTOR,
        engine_sub=Vector.SILU_MUL,
        inputs=[
            harness.const_view(gate, DType.BF16),
            harness.const_view(up, DType.BF16),
        ],
        outputs=[output, activation],
        numeric_profile_id=numeric,
    )
    harness.run(Major.VECTOR, Vector.SILU_MUL, operator)

    expected = exact_silu_mul(
        [tuple(int(c) for c in row) for row in gate],
        [tuple(int(c) for c in row) for row in up],
    )
    np.testing.assert_array_equal(
        harness.result(output), np.asarray(expected.values, dtype=np.uint16)
    )
    np.testing.assert_array_equal(
        harness.result(activation),
        np.asarray(expected.activation_values, dtype=np.uint16),
    )
    assert harness.counters["vector.activation_elements"] == 10


def test_silu_mul_refuses_the_unspecified_three_operand_form(
    harness: Harness,
) -> None:
    rng = np.random.default_rng(43)
    numeric = harness.numeric(
        contract="qwen3_silu_mul_bf16_v1",
        input_dtype=DType.BF16,
        output_dtype=DType.BF16,
    )
    operator = harness.operator(
        engine_family=Major.VECTOR,
        engine_sub=Vector.SILU_MUL,
        inputs=[
            harness.const_view(random_bf16(rng, (1, 4)), DType.BF16),
            harness.const_view(random_bf16(rng, (1, 4)), DType.BF16),
            harness.const_view(random_bf16(rng, (1, 4)), DType.BF16),
        ],
        outputs=[harness.output_view((1, 4), DType.BF16)],
        numeric_profile_id=numeric,
    )
    with pytest.raises(EngineError, match="three-operand"):
        harness.run(Major.VECTOR, Vector.SILU_MUL, operator)


# ---------------------------------------------------------------------------
# VECTOR.CONVERT
# ---------------------------------------------------------------------------
def test_convert_widens_bf16_to_binary32(harness: Harness) -> None:
    rng = np.random.default_rng(47)
    values = random_bf16(rng, (2, 4))
    numeric = harness.numeric(
        contract="bf16_to_fp32_exact_v1",
        input_dtype=DType.BF16,
        output_dtype=DType.FP32,
    )
    output = harness.output_view((2, 4), DType.FP32)
    operator = harness.operator(
        engine_family=Major.VECTOR,
        engine_sub=Vector.CONVERT,
        inputs=[harness.const_view(values, DType.BF16)],
        outputs=[output],
        numeric_profile_id=numeric,
    )
    harness.run(Major.VECTOR, Vector.CONVERT, operator)
    np.testing.assert_array_equal(harness.result(output), widen_bf16(values))


def test_convert_narrows_binary32_to_bf16_with_ties_to_even(
    harness: Harness,
) -> None:
    # 1.0 + half an ulp of BF16 ties to even, 3 ulps rounds up.
    values = np.array([[1.00390625, 1.01171875]], dtype=np.float32)
    numeric = harness.numeric(
        contract="fp32_to_bf16_rne_v1",
        input_dtype=DType.FP32,
        output_dtype=DType.BF16,
    )
    output = harness.output_view((1, 2), DType.BF16)
    operator = harness.operator(
        engine_family=Major.VECTOR,
        engine_sub=Vector.CONVERT,
        inputs=[harness.const_view(values, DType.FP32)],
        outputs=[output],
        numeric_profile_id=numeric,
    )
    harness.run(Major.VECTOR, Vector.CONVERT, operator)
    produced = harness.result(output)
    expected = [
        exact.binary32_bits_to_bf16_rne(int(v.view(np.uint32))).code
        for v in values[0]
    ]
    np.testing.assert_array_equal(produced[0], np.asarray(expected, dtype=np.uint16))
    assert harness.counters["vector.conversions"] == 2


def test_convert_dequantises_a_block_scaled_tensor(harness: Harness) -> None:
    rng = np.random.default_rng(53)
    width, blocks = 16, 2
    codes = rng.integers(0, 0x7E, size=(2, width), dtype=np.uint8)
    scales = rng.integers(120, 132, size=(2, blocks), dtype=np.uint8)
    numeric = harness.numeric(
        contract="fp8_e4m3fn_e8m0_to_fp32_v1",
        input_dtype=DType.FP8_E4M3FN,
        second_input_dtype=DType.E8M0_SCALE,
        output_dtype=DType.FP32,
    )
    output = harness.output_view((2, width), DType.FP32)
    operator = harness.operator(
        engine_family=Major.VECTOR,
        engine_sub=Vector.CONVERT,
        inputs=[
            harness.const_view(codes, DType.FP8_E4M3FN),
            harness.const_view(scales, DType.E8M0_SCALE),
        ],
        outputs=[output],
        numeric_profile_id=numeric,
    )
    harness.run(Major.VECTOR, Vector.CONVERT, operator)

    block = width // blocks
    produced = harness.result(output)
    for row in range(2):
        for index in range(width):
            value = exact.decode_e4m3fn(int(codes[row, index]))
            scale = exact.decode_e8m0(int(scales[row, index // block]))
            assert value.value is not None and scale.value is not None
            expected = exact.encode_binary32_rne(value.value * scale.value)
            assert int(produced[row, index].view(np.uint32)) == expected


def test_convert_quantises_a_bf16_block_exactly(harness: Harness) -> None:
    rng = np.random.default_rng(59)
    width, blocks = 16, 2
    values = random_bf16(rng, (2, width), scale=3.0)
    numeric = harness.numeric(
        contract="bf16_to_fp8_e4m3fn_e8m0_v1",
        input_dtype=DType.BF16,
        output_dtype=DType.FP8_E4M3FN,
    )
    codes = harness.output_view((2, width), DType.FP8_E4M3FN)
    scales = harness.output_view((2, blocks), DType.E8M0_SCALE)
    operator = harness.operator(
        engine_family=Major.VECTOR,
        engine_sub=Vector.CONVERT,
        inputs=[harness.const_view(values, DType.BF16)],
        outputs=[codes, scales],
        numeric_profile_id=numeric,
    )
    harness.run(Major.VECTOR, Vector.CONVERT, operator)

    block = width // blocks
    produced_codes = harness.result(codes)
    produced_scales = harness.result(scales)
    for row in range(2):
        for index in range(blocks):
            expected = exact.quantize_bf16_activation_block(
                int(code) for code in values[row, index * block : (index + 1) * block]
            )
            assert int(produced_scales[row, index]) == expected.scale_code
            np.testing.assert_array_equal(
                produced_codes[row, index * block : (index + 1) * block],
                np.asarray(expected.value_codes, dtype=np.uint8),
            )


def test_convert_dispatches_the_declared_fp8_qdq_contract(harness: Harness) -> None:
    """The same FP8/E8M0 dtypes carry two intentionally different rules."""
    from runtime.reference.quantization import fp8_qdq_bf16

    rng = np.random.default_rng(0xF8D0)
    width, blocks = 128, 2
    values = random_bf16(rng, (2, width), scale=3.0)
    # The QDQ amax floor gives an all-zero block scale 2**-22; NUM-3.3 gives
    # it scale 1.  This makes the dispatch distinction deterministic instead
    # of relying on a random block landing on a scale-rounding edge.
    values[0, :64] = 0
    numeric = harness.numeric(
        contract="quantization_fp8_qdq_bf16_quantize_v1",
        input_dtype=DType.BF16,
        output_dtype=DType.FP8_E4M3FN,
    )
    codes = harness.output_view((2, width), DType.FP8_E4M3FN)
    scales = harness.output_view((2, blocks), DType.E8M0_SCALE)
    operator = harness.operator(
        engine_family=Major.VECTOR,
        engine_sub=Vector.CONVERT,
        inputs=[harness.const_view(values, DType.BF16)],
        outputs=[codes, scales],
        numeric_profile_id=numeric,
    )
    harness.run(Major.VECTOR, Vector.CONVERT, operator)

    expected = fp8_qdq_bf16(
        tuple(tuple(int(code) for code in row) for row in values)
    )
    produced_codes = harness.result(codes)
    produced_scales = harness.result(scales)
    np.testing.assert_array_equal(
        produced_codes, np.asarray(expected.e4m3fn_codes, dtype=np.uint8)
    )
    np.testing.assert_array_equal(
        produced_scales, np.asarray(expected.scale_codes, dtype=np.uint8)
    )

    generic_zero = exact.quantize_bf16_activation_block([0] * 64)
    assert int(produced_scales[0, 0]) != generic_zero.scale_code


def test_convert_quantises_a_bf16_block_into_packed_mxfp4(harness: Harness) -> None:
    """``quantization_fp4_qdq_bf16_quantize_v1`` end to end, including the write.

    The engine had no MXFP4 quantiser at all -- ``_convert_quantize`` required
    the code output to be E4M3FN -- and 4-bit views were read-only besides, so
    even a correct quantiser had nowhere to put its answer.  This exercises
    both: the codes come out equal to the reference block by block, and they
    arrive in the object packed two per byte, low nibble first, which is the
    order the reader already assumed.
    """
    rng = np.random.default_rng(0x4D58)
    width, blocks = 64, 2
    values = random_bf16(rng, (2, width), scale=3.0)
    numeric = harness.numeric(
        contract="quantization_fp4_qdq_bf16_quantize_v1",
        input_dtype=DType.BF16,
        output_dtype=DType.MXFP4_E2M1,
    )
    codes = harness.output_view((2, width), DType.MXFP4_E2M1)
    scales = harness.output_view((2, blocks), DType.E8M0_SCALE)
    operator = harness.operator(
        engine_family=Major.VECTOR,
        engine_sub=Vector.CONVERT,
        inputs=[harness.const_view(values, DType.BF16)],
        outputs=[codes, scales],
        numeric_profile_id=numeric,
    )
    harness.run(Major.VECTOR, Vector.CONVERT, operator)

    from runtime.reference.quantization import (
        FP4_AMAX_FLOOR,
        FP4_MAXIMUM,
        _BINARY32_RECIPROCAL_SIX,
        _ceil_log2,
        _finite_bf16_matrix,
        _power_of_two,
    )

    produced_codes = harness.result(codes)
    produced_scales = harness.result(scales)
    block = width // blocks
    rows = _finite_bf16_matrix(tuple(tuple(int(c) for c in r) for r in values))
    for row in range(2):
        for index in range(blocks):
            span = rows[row][index * block : (index + 1) * block]
            maximum = max(max(abs(v) for v in span), FP4_AMAX_FLOOR)
            ratio = exact.decode_binary32(
                exact.binary32_multiply(
                    exact.encode_binary32_rne(maximum), _BINARY32_RECIPROCAL_SIX
                )
            )
            exponent = _ceil_log2(ratio.value)
            assert int(produced_scales[row, index]) == exponent + 127
            scale = exact.encode_binary32_rne(_power_of_two(exponent))
            for offset, value in enumerate(span):
                quotient = exact.decode_binary32(
                    exact.binary32_divide(exact.encode_binary32_rne(value), scale)
                )
                clamped = max(-FP4_MAXIMUM, min(FP4_MAXIMUM, quotient.value))
                expected = exact.encode_e2m1_rne(clamped).code
                assert int(produced_codes[row, index * block + offset]) == expected

    # The nibbles are packed, not one per byte: the object is half the element
    # count, and reading it as pairs is what the MXFP4 reader already does.
    object_id, dims, _ = harness.outputs[codes]
    assert harness.memory[object_id].size_bytes == (2 * width) // 2


def test_a_strided_four_bit_destination_is_refused_rather_than_aliased(
    harness: Harness,
) -> None:
    """Two elements share a byte, so a strided 4-bit write is an aliasing write."""
    from runtime.sim.memory import MemoryError_

    rng = np.random.default_rng(0x4D59)
    values = random_bf16(rng, (2, 32), scale=1.0)
    numeric = harness.numeric(
        contract="quantization_fp4_qdq_bf16_quantize_v1",
        input_dtype=DType.BF16,
        output_dtype=DType.MXFP4_E2M1,
    )
    object_id = harness.scratch(64)
    codes = harness.builder.tensor_view(
        object_id=object_id,
        dtype=DType.MXFP4_E2M1,
        dims=[2, 32],
        strides=[64, 1],          # a row pitch wider than the row
        permissions=READ_WRITE,
    )
    scales = harness.output_view((2, 1), DType.E8M0_SCALE)
    operator = harness.operator(
        engine_family=Major.VECTOR,
        engine_sub=Vector.CONVERT,
        inputs=[harness.const_view(values, DType.BF16)],
        outputs=[codes, scales],
        numeric_profile_id=numeric,
    )
    with pytest.raises(MemoryError_, match="dense and row-major"):
        harness.run(Major.VECTOR, Vector.CONVERT, operator)


# ---------------------------------------------------------------------------
# VECTOR.SCALE
# ---------------------------------------------------------------------------
def test_scale_multiplies_two_operands_with_one_rounding(harness: Harness) -> None:
    rng = np.random.default_rng(61)
    values = random_bf16(rng, (2, 4))
    gains = random_bf16(rng, (4,), scale=0.5)
    numeric = harness.numeric(
        contract="bf16_mul_rne_v1", input_dtype=DType.BF16, output_dtype=DType.BF16
    )
    output = harness.output_view((2, 4), DType.BF16)
    operator = harness.operator(
        engine_family=Major.VECTOR,
        engine_sub=Vector.SCALE,
        inputs=[
            harness.const_view(values, DType.BF16),
            harness.const_view(gains, DType.BF16),
        ],
        outputs=[output],
        numeric_profile_id=numeric,
    )
    harness.run(Major.VECTOR, Vector.SCALE, operator)

    produced = harness.result(output)
    for row in range(2):
        for index in range(4):
            expected = exact.binary32_bits_to_bf16_rne(
                exact.binary32_multiply(
                    int(values[row, index]) << 16, int(gains[index]) << 16
                )
            ).code
            assert int(produced[row, index]) == expected


def test_scale_applies_the_declared_constant(harness: Harness) -> None:
    rng = np.random.default_rng(67)
    values = random_bf16(rng, (1, 4))
    constant_bits = int(np.float32(0.125).view(np.uint32))
    numeric = harness.numeric(
        contract="bf16_scale_rne_v1",
        input_dtype=DType.BF16,
        output_dtype=DType.BF16,
        scale_bits=constant_bits,
    )
    output = harness.output_view((1, 4), DType.BF16)
    operator = harness.operator(
        engine_family=Major.VECTOR,
        engine_sub=Vector.SCALE,
        inputs=[harness.const_view(values, DType.BF16)],
        outputs=[output],
        aux=[0],  # amendment A8: aux0 names the sub-case, not ``scale_bits``
        numeric_profile_id=numeric,
    )
    harness.run(Major.VECTOR, Vector.SCALE, operator)

    produced = harness.result(output)
    for index in range(4):
        expected = exact.binary32_bits_to_bf16_rne(
            exact.binary32_multiply(int(values[0, index]) << 16, constant_bits)
        ).code
        assert int(produced[0, index]) == expected


def test_scale_sub_case_two_is_the_logistic_sigmoid(harness: Harness) -> None:
    """Cross-checked against the frozen SiLU contract: silu(x) = x * sigmoid(x).

    Amendment A8: the sigmoid is selected by ``aux0 == 2``, not by a zero
    ``scale_bits`` -- which is what made a legitimate scale of zero
    unrepresentable.
    """
    rng = np.random.default_rng(71)
    gate = random_bf16(rng, (2, 5), scale=2.0)
    numeric = harness.numeric(
        contract="qwen3_sigmoid_bf16_v1",
        input_dtype=DType.BF16,
        output_dtype=DType.FP32,
    )
    output = harness.output_view((2, 5), DType.FP32)
    operator = harness.operator(
        engine_family=Major.VECTOR,
        engine_sub=Vector.SCALE,
        inputs=[harness.const_view(gate, DType.BF16)],
        outputs=[output],
        aux=[2],
        numeric_profile_id=numeric,
    )
    harness.run(Major.VECTOR, Vector.SCALE, operator)

    sigmoid = harness.result(output)
    ones = bf16(np.ones((2, 5), dtype=np.float32))
    frozen = exact_silu_mul(
        [tuple(int(c) for c in row) for row in gate],
        [tuple(int(c) for c in row) for row in ones],
    )
    for row in range(2):
        for index in range(5):
            silu = exact.binary32_bits_to_bf16_rne(
                exact.binary32_multiply(
                    int(gate[row, index]) << 16,
                    int(sigmoid[row, index].view(np.uint32)),
                )
            ).code
            assert silu == frozen.activation_values[row][index]
    assert harness.counters["vector.activation_elements"] == 10


# ---------------------------------------------------------------------------
# VECTOR.SOFTMAX
# ---------------------------------------------------------------------------
def oracle_softmax(codes: np.ndarray) -> list[list[int]]:
    """Exact row softmax with the eight-lane denominator order."""
    rows = []
    for row in codes:
        binary32 = [int(code) << 16 for code in row]
        maximum = max(binary32, key=lambda c: exact.decode_binary32(c).value)
        exponentials = [
            exact.binary32_exp_nonpositive(
                exact.binary32_add(code, 0 if maximum == 0 else maximum ^ 0x80000000)
            )
            for code in binary32
        ]
        denominator = exact.binary32_lanes8_sum(exponentials)
        inverse = exact.binary32_divide(0x3F800000, denominator)
        rows.append(
            [exact.binary32_multiply(item, inverse) for item in exponentials]
        )
    return rows


def test_softmax_matches_the_exact_eight_lane_contract(harness: Harness) -> None:
    rng = np.random.default_rng(73)
    values = random_bf16(rng, (2, 12), scale=3.0)
    numeric = harness.numeric(
        contract="fp32_softmax_lanes8_v1",
        input_dtype=DType.BF16,
        output_dtype=DType.FP32,
        reduction_order=ReductionOrder.BLOCKED_ASCENDING,
    )
    output = harness.output_view((2, 12), DType.FP32)
    operator = harness.operator(
        engine_family=Major.VECTOR,
        engine_sub=Vector.SOFTMAX,
        inputs=[harness.const_view(values, DType.BF16)],
        outputs=[output],
        numeric_profile_id=numeric,
    )
    harness.run(Major.VECTOR, Vector.SOFTMAX, operator)

    produced = harness.result(output)
    expected = oracle_softmax(values)
    for row in range(2):
        for index in range(12):
            assert int(produced[row, index].view(np.uint32)) == expected[row][index]
    assert harness.counters["vector.softmax_rows"] == 2


@pytest.mark.parametrize(
    "order",
    [
        ReductionOrder.SEQUENTIAL_ASCENDING,
        ReductionOrder.PAIRWISE_TREE,
        ReductionOrder.BLOCKED_ASCENDING,
    ],
)
def test_softmax_honours_every_declared_reduction_order(
    harness: Harness, order: ReductionOrder
) -> None:
    rng = np.random.default_rng(79)
    values = random_bf16(rng, (1, 9), scale=2.0)
    numeric = harness.numeric(
        contract="fp32_softmax_v1",
        input_dtype=DType.BF16,
        output_dtype=DType.FP32,
        reduction_order=order,
    )
    output = harness.output_view((1, 9), DType.FP32)
    operator = harness.operator(
        engine_family=Major.VECTOR,
        engine_sub=Vector.SOFTMAX,
        inputs=[harness.const_view(values, DType.BF16)],
        outputs=[output],
        numeric_profile_id=numeric,
    )
    harness.run(Major.VECTOR, Vector.SOFTMAX, operator)
    produced = harness.result(output)
    assert np.all(produced >= 0)
    assert abs(float(produced.sum()) - 1.0) < 1e-6


# ---------------------------------------------------------------------------
# VECTOR.SQRT_SOFTPLUS
# ---------------------------------------------------------------------------
def test_sqrt_softplus_matches_the_exact_operator(harness: Harness) -> None:
    values = np.array([[-4.0, -0.5, 0.0, 0.5, 4.0, 20.0]], dtype=np.float32)
    numeric = harness.numeric(
        contract="deepseek_v4_sqrt_softplus_v1",
        input_dtype=DType.FP32,
        output_dtype=DType.FP32,
    )
    output = harness.output_view((1, 6), DType.FP32)
    operator = harness.operator(
        engine_family=Major.VECTOR,
        engine_sub=Vector.SQRT_SOFTPLUS,
        inputs=[harness.const_view(values, DType.FP32)],
        outputs=[output],
        numeric_profile_id=numeric,
    )
    harness.run(Major.VECTOR, Vector.SQRT_SOFTPLUS, operator)

    produced = harness.result(output)
    for index, value in enumerate(values[0]):
        expected = binary32_sqrt_softplus_rne(int(value.view(np.uint32)))
        assert int(produced[0, index].view(np.uint32)) == expected
    assert harness.counters["vector.activation_elements"] == 6


# ---------------------------------------------------------------------------
# VECTOR.HADAMARD
# ---------------------------------------------------------------------------
def test_hadamard_matches_the_exact_reference(harness: Harness) -> None:
    rng = np.random.default_rng(83)
    values = random_bf16(rng, (2, HADAMARD_WIDTH), scale=0.5)
    numeric = harness.numeric(
        contract="deepseek_v4_hadamard_128_bf16_v1",
        input_dtype=DType.BF16,
        output_dtype=DType.BF16,
    )
    output = harness.output_view((2, HADAMARD_WIDTH), DType.BF16)
    operator = harness.operator(
        engine_family=Major.VECTOR,
        engine_sub=Vector.HADAMARD,
        inputs=[harness.const_view(values, DType.BF16)],
        outputs=[output],
        numeric_profile_id=numeric,
    )
    harness.run(Major.VECTOR, Vector.HADAMARD, operator)

    expected = hadamard_rotate_128_bf16(
        [tuple(int(code) for code in row) for row in values]
    )
    np.testing.assert_array_equal(
        harness.result(output), np.asarray(expected, dtype=np.uint16)
    )
    assert harness.counters["vector.elements"] == 2 * HADAMARD_WIDTH


def test_hadamard_rejects_an_unqualified_width(harness: Harness) -> None:
    rng = np.random.default_rng(89)
    numeric = harness.numeric(
        contract="deepseek_v4_hadamard_128_bf16_v1",
        input_dtype=DType.BF16,
        output_dtype=DType.BF16,
    )
    operator = harness.operator(
        engine_family=Major.VECTOR,
        engine_sub=Vector.HADAMARD,
        inputs=[harness.const_view(random_bf16(rng, (1, 64)), DType.BF16)],
        outputs=[harness.output_view((1, 64), DType.BF16)],
        numeric_profile_id=numeric,
    )
    with pytest.raises(EngineError, match="qualified transform"):
        harness.run(Major.VECTOR, Vector.HADAMARD, operator)


# ---------------------------------------------------------------------------
# Rounding mode
# ---------------------------------------------------------------------------
def test_engines_refuse_a_rounding_mode_they_do_not_implement(
    harness: Harness,
) -> None:
    rng = np.random.default_rng(97)
    numeric = harness.numeric(
        contract="bf16_add_rne_v1",
        input_dtype=DType.BF16,
        output_dtype=DType.BF16,
        rounding=RoundingMode.STOCHASTIC,
    )
    operator = harness.operator(
        engine_family=Major.VECTOR,
        engine_sub=Vector.ADD,
        inputs=[
            harness.const_view(random_bf16(rng, (1, 4)), DType.BF16),
            harness.const_view(random_bf16(rng, (1, 4)), DType.BF16),
        ],
        outputs=[harness.output_view((1, 4), DType.BF16)],
        numeric_profile_id=numeric,
    )
    with pytest.raises(EngineError) as error:
        harness.run(Major.VECTOR, Vector.ADD, operator)
    assert error.value.trap_class == 6


# ---------------------------------------------------------------------------
# End to end through the microsequencer
# ---------------------------------------------------------------------------
def test_a_device_transaction_executes_a_tensor_program(tmp_path: Path) -> None:
    """One compiled program, one transaction, engines reached only by dispatch."""
    rng = np.random.default_rng(101)
    rows, cols, depth = 2, 4, 8
    activations = random_bf16(rng, (rows, depth))
    weights = random_bf16(rng, (cols, depth))

    capability = fixture_capability()
    builder = DeploymentBuilder(
        target_id="engine-device-test",
        model_id="engine-device-test",
        backend="test",
        capability=capability,
    )
    builder.require(Feature.BF16_TENSOR)
    builder.topology(
        topology_class=TopologyClass.SINGLE_CHIP,
        node_count=1,
        hbm_bytes_per_node=capability.memory["hbm"]["bytes"],
        sram_bytes_per_node=capability.memory["sram"]["bytes"],
    )

    def constant(name: str, payload: bytes, storage_class: StorageClass) -> int:
        (tmp_path / name).write_bytes(payload)
        return builder.memory_object(
            storage_class=storage_class,
            size_bytes=len(payload),
            source=ObjectSource(
                "segments", len(payload), (Segment(name, 0, len(payload)),)
            ),
            permissions=IMMUTABLE,
        )

    activation_object = constant(
        "device_activations.bin", activations.tobytes(), StorageClass.SRAM
    )
    weight_object = constant("device_weights.bin", weights.tobytes(), StorageClass.ROM)
    output_object = builder.memory_object(
        storage_class=StorageClass.SRAM,
        size_bytes=rows * cols * 2,
        source=ObjectSource.zeros(rows * cols * 2),
        permissions=READ_WRITE,
    )
    numeric = builder.numeric(
        contract="bf16_bf16_fp32_sequential_rne_v1",
        input_dtype=DType.BF16,
        output_dtype=DType.BF16,
    )
    schedule = builder.schedule(
        engine_family=Major.TENSOR,
        tile_rows=rows,
        tile_cols=cols,
        tile_depth=depth,
        bank_mask=0b1,
        max_outstanding=1,
    )
    operator = builder.operator(
        engine_family=Major.TENSOR,
        engine_sub=Tensor.MATMUL,
        schedule_id=schedule,
        inputs=[
            builder.tensor_view(
                object_id=activation_object,
                dtype=DType.BF16,
                dims=[rows, depth],
                permissions=READ,
            ),
            builder.tensor_view(
                object_id=weight_object,
                dtype=DType.BF16,
                dims=[cols, depth],
                permissions=READ,
            ),
        ],
        outputs=[
            builder.tensor_view(
                object_id=output_object,
                dtype=DType.BF16,
                dims=[rows, cols],
                permissions=READ_WRITE,
            )
        ],
        numeric_profile_id=numeric,
    )
    builder.emit(Major.TENSOR, Tensor.MATMUL, descriptor_id=operator)
    builder.emit(Major.CONTROL, Control.COMPLETE)
    builder.entrypoint(entrypoint_id=0, first_instruction=0, phase=Phase.PREFILL)
    deployment = builder.finish()
    deployment.root = tmp_path

    device = Device(deployment, capability, root=tmp_path, verify=True)
    assert device.report is not None and device.report.admitted
    session = device.create_session()
    result = device.run_transaction(session, entrypoint_id=0, symbols={})

    assert result.status == 0, result.message
    assert result.trap_class == 0
    produced = np.frombuffer(
        device.memory[output_object].read(0, rows * cols * 2), dtype=np.uint16
    ).reshape(rows, cols)
    np.testing.assert_array_equal(produced, oracle_matmul(activations, weights))
    assert result.counters["engine.tensor.descriptors"] == 1
    assert result.counters["tensor.multiplications"] == rows * cols * depth
    assert result.counters["rom.bytes_read"] == cols * depth * 2


def test_the_engine_registry_covers_the_frozen_subopcodes() -> None:
    from runtime.sim.engine import implemented

    registered = implemented()
    for sub in (
        Tensor.MATMUL,
        Tensor.GROUPED_MATMUL,
        Tensor.ROUTED_MATMUL,
        Tensor.EMBED_LOOKUP,
    ):
        assert (int(Major.TENSOR), int(sub)) in registered
    for sub in (
        Vector.RMS_NORM,
        Vector.HEAD_RMS_NORM,
        Vector.ROPE,
        Vector.ADD,
        Vector.SILU_MUL,
        Vector.CONVERT,
        Vector.SCALE,
        Vector.SOFTMAX,
        Vector.SQRT_SOFTPLUS,
        Vector.HADAMARD,
    ):
        assert (int(Major.VECTOR), int(sub)) in registered
