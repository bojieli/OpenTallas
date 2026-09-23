import hashlib
import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import rtl_rom_pkg_link_campaign as campaign  # noqa: E402

pytestmark = pytest.mark.skipif(
    not (shutil.which("iverilog") and shutil.which("verilator")),
    reason="needs iverilog and verilator",
)


def test_link_is_cut_through_with_a_fixed_digital_overhead():
    result = campaign.run()
    assert result["status"] == "pass"
    free = [c for c in result["cases"] if c["label"] != "backpressure"]
    for case in free:
        assert case["first_flit_latency_cycles"] == campaign.FIRST
        assert case["last_flit_latency_cycles"] == campaign.FIRST + case["flits"] - 1
    backpressure = next(c for c in result["cases"] if c["label"] == "backpressure")
    assert backpressure["credit_stalls"] > 0 and backpressure["scoreboard_errors"] == 0


def test_committed_record_is_current():
    record = json.loads(campaign.OUT.read_text())
    assert record["status"] == "pass"
    for name, digest in record["input_sha256"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest
