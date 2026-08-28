from __future__ import annotations

from dataclasses import asdict
import hashlib
from pathlib import Path

import numpy as np
import pytest

from runtime.reference.formats import (
    NumericReferenceError,
    binary32_exp_nonpositive,
    binary32_lanes8_sum,
)
from runtime.reference.tensor_accelerator_attention import (
    CAUSAL_MASK_BF16_CODE as REFERENCE_MASK,
    NUMERIC_CONTRACT as REFERENCE_CONTRACT,
    SCALE_BF16_CODE as REFERENCE_SCALE,
    AttentionReferenceError,
    abort_kv_group as reference_abort_group,
    commit_kv_append as reference_commit,
    commit_kv_group as reference_commit_group,
    empty_kv_snapshot as reference_empty,
    gqa_causal_attention_bf16 as reference_attention,
    make_kv_snapshot as reference_snapshot,
    prepare_kv_append as reference_prepare,
    prepared_kv_values as reference_prepared_values,
)
from runtime.tensor_accelerator.attention import (
    CAUSAL_MASK_BF16_CODE as KERNEL_MASK,
    NUMERIC_CONTRACT as KERNEL_CONTRACT,
    SCALE_BF16_CODE as KERNEL_SCALE,
    AttentionKernelError,
    abort_kv_group as kernel_abort_group,
    commit_kv_append as kernel_commit,
    commit_kv_group as kernel_commit_group,
    empty_kv_snapshot as kernel_empty,
    gqa_causal_attention_bf16 as kernel_attention,
    make_kv_snapshot as kernel_snapshot,
    prepare_kv_append as kernel_prepare,
    prepared_kv_values as kernel_prepared_values,
)


_FINITE_CODES = np.asarray(
    [0, 0x3D80, 0xBD80, 0x3E80, 0xBE80, 0x3F00, 0xBF00, 0x3F80, 0xBF80],
    dtype=np.uint16,
)


def _data(shape: tuple[int, ...], offset: int) -> np.ndarray:
    indices = np.arange(np.prod(shape), dtype=np.int64).reshape(shape)
    return _FINITE_CODES[(indices * 17 + offset * 13) % len(_FINITE_CODES)]


def _tuples(values: np.ndarray) -> tuple:
    return tuple(
        tuple(tuple(int(item) for item in row) for row in token)
        for token in values.tolist()
    )


def _assert_result_equal(reference: object, kernel: object) -> None:
    assert asdict(reference.accounting) == asdict(kernel.accounting)
    assert reference.mask_saturated_element_count == kernel.mask_saturated_element_count
    assert (
        reference.output_saturated_element_count
        == kernel.output_saturated_element_count
    )
    assert (
        reference.probability_saturated_element_count
        == kernel.probability_saturated_element_count
    )
    assert (
        reference.scaling_saturated_element_count
        == kernel.scaling_saturated_element_count
    )
    assert (
        reference.score_saturated_element_count == kernel.score_saturated_element_count
    )
    assert _tuples(kernel.output_values) == reference.output_values
    assert _tuples(kernel.probability_values) == reference.probability_values
    assert _tuples(kernel.scaled_score_values) == reference.scaled_score_values


def test_contract_constants_and_softmax_scalar_primitives_are_frozen() -> None:
    assert REFERENCE_CONTRACT == KERNEL_CONTRACT == ("qwen3_gqa_fp32_softmax_bf16_v1")
    assert REFERENCE_SCALE == KERNEL_SCALE == 0x3DB5
    assert REFERENCE_MASK == KERNEL_MASK == 0xFF7F
    assert binary32_exp_nonpositive(0) == 0x3F800000
    assert binary32_exp_nonpositive(0xBF800000) == 0x3EBC5AB2
    assert binary32_exp_nonpositive(0xC2D00000) == 0
    assert binary32_lanes8_sum([0x3F800000] * 8) == 0x41000000
    with pytest.raises(NumericReferenceError, match="must be <= 0"):
        binary32_exp_nonpositive(0x3F800000)


