"""Verify the source-pinned, two-token Qwen K-tile boundary gate."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "results/rtl/hdc_qwen_2047_2048_two.json"


def test_qwen_2047_2048_two_record():
    rec = json.loads(RECORD.read_text())
    assert rec["schema"] == "opentallas.qwen-vector-long-two.v2"
    assert rec["status"] == "pass" and rec["phase"] == "simulation"
    cfg, oracle = rec["configuration"], rec["oracle"]
    assert cfg["positions"] == [2047, 2048]
    assert cfg["context_positions"] == cfg["reducer_max_elements"] == 8192
    assert cfg["kv_window_lines"] == 16384
    assert oracle["prefill_positions"] == 2047
    assert oracle["expected_tokens"] == [1509, 1509]
    assert oracle["kv_words"] == oracle["vm_elements"] == 131072
    assert oracle["program_words"] == 97
    for name, digest in rec["source_sha256"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name
    model = ROOT / "build/models/qwen3-reduced-v1/model-00001-of-00001.safetensors"
    if model.exists():
        assert hashlib.sha256(model.read_bytes()).hexdigest() == rec["model_sha256"]
    work = Path(rec["workdir"])
    if work.exists():
        for name, digest in rec["image_sha256"].items():
            assert hashlib.sha256((work / "img" / name).read_bytes()).hexdigest() == digest, name
        exe = (work / f"obj_8k_qd{cfg['hbm_queue_depth']}_room{cfg['hbm_pc_room']}"
               / "Vtb_hdc_core")
        if exe.exists():
            assert hashlib.sha256(exe.read_bytes()).hexdigest() == rec["binary_sha256"]
    first, second = rec["first_token"], rec["token"]
    assert first["position"] == 2047 and second["position"] == 2048
    assert first["actual"] == first["expected"] == oracle["expected_tokens"][0]
    assert second["actual"] == second["expected"] == oracle["expected_tokens"][1]
    assert first["cycles"] == 1647282 and second["cycles"] == 1663928
    for step in (first, second):
        assert step["cycles"] > 0
        assert all(step[k] == 0 for k in
                   ("fault", "logit_mismatches", "vm_mismatches", "kv_mismatches"))
    assert rec["cross_token_v_reads_after_write"] == 8
    assert rec["k_tile_close"] == {"position": 2048, "tile": 127}
    assert rec["k_flush"] == {"accepted_writes": 128, "sectors_checked": 64,
                              "byte_mismatches": 0, "close_sent": 1}
    phys = rec["physical_hbm"]
    assert phys["boot_reads"] == 128 and phys["kv_reads"] == 49056
    assert phys["kv_writes"] == phys["committed_writes"] == 144
    assert phys["physical_byte_mismatches"] == phys["fault"] == 0
    assert phys["acts"] == 29272 and phys["refreshes"] == 3386
    assert "KV_WINDOW_UNDERFLOW" not in rec["stdout"]
