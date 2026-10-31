"""DIE-KV-10: gen_core_kit_kv --related-clock (opt-in related fclk root for count-aligned landing-ring cores).
Default SDC text is byte-identical; with fclk related the SDC is the S81-KITS-1 landing form and passes sdc_lint;
a relaxed window, a clock group or a missing landed context fails closed."""
import importlib.util
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
sys.path.insert(0, str(REPO / "tools/die_plan"))
import sdc_lint  # noqa: E402

spec = importlib.util.spec_from_file_location("gk", HERE / "gen_core_kit_kv.py")
gk = importlib.util.module_from_spec(spec); spec.loader.exec_module(gk)

PER, INS, TOL = 833.333, 250.0, 20.0
CLKS, RSTS = ["clk", "fclk"], ["rst_n", "t_rst_n"]
INS_P, OUTS = ["rst_n", "t_rst_n", "d", "strap_k"], ["q", "ready", "fault"]


def _ctx(landed=("fclk",)):
    return dict(period_ps=PER, insertion_ps=INS, insertion_ff_ps=INS * 0.81, insertion_tol_ps=TOL, clock_ports=CLKS,
                inputs=INS_P, outputs=OUTS, unc_setup_ps=sdc_lint.POLICY_SETUP_PS, unc_hold_ps=sdc_lint.POLICY_HOLD_PS,
                time_unit_ps=1.0, io_floor_ps={p: gk.IO_BUDGET * PER for p in INS_P + OUTS}, port_latency_ps={},
                straps=["strap_k"], **({"landed_clock_inputs": list(landed)} if landed else {}))


def _sdc(related=()):
    return gk.sdc(PER, INS, TOL, CLKS, RSTS, "ring", ["strap_k"], None, related)


def test_default_byte_identical():
    assert _sdc() == gk.sdc(PER, INS, TOL, CLKS, RSTS, "ring", ["strap_k"], None)
    assert "create_clock -name clk -period 833.3330 [get_ports {clk fclk}]" in _sdc()
    assert "ignore_clock_latency" not in _sdc()


def test_related_fclk_root_lints_clean():
    t = _sdc(["fclk"])
    assert "create_clock -name clk -period 833.3330 [get_ports {clk}]" in t
    assert "create_clock -name fclk -period 833.3330 [get_ports {fclk}]" in t
    assert t.count("-ignore_clock_latency") == 4 and "416.6665" in t
    assert "set_clock_groups" not in t and "ASSUMPTION" not in t
    assert sdc_lint.lint(t, **_ctx()) == []


@pytest.mark.parametrize("mut,msg", [
    (lambda t: t.replace("-ignore_clock_latency 416.6665", "-ignore_clock_latency 500.0000", 1), "window"),
    (lambda t: t + "set_clock_groups -asynchronous -group clk -group fclk\n", "forbidden"),
    (lambda t: t + "set_false_path -from [get_clocks fclk] -to [get_clocks clk]\n", "fail-closed"),
])
def test_related_fclk_negatives(mut, msg):
    bad = mut(_sdc(["fclk"]))
    errs = sdc_lint.lint(bad, **_ctx())
    assert any(msg in e for e in errs), errs


def test_related_needs_landed_context_and_a_core_clock():
    assert sdc_lint.lint(_sdc(["fclk"]), **_ctx(landed=None))      # without landed context: fail-closed
    with pytest.raises(SystemExit):
        _sdc(["clk", "fclk"])
