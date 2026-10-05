"""Verify two exact Qwen vector tokens under tagged HBM queue pressure."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "results/rtl/hdc_qwen_long_two_stress_254_255.json"
CONTROL = ROOT / "results/rtl/hdc_qwen_long_two_254_255.json"


def test_qwen_long_two_stress_record():
    rec = json.loads(RECORD.read_text())
    control = json.loads(CONTROL.read_text())
    assert rec["schema"] == "opentallas.qwen-vector-long-two-stress.v1"
    assert rec["status"] == "pass" and rec["phase"] == "simulation"
    assert rec["configuration"]["positions"] == [254, 255]
    assert rec["oracle"]["prefill_positions"] == 254
    assert rec["oracle"]["expected_tokens"] == [1561, 1561]
    assert rec["image_sha256"] == control["image_sha256"]
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
    st = rec["stress"]
    assert st["model_backpressure"] > 0 and st["core_stalls"] > 0
    assert 0 < st["offers"] <= 512 and st["deliberate_holds"] == st["offers"]
    assert st["accepted_requests"] > 0
    assert st["completed_beats"] == 16 * st["accepted_requests"]
    assert st["response_errors"] == 0
    assert st["core_completed_beats"] == st["core_accepted_beats"]
    assert st["core_accepted_beats"] == phys["kv_reads"] == 5904
    inj = rec["injector"]
    assert inj["deterministic"] and inj["seed"] is None
    assert (inj["scratch_first_sector"], inj["scratch_last_sector"]) == (2048, 2063)
    assert inj["deliberate_core_hold_cycles"] == st["deliberate_holds"] == 5
    assert inj["core_protocol_stall_cycles"] == st["core_stalls"] == 26
    assert inj["accepted_sectors"] == inj["completed_sectors"] == 64
    assert [rec[k]["cycles"] for k in ("first_token", "token")] == [
        control[k]["cycles"] for k in ("first_token", "token")]
