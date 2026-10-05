"""Check the exact, source-pinned Qwen context-2048 RTL result."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "results/rtl/hdc_qwen_context_2048.json"


def test_qwen_context_2048_record():
    rec = json.loads(RECORD.read_text())
    assert rec["schema"] == "opentallas.qwen-vector-context-ladder.v1"
    assert rec["status"] == "pass" and rec["phase"] == "simulation"
    cfg, oracle = rec["configuration"], rec["oracle"]
    assert cfg["context_positions"] == 2048 and cfg["position"] == 2047
    assert cfg["reducer_levels"] == 7 and cfg["reducer_max_elements"] == 2048
    assert cfg["kv_window_lines"] == 4096 and cfg["kv_cfg_lead_cycles"] == 8192
    assert oracle["prefill_positions"] == 2047 and oracle["expected_token"] == 1509
    assert oracle["kv_words"] == oracle["vm_elements"] == 32768
    assert oracle["crom_words"] == 18177 and oracle["program_words"] == 97
    for name, digest in rec["source_sha256"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name
    model = ROOT / "build/models/qwen3-reduced-v1/model-00001-of-00001.safetensors"
    if model.exists():
        assert hashlib.sha256(model.read_bytes()).hexdigest() == rec["model_sha256"]
    work = Path(rec["workdir"])
    if work.exists():
        for name, digest in rec["image_sha256"].items():
            assert hashlib.sha256((work / "img" / name).read_bytes()).hexdigest() == digest, name
        obj = work / (f"obj_ctx2048_w4096_lead8192_qd{cfg['hbm_queue_depth']}"
                      f"_room{cfg['hbm_pc_room']}") / "Vtb_hdc_core"
        if obj.exists():
            assert hashlib.sha256(obj.read_bytes()).hexdigest() == rec["binary_sha256"]
    token, phys = rec["token"], rec["physical_hbm"]
    assert token["position"] == 2047 and token["actual"] == token["expected"] == 1509
    assert token["cycles"] == phys["cycles"] == 1357554
    assert all(token[k] == 0 for k in ("fault", "logit_mismatches", "vm_mismatches", "kv_mismatches"))
    assert phys["boot_reads"] == 128 and phys["kv_reads"] == 24456
    assert phys["kv_writes"] == phys["committed_writes"] == 8
    assert phys["physical_byte_mismatches"] == phys["fault"] == 0
    assert phys["acts"] == 10700 and phys["refreshes"] == 1381
    assert "KV_WINDOW_UNDERFLOW" not in rec["stdout"]