def test_empty_history_current_token_is_private_until_commit_and_exact() -> None:
    query = _data((1, 32, 128), 1)
    keys = _data((1, 8, 128), 2)
    values = _data((1, 8, 128), 3)
    reference_state = reference_empty("kv.layer.0", capacity=8)
    kernel_state = kernel_empty("kv.layer.0", capacity=8)
    reference_transaction = reference_prepare(
        reference_state,
        transaction_id=11,
        expected_generation=0,
        position_start=0,
        key_values=keys.tolist(),
        value_values=values.tolist(),
    )
    kernel_transaction = kernel_prepare(
        kernel_state,
        transaction_id=11,
        expected_generation=0,
        position_start=0,
        key_values=keys,
        value_values=values,
    )

    assert reference_state.length == kernel_state.length == 0
    reference_view = reference_prepared_values(reference_state, reference_transaction)
    kernel_view = kernel_prepared_values(kernel_state, kernel_transaction)
    assert reference_view[0] == _tuples(kernel_view[0])
    assert reference_view[1] == _tuples(kernel_view[1])

    reference_result = reference_attention(
        query.tolist(), reference_state, reference_transaction
    )
    kernel_result = kernel_attention(query, kernel_state, kernel_transaction)
    _assert_result_equal(reference_result, kernel_result)
    assert np.all(kernel_result.probability_values == np.uint16(0x3F80))
    for query_head in range(32):
        kv_head = query_head // 4
        assert np.array_equal(
            kernel_result.output_values[0, query_head], values[0, kv_head]
        )
    assert asdict(kernel_result.accounting) == {
        "exponential_evaluations": 32,
        "mask_additions": 32,
        "probability_multiplications": 32,
        "scaling_multiplications": 32,
        "score_accumulation_additions": 4096,
        "score_multiplications": 4096,
        "softmax_reduction_additions": 0,
        "softmax_reciprocal_divisions": 32,
        "value_accumulation_additions": 4096,
        "value_multiplications": 4096,
    }

    reference_committed = reference_commit(reference_state, reference_transaction)
    kernel_committed = kernel_commit(kernel_state, kernel_transaction)
    assert reference_committed.generation == kernel_committed.generation == 1
    assert reference_committed.length == kernel_committed.length == 1
    assert reference_committed.key_values == _tuples(kernel_committed.key_values)
    assert reference_committed.value_values == _tuples(kernel_committed.value_values)
    assert reference_state.length == kernel_state.length == 0
    with pytest.raises(ValueError, match="read-only"):
        kernel_committed.key_values[0, 0, 0] = np.uint16(0)


def test_nonempty_causal_history_has_nontrivial_exact_softmax_and_output() -> None:
    history_keys = _data((3, 8, 128), 1)
    history_values = _data((3, 8, 128), 2)
    current_keys = _data((1, 8, 128), 3)
    current_values = _data((1, 8, 128), 4)
    query = _data((1, 32, 128), 5)
    reference_state = reference_snapshot(
        resource_id="kv.layer.0",
        generation=7,
        capacity=8,
        key_values=history_keys.tolist(),
        value_values=history_values.tolist(),
    )
    kernel_state = kernel_snapshot(
        resource_id="kv.layer.0",
        generation=7,
        capacity=8,
        key_values=history_keys,
        value_values=history_values,
    )
    reference_transaction = reference_prepare(
        reference_state,
        transaction_id=19,
        expected_generation=7,
        position_start=3,
        key_values=current_keys.tolist(),
        value_values=current_values.tolist(),
    )
    kernel_transaction = kernel_prepare(
        kernel_state,
        transaction_id=19,
        expected_generation=7,
        position_start=3,
        key_values=current_keys,
        value_values=current_values,
    )
    reference_result = reference_attention(
        query.tolist(), reference_state, reference_transaction
    )
    kernel_result = kernel_attention(query, kernel_state, kernel_transaction)
    _assert_result_equal(reference_result, kernel_result)
    assert np.count_nonzero(kernel_result.probability_values[0, 0]) == 4
    assert len(set(int(item) for item in kernel_result.probability_values[0, 0])) > 1
    assert (
        hashlib.sha256(
            kernel_result.probability_values.astype("<u2", copy=False).tobytes()
        ).hexdigest()
        == "8979a279785ed973bd000e69551c178e54103912c332eb5cb780cb73fc6fdb92"
    )
    assert (
        hashlib.sha256(
            kernel_result.output_values.astype("<u2", copy=False).tobytes()
        ).hexdigest()
        == "b7704b483e8c4f37bd8b634c405bb5e5ba93fda1c0a64153c5c6d01ca9bf1bb5"
    )


def test_two_token_prefill_masks_future_prepared_state_exactly() -> None:
    query = _data((2, 32, 128), 1)
    keys = _data((2, 8, 128), 2)
    values = _data((2, 8, 128), 3)
    reference_state = reference_empty("kv.layer.0", capacity=8)
    kernel_state = kernel_empty("kv.layer.0", capacity=8)
    reference_transaction = reference_prepare(
        reference_state,
        transaction_id=23,
        expected_generation=0,
        position_start=0,
        key_values=keys.tolist(),
        value_values=values.tolist(),
    )
    kernel_transaction = kernel_prepare(
        kernel_state,
        transaction_id=23,
        expected_generation=0,
        position_start=0,
        key_values=keys,
        value_values=values,
    )
    reference_result = reference_attention(
        query.tolist(), reference_state, reference_transaction
    )
    kernel_result = kernel_attention(query, kernel_state, kernel_transaction)
    _assert_result_equal(reference_result, kernel_result)
    assert np.all(kernel_result.scaled_score_values[0, :, 1] == 0xFF7F)
    assert np.all(kernel_result.probability_values[0, :, 1] == 0)
    assert np.all(kernel_result.probability_values[0, :, 0] == 0x3F80)
    assert np.all(kernel_result.probability_values[1] != 0)


