"""TYPE-SAFE-1 11-06 (COORD RULINGS 19:0x (3)): subtree_balance.tcl, the GRT-RC subtree latency balance of every clock
tree, default on in every core kit (core_flow.apply: grt_post_core.tcl, after the kit's post-GRT hooks, before the final
TT/FF repair) and in the partition GRT-RC pre-pass (tapbal_grt.tcl).  The REAL hook runs under tclsh on a mock OpenDB /
STA whose sink arrival = sum of the driving cells' delays (delay buffers +20 ps)."""
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import core_flow  # noqa: E402

HOOK = HERE / "subtree_balance.tcl"


def test_core_kits_balance_before_final_repair(tmp_path):
    core_flow.apply(tmp_path, core_flow.binding(500.0), "x", rc_cal=False, grt_post_extra=("/work/kit_post.tcl",))
    post = (tmp_path / "grt_post_core.tcl").read_text().splitlines()
    src = [ln for ln in post if ln.startswith("source ")]
    assert src == ["source /work/kit_post.tcl", "source /work/grt_post.tcl", "source /work/subtree_balance.tcl",
                   "source /work/core_final_repair.tcl"], post
    assert (tmp_path / "subtree_balance.tcl").read_text() == HOOK.read_text()


def test_partition_pre_pass_sources_it():
    t = (HERE / "tapbal_grt.tcl").read_text()
    assert "source [file join $tg_dir subtree_balance.tcl]" in t and "OT_STB_BLOCK_SINKS) fixed" in t
    assert '"subtree_balance.tcl"' in (HERE / "gen_phys.py").read_text()


MOCK = r'''
namespace eval ord {}
namespace eval odb {}
namespace eval sta {}
proc ord::get_db_block {} { return blk }
proc ord::get_db {} { return db }
proc db {m args} { if {$m eq "findMaster"} { return M_[lindex $args 0] } }
foreach {m blk} {M_BUFx4_ASAP7_75t_R 0 M_BUFx2_ASAP7_75t_R 0 M_DFFHQNx1_ASAP7_75t_R 0 M_SRAM 1} {
  proc $m {op args} "switch \$op { isBlock { return $blk } getName { return [string range $m 2 end] } }"
}
# objects: A(obj,attr)
proc mkobj {o} { proc $o {op args} "objcall $o \$op {*}\$args" }
proc objcall {o op args} {
  global A NETS
  switch $op {
    getName { return $A($o,name) }
    getNet { return $A($o,net) }
    getInst { return $A($o,inst) }
    getMTerm { return $A($o,mterm) }
    getMaster { return $A($o,master) }
    getITerms { if {[info exists A($o,iterms)]} { return $A($o,iterms) }; set r {}; foreach k [array names A *.*,net] { if {$A($k) eq $o} { lappend r [lindex [split $k ,] 0] } }; return [lsort $r] }
    isInputSignal { return [expr {$A($o,dir) eq "in"}] }
    isOutputSignal { return [expr {$A($o,dir) eq "out"}] }
    isDoNotTouch { return [expr {[info exists A($o,dnt)] && $A($o,dnt)}] }
    setDoNotTouch { set A($o,dnt) [lindex $args 0] }
    getLocation { return {0 0} }
    setLocation - setPlacementStatus - setSigType { return }
    disconnect { set A($o,net) NULL }
    connect { set A($o,net) [lindex $args 0] }
    findITerm { return $o.[lindex $args 0] }
    findBTerm { set b bt_[lindex $args 0]; if {[info commands $b] eq ""} { return NULL }; return $b }
    findInst { set n [lindex $args 0]; if {[info commands $n] eq ""} { return NULL }; return $n }
  }
}
proc mt {name} { proc mt_$name {op} "return $name" }
mt A; mt Y; mt CLK
mkobj blk
proc net {n} { mkobj $n }
proc port {p n} { global A; mkobj bt_$p; set A(bt_$p,net) $n; net $n }
# cell name master in_net out_net(or "") ; delay ps
proc cell {name master in out {d 10}} {
  global A DLY
  mkobj $name; set A($name,name) $name; set A($name,master) $master; set DLY($name) $d
  set its {}
  if {$out ne ""} {
    mkobj $name.A; set A($name.A,net) $in; set A($name.A,inst) $name; set A($name.A,mterm) mt_A; set A($name.A,dir) in
    mkobj $name.Y; set A($name.Y,net) $out; set A($name.Y,inst) $name; set A($name.Y,mterm) mt_Y; set A($name.Y,dir) out
    net $out; set its [list $name.A $name.Y]
  } else {
    mkobj $name.CLK; set A($name.CLK,net) $in; set A($name.CLK,inst) $name; set A($name.CLK,mterm) mt_CLK; set A($name.CLK,dir) in
    set its [list $name.CLK]
  }
  set A($name,iterms) $its
}
proc odb::dbInst_create {b m name} { global A DLY; mkobj $name; set A($name,name) $name; set A($name,master) $m; set DLY($name) 20
  foreach {p d} {A in Y out} { mkobj $name.$p; set A($name.$p,net) NULL; set A($name.$p,inst) $name; set A($name.$p,mterm) mt_$p; set A($name.$p,dir) $d }
  set A($name,iterms) [list $name.A $name.Y]; return $name }
proc odb::dbNet_create {b name} { net $name; return $name }
# STA: arrival of a sink pin = sum of delays of the BUF cells driving its net chain
proc get_pins {args} { set p [string map {/ .} [lindex $args end]]; if {[info commands $p] eq ""} { return {} }; return $p }
proc get_property {p prop} {
  global A DLY
  set t 0; set net $A($p,net)
  while {1} {
    set drv ""
    foreach k [array names A *.Y,net] { if {$A($k) eq $net} { set drv [lindex [split $k ,] 0] } }
    if {$drv eq ""} break
    set i $A($drv,inst); set t [expr {$t + $DLY($i)}]; set net $A($i.A,net)
  }
  return $t
}
foreach c {set_propagated_clock estimate_parasitics global_route sta::arrivals_invalid detailed_placement check_placement global_connect} { proc $c {args} {} }
proc all_clocks {} { return {} }
'''

