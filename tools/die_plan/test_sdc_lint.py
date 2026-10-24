"""sdc_lint (CP1-R10, COORD 10-24): the generated kit SDCs pass; every bug class it guards fails closed.
    python3 -m pytest -q tools/die_plan/test_sdc_lint.py"""
import gzip
import json
import sys
import tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_phys  # noqa: E402
import schema  # noqa: E402
import sdc_lint  # noqa: E402

TINY = json.loads((HERE / "examples" / "tiny_plan.json").read_text())
PAIR = json.loads((HERE / "examples" / "s81_pair" / "s81_pair_plan.json").read_text())


def _kit(raw, tn=None):
    P = schema.Plan(raw)
    tn = tn or next(iter(t for t in P.types if not P.types[t].get("hard")))
    txt = gen_phys.sdc(P, tn, gen_phys.type_pins(P, tn))
    return txt, sdc_lint.kit_context(P, tn)


def _errs(txt, ctx, **kw):
    return sdc_lint.lint(txt, **dict(ctx, **kw))


@pytest.mark.parametrize("raw", [TINY, PAIR])
def test_generated_kit_sdcs_pass(raw):
    P = schema.Plan(raw)
    for tn, t in P.types.items():
        if t.get("hard") or not any(p["type"] == tn for p in P.parts.values()):
            continue
        txt = gen_phys.sdc(P, tn, gen_phys.type_pins(P, tn))
        assert _errs(txt, sdc_lint.kit_context(P, tn)) == [], tn


def test_kit_generation_writes_and_runs_the_lint():
    P = schema.Plan(TINY)
    with tempfile.TemporaryDirectory() as d:
        kd = gen_phys.write_type_kit(P, "src", d, [])
        assert (kd / "sdc_lint.py").is_file() and (kd / "sdc_lint.json").is_file()
        assert sdc_lint.lint_kit_files(kd) == []
        assert "sdc_lint.py" in gen_phys.RUN_KIT and "--liberty" in gen_phys.RUN_KIT


def test_kit_generation_raises_on_a_bad_sdc(monkeypatch):
    P = schema.Plan(TINY)
    monkeypatch.setattr(gen_phys, "UNC_HOLD_PS", 10.0)          # a relaxed hold uncertainty in the generator
    with tempfile.TemporaryDirectory() as d, pytest.raises(sdc_lint.SdcLintError):
        gen_phys.write_type_kit(P, "src", d, [])


def test_ns_values_against_a_ps_liberty():
    """KV-P3b 10-23: SDC written in ns (period 0.833) against a 1ps liberty = a 0.833-ps clock."""
    txt, ctx = _kit(TINY)
    bad = txt.replace(f"-period {ctx['period_ps']:.4f}", f"-period {ctx['period_ps'] / 1000:.4f}")
    e = _errs(bad, ctx)
    assert any("period" in x for x in e)
    assert any("liberty time_unit" in x for x in _errs(txt, ctx, liberty_unit_ps=1000.0))


def test_liberty_time_unit_parse():
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "a.lib.gz"
        with gzip.open(p, "wt") as f:
            f.write('library (x) {\n  time_unit : "1ps";\n  capacitive_load_unit (1,ff);\n')
        assert sdc_lint.liberty_time_unit_ps(p) == 1.0
        q = Path(d) / "b.lib"
        q.write_text('library (x) {\n time_unit : "1ns" ;\n')
        assert sdc_lint.liberty_time_unit_ps(q) == 1000.0


def test_missing_min_output_delay_and_positive_min():
    txt, ctx = _kit(TINY)
    lines = [ln for ln in txt.splitlines() if not ln.startswith("set_output_delay -min")]
    assert any("no min output delay" in x for x in _errs("\n".join(lines), ctx))
    # the pre-10-24 generator: plain set_output_delay = min output delay +0.2 T (sender hold waived)
    old = txt.replace("set_output_delay -max", "set_output_delay").replace(
        [ln for ln in txt.splitlines() if ln.startswith("set_output_delay -min")][0], "")
    assert any("sender hold check waived" in x for x in _errs(old, ctx))


def test_missing_input_delays():
    txt, ctx = _kit(TINY)
    lines = [ln for ln in txt.splitlines() if not ln.startswith("set_input_delay -min")]
    e = _errs("\n".join(lines), ctx)
    assert any("no min input delay" in x for x in e)
    lines = [ln for ln in txt.splitlines() if not ln.startswith("set_input_delay -max")]
    assert any("no max input delay" in x for x in _errs("\n".join(lines), ctx))


def test_seam_hold_padding_relaxed():
    txt, ctx = _kit(TINY)
    bad = txt.replace(f"set_input_delay -min {-ctx['insertion_tol_ps']:.4f}", "set_input_delay -min 0.0000")
    assert any("seam-hold padding relaxed" in x for x in _errs(bad, ctx))


def test_undefined_clock_and_untapped_clock_port():
    txt, ctx = _kit(TINY)
    assert any("not defined" in x for x in _errs(txt.replace("-clock vclk $non_clk_in", "-clock vclk2 $non_clk_in", 1), ctx))
    assert any("clock tap port clk_t9 has no create_clock" in x
               for x in _errs(txt, ctx, clock_ports=ctx["clock_ports"] + ["clk_t9"]))


@pytest.mark.parametrize("old,new,msg", [
    ("set_clock_uncertainty 60.0000 -setup", "set_clock_uncertainty 40.0000 -setup", "policy 60"),
    ("set_clock_uncertainty 25.0000 -hold [all_clocks]", "", "hold uncertainty on clock"),
    ("-to [get_clocks clk] -setup 30.0000", "-to [get_clocks clk] -setup 60.0000", "once per seam"),
    ("-to [get_clocks clk] -hold 12.5000", "-to [get_clocks clk] -hold 0.0000", "once per seam"),
])
def test_uncertainty_policy(old, new, msg):
    txt, ctx = _kit(TINY)
    assert old in txt
    assert any(msg in x for x in _errs(txt.replace(old, new), ctx))


@pytest.mark.parametrize("extra", [
    "set_false_path -hold -from [all_inputs]",
    "set_multicycle_path 2 -setup -to [all_outputs]",
    "set_max_delay 2000 -from [all_inputs]",
    "set_disable_timing [get_ports clk]",
    "set_clock_groups -asynchronous -group clk -group vclk",
])
def test_exceptions_are_forbidden(extra):
    txt, ctx = _kit(TINY)
    assert any("forbidden" in x for x in _errs(txt + extra + "\n", ctx))


def test_relaxed_period_waveform_and_io_budget():
    txt, ctx = _kit(TINY)
    per = f"{ctx['period_ps']:.4f}"
    assert any("period" in x for x in _errs(txt.replace(f"-period {per}", "-period 1000.0000", 1), ctx))
    assert any("waveform" in x for x in _errs(txt.replace(f"-period {per}", f"-period {per} -waveform {{0 600}}", 1), ctx))
    io = f"{gen_phys.IO_BUDGET * ctx['period_ps']:.4f}"
    assert any("below its IO budget" in x for x in _errs(txt.replace(f"set_input_delay -max {io}", "set_input_delay -max 10.0", 1), ctx))
    lat = f"{ctx['insertion_ps']:.4f}"
    assert any("source latency" in x for x in _errs(txt.replace(f"-source {lat}", "-source 200.0000"), ctx))
