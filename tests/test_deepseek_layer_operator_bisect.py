"""Tests for the early-stop DeepSeek layer operator comparison."""

import hashlib
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import numpy as np

from runtime.abi3.constants import DType
from tools.bisect_deepseek_layer_operators import (
    _payload,
    compare_operator_inputs,
    compare_operator_outputs,
)

REPO = Path(__file__).resolve().parents[1]
_BLAS_THREAD_VARIABLES = (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
)


def _record(source: int, slot: int, digest: str, observation: int) -> dict:
    return {
        "source_kernel_id": source,
        "output_slot": slot,
        "payload_sha256": digest,
        "dtype": "BF16",
        "shape": [32, 4096],
        "elements": 131072,
        "observation": observation,
    }


def test_payload_can_hash_each_leading_slice() -> None:
    raw = np.arange(12, dtype=np.uint16).reshape(3, 4)
    view = SimpleNamespace(dtype=int(DType.BF16))
    context = SimpleNamespace(read=lambda _view: raw)

    payload = _payload(view, context, hash_leading_slices=True)

    assert payload["leading_slice_sha256"] == [
        hashlib.sha256(np.ascontiguousarray(row).tobytes()).hexdigest() for row in raw
    ]


def test_simulation_cli_modules_establish_the_governed_thread_default() -> None:
    for module in (
        "tools.bisect_deepseek_lane_activations",
        "tools.bisect_deepseek_layer_operators",
        "tools.run_accelerator_tokens",
    ):
        environment = os.environ.copy()
        for variable in _BLAS_THREAD_VARIABLES:
            environment.pop(variable, None)
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    f"import os; import {module}; "
                    "print(*(os.environ[name] for name in "
                    f"{_BLAS_THREAD_VARIABLES!r}))"
                ),
            ],
            cwd=REPO,
            env=environment,
            check=True,
            capture_output=True,
            text=True,
        )
        assert result.stdout.strip() == "8 8 8"


def test_simulation_cli_respects_an_explicit_thread_identity() -> None:
    environment = os.environ.copy()
    for variable in _BLAS_THREAD_VARIABLES:
        environment[variable] = "3"
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import os; import tools.bisect_deepseek_layer_operators; "
                "print(*(os.environ[name] for name in "
                f"{_BLAS_THREAD_VARIABLES!r}))"
            ),
        ],
        cwd=REPO,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.stdout.strip() == "3 3 3"


def test_comparison_uses_the_last_auxiliary_output_for_each_source() -> None:
    left_partial = _record(10, 0, "partial-rom", 0)
    left_logical = _record(10, 0, "logical", 1)
    right_partial = _record(10, 0, "partial-hbm", 0)
    right_logical = _record(10, 0, "logical", 1)
    for record, descriptor in (
        (left_partial, 100),
        (right_partial, 200),
        (left_logical, 101),
        (right_logical, 201),
    ):
        record["operator_descriptor_id"] = descriptor
        record["pc"] = descriptor
    left = {"operator_outputs": [left_partial, left_logical]}
    right = {"operator_outputs": [right_partial, right_logical]}

    comparison = compare_operator_outputs(left, right)

    assert comparison["all_comparable_payloads_equal"] is True
    assert comparison["comparable_output_count"] == 1
    assert comparison["first_divergence"] is None


def test_comparison_reports_the_first_source_mismatch() -> None:
    left = {
        "operator_outputs": [
            _record(10, 0, "same", 0),
            _record(11, 0, "rom", 1),
        ]
    }
    right = {
        "operator_outputs": [
            _record(10, 0, "same", 0),
            _record(11, 0, "hbm", 1),
        ]
    }

    comparison = compare_operator_outputs(left, right)

    assert comparison["all_comparable_payloads_equal"] is False
    assert comparison["first_divergent_source_kernel_id"] == 11
    assert comparison["first_divergent_output_slot"] == 0


def test_comparison_fails_closed_on_an_output_missing_from_one_lane() -> None:
    left = {"operator_outputs": [_record(10, 0, "same", 0)]}
    right = {"operator_outputs": []}

    comparison = compare_operator_outputs(left, right)

    assert comparison["all_comparable_payloads_equal"] is False
    assert comparison["first_divergent_source_kernel_id"] == 10
    assert comparison["first_divergence"]["rom"] is not None
    assert comparison["first_divergence"]["hbm"] is None


def test_comparison_ignores_transport_shape_when_payload_is_identical() -> None:
    rom = _record(10, 0, "same", 0)
    hbm = _record(10, 0, "same", 0)
    rom["shape"] = [4096]
    hbm["shape"] = [1, 4096]
    left = {"operator_outputs": [rom]}
    right = {"operator_outputs": [hbm]}

    comparison = compare_operator_outputs(left, right)

    assert comparison["all_comparable_payloads_equal"] is True
    assert comparison["transport_shape_differences"] == [
        {
            "source_kernel_id": 10,
            "output_slot": 0,
            "occurrence": 0,
            "rom_shape": [4096],
            "hbm_shape": [1, 4096],
        }
    ]


def test_comparison_lists_physical_intermediates_without_false_divergence() -> None:
    rom = _record(10, 0, "rom-shard", 0)
    hbm = _record(10, 0, "hbm-shard", 0)
    rom["elements"] = 1024
    hbm["elements"] = 2048
    left = {"operator_outputs": [rom]}
    right = {"operator_outputs": [hbm]}

    comparison = compare_operator_outputs(left, right)

    assert comparison["all_comparable_payloads_equal"] is True
    assert comparison["comparable_output_count"] == 0
    assert len(comparison["physical_intermediates_not_compared"]) == 1


def test_input_comparison_uses_input_slots() -> None:
    rom = _record(196, 2, "rom-state", 0)
    hbm = _record(196, 2, "hbm-state", 0)
    rom["input_slot"] = rom.pop("output_slot")
    hbm["input_slot"] = hbm.pop("output_slot")
    left = {"operator_inputs": [rom]}
    right = {"operator_inputs": [hbm]}

    comparison = compare_operator_inputs(left, right)

    assert comparison["first_divergent_source_kernel_id"] == 196
    assert comparison["first_divergent_input_slot"] == 2


def test_comparison_checks_every_repeated_terminal_invocation() -> None:
    rom_rows = [
        _record(331, 0, digest, observation)
        for observation, digest in enumerate(("row-0", "rom-row-1", "row-2"))
    ]
    hbm_rows = [
        _record(331, 0, digest, observation)
        for observation, digest in enumerate(("row-0", "hbm-row-1", "row-2"))
    ]
    for record in (*rom_rows, *hbm_rows):
        record["operator_descriptor_id"] = 123
        record["pc"] = 456

    comparison = compare_operator_outputs(
        {"operator_outputs": rom_rows},
        {"operator_outputs": hbm_rows},
    )

    assert comparison["all_comparable_payloads_equal"] is False
    assert comparison["comparable_output_count"] == 3
    assert comparison["first_divergent_source_kernel_id"] == 331
    assert comparison["first_divergence"]["occurrence"] == 1
    assert comparison["first_divergence"]["rom"]["payload_sha256"] == "rom-row-1"
    assert comparison["first_divergence"]["hbm"]["payload_sha256"] == "hbm-row-1"
