"""Check the exact, source-pinned Qwen context-1024 RTL result."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "results/rtl/hdc_qwen_context_1024.json"


def test_qwen_context_1024_record():
    rec = json.loads(RECORD.read_text())
    assert rec["schema"] == "opentallas.qwen-vector-context-ladder.v1"
    assert rec["status"] == "pass" and rec["phase"] == "simulation"
    cfg, oracle = rec["configuration"], rec["oracle"]
    assert cfg["context_positions"] == 1024 and cfg["position"] == 1023
    assert cfg["reducer_levels"] == 6 and cfg["reducer_max_elements"] == 1024
    assert cfg["kv_window_lines"] == 2048 and cfg["kv_cfg_lead_cycles"] == 4096
    assert oracle["prefill_positions"] == 1023 and oracle["expected_token"] == 1509
    assert oracle["kv_words"] == oracle["vm_elements"] == 16384
    assert oracle["crom_words"] == 9985 and oracle["program_words"] == 97
    for name, digest in rec["source_sha256"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name
    model = ROOT / "build/models/qwen3-reduced-v1/model-00001-of-00001.safetensors"
    if model.exists():
        assert hashlib.sha256(model.read_bytes()).hexdigest() == rec["model_sha256"]
    work = Path(rec["workdir"])
    if work.exists():
        for name, digest in rec["image_sha256"].items():
            assert hashlib.sha256((work / "img" / name).read_bytes()).hexdigest() == digest, name
        obj = work / (f"obj_ctx1024_w2048_lead4096_qd{cfg['hbm_queue_depth']}"
                      f"_room{cfg['hbm_pc_room']}") / "Vtb_hdc_core"
        if obj.exists():
            assert hashlib.sha256(obj.read_bytes()).hexdigest() == rec["binary_sha256"]
    token, phys = rec["token"], rec["physical_hbm"]
    assert token["position"] == 1023 and token["actual"] == token["expected"] == 1509
    assert all(token[k] == 0 for k in ("fault", "logit_mismatches", "vm_mismatches", "kv_mismatches"))
    assert phys["boot_reads"] == 128 and phys["kv_reads"] == 12168
    assert phys["kv_writes"] == phys["committed_writes"] == 8
    assert phys["physical_byte_mismatches"] == phys["fault"] == 0
    assert "KV_WINDOW_UNDERFLOW" not in rec["stdout"]
