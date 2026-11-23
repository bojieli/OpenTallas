"""S81-CRR-PRE: s81_crr_pre_overlay.py on the J8 event-tree ot_s81sl_crr text (j8_cut_tree slice.sv lines 35-38).  Every
edit is counted, no source line moves, a second run and a foreign source are refused.  The PRE 0 / 2 delay check (q = d
delayed 1 / 3 edges, lock-step vs a reference shift register) ran as an iverilog bench (s81_crr_pre_bench.sh).
    python3 -m pytest -q tools/die_plan/test_s81_crr_pre_overlay.py"""
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import s81_crr_pre_overlay as R  # noqa: E402

J8 = ("// would be opt_merged; no reset of its own: assert and release both move one clk edge, the clock runs during reset).\n"
      "// ----\n(* keep_hierarchy, keep *)\n"
      "module ot_s81sl_crr (input wire clk, input wire d, output reg q);\n"
      "    always @(posedge clk) q <= d;\nendmodule\n\nmodule ot_s81sl_leaf #(\n")


def test_patch_counts_and_keeps_lines():
    out = R.patch(J8)
    assert out.count("\n") == J8.count("\n") and out.count(R.TAG) == 1
    assert "parameter integer PRE = `ifdef OT_S81SL_CRR_PRE2 2 `else 0 `endif" in out
    assert "begin : g_p0 always @(posedge clk) q <= d; end" in out and "q <= s[PRE-1];" in out
    a, b = J8.split("\n"), out.split("\n")
    assert sum(x != y for x, y in zip(a, b)) == 2


def test_refuses_twice_and_foreign_source(tmp_path):
    with pytest.raises(SystemExit, match="CRRPRE_OVERLAY_TWICE"):
        R.patch(R.patch(J8))
    with pytest.raises(SystemExit, match="CRRPRE_OVERLAY_MISS"):
        R.patch(J8.replace("q <= d;", "q <= ~d;"))
    p = tmp_path / R.REL
    p.parent.mkdir(parents=True)
    p.write_text(J8)
    assert R.main([str(tmp_path)]) == 0 and R.TAG in p.read_text()
