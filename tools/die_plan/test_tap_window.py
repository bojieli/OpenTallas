"""INFRA-FIRST-R4 / COORD 2026-10-26 11:24: plan-declared kit hold window (clock.tap_window + clock.seam_hold 80)
-> kit SDC per-tap source window, exact IO shift, pre-CTS zero / restore, lint, sign-off overlay, hold-gate guard."""
import copy
import json
import subprocess
from pathlib import Path

import pytest

import gen_phys
import schema
import sdc_lint
import signoff

HERE = Path(__file__).parent


def _raw(window=80.0, seam=80.0):
    raw = json.loads((HERE / "examples/tiny_plan.json").read_text())
    if seam is not None:
        raw["clock"]["seam_hold"] = dict(sender_ps=25, seam_ps=seam)
    if window is not None:
        raw["clock"]["tap_window"] = dict(window_ps=window, note="COORD 11:24 W = 80 intra + seam")
    return raw


def _sdc(P, tn="src"):
    return gen_phys.sdc(P, tn, gen_phys.type_pins(P, tn))


def test_no_window_byte_identical():
    base = schema.Plan(_raw(window=None, seam=None))
    assert gen_phys.tap_window_ps(base) == 0.0
    s = _sdc(base)
    assert "-early" not in s and "tap_window" not in s
    assert "set_input_delay -max 166.6000 -clock vclk $non_clk_in" in s
    assert "tap_window_ps" not in sdc_lint.kit_context(base, "src")


def test_window_lines_and_io_shift():
    P = schema.Plan(_raw())
    s = _sdc(P)
    ports = " ".join(n for n, _x, _y in gen_phys.clock_pins(P, "src"))
    assert f"set_clock_latency -source -early -clock clk -80.0000 [get_ports {{{ports}}}]" in s
    assert f"set_clock_latency -source -late -clock clk 0.0000 [get_ports {{{ports}}}]" in s
    # contract unchanged (seam 80 = sender 25 + receiver 55), SDC carries the exact shift of the early tap
    sh = gen_phys.seam_hold(P)
    assert (sh["in_min_ps"], sh["out_min_ps"], sh["seam_ps"]) == (-55.0, -25.0, 80.0)
    assert gen_phys.hold_out_min_ps(P) == -25.0 and gen_phys.hold_out_min_sdc_ps(P) == 55.0
    assert "set_input_delay -max 86.6000 -clock vclk $non_clk_in" in s
    assert "set_input_delay -min -55.0000 -clock vclk $non_clk_in" in s
    assert "set_output_delay -min 55.0000 -clock vclk [all_outputs]" in s
    assert "set_output_delay -max 166.6000 -clock vclk [all_outputs]" in s
    # identical for every type (one die-wide declared number)
    for tn in P.types:
        assert "-early -clock clk -80.0000" in _sdc(P, tn)


def test_lint_accepts_window_and_rejects_tampering():
    P = schema.Plan(_raw())
    s, ctx = _sdc(P), sdc_lint.kit_context(P, "src")
    assert ctx["tap_window_ps"] == 80.0
    assert sdc_lint.lint(s, **ctx) == []
    assert sdc_lint.lint(s.replace("-early -clock clk -80.0000", "-early -clock clk -60.0000"), **ctx)
    assert sdc_lint.lint(s.replace("set_output_delay -min 55.0000", "set_output_delay -min 56.0000"), **ctx)
    assert sdc_lint.lint(s.replace("set_input_delay -max 86.6000", "set_input_delay -max 80.0000"), **ctx)
    nowin = {k: v for k, v in ctx.items() if k != "tap_window_ps"}
    assert any("without a plan clock.tap_window" in e for e in sdc_lint.lint(s, **nowin))
    bare = "".join(l for l in s.splitlines(True) if "-early" not in l and "-late" not in l)
    assert any("window early None" in e for e in sdc_lint.lint(bare, **ctx))


def test_prects_zero_and_restore():
    P = schema.Plan(_raw())
    pre, cts = gen_phys.clock_phase_tcl(P, "src"), gen_phys.clock_phase_tcl(P, "src", before_cts=True)
    assert "-early -clock clk 0.0000" in pre and "-0.0000" not in pre
    assert "-early -clock clk -80.0000" in cts
    assert cts.index("unset_clock_latency") < cts.index("-early") < cts.index("source /work/clock_taps.tcl")


def test_requires_seam_hold_and_bounds():
    with pytest.raises(ValueError, match="seam_hold"):
        gen_phys.tap_window_ps(schema.Plan(_raw(seam=None)))
    with pytest.raises(ValueError):
        gen_phys.tap_window_ps(schema.Plan(_raw(window=300.0)))


