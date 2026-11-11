"""VSN2-HOLD 11-11 (DIE-HBM-97): opt-in launch-tap hop latches and reset-follows-clock-tap for listed types only."""
import shutil
import subprocess
import types
from pathlib import Path

import pytest

import gen_phys

HOOK = Path(__file__).with_name("reset_follow_clock.tcl")


def _p(name, clock=None, reset=None):
    return types.SimpleNamespace(die={"name": name}, clock=clock or {}, reset=reset or {})


def test_launch_tap_type_has_no_capture_tap_line(monkeypatch):
    monkeypatch.delenv("OT_HOP_LATCH_CAPTURE_TAP", raising=False)
    P = _p("hbm_arch_B2o", clock={"hop_latch_launch_tap": {"types": ["vsN2"]}})
    assert gen_phys._hop_latch_capture_tap(P, "vsN2") is None
    assert gen_phys._hop_latch_capture_tap(P, "vsN1") == "u_fl_rst_ u_fl_L201x"
    assert gen_phys._hop_latch_capture_tap(P) == "u_fl_rst_ u_fl_L201x"


def test_absent_flag_keeps_die_default(monkeypatch):
    monkeypatch.delenv("OT_HOP_LATCH_CAPTURE_TAP", raising=False)
    assert gen_phys._hop_latch_capture_tap(_p("hbm_arch_B2o"), "vsN2") == "u_fl_rst_ u_fl_L201x"
    assert gen_phys._hop_latch_capture_tap(types.SimpleNamespace(die={"name": "hbm_x"}), "vsN2") == \
        "u_fl_rst_ u_fl_L201x"


def test_env_still_wins(monkeypatch):
    monkeypatch.setenv("OT_HOP_LATCH_CAPTURE_TAP", "u_fl_rst_")
    P = _p("hbm_arch_B2o", clock={"hop_latch_launch_tap": {"types": ["vsN2"]}})
    assert gen_phys._hop_latch_capture_tap(P, "vsN2") == "u_fl_rst_"


def test_reset_follow_flag():
    P = _p("hbm_arch_B2o", reset={"follow_clock_tap": {"types": ["vsN2"]}})
    assert gen_phys.reset_follow_clock_tap(P, "vsN2")
    assert not gen_phys.reset_follow_clock_tap(P, "vsN1")
    assert not gen_phys.reset_follow_clock_tap(_p("hbm_arch_B2o"), "vsN2")
    assert not gen_phys.reset_follow_clock_tap(types.SimpleNamespace(die={}), "vsN2")


# OpenDB mock: terminal 7 (rst_n_t7) launches from relay r7 on clk_t7, terminal 2 from relay r2 on clk_t2.
# The sink u_ft_x_o_2/eq is clocked by SINK_CLK and its RESETN starts on the rst_n_t7 net.
MOCK = r'''
proc blk {m args} {switch $m {getInsts {return {r7 r2 sink}}}}
proc dff {m} {return DFFASRHQNx1}
proc out {m} {switch $m {getIoType {return OUTPUT} getName {return QN}}}
proc inp {m} {switch $m {getIoType {return INPUT} getName {return RESETN}}}
proc ckm {m} {switch $m {getIoType {return INPUT} getName {return CLK}}}
proc c7 {m} {switch $m {getName {return clk_t7}}}
proc c2 {m} {switch $m {getName {return clk_t2}}}
proc t7 {m} {switch $m {getName {return rst_n_t7} getITerms {return {q7}}}}
proc t2 {m} {switch $m {getName {return rst_n_t2} getITerms {return {q2}}}}
proc q7 {m} {switch $m {getMTerm {return out} getInst {return r7} getNet {return t7}}}
proc q2 {m} {switch $m {getMTerm {return out} getInst {return r2} getNet {return t2}}}
proc k7 {m} {switch $m {getMTerm {return ckm} getNet {return c7}}}
proc k2 {m} {switch $m {getMTerm {return ckm} getNet {return c2}}}
proc r7 {m} {switch $m {getMaster {return dff} getName {return u_rrl_9/q} getITerms {return {k7 q7}} getPlacementStatus {return PLACED} getLocation {return {1000 0}}}}
proc r2 {m} {switch $m {getMaster {return dff} getName {return u_rrl_4/q} getITerms {return {k2 q2}} getPlacementStatus {return PLACED} getLocation {return {$::R2X 0}}}}
proc sink {m} {switch $m {getMaster {return dff} getName {return u_ft_x_o_2/eq} getITerms {return {ks si}} getPlacementStatus {return PLACED} getLocation {return {0 0}}}}
proc ks {m} {switch $m {getMTerm {return ckm} getNet {return $::SINK_CLK}}}
set current t7
proc si {m args} {global current; switch $m {getMTerm {return inp} getNet {return $current} getInst {return sink} disconnect {} connect {set current [lindex $args 0]}}}
proc rt_tapnet {blk i} {return [expr {$i == 7 ? "t7" : "t2"}]}
proc rt_launch_source {net seen} {
  set q [expr {$net eq "t7" ? "q7" : "q2"}]
  return [list $net 0 [[$q getInst] getLocation]]
}
set rt_blk blk
set rt_dbu 1
set rt_leaf_reach_um 405
set rt_taps {{7 1000 0} {2 0 0}}
set rt_role_tables {{mission {} {}}}
set rt_cls [dict create rst_n_t7 {7 0} rst_n_t2 {2 0}]
set rt_rep [dict create 7,0 t7 2,0 t2]
'''


def run_hook(sink_clk, r2x=100):
    if not shutil.which("tclsh"):
        pytest.skip("tclsh unavailable")
    script = (MOCK.replace("$::R2X", str(r2x)) + f"\nset SINK_CLK {sink_clk}\n"
              + f"if {{[catch {{source {{{HOOK}}}}} msg]}} {{puts stderr $msg; exit 1}}\n"
              + 'puts "FINAL $current"\n')
    return subprocess.run(["tclsh"], input=script, text=True, capture_output=True)


def test_cross_tap_sink_follows_its_clock_terminal():
    p = run_hook("c2")
    assert p.returncode == 0, p.stderr
    assert "FINAL t2" in p.stdout
    assert "1 re-pointed" in p.stdout


def test_same_clock_sink_is_kept():
    p = run_hook("c7")
    assert p.returncode == 0, p.stderr
    assert "FINAL t7" in p.stdout
    assert "1 already same-clock" in p.stdout


def test_out_of_reach_terminal_is_not_used():
    p = run_hook("c2", r2x=500)
    assert p.returncode == 0, p.stderr
    assert "FINAL t7" in p.stdout
    assert "1 kept" in p.stdout and "u_ft_x_o_2/eq/RESETN:clk_t2" in p.stdout
