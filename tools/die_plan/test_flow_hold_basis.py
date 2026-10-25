"""FLOW 2026-10-25: per-corner insertion binding (METHODOLOGY ruling 9.7 / BRIEFING decision 5e), the RCX-calibrated RC
basis and the F4 leaf-affinity CTS default as kit-generation defaults; sign-off rebind + per-corner contract check.
    python3 -m pytest -q tools/die_plan/test_flow_hold_basis.py"""
import copy
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
import signoff  # noqa: E402
from test_signoff import record  # noqa: E402

TINY = json.loads((HERE / "examples" / "tiny_plan.json").read_text())


def _plan(die_ff=None, type_clock=None):
    raw = copy.deepcopy(TINY)
    if die_ff is not None:
        raw["clock"]["insertion_ff_ps"] = die_ff
    if type_clock:
        raw["partition_types"]["src"]["clock"].update(type_clock)
    schema.validate(raw) if hasattr(schema, "validate") else None
    return schema.Plan(raw)


def test_binding_defaults_die_budget_and_ratio():
    b = gen_phys.insertion_binding(_plan(), "src")
    assert b["tt"] == 250.0 and b["ff"] == round(gen_phys.FF_TT_INSERTION_RATIO * 250.0, 1)
    assert "RATIO" in b["basis"]["ff"] and b["early_tap_ps"] == 0.0 and b["tol"] == 40.0


def test_binding_die_ff_and_type_measured_view():
    assert gen_phys.insertion_binding(_plan(die_ff=205.0), "src")["ff"] == 205.0
    b = gen_phys.insertion_binding(_plan(die_ff=205.0, type_clock=dict(
        insertion_ps=270.3, insertion_ff_ps=219.5, insertion_basis="signed view routed RCX (ve_s m0)")), "src")
    assert (b["tt"], b["ff"]) == (270.3, 219.5) and b["basis"]["tt"].startswith("signed view")
    assert abs(b["early_tap_ps"] - 20.3) < 1e-9          # 9.7: parent delivers the type's tap I - 250 early
    # a type TT override without an FF value takes the ratio of ITS TT, never the die FF budget
    b = gen_phys.insertion_binding(_plan(die_ff=205.0, type_clock=dict(insertion_ps=300.0)), "src")
    assert b["ff"] == round(gen_phys.FF_TT_INSERTION_RATIO * 300.0, 1)


def test_binding_rejects_ff_above_tt():
    with pytest.raises(ValueError):
        gen_phys.insertion_binding(_plan(type_clock=dict(insertion_ps=200.0, insertion_ff_ps=230.0)), "src")


def test_kit_carries_the_binding_rc_basis_and_hooks():
    P = _plan(type_clock=dict(insertion_ps=270.3, insertion_ff_ps=219.5, insertion_basis="measured"))
    with tempfile.TemporaryDirectory() as d:
        kd = gen_phys.write_type_kit(P, "src", d, [], hold_ff_margin=gen_phys.HOLD_FF_MARGIN_DEFAULT)
        sdc = (kd / "constraint.sdc").read_text()
        assert "set_clock_latency -source 270.3000 [get_clocks vclk]" in sdc
        cfg = (kd / "config.mk").read_text()
        for line in ("export OT_VCLK_TT = 270.3000", "export OT_VCLK_FF = 219.5000", "export OT_TAP_TARGET_PS = 270.3",
                     "export LAYER_PARASITICS_FILE = /work/setRC_rcx.tcl", "export SET_RC_TCL = /work/setRC_rcx.tcl",
                     "export PRE_GLOBAL_ROUTE_TCL = /work/grt_pre.tcl",
                     "export POST_GLOBAL_ROUTE_TCL = /work/grt_post.tcl", "export POST_CTS_TCL = /work/cts_post.tcl",
                     "export OT_HOLD_FF_MARGIN = 5"):
            assert line in cfg, line
        for f in ("vclk_corner.tcl", "grt_pre.tcl", "grt_post.tcl", "cts_post.tcl", "leaf_affinity.tcl",
                  "setRC_rcx.tcl", "tap_balance.tcl", "hold_gate.tcl"):
            assert (kd / f).is_file(), f
        cb = json.loads((kd / "clock_binding.json").read_text())
        assert cb["insertion_ps"] == dict(tt=270.3, ff=219.5) and cb["insertion_tol_ps"] == 40.0
        bud = json.loads((kd / "budget.json").read_text())["clock"]
        assert bud["insertion_ps"] == 270.3 and bud["insertion_ff_ps"] == 219.5
        ctx = json.loads((kd / "sdc_lint.json").read_text())
        assert ctx["insertion_ps"] == 270.3 and ctx["insertion_ff_ps"] == 219.5
        assert sdc_lint.lint_kit_files(kd) == []


