"""Pinned real-checkpoint row-stream arithmetic evidence."""
import hashlib
import json
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]


def test_real_layer0_stream_numerics_record():
    r = json.loads((ROOT / "results/rtl/v41_w2_stream_exact.json").read_text())
    assert r["schema"] == "v41_w2_stream_exact_v1"
    assert r["rows_checked"] == 32
    assert len(r["expert_ids"]) == 6 and r["expert_ids"] == sorted(r["expert_ids"])
    for field in ("gathered_code_mismatches", "gathered_exp_mismatches",
                  "expert_output_mismatches", "final_mismatches", "shard_mismatches"):
        assert r[field] == 0
    for path, digest in r["source_sha256"].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest
    fixture = ROOT / r["fixture_path"]
    assert hashlib.sha256(fixture.read_bytes()).hexdigest() == r["fixture_sha256"]
    with np.load(fixture) as z:
        assert z["codes"].shape == (7, 4, 576) and z["codes"].dtype == np.uint8
        assert z["scales"].shape == (7, 4, 18) and z["scales"].dtype == np.uint8
        assert z["y_bf16"].shape == (4, 1280) and z["y_bf16"].dtype == np.uint16


def test_per_expert_stage_record():
    r = json.loads((ROOT / "results/rtl/v41_w2_expert_stream_stage.json").read_text())
    assert r["schema"] == "v41_w2_expert_stream_stage_v1"
    assert r["expert_count"] == 7
    assert r["per_expert_words_per_die"] * r["expert_count"] == r["fused_words_per_die"]
    assert len(r["cases"]) == 2
    for case in r["cases"]:
        assert case["passed"] and case["mismatches"] == case["timeout"] == 0
    v1 = r["serial_v1_projection"]
    assert v1["depth16_qtx2_seven_isolated_tail_cycles"] == 7 * r["cases"][0]["exposed_tail_cycles"]
    assert v1["extra_cycles_before_me_drains"] > 0
    for path, digest in r["source_sha256"].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest
