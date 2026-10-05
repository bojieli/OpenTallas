"""Conformance tests for the ABI 3.0 execution backends.

Amendment A7 declares two contraction contracts and makes the *implementation
identity* of the blocked one part of every execution report.  These tests hold
that claim to the standard it states:

* both contracts produce the documented result on small shapes, checked against
  the exact ``fractions.Fraction`` scalar oracle in ``runtime/reference`` rather
  than against another NumPy expression;
* the sequential contract is identical on every backend, because it is defined
  to be reproducible on any machine;
* the blocked contract is bit-identical across repeats on one implementation,
  which is the whole of what it claims;
* TF32 is off, because it would silently truncate the binary32 significand;
* the implementation identity is recorded and names a library, a version and a
  device;
* an unavailable or unknown backend raises rather than resolving to another
  one, so a comparison can never straddle two associations.

The engine-level half checks that the numeric descriptor's contract, not a
global switch, decides which path runs -- and that both paths are reachable.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Sequence

import numpy as np
import pytest

import runtime.sim.engines.tensor as tensor_engine  # noqa: F401  (registers)
import runtime.sim.engines.vector as vector_engine  # noqa: F401  (registers)
from runtime.abi3.builder import NUMERIC_CONTRACT_REDUCTION_ORDER
from runtime.abi3.constants import (
    DType,
    Major,
    ReductionOrder,
    Tensor,
    Vector,
)
from runtime.reference import formats as exact
from runtime.sim import backend as backends
from runtime.sim.backend import (
    CONTRACT_BLOCKED,
    CONTRACT_DEEPSEEK_RMSNORM,
    CONTRACT_QWEN_RMSNORM,
    CONTRACT_SEQUENTIAL,
    BackendError,
    NumpyBackend,
)
from runtime.sim.engine import EngineError
from runtime.sim.formats import narrow_bf16_rne, widen_bf16
# The frozen engine-conformance harness lives beside this file.  pytest puts
# this directory on ``sys.path`` for a non-package test tree; the explicit
# insertion keeps a direct ``python -m pytest tests/sim/test_backend.py`` and an
# IDE runner working too.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_engines_tensor_vector import (  # noqa: E402  (path set above)
    Harness,
    bf16,
    random_bf16,
)

ALL_BACKENDS = ("numpy", "torch_cpu", "torch_cuda")


def exact_bf16(rng: np.random.Generator, shape: tuple[int, ...]) -> np.ndarray:
    """Small integer-valued BF16 operands.

    Their products and every partial sum are exactly representable in binary32,
    so *no* association can change the result.  That is what makes a single
    expected value legitimate for both contracts: any difference the test then
    sees is a real defect, not the association the blocked contract is allowed
    to choose.
    """
    return bf16(rng.integers(-4, 5, size=shape).astype(np.float32))


@pytest.fixture
def harness(tmp_path: Path) -> Harness:
    return Harness.create(tmp_path)


def available(name: str) -> bool:
    return backends.BACKENDS[name].is_available()[0]


def backend_or_skip(name: str):
    ok, reason = backends.BACKENDS[name].is_available()
    if not ok:
        pytest.skip(f"backend {name} unavailable: {reason}")
    return backends.get_backend(name)


@pytest.fixture(autouse=True)
def _restore_selection():
    """No test may leave a process-wide backend selected behind it."""
    yield
    backends.select_backend(None)


# ---------------------------------------------------------------------------
# Contracts on small shapes, against the exact scalar oracle
# ---------------------------------------------------------------------------
def _oracle_contraction(activations: np.ndarray, weights: np.ndarray) -> np.ndarray:
    """``[M,K] x [N,K]^T`` in exact rational arithmetic, rounded once.

    ``runtime.reference.formats`` decodes, multiplies and accumulates with
    :class:`fractions.Fraction`, so no host floating-point mode participates.
    Both contracts must agree with this whenever the operand count is small
    enough that no association can change the binary32 result.
    """
    rows, cols = activations.shape[0], weights.shape[0]
    out = np.empty((rows, cols), dtype=np.uint16)
    for row in range(rows):
        for col in range(cols):
            accumulator = 0
            for index in range(activations.shape[1]):
                product = exact.binary32_multiply(
                    int(activations[row, index]) << 16, int(weights[col, index]) << 16
                )
                accumulator = exact.binary32_add(accumulator, product)
            out[row, col] = exact.binary32_bits_to_bf16_rne(accumulator).code
    return out


@pytest.mark.parametrize("name", ALL_BACKENDS)
@pytest.mark.parametrize("contract", (CONTRACT_SEQUENTIAL, CONTRACT_BLOCKED))
def test_both_contracts_match_the_exact_oracle_on_small_shapes(
    name: str, contract: str
) -> None:
    backend = backend_or_skip(name)
    rng = np.random.default_rng(17)
    activations = exact_bf16(rng, (3, 6))
    weights = exact_bf16(rng, (5, 6))
    accumulator = backend.matmul_binary32(
        backend.widen_bf16(activations),
        backend.widen_bf16(weights),
        contract=contract,
    )
    codes = np.asarray(backend.fetch(backend.narrow_rne(accumulator).codes)).astype(
        np.uint16
    )
    np.testing.assert_array_equal(codes, _oracle_contraction(activations, weights))


@pytest.mark.parametrize("name", ALL_BACKENDS)
def test_the_sequential_contract_is_identical_on_every_backend(name: str) -> None:
    """It is defined as reproducible on any machine, so it must not move."""
    backend = backend_or_skip(name)
    rng = np.random.default_rng(23)
    activations = random_bf16(rng, (4, 64))
    weights = random_bf16(rng, (8, 64))
    reference = NumpyBackend()
    expected = reference.matmul_binary32(
        reference.widen_bf16(activations),
        reference.widen_bf16(weights),
        contract=CONTRACT_SEQUENTIAL,
    )
    produced = np.asarray(
        backend.fetch(
            backend.matmul_binary32(
                backend.widen_bf16(activations),
                backend.widen_bf16(weights),
                contract=CONTRACT_SEQUENTIAL,
            )
        )
    )
    np.testing.assert_array_equal(
        produced.view(np.uint32), np.asarray(expected).view(np.uint32)
    )


@pytest.mark.parametrize("name", ALL_BACKENDS)
def test_the_blocked_contract_is_bit_identical_across_repeats(name: str) -> None:
    """The one determinism claim the blocked contract actually makes."""
    backend = backend_or_skip(name)
    rng = np.random.default_rng(29)
    activations = random_bf16(rng, (8, 512))
    weights = random_bf16(rng, (64, 512))
    results = []
    for _ in range(4):
        accumulator = backend.matmul_binary32(
            backend.widen_bf16(activations),
            backend.widen_bf16(weights),
            contract=CONTRACT_BLOCKED,
        )
        results.append(
            np.ascontiguousarray(backend.fetch(accumulator), dtype=np.float32)
            .view(np.uint32)
            .copy()
        )
    for other in results[1:]:
        np.testing.assert_array_equal(results[0], other)


@pytest.mark.parametrize("name", ALL_BACKENDS)
def test_narrowing_reproduces_the_frozen_bf16_conversion(name: str) -> None:
    """Including subnormals, ties, negative zero and the saturation clamp."""
    backend = backend_or_skip(name)
    rng = np.random.default_rng(31)
    bits = rng.integers(0, 1 << 32, size=20000, dtype=np.uint64).astype(np.uint32)
    values = bits.view(np.float32)
    values = np.ascontiguousarray(values[np.isfinite(values)][:16384]).reshape(1, -1)
    expected, expected_saturations = narrow_bf16_rne(values)
    produced = backend.narrow_rne(values)
    np.testing.assert_array_equal(
        np.asarray(backend.fetch(produced.codes)).astype(np.uint16), expected
    )
    assert produced.saturations == expected_saturations


@pytest.mark.parametrize("name", ALL_BACKENDS)
def test_widening_bf16_is_exact_and_round_trips(name: str) -> None:
    backend = backend_or_skip(name)
    codes = np.arange(0, 0x7F80, 7, dtype=np.uint16).reshape(1, -1)
    widened = backend.widen_bf16(codes)
    np.testing.assert_array_equal(
        np.asarray(backend.fetch(widened), dtype=np.float32), widen_bf16(codes)
    )
    back = np.asarray(backend.fetch(backend.narrow_rne(widened).codes)).astype(
        np.uint16
    )
    np.testing.assert_array_equal(back, codes)


# ---------------------------------------------------------------------------
# Fail-closed behaviour
# ---------------------------------------------------------------------------
def test_an_unknown_backend_name_raises() -> None:
    with pytest.raises(BackendError) as error:
        backends.get_backend("cuda-graph-magic")
    assert "unknown execution backend" in str(error.value)


def test_an_unavailable_backend_fails_closed_rather_than_falling_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No silent substitution: a comparison must not straddle two associations."""
    backends.reset_backends()
    monkeypatch.setattr(
        backends.TorchCudaBackend,
        "is_available",
        classmethod(lambda cls: (False, "no CUDA device is visible")),
    )
    with pytest.raises(BackendError) as error:
        backends.get_backend("torch_cuda")
    message = str(error.value)
    assert "unavailable" in message and "no CUDA device is visible" in message
    assert "fails closed" in message
    backends.reset_backends()


