"""Check the source-pinned, competing-read Qwen context-256 RTL gate."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "results/rtl/hdc_qwen_long_context_256_stress.json"


def test_qwen_long_context_record():
    rec = json.loads(RECORD.read_text())
    assert rec["schema"] == "opentallas.qwen-vector-long-context-stress.v1"
    assert rec["status"] == "pass" and rec["phase"] == "simulation"
    assert rec["configuration"]["context_positions"] == 256
    assert rec["configuration"]["position"] == 255
    assert rec["oracle"]["prefill_positions"] == 255
    assert rec["oracle"]["expected_token"] == 1561
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
    token = rec["token"]
    assert token["position"] == 255 and token["actual"] == token["expected"] == 1561
    assert all(token[k] == 0 for k in ("fault", "logit_mismatches", "vm_mismatches", "kv_mismatches"))
    phys = rec["physical_hbm"]
    assert phys["boot_reads"] == 128 and phys["kv_reads"] > 128
    assert phys["kv_writes"] > 0 and phys["committed_writes"] == phys["kv_writes"]
    assert phys["physical_byte_mismatches"] == phys["fault"] == 0
    assert phys["backpressure_cycles"] > 0 and phys["system_request_stalls"] > 0
    assert 0 < phys["stress_offers"] <= 512
    assert phys["stress_holds"] == phys["stress_offers"]
    assert phys["stress_accepted"] > 0
    assert phys["stress_completed"] == 16 * phys["stress_accepted"]
    assert phys["stress_bad"] == 0
    assert phys["core_completed_beats"] == phys["core_accepted_beats"]
    assert phys["acts"] > 0
    inj = rec["injector"]
    assert inj["deterministic"] and inj["seed"] is None
    assert (inj["scratch_first_sector"], inj["scratch_last_sector"]) == (2048, 2063)
    assert inj["deliberate_core_hold_cycles"] == phys["stress_holds"] == 5
    assert inj["core_protocol_stall_cycles"] == phys["system_request_stalls"] == 26
    assert inj["accepted_sectors"] == inj["completed_sectors"] == 64
