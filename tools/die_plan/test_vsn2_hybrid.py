"""VSN2-HOLD hybrid 11-11 (COORD 00:5x): hop_latch_launch_tap.capture subset + clock.reset_root_tap."""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_phys as G  # noqa: E402
import schema as S  # noqa: E402


def _plan(clock, die="hbm_t"):
    return SimpleNamespace(clock=clock, die={"name": die})


def test_capture_subset_for_launch_tap_type(monkeypatch):
    monkeypatch.delenv("OT_HOP_LATCH_CAPTURE_TAP", raising=False)
    P = _plan({"hop_latch_launch_tap": {"types": ["vsN2"], "capture": " u_fl_rst_  "}})
    assert G._hop_latch_capture_tap(P, "vsN2") == "u_fl_rst_"
    # other types keep the die default, form-1 plans (no capture) keep "none"
    assert G._hop_latch_capture_tap(P, "vsN1") == G.HOP_LATCH_CAPTURE_TAP_DEFAULT["hbm"]
    P1 = _plan({"hop_latch_launch_tap": {"types": ["vsN2"]}})
    assert G._hop_latch_capture_tap(P1, "vsN2") is None


def test_env_still_wins(monkeypatch):
    monkeypatch.setenv("OT_HOP_LATCH_CAPTURE_TAP", "off")
    P = _plan({"hop_latch_launch_tap": {"types": ["vsN2"], "capture": "u_fl_rst_"}})
    assert G._hop_latch_capture_tap(P, "vsN2") is None


def test_reset_root_tap_flag():
    P = _plan({"reset_root_tap": {"types": ["vsN2"]}})
    assert G.reset_root_tap(P, "vsN2") and not G.reset_root_tap(P, "vsN1")
    assert not G.reset_root_tap(P, None) and not G.reset_root_tap(_plan({}), "vsN2")


def test_schema_keys():
    ck = S.SCHEMA["properties"]["clock"]["properties"]
    assert ck["hop_latch_launch_tap"]["properties"]["capture"] == {"type": "string"}
    assert set(ck["reset_root_tap"]["properties"]) == {"types", "note"}
    js = json.loads((HERE / "die_plan.schema.json").read_text())["properties"]["clock"]["properties"]
    assert js["reset_root_tap"] == ck["reset_root_tap"]
    assert js["hop_latch_launch_tap"] == ck["hop_latch_launch_tap"]


