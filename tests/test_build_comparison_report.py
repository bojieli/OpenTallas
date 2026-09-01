"""Tests for governed comparison-report input normalization."""

from __future__ import annotations

import json

from tools.build_comparison_report import load_record


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
