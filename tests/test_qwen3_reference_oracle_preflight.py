"""Focused fail-closed tests for the exact-8K external-oracle launch."""

from __future__ import annotations

import argparse
import copy
import importlib.util
import json
from pathlib import Path
import shutil

import pytest


REPO = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "run_qwen3_reference_oracle",
    REPO / "tools/run_qwen3_reference_oracle.py",
)
oracle = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(oracle)


def _gate_args(**changes) -> argparse.Namespace:
    values = {
        "agent_episode": None,
        "attention_implementation": "sdpa",
        "checkpoint_lock": oracle.DEFAULT_CHECKPOINT_LOCK,
        "cpu_gib": 80,
        "cpu_only": False,
        "exact_8k_construction": oracle.DEFAULT_EXACT_8K_CONSTRUCTION,
        "force": False,
        "gate_1_production": True,
        "gpu_gib": 9,
        "only": None,
        "prefill_chunk": 0,
        "snapshot": oracle.DEFAULT_SNAPSHOT,
        "workloads": oracle.DEFAULT_WORKLOADS,
    }
    values.update(changes)
    return argparse.Namespace(**values)


def test_gate_1_switch_owns_selection_chunking_and_placement() -> None:
    args = _gate_args()

    assert oracle._configure_gate_1_production(args) == []
    assert args.only == [oracle.EXACT_8K_WORKLOAD_ID]
    assert args.prefill_chunk == 512
    assert args.gpu_gib == 8

    assert "cannot overwrite" in oracle._configure_gate_1_production(
        _gate_args(force=True)
    )[0]
    assert "only permits" in oracle._configure_gate_1_production(
        _gate_args(only=["TA-QW-CHAT-1"])
    )[0]


def test_selection_rejects_unknown_duplicate_and_tampered_workloads(
    tmp_path: Path,
) -> None:
    with pytest.raises(oracle.OracleInputError, match="unknown workloads"):
        oracle._load_selected_workloads(oracle.DEFAULT_WORKLOADS, ["UNKNOWN"])
    with pytest.raises(oracle.OracleInputError, match="duplicate"):
        oracle._load_selected_workloads(
            oracle.DEFAULT_WORKLOADS,
            [oracle.EXACT_8K_WORKLOAD_ID, oracle.EXACT_8K_WORKLOAD_ID],
        )

    copied = tmp_path / "workloads"
    copied.mkdir()
    shutil.copy(oracle.DEFAULT_WORKLOADS / "index.json", copied / "index.json")
    source = oracle.DEFAULT_WORKLOADS / f"{oracle.EXACT_8K_WORKLOAD_ID}.json"
    body = json.loads(source.read_text())
    body["token_ids"][0] += 1
    (copied / source.name).write_text(json.dumps(body))
    with pytest.raises(oracle.OracleInputError, match="do not agree"):
        oracle._load_selected_workloads(copied, [oracle.EXACT_8K_WORKLOAD_ID])


@pytest.mark.skipif(
    not oracle.DEFAULT_CHECKPOINT_LOCK.is_file()
    or not (oracle.DEFAULT_SNAPSHOT / "tokenizer.json").is_file(),
    reason="pinned Qwen tokenizer sources are unavailable",
)
def test_gate_1_authenticates_and_reconstructs_before_model_import(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    index, _selected, bodies, identities = oracle._load_selected_workloads(
        oracle.DEFAULT_WORKLOADS, [oracle.EXACT_8K_WORKLOAD_ID]
    )
    verified: list[tuple[Path, str]] = []

    def record_verify(snapshot: Path, lock: dict) -> dict:
        verified.append((snapshot, lock["lock_id"]))
        return lock

    # This focused test proves that the full verifier is invoked without
    # spending 16.38 GB of I/O while another model session owns the host.
    monkeypatch.setattr(oracle, "verify_checkpoint_lock", record_verify)
    evidence, _tokenizer = oracle._authenticate_gate_1_inputs(
        _gate_args(), index, bodies, identities
    )

    assert verified == [
        (oracle.DEFAULT_SNAPSHOT, oracle.GATE_1_CHECKPOINT_LOCK_ID)
    ]
    assert evidence == {
        "completed_before_model_framework_import": True,
        "full_byte_hash_verified": True,
        "lock_id": oracle.GATE_1_CHECKPOINT_LOCK_ID,
        "lock_source_sha256": oracle.GATE_1_CHECKPOINT_LOCK_SHA256,
        "payload_bytes": 16_381_470_720,
        "shard_count": 5,
        "tensor_count": 399,
    }
    assert set(identities) == {
        "checkpoint_lock",
        "exact_8k_construction",
        "workload_index",
        "workload_sources",
    }


def test_gate_1_terminal_validation_requires_first_eos_or_exact_cap() -> None:
    oracle._validate_gate_1_generation([7] * 256, eos_ids={99})
    oracle._validate_gate_1_generation([7, 99], eos_ids={99})

    for tokens, match in (
        ([], "no token"),
        ([7], "before EOS"),
        ([99, 7], "after EOS"),
        ([151_669], "invalid or padded"),
    ):
        with pytest.raises(oracle.OracleInputError, match=match):
            oracle._validate_gate_1_generation(tokens, eos_ids={99})


def test_gate_1_refuses_pinned_source_hash_drift() -> None:
    index, _selected, bodies, identities = oracle._load_selected_workloads(
        oracle.DEFAULT_WORKLOADS, [oracle.EXACT_8K_WORKLOAD_ID]
    )
    changed = copy.deepcopy(identities)
    changed["workload_index"]["sha256"] = "0" * 64

    with pytest.raises(oracle.OracleInputError, match="not Gate-1 pinned"):
        oracle._authenticate_gate_1_inputs(
            _gate_args(), index, bodies, changed
        )
