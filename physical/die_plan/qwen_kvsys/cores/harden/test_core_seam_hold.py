#!/usr/bin/env python3
"""DIE-KV-13: gen_core_kit_kv --seam-hold opt-in (shared CLOCK-RESET IO-HOLD contract on KV core kits).
legacy default text unchanged; 25/25 -> min output -25 / min input 0 and sdc_lint PASS with the seam context;
a contract whose sender + receiver != seam, or a missing context, fails the lint (fail closed)."""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
sys.path[:0] = [str(HERE), str(REPO / "tools/die_plan")]
import gen_core_kit_kv as G
import sdc_lint

PER, INS, TOL = 833.0, 250.0, 40.0
CTX = dict(period_ps=PER, insertion_ps=INS, insertion_ff_ps=202.5, insertion_tol_ps=TOL, clock_ports=["ck"],
           inputs=["in_d", "rst_n"], outputs=["out_d"], unc_setup_ps=sdc_lint.POLICY_SETUP_PS,
           unc_hold_ps=sdc_lint.POLICY_HOLD_PS, time_unit_ps=1.0,
           io_floor_ps={p: G.IO_BUDGET * PER for p in ("in_d", "rst_n", "out_d")}, port_latency_ps={}, straps=[])


def _sdc(seam=None):
    return G.sdc(PER, INS, TOL, ["ck"], ["rst_n"], "t", (), None, (), seam)


def test_legacy_default_unchanged():
    s = _sdc()
    assert s == G.sdc(PER, INS, TOL, ["ck"], ["rst_n"], "t")
    assert "set_input_delay -min -40.0000 -clock vclk $non_clk_in" in s
    assert "set_output_delay -min 0.0000 -clock vclk [all_outputs]" in s and "seam_hold" not in s
    assert sdc_lint.lint(s, **CTX) == []


def test_seam_25_25():
    s = _sdc((25.0, 25.0))
    assert "set_input_delay -min 0.0000 -clock vclk $non_clk_in" in s
    assert "set_output_delay -min -25.0000 -clock vclk [all_outputs]" in s
    assert sdc_lint.lint(s, **CTX, hold_in_min_ps=0.0, hold_out_min_ps=-25.0, seam_hold_ps=25.0) == []


def test_fail_closed():
    s = _sdc((25.0, 25.0))
    assert sdc_lint.lint(s, **CTX)                      # seam SDC under the legacy context: min output -25 > 0 waived? no: lint must flag
    assert sdc_lint.lint(s, **CTX, hold_in_min_ps=0.0, hold_out_min_ps=-25.0, seam_hold_ps=40.0)


if __name__ == "__main__":
    for k, f in list(globals().items()):
        if k.startswith("test_"):
            f()
            print("PASS", k)
