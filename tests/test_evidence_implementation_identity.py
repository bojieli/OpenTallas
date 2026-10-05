"""Two runs of one implementation are comparable however much work each did.

``implementation_identity`` records what ran a token -- backend, library,
accelerated kernel -- and, nested under ``executed``, how many times that
kernel was called.  ``check_comparable`` compared the whole dict, so a wafer
partition making 583 numba calls could never be compared with a 32-node
partition making 18,656, and the only pair that ever passed was two 32-node
runs whose counts happened to coincide.  The refusal message printed
``numpy vs numpy``, naming the one field that agreed.

Statistics are evidence.  They are not identity.
"""

from __future__ import annotations

import dataclasses

from runtime.evidence import (
    EvidenceClass,
    ExecutionRecord,
    TargetIdentity,
    WorkloadIdentity,
    _implementation_only,
    check_comparable,
)


def _record(identity: dict) -> ExecutionRecord:
    workload = WorkloadIdentity(
        model_id="m", workload_id="w", workload_digest="d" * 64,
        prompt_token_count=32, max_new_tokens=4, generation_policy_digest="g" * 64,
        numeric_profile="p", graph_id="h" * 64, tokenizer_sha256="t" * 64,
    )
    target = TargetIdentity(
        target_id="t", backend="rom", topology_class=1, node_count=32,
        capability_digest="c" * 64, deployment_digest="e" * 64,
    )
    return ExecutionRecord(
        evidence_class=EvidenceClass.FUNCTIONAL, workload=workload, target=target,
        generated_token_ids=(1, 2, 3, 4), stop_reason="max_new_tokens",
        counters={}, implementation_identity=identity,
    )


WAFER = {
    "backend": "numpy", "library": "numpy", "library_version": "2.1",
    "deepseek_ordered_product_add": {
        "accelerated_kernel": "numba_fastmath_false_k_serial_v1",
        "executed": {"numba_calls": 583, "numba_scalar_products": 9_000_000},
    },
}
ARRAY = {
    **WAFER,
    "deepseek_ordered_product_add": {
        "accelerated_kernel": "numba_fastmath_false_k_serial_v1",
        "executed": {"numba_calls": 18_656, "numba_scalar_products": 1_000_000},
    },
}


def test_execution_statistics_are_stripped_recursively() -> None:
    stripped = _implementation_only(WAFER)
    assert "executed" not in stripped["deepseek_ordered_product_add"]
    assert stripped["deepseek_ordered_product_add"]["accelerated_kernel"] == (
        "numba_fastmath_false_k_serial_v1"
    )
    assert stripped["library_version"] == "2.1"


def test_two_partitions_of_one_implementation_are_comparable() -> None:
    left = _record(WAFER)
    right = _record(dataclasses.replace(left, implementation_identity=ARRAY).implementation_identity)
    problems = [p for p in check_comparable(left, right) if "implementation" in p]
    assert problems == [], problems


def test_a_different_kernel_is_still_refused_and_named() -> None:
    other = {
        **WAFER,
        "deepseek_ordered_product_add": {
            "accelerated_kernel": "numba_fastmath_true_v2",
            "executed": {"numba_calls": 583},
        },
    }
    problems = [p for p in check_comparable(_record(WAFER), _record(other)) if "implementation" in p]
    assert len(problems) == 1
    assert "deepseek_ordered_product_add" in problems[0]
    assert "numba_fastmath_true_v2" in problems[0]
    # The old message named only the backend, which agreed; the new one must
    # not degenerate into "numpy vs numpy" again.
    assert "numpy vs numpy" not in problems[0]