def test_stock_rc_opt_out_and_mcmm_opt_out():
    with tempfile.TemporaryDirectory() as d:
        kd = gen_phys.write_type_kit(_plan(), "src", d, [], hold_ff_margin=None, rc_cal=False)
        cfg = (kd / "config.mk").read_text()
        assert "LAYER_PARASITICS_FILE" not in cfg and not (kd / "setRC_rcx.tcl").exists()
        assert "OT_HOLD_FF_MARGIN" not in cfg and "OT_VCLK_FF" in cfg


def test_gen_cli_defaults_are_the_flow_defaults():
    import gen
    src = Path(gen.__file__).read_text()
    assert '"--hold-ff-margin", type=float, default=5.0' in src and "--hold-mcmm" in src and "--stock-rc" in src
    assert gen_phys.write_phys.__defaults__ is not None


def test_run_kit_binds_ff_vclk_in_ff_only_steps():
    rk = gen_phys.RUN_KIT
    assert "OT_VCLK_CORNER=ff \\$M grt CORNER=BC CORNERS=bc" in rk
    assert "OT_VCLK_FF=" in rk and "LAYER_PARASITICS_FILE=" in rk          # hold_gate.tcl env
    hg = (HERE / "hold_gate.tcl").read_text()
    assert "ot_vclk_bind ff" in hg and "LAYER_PARASITICS_FILE" in hg
    vc = (HERE / "vclk_corner.tcl").read_text()
    assert "set_clock_latency -source" in vc and "OT_VCLK_CORNER" in vc
    assert "ot_vclk_bind tt" in (HERE / "grt_post.tcl").read_text()        # 5_1_grt.sdc keeps the SDC (TT) value
    assert "vclk_corner.tcl" in (HERE / "grt_pre.tcl").read_text()
    assert "leaf_affinity.tcl" in (HERE / "cts_post.tcl").read_text()


def test_sdc_lint_rejects_ff_above_tt():
    P = _plan()
    txt = gen_phys.sdc(P, "src", gen_phys.type_pins(P, "src"))
    ctx = sdc_lint.kit_context(P, "src")
    assert sdc_lint.lint(txt, **ctx) == []
    assert any("bound FF insertion" in e for e in sdc_lint.lint(txt, **dict(ctx, insertion_ff_ps=300.0)))


def _rebind(rec, tt=None, ff=None, tol=40.0, applied=True):
    rec["policy"] = dict(ff_vclk="rebind", insertion_bound=dict(tt=tt, ff=ff, tol=tol))
    for c in ("tt", "ff"):
        rec["corners"][c]["ff_vclk_reference"] = ("applied mode pin_flop_mean clock vclk latency_ps 260 samples 2"
                                                  if applied else "unavailable mode pin_flop_mean")
    return rec


def test_signoff_rebind_contract_per_corner():
    # record(): TT pin-flop mean 270 (250 / 290), FF 265 (250 / 280)
    rec = signoff.evaluate(_rebind(record(), tt=270.0, ff=265.0))
    assert rec["checks"]["clock"]["verdict"] == "PASS" and rec["verdict"] == "SIGNED"
    rec = signoff.evaluate(_rebind(record(), tt=270.0, ff=219.0))          # FF routed I 46 ps off the bound value
    assert rec["checks"]["clock"]["verdict"] == "FAIL"
    assert any("FF pin-flop insertion" in p for p in rec["checks"]["clock"]["problems"])
    rec = signoff.evaluate(_rebind(record(), tt=313.7, ff=265.0))
    assert any("TT pin-flop insertion" in p for p in rec["checks"]["clock"]["problems"])


def test_signoff_rebind_setup_uses_rebound_tt_and_requires_it():
    rec = signoff.evaluate(_rebind(record(tt_setup=5.0), tt=270.0, ff=265.0))
    assert rec["checks"]["setup_tt"]["verdict"] == "PASS"
    rec = signoff.evaluate(_rebind(record(), tt=270.0, ff=265.0, applied=False))
    assert rec["checks"]["setup_tt"]["verdict"] == "NOT RUN" and rec["checks"]["hold_ff"]["verdict"] == "NOT RUN"
    assert rec["verdict"] == "NOT SIGNED"


def test_signoff_session_rebinds_tt_and_ff_only_in_rebind_mode():
    s_tt = signoff.session_tcl("tt", [], "x.spef", ff_vclk="rebind")
    s_ff = signoff.session_tcl("ff", [], "x.spef", ff_vclk="rebind")
    s_sdc = signoff.session_tcl("ff", [], "x.spef", ff_vclk="sdc")
    assert "FF_VCLK applied" in s_tt and "FF_VCLK applied" in s_ff and "FF_VCLK applied" not in s_sdc
    assert "FF_VCLK applied" not in signoff.session_tcl("ss", [], "x.spef", ff_vclk="rebind")


def test_leaf_affinity_tcl_is_report_only_capable_and_bounded():
    t = (HERE / "leaf_affinity.tcl").read_text()
    for k in ("OT_LEAF_AFF_UM", "OT_LEAF_AFF_MAX_GROUP", "OT_LEAF_AFF_REPORT_ONLY", "getSigType", "OT_LEAF_AFF pairs"):
        assert k in t, k
