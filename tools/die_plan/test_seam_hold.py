"""CLOCK-RESET IO-HOLD 10-25: opt-in seam hold contract (clock.seam_hold) -> kit SDC, lint ctx, sign-off overlay,
post-CTS gate env, die_trial stand-in cell; legacy contract unchanged."""
import types

import pytest

import gen_phys
import sdc_lint
import signoff


def _P(**clock):
    c = dict(insertion_ps=250.0, insertion_tol_ps=40.0)
    c.update(clock)
    return types.SimpleNamespace(clock=c)


def test_legacy_unchanged():
    sh = gen_phys.seam_hold(_P())
    assert (sh["in_min_ps"], sh["out_min_ps"], sh["seam_ps"]) == (-40.0, 0.0, 40.0)
    assert gen_phys.hold_in_min_ps(_P()) == -40.0 and gen_phys.hold_out_min_ps(_P()) == 0.0


def test_contract_split():
    P = _P(seam_hold=dict(sender_ps=25, seam_ps=25))
    sh = gen_phys.seam_hold(P)
    assert (sh["in_min_ps"], sh["out_min_ps"], sh["seam_ps"]) == (0.0, -25.0, 25.0)


@pytest.mark.parametrize("bad", [dict(sender_ps=25, seam_ps=20), dict(sender_ps=-5, seam_ps=30)])
def test_contract_floor(bad):
    with pytest.raises(ValueError):
        gen_phys.seam_hold(_P(seam_hold=bad))


SDC = """create_clock -name clk -period 833 [get_ports clk]
create_clock -name vclk -period 833
set_clock_latency -source 250 [get_clocks vclk]
set_clock_uncertainty 60 -setup [all_clocks]
set_clock_uncertainty 25 -hold [all_clocks]
set_clock_uncertainty -from [get_clocks vclk] -to [get_clocks clk] -setup 30
set_clock_uncertainty -from [get_clocks clk] -to [get_clocks vclk] -setup 30
set_clock_uncertainty -from [get_clocks vclk] -to [get_clocks clk] -hold 12.5
set_clock_uncertainty -from [get_clocks clk] -to [get_clocks vclk] -hold 12.5
set_input_delay -max 166 -clock vclk [get_ports a]
set_output_delay -max 166 -clock vclk [get_ports y]
set_input_delay -min {imin} -clock vclk [get_ports a]
set_output_delay -min {omin} -clock vclk [get_ports y]
"""


def _lint(imin, omin, **kw):
    return [e for e in sdc_lint.lint(SDC.format(imin=imin, omin=omin), period_ps=833, insertion_ps=250,
                                     insertion_tol_ps=40, clock_ports=["clk"], inputs=["a"], outputs=["y"], **kw)
            if e.startswith("hold")]


def test_lint_legacy():
    assert _lint(-40, 0) == []
    assert _lint(0, -25)            # legacy rule: receiver must pad the whole -40 window


def test_lint_contract():
    ctx = dict(hold_in_min_ps=0.0, hold_out_min_ps=-25.0, seam_hold_ps=25.0)
    assert _lint(0, -25, **ctx) == []
    assert _lint(5, -25, **ctx)           # receiver relaxed beyond the contract
    assert _lint(0, 0, **ctx)             # sender share missing
    assert _lint(0, -25, hold_in_min_ps=0.0, hold_out_min_ps=-15.0, seam_hold_ps=15.0)   # below the 25 ps floor


def test_signoff_overlay():
    legacy = signoff.session_tcl("ff", [], "x.spef", ff_vclk="rebind")
    assert "set_input_delay -min [expr {-40}] " in legacy and "set_output_delay -min 0 " in legacy
    t = signoff.session_tcl("ff", [], "x.spef", ff_vclk="rebind", hold_in_min=0.0, hold_out_min=-25.0)
    assert "set_input_delay -min 0 " in t and "set_output_delay -min -25 " in t
    with pytest.raises(ValueError):
        signoff.session_tcl("ff", [], "x.spef", hold_in_min=-40, hold_out_min=5)


def test_floor_constant_matches_generator():
    assert sdc_lint.SEAM_HOLD_MIN_PS == gen_phys.SEAM_HOLD_MIN_PS


def _standalone(kd):
    import subprocess
    import sys
    return subprocess.run([sys.executable, "-I", str(kd / "sdc_lint.py"), str(kd)], cwd=kd, capture_output=True,
                          text=True)


def test_kit_linter_runs_standalone_with_seam_hold(tmp_path):
    """CLOCK-KV-R3 canary e444b9df7: the kit ships sdc_lint.py without gen_phys.py; with clock.seam_hold set the
    kit lint must run self-contained (it crashed with ModuleNotFoundError gen_phys)."""
    import copy
    import json
    import shutil
    from pathlib import Path
    import schema
    raw = copy.deepcopy(json.loads((Path(__file__).with_name("examples") / "tiny_plan.json").read_text()))
    raw["clock"]["seam_hold"] = dict(sender_ps=25, seam_ps=25)
    P = schema.Plan(raw)
    kd = gen_phys.write_type_kit(P, "src", tmp_path / "gen", [])
    ctx = json.loads((kd / "sdc_lint.json").read_text())
    assert ctx["seam_hold_ps"] == 25.0 and ctx["hold_out_min_ps"] == -25.0
    kit = tmp_path / "work"                       # kit-like dir: only the shipped linter + its inputs, no generator
    kit.mkdir()
    for f in ("sdc_lint.py", "sdc_lint.json", "constraint.sdc") + tuple(
            f for f in ("ft_ports.json", "ft_interface.json", "straps.json") if (kd / f).is_file()):
        shutil.copyfile(kd / f, kit / f)
    assert not (kit / "gen_phys.py").exists()
    r = _standalone(kit)
    assert r.returncode == 0 and "SDC_LINT PASS" in r.stdout, r.stdout + r.stderr
    ctx["seam_hold_ps"] = 15.0                    # below the floor: a lint ERROR, not a crash
    ctx["hold_in_min_ps"] = 10.0
    (kit / "sdc_lint.json").write_text(json.dumps(ctx))
    r = _standalone(kit)
    assert r.returncode == 1 and "below 25 ps" in r.stdout and "Traceback" not in r.stderr, r.stdout + r.stderr
