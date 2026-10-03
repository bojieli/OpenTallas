"""Cached simulation must neither create CPU goldens nor accept crashed RTL."""
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("cached", ROOT / "tools/dsrom_dspark_cached_rtl.py")
cached = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cached)


def test_missing_image_refuses_before_build_or_golden(tmp_path):
    job = tmp_path / "job"
    r = subprocess.run([sys.executable, str(ROOT / "tools/dsrom_dspark_cached_rtl.py"),
                        "--part", "missing", "--image", str(tmp_path / "absent"),
                        "--run-dir", str(job)], capture_output=True, text=True)
    assert r.returncode != 0 and not job.exists()
    assert "run.args" in r.stderr and "hdc_golden" not in r.stderr


def test_crashed_or_faulted_rtl_cannot_pass():
    names = ("prompt", "generated", "iters", "token_mismatches", "accept_mismatches", "heads",
             "head_mismatches", "prefill_cycles", "iter_cycles", "draft_cycles", "vm_mismatch", "kv_mismatch")
    summary = "HDC41_MTP " + " ".join(k + r"=(\d+)" for k in names)
    fake = SimpleNamespace(C=SimpleNamespace(SUMMARY=re.compile(summary),
        ITER=re.compile(r"ITER it=(\d+) pos=(\d+) in=(\d+) accepted=(\d+) emitted=(\d+) cycles=(\d+) draft_cycles=(\d+) fault=(\d+)")),
        XCNT=re.compile(r"XCNT unit=(\w+) ops=(\d+) elems=(\d+)"),
        X=SimpleNamespace(activation=lambda _: {"pass": True}))
    out = ("ITER it=0 pos=4 in=1 accepted=0 emitted=1 cycles=10 draft_cycles=2 fault=0\n"
           "HDC41_MTP " + " ".join(f"{k}={v}" for k, v in zip(names, (4, 2, 1, 0, 0, 10, 0, 40, 10, 2, 0, 0))) + "\nPASS\n")
    assert cached.parse_terminal(out, 0, fake)["pass"]
    assert not cached.parse_terminal(out, -9, fake)["pass"]
    assert not cached.parse_terminal(out.replace("fault=0", "fault=1"), 0, fake)["pass"]
    assert not cached.parse_terminal("TIMEOUT\nPASS\n", 0, fake)["pass"]


def test_empty_inventory_is_incomplete_and_immutable(tmp_path):
    (tmp_path / "parts").mkdir()
    cmd = [sys.executable, str(ROOT / "tools/dsrom_dspark_rtl_record.py"), "--dir", str(tmp_path)]
    assert subprocess.run(cmd, capture_output=True).returncode == 2
    target = tmp_path / "summary.json"
    original = target.read_bytes()
    assert json.loads(original)["status"] == "incomplete"
    assert len(json.loads(original)["missing_parts"]) == 10
    assert subprocess.run(cmd, capture_output=True).returncode != 0
    assert target.read_bytes() == original