def test_group_commit_is_atomic_generation_checked_and_abort_preserves_state() -> None:
    keys0 = _data((1, 8, 128), 1)
    values0 = _data((1, 8, 128), 2)
    keys1 = _data((1, 8, 128), 3)
    values1 = _data((1, 8, 128), 4)
    reference_states = (
        reference_empty("kv.layer.0", capacity=2),
        reference_empty("kv.layer.1", capacity=2),
    )
    kernel_states = (
        kernel_empty("kv.layer.0", capacity=2),
        kernel_empty("kv.layer.1", capacity=2),
    )
    reference_transactions = (
        reference_prepare(
            reference_states[0],
            transaction_id=31,
            expected_generation=0,
            position_start=0,
            key_values=keys0.tolist(),
            value_values=values0.tolist(),
        ),
        reference_prepare(
            reference_states[1],
            transaction_id=31,
            expected_generation=0,
            position_start=0,
            key_values=keys1.tolist(),
            value_values=values1.tolist(),
        ),
    )
    kernel_transactions = (
        kernel_prepare(
            kernel_states[0],
            transaction_id=31,
            expected_generation=0,
            position_start=0,
            key_values=keys0,
            value_values=values0,
        ),
        kernel_prepare(
            kernel_states[1],
            transaction_id=31,
            expected_generation=0,
            position_start=0,
            key_values=keys1,
            value_values=values1,
        ),
    )
    reference_aborted = reference_abort_group(
        tuple(zip(reference_states, reference_transactions, strict=True))
    )
    kernel_aborted = kernel_abort_group(
        tuple(zip(kernel_states, kernel_transactions, strict=True))
    )
    assert [state.generation for state in reference_aborted] == [0, 0]
    assert [state.generation for state in kernel_aborted] == [0, 0]
    assert [state.length for state in reference_aborted] == [0, 0]
    assert [state.length for state in kernel_aborted] == [0, 0]

    reference_committed = reference_commit_group(
        tuple(zip(reference_states, reference_transactions, strict=True))
    )
    kernel_committed = kernel_commit_group(
        tuple(zip(kernel_states, kernel_transactions, strict=True))
    )
    assert [state.generation for state in reference_committed] == [1, 1]
    assert [state.generation for state in kernel_committed] == [1, 1]
    assert [state.length for state in reference_committed] == [1, 1]
    assert [state.length for state in kernel_committed] == [1, 1]

    other_kernel_transaction = kernel_prepare(
        kernel_states[1],
        transaction_id=32,
        expected_generation=0,
        position_start=0,
        key_values=keys1,
        value_values=values1,
    )
    with pytest.raises(AttentionKernelError, match="more than one transaction"):
        kernel_commit_group(
            (
                (kernel_states[0], kernel_transactions[0]),
                (kernel_states[1], other_kernel_transaction),
            )
        )
    assert [state.generation for state in kernel_states] == [0, 0]
    assert [state.length for state in kernel_states] == [0, 0]
    with pytest.raises(AttentionKernelError, match="stale"):
        kernel_commit(kernel_committed[0], kernel_transactions[0])
    with pytest.raises(AttentionReferenceError, match="stale"):
        reference_commit(reference_committed[0], reference_transactions[0])


def test_state_bounds_shapes_nonfinite_values_and_import_independence_fail_closed() -> (
    None
):
    keys = _data((1, 8, 128), 1)
    values = _data((1, 8, 128), 2)
    kernel_state = kernel_empty("kv.layer.0", capacity=1)
    reference_state = reference_empty("kv.layer.0", capacity=1)
    with pytest.raises(AttentionKernelError, match="exceeds capacity"):
        kernel_prepare(
            kernel_state,
            transaction_id=1,
            expected_generation=0,
            position_start=0,
            key_values=np.concatenate((keys, keys), axis=0),
            value_values=np.concatenate((values, values), axis=0),
        )
    with pytest.raises(AttentionReferenceError, match="exceeds capacity"):
        reference_prepare(
            reference_state,
            transaction_id=1,
            expected_generation=0,
            position_start=0,
            key_values=np.concatenate((keys, keys), axis=0).tolist(),
            value_values=np.concatenate((values, values), axis=0).tolist(),
        )
    bad_query = _data((1, 32, 128), 3)
    bad_query[0, 0, 0] = np.uint16(0x7F80)
    kernel_transaction = kernel_prepare(
        kernel_state,
        transaction_id=1,
        expected_generation=0,
        position_start=0,
        key_values=keys,
        value_values=values,
    )
    reference_transaction = reference_prepare(
        reference_state,
        transaction_id=1,
        expected_generation=0,
        position_start=0,
        key_values=keys.tolist(),
        value_values=values.tolist(),
    )
    with pytest.raises(AttentionKernelError, match="NaN or infinity"):
        kernel_attention(bad_query, kernel_state, kernel_transaction)
    with pytest.raises(AttentionReferenceError, match="finite BF16"):
        reference_attention(bad_query.tolist(), reference_state, reference_transaction)

    reference_module = __import__(
        "runtime.reference.tensor_accelerator_attention", fromlist=["unused"]
    )
    source = Path(reference_module.__file__).read_text(encoding="utf-8").lower()
    assert "compiler." not in source
    assert "runtime.tensor_accelerator" not in source
    assert "import numpy" not in source
    assert "import torch" not in source