# --- reset_root_tap.tcl on a tiny OpenDB mock (tclsh) ---
MOCK = r"""
proc mk {kind name args} { set o ::obj_$kind\_$name; interp alias {} $o {} objcall $kind $name; set ::P($o) $args; return $o }
proc objcall {kind name m args} {
  set o ::obj_$kind\_$name; array set p $::P($o)
  switch -- $m {
    getName { return $name }
    getNet { return $p(net) }
    getMTerm { return $p(mterm) }
    getIoType { return $p(io) }
    getInst { return $p(inst) }
    getMaster { return $p(master) }
    getITerms { return $p(iterms) }
    getBTerms { return $::BTERMS }
    getInsts { return $::INSTS }
    disconnect { set p(net) NULL; set ::P($o) [array get p]; return }
    connect { set p(net) [lindex $args 0]; set ::P($o) [array get p]; lappend ::CONN($p(net)) $o; return }
  }
}
proc setp {o k v} { array set p $::P($o); set p($k) $v; set ::P($o) [array get p] }
namespace eval ::ord { proc get_db_block {} { return $::BLK } }
set MI [mk mterm in io INPUT]; set MO [mk mterm out io OUTPUT]
set BLK [mk blk b]
# clock nets of two tap ports
set NA [mk net clk_t1 iterms {}]; set NB [mk net clk_t2 iterms {}]; set NC [mk net clk_t3 iterms {}]
set BTERMS [list [mk bterm clk_t1 net $NA] [mk bterm clk_t2 net $NB] [mk bterm clk_t3 net $NC] [mk bterm arst_n net NULL]]
set INSTS {}
proc N {nm} { return [mk net $nm iterms {}] }
proc flop {nm clknet dnet qnet} {
  if {![string match ::obj_* $clknet]} { set clknet [N $clknet] }
  if {![string match ::obj_* $dnet]} { set dnet [N $dnet] }
  if {![string match ::obj_* $qnet]} { set qnet [N $qnet] }
  set i [mk inst $nm master [mk master DFFHQNx1_ASAP7_75t_R]]
  set c [mk iterm $nm.CLK net $clknet mterm $::MI inst $i]
  set d [mk iterm $nm.D net $dnet mterm $::MI inst $i]
  set q [mk iterm $nm.QN net $qnet mterm $::MO inst $i]
  setp $i iterms [list $c $d $q]; lappend ::INSTS $i; return $i
}
proc buf {nm a y} {
  set i [mk inst $nm master [mk master BUFx2_ASAP7_75t_R]]
  set ia [mk iterm $nm.A net $a mterm $::MI inst $i]; set iy [mk iterm $nm.Y net $y mterm $::MO inst $i]
  setp $i iterms [list $ia $iy]; lappend ::INSTS $i; return $i
}
set R [mk net rootq iterms {}]; set R2 [mk net rootb iterms {}]; set X [mk net other iterms {}]
flop u_bound.u_rst_in/q CK0 D0 $R
flop u_bound.u_rrl_0/q CK1 D1 X1q
flop u_bound.u_rrl_27/q CK2 D2 X2q
flop u_bound.u_rrl_38/q CK3 D3 X3q
flop u_bound.u_ft_x/q CK4 D4 X4q
buf place1 $R $R2
# wire the clocks / data: root on clk_t1; relay 0 already on clk_t1; relays 27/38 on clk_t2/clk_t3 (27 behind a buffer)
foreach {inst ck d} [list u_bound.u_rst_in/q $NA [N ARST] u_bound.u_rrl_0/q $NA $R u_bound.u_rrl_27/q $NB $R2 u_bound.u_rrl_38/q $NC $R u_bound.u_ft_x/q $NB $X] {
  setp ::obj_iterm_$inst.CLK net $ck; setp ::obj_iterm_$inst.D net $d
}
# net -> iterms (sinks + drivers)
proc netiterms {} {
  foreach n [list $::R $::R2 $::X] { set l {}
    foreach i $::INSTS { foreach it [objcall inst [string range $i [string length ::obj_inst_] end] getITerms] {
      if {[objcall iterm [string range $it [string length ::obj_iterm_] end] getNet] eq $n} { lappend l $it } } }
    setp $n iterms $l }
}
netiterms
source [lindex $argv 0]
foreach r {u_bound.u_rrl_0/q u_bound.u_rrl_27/q u_bound.u_rrl_38/q u_bound.u_ft_x/q} {
  puts "CK $r [::obj_iterm_$r.CLK getNet]"
}
"""


@pytest.mark.skipif(shutil.which("tclsh") is None, reason="no tclsh")
def test_reset_root_tap_tcl_moves_direct_relays_only(tmp_path):
    m = tmp_path / "mock.tcl"
    m.write_text(MOCK)
    r = subprocess.run(["tclsh", str(m), str(HERE / "reset_root_tap.tcl")], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    out = r.stdout
    assert "OT_RESET_ROOT_TAP root u_bound.u_rst_in/q on clk_t1: 3 direct clocked sinks, 2 re-hung onto the root tap, 1 already there" in out, out
    ck = dict(l.split()[1:3] for l in out.splitlines() if l.startswith("CK "))
    assert ck["u_bound.u_rrl_0/q"].endswith("clk_t1")
    assert ck["u_bound.u_rrl_27/q"].endswith("clk_t1")     # behind a buffer: followed
    assert ck["u_bound.u_rrl_38/q"].endswith("clk_t1")
    assert ck["u_bound.u_ft_x/q"].endswith("clk_t2")       # not driven by the root: untouched


@pytest.mark.skipif(shutil.which("tclsh") is None, reason="no tclsh")
def test_reset_root_tap_tcl_skips_without_unique_root(tmp_path):
    m = tmp_path / "mock.tcl"
    m.write_text(MOCK.replace("flop u_bound.u_rst_in/q CK0", "flop u_bound.u_rst_inX/q CK0").replace(
        "u_bound.u_rst_in/q $NA [N ARST]", "u_bound.u_rst_inX/q $NA [N ARST]"))
    r = subprocess.run(["tclsh", str(m), str(HERE / "reset_root_tap.tcl")], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert "OT_RESET_ROOT_TAP skip: 0 clocked root flops" in r.stdout