@pytest.mark.parametrize("name", ALL_BACKENDS)
def test_an_unknown_contract_raises_instead_of_choosing_an_association(
    name: str,
) -> None:
    backend = backend_or_skip(name)
    operand = backend.widen_bf16(np.zeros((2, 2), dtype=np.uint16))
    for contract in ("", "bf16_bf16_fp32_whatever_v9", CONTRACT_QWEN_RMSNORM):
        with pytest.raises(BackendError) as error:
            backend.matmul_binary32(operand, operand, contract=contract)
        assert "not a contraction contract" in str(error.value)


@pytest.mark.parametrize("name", ALL_BACKENDS)
def test_an_unknown_elementwise_operation_raises(name: str) -> None:
    backend = backend_or_skip(name)
    with pytest.raises(BackendError):
        backend.elementwise("arctangent", np.zeros((2,), dtype=np.float32))


@pytest.mark.parametrize("name", ALL_BACKENDS)
def test_an_unimplemented_reduction_order_raises(name: str) -> None:
    backend = backend_or_skip(name)
    with pytest.raises(BackendError):
        backend.reduce_sum(np.zeros((1, 4), dtype=np.float32), order=99)


# ---------------------------------------------------------------------------
# TF32 and the implementation identity
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("name", ("torch_cpu", "torch_cuda"))
def test_tf32_is_off(name: str) -> None:
    """TF32 truncates the significand to 10 bits inside the matmul."""
    backend = backend_or_skip(name)
    torch = backend.torch
    assert torch.backends.cuda.matmul.allow_tf32 is False
    assert torch.backends.cudnn.allow_tf32 is False
    assert torch.get_float32_matmul_precision() == "highest"
    identity = backend.implementation_identity()
    assert identity["flags"]["torch.backends.cuda.matmul.allow_tf32"] is False


@pytest.mark.parametrize("name", ("torch_cpu", "torch_cuda"))
def test_a_tf32_enabled_context_is_refused(name: str) -> None:
    """The flag is re-read before every contraction, never assumed."""
    backend = backend_or_skip(name)
    torch = backend.torch
    operand = backend.widen_bf16(np.zeros((2, 2), dtype=np.uint16))
    torch.backends.cuda.matmul.allow_tf32 = True
    try:
        with pytest.raises(BackendError) as error:
            backend.matmul_binary32(operand, operand, contract=CONTRACT_BLOCKED)
        assert "TF32" in str(error.value)
    finally:
        torch.backends.cuda.matmul.allow_tf32 = False
    # And it works again once the context is legal.
    backend.matmul_binary32(operand, operand, contract=CONTRACT_BLOCKED)


