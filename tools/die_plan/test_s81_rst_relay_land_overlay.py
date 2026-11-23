"""S81-RST-RELAY-LAND: s81_rst_relay_land_overlay.py on the repo rtl/lib/ot_rst_relay.sv.  Every edit is counted, no
source line moves, a second run and a foreign source are refused, and the define-off text keeps rst_n_in on the relay
clear.  The waveform equivalence (LANDED ot_rst_relay vs rtl/lib/ot_rst_relay_l.sv and vs the unpatched source, random
async rst_n_in, REGIONS 4/20 x TREE_STAGES 1/2) ran as an iverilog bench (tools/die_plan/s81_rst_relay_land_bench.sh).
    python3 -m pytest -q tools/die_plan/test_s81_rst_relay_land_overlay.py"""
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import s81_rst_relay_land_overlay as R  # noqa: E402

SRC = HERE.parents[1] / R.REL


def test_patch_counts_and_keeps_lines():
    s = SRC.read_text()
    out = R.patch(s)
    assert out.count("\n") == s.count("\n")
    assert out.count(R.TAG) == 1
    assert "`ifdef OT_RST_RELAY_LANDED sync_q[SYNC_STAGES-1] `else rst_n_in `endif" in out
    assert "always @(posedge clk or negedge relay_clr_n) begin" in out
    assert out.count("negedge rst_n_in") == 1                     # only the synchroniser keeps the port clear
    a, b = s.split("\n"), out.split("\n")
    assert sum(x != y for x, y in zip(a, b)) == 3                 # decl line + always + if


def test_refuses_twice_and_foreign_source():
    s = SRC.read_text()
    with pytest.raises(SystemExit, match="RRL_OVERLAY_TWICE"):
        R.patch(R.patch(s))
    with pytest.raises(SystemExit, match="RRL_OVERLAY_MISS"):
        R.patch(s.replace("reg [REGIONS-1:0] relay_q [0:TREE_STAGES-1];", "reg [REGIONS-1:0] relay_q [0:TREE_STAGES];"))


def test_main_on_tree(tmp_path):
    p = tmp_path / R.REL
    p.parent.mkdir(parents=True)
    p.write_text(SRC.read_text())
    assert R.main([str(tmp_path)]) == 0
    assert R.TAG in p.read_text()
    with pytest.raises(SystemExit, match="RRL_OVERLAY_TWICE"):
        R.main([str(tmp_path)])
