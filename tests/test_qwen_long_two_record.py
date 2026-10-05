"""Verify the two exact Qwen vector tokens and post-token physical K close."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "results/rtl/hdc_qwen_long_two_254_255.json"


def test_qwen_long_two_record():
    rec = json.loads(RECORD.read_text())
    assert rec["schema"] == "opentallas.qwen-vector-long-two.v1"
    assert rec["status"] == "pass" and rec["phase"] == "simulation"
    assert rec["configuration"]["positions"] == [254, 255]
    assert rec["oracle"]["prefill_positions"] == 254
    assert rec["oracle"]["expected_tokens"] == [1561, 1561]
    for name, digest in rec["source_sha256"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name
    model = ROOT / "build/models/qwen3-reduced-v1/model-00001-of-00001.safetensors"
    if model.exists():
        assert hashlib.sha256(model.read_bytes()).hexdigest() == rec["model_sha256"]
    work = Path(rec["workdir"])
    if work.exists():
        for name, digest in rec["image_sha256"].items():
            assert hashlib.sha256((work / "img" / name).read_bytes()).hexdigest() == digest, name
        exe = work / f"obj_qd{rec['configuration']['hbm_queue_depth']}_room{rec['configuration']['hbm_pc_room']}" / "Vtb_hdc_core"
        if exe.exists():
            assert hashlib.sha256(exe.read_bytes()).hexdigest() == rec["binary_sha256"]
    first, second = rec["first_token"], rec["token"]
    assert first["position"] == 254 and second["position"] == 255
    assert first["actual"] == first["expected"] == second["actual"] == second["expected"] == 1561
    for step in (first, second):
        assert all(step[k] == 0 for k in ("fault", "logit_mismatches", "vm_mismatches", "kv_mismatches"))
        assert step["cycles"] > 0
    assert rec["cross_token_v_reads_after_write"] > 0
    assert rec["post_token_close"] == {"position": 256, "after_second": 1}
    assert rec["k_flush"] == {"accepted_writes": 128, "sectors_checked": 64,
                              "byte_mismatches": 0, "close_sent": 1}
    phys = rec["physical_hbm"]
    assert phys["boot_reads"] == 128 and phys["kv_reads"] > 128
    assert phys["kv_writes"] >= 128 and phys["committed_writes"] == phys["kv_writes"]
    assert phys["physical_byte_mismatches"] == phys["fault"] == 0
