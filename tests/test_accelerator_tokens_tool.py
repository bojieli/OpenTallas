"""What `tools/run_accelerator_tokens.py` refuses, and what it compares.

The first DeepSeek ROM token was produced by a session scratchpad that compared
its result against the *wrong* workload's gold, wrote ``matches_gold_prefix:
false`` into its own artifact, and was rescued by a human comparing the right
two lists afterwards.  These are the checks that make that a refusal rather
than a footnote.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import pytest
from tokenizers import Tokenizer
from tokenizers.models import WordLevel
from tokenizers.pre_tokenizers import Whitespace

REPO = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "run_accelerator_tokens", REPO / "tools" / "run_accelerator_tokens.py"
)
tool = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(tool)


def _reference(tmp_path: Path, body: dict) -> Path:
    path = tmp_path / "oracle.json"
    path.write_text(json.dumps(body))
    return path


WORKLOAD = {"workload_id": "W-1", "digest": "abc123", "token_ids": [1, 2, 3]}


def _tokenizer_checkpoint(tmp_path: Path) -> tuple[Path, str]:
    checkpoint = tmp_path / "checkpoint"
    checkpoint.mkdir()
    tokenizer = Tokenizer(
        WordLevel(
            {
                "[UNK]": 0,
                "hello": 1,
                "world": 2,
                "answer": 3,
                "<eos>": 4,
            },
            unk_token="[UNK]",
        )
    )
    tokenizer.pre_tokenizer = Whitespace()
    tokenizer.add_special_tokens(["<eos>"])
    path = checkpoint / "tokenizer.json"
    tokenizer.save(str(path))
    return checkpoint, hashlib.sha256(path.read_bytes()).hexdigest()


def test_existing_publish_root_is_refused_before_lowering(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    publish = tmp_path / "deployment"
    publish.mkdir()
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_accelerator_tokens.py",
            "--kernel-ir",
            str(tmp_path / "unused-ir.json"),
            "--backend",
            "hbm_sram",
            "--capability",
            str(tmp_path / "unused-capability.json"),
            "--workload",
            str(tmp_path / "unused-workload.json"),
            "--reference",
            str(tmp_path / "unused-reference.json"),
            "--checkpoint",
            str(tmp_path / "unused-checkpoint"),
            "--publish",
            str(publish),
            "--output",
            str(tmp_path / "result.json"),
        ],
    )

    assert tool.main() == 1
    assert "refusing to overwrite deployment root" in capsys.readouterr().err


def test_a_gold_produced_for_another_prompt_is_refused(tmp_path):
    reference = _reference(
        tmp_path,
        {
            "results": {
                "W-1": {
                    "workload_digest": "a-different-prompt",
                    "generated_token_ids": [7],
                    "expert_numeric_path": "fp8",
                }
            }
        },
    )
    with pytest.raises(SystemExit, match="two different prompts"):
        tool._load_gold(reference, WORKLOAD, "fp8")


def test_a_gold_from_another_numeric_path_is_refused(tmp_path):
    reference = _reference(
        tmp_path,
        {
            "results": {
                "W-1": {
                    "workload_digest": "abc123",
                    "generated_token_ids": [7],
                    "expert_numeric_path": "fp4",
                }
            }
        },
    )
    with pytest.raises(SystemExit, match="numeric path"):
        tool._load_gold(reference, WORKLOAD, "fp8")


def test_a_gold_for_a_workload_the_reference_does_not_hold_is_refused(tmp_path):
    reference = _reference(tmp_path, {"results": {"W-2": {}}})
    with pytest.raises(SystemExit, match="holds no result"):
        tool._load_gold(reference, WORKLOAD, "")


def test_the_matching_gold_is_returned(tmp_path):
    gold = {
        "workload_digest": "abc123",
        "generated_token_ids": [7, 8],
        "expert_numeric_path": "fp8",
    }
    reference = _reference(tmp_path, {"results": {"W-1": gold}})
    assert tool._load_gold(reference, WORKLOAD, "fp8") == gold


def test_two_empty_lists_are_not_an_agreement():
    """The vacuous pass this repository has produced once already."""
    assert tool._compare([], [])["agreement"] is False
    assert tool._compare([], [1, 2])["agreement"] is False
    assert tool._compare([1], [])["agreement"] is False


def test_a_capped_run_is_compared_against_the_oracle_prefix():
    body = tool._compare([13806, 345], [13806, 345, 7472, 55560])
    assert body["agreement"] is True
    assert body["first_divergence_index"] is None
    assert body["compared_tokens"] == 2


def test_a_divergence_names_the_step_and_both_tokens():
    body = tool._compare([13806, 999], [13806, 345, 7472])
    assert body["agreement"] is False
    assert body["first_divergence_index"] == 1
    assert body["divergence"] == {
        "index": 1,
        "accelerator_token_id": 999,
        "oracle_token_id": 345,
    }


def _steps(tokens: list[int]) -> list[dict]:
    return [
        {
            "step": index,
            "transaction_id": index + 1,
            "produced_tokens": [token],
            "final_token_id": token,
            "status": "SUCCESS",
            "trap": "NONE",
        }
        for index, token in enumerate(tokens)
    ]


def test_exact_cap_terminal_contract_refuses_a_matching_short_prefix():
    body = tool._terminal_acceptance(
        contract="exact_cap",
        got=[10, 11],
        gold=[10, 11, 12],
        stop_reason="max_new_tokens",
        gold_stop_reason="max_new_tokens",
        limit=3,
        eos_token_ids=[99],
        per_step=_steps([10, 11]),
    )
    assert body["accepted"] is False
    assert "terminal_reason_allowed" in body["failed_checks"]
    assert "oracle_horizon_exact" in body["failed_checks"]


def test_exact_cap_terminal_contract_accepts_only_the_complete_oracle_horizon():
    tokens = [10, 11, 12]
    body = tool._terminal_acceptance(
        contract="exact_cap",
        got=tokens,
        gold=tokens,
        stop_reason="max_new_tokens",
        gold_stop_reason="max_new_tokens",
        limit=3,
        eos_token_ids=[99],
        per_step=_steps(tokens),
    )
    assert body["accepted"] is True
    assert body["terminal_kind"] == "cap"
    assert body["failed_checks"] == []


def test_eos_or_cap_contract_accepts_the_same_first_oracle_eos():
    tokens = [10, 99]
    body = tool._terminal_acceptance(
        contract="exact_eos_or_cap",
        got=tokens,
        gold=tokens,
        stop_reason="eos",
        gold_stop_reason="eos",
        limit=256,
        eos_token_ids=[98, 99],
        per_step=_steps(tokens),
    )
    assert body["accepted"] is True
    assert body["terminal_kind"] == "eos"


def test_eos_or_cap_contract_refuses_post_eos_or_bad_step_evidence():
    tokens = [10, 99, 12]
    steps = _steps(tokens)
    steps[-1]["transaction_id"] = steps[-2]["transaction_id"]
    body = tool._terminal_acceptance(
        contract="exact_eos_or_cap",
        got=tokens,
        gold=tokens,
        stop_reason="eos",
        gold_stop_reason="eos",
        limit=256,
        eos_token_ids=[99],
        per_step=steps,
    )
    assert body["accepted"] is False
    assert "terminal_reason_allowed" in body["failed_checks"]
    assert "no_post_eos_transaction" in body["failed_checks"]
    assert "transaction_ids_strictly_increasing" in body["failed_checks"]


def test_decoded_text_evidence_proves_natural_prompt_and_complete_output(tmp_path):
    checkpoint, tokenizer_sha256 = _tokenizer_checkpoint(tmp_path)

    evidence, problems = tool._decoded_text_evidence(
        checkpoint=checkpoint,
        tokenizer_sha256=tokenizer_sha256,
        prompt=[1, 2],
        generated=[3, 4],
        gold=[3, 4],
        workload={"rendered_text": "hello world"},
        gold_result={
            "raw_decoded_text": "answer <eos>",
            "visible_decoded_text": "answer",
        },
    )

    assert problems == []
    assert evidence["accepted"] is True
    assert evidence["input"]["rendered_text"] == "hello world"
    assert evidence["input"]["decode_matches_frozen_text"] is True
    assert evidence["input"]["encode_round_trip_matches_ids"] is True
    assert evidence["output"]["token_ids"] == [3, 4]
    assert evidence["output"]["raw_decoded_text"] == "answer <eos>"
    assert evidence["output"]["visible_decoded_text"] == "answer"
    assert evidence["output"]["raw_matches_oracle_compared_horizon"] is True
    assert evidence["output"]["visible_matches_oracle_compared_horizon"] is True
    assert evidence["output"]["raw_matches_frozen_oracle"] is True
    assert evidence["output"]["visible_matches_frozen_oracle"] is True


def test_decoded_text_evidence_accepts_only_the_exact_oracle_prefix(tmp_path):
    checkpoint, tokenizer_sha256 = _tokenizer_checkpoint(tmp_path)

    evidence, problems = tool._decoded_text_evidence(
        checkpoint=checkpoint,
        tokenizer_sha256=tokenizer_sha256,
        prompt=[1, 2],
        generated=[3],
        gold=[3, 2, 4],
        workload={"rendered_text": "hello world"},
        gold_result={
            "raw_decoded_text": "answer world <eos>",
            "visible_decoded_text": "answer world",
        },
    )

    assert problems == []
    assert evidence["accepted"] is True
    assert evidence["output"]["raw_decoded_text"] == "answer"
    assert evidence["oracle_compared_horizon"]["raw_decoded_text"] == "answer"
    assert evidence["oracle_compared_horizon"]["is_complete_frozen_oracle"] is False
    assert evidence["output"]["raw_matches_frozen_oracle"] is False


def test_decoded_text_evidence_rejects_tokenizer_prompt_and_output_drift(tmp_path):
    checkpoint, tokenizer_sha256 = _tokenizer_checkpoint(tmp_path)

    evidence, problems = tool._decoded_text_evidence(
        checkpoint=checkpoint,
        tokenizer_sha256="0" * 64,
        prompt=[1, 2],
        generated=[2],
        gold=[3],
        workload={"rendered_text": "hello"},
        gold_result={
            "raw_decoded_text": "answer",
            "visible_decoded_text": "answer",
        },
    )

    assert evidence["accepted"] is False
    assert evidence["tokenizer"]["sha256"] == tokenizer_sha256
    assert "checkpoint tokenizer.json does not match the workload lock" in problems
    assert "decoded prompt does not equal the frozen natural context" in problems
    assert "frozen natural context does not round-trip to prompt IDs" in problems
    assert "decoded output differs from the oracle compared horizon" in problems


def test_counter_evidence_retains_measured_node_splits_without_division():
    class Counters:
        def __init__(self, values):
            self.values = values

        def snapshot(self):
            return dict(self.values)

    class Device:
        node_count = 2
        node_counters = (
            Counters({"attention.context_positions": 7, "dma.transfers": 3}),
            Counters({"attention.context_positions": 7, "dma.transfers": 5}),
        )

    evidence = tool._counter_evidence(Device())
    assert evidence["counter_scope"] == {
        "aggregate": "cluster_total",
        "per_node": "engine_work_by_node_id",
        "node_count": 2,
        "node_counters_index": "NODE_ID",
        "reconciliation": (
            "cluster total equals the sum of per-node engine work plus "
            "cluster-only LINK, STATE, control, and host bookkeeping"
        ),
    }
    assert evidence["node_counters"] == [
        {"attention.context_positions": 7, "dma.transfers": 3},
        {"attention.context_positions": 7, "dma.transfers": 5},
    ]


def test_functional_source_lock_accepts_a_relative_script_path(monkeypatch):
    """The Make target invokes the tool as ``python3 tools/...``.

    Python may therefore expose a relative ``__file__``.  Provenance is written
    only after the expensive model run, so resolving that path is a release
    requirement rather than a cosmetic convenience.
    """

    monkeypatch.setattr(tool, "__file__", "tools/run_accelerator_tokens.py")
    sources = tool._functional_source_sha256()
    relative = "tools/run_accelerator_tokens.py"
    assert sources[relative] == hashlib.sha256(
        (REPO / relative).read_bytes()
    ).hexdigest()
    assert "runtime/sim/engines/tensor.py" in sources


def test_functional_source_lock_covers_admission_driver_and_selected_lowering():
    sources = tool._functional_source_sha256("hbm_sram")
    required = {
        "compiler/backends/hbm_sram/lower.py",
        "compiler/backends/hbm_sram/plan.py",
        "compiler/ir/v3/kernel_ir.py",
        "runtime/abi3/deployment.py",
        "runtime/abi3/records.py",
        "runtime/abi3/verifier.py",
        "runtime/driver.py",
        "runtime/evidence.py",
        "runtime/sim/backend.py",
        "runtime/sim/formats.py",
        "runtime/sim/generators.py",
    }
    assert required <= set(sources)
    assert "compiler/backends/rom/qwen3.py" not in sources
    for relative, digest in sources.items():
        assert digest == hashlib.sha256((REPO / relative).read_bytes()).hexdigest()


def test_loaded_input_identities_hash_files_and_state_checkpoint_boundary(tmp_path):
    files = {}
    for name in ("kernel", "capability", "workload", "reference"):
        path = tmp_path / f"{name}.json"
        path.write_bytes(name.encode())
        files[name] = path
    checkpoint = tmp_path / "checkpoint"
    checkpoint.mkdir()

    identities = tool._loaded_input_identities(
        kernel_ir=files["kernel"],
        capability=files["capability"],
        workload=files["workload"],
        reference=files["reference"],
        checkpoint=checkpoint,
    )

    for key, source in (
        ("kernel_ir", files["kernel"]),
        ("capability", files["capability"]),
        ("workload", files["workload"]),
        ("reference", files["reference"]),
    ):
        assert identities[key]["sha256"] == hashlib.sha256(
            source.read_bytes()
        ).hexdigest()
        assert identities[key]["bytes"] == source.stat().st_size
    assert identities["checkpoint_root"]["path"] == str(checkpoint.resolve())
    assert "deployment object segment" in identities["checkpoint_root"][
        "content_binding"
    ]
