"""Validate the committed matched vector weight supply checkpoint and its pins."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "results/rtl/hdc_qwen_vector_matched_weight_g4sw16.json"


def test_matched_vector_weight_record():
    rec = json.loads(RECORD.read_text())
    assert rec["schema"] == "opentallas.qwen-vector-matched-weight.v1"
    assert rec["status"] == "pass"
    assert rec["configuration"]["steps_executed"] == 2
    assert rec["configuration"]["groups"] == 4
    assert rec["configuration"]["su_width"] == 16
    assert rec["configuration"]["weight_chunk_words"] == 1536
    for name, digest in rec["source_sha256"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name
    model = ROOT / "build/models/qwen3-reduced-v1/model-00001-of-00001.safetensors"
    assert len(rec["model_sha256"]) == 64
    if model.exists():
        assert hashlib.sha256(model.read_bytes()).hexdigest() == rec["model_sha256"]
    for mode, whbm in (("rom", 0), ("hbm", 1)):
        entry = rec[mode]
        assert entry["pass"] and entry["returncode"] == 0
        assert len(entry["steps"]) == 2
        assert entry["summary"]["steps"] == 2
        assert entry["summary"]["token_mismatches"] == 0
        assert entry["summary"]["logit_mismatches"] == 0
        assert entry["summary"]["vm_mismatches"] == 0
        assert entry["summary"]["kv_mismatches"] == 0
        assert entry["summary"]["physical_byte_mismatches"] == 0
        assert [s["output_token"] for s in entry["steps"]] == [s["expected_token"] for s in entry["steps"]]
        phys, weights = entry["physical_hbm"], entry["weights"]
        pipe = entry["hbm_read_pipeline"]
        assert pipe["accepted_sectors"] >= pipe["scheduled_sectors"] >= pipe["delivered_sectors"]
        assert pipe["queued_unscheduled_sectors"] == pipe["accepted_sectors"] - pipe["scheduled_sectors"]
        assert pipe["scheduled_undelivered_sectors"] == pipe["scheduled_sectors"] - pipe["delivered_sectors"]
        assert pipe["scheduled_sectors"] == entry["hbm_timing"]["completed_reads"]
        assert phys["boot_done"] == 1 and phys["boot_reads"] == 128
        assert phys["v_reads_after_write"] > 0 and phys["byte_mismatches"] == 0
        assert phys["fault"] == 0 and phys["drained"] == 1
        assert pipe["accepted_sectors"] == phys["reads"] + weights["weight_sector_reads"]
        assert pipe["delivered_sectors"] == weights["kv_completed_sectors"] + weights["weight_completed_sectors"]
        assert weights["whbm"] == whbm and weights["boot_cycles"] > 0
        assert weights["weight_delivery_mismatches"] == 0 and weights["weight_fault"] == 0
        if whbm:
            assert weights["weight_req_reads"] > 0
            assert weights["weight_sector_reads"] > 0
            assert weights["weight_consumed"] > 0
        else:
            assert weights["weight_req_reads"] == 0
            assert weights["weight_sector_reads"] == 0
