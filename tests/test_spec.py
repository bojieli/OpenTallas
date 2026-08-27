from __future__ import annotations

from pathlib import Path

from tools.check_spec import generate_traceability, validate


ROOT = Path(__file__).resolve().parents[1]


def test_specification_gate_and_traceability_are_current() -> None:
    generated = validate()
    checked_in = (ROOT / "spec" / "TRACEABILITY.md").read_text(encoding="utf-8")
    assert generated == checked_in


def test_traceability_generation_is_byte_deterministic() -> None:
    import json

    requirements = json.loads(
        (ROOT / "spec" / "requirements.json").read_text(encoding="utf-8")
    )["requirements"]
    checks = json.loads(
        (ROOT / "spec" / "verification.json").read_text(encoding="utf-8")
    )["planned_checks"]
    assert generate_traceability(requirements, checks) == generate_traceability(
        requirements, checks
    )


def test_qwen_dense_control_is_in_frozen_manifest() -> None:
    import json

    manifest = json.loads((ROOT / "spec" / "manifest.json").read_text(encoding="utf-8"))
    qwen = next(item for item in manifest["models"] if item["name"] == "Qwen3-8B")
    assert qwen["role"] == "dense_control"
    assert qwen["stages_midpoint"] == 1
    assert qwen["study_context_tokens"] == [8192]


def test_fault_campaign_is_source_complete() -> None:
    import json

    campaign = json.loads(
        (ROOT / "spec" / "fault_campaign.json").read_text(encoding="utf-8")
    )
    assert campaign["planned_site_count"] == 87
    assert len(campaign["sites"]) == 87
    assert len({site["id"] for site in campaign["sites"]}) == 87
    assert len(campaign["required_simulators"]) == 2
    assert campaign["external_gates"]
