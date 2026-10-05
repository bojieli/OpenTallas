"""The executable layer-0 collective sequence, not a fused descriptor proxy."""

import hashlib
import json
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import rtl_v41_tp_layer0_collectives as C  # noqa: E402


def test_descriptor_sequence_is_emitted_by_tp_builder():
    ds = C.descriptors()
    assert len(ds) == 12
    assert [d["source_words"] for d in ds] == [20, 8, 320, 36, 6, 36, 36, 36, 36, 36, 36, 80]
    assert sum(d["source_words"] for d in ds) == 686
    assert [d["seq"] for d in ds] == list(range(12))
    assert len([d for d in ds if ".act" in d["tag"]]) == 7


def test_exact_stage_record_is_current():
    record = json.loads((ROOT / "results/rtl/v41_tp_layer0_collective_sequence.json").read_text())
    assert record["schema"] == "v41_tp_layer0_collective_sequence_v1"
    assert record["passed"] and record["total_source_words_per_die"] == 686
    for p, digest in record["source_sha256"].items():
        assert hashlib.sha256((ROOT / p).read_bytes()).hexdigest() == digest, p
    assert len(record["program_bind_sha256"]) == 64
    assert "tools/hdc_replay_v41.py" in record["program_bind_sources"]
    bound = ROOT / record["program_bind_record"]
    if bound.exists():
        assert hashlib.sha256(bound.read_bytes()).hexdigest() == record["program_bind_sha256"]
    local = C.descriptors()
    for case, emitted in zip(record["cases"], local):
        for field in ("tag", "seq", "mode", "rnd", "source_elements", "source_words", "src_element", "dst_element"):
            assert case["descriptor"][field] == emitted[field]
    for case in record["cases"]:
        assert len(case["per_die"]) == 4
        assert case["cycles_from_issue_to_commit"] > 0
        assert case["cycles_blocked_to_all_done"] >= case["cycles_from_issue_to_commit"]
        assert case["startup_cycles"] + case["transfer_through_last_vm_cycles"] + case["commit_cycles_after_last_vm"] == case["cycles_blocked_to_all_done"]
