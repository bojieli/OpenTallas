"""FLOW-INFRA-2 10-25: GRT-RC tap pre-pass (tapbal_grt.tcl) between CTS and the FF GRT hold repair."""
import tempfile

import pytest

from test_flow_hold_basis import HERE, _plan, gen_phys


def _cfg(monkeypatch, env=None, type_clock=None):
    if env is None:
        monkeypatch.delenv("OT_GEN_TAP_GRT_PRE", raising=False)
    else:
        monkeypatch.setenv("OT_GEN_TAP_GRT_PRE", env)
    with tempfile.TemporaryDirectory() as d:
        kd = gen_phys.write_type_kit(_plan(type_clock=type_clock), "src", d, [],
                                     hold_ff_margin=gen_phys.HOLD_FF_MARGIN_DEFAULT)
        assert (kd / "tapbal_grt.tcl").is_file()
        return (kd / "config.mk").read_text()


def test_default_off_env_and_plan_on(monkeypatch):
    assert gen_phys.TAP_GRT_PRE_DEFAULT is False
    assert "OT_TAP_GRT_PRE" not in _cfg(monkeypatch)
    assert "export OT_TAP_GRT_PRE = 1" in _cfg(monkeypatch, env="1")
    assert "export OT_PINREG_PAD = 1" in _cfg(monkeypatch, env="1")
    assert "OT_TAP_GRT_PRE" not in _cfg(monkeypatch, env="0")
    assert "export OT_TAP_GRT_PRE = 1" in _cfg(monkeypatch, type_clock=dict(tap_grt_pre=True))
    assert "OT_TAP_GRT_PRE" not in _cfg(monkeypatch, env="1", type_clock=dict(tap_grt_pre=False))


def test_run_kit_runs_prepass_after_cts_before_hold_gate_and_ff_grt():
    rk = gen_phys.RUN_KIT
    i_cts = rk.index("\\$M cts SKIP_CTS_REPAIR_TIMING=1")
    i_pre = rk.index("RUN_SCRIPT=/work/tapbal_grt.tcl")
    i_hg = rk.index("/work/hold_gate.tcl")
    i_grt = rk.index("OT_VCLK_CORNER=ff \\$M grt")
    assert i_cts < i_pre < i_hg < i_grt
    assert "grep -q '^export OT_TAP_GRT_PRE = 1' /work/config.mk" in rk
    assert "CORNER=TC CORNERS=tc" in rk[i_pre - 200:i_pre + 200]


def test_prepass_script_routes_balances_on_grt_and_rewrites_cts_odb():
    s = (HERE / "tapbal_grt.tcl").read_text()
    order = ["load_design 4_cts.odb 4_cts.sdc", "\nglobal_route {*}$tg_args", "\nestimate_parasitics -global_routing",
             "set ::env(OT_TAP_EST) grt", "source [file join $tg_dir tap_balance.tcl]", "file copy -force", "write_db $::env(RESULTS_DIR)/4_cts.odb"]
    pos = [s.index(o) for o in order]
    assert pos == sorted(pos)
    assert "set ::env(OT_TAP_REPORT_ONLY) 0" in s


def test_pinreg_pad_uses_gate_set_and_fresh_measure():
    s = (HERE / "pinreg_pad.tcl").read_text()
    g = (HERE / "postcts_gate.tcl").read_text()
    for frag in ("get_fanout -from", "-endpoints_only -trace_arcs all", "get_fanin -to [all_outputs]", "ot_cf_wire"):
        assert frag in s and frag in g, frag
    m = s[s.index("proc pp_measure"):]
    assert m.index("set_propagated_clock [all_clocks]") < m.index("estimate_parasitics -global_routing")
    assert "sta::sta_to_db_pin" in s and "global_route -start_incremental" in s and "global_route -end_incremental" in s
    t = (HERE / "tapbal_grt.tcl").read_text()
    assert t.index("tap_balance.tcl]") < t.index("pinreg_pad.tcl") < t.index("write_db")
