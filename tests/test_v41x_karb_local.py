"""Focused gate of the opt-in local K arbitration partition (tools/rtl_chip_v41x_karb_local.py --quick)."""
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
REC = ROOT / "results/rtl/chip_v41x_karb_local_equiv.json"


def test_record_pins_current_sources():
    d = json.loads(REC.read_text())
    assert d["pass"] and d["added_uncontended_k_round_trip_cycles"] == [4]
    assert all(r["pass"] and r["arms_identical"] for r in d["runs"])
    assert all(r["pass"] for r in d["kv_prefetch_bench"]) and len(d["kv_prefetch_bench"]) == 3
    for p, h in d["sources"].items():
        assert hashlib.sha256((ROOT / p).read_bytes()).hexdigest() == h, p


@pytest.mark.skipif(shutil.which("iverilog") is None, reason="iverilog not installed")
def test_quick_equivalence():
    r = subprocess.run([sys.executable, str(ROOT / "tools/rtl_chip_v41x_karb_local.py"), "--quick"],
                       capture_output=True, text=True, timeout=1800, cwd=ROOT)
    assert r.returncode == 0 and r.stdout.strip().endswith("PASS"), r.stdout[-2000:]
