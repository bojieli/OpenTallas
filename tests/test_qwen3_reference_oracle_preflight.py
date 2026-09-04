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
        "heterogeneous_gate_1_production": None,
        "only": None,
        "output": REPO / "results/abi3/qwen3_reference_oracle.json",
        "prefill_chunk": 0,
        "snapshot": oracle.DEFAULT_SNAPSHOT,
        "workloads": oracle.DEFAULT_WORKLOADS,
    }
    values.update(changes)
    return argparse.Namespace(**values)


def _heterogeneous_args(**changes) -> argparse.Namespace:
    workload_ids = changes.get(
        "only", [oracle.HETEROGENEOUS_LANE_SPECS[0].workload_id]
    )
    selected_id = (
        workload_ids[0]
        if isinstance(workload_ids, list) and len(workload_ids) == 1
        else "invalid-selection"
    )
    values = vars(
        _gate_args(
            gate_1_production=False,
            heterogeneous_gate_1_production=oracle.DEFAULT_HETEROGENEOUS_MANIFEST,
            only=workload_ids,
            output=(
                oracle.DEFAULT_HETEROGENEOUS_MANIFEST.parent
                / "references"
                / f"{selected_id}.json"
            ),
        )
    )
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
    assert oracle._gate_1_launch_contract() == {
        "schema": "opentallas.qwen3.gate1_launch.v1",
        "profile_id": "qwen3_exact_8k_external_oracle_v1",
        "workload_id": oracle.EXACT_8K_WORKLOAD_ID,
        "prompt_token_count": 8000,
        "max_new_tokens": 256,
        "selection": "greedy_lowest_token_id_argmax",
        "terminal": {
            "eos_token_ids": list(oracle.EOS_TOKEN_IDS),
            "include_eos_in_output": True,
            "rule": "first_official_eos_or_exact_cap",
        },
        "prefill": {"mode": "chunked_forward_kv_cache", "chunk_tokens": 512},
        "numeric": {"dtype": "bfloat16", "attention_implementation": "sdpa"},
        "placement": {
            "policy": "auto",
            "gpu_memory_gib": 8,
            "cpu_memory_gib": 80,
        },
    }


def test_heterogeneous_switch_requires_one_declared_lane_and_exact_output() -> None:
    args = _heterogeneous_args()

    assert oracle._configure_heterogeneous_gate_1_production(args) == []
    assert args.only == ["TA-QW-8K-1"]
    assert args.workloads == oracle.DEFAULT_HETEROGENEOUS_WORKLOADS
    assert args.prefill_chunk == 512
    assert args.gpu_gib == 8

    for changes, match in (
        ({"only": None}, "exactly one explicit"),
        ({"only": ["TA-QW-8K-1", "TA-QW-8K-REASON-1"]}, "exactly one"),
        ({"only": ["TA-QW-8K-1", "TA-QW-8K-1"]}, "duplicate"),
        ({"only": ["UNKNOWN"]}, "declared lane"),
        ({"output": REPO / "wrong.json"}, "manifest-declared path"),
        ({"force": True}, "cannot overwrite"),
        ({"agent_episode": ["TA-QW-8K-1"]}, "agent episode"),
        ({"cpu_only": True}, "GPU/CPU placement"),
        ({"attention_implementation": "eager"}, "SDPA"),
        ({"prefill_chunk": 64}, "512-token"),
        ({"cpu_gib": 79}, "80 GiB"),
        ({"workloads": REPO / "wrong-workloads"}, "integrated workload root"),
        (
            {"heterogeneous_gate_1_production": REPO / "wrong-manifest.json"},
            "integrated manifest",
        ),
    ):
        problems = oracle._configure_heterogeneous_gate_1_production(
            _heterogeneous_args(**changes)
        )
        assert any(match in problem for problem in problems), problems


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


