"""FT-HOP-M2-WIRE (GEN-CLASS-1 11-12): post-GRT repeater pitch on the ft-station hop nets only (ft_hop_maxwire.tcl).

HEAD hd_spn_wshim_tx: 120 of 125 sign-off slew pins were fanout-1 ~200-um M2 hops from a repair BUFx3 to the next ft
station.  The hook runs repair_design -max_wire_length OT_FT_MAXWIRE_UM after the flow's own repair_design, with every
other net dont_touch for that call only.  tclsh tests on a stub ODB; gen_phys tests on examples/tiny_plan.json."""
import copy
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
TCL = HERE / "ft_hop_maxwire.tcl"
needs_tclsh = pytest.mark.skipif(shutil.which("tclsh") is None, reason="tclsh not installed")

# stub ODB: insts {name x_um y_um master}, nets {name {iterm insts} {bterm xy_um} sigtype dont_touch}
STUBS = r"""
set ::env(OT_FT_MAXWIRE_UM) 110
proc log_cmd {args} {
  set dt {}
  foreach n [blk getNets] { lappend dt "[$n getName]=[$n isDoNotTouch]" }
  puts "LOG [join $args { }] DT [join $dt { }]"
}
namespace eval sta { proc network_leaf_instance_count {} { return 7 } }
namespace eval ord { proc get_db_block {} { return blk } }
array set INST {}
array set NET {}
proc mkinst {name x y master} { set ::INST($name) [list $x $y $master]
  proc $name {m args} "switch \$m { getName { return $name } getLocation { return \[list [expr {int($x*1000)}] [expr {int($y*1000)}]\] } getMaster { return m_$master } }"
  proc m_$master {m args} "return $master" }
proc mkbox {name x y} { proc $name {m args} "switch \$m { xMin { return [expr {int($x*1000)}] } yMin { return [expr {int($y*1000)}] } getBBox { return $name } }" }
proc mknet {name id insts bterms sig dt} {
  set ::NET($name,dt) $dt
  set its {}; foreach i $insts { proc it_${name}_$i {m args} "return $i"; lappend its it_${name}_$i }
  set bts {}; set k 0; foreach xy $bterms { mkbox bp_${name}_$k {*}$xy; proc bt_${name}_$k {m args} "return bp_${name}_$k"; lappend bts bt_${name}_$k; incr k }
  proc $name {m args} "switch \$m { getName { return $name } getId { return $id } getSigType { return $sig } isSpecial { return 0 }
    getITerms { return [list $its] } getBTerms { return [list $bts] } isDoNotTouch { return \$::NET($name,dt) }
    setDoNotTouch { set ::NET($name,dt) \[lindex \$args 0\] } }"
}
proc blk {m args} { switch $m { getDbUnitsPerMicron { return 1000 } getNets { return {hop face short other keep} } } }
mkinst u_ft_link_s0/q_reg 10 50 DFFHQNx1_ASAP7_75t_R
mkinst place4070 148 50 BUFx3_ASAP7_75t_R
mkinst u_bound.u_ft_ft12_o_4/_0894_ 349 50 INVx1_ASAP7_75t_R
mkinst u_core/u_alu 10 300 NAND2x1_ASAP7_75t_R
mkinst u_core/u_out 300 300 DFFHQNx1_ASAP7_75t_R
mkinst u_ft_link_s1/a 400 60 INVx1_ASAP7_75t_R
mkinst u_ft_link_s1/b 420 60 DFFHQNx1_ASAP7_75t_R
mknet hop 1 {place4070 u_bound.u_ft_ft12_o_4/_0894_} {} SIGNAL 0
mknet face 2 {u_ft_link_s0/q_reg} {{200 50}} SIGNAL 0
mknet short 3 {u_ft_link_s1/a u_ft_link_s1/b} {} SIGNAL 0
mknet other 4 {u_core/u_alu u_core/u_out} {} SIGNAL 0
mknet keep 5 {u_core/u_alu place4070} {} SIGNAL 1
"""
BASE = "proc repair_design_helper {} { puts ORIG_BASE }\n"
WRAP = r"""
proc ot_g183_orig_repair_design_helper {args} { puts ORIG_BODY }
proc repair_design_helper {args} {
  puts WRAP_ENTER
  set rc [catch {uplevel 1 [linsert $args 0 ot_g183_orig_repair_design_helper]} msg opts]
  puts WRAP_EXIT
  return -options $opts $msg
}
"""


