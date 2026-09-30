"""W11 streaming-domain units (V4.1 indexer element and attention tile at 1.2 GHz / 0.833 ns SS).

* the latency-cut arithmetic (q4dot QL 3..5, indexer bmul ML 3..5, attention bmul ML 3..6) equals the as-built
  LAT-3 unit delayed by the added cycles (Icarus, random operands, one per cycle);
* the record builder's latency model is the RTL's own localparam formulas, and gives the as-built latencies
  (indexer engine 48, attention tile 33 at TD = 32);
* the committed record: every routed unit closed at 0.833 ns with WC (SS) setup and WC + BC (FF) hold, and every
  bit-exactness gate at the streaming latencies passed.
"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import w11_stream_record as R  # noqa: E402

SUMMARY = R.OUT_DIR / "w11_stream_summary.json"


@pytest.mark.skipif(shutil.which("iverilog") is None, reason="iverilog not installed")
def test_cut_units_equal_lat3_delayed(tmp_path):
    srcs = ["rtl/test/tb_w11s_cut_equiv.sv", "rtl/hdc/v41x/ot_hdc_v41x_idx_arith.sv",
            "rtl/hdc/v41x/ot_hdc_v41x_attn_tile.sv", "rtl/hdc/ot_hdc_delay.sv", "rtl/hdc/ot_hdc_fastfp.sv"]
    vvp = tmp_path / "eq.vvp"
    subprocess.run(["iverilog", "-g2012", "-s", "tb_w11s_cut_equiv", "-o", str(vvp), *[str(ROOT / s) for s in srcs]],
                   check=True)
    out = subprocess.run(["vvp", "-n", str(vvp), "+NCYC=1500"], capture_output=True, text=True, check=True).stdout
    m = re.search(r"W11SEQ checked=(\d+) errors=(\d+)", out)
    assert m and int(m.group(1)) > 10000 and int(m.group(2)) == 0, out[-2000:]


def test_latency_model_is_the_rtl():
    idx = (ROOT / "rtl/hdc/v41x/ot_hdc_v41x_idx.sv").read_text()
    assert "LAT_C = 1 + QL + FPL * (NB - 1) + 1 + FML + FPL * 7 + 1" in idx
    assert "LAT_T = 1 + FPL * LVT + 1" in idx
    att = (ROOT / "rtl/hdc/v41x/ot_hdc_v41x_attn.sv").read_text()
    assert "TLAT = 3 + FML + FPL * (7 + LVT)" in att
    assert "GUARD_Q = skew(7) + 2" in att
    tile = (ROOT / "rtl/hdc/v41x/ot_hdc_v41x_attn_tile.sv").read_text()
    assert "LAT_CORE = FML + 7 * FPL + FPL * LV" in tile
    assert R.idx_engine_lat(3, 3, 3) + 1 == 48          # the as-built first-score latency
    assert R.idx_engine_lat(3, 3, 3, nb=1) + 1 == 39    # the reduced shape, measured by the campaign
    assert R.idx_engine_lat(7, 5, 5, nb=1) + 1 == 79    # measured at the streaming latencies (reduced shape)
    assert R.attn_tile_lat(3, 3, 64) == 36 and R.attn_guard_q(3) == 20


@pytest.mark.skipif(not SUMMARY.is_file(), reason="record not committed yet")
def test_committed_record():
    s = json.loads(SUMMARY.read_text())
    assert s["units"], "no routed units"
    for u in s["units"]:
        assert u["target_period_ns"] == pytest.approx(0.833)
        assert u["primary_corner"] == ["WC"] and u["hold_corners"] == ["WC", "BC"]
        if u["run"] in s.get("claimed_closed", []):
            assert u["closed"] and u["status"] == "pass" and u["setup_wns_ns"] >= 0 and u["hold_wns_ns"] >= 0
            assert u["drc"] == 0 and u["max_slew_violations"] == 0 and u["max_cap_violations"] == 0
    for name, g in s["gates"].items():
        assert g.get("status", "pass") == "pass" and g.get("bit_exact", True), name
