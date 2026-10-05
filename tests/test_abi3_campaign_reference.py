"""What `tools/run_abi3_campaign.py` will and will not accept as gold.

`tools/run_accelerator_tokens.py` refuses an oracle result produced for a
different prompt, and `tests/test_accelerator_tokens_tool.py` holds it to that.
`run_abi3_campaign.py` drives the same deployments against the same oracle
files and had no such guard: it selected `results[workload_id]` and compared
against it, so a workload rebuilt under the same id -- a different corpus, a
different tokenizer revision, a truncation the tokenizer re-merged across --
would have been scored against gold for a prompt it never asked.

That is this repository's recurring defect shape: legal values on both sides,
no trap, and a token-agreement verdict that answers the wrong question.  The
DeepSeek sparse-attention threshold ladder is driven by this tool, so the guard
is load-bearing for the sparse gate.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "run_abi3_campaign", REPO / "tools" / "run_abi3_campaign.py"
)
tool = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(tool)

WORKLOAD = {"workload_id": "TA-DS-CTX-129-1", "digest": "the-prompt-that-ran"}


def _reference(tmp_path: Path, body: dict) -> Path:
    path = tmp_path / "oracle.json"
    path.write_text(json.dumps(body))
    return path


def test_gold_for_the_same_id_but_another_prompt_is_refused(tmp_path):
    reference = _reference(
        tmp_path,
        {
            "results": {
                "TA-DS-CTX-129-1": {
                    "workload_digest": "a-different-prompt",
                    "generated_token_ids": [6729, 223],
                }
            }
        },
    )
    with pytest.raises(SystemExit) as excinfo:
        tool._load_reference(reference, WORKLOAD)
    assert "two different prompts" in str(excinfo.value)


def test_gold_with_no_stated_digest_is_refused(tmp_path):
    """An oracle that never recorded which prompt it ran cannot be matched.

    Absence is not agreement.  Every oracle this repository has committed does
    record `workload_digest`, so requiring it weakens nothing.
    """
    reference = _reference(
        tmp_path,
        {"results": {"TA-DS-CTX-129-1": {"generated_token_ids": [6729]}}},
    )
    with pytest.raises(SystemExit):
        tool._load_reference(reference, WORKLOAD)


def test_gold_for_this_exact_prompt_is_returned(tmp_path):
    reference = _reference(
        tmp_path,
        {
            "results": {
                "TA-DS-CTX-129-1": {
                    "workload_digest": "the-prompt-that-ran",
                    "generated_token_ids": [6729, 223, 24],
                }
            }
        },
    )
    assert tool._load_reference(reference, WORKLOAD) == [6729, 223, 24]


def test_a_missing_workload_id_still_names_what_the_oracle_holds(tmp_path):
    reference = _reference(
        tmp_path,
        {
            "results": {
                "TA-DS-CTX-160-1": {
                    "workload_digest": "the-prompt-that-ran",
                    "generated_token_ids": [201],
                }
            }
        },
    )
    with pytest.raises(SystemExit) as excinfo:
        tool._load_reference(reference, WORKLOAD)
    assert "TA-DS-CTX-160-1" in str(excinfo.value)


def test_no_reference_named_is_not_an_error(tmp_path):
    assert tool._load_reference(None, WORKLOAD) is None
