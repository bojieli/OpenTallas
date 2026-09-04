"""Focused qualification for the exact-8K heterogeneous Qwen contracts."""

from __future__ import annotations

import copy
import hashlib
from pathlib import Path
import shutil
from typing import Any, Callable

import pytest
from jsonschema import Draft202012Validator

from compiler.tensor_accelerator.common import (
    canonical_json_bytes,
    load_strict_json,
)
from compiler.workloads import qwen3_heterogeneous_8k as campaign


REPO = Path(__file__).resolve().parents[1]
COMMITTED = (
    REPO / "configs/abi3/workloads/qwen3_heterogeneous_exact_8k_v1"
)


def _write(path: Path, body: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(body))


def _file(path: Path, root: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    return {
        "path": path.relative_to(root).as_posix(),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "size_bytes": len(raw),
    }


def _identity(body: dict[str, Any], field: str) -> None:
    body.pop(field, None)
    body[field] = hashlib.sha256(canonical_json_bytes(body)).hexdigest()


class FrozenCodec:
    """Small exact mapping; it never depends on a local model/tokenizer cache."""

    def __init__(self, root: Path):
        manifest = load_strict_json(root / "manifest.json")
        self._encodes: dict[str, list[int]] = {}
        self._raw: dict[tuple[int, ...], str] = {}
        self._visible: dict[tuple[int, ...], str] = {}
        for lane in manifest["lanes"]:
            body = load_strict_json(root / lane["workload"]["file"]["path"])
            ids = tuple(body["token_ids"])
            self._encodes[body["rendered_text"]] = list(ids)
            self._raw[ids] = body["rendered_text"]
            self._visible[ids] = body["rendered_text"]

    def add_output(self, ids: list[int], raw: str, visible: str) -> None:
        key = tuple(ids)
        self._raw[key] = raw
        self._visible[key] = visible

    def encode(self, text: str) -> list[int]:
        if text not in self._encodes:
            raise ValueError("unknown fixture text")
        return list(self._encodes[text])

    def decode(self, ids: list[int], *, skip_special_tokens: bool = False) -> str:
        table = self._visible if skip_special_tokens else self._raw
        return table[tuple(ids)]


@pytest.fixture()
def frozen_campaign(tmp_path: Path) -> tuple[Path, FrozenCodec]:
    root = tmp_path / "campaign"
    shutil.copytree(COMMITTED, root)
    return root, FrozenCodec(root)


def _validate(root: Path, codec: FrozenCodec) -> campaign.CampaignValidation:
    return campaign.validate_workload_set(
        root / "manifest.json", codec=codec, repo=REPO
    )


def _refresh_manifest(root: Path, manifest: dict[str, Any]) -> None:
    _identity(manifest, "workload_set_id")
    _write(root / "manifest.json", manifest)


def _rewrite_workload(
    root: Path,
    lane_index: int,
    mutate: Callable[[dict[str, Any]], None],
) -> None:
    manifest = load_strict_json(root / "manifest.json")
    lane = manifest["lanes"][lane_index]
    path = root / lane["workload"]["file"]["path"]
    body = load_strict_json(path)
    mutate(body)
    body["digest"] = campaign.workload_digest(body)
    _write(path, body)
    lane["workload"]["file"] = _file(path, root)
    lane["workload"]["prompt_token_sha256"] = campaign.prompt_token_sha256(
        body["token_ids"]
    )
    lane["workload"]["workload_digest"] = body["digest"]

    index_path = root / manifest["workload_index"]["path"]
    index = load_strict_json(index_path)
    index["workloads"][body["workload_id"]] = {
        "digest": body["digest"],
        "kind": body["kind"],
        "max_new_tokens": body["max_new_tokens"],
        "path": path.name,
        "prompt_token_count": body["prompt_token_count"],
    }
    _write(index_path, index)
    manifest["workload_index"] = _file(index_path, root)
    _refresh_manifest(root, manifest)


def _oracle(
    root: Path,
    accepted: campaign.CampaignValidation,
    codec: FrozenCodec,
    lane_index: int,
) -> Path:
    lane = accepted.manifest["lanes"][lane_index]
    workload = accepted.workloads[lane_index]
    generated = [100 + lane_index, campaign.EOS_TOKEN_IDS[0]]
    raw = f"lane-{lane_index}<|im_end|>"
    visible = f"lane-{lane_index}"
    codec.add_output(generated, raw, visible)
    body = {
        "schema": campaign.REFERENCE_ORACLE_SCHEMA,
        "evidence_class": "external_reference_comparator",
        "not_a_claim": [
            "accelerator_execution",
            "artifact_only_execution",
            "timing_or_performance",
        ],
        "model_id": "qwen3-8b",
        "snapshot": f"Qwen/Qwen3-8B@{campaign.SOURCE_REVISION}",
        "tokenizer_sha256": accepted.manifest["model"]["tokenizer_sha256"],
        "torch_version": "test-fixture",
        "transformers_version": "test-fixture",
        "dtype": "bfloat16",
        "selection": "greedy_lowest_token_id_argmax",
        "device_map": "test-fixture",
        "attention_implementation": "sdpa",
        "producer": {
            "tool": campaign.ORACLE_TOOL,
            "tool_version": "test-structure-only",
            "command_argv": [campaign.ORACLE_TOOL, "--only", workload["workload_id"]],
            "selected_workload_ids": [workload["workload_id"]],
        },
        "input_identity": {
            "checkpoint_lock": dict(accepted.manifest["model"]["checkpoint_lock"]),
            "workload_index": dict(accepted.manifest["workload_index"]),
            "workload_sources": {
                workload["workload_id"]: dict(lane["workload"]["file"])
            },
        },
        "production_checkpoint_preflight": {
            "completed_before_model_framework_import": True,
            "full_byte_hash_verified": True,
            "lock_id": accepted.manifest["model"]["checkpoint_lock"]["lock_id"],
            "lock_source_sha256": accepted.manifest["model"]["checkpoint_lock"][
                "sha256"
            ],
        },
        "production_launch": {
            "explicitly_requested": True,
            "contract": {
                "schema": "opentallas.qwen3.gate1_launch.v1",
                "profile_id": "test-structure-only",
                "workload_id": workload["workload_id"],
                "prompt_token_count": 8000,
                "max_new_tokens": 256,
                "selection": "greedy_lowest_token_id_argmax",
                "terminal": {
                    "eos_token_ids": list(campaign.EOS_TOKEN_IDS),
                    "include_eos_in_output": True,
                    "rule": "first_official_eos_or_exact_cap",
                },
            },
        },
        "results": {
            workload["workload_id"]: {
                "kind": workload["kind"],
                "workload_digest": workload["digest"],
                "prompt_token_count": 8000,
                "generated_token_ids": generated,
                "generated_token_count": len(generated),
                "stop_reason": "eos",
                "raw_decoded_text": raw,
                "visible_decoded_text": visible,
                "prefill_association": {
                    "schema": "opentallas.qwen3.prefill_association.v1"
                },
            }
        },
    }
    path = root / lane["oracle_binding"]["expected_path"]
    _write(path, body)
    return path


def test_schemas_are_draft_2020_12_valid() -> None:
    for path in (
        campaign.WORKLOAD_SET_SCHEMA_PATH,
        campaign.REFERENCE_SET_SCHEMA_PATH,
    ):
        Draft202012Validator.check_schema(load_strict_json(path))


def test_committed_preparation_set_is_exact_distinct_nested_and_nonclaiming(
    frozen_campaign: tuple[Path, FrozenCodec],
) -> None:
    root, codec = frozen_campaign
    accepted = _validate(root, codec)

    assert len(accepted.workloads) == 8
    assert {len(body["token_ids"]) for body in accepted.workloads} == {8000}
    assert {body["max_new_tokens"] for body in accepted.workloads} == {256}
    assert len({body["digest"] for body in accepted.workloads}) == 8
    assert len(
        {campaign.prompt_token_sha256(body["token_ids"]) for body in accepted.workloads}
    ) == 8
    assert [row["batch_size"] for row in accepted.manifest["batch_profiles"]] == [
        1,
        2,
        4,
        8,
    ]
    assert all(
        lane["oracle_binding"]["status"] == "pending_production_oracle"
        and lane["oracle_binding"]["file"] is None
        for lane in accepted.manifest["lanes"]
    )
    assert accepted.manifest["claim_boundary"] == {
        "accelerator_executed": False,
        "gate1_correctness_passed": False,
        "model_executed": False,
        "oracle_results_frozen": False,
        "runnable_batch_request": False,
        "tokenizer_only_construction": True,
        "tpot_claim": False,
    }


def test_byte_tamper_is_refused_before_semantic_use(
    frozen_campaign: tuple[Path, FrozenCodec],
) -> None:
    root, codec = frozen_campaign
    manifest = load_strict_json(root / "manifest.json")
    path = root / manifest["lanes"][0]["workload"]["file"]["path"]
    path.write_bytes(path.read_bytes() + b" ")

    with pytest.raises(campaign.QwenHeterogeneousCampaignError, match="content identity"):
        _validate(root, codec)


def test_non_8000_prompt_and_non_256_cap_are_refused(
    frozen_campaign: tuple[Path, FrozenCodec],
) -> None:
    root, codec = frozen_campaign

    def shorten(body: dict[str, Any]) -> None:
        body["token_ids"] = body["token_ids"][:-1]
        body["prompt_token_count"] = len(body["token_ids"])

    _rewrite_workload(root, 0, shorten)
    with pytest.raises(campaign.QwenHeterogeneousCampaignError, match="exactly 8,000"):
        _validate(root, codec)

    shutil.rmtree(root)
    shutil.copytree(COMMITTED, root)
    codec = FrozenCodec(root)
    _rewrite_workload(root, 0, lambda body: body.__setitem__("max_new_tokens", 255))
    with pytest.raises(campaign.QwenHeterogeneousCampaignError, match="not 256"):
        _validate(root, codec)


def test_cloned_prompt_is_refused_even_with_recomputed_hashes(
    frozen_campaign: tuple[Path, FrozenCodec],
) -> None:
    root, _codec = frozen_campaign
    manifest = load_strict_json(root / "manifest.json")
    first = load_strict_json(
        root / manifest["lanes"][0]["workload"]["file"]["path"]
    )

    def clone(body: dict[str, Any]) -> None:
        for field in (
            "prompt_token_count",
            "rendered_text",
            "rendered_text_sha256",
            "token_ids",
        ):
            body[field] = copy.deepcopy(first[field])

    _rewrite_workload(root, 1, clone)
    codec = FrozenCodec(root)
    with pytest.raises(campaign.QwenHeterogeneousCampaignError, match="cloned or duplicate"):
        _validate(root, codec)


def test_source_hash_nested_profiles_and_homogeneous_contract_fail_closed(
    frozen_campaign: tuple[Path, FrozenCodec],
) -> None:
    root, codec = frozen_campaign
    manifest = load_strict_json(root / "manifest.json")
    manifest["sources"]["corpus"]["sha256"] = "0" * 64
    _refresh_manifest(root, manifest)
    with pytest.raises(campaign.QwenHeterogeneousCampaignError, match="content identity"):
        _validate(root, codec)

    shutil.rmtree(root)
    shutil.copytree(COMMITTED, root)
    codec = FrozenCodec(root)
    manifest = load_strict_json(root / "manifest.json")
    manifest["batch_profiles"][2]["sequence_ids"].reverse()
    _refresh_manifest(root, manifest)
    with pytest.raises(campaign.QwenHeterogeneousCampaignError, match="nested ordered"):
        _validate(root, codec)

    shutil.rmtree(root)
    shutil.copytree(COMMITTED, root)
    codec = FrozenCodec(root)
    manifest = load_strict_json(root / "manifest.json")
    manifest["execution_contract"][
        "homogeneous_comparison_contract_permitted"
    ] = True
    _refresh_manifest(root, manifest)
    with pytest.raises(campaign.QwenHeterogeneousCampaignError, match="schema violation"):
        _validate(root, codec)


def test_missing_oracle_blocks_reference_set_and_runnable_inputs(
    frozen_campaign: tuple[Path, FrozenCodec],
) -> None:
    root, codec = frozen_campaign
    accepted = _validate(root, codec)
    with pytest.raises(campaign.QwenHeterogeneousCampaignError, match="oracle is missing"):
        campaign.build_reference_set(accepted, codec=codec)


def test_eight_singleton_oracles_form_one_authenticated_reference_set(
    frozen_campaign: tuple[Path, FrozenCodec],
) -> None:
    root, codec = frozen_campaign
    accepted = _validate(root, codec)
    for lane_index in range(8):
        _oracle(root, accepted, codec, lane_index)

    body = campaign.build_reference_set(accepted, codec=codec)
    path = root / "reference-set.json"
    _write(path, body)

    assert campaign.validate_reference_set(
        path, campaign=accepted, codec=codec
    ) == body
    assert len(body["references"]) == 8
    assert len({row["oracle_result_sha256"] for row in body["references"]}) == 8
    assert body["claim_boundary"]["accelerator_execution"] is False
    assert body["claim_boundary"]["gate1_correctness_passed"] is False


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (
            lambda body, wid: body["producer"].__setitem__(
                "selected_workload_ids", ["different-workload"]
            ),
            "independently selected",
        ),
        (
            lambda body, wid: body["results"].__setitem__(
                "extra-workload", copy.deepcopy(body["results"][wid])
            ),
            "exactly one selected result",
        ),
        (
            lambda body, wid: body["results"][wid].__setitem__(
                "workload_digest", "0" * 64
            ),
            "illegal, padded, or misbound",
        ),
        (
            lambda body, wid: body["results"][wid].update(
                {
                    "generated_token_ids": [151645, 100],
                    "generated_token_count": 2,
                    "raw_decoded_text": "unused",
                    "visible_decoded_text": "unused",
                }
            ),
            "first-EOS-or-exact-256",
        ),
        (
            lambda body, wid: body["results"][wid].update(
                {
                    "generated_token_ids": [151669],
                    "generated_token_count": 1,
                    "stop_reason": "max_new_tokens",
                }
            ),
            "illegal, padded, or misbound",
        ),
        (
            lambda body, wid: body["results"][wid].update(
                {
                    "generated_token_ids": [100],
                    "generated_token_count": 1,
                    "stop_reason": "max_new_tokens",
                }
            ),
            "first-EOS-or-exact-256",
        ),
        (
            lambda body, wid: body["results"][wid].__setitem__(
                "raw_decoded_text", "tampered"
            ),
            "decoded text differs",
        ),
    ],
)
def test_oracle_tampering_is_refused(
    frozen_campaign: tuple[Path, FrozenCodec],
    mutate: Callable[[dict[str, Any], str], None],
    message: str,
) -> None:
    root, codec = frozen_campaign
    accepted = _validate(root, codec)
    path = _oracle(root, accepted, codec, 0)
    body = load_strict_json(path)
    workload_id = accepted.workloads[0]["workload_id"]
    mutate(body, workload_id)
    _write(path, body)

    with pytest.raises(campaign.QwenHeterogeneousCampaignError, match=message):
        campaign.validate_production_oracle(
            path, campaign=accepted, lane_index=0, codec=codec
        )
