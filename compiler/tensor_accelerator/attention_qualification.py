"""Qualification evidence for Qwen causal attention and transactional KV."""

from __future__ import annotations

from dataclasses import asdict
import hashlib
import os
from pathlib import Path
import tempfile
from typing import Any, Mapping

import numpy as np

from runtime.reference.tensor_accelerator_attention import (
    CAUSAL_MASK_BF16_CODE,
    HEAD_DIM,
    KEY_VALUE_HEADS,
    MAX_CONTEXT_TOKENS,
    NUMERIC_CONTRACT,
    QUERY_HEADS,
    SCALE_BF16_CODE,
    STATE_CONTRACT,
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

from .common import (
    ArtifactError,
    canonical_json_bytes,
    exact_keys,
    load_strict_json,
    require_int,
    require_sha256,
    sha256_bytes,
)


SCHEMA = "opentallas.tensor_accelerator.attention_qualification.v1"
QKV_EXECUTION_SCHEMA = "opentallas.tensor_accelerator.qkv_execution.v1"
PINNED_QKV_BUILD_ID = "b84d8f049fd16d90bed1aeb67c7317919d80ca3096055688d3a2144a81c06b63"
PINNED_QKV_REPORT_ID = (
    "af4b5b5d3ea68689f073fdc22584699462ad64c44295120cea7a5e7873383730"
)
PINNED_SOURCE_SHA256 = (
    "704c914530530a1acb0b443add1f520404e3ac2c28c0ab7e16f80f86cfe8ccb2"
)
EXPECTED_QKV_PAYLOAD_SHA256 = {
    "k_rotary": "ce427ae533331720b9b58dde633e3ca352fa9fe0d3dd09d8cab222b799963858",
    "q_rotary": "a846335c825cf9fb06213220acf157c6a805376b1324a7cec09d6fa4621e718d",
    "v": "b07011da7a3d58dcccceb91e596ceebc2084ab3c2fc9d0b6a9a8704e91ef8dc5",
}
EXPECTED_SHAPES = {
    "k_rotary": [KEY_VALUE_HEADS, HEAD_DIM],
    "q_rotary": [QUERY_HEADS, HEAD_DIM],
    "v": [KEY_VALUE_HEADS, HEAD_DIM],
}


class AttentionQualificationError(ArtifactError):
    """Raised when attention or state evidence is incomplete."""


def _identity(value: Mapping[str, Any], field: str, label: str) -> None:
    expected = sha256_bytes(
        canonical_json_bytes({key: item for key, item in value.items() if key != field})
    )
    observed = require_sha256(value.get(field), f"{label}.{field}")
    if observed != expected:
        raise AttentionQualificationError(f"{label} identity differs")


def _load_canonical(path: Path, label: str) -> tuple[dict[str, Any], bytes]:
    try:
        payload = path.read_bytes()
        value = load_strict_json(path)
    except (OSError, ArtifactError) as exc:
        raise AttentionQualificationError(f"cannot load {label}: {exc}") from exc
    if canonical_json_bytes(value) != payload:
        raise AttentionQualificationError(f"{label} is not canonical JSON")
    return value, payload


def _payload(values: object) -> bytes:
    return np.ascontiguousarray(values, dtype="<u2").tobytes(order="C")


def _hash(values: object) -> str:
    return hashlib.sha256(_payload(values)).hexdigest()


def _output_codes(
    report: Mapping[str, Any],
    role: str,
) -> np.ndarray[Any, np.dtype[np.uint16]]:
    outputs = report.get("outputs")
    if not isinstance(outputs, Mapping) or set(outputs) != set(EXPECTED_SHAPES):
        raise AttentionQualificationError("Q/K/V execution output coverage differs")
    raw = outputs[role]
    if not isinstance(raw, Mapping):
        raise AttentionQualificationError(f"Q/K/V {role} output is malformed")
    exact_keys(
        raw,
        {"codes", "dtype", "payload_sha256", "shape", "size_bytes"},
        set(),
        f"Q/K/V {role} output",
    )
    shape = EXPECTED_SHAPES[role]
    if raw.get("dtype") != "bf16" or raw.get("shape") != shape:
        raise AttentionQualificationError(f"Q/K/V {role} type or shape differs")
    count = shape[0] * shape[1]
    if raw.get("size_bytes") != 2 * count:
        raise AttentionQualificationError(f"Q/K/V {role} byte count differs")
    codes = raw.get("codes")
    if not isinstance(codes, list) or len(codes) != count:
        raise AttentionQualificationError(f"Q/K/V {role} code coverage differs")
    parsed = np.asarray(
        [
            require_int(code, f"Q/K/V {role}.codes[{index}]", minimum=0, maximum=0xFFFF)
            for index, code in enumerate(codes)
        ],
        dtype=np.uint16,
    ).reshape(tuple(shape))
    digest = _hash(parsed)
    if (
        require_sha256(raw.get("payload_sha256"), f"Q/K/V {role}.payload_sha256")
        != digest
        or digest != EXPECTED_QKV_PAYLOAD_SHA256[role]
    ):
        raise AttentionQualificationError(f"Q/K/V {role} payload identity differs")
    if np.any((parsed & np.uint16(0x7F80)) == np.uint16(0x7F80)):
        raise AttentionQualificationError(f"Q/K/V {role} contains nonfinite BF16")
    return parsed


def _state_record(state: object) -> dict[str, Any]:
    key_values = state.key_values
    value_values = state.value_values
    body = {
        "capacity": int(state.capacity),
        "generation": int(state.generation),
        "key_payload_sha256": _hash(key_values),
        "length": int(state.length),
        "resource_id": state.resource_id,
        "value_payload_sha256": _hash(value_values),
    }
    return {**body, "state_sha256": sha256_bytes(canonical_json_bytes(body))}


def _assert_state_equal(reference_state: object, kernel_state: object) -> None:
    if _state_record(reference_state) != _state_record(kernel_state):
        raise AttentionQualificationError(
            "optimized transactional state differs from scalar state"
        )


def _tuples(values: np.ndarray) -> tuple:
    return tuple(
        tuple(tuple(int(item) for item in row) for row in token)
        for token in values.tolist()
    )


def _attention_fixture(
    *,
    fixture_id: str,
    fixture_class: str,
    query: np.ndarray,
    committed_keys: np.ndarray,
    committed_values: np.ndarray,
    prepared_keys: np.ndarray,
    prepared_values: np.ndarray,
    generation: int,
    transaction_id: int,
    transform: str,
) -> dict[str, Any]:
    if committed_keys.shape[0] == 0:
        reference_state = reference_empty("kv.layer.0")
        kernel_state = kernel_empty("kv.layer.0")
    else:
        reference_state = reference_snapshot(
            resource_id="kv.layer.0",
            generation=generation,
            capacity=MAX_CONTEXT_TOKENS,
            key_values=committed_keys.tolist(),
            value_values=committed_values.tolist(),
        )
        kernel_state = kernel_snapshot(
            resource_id="kv.layer.0",
            generation=generation,
            capacity=MAX_CONTEXT_TOKENS,
            key_values=committed_keys,
            value_values=committed_values,
        )
    _assert_state_equal(reference_state, kernel_state)
    before = _state_record(reference_state)
    reference_transaction = reference_prepare(
        reference_state,
        transaction_id=transaction_id,
        expected_generation=generation,
        position_start=committed_keys.shape[0],
        key_values=prepared_keys.tolist(),
        value_values=prepared_values.tolist(),
    )
    kernel_transaction = kernel_prepare(
        kernel_state,
        transaction_id=transaction_id,
        expected_generation=generation,
        position_start=committed_keys.shape[0],
        key_values=prepared_keys,
        value_values=prepared_values,
    )
    reference_view = reference_prepared_values(reference_state, reference_transaction)
    kernel_view = kernel_prepared_values(kernel_state, kernel_transaction)
    if reference_view[0] != _tuples(kernel_view[0]) or reference_view[1] != _tuples(
        kernel_view[1]
    ):
        raise AttentionQualificationError("prepared KV visibility differs")
    try:
        reference_result = reference_attention(
            query.tolist(), reference_state, reference_transaction
        )
        kernel_result = kernel_attention(query, kernel_state, kernel_transaction)
    except (AttentionReferenceError, AttentionKernelError) as exc:
        raise AttentionQualificationError(
            f"attention fixture {fixture_id!r} failed: {exc}"
        ) from exc
    if (
        asdict(reference_result.accounting) != asdict(kernel_result.accounting)
        or reference_result.mask_saturated_element_count
        != kernel_result.mask_saturated_element_count
        or reference_result.output_saturated_element_count
        != kernel_result.output_saturated_element_count
        or reference_result.probability_saturated_element_count
        != kernel_result.probability_saturated_element_count
        or reference_result.scaling_saturated_element_count
        != kernel_result.scaling_saturated_element_count
        or reference_result.score_saturated_element_count
        != kernel_result.score_saturated_element_count
        or reference_result.output_values != _tuples(kernel_result.output_values)
        or reference_result.probability_values
        != _tuples(kernel_result.probability_values)
        or reference_result.scaled_score_values
        != _tuples(kernel_result.scaled_score_values)
    ):
        raise AttentionQualificationError(
            f"optimized attention differs from scalar fixture {fixture_id!r}"
        )

    reference_aborted = reference_abort_group(
        ((reference_state, reference_transaction),)
    )[0]
    kernel_aborted = kernel_abort_group(((kernel_state, kernel_transaction),))[0]
    _assert_state_equal(reference_aborted, kernel_aborted)
    if _state_record(reference_aborted) != before:
        raise AttentionQualificationError("abort changed committed KV state")
    reference_committed = reference_commit(reference_state, reference_transaction)
    kernel_committed = kernel_commit(kernel_state, kernel_transaction)
    _assert_state_equal(reference_committed, kernel_committed)
    after = _state_record(reference_committed)
    expected_length = committed_keys.shape[0] + prepared_keys.shape[0]
    if (
        reference_committed.generation != generation + 1
        or reference_committed.length != expected_length
    ):
        raise AttentionQualificationError("commit generation or length differs")

    outputs = {
        "attention": {
            "payload_sha256": _hash(kernel_result.output_values),
            "shape": list(kernel_result.output_values.shape),
        },
        "probabilities": {
            "payload_sha256": _hash(kernel_result.probability_values),
            "shape": list(kernel_result.probability_values.shape),
        },
        "scaled_scores": {
            "payload_sha256": _hash(kernel_result.scaled_score_values),
            "shape": list(kernel_result.scaled_score_values.shape),
        },
    }
    selected_heads = (0, 1, 10, 31)
    return {
        "accounting": asdict(kernel_result.accounting),
        "fixture_class": fixture_class,
        "fixture_id": fixture_id,
        "inputs": {
            "committed_key_payload_sha256": _hash(committed_keys),
            "committed_length": int(committed_keys.shape[0]),
            "committed_value_payload_sha256": _hash(committed_values),
            "prepared_key_payload_sha256": _hash(prepared_keys),
            "prepared_length": int(prepared_keys.shape[0]),
            "prepared_value_payload_sha256": _hash(prepared_values),
            "query_payload_sha256": _hash(query),
            "query_shape": list(query.shape),
            "transform": transform,
        },
        "outputs": outputs,
        "saturation": {
            "mask": kernel_result.mask_saturated_element_count,
            "output": kernel_result.output_saturated_element_count,
            "probability": kernel_result.probability_saturated_element_count,
            "scaling": kernel_result.scaling_saturated_element_count,
            "score": kernel_result.score_saturated_element_count,
        },
        "selected_probability_codes": [
            {
                "codes": [
                    int(item)
                    for item in kernel_result.probability_values[0, head].tolist()
                ],
                "query_head": head,
            }
            for head in selected_heads
        ],
        "status": "exact_match",
        "transaction": {
            "aborted_state_sha256": before["state_sha256"],
            "base_generation": generation,
            "committed_length": expected_length,
            "committed_state_sha256": after["state_sha256"],
            "next_generation": generation + 1,
            "prepared_key_payload_sha256": _hash(kernel_view[0]),
            "prepared_value_payload_sha256": _hash(kernel_view[1]),
            "transaction_id": transaction_id,
        },
    }


def _transaction_qualification(
    keys: np.ndarray,
    values: np.ndarray,
) -> dict[str, Any]:
    reference_states = (
        reference_empty("kv.layer.0"),
        reference_empty("kv.layer.1"),
    )
    kernel_states = (
        kernel_empty("kv.layer.0"),
        kernel_empty("kv.layer.1"),
    )
    reference_transactions = tuple(
        reference_prepare(
            state,
            transaction_id=0x5157454E,
            expected_generation=0,
            position_start=0,
            key_values=keys.tolist(),
            value_values=values.tolist(),
        )
        for state in reference_states
    )
    kernel_transactions = tuple(
        kernel_prepare(
            state,
            transaction_id=0x5157454E,
            expected_generation=0,
            position_start=0,
            key_values=keys,
            value_values=values,
        )
        for state in kernel_states
    )
    reference_aborted = reference_abort_group(
        tuple(zip(reference_states, reference_transactions, strict=True))
    )
    kernel_aborted = kernel_abort_group(
        tuple(zip(kernel_states, kernel_transactions, strict=True))
    )
    for reference_state, kernel_state in zip(
        reference_aborted, kernel_aborted, strict=True
    ):
        _assert_state_equal(reference_state, kernel_state)
        if reference_state.generation != 0 or reference_state.length != 0:
            raise AttentionQualificationError("group abort changed committed state")
    reference_committed = reference_commit_group(
        tuple(zip(reference_states, reference_transactions, strict=True))
    )
    kernel_committed = kernel_commit_group(
        tuple(zip(kernel_states, kernel_transactions, strict=True))
    )
    for reference_state, kernel_state in zip(
        reference_committed, kernel_committed, strict=True
    ):
        _assert_state_equal(reference_state, kernel_state)
        if reference_state.generation != 1 or reference_state.length != keys.shape[0]:
            raise AttentionQualificationError("atomic group commit differs")

    stale_rejected = False
    mixed_transaction_rejected = False
    try:
        kernel_commit(kernel_committed[0], kernel_transactions[0])
    except AttentionKernelError:
        stale_rejected = True
    other = kernel_prepare(
        kernel_states[1],
        transaction_id=0x5157454F,
        expected_generation=0,
        position_start=0,
        key_values=keys,
        value_values=values,
    )
    try:
        kernel_commit_group(
            (
                (kernel_states[0], kernel_transactions[0]),
                (kernel_states[1], other),
            )
        )
    except AttentionKernelError:
        mixed_transaction_rejected = True
    if not stale_rejected or not mixed_transaction_rejected:
        raise AttentionQualificationError("transaction rejection coverage differs")
    return {
        "abort_preserved_all_resources": True,
        "committed_state_sha256": [
            _state_record(state)["state_sha256"] for state in reference_committed
        ],
        "generation_checked": stale_rejected,
        "mixed_transaction_rejected": mixed_transaction_rejected,
        "resource_count": len(reference_committed),
        "status": "pass",
    }


def qualify_qkv_attention(
    *,
    qkv_execution_path: Path,
    modeling_source_path: Path,
) -> dict[str, Any]:
    """Qualify full-shape causal GQA from retained authentic Q/K/V outputs."""

    report, report_payload = _load_canonical(
        Path(qkv_execution_path), "Q/K/V execution report"
    )
    if report.get("schema") != QKV_EXECUTION_SCHEMA or report.get("status") != "pass":
        raise AttentionQualificationError("Q/K/V execution report status differs")
    _identity(report, "report_id", "Q/K/V execution report")
    if (
        report.get("build_id") != PINNED_QKV_BUILD_ID
        or report.get("report_id") != PINNED_QKV_REPORT_ID
    ):
        raise AttentionQualificationError("Q/K/V execution handoff identity differs")
    try:
        source_payload = Path(modeling_source_path).read_bytes()
    except OSError as exc:
        raise AttentionQualificationError(
            f"cannot read pinned Qwen source: {exc}"
        ) from exc
    source_sha256 = hashlib.sha256(source_payload).hexdigest()
    if source_sha256 != PINNED_SOURCE_SHA256:
        raise AttentionQualificationError("pinned Qwen source identity differs")

    q = _output_codes(report, "q_rotary")[None, :, :]
    k = _output_codes(report, "k_rotary")[None, :, :]
    v = _output_codes(report, "v")[None, :, :]
    empty = np.empty((0, KEY_VALUE_HEADS, HEAD_DIM), dtype=np.uint16)
    history_keys = np.stack(
        (
            np.roll(k[0], 1, axis=0),
            k[0, :, ::-1],
            np.roll(k[0], 17, axis=1),
        )
    )
    history_values = np.stack(
        (
            np.roll(v[0], 1, axis=0),
            v[0, :, ::-1],
            np.roll(v[0], 23, axis=1),
        )
    )
    prefill_queries = np.stack((q[0], np.roll(q[0], 9, axis=1)))
    prefill_keys = np.stack((k[0], np.roll(k[0], 7, axis=1)))
    prefill_values = np.stack((v[0], np.roll(v[0], 11, axis=1)))

    fixtures = [
        _attention_fixture(
            fixture_id="authentic_empty_history",
            fixture_class="decode",
            query=q,
            committed_keys=empty,
            committed_values=empty,
            prepared_keys=k,
            prepared_values=v,
            generation=0,
            transaction_id=0x4154544E0001,
            transform="none; authentic retained Q/K/V payloads",
        ),
        _attention_fixture(
            fixture_id="checkpoint_derived_nonempty_history",
            fixture_class="decode",
            query=q,
            committed_keys=history_keys,
            committed_values=history_values,
            prepared_keys=k,
            prepared_values=v,
            generation=4,
            transaction_id=0x4154544E0002,
            transform=(
                "history uses authenticated payload head rotation, element reversal, "
                "and element rotation"
            ),
        ),
        _attention_fixture(
            fixture_id="checkpoint_derived_causal_prefill",
            fixture_class="prefill",
            query=prefill_queries,
            committed_keys=empty,
            committed_values=empty,
            prepared_keys=prefill_keys,
            prepared_values=prefill_values,
            generation=0,
            transaction_id=0x4154544E0003,
            transform="second prepared token uses authenticated element rotations",
        ),
    ]
    if fixtures[2]["selected_probability_codes"][0]["codes"][1] != 0:
        raise AttentionQualificationError(
            "causal prefill future probability is not zero"
        )
    body: dict[str, Any] = {
        "fixtures": fixtures,
        "numeric_contract": NUMERIC_CONTRACT,
        "profile": {
            "causal_mask_bf16_code": CAUSAL_MASK_BF16_CODE,
            "context_capacity": MAX_CONTEXT_TOKENS,
            "head_dim": HEAD_DIM,
            "key_value_heads": KEY_VALUE_HEADS,
            "query_heads": QUERY_HEADS,
            "scale_bf16_code": SCALE_BF16_CODE,
            "softmax_reduction_lanes": 8,
        },
        "schema": SCHEMA,
        "source": {
            "modeling_source_path": "transformers/models/qwen3/modeling_qwen3.py",
            "modeling_source_sha256": source_sha256,
            "qkv_build_id": report["build_id"],
            "qkv_execution_payload_sha256": hashlib.sha256(report_payload).hexdigest(),
            "qkv_execution_report_id": report["report_id"],
            "qkv_output_payload_sha256": EXPECTED_QKV_PAYLOAD_SHA256,
        },
        "state_contract": STATE_CONTRACT,
        "status": "pass",
        "target_adaptation": {
            "dot_reduction": "increasing_logical_index_binary32_rne",
            "framework_fallback": False,
            "softmax_reduction": "eight_lane_then_fixed_tree_binary32_rne",
            "source_semantics": (
                "repeat_kv, BF16 score scale, causal mask, FP32 softmax, "
                "BF16 probability, and BF16 value aggregation"
            ),
        },
        "transaction_qualification": _transaction_qualification(k, v),
    }
    return {**body, "report_id": sha256_bytes(canonical_json_bytes(body))}


def load_attention_qualification(path: Path) -> dict[str, Any]:
    """Load a canonical, internally authenticated qualification report."""

    value, _ = _load_canonical(Path(path), "attention qualification")
    exact_keys(
        value,
        {
            "fixtures",
            "numeric_contract",
            "profile",
            "report_id",
            "schema",
            "source",
            "state_contract",
            "status",
            "target_adaptation",
            "transaction_qualification",
        },
        set(),
        "attention qualification",
    )
    if (
        value.get("schema") != SCHEMA
        or value.get("status") != "pass"
        or value.get("numeric_contract") != NUMERIC_CONTRACT
        or value.get("state_contract") != STATE_CONTRACT
    ):
        raise AttentionQualificationError("attention qualification contract differs")
    _identity(value, "report_id", "attention qualification")
    return value


def publish_attention_qualification(
    report: Mapping[str, Any],
    output_path: Path,
) -> None:
    """Atomically retain one qualification report without overwriting evidence."""

    if not isinstance(report, Mapping):
        raise AttentionQualificationError("attention qualification must be an object")
    body = {key: value for key, value in report.items() if key != "report_id"}
    expected = sha256_bytes(canonical_json_bytes(body))
    if report.get("report_id") != expected:
        raise AttentionQualificationError("attention qualification identity differs")
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise AttentionQualificationError(
            f"qualification evidence will not be overwritten: {destination}"
        )
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.",
        dir=destination.parent,
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(canonical_json_bytes(dict(report)))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


__all__ = [
    "AttentionQualificationError",
    "EXPECTED_QKV_PAYLOAD_SHA256",
    "PINNED_QKV_BUILD_ID",
    "PINNED_QKV_REPORT_ID",
    "PINNED_SOURCE_SHA256",
    "SCHEMA",
    "load_attention_qualification",
    "publish_attention_qualification",
    "qualify_qkv_attention",
]