def run(tmp_path, body, env_lim="110"):
    t = tmp_path / "t.tcl"
    t.write_text(STUBS.replace("OT_FT_MAXWIRE_UM) 110", f"OT_FT_MAXWIRE_UM) {env_lim}") + body + f"source {TCL}\n"
                 "repair_design_helper\nputs \"AFTER [join [lmap n [blk getNets] {list $n [$n isDoNotTouch]}] { }]\"\n")
    return subprocess.run(["tclsh", str(t)], capture_output=True, text=True, check=True).stdout


@needs_tclsh
def test_only_ft_hop_nets_are_repaired_and_dont_touch_is_restored(tmp_path):
    out = run(tmp_path, BASE)
    assert out.index("ORIG_BASE") < out.index("OT_FT_MAXWIRE repair_design")      # after the flow's own repair
    assert "on 2 ft hop nets" in out                                               # hop (repeater chain) + face port
    log = next(l for l in out.splitlines() if l.startswith("LOG repair_design"))
    assert "-max_wire_length 110" in log
    assert "hop=0" in log and "face=0" in log                                      # the ft hops are repairable
    assert "short=1" in log and "other=1" in log and "keep=1" in log              # everything else frozen
    after = out.splitlines()[-1]
    assert after == "AFTER hop 0 face 0 short 0 other 0 keep 1"                # restored; prior dont_touch kept


@needs_tclsh
def test_grt183_wrapper_stays_in_front(tmp_path):
    out = run(tmp_path, WRAP)
    assert out.index("WRAP_ENTER") < out.index("ORIG_BODY") < out.index("OT_FT_MAXWIRE repair_design") < out.index("WRAP_EXIT")


@needs_tclsh
def test_off_when_zero(tmp_path):
    out = run(tmp_path, BASE, env_lim="0")
    assert "ORIG_BASE" in out and "OT_FT_MAXWIRE" not in out


def _kit(tmp_path, raw, tn="mid"):
    import gen_phys as GP
    GP.write_phys(copy.deepcopy(raw), tmp_path / "k", trial=True, skip_ir=True, rc_cal=False, types=[tn])
    kd = next(p.parent for p in (tmp_path / "k").rglob("config.mk"))
    return kd, kd.joinpath("config.mk").read_text()


def test_gen_phys_arms_ft_kits(tmp_path):
    raw = json.loads((HERE / "examples/tiny_plan.json").read_text())
    assert raw["partition_types"]["mid"]["ft_slots"]
    kd, cfg = _kit(tmp_path, raw)
    assert "export OT_FT_MAXWIRE_UM = 110" in cfg and (kd / "ft_hop_maxwire.tcl").is_file()
    assert "ft_hop_maxwire.tcl" in (kd / "grt_pre.tcl").read_text()


def test_gen_phys_type_opt_out_and_no_ft(tmp_path):
    raw = json.loads((HERE / "examples/tiny_plan.json").read_text())
    raw["partition_types"]["mid"]["ft_hop_maxwire_um"] = 0
    kd, cfg = _kit(tmp_path / "a", raw)
    assert "OT_FT_MAXWIRE_UM" not in cfg and not (kd / "ft_hop_maxwire.tcl").exists()
    raw = json.loads((HERE / "examples/tiny_plan.json").read_text())
    assert not raw["partition_types"]["src"].get("ft_slots")
    kd, cfg = _kit(tmp_path / "b", raw, "src")                       # a type without ft slots is not armed
    assert "OT_FT_MAXWIRE_UM" not in cfg and not (kd / "ft_hop_maxwire.tcl").exists()
