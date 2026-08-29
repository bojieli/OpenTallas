"""Conformance tests for the ABI 3.0 TENSOR and VECTOR engines.

Every numeric assertion compares the engine against an *independent* oracle:
either the exact ``fractions.Fraction`` scalar semantics in
``runtime/reference`` -- which decode, multiply and round without any host
floating-point mode -- or a straightforward NumPy computation that does not
share code with the engine.  Counter assertions check the frozen registry names
the engines are allowed to use.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
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
from runtime.abi3.descriptors import LayoutClass, Phase
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
from runtime.sim.device import Device
from runtime.sim.engine import EngineContext, EngineError, dispatch
from runtime.sim.formats import narrow_bf16_rne, widen_bf16
from runtime.sim.memory import DeviceMemory, ViewResolver

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
        self, payload: bytes, storage_class: StorageClass = StorageClass.HBM
    ) -> int:
        self.files += 1
        name = f"object{self.files}.bin"
        (self.root / name).write_bytes(payload)
        return self.builder.memory_object(
            storage_class=storage_class,
            size_bytes=len(payload),
            source=ObjectSource(
                "segments", len(payload), (Segment(name, 0, len(payload)),)
            ),
            permissions=IMMUTABLE,
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
    ) -> int:
        payload = np.ascontiguousarray(array).tobytes()
        object_id = self.constant(payload, storage_class)
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
        }[dtype]
        count = int(np.prod(dims))
        object_id = self.scratch(count * numpy_dtype.itemsize, storage_class)
        view = self.builder.tensor_view(
            object_id=object_id,
            dtype=dtype,
            dims=list(dims),
            permissions=READ_WRITE,
        )
        self.outputs[view] = (object_id, tuple(int(d) for d in dims), numpy_dtype)
        return view

    def numeric(self, **kwargs: Any) -> int:
        kwargs.setdefault("contract", "engine-test")
        return self.builder.numeric(**kwargs)

    def operator(self, **kwargs: Any) -> int:
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
        payload = self.memory[object_id].read(
            0, int(np.prod(dims)) * numpy_dtype.itemsize
        )
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
        numeric_profile_id=numeric,
    )
    harness.run(Major.VECTOR, Vector.SCALE, operator)

    produced = harness.result(output)
    for index in range(4):
        expected = exact.binary32_bits_to_bf16_rne(
            exact.binary32_multiply(int(values[0, index]) << 16, constant_bits)
        ).code
        assert int(produced[0, index]) == expected


def test_scale_without_a_constant_is_the_logistic_sigmoid(harness: Harness) -> None:
    """Cross-checked against the frozen SiLU contract: silu(x) = x * sigmoid(x)."""
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
    operator = builder.operator(
        engine_family=Major.TENSOR,
        engine_sub=Tensor.MATMUL,
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
