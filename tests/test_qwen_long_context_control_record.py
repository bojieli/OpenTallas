"""Verify the exact context-256 control, including its unmet pressure target."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "results/rtl/hdc_qwen_long_context_256_control.json"


def test_qwen_long_context_control_record():
    rec = json.loads(RECORD.read_text())
    assert rec["schema"] == "opentallas.qwen-vector-long-context.v1"
    assert rec["gate"] == "exactness_control" and rec["status"] == "pass"
    assert rec["phase"] == "simulation" and rec["returncode"] == 0
    assert rec["pressure_target_met"] is False
    assert rec["configuration"]["context_positions"] == 256
    assert rec["oracle"]["prefill_positions"] == 255
    for name, digest in rec["source_sha256"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name
    model = ROOT / "build/models/qwen3-reduced-v1/model-00001-of-00001.safetensors"
    if model.exists():
        assert hashlib.sha256(model.read_bytes()).hexdigest() == rec["model_sha256"]
    work = Path(rec["workdir"])
    if work.exists():
        for name, digest in rec["image_sha256"].items():
            assert hashlib.sha256((work / "img" / name).read_bytes()).hexdigest() == digest, name
        exe = work / "obj_qd16_room4/Vtb_hdc_core"
        if exe.exists():
            assert hashlib.sha256(exe.read_bytes()).hexdigest() == rec["binary_sha256"]
    token = rec["token"]
    assert token["position"] == 255 and token["actual"] == token["expected"] == 1561
    assert all(token[k] == 0 for k in ("fault", "logit_mismatches", "vm_mismatches", "kv_mismatches"))
    phys = rec["physical_hbm"]
    assert phys["boot_reads"] == 128 and phys["kv_reads"] == 2952
    assert phys["kv_writes"] == phys["committed_writes"] == 8
    assert phys["physical_byte_mismatches"] == phys["fault"] == 0
    assert phys["backpressure_cycles"] == 0
    assert "FAIL" in rec["stdout"] and "PASS" not in rec["stdout"]
