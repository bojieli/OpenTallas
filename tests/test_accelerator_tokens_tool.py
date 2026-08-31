"""What `tools/run_accelerator_tokens.py` refuses, and what it compares.

The first DeepSeek ROM token was produced by a session scratchpad that compared
its result against the *wrong* workload's gold, wrote ``matches_gold_prefix:
false`` into its own artifact, and was rescued by a human comparing the right
two lists afterwards.  These are the checks that make that a refusal rather
than a footnote.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

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
