"""Tests for governed comparison-report input normalization."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

import tools.build_comparison_report as comparison_tool
from tools.build_comparison_report import InputRefusal, load_governed_input, load_record


REPO = Path(__file__).resolve().parents[1]


def _governed_capture(deployment: str = "deployment-a") -> dict:
    return {
        "status": "pass",
        "backend": "hbm_sram",
        "evidence_class": "functional_artifact_only",
        "model": {
            "model_id": "model-a",
            "graph_id": "graph-a",
            "numeric_profile": "numeric-a",
        },
        "workload": {
            "workload_id": "workload-a",
            "workload_digest": "workload-digest",
            "prompt_token_count": 2,
            "max_new_tokens": 4,
            "tokenizer_sha256": "a" * 64,
        },
        "generation_policy_digest": "policy-digest",
        "generation_policy": {
            "selection_mode": 0,
            "tie_rule": 0,
            "eos_count": 1,
            "eos_token_0": 1,
            "vocabulary_size": 32,
        },
        "target": {
            "target_id": f"target-{deployment}",
            "backend": f"backend-{deployment}",
            "topology_class": 2,
            "node_count": 1,
            "capability_digest": f"capability-{deployment}",
            "deployment_digest": deployment,
            "technology_view": "view-a",
        },
        "generated_token_ids": [12, 13],
        "stop_reason": "max_new_tokens",
        "counters": {"instructions.retired": 7},
        "implementation_identity": {"backend": "numpy", "library_version": "2"},
        "verification": {"admitted": True},
        "oracle": {"agreement": True},
        "token_legitimacy_problems": [],
        "source_sha256": {
            relative: hashlib.sha256((REPO / relative).read_bytes()).hexdigest()
            for relative in (
                *comparison_tool.REQUIRED_EXECUTION_SOURCE_PATHS,
                *comparison_tool.BACKEND_EXECUTION_SOURCE_PATHS["hbm_sram"],
            )
        },
        "failure": None,
    }


def test_load_record_accepts_the_governed_token_capture_schema(tmp_path) -> None:
    capture = {
        "evidence_class": "functional_artifact_only",
        "model": {
            "model_id": "model-a",
            "graph_id": "graph-a",
            "numeric_profile": "numeric-a",
        },
        "workload": {
            "workload_id": "workload-a",
            "workload_digest": "workload-digest",
            "prompt_token_count": 2,
            "prompt_token_ids": [10, 11],
            "rendered_text_sha256": "rendered-digest",
            "max_new_tokens": 4,
        },
        "generation_policy_digest": "policy-digest",
        "generation_policy": {
            "selection_mode": 0,
            "tie_rule": 0,
            "eos_count": 1,
            "eos_token_0": 1,
            "vocabulary_size": 32,
        },
        "target": {
            "target_id": "target-a",
            "backend": "backend-a",
            "topology_class": 2,
            "node_count": 1,
            "capability": "extra/path.json",
            "capability_digest": "capability-digest",
            "deployment_digest": "deployment-digest",
            "technology_view": "view-a",
        },
        "generated_token_ids": [12, 13],
        "stop_reason": "max_new_tokens",
        "counters": {"instructions.retired": 7},
        "implementation_identity": {"backend": "numpy", "library_version": "2"},
        "failure": None,
    }
    path = tmp_path / "capture.json"
    path.write_text(json.dumps(capture))

    record = load_record(path)

    assert record.workload.model_id == "model-a"
    assert record.workload.graph_id == "graph-a"
    assert record.workload.numeric_profile == "numeric-a"
    assert record.workload.generation_policy_digest == "policy-digest"
    assert record.workload.generation_policy["vocabulary_size"] == 32
    assert record.target.target_id == "target-a"
    assert record.target.technology_view == "view-a"
    assert record.generated_token_ids == (12, 13)
    assert record.implementation_identity["backend"] == "numpy"


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda body: body.update(status="diverged"), "status is 'diverged'"),
        (
            lambda body: body["verification"].update(admitted=False),
            "verification.admitted is not true",
        ),
        (
            lambda body: body["oracle"].update(agreement=False),
            "oracle.agreement is not true",
        ),
        (
            lambda body: body["token_legitimacy_problems"].append("bad token"),
            "token legitimacy problems are present",
        ),
        (
            lambda body: body.pop("source_sha256"),
            "no non-empty source_sha256 map",
        ),
    ],
)
def test_governed_input_refuses_unpromotable_records(
    tmp_path, mutation, message
) -> None:
    body = _governed_capture()
    mutation(body)
    path = tmp_path / "capture.json"
    path.write_text(json.dumps(body))

    with pytest.raises(InputRefusal, match=message):
        load_governed_input(path)


def test_governed_input_refuses_a_stale_recorded_source(tmp_path) -> None:
    body = _governed_capture()
    body["source_sha256"]["runtime/evidence.py"] = "0" * 64
    path = tmp_path / "capture.json"
    path.write_text(json.dumps(body))

    with pytest.raises(InputRefusal, match="does not match the current source"):
        load_governed_input(path)


def test_governed_input_refuses_a_partial_source_map(tmp_path) -> None:
    body = _governed_capture()
    del body["source_sha256"]["runtime/abi3/verifier.py"]
    path = tmp_path / "capture.json"
    path.write_text(json.dumps(body))

    with pytest.raises(
        InputRefusal,
        match="record does not bind required source runtime/abi3/verifier.py",
    ):
        load_governed_input(path)


def test_comparison_records_input_artifact_and_comparison_source_hashes(
    tmp_path, monkeypatch
) -> None:
    rom = tmp_path / "rom.json"
    hbm = tmp_path / "hbm.json"
    output = tmp_path / "comparison.json"
    rom.write_text(json.dumps(_governed_capture("rom")))
    hbm.write_text(json.dumps(_governed_capture("hbm")))
    monkeypatch.setattr(
        "sys.argv",
        [
            "build_comparison_report.py",
            "--rom",
            str(rom),
            "--hbm",
            str(hbm),
            "--comparison-id",
            "test-comparison",
            "--output",
            str(output),
        ],
    )

    assert comparison_tool.main() == 0
    report = json.loads(output.read_text())
    assert report["sources"] == {
        "rom": {
            "path": str(rom),
            "sha256": hashlib.sha256(rom.read_bytes()).hexdigest(),
        },
        "hbm": {
            "path": str(hbm),
            "sha256": hashlib.sha256(hbm.read_bytes()).hexdigest(),
        },
    }
    assert set(report["source_sha256"]) == set(
        comparison_tool.COMPARISON_SOURCE_PATHS
    )
    for relative, digest in report["source_sha256"].items():
        assert digest == hashlib.sha256((REPO / relative).read_bytes()).hexdigest()
