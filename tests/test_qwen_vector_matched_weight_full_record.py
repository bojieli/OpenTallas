"""Validate the committed 18-step matched vector weight supply result."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "results/rtl/hdc_qwen_vector_matched_weight_full_g4sw16.json"
TWO = ROOT / "results/rtl/hdc_qwen_vector_matched_weight_g4sw16.json"


def test_matched_vector_weight_full_record():
    rec = json.loads(RECORD.read_text())
    smoke = json.loads(TWO.read_text())
    assert rec["schema"] == "opentallas.qwen-vector-matched-weight-full.v1"
    assert rec["status"] == "pass"
    assert rec["configuration"]["steps_executed"] == 18
    assert rec["configuration"]["prompt_steps"] == 16
    assert rec["configuration"]["generated_steps"] == 3
    assert rec["configuration"]["weight_chunk_words"] == 1536
    assert rec["image_sha256"] == smoke["image_sha256"]
    for name, digest in rec["source_sha256"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name
    model = ROOT / "build/models/qwen3-reduced-v1/model-00001-of-00001.safetensors"
    assert len(rec["model_sha256"]) == 64
    if model.exists():
        assert hashlib.sha256(model.read_bytes()).hexdigest() == rec["model_sha256"]
    assert rec["isa_tokens"][15:] == [1073, 382, 93]
    for mode, whbm in (("rom", 0), ("hbm", 1)):
        entry = rec[mode]
        assert entry["pass"] and entry["returncode"] == 0
        assert len(entry["steps"]) == 18
        assert [s["position"] for s in entry["steps"]] == list(range(18))
        assert [s["output_token"] for s in entry["steps"]] == rec["isa_tokens"]
        assert all(all(s[k] == 0 for k in ("fault", "logit_mismatches", "vm_mismatches",
                                        "kv_mismatches")) for s in entry["steps"])
        summary, phys, weights = entry["summary"], entry["physical_hbm"], entry["weights"]
        assert summary["steps"] == 18 and summary["generated"] == 3
        assert all(summary[k] == 0 for k in ("token_mismatches", "logit_mismatches",
                                             "vm_mismatches", "kv_mismatches",
                                             "physical_byte_mismatches"))
        assert phys["boot_done"] == 1 and phys["boot_reads"] == 128
        assert phys["v_reads_after_write"] > 0 and phys["k_flush_writes"] >= 128
        assert phys["byte_mismatches"] == phys["fault"] == 0 and phys["drained"] == 1
        assert phys["committed_writes"] == phys["writes"]
        assert weights["whbm"] == whbm and weights["boot_cycles"] > 0
        assert weights["weight_delivery_mismatches"] == weights["weight_fault"] == 0
        p = entry["hbm_read_pipeline"]
        assert p["accepted_sectors"] >= p["scheduled_sectors"] >= p["delivered_sectors"]
        assert p["accepted_sectors"] == phys["reads"] + weights["weight_sector_reads"]
        assert p["delivered_sectors"] == weights["kv_completed_sectors"] + weights["weight_completed_sectors"]
        assert p["queued_unscheduled_sectors"] == p["accepted_sectors"] - p["scheduled_sectors"]
        assert p["scheduled_undelivered_sectors"] == p["scheduled_sectors"] - p["delivered_sectors"]
        if whbm:
            assert weights["weight_sector_reads"] > 0 and weights["weight_consumed"] > 0
            assert weights["arb_weight_denied_cycles"] > 0
        else:
            assert weights["weight_sector_reads"] == 0