# clk: b0 -> {b1 (d 10) -> f1, f2 ; b2 (d 70) -> f3} : arrivals f1,f2 = 20, f3 = 80 -> b1 early by 60
# ck2: c0 -> {c1 -> g1 ; c2 (d 50) -> g2 ; c3 -> SRAM pin}  (second port balanced on its own target)
TREE = r'''
port clk n0
cell b0 M_BUFx2_ASAP7_75t_R n0 n_b0
cell b1 M_BUFx2_ASAP7_75t_R n_b0 n_b1
cell b2 M_BUFx2_ASAP7_75t_R n_b0 n_b2 70
cell f1 M_DFFHQNx1_ASAP7_75t_R n_b1 ""
cell f2 M_DFFHQNx1_ASAP7_75t_R n_b1 ""
cell f3 M_DFFHQNx1_ASAP7_75t_R n_b2 ""
port ck2 m0
cell c0 M_BUFx2_ASAP7_75t_R m0 m_c0
cell c1 M_BUFx2_ASAP7_75t_R m_c0 m_c1
cell c2 M_BUFx2_ASAP7_75t_R m_c0 m_c2 50
cell c3 M_BUFx2_ASAP7_75t_R m_c0 m_c3
cell g1 M_DFFHQNx1_ASAP7_75t_R m_c1 ""
cell g2 M_DFFHQNx1_ASAP7_75t_R m_c2 ""
cell u_mem M_SRAM m_c3 ""
set ::env(OT_STB_PORTS) {clk ck2}
'''


def _run(env=""):
    if not shutil.which("tclsh"):
        pytest.skip("no tclsh")
    body = (MOCK + TREE + env + f"\nproc wrap {{}} {{ source {{{HOOK}}} }}\nwrap\n"
            + 'foreach p {f1 f2 f3 g1 g2 u_mem} { puts "ARR $p [get_property $p.CLK arrival_max_rise]" }\n')
    r = subprocess.run(["tclsh"], input=body, text=True, capture_output=True)
    assert r.returncode == 0 and not r.stderr, r.stdout + r.stderr
    arr = {ln.split()[1]: float(ln.split()[2]) for ln in r.stdout.splitlines() if ln.startswith("ARR ")}
    return r.stdout, arr


def test_balances_each_port_tree_to_its_latest_sink():
    out, arr = _run("set ::env(OT_STB_EST) placement\n")
    assert "OT_STB ERROR" not in out, out
    # clk: target 80; b1's subtree (20) gets 2 buffers in round 0 (0.75*52/20 -> 1, then 1 more...) until within tol+stage
    assert 80 - 8 - 20 < arr["f1"] <= 80 and arr["f1"] == arr["f2"] and arr["f3"] == 80, (arr, out)
    # ck2: target 60 (g2); g1 and the macro pin brought up on their own tree, not to clk's 80
    assert 60 - 8 - 20 < arr["g1"] <= 60 and arr["g2"] == 60 and 60 - 8 - 20 < arr["u_mem"] <= 60, (arr, out)
    assert "OT_STB done:" in out and "on 2 clock trees" in out


def test_fixed_macro_subtrees_and_protected_spine_are_never_delayed(tmp_path):
    spine = tmp_path / "spine.tsv"
    out, arr = _run("set ::env(OT_STB_EST) placement\nset ::env(OT_STB_BLOCK_SINKS) fixed\n"
                    "proc b1_dnt {} {}\nset A(b1,dnt) 1\n")
    assert arr["u_mem"] == 20, (arr, out)        # macro subtree fixed (its internal latency is not ours to balance)
    # b1 is DoNotTouch: its sinks still balanced, one level down (in front of f1 / f2 themselves)
    assert 80 - 8 - 20 < arr["f1"] <= 80 and 80 - 8 - 20 < arr["f2"] <= 80, (arr, out)


def test_report_and_off_modes_change_nothing():
    for env, word in (("set ::env(OT_STB) report\n", "OT_STB before"), ("set ::env(OT_STB) 0\n", "OT_STB skipped")):
        out, arr = _run(env)
        assert word in out and arr == {"f1": 20, "f2": 20, "f3": 80, "g1": 20, "g2": 60, "u_mem": 20}, (env, arr, out)