@pytest.mark.skipif(
    not oracle.DEFAULT_CHECKPOINT_LOCK.is_file()
    or not (oracle.DEFAULT_SNAPSHOT / "tokenizer.json").is_file(),
    reason="pinned Qwen tokenizer sources are unavailable",
)
def test_heterogeneous_gate_1_authenticates_one_exact_lane_before_model_import(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    args = _heterogeneous_args(
        only=["TA-QW-8K-AGENT-HELLO-1"],
        output=(
            oracle.DEFAULT_HETEROGENEOUS_MANIFEST.parent
            / "references/TA-QW-8K-AGENT-HELLO-1.json"
        ),
    )
    assert oracle._configure_heterogeneous_gate_1_production(args) == []
    index, _selected, bodies, identities = oracle._load_selected_workloads(
        args.workloads, args.only
    )
    verified: list[tuple[Path, str]] = []

    def record_verify(snapshot: Path, lock: dict) -> dict:
        verified.append((snapshot, lock["lock_id"]))
        return lock

    monkeypatch.setattr(oracle, "verify_checkpoint_lock", record_verify)
    evidence, _tokenizer, contract = (
        oracle._authenticate_heterogeneous_gate_1_inputs(
            args, index, bodies, identities
        )
    )

    assert verified == [
        (oracle.DEFAULT_SNAPSHOT, oracle.GATE_1_CHECKPOINT_LOCK_ID)
    ]
    assert evidence["full_byte_hash_verified"] is True
    assert evidence["payload_bytes"] == 16_381_470_720
    assert set(identities) == {
        "checkpoint_lock",
        "exact_8k_construction",
        "heterogeneous_workload_set",
        "workload_index",
        "workload_sources",
    }
    workload_set = identities["heterogeneous_workload_set"]
    assert workload_set["manifest_file"]["sha256"] == (
        "6a7f49d621a93fcb02111916e1ab03ee600882629260742a66669c428ffa428c"
    )
    assert workload_set["workload_set_id"] == (
        "4f3e2e3c3dd06683e4aa9374d317dbbbb9227ce90815cf6dc9fc93f195295bea"
    )
    assert workload_set["selected_lane"] == {
        "category": "agentic_tool",
        "lane_index": 2,
        "sequence_id": "qwen3-8k-lane2-agent-hello",
        "source_id": "hello-world",
        "max_new_tokens": 256,
        "prompt_token_count": 8000,
        "prompt_token_sha256": (
            "3774c8c85f5e98a445d2afea303987ea753ff297842781ff4a205fa6e8735ce4"
        ),
        "workload_digest": (
            "20d75fdc642d6cb971d8ac80e9b1d55e53cee61c9d5dbd4d4523ace12437ffde"
        ),
        "workload_file_sha256": (
            "69da17d9c684440e8527feacfb8912dae1d95a239dbe8deeafd5b8eb368d7d5d"
        ),
        "workload_id": "TA-QW-8K-AGENT-HELLO-1",
    }
    assert contract["schema"] == oracle.HETEROGENEOUS_GATE_1_LAUNCH_SCHEMA
    assert contract["profile_id"] == oracle.HETEROGENEOUS_GATE_1_PROFILE_ID
    assert contract["workload_set"] == {
        "manifest_sha256": (
            "6a7f49d621a93fcb02111916e1ab03ee600882629260742a66669c428ffa428c"
        ),
        "workload_set_id": (
            "4f3e2e3c3dd06683e4aa9374d317dbbbb9227ce90815cf6dc9fc93f195295bea"
        ),
    }
    assert contract["lane"] == {
        "category": "agentic_tool",
        "lane_index": 2,
        "sequence_id": "qwen3-8k-lane2-agent-hello",
        "source_id": "hello-world",
    }
    assert contract["workload"] == {
        key: workload_set["selected_lane"][key]
        for key in (
            "max_new_tokens",
            "prompt_token_count",
            "prompt_token_sha256",
            "workload_digest",
            "workload_file_sha256",
            "workload_id",
        )
    }
    assert contract["prefill"] == {
        "chunk_tokens": 512,
        "mode": "chunked_forward_kv_cache",
    }
    assert contract["numeric"] == {
        "attention_implementation": "sdpa",
        "dtype": "bfloat16",
    }
    assert contract["placement"] == {
        "cpu_memory_gib": 80,
        "gpu_memory_gib": 8,
        "policy": "auto",
    }


@pytest.mark.skipif(
    not oracle.DEFAULT_CHECKPOINT_LOCK.is_file()
    or not (oracle.DEFAULT_SNAPSHOT / "tokenizer.json").is_file(),
    reason="pinned Qwen tokenizer sources are unavailable",
)
@pytest.mark.parametrize("target", ["manifest", "index", "workload"])
def test_heterogeneous_gate_1_refuses_campaign_byte_tampering(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    target: str,
) -> None:
    copied = tmp_path / "campaign"
    shutil.copytree(oracle.DEFAULT_HETEROGENEOUS_MANIFEST.parent, copied)
    manifest_path = copied / "manifest.json"
    workload_root = copied / "workloads"
    monkeypatch.setattr(oracle, "DEFAULT_HETEROGENEOUS_MANIFEST", manifest_path)
    monkeypatch.setattr(oracle, "DEFAULT_HETEROGENEOUS_WORKLOADS", workload_root)
    monkeypatch.setattr(oracle, "verify_checkpoint_lock", lambda snapshot, lock: lock)

    tampered = {
        "manifest": manifest_path,
        "index": workload_root / "index.json",
        "workload": workload_root / "TA-QW-8K-1.json",
    }[target]
    tampered.write_bytes(tampered.read_bytes() + b" ")

    args = _heterogeneous_args()
    assert oracle._configure_heterogeneous_gate_1_production(args) == []
    index, _selected, bodies, identities = oracle._load_selected_workloads(
        args.workloads, args.only
    )
    with pytest.raises(oracle.OracleInputError, match="heterogeneous Gate-1"):
        oracle._authenticate_heterogeneous_gate_1_inputs(
            args, index, bodies, identities
        )


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
