"""Protect the bounded TP-2 DFlash acceptance evidence and its claim boundary."""
import hashlib
import json
from pathlib import Path

from tools.qwen3_dflash_int8_summary import summarize


ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "results/speculative"


def test_tp2_target_and_int8_drafter_records_are_greedy_and_source_pinned():
    paths = [SPEC / "qwen3_o4_tp2_int8_target_bf16_drafter_pilot.json",
             SPEC / "qwen3_o4_tp2_int8_target_drafter_pilot.json"]
    a, b = [json.loads(p.read_text()) for p in paths]
    for rec in (a, b):
        assert rec["tp2_target"] is True and rec["groups"] == 6144 and rec["block"] == 5
        assert rec["max_new"] == 128 and len(rec["rows"]) == 10
        for name, expected in rec["source_sha256"].items():
            assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected
        for row in rec["rows"]:
            assert not row["greedy_mismatches"]
            assert sum(row["acceptance_lengths"]) == row["tokens"] - 1
            assert len(row["acceptance_lengths"]) == row["cycles"]
    assert a["draft_weights"] == "bf16" and b["draft_weights"] == "w8" and b["draft_tp2"]
    assert [(r["workload"], r["prompt_id"]) for r in a["rows"]] == [
        (r["workload"], r["prompt_id"]) for r in b["rows"]]
    assert [r["output_ids"] for r in a["rows"]] == [r["output_ids"] for r in b["rows"]]


def test_tp2_summary_reproduces_the_record_and_stays_scoped():
    path = SPEC / "qwen3_o4_tp2_int8_target_drafter_pilot.json"
    rec = json.loads(path.read_text())
    actual = summarize(rec, path)
    saved = json.loads((SPEC / "qwen3_o4_tp2_int8_target_drafter_summary.json").read_text())
    assert actual["measurement"] == saved["measurement"]
    assert actual["ci95_prompt_bootstrap_stratified_by_workload"] == saved["ci95_prompt_bootstrap_stratified_by_workload"]
    assert actual["source_record_sha256"] == saved["source_record_sha256"]
    assert "Not a routed RTL throughput" in saved["scope"]
    assert saved["measurement"]["post_prefill_tokens"] == 912
    assert saved["measurement"]["int8_verify_cycles"] == 327


def test_full_length_reasoning_record_does_not_claim_a_two_prompt_ci():
    path = SPEC / "qwen3_o4_tp2_int8_reasoning_2k.json"
    rec = json.loads(path.read_text())
    saved = json.loads((SPEC / "qwen3_o4_tp2_int8_reasoning_2k_summary.json").read_text())
    assert rec["max_new"] == 2048 and len(rec["rows"]) == 2
    assert {r["workload"] for r in rec["rows"]} == {"reasoning_math500", "reasoning_humaneval"}
    assert all(r["tokens"] == 2048 and not r["greedy_mismatches"] for r in rec["rows"])
    assert saved["measurement"]["post_prefill_tokens"] == 4094
    assert saved["measurement"]["int8_verify_cycles"] == 1375
    assert "reason" in saved["ci95_prompt_bootstrap_stratified_by_workload"]
    assert summarize(rec, path)["measurement"] == saved["measurement"]
