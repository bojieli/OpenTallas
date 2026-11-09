"""DIE-HBM-97 11-09 HOPLATCH-HOLD: grt_pre.tcl puts -hold uncertainty OT_HOP_LATCH_HOLD_PS (default 30) on the clock pin of
every hop latch matched by OT_HOP_LATCH_CAPTURE_TAP for the GRT hold repair only; grt_post.tcl removes it again before
the SDC is written.  Unset pattern or OT_HOP_LATCH_HOLD_PS=0 = nothing."""
import os
import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent

MOCK = r"""
set ::log {}
proc mk_mterm {nm io} { set o mt_[incr ::uid]; proc $o {m} "switch \$m {getName {return {$nm}} getIoType {return $io}}"; return $o }
proc mk_iterm {inst mt net} { set o it_[incr ::uid]; proc $o {m} "switch \$m {getMTerm {return $mt} getNet {return $net} getInst {return $inst}}"; return $o }
proc mk_inst {nm pins} {
  set o in_[incr ::uid]; set its {}
  foreach {pn io net} $pins { lappend its [mk_iterm $o [mk_mterm $pn $io] $net] }
  proc $o {m} "switch \$m {getName {return {$nm}} getITerms {return {$its}}}"
  return $o
}
set ::insts [list \
  [mk_inst {u_bound.u_fl_rst_26/q$_DLATCH_N_} {D INPUT n1 CLK INPUT ck Q OUTPUT n2}] \
  [mk_inst {u_bound.u_fl_L201x1_o_6/q[463]$_DLATCH_N_} {D INPUT n3 CLK INPUT ck Q OUTPUT n4}] \
  [mk_inst {u_bound.u_fl_X9_o_1/q$_DLATCH_N_} {D INPUT n5 CLK INPUT ck Q OUTPUT n6}] \
  [mk_inst {u_bound.u_rrl_26/q$_DFF_P_} {D INPUT n2 CLK INPUT ck QN OUTPUT n7}] \
  [mk_inst {u_bound.u_fl_rst_99/q$_DLATCH_N_} {D INPUT n8 CLK INPUT NULL Q OUTPUT n9}]]
proc blk {m} { switch $m getInsts { return $::insts } }
namespace eval ord { proc get_db_block {} { return blk } }
namespace eval sta { proc find_pin {n} { return "PIN:$n" } }
proc set_clock_uncertainty {args} { lappend ::log [concat set $args] }
proc unset_clock_uncertainty {args} { lappend ::log [concat unset $args] }
proc ot_pg_connect_all {args} {}
proc ot_pg_require_bound {args} {}
source grt_pre.tcl
source grt_post.tcl
puts "LOG [join $::log |]"
"""


def _run(tmp_path, env_extra):
    for f in ("grt_pre.tcl", "grt_post.tcl"):
        shutil.copyfile(HERE / f, tmp_path / f)
    (tmp_path / "vclk_corner.tcl").write_text("")
    (tmp_path / "pg_connect.tcl").write_text("")
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("OT_HOP_LATCH", "OT_MAXWIRE", "OT_TAP_GRT", "OT_VCLK", "OT_RESET_PAIR"))}
    env.update(env_extra)
    out = subprocess.run(["tclsh"], input=MOCK, capture_output=True, text=True, env=env, cwd=tmp_path,
                         check=True).stdout
    return out, out.split("LOG ", 1)[1].strip()


@pytest.mark.skipif(shutil.which("tclsh") is None, reason="tclsh not installed")
def test_matched_hop_latches_padded_then_removed(tmp_path):
    out, log = _run(tmp_path, {"OT_HOP_LATCH_CAPTURE_TAP": "u_fl_rst_ u_fl_L201x"})
    a = "PIN:u_bound.u_fl_rst_26/q$_DLATCH_N_/CLK"
    b = "PIN:u_bound.u_fl_L201x1_o_6/q[463]$_DLATCH_N_/CLK"
    assert log.split("|") == [f"set -hold 30 {{{a}}}", f"set -hold 30 {{{b}}}",
                              f"unset -hold {{{a}}}", f"unset -hold {{{b}}}"] or log.split("|") == [
        f"set -hold 30 {a}", f"set -hold 30 {b}", f"unset -hold {a}", f"unset -hold {b}"], log
    # not matched (u_fl_X9), not a hop latch (u_rrl), unclocked latch: untouched
    assert "X9" not in log and "u_rrl" not in log and "rst_99" not in log
    assert "OT_HOP_LATCH_HOLD 2 hop latch clock pins" in out and "removed from 2" in out


@pytest.mark.skipif(shutil.which("tclsh") is None, reason="tclsh not installed")
def test_margin_value_and_off(tmp_path):
    _, log = _run(tmp_path, {"OT_HOP_LATCH_CAPTURE_TAP": "u_fl_rst_", "OT_HOP_LATCH_HOLD_PS": "45"})
    assert log.startswith("set -hold 45 ") and log.count("|") == 1
    _, log = _run(tmp_path, {"OT_HOP_LATCH_CAPTURE_TAP": "u_fl_rst_", "OT_HOP_LATCH_HOLD_PS": "0"})
    assert log == ""
    _, log = _run(tmp_path, {})
    assert log == ""
