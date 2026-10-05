"""Verify the source-pinned context-512 Qwen vector RTL gate."""
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "results/rtl/hdc_qwen_context_512.json"


def test_qwen_context_512_record():
    rec = json.loads(RECORD.read_text())
    assert rec["schema"] == "opentallas.qwen-vector-context-512.v1"
    assert rec["status"] == "pass" and rec["phase"] == "simulation"
    cfg = rec["configuration"]
    assert cfg["context_positions"] == 512 and cfg["position"] == 511
    assert cfg["reducer_levels"] == 5 and cfg["reducer_max_elements"] == 512
    assert cfg["kv_window_lines"] == 1024 and cfg["kv_cfg_lead_cycles"] == 2048
    oracle = rec["oracle"]
    assert oracle["prefill_positions"] == 511
    assert oracle["expected_token"] == 1509
    assert oracle["kv_words"] == 8192 and oracle["vm_elements"] == 8192
    assert oracle["crom_words"] == 5889
    # This frozen run predates the finite-extreme SFU repair. Each exact source
    # blob is reachable from the recorded mainline commits, including the
    # passing testbench added after the shared-source baseline.
    for name, digest in rec["source_sha256"].items():
        assert any(
            hashlib.sha256(subprocess.check_output(
                ["git", "show", f"{commit}:{name}"], cwd=ROOT,
                stderr=subprocess.DEVNULL,
            )).hexdigest() == digest
            for commit in rec["source_blob_commits"]
            if subprocess.run(["git", "cat-file", "-e", f"{commit}:{name}"], cwd=ROOT,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
        ), name
    model = ROOT / "build/models/qwen3-reduced-v1/model-00001-of-00001.safetensors"
    if model.exists():
        assert hashlib.sha256(model.read_bytes()).hexdigest() == rec["model_sha256"]
    work = Path(rec["workdir"])
    if work.exists():
        for name, digest in rec["image_sha256"].items():
            assert hashlib.sha256((work / "img" / name).read_bytes()).hexdigest() == digest, name
        exe = work / f"obj_qd{cfg['hbm_queue_depth']}_room{cfg['hbm_pc_room']}" / "Vtb_hdc_core"
        if exe.exists():
            assert hashlib.sha256(exe.read_bytes()).hexdigest() == rec["binary_sha256"]
    token = rec["token"]
    assert token["position"] == 511 and token["actual"] == token["expected"] == 1509
    assert all(token[k] == 0 for k in ("fault", "logit_mismatches", "vm_mismatches", "kv_mismatches"))
    phys = rec["physical_hbm"]
    assert phys["boot_reads"] == 128 and phys["kv_reads"] > 128
    assert phys["kv_writes"] > 0 and phys["committed_writes"] == phys["kv_writes"]
    assert phys["physical_byte_mismatches"] == phys["fault"] == 0
    assert phys["acts"] > 0