@pytest.mark.parametrize("name", ALL_BACKENDS)
def test_the_implementation_identity_names_library_version_and_device(
    name: str,
) -> None:
    backend = backend_or_skip(name)
    identity = backend.implementation_identity()
    for field in ("backend", "library", "library_version", "device", "device_name"):
        assert identity[field], f"{name} identity is missing {field}"
    assert identity["backend"] == name
    assert identity["blocked_association"]
    assert isinstance(identity["flags"], dict)


def test_executed_association_manifest_binds_shapes_counts_and_identity() -> None:
    backend = NumpyBackend()
    backend.reset_executed_associations()
    left = backend.widen_bf16(np.zeros((3, 7), dtype=np.uint16))
    weights_a = backend.widen_bf16(np.zeros((5, 7), dtype=np.uint16))
    weights_b = backend.widen_bf16(np.zeros((2, 7), dtype=np.uint16))
    for _ in range(2):
        backend.matmul_binary32(left, weights_a, contract=CONTRACT_BLOCKED)
    backend.matmul_binary32(left, weights_b, contract=CONTRACT_BLOCKED)
    # The portable sequential contract is not an implementation-defined
    # association and therefore does not enter the blocked manifest.
    backend.matmul_binary32(left, weights_b, contract=CONTRACT_SEQUENTIAL)

    manifest = backend.executed_association_manifest()
    assert manifest["schema"] == "opentallas.abi3.executed_association.v1"
    assert manifest["association_policy"] == (
        "implementation_and_executed_shape_pinned"
    )
    assert manifest["blocked_call_count"] == 3
    assert manifest["distinct_association_count"] == 2
    assert manifest["implementation_identity"]["backend"] == "numpy"
    assert manifest["entries"] == [
        {
            "numeric_contract": CONTRACT_BLOCKED,
            "activation_shape": [3, 7],
            "weight_shape": [2, 7],
            "output_shape": [3, 2],
            "call_count": 1,
        },
        {
            "numeric_contract": CONTRACT_BLOCKED,
            "activation_shape": [3, 7],
            "weight_shape": [5, 7],
            "output_shape": [3, 5],
            "call_count": 2,
        },
    ]
    unsigned = dict(manifest)
    digest = unsigned.pop("manifest_sha256")
    encoded = json.dumps(
        unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")
    assert digest == hashlib.sha256(encoded).hexdigest()

    backend.reset_executed_associations()
    empty = backend.executed_association_manifest()
    assert empty["entries"] == []
    assert empty["blocked_call_count"] == 0


def test_the_cuda_identity_records_the_device_it_ran_on() -> None:
    backend = backend_or_skip("torch_cuda")
    identity = backend.implementation_identity()
    assert identity["device"].startswith("cuda:")
    assert identity["cuda_version"]
    assert identity["compute_capability"]
    assert identity["device_memory_bytes"]["total"] > 0


# ---------------------------------------------------------------------------
# Selection
# ---------------------------------------------------------------------------
def test_the_default_backend_is_numpy_and_is_always_available() -> None:
    backends.select_backend(None)
    os.environ.pop(backends.BACKEND_ENVIRONMENT_VARIABLE, None)
    assert backends.selected_backend_name() == "numpy"
    assert backends.get_backend().name == "numpy"
    assert "numpy" in backends.available_backends()


def test_the_environment_variable_selects_the_backend(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(backends.BACKEND_ENVIRONMENT_VARIABLE, "torch_cpu")
    backends.select_backend(None)
    if not available("torch_cpu"):
        pytest.skip("torch is unavailable")
    assert backends.get_backend().name == "torch_cpu"


def test_an_unknown_environment_variable_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(backends.BACKEND_ENVIRONMENT_VARIABLE, "abacus")
    backends.select_backend(None)
    with pytest.raises(BackendError):
        backends.get_backend()


def test_an_explicit_selection_overrides_the_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(backends.BACKEND_ENVIRONMENT_VARIABLE, "torch_cuda")
    backends.select_backend("numpy")
    assert backends.get_backend().name == "numpy"


def test_a_backend_scope_selects_inside_and_restores_outside() -> None:
    """Everything inside the scope must see it, engines included."""
    backends.select_backend("numpy")
    if not available("torch_cpu"):
        pytest.skip("torch is unavailable")
    with backends.backend_scope("torch_cpu") as scoped:
        assert scoped.name == "torch_cpu"
        assert backends.selected_backend_name() == "torch_cpu"
        assert backends.get_backend().name == "torch_cpu"
    assert backends.selected_backend_name() == "numpy"


def test_a_backend_scope_restores_the_selection_after_a_failure() -> None:
    backends.select_backend("numpy")
    if not available("torch_cpu"):
        pytest.skip("torch is unavailable")
    with pytest.raises(RuntimeError):
        with backends.backend_scope("torch_cpu"):
            raise RuntimeError("engine trapped")
    assert backends.selected_backend_name() == "numpy"


def test_backend_availability_reports_a_reason_for_every_backend() -> None:
    report = backends.backend_availability()
    assert set(report) == set(backends.backend_names())
    for name, record in report.items():
        assert isinstance(record["available"], bool)
        if not record["available"]:
            assert record["reason"], f"{name} is unavailable without a reason"


# ---------------------------------------------------------------------------
# Contract digests and the declared reduction order
# ---------------------------------------------------------------------------
def test_contract_digests_resolve_and_aliases_collapse() -> None:
    for name in (CONTRACT_SEQUENTIAL, CONTRACT_BLOCKED, CONTRACT_QWEN_RMSNORM):
        assert backends.contract_for_digest(backends.contract_digest(name)) == name
    alias = "runtime.reference.normalization.rms_norm_bf16"
    assert (
        backends.contract_for_digest(backends.contract_digest(alias))
        == CONTRACT_DEEPSEEK_RMSNORM
    )
    assert backends.contract_for_digest(backends.contract_digest("nothing")) == ""
    assert backends.contract_for_digest(None) == ""


def test_each_contraction_contract_fixes_its_reduction_order() -> None:
    assert backends.required_reduction_order(CONTRACT_SEQUENTIAL) == int(
        ReductionOrder.SEQUENTIAL_ASCENDING
    )
    assert backends.required_reduction_order(CONTRACT_BLOCKED) == int(
        ReductionOrder.BLOCKED_ASCENDING
    )
    assert backends.required_reduction_order("unnamed") is None


def test_the_rmsnorm_contracts_declare_a_pairwise_tree() -> None:
    """The frozen row sum is a balanced tree; the builder must not default it."""
    for contract in (CONTRACT_QWEN_RMSNORM, CONTRACT_DEEPSEEK_RMSNORM):
        assert NUMERIC_CONTRACT_REDUCTION_ORDER[contract] == ReductionOrder.PAIRWISE_TREE
        assert backends.required_reduction_order(contract) == int(
            ReductionOrder.PAIRWISE_TREE
        )


def test_the_builder_takes_an_unstated_reduction_order_from_the_contract(
    harness: Harness,
) -> None:
    numeric = harness.numeric(
        contract=CONTRACT_QWEN_RMSNORM,
        input_dtype=DType.BF16,
        output_dtype=DType.BF16,
    )
    descriptor = harness.builder.table[numeric]
    assert descriptor.payload["reduction_order"] == int(ReductionOrder.PAIRWISE_TREE)
    matmul = harness.numeric(
        contract=CONTRACT_SEQUENTIAL,
        input_dtype=DType.BF16,
        output_dtype=DType.BF16,
    )
    assert harness.builder.table[matmul].payload["reduction_order"] == int(
        ReductionOrder.SEQUENTIAL_ASCENDING
    )


# ---------------------------------------------------------------------------
# Engine dispatch: both paths reachable, chosen by the descriptor
# ---------------------------------------------------------------------------
def _matmul(
    harness: Harness,
    contract: str,
    activations: np.ndarray,
    weights: np.ndarray,
    *,
    reduction_order: ReductionOrder | None = None,
) -> int:
    numeric = harness.numeric(
        contract=contract,
        input_dtype=DType.BF16,
        output_dtype=DType.BF16,
        reduction_order=reduction_order,
    )
    output = harness.output_view(
        (activations.shape[0], weights.shape[0]), DType.BF16
    )
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
    harness.ctx = None  # rebind: objects added since the last run must be mapped
    harness.run(Major.TENSOR, Tensor.MATMUL, operator)
    return output


@pytest.mark.parametrize("name", ALL_BACKENDS)
@pytest.mark.parametrize("contract", (CONTRACT_SEQUENTIAL, CONTRACT_BLOCKED))
def test_the_tensor_engine_executes_the_contract_its_descriptor_names(
    harness: Harness, name: str, contract: str
) -> None:
    backend_or_skip(name)
    rng = np.random.default_rng(37)
    activations = exact_bf16(rng, (3, 8))
    weights = exact_bf16(rng, (4, 8))
    with backends.backend_scope(name):
        output = _matmul(harness, contract, activations, weights)
    np.testing.assert_array_equal(
        harness.result(output), _oracle_contraction(activations, weights)
    )


def test_a_blocked_descriptor_declaring_the_ordered_reduction_is_refused(
    harness: Harness,
) -> None:
    rng = np.random.default_rng(41)
    with pytest.raises(EngineError) as error:
        _matmul(
            harness,
            CONTRACT_BLOCKED,
            random_bf16(rng, (2, 4)),
            random_bf16(rng, (2, 4)),
            reduction_order=ReductionOrder.SEQUENTIAL_ASCENDING,
        )
    assert error.value.trap_class == 4
    assert "accumulates under" in str(error.value)


def test_an_unnamed_contract_never_acquires_a_blocked_association(
    harness: Harness,
) -> None:
    """An unnamed contract is executed under the exact ordered interpretation."""
    rng = np.random.default_rng(43)
    activations = exact_bf16(rng, (2, 6))
    weights = exact_bf16(rng, (3, 6))
    output = _matmul(harness, "some-emitter-private-name", activations, weights)
    np.testing.assert_array_equal(
        harness.result(output), _oracle_contraction(activations, weights)
    )


# ---------------------------------------------------------------------------
# The two RMSNorm contracts
# ---------------------------------------------------------------------------
def _rms_norm(
    harness: Harness, contract: str, values: np.ndarray, gains: np.ndarray
) -> int:
    from runtime.reference.tensor_accelerator_rmsnorm import EPSILON_CODE

    numeric = harness.numeric(
        contract=contract,
        input_dtype=DType.BF16,
        output_dtype=DType.BF16,
        epsilon_bits=EPSILON_CODE,
    )
    output = harness.output_view(values.shape, DType.BF16)
    operator = harness.operator(
        engine_family=Major.VECTOR,
        engine_sub=Vector.RMS_NORM,
        inputs=[
            harness.const_view(values, DType.BF16),
            harness.const_view(gains, DType.BF16),
        ],
        outputs=[output],
        numeric_profile_id=numeric,
    )
    harness.ctx = None  # rebind: objects added since the last run must be mapped
    harness.run(Major.VECTOR, Vector.RMS_NORM, operator)
    return output


@pytest.mark.parametrize("name", ALL_BACKENDS)
def test_the_deepseek_rmsnorm_contract_matches_its_exact_reference(
    harness: Harness, name: str
) -> None:
    """One rounding, at the output: the DeepSeek contract, not the Qwen one."""
    from runtime.reference.normalization import (
        RMS_NORM_EPSILON_BINARY32,
        rms_norm_bf16 as exact_deepseek_rms_norm,
    )

    backend_or_skip(name)
    rng = np.random.default_rng(47)
    values = random_bf16(rng, (3, 128))
    gains = random_bf16(rng, (128,), scale=0.5)
    from runtime.reference.tensor_accelerator_rmsnorm import EPSILON_CODE

    if EPSILON_CODE != RMS_NORM_EPSILON_BINARY32:
        pytest.skip("the two references pin different epsilon encodings")
    with backends.backend_scope(name):
        output = _rms_norm(harness, CONTRACT_DEEPSEEK_RMSNORM, values, gains)
    expected = exact_deepseek_rms_norm(
        [tuple(int(code) for code in row) for row in values],
        [int(code) for code in gains],
    )
    np.testing.assert_array_equal(
        harness.result(output), np.asarray(expected.output_codes, dtype=np.uint16)
    )


def test_the_qwen_rmsnorm_contract_matches_its_exact_reference(
    harness: Harness,
) -> None:
    from runtime.reference.tensor_accelerator_rmsnorm import (
        rms_norm_bf16 as exact_qwen_rms_norm,
    )

    rng = np.random.default_rng(53)
    values = random_bf16(rng, (3, 128))
    gains = random_bf16(rng, (128,), scale=0.5)
    output = _rms_norm(harness, CONTRACT_QWEN_RMSNORM, values, gains)
    expected = exact_qwen_rms_norm(
        [tuple(int(code) for code in row) for row in values],
        [int(code) for code in gains],
    )
    np.testing.assert_array_equal(
        harness.result(output), np.asarray(expected.values, dtype=np.uint16)
    )


def test_the_two_rmsnorm_contracts_actually_disagree(harness: Harness) -> None:
    """If they agreed there would be no reason to keep both names."""
    rng = np.random.default_rng(59)
    values = random_bf16(rng, (16, 256))
    gains = random_bf16(rng, (256,), scale=0.5)
    qwen = harness.result(_rms_norm(harness, CONTRACT_QWEN_RMSNORM, values, gains))
    deepseek = harness.result(
        _rms_norm(harness, CONTRACT_DEEPSEEK_RMSNORM, values, gains)
    )
    differing = int(np.count_nonzero(qwen != deepseek))
    assert differing > 0, "the two RMSNorm contracts must not be the same operation"
    distance = np.abs(qwen.astype(np.int32) - deepseek.astype(np.int32))
    assert int(distance.max()) <= 1, "they should differ by at most one ulp"


def test_an_unrecognised_rmsnorm_contract_is_refused(harness: Harness) -> None:
    """Silently picking one would corrupt whichever model did not get it."""
    rng = np.random.default_rng(61)
    with pytest.raises(EngineError) as error:
        _rms_norm(
            harness, "someone_elses_rmsnorm_v1", random_bf16(rng, (2, 128)),
            random_bf16(rng, (128,), scale=0.5),
        )
    assert error.value.trap_class == 4
    assert "no RMSNorm contract" in str(error.value)


def test_an_rmsnorm_declaring_the_ordered_reduction_is_refused(
    harness: Harness,
) -> None:
    from runtime.reference.tensor_accelerator_rmsnorm import EPSILON_CODE

    rng = np.random.default_rng(67)
    values = random_bf16(rng, (2, 128))
    gains = random_bf16(rng, (128,), scale=0.5)
    numeric = harness.numeric(
        contract=CONTRACT_QWEN_RMSNORM,
        input_dtype=DType.BF16,
        output_dtype=DType.BF16,
        epsilon_bits=EPSILON_CODE,
        reduction_order=ReductionOrder.SEQUENTIAL_ASCENDING,
    )
    operator = harness.operator(
        engine_family=Major.VECTOR,
        engine_sub=Vector.RMS_NORM,
        inputs=[
            harness.const_view(values, DType.BF16),
            harness.const_view(gains, DType.BF16),
        ],
        outputs=[harness.output_view(values.shape, DType.BF16)],
        numeric_profile_id=numeric,
    )
    with pytest.raises(EngineError) as error:
        harness.run(Major.VECTOR, Vector.RMS_NORM, operator)
    assert error.value.trap_class == 4
    assert "balanced tree" in str(error.value)


# ---------------------------------------------------------------------------
# VECTOR.SCALE sub-cases (amendment A8)
# ---------------------------------------------------------------------------
def _scale(
    harness: Harness,
    *,
    aux: Sequence[int] | None,
    values: np.ndarray,
    second: np.ndarray | None = None,
    scale_bits: int = 0,
) -> int:
    numeric = harness.numeric(
        contract="bf16_scale_rne_v1",
        input_dtype=DType.BF16,
        output_dtype=DType.BF16,
        scale_bits=scale_bits,
    )
    inputs = [harness.const_view(values, DType.BF16)]
    if second is not None:
        inputs.append(harness.const_view(second, DType.BF16))
    output = harness.output_view(values.shape, DType.BF16)
    operator = harness.operator(
        engine_family=Major.VECTOR,
        engine_sub=Vector.SCALE,
        inputs=inputs,
        outputs=[output],
        aux=list(aux) if aux is not None else (),
        numeric_profile_id=numeric,
    )
    harness.ctx = None  # rebind: objects added since the last run must be mapped
    harness.run(Major.VECTOR, Vector.SCALE, operator)
    return output


def test_a_scale_of_zero_is_representable(harness: Harness) -> None:
    """The bug amendment A8 fixes: ``scale_bits == 0`` meant "sigmoid"."""
    rng = np.random.default_rng(71)
    values = random_bf16(rng, (2, 4))
    output = _scale(harness, aux=[0], values=values, scale_bits=0)
    np.testing.assert_array_equal(
        harness.result(output), np.zeros_like(values, dtype=np.uint16)
    )


def test_scale_without_a_sub_case_and_one_operand_is_refused(
    harness: Harness,
) -> None:
    rng = np.random.default_rng(73)
    with pytest.raises(EngineError) as error:
        _scale(harness, aux=None, values=random_bf16(rng, (2, 4)), scale_bits=0)
    assert "aux_id_0" in str(error.value)


def test_an_undefined_scale_sub_case_is_refused(harness: Harness) -> None:
    rng = np.random.default_rng(79)
    with pytest.raises(EngineError) as error:
        _scale(harness, aux=[7], values=random_bf16(rng, (2, 4)))
    assert "sub-case 7 is not defined" in str(error.value)


def test_the_scale_sub_case_must_match_the_bound_operands(harness: Harness) -> None:
    rng = np.random.default_rng(83)
    values = random_bf16(rng, (2, 4))
    with pytest.raises(EngineError):
        _scale(harness, aux=[1], values=values)
    with pytest.raises(EngineError):
        _scale(harness, aux=[0], values=values, second=random_bf16(rng, (4,)))


def test_the_elementwise_sub_case_multiplies_the_second_operand(
    harness: Harness,
) -> None:
    rng = np.random.default_rng(89)
    values = random_bf16(rng, (2, 4))
    gains = random_bf16(rng, (4,), scale=0.5)
    output = _scale(harness, aux=[1], values=values, second=gains)
    produced = harness.result(output)
    for row in range(2):
        for index in range(4):
            expected = exact.binary32_bits_to_bf16_rne(
                exact.binary32_multiply(
                    int(values[row, index]) << 16, int(gains[index]) << 16
                )
            ).code
            assert int(produced[row, index]) == expected


# ---------------------------------------------------------------------------
# Counters
# ---------------------------------------------------------------------------
def test_the_vector_group_owns_its_saturation_and_exceptional_counters() -> None:
    from runtime.abi3.constants import CounterGroup, counter_id
    from runtime.sim.counters import COUNTERS, NAME_TO_ID

    for event, name in ((11, "vector.saturations"), (12, "vector.exceptional_values")):
        cid = counter_id(CounterGroup.VECTOR_REDUCTION, event)
        assert COUNTERS[cid] == name
        assert NAME_TO_ID[name] >> 24 == int(CounterGroup.VECTOR_REDUCTION)


def test_vector_saturation_is_counted_in_the_vector_group(harness: Harness) -> None:
    """It used to be dropped, or charged to the TENSOR group.

    The narrow band between the largest finite BF16 (about 3.3895e38) and the
    largest finite binary32 (about 3.4028e38) is exactly where a conversion
    saturates without the source ever leaving the binary32 range, so it isolates
    the saturation counter from the exceptional-value one.
    """
    source = np.full((1, 4), np.float32(3.4e38), dtype=np.float32)
    numeric = harness.numeric(
        contract="fp32_to_bf16_rne_v1",
        input_dtype=DType.FP32,
        output_dtype=DType.BF16,
    )
    output = harness.output_view((1, 4), DType.BF16)
    operator = harness.operator(
        engine_family=Major.VECTOR,
        engine_sub=Vector.CONVERT,
        inputs=[harness.const_view(source, DType.FP32)],
        outputs=[output],
        numeric_profile_id=numeric,
    )
    harness.run(Major.VECTOR, Vector.CONVERT, operator)
    counters = harness.ctx.counters.snapshot()
    assert counters.get("vector.saturations", 0) == 4
    assert "tensor.saturations" not in counters


def test_a_vector_exceptional_value_is_counted_in_the_vector_group(
    harness: Harness,
) -> None:
    source = np.full((1, 2), np.float32(np.inf), dtype=np.float32)
    numeric = harness.numeric(
        contract="fp32_to_bf16_rne_v1",
        input_dtype=DType.FP32,
        output_dtype=DType.BF16,
    )
    operator = harness.operator(
        engine_family=Major.VECTOR,
        engine_sub=Vector.CONVERT,
        inputs=[harness.const_view(source, DType.FP32)],
        outputs=[harness.output_view((1, 2), DType.BF16)],
        numeric_profile_id=numeric,
    )
    with pytest.raises(EngineError):
        harness.run(Major.VECTOR, Vector.CONVERT, operator)
    assert harness.ctx.counters.get("vector.exceptional_values") == 2


# ---------------------------------------------------------------------------
# Device placement
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("name", ALL_BACKENDS)
def test_a_view_reaches_the_device_without_a_host_widening(
    harness: Harness, name: str
) -> None:
    """The mapped BF16 codes cross the bus, not a widened binary32 copy."""
    backend = backend_or_skip(name)
    rng = np.random.default_rng(97)
    weights = random_bf16(rng, (8, 16))
    view_id = harness.const_view(weights, DType.BF16)
    harness.bind()
    view = harness.ctx.view(view_id)
    placed = harness.ctx.views.device_array(view, backend)
    fetched = np.asarray(backend.fetch(placed))
    assert fetched.dtype.itemsize == 2, "codes must cross at their storage width"
    np.testing.assert_array_equal(fetched.view(np.uint16), weights)


def test_the_host_backend_returns_the_mapping_itself(harness: Harness) -> None:
    """The zero-copy weight residency must survive the placement API."""
    rng = np.random.default_rng(101)
    weights = random_bf16(rng, (4, 8))
    view_id = harness.const_view(weights, DType.BF16)
    harness.bind()
    view = harness.ctx.view(view_id)
    backend = backends.get_backend("numpy")
    placed = harness.ctx.views.device_array(view, backend)
    assert isinstance(placed, np.ndarray)
    assert placed.base is not None or not placed.flags["OWNDATA"]
    np.testing.assert_array_equal(placed, harness.ctx.views.read_array(view))


def test_the_device_cache_is_off_unless_an_operator_opts_in(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The device is shared and the model does not fit; weights stream."""
    backend = backend_or_skip("torch_cuda")
    monkeypatch.delenv("OPENTALLAS_ABI3_DEVICE_CACHE_BYTES", raising=False)
    assert backend.device_cache_bytes() == 0
    monkeypatch.setenv("OPENTALLAS_ABI3_DEVICE_CACHE_BYTES", "1048576")
    assert backend.device_cache_bytes() > 0
    monkeypatch.setenv("OPENTALLAS_ABI3_DEVICE_CACHE_BYTES", "not-a-number")
    with pytest.raises(BackendError):
        backend.device_cache_bytes()


# ---------------------------------------------------------------------------
# The two schedules of the sequential contraction
# ---------------------------------------------------------------------------
# ``bf16_bf16_fp32_sequential_rne_v1`` fixes each output element's reduction:
# its own K products, formed exactly, accumulated in strictly ascending
# reduction index in binary32.  It fixes nothing about *which* output element is
# worked on when, and ``sequential_matmul_binary32`` uses that freedom: a K-last
# schedule that materialises ``[rows, cols, K]`` and lets ``np.add.accumulate``
# walk the contiguous reduction axis, and a K-major schedule that walks the
# reduction on the outside and forms one rank-1 plane of products per reduction
# index.  K-last pays no per-index dispatch and wins on a small tile; K-major
# vectorises the reduction and wins on a large one, measured at 4.6-5.7x at the
# DeepSeek dense shapes.
#
# The tests below are the reason that choice is takeable: the two schedules are
# differentially identical on raw binary32 codes, both answer to the exact
# rational oracle, and the mutations that would make either one a different
# association are caught.
def _schedule_operands(
    rng: np.random.Generator, shape: tuple[int, int], kind: str
) -> np.ndarray:
    """BF16-exact operands of three kinds, all representable without rounding."""
    if kind == "unit":
        return bf16(rng.normal(0.0, 1.0, shape).astype(np.float32))
    if kind == "wide":
        # Sixty binades of spread, so partial sums cross magnitudes and an
        # out-of-order accumulation would round differently.  The bound keeps
        # every product inside binary32 -- an operand pool that overflows would
        # test the refusal, not the association.
        scale = np.float32(2.0) ** rng.integers(-30, 30, shape).astype(np.float32)
        return bf16((rng.normal(0.0, 1.0, shape).astype(np.float32) * scale))
    if kind == "edge":
        pool = bf16(
            np.asarray(
                [
                    0.0,
                    -0.0,
                    1.0,
                    -1.0,
                    float(np.float32(2.0) ** -126),
                    -float(np.float32(2.0) ** -126),
                    float(np.float32(2.0) ** -140),
                    float(np.float32(2.0) ** -63),
                    float(np.float32(2.0) ** 30),
                    float(np.float32(2.0) ** 50),
                ],
                dtype=np.float32,
            )
        )
        return pool[rng.integers(0, pool.size, shape)]
    raise AssertionError(kind)


def _run_schedule(schedule, left: np.ndarray, right: np.ndarray) -> np.ndarray:
    output = np.empty((left.shape[0], right.shape[0]), dtype=np.float32)
    previous = np.seterr(over="ignore", invalid="ignore", under="ignore")
    try:
        schedule(
            np.ascontiguousarray(left, dtype=np.float32),
            np.ascontiguousarray(right, dtype=np.float32),
            output,
        )
    finally:
        np.seterr(**previous)
    return output


#: Shapes straddling the schedule threshold, including the DeepSeek-V4-Flash
#: dense and routed contraction shapes and the Qwen3-8B projection shape.
_SCHEDULE_SHAPES = (
    (1, 1, 1),
    (1, 1, 64),
    (1, 2048, 65),
    (2, 2048, 33),
    (3, 63, 64),
    (5, 65, 7),
    (8, 1024, 63),
    (9, 1023, 64),
    (13, 1025, 65),
    (16, 512, 128),
    (64, 64, 64),
    (104, 512, 129),
    (104, 1024, 64),
    (104, 2048, 33),
    (128, 65, 2),
    (257, 3, 513),
)


def test_the_two_sequential_schedules_are_bit_identical() -> None:
    """Same contract, two schedules, no bit between them.

    Every element's reduction is untouched by the schedule; only the order in
    which independent output elements are visited moves.  This is the check
    that says so on raw ``uint32`` codes rather than approximately, over shapes
    on both sides of the threshold and over operand pools chosen to make an
    out-of-order accumulation visible: sixty binades of spread, signed zeros,
    subnormals, and products that underflow.
    """
    rng = np.random.default_rng(0x5EED)
    compared = 0
    kmajor = klast = 0
    for rows, cols, depth in _SCHEDULE_SHAPES:
        for kind in ("unit", "wide", "edge"):
            left = _schedule_operands(rng, (rows, depth), kind)
            right = _schedule_operands(rng, (cols, depth), kind)
            widened_left = widen_bf16(left)
            widened_right = widen_bf16(right)
            k_last = _run_schedule(
                backends._sequential_k_last, widened_left, widened_right
            )
            k_major = _run_schedule(
                backends._sequential_k_major, widened_left, widened_right
            )
            dispatched = backends.sequential_matmul_binary32(
                widened_left, widened_right
            )
            np.testing.assert_array_equal(
                k_major.view(np.uint32), k_last.view(np.uint32),
                err_msg=f"{(rows, cols, depth)} {kind}",
            )
            np.testing.assert_array_equal(
                dispatched.view(np.uint32), k_last.view(np.uint32),
                err_msg=f"{(rows, cols, depth)} {kind}",
            )
            compared += 1
            tile = rows * min(cols, backends.SEQUENTIAL_KMAJOR_COL_TILE)
            if tile >= backends.SEQUENTIAL_KMAJOR_MIN_TILE:
                kmajor += 1
            else:
                klast += 1
    assert compared == len(_SCHEDULE_SHAPES) * 3
    # A differential that only ever exercised one schedule would pass without
    # having compared anything, so the coverage is asserted rather than hoped
    # for.
    assert kmajor > 0 and klast > 0, (kmajor, klast)


def test_the_k_major_schedule_answers_to_the_exact_rational_oracle() -> None:
    """Not just "the same as the other schedule" -- the same as the contract.

    The shape is above the threshold, so the dispatcher reaches K-major, and
    small enough that the ``fractions.Fraction`` oracle can enumerate it.
    """
    rng = np.random.default_rng(0x0AC1)
    activations = exact_bf16(rng, (9, 3))
    weights = exact_bf16(rng, (1024, 3))
    assert (
        activations.shape[0] * min(weights.shape[0], backends.SEQUENTIAL_KMAJOR_COL_TILE)
        >= backends.SEQUENTIAL_KMAJOR_MIN_TILE
    ), "this shape must reach the K-major schedule for the test to mean anything"
    accumulator = backends.sequential_matmul_binary32(
        widen_bf16(activations), widen_bf16(weights)
    )
    codes, _ = narrow_bf16_rne(accumulator)
    np.testing.assert_array_equal(codes, _oracle_contraction(activations, weights))


def test_the_schedule_threshold_cannot_change_a_bit(monkeypatch) -> None:
    """The threshold is a performance knob, so moving it must change nothing.

    Driving one shape through both settings is the direct statement that the
    dispatcher's choice is not load-bearing -- which is what makes it safe for
    a later measurement to move it.
    """
    rng = np.random.default_rng(0xB0A7)
    activations = widen_bf16(_schedule_operands(rng, (16, 96), "wide"))
    weights = widen_bf16(_schedule_operands(rng, (512, 96), "wide"))
    results = []
    for threshold in (0, 1 << 40):
        monkeypatch.setattr(backends, "SEQUENTIAL_KMAJOR_MIN_TILE", threshold)
        results.append(backends.sequential_matmul_binary32(activations, weights))
    monkeypatch.undo()
    np.testing.assert_array_equal(
        results[0].view(np.uint32), results[1].view(np.uint32)
    )
    for tile in (1, 7, 64, 1024):
        monkeypatch.setattr(backends, "SEQUENTIAL_KMAJOR_COL_TILE", tile)
        monkeypatch.setattr(backends, "SEQUENTIAL_KMAJOR_MIN_TILE", 0)
        np.testing.assert_array_equal(
            backends.sequential_matmul_binary32(activations, weights).view(np.uint32),
            results[0].view(np.uint32),
            err_msg=f"column tile {tile}",
        )
        monkeypatch.undo()


def test_reversing_the_k_major_reduction_is_caught() -> None:
    """The mutation the differential exists to refuse.

    Reversing the reduction index is still a sum of the same products, and it
    is a *different number* in binary32.  If this ever stops differing, the
    operand pool has gone soft and the differential above has stopped proving
    anything.
    """
    rng = np.random.default_rng(0xDEC0)
    left = widen_bf16(_schedule_operands(rng, (16, 512), "wide"))
    right = widen_bf16(_schedule_operands(rng, (512, 512), "wide"))
    expected = backends.sequential_matmul_binary32(left, right)

    rows, cols = left.shape[0], right.shape[0]
    observed = np.empty((rows, cols), dtype=np.float32)
    previous = np.seterr(over="ignore", invalid="ignore", under="ignore")
    try:
        for col_start in range(0, cols, backends.SEQUENTIAL_KMAJOR_COL_TILE):
            col_end = min(col_start + backends.SEQUENTIAL_KMAJOR_COL_TILE, cols)
            transposed = np.ascontiguousarray(right[col_start:col_end].T)
            accumulator = np.zeros((rows, col_end - col_start), dtype=np.float32)
            products = np.empty_like(accumulator)
            for index in reversed(range(left.shape[1])):  # the mutation
                np.multiply(
                    left[:, index, None],
                    transposed[index][None, :],
                    out=products,
                    dtype=np.float32,
                )
                products[products == 0] = np.float32(0.0)
                np.add(accumulator, products, out=accumulator, dtype=np.float32)
            observed[:, col_start:col_end] = accumulator
    finally:
        np.seterr(**previous)
    assert not np.array_equal(expected.view(np.uint32), observed.view(np.uint32))


def test_a_contraction_that_overflows_names_the_product_not_the_sum() -> None:
    """Both schedules must refuse the same operand with the same message.

    A product that leaves the binary32 range is a different fault from a sum
    that does, and folding one into the other would report the wrong cause.
    The K-major schedule reaches its finiteness checks in a different order
    from the K-last one -- per reduction index rather than per tile -- so the
    two shapes here drive one case through each.
    """

    def contraction(rows: int, cols: int, left_value: float, right_value: float):
        left = bf16(np.full((rows, 4), left_value, dtype=np.float32))
        right = bf16(np.full((cols, 4), right_value, dtype=np.float32))
        return widen_bf16(left), widen_bf16(right)

    # 2**120 x 2**120 = 2**240: every product is out of range.
    for rows, cols in ((16, 1024), (1, 2)):
        tile = rows * min(cols, backends.SEQUENTIAL_KMAJOR_COL_TILE)
        assert (tile >= backends.SEQUENTIAL_KMAJOR_MIN_TILE) == (rows == 16)
        with pytest.raises(BackendError, match="product left the binary32 range"):
            backends.sequential_matmul_binary32(
                *contraction(rows, cols, float(np.float32(2.0) ** 120),
                             float(np.float32(2.0) ** 120))
            )
    # 2**100 x 2**27 = 2**127, finite; four of them sum past the binary32 top.
    for rows, cols in ((16, 1024), (1, 2)):
        with pytest.raises(BackendError, match="sum left the binary32 range"):
            backends.sequential_matmul_binary32(
                *contraction(rows, cols, float(np.float32(2.0) ** 100),
                             float(np.float32(2.0) ** 27))
            )
