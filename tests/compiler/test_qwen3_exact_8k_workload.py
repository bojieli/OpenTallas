from __future__ import annotations

import copy
from pathlib import Path

import pytest

from compiler.tensor_accelerator.common import (
    canonical_json_bytes,
    load_strict_json,
    sha256_bytes,
)
from compiler.tensor_accelerator.qwen_chat import QwenChatTokenizer
from compiler.workloads.qwen3_exact_8k import (
    AuthenticatedWorkloadTokenizer,
    EXPECTED_VISIBLE_ANSWER,
    QwenExact8KError,
    build_exact_8k_workload,
    load_construction,
    validate_construction,
    validate_materialized_workload,
)


ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = Path(
    "/home/ubuntu/.cache/huggingface/hub/models--Qwen--Qwen3-8B/"
    "snapshots/b968826d9c46dd6066d109eabc6255188de91218"
)
LOCK = (
    ROOT
    / "results/tensor_accelerator/qwen3_full_model_physical/source/"
    "checkpoint.lock.json"
)
CONSTRUCTION = ROOT / "configs/abi3/workloads/qwen3_exact_8k_chat_v1.json"
AUTHENTIC = pytest.mark.skipif(
    not (SNAPSHOT / "tokenizer.json").is_file() or not LOCK.is_file(),
    reason="pinned Qwen tokenizer sources are unavailable",
)


def _reidentify(value: dict, field: str) -> dict:
    body = {key: item for key, item in value.items() if key != field}
    return {**body, field: sha256_bytes(canonical_json_bytes(body))}


def _tokenizer() -> AuthenticatedWorkloadTokenizer:
    chat = QwenChatTokenizer(SNAPSHOT, load_strict_json(LOCK))
    return AuthenticatedWorkloadTokenizer(chat)


@AUTHENTIC
def test_exact_8k_workload_reuses_canonical_query_and_official_template() -> None:
    construction = load_construction(CONSTRUCTION)
    tokenizer = _tokenizer()
    workload = build_exact_8k_workload(
        tokenizer, construction, construction_path=CONSTRUCTION
    ).to_dict()

    assert workload["workload_id"] == "TA-QW-8K-1"
    assert workload["kind"] == "long_natural_chat"
    assert workload["prompt_token_count"] == len(workload["token_ids"]) == 8000
    assert workload["max_new_tokens"] == 256
    assert workload["rendered_text"].startswith("<|im_start|>user\nMOBY-DICK;")
    assert workload["rendered_text"].endswith(
        "\n\nWhat is 17 multiplied by 23? Give only the number.<|im_end|>\n"
        "<|im_start|>assistant\n<think>\n\n</think>\n\n"
    )
    semantics = workload["metadata"]["canonical_semantics"]
    assert semantics["query_case_id"] == "arithmetic"
    assert semantics["expected_visible_answer"] == EXPECTED_VISIBLE_ANSWER == "391"
    assert semantics["workload_id"] == (
        "6e416e625cc278a50c392aa7500163ac5c8b1670756f3519a658c70529c2e998"
    )
    assert workload["metadata"]["oracle_output_tokens"] == (
        "absent_generate_externally"
    )
    assert "generated_token_ids" not in workload
    assert (
        validate_materialized_workload(
            workload,
            tokenizer,
            construction,
            construction_path=CONSTRUCTION,
        )
        == workload
    )


@AUTHENTIC
def test_exact_8k_construction_is_deterministic() -> None:
    construction = load_construction(CONSTRUCTION)
    tokenizer = _tokenizer()
    left = build_exact_8k_workload(
        tokenizer, construction, construction_path=CONSTRUCTION
    ).to_dict()
    right = build_exact_8k_workload(
        tokenizer, construction, construction_path=CONSTRUCTION
    ).to_dict()
    assert canonical_json_bytes(left) == canonical_json_bytes(right)
    assert left["digest"] == (
        "5c8fce7d61afd1e06b7a061133c0a6d639fac7d65739227f84e199d6c870297e"
    )
    assert left["rendered_text_sha256"] == (
        "1b85b8c0264a0f26054d69cbc1ffc076ba3971ecd91ad39e8ba51cd1820647cb"
    )


def test_exact_8k_construction_rejects_query_or_source_drift() -> None:
    construction = load_strict_json(CONSTRUCTION)

    wrong_query = copy.deepcopy(construction)
    wrong_query["canonical_semantics"]["query_case_id"] = "reasoning"
    wrong_query = _reidentify(wrong_query, "construction_id")
    with pytest.raises(QwenExact8KError, match="canonical query differs"):
        validate_construction(wrong_query)

    wrong_source = copy.deepcopy(construction)
    wrong_source["canonical_semantics"]["source_sha256"] = "f" * 64
    wrong_source = _reidentify(wrong_source, "construction_id")
    with pytest.raises(QwenExact8KError, match="semantics source differs"):
        validate_construction(wrong_source)