def test_early_core_taps_take_the_window(monkeypatch):
    """DIE-S81-10: 12.8d ban lifted (v5.0); the core tap keeps its own early latency, early end -(early + W)
    (full coverage in test_tap_window_core.py)."""
    P = schema.Plan(_raw())
    monkeypatch.setattr(gen_phys, "core_tap_rows", lambda p, t, corner="TT": [("clk_c0", "u", "*", 50.0, 300.0)])
    t = gen_phys.tap_window_tcl(P, "src")
    assert t.endswith("set_clock_latency -source -early -clock clk -130.0000 [get_ports clk_c0]\n")
    assert "clk_c0" not in gen_phys.tap_window_tcl(P, "src", core=False)


def test_kit_config_and_signoff_overlay(tmp_path):
    P = schema.Plan(_raw())
    kit = gen_phys.write_type_kit(P, "src", tmp_path, [])
    cfg = (kit / "config.mk").read_text()
    assert "export OT_HOLD_OUT_MIN = 55.0000" in cfg and "export OT_TAP_WINDOW = 80.0000" in cfg
    assert "OT_TAP_WINDOW=" in (kit / "run_kit.sh").read_text() if (kit / "run_kit.sh").exists() else True
    lctx = json.loads((kit / "sdc_lint.json").read_text())
    assert sdc_lint.lint((kit / "constraint.sdc").read_text(), **lctx) == []
    t = signoff.session_tcl("ff", [], "x.spef", ff_vclk="rebind", hold_in_min=lctx["hold_in_min_ps"],
                            hold_out_min=lctx["hold_out_min_ps"], tap_window=lctx["tap_window_ps"])
    assert "set_output_delay -min 55 " in t and "set_input_delay -min -55 " in t
    legacy = signoff.session_tcl("ff", [], "x.spef", ff_vclk="rebind", hold_in_min=-55.0, hold_out_min=-25.0)
    assert "set_output_delay -min -25 " in legacy


def _hold_gate(tmp_path, out_min, window):
    p = tmp_path / "hg.tcl"
    p.write_text("proc get_property {o k} {return {}}\nproc all_clocks {} {return {vclk}}\n"
                 "proc all_inputs {} {return {}}\nproc all_outputs {} {return {}}\nproc get_full_name {x} {return $x}\n"
                 "proc read_liberty {args} {}\nproc read_db {args} {}\nproc read_sdc {args} {}\nproc source {args} {}\n"
                 "proc set_propagated_clock {args} {}\nproc estimate_parasitics {args} {}\nproc get_clocks {args} {}\n"
                 "proc set_input_delay {args} {}\nproc set_output_delay {args} {}\n"
                 "namespace eval sta {}\nproc sta::time_sta_ui {x} {return $x}\n"
                 "proc sta::worst_slack_cmd {args} {return 1}\nproc sta::endpoint_violation_count {args} {return 0}\n"
                 f"set ::env(OT_HOLD_OUT_MIN) {out_min}\nset ::env(OT_TAP_WINDOW) {window}\n")
    txt = (HERE / "hold_gate.tcl").read_text()
    guard = txt[txt.index("set hg_in -40"):txt.index('puts "OT_HOLD_GATE contract')]
    p.write_text(p.read_text() + guard + 'puts GUARD_OK\n')
    return subprocess.run(["tclsh", str(p)], capture_output=True, text=True)


def test_hold_gate_guard(tmp_path):
    if subprocess.run(["which", "tclsh"], capture_output=True).returncode:
        pytest.skip("no tclsh")
    assert "GUARD_OK" in _hold_gate(tmp_path, 55.0, 80.0).stdout
    assert _hold_gate(tmp_path, 55.0, 0).returncode != 0
    assert _hold_gate(tmp_path, 85.0, 80.0).returncode != 0


def test_per_type_window_overrides_one_type_only():
    # DIE-S81-41 (COORD 2026-10-31 05:2x): clock.tap_window.per_type_ps; unlisted types byte-identical to the die W
    base = schema.Plan(_raw())
    raw = _raw()
    raw["clock"]["tap_window"]["per_type_ps"] = {"src": 40.0}
    P = schema.Plan(raw)
    assert gen_phys.tap_window_ps(P, "src") == 40.0 and gen_phys.tap_window_ps(P) == 80.0
    s = _sdc(P, "src")
    assert "-early -clock clk -40.0000" in s and "-early -clock clk -80.0000" not in s
    assert gen_phys.tap_window_io_shift(P, "src") == (-40.0, 40.0)
    assert gen_phys.hold_out_min_sdc_ps(P, "src") == -25.0 + 40.0
    assert sdc_lint.kit_context(P, "src")["tap_window_ps"] == 40.0
    for tn in P.types:
        if tn != "src":
            assert _sdc(P, tn) == _sdc(base, tn)
            assert sdc_lint.kit_context(P, tn)["tap_window_ps"] == 80.0
    raw["clock"]["tap_window"]["per_type_ps"] = {"src": 400.0}
    with pytest.raises(ValueError):
        gen_phys.tap_window_ps(schema.Plan(raw), "src")
