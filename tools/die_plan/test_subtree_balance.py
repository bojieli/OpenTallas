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
                   "source /work/core_drv_repair.tcl", "source /work/core_final_repair.tcl"], post
    assert (tmp_path / "subtree_balance.tcl").read_text() == HOOK.read_text()


def test_core_kits_run_repair_design_once_when_incremental_repair_skipped(tmp_path):
    """S81-CORES-1115: the POST override replaced post_grt_drv.tcl; core_drv_repair.tcl is the one repair_design, self-gated on
    SKIP_INCREMENTAL_REPAIR=1, staged next to the final repair."""
    core_flow.apply(tmp_path, core_flow.binding(500.0), "x", rc_cal=False)
    t = (tmp_path / "core_drv_repair.tcl").read_text()
    assert t == (HERE / "core_drv_repair.tcl").read_text()
    assert t.count("repair_design -slew_margin 40 -cap_margin 20") == 1 and t.count("global_route -start_incremental") == 1
    assert 'SKIP_INCREMENTAL_REPAIR) ne "1"' in t and "repair_timing" not in t.replace("# ", "")
    post = (tmp_path / "grt_post_core.tcl").read_text().splitlines()
    assert post.index("source /work/core_drv_repair.tcl") < post.index("source /work/core_final_repair.tcl")


def test_partition_pre_pass_sources_it():
    t = (HERE / "tapbal_grt.tcl").read_text()
    assert "source [file join $tg_dir subtree_balance.tcl]" in t and "OT_STB_BLOCK_SINKS) fixed" in t
    assert '"subtree_balance.tcl"' in (HERE / "gen_phys.py").read_text()


MOCK = r'''
namespace eval ord {}
namespace eval odb {}
namespace eval sta {}
set ::mock_ps_per_ui 1.0
proc sta::time_sta_ui {seconds} { return [expr {$seconds * 1.0e12 / $::mock_ps_per_ui}] }
proc ord::get_db_block {} { return blk }
proc ord::get_db {} { return db }
proc db {m args} { if {$m eq "findMaster"} { return M_[lindex $args 0] } }
foreach {m blk} {M_BUFx4_ASAP7_75t_R 0 M_INVx4_ASAP7_75t_R 0 M_BUFx2_ASAP7_75t_R 0 M_DFFHQNx1_ASAP7_75t_R 0 M_SRAM 1} {
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
  return [expr {$t / $::mock_ps_per_ui}]
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


def _run(env="", *, hook=HOOK, after=""):
    if not shutil.which("tclsh"):
        pytest.skip("no tclsh")
    body = (MOCK + TREE + env + f"\nproc wrap {{}} {{ source {{{hook}}} }}\nwrap\n"
            + 'foreach p {f1 f2 f3 g1 g2 u_mem} { puts "ARR $p [get_property $p.CLK arrival_max_rise]" }\n' + after)
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


@pytest.mark.parametrize("ps_per_ui", [1.0, 1000.0])
def test_subunit_arrival_uses_sta_units_and_does_not_pad_tap(ps_per_ui):
    env = (f"set ::mock_ps_per_ui {ps_per_ui}\n"
           "set ::env(OT_STB_EST) placement\nset ::env(OT_STB_PORTS) clk\n"
           "set DLY(b0) 0.0\nset DLY(b1) 0.351169\nset DLY(b2) 0.951777\n")
    after = ('puts "NORMALIZED [stb::arr f1/CLK] [stb::arr f3/CLK]"\n')
    out, _ = _run(env, after=after)
    assert "OT_STB ERROR" not in out
    assert "OT_STB done: 0 delay buffers" in out
    measured = out.split("NORMALIZED ")[1].splitlines()[0].split()
    assert list(map(float, measured)) == pytest.approx([0.351169, 0.951777])


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


def test_forwarded_output_without_local_sinks_is_not_padded(tmp_path):
    # A real sink-bearing tree also forks into an output-only clock buffer.
    # No receiver is present during partition hardening, so that fork has no
    # local sequential sink. The positive case runs the real balancing hook.
    env = "set ::env(OT_STB_EST) placement\ncell fwd M_BUFx2_ASAP7_75t_R n_b0 n_fwd\n"
    after = 'puts "ARR fwd [get_property fwd.A arrival_max_rise]"\n'
    out, arr = _run(env, after=after)
    assert "OT_STB ERROR" not in out
    assert arr["fwd"] == 10, out
    # Mutant reproduces the measured silicon defect: twelve gratuitous stages
    # on each of eight rounds, even though legitimate local sinks still close.
    mutant = tmp_path / "sinkless_mutant.tcl"
    text = HOOK.read_text()
    guard = "        if {$::stb::hi($p,$n) == -1e9} { continue }\n"
    assert guard in text
    mutant.write_text(text.replace(guard, "", 1))
    _, bad = _run(env, hook=mutant, after=after)
    assert bad["fwd"] == 10 + 96 * 20


def test_inverter_pair_pads_and_span_acceptance():
    """S81-RCK-BALANCE: OT_STB_PAIR=1 pads with two inverters per stage (mock: +20 ps each), the span line reports PASS/FAIL."""
    env = ("set ::env(OT_STB_EST) placement\nset ::env(OT_STB_PORTS) clk\nset ::env(OT_STB_PAIR) 1\n"
           "set ::env(OT_STB_CELL) INVx4_ASAP7_75t_R\nset ::env(OT_STB_STAGE) 40\nset ::env(OT_STB_SPAN_MAX) 30\n")
    out, arr = _run(env, after='puts "NINV [llength [lsearch -all -inline -not [info commands delaybuf_otstb_*] *.*]]"\n')
    assert "OT_STB ERROR" not in out, out
    assert arr["f1"] == 60 and arr["f3"] == 80, (arr, out)               # one pair (+40) on b1's subtree
    assert "NINV 2" in out, out                                             # exactly two inverters for one pair
    assert "OT_STB_SPAN clk sinks 3 min 60.0 max 80.0 span 20.0 limit 30.0 PASS" in out, out
    tight = env.replace("SPAN_MAX) 30", "SPAN_MAX) 10") + "set ::env(OT_STB_SPAN_FAIL) 1\n"
    out2, _ = _run(tight)
    assert "OT_STB_SPAN clk" in out2 and "FAIL" in out2 and "OT_STB ERROR" in out2, out2


def test_rck_balance_hook_is_opt_in_after_leaf_repeat_and_staged():
    post = (HERE / "cts_post.tcl").read_text()
    assert 'OT_S81_RCK_BALANCE) eq "1"' in post and "rck_balance.tcl" in post
    assert post.index("leaf_affinity.tcl") < post.index("rck_balance.tcl")
    rb = (HERE / "rck_balance.tcl").read_text()
    for need in ("OT_STB_PAIR) 1", "OT_STB_EST) placement", "INVx4_ASAP7_75t_R", "OT_STB_SPAN_MAX", "io_pma_rck[0]", "subtree_balance.tcl"):
        assert need in rb, need
    gp = (HERE / "gen_phys.py").read_text()
    assert '"rck_balance.tcl"' in gp and "OT_S81_RCK_BALANCE" in gp


def test_cts_post_balances_in_tap_subtrees_before_the_tap_pad():
    """DIE-CORETAP-1119 (FABLE-CLOSURE lever 1): the post-CTS edits (leaf repeat, long-wire buffers) make a few branches of a
    tap late and the tap pad is capped at that latest sink, so the subtree balance runs first on placement RC, per tap port,
    hard-core subtrees fixed, under its own cell tag; OT_CTS_STB=0 restores the old order."""
    post = (HERE / "cts_post.tcl").read_text()
    text = "\n".join(ln for ln in post.splitlines() if not ln.lstrip().startswith("#"))
    assert text.index("subtree_balance.tcl") < text.index("tap_balance.tcl") < text.index("leaf_affinity.tcl")
    assert '$::env(OT_CTS_STB) ne "0")' in text
    assert "OT_STB_EST placement OT_STB_BLOCK_SINKS fixed OT_STB_TAG c" in text
    assert "unset ::env($k)" in text                       # caller settings restored for a later rck_balance pass
    deps = (HERE / "signoff.py").read_text().split('"cts_post.tcl": (')[1].split(")")[0]
    assert '"subtree_balance.tcl"' in deps


def test_tag_keeps_cell_names_of_two_passes_apart():
    env = "set ::env(OT_STB_EST) placement\nset ::env(OT_STB_TAG) c\n"
    after = 'puts "TAGGED [llength [info commands delaybuf_otstb_c*]] PLAIN [llength [info commands {delaybuf_otstb_[0-9]*}]]"\n'
    out, arr = _run(env, after=after)
    assert "OT_STB ERROR" not in out, out
    assert 80 - 8 - 20 < arr["f1"] <= 80, (arr, out)
    tagged = int(out.split("TAGGED ")[1].split()[0])
    plain = int(out.split("PLAIN ")[1].split()[0])
    assert tagged > 0 and plain == 0, out
    # untagged pass (tapbal_grt.tcl, a later process) keeps the old names
    out2, _ = _run("set ::env(OT_STB_EST) placement\n", after=after)
    assert int(out2.split("TAGGED ")[1].split()[0]) == 0 and int(out2.split("PLAIN ")[1].split()[0]) > 0, out2


def test_sentinel_arrival_is_unmeasured_not_a_target():
    """TAP-GRID-R5 11-22: QC slw_hc1 cle683a076 clk_t11/t18 sinks read ~9.4e11 ps (unset STA arrival); the latest-sink target
    padded long delay chains per tap (2,062 ps raw insertion).  A sink beyond OT_STB_ARR_MAX_PS (1 us) is skipped."""
    env = ("set ::env(OT_STB_EST) placement\nset ::env(OT_STB_PORTS) clk\n"
           "rename get_property _gp\n"
           "proc get_property {p prop} { if {$p eq \"f3.CLK\"} { return 948620000000.0 }; return [_gp $p $prop] }\n")
    out, arr = _run(env)
    assert "OT_STB ERROR" not in out
    # f3 unmeasured -> clk target = f1/f2 (20): nothing padded, no 1e11 target
    assert "target 20.0" in out and "OT_STB done: 0 delay buffers" in out, out
    assert arr["f1"] == 20 and arr["f2"] == 20, (arr, out)


def test_target_capped_at_the_tap_bound_far_sink():
    """STB-BOUND 11-24 (QC-CBX-CLOCK): cbn_q01 clab6e67f2 clk_t66 padded its ~280 ps sinks to a 753 ps far sink (19 otstb in
    series, tap 811 ps).  The target is min(latest sink, bound); bound = OT_TAP_TARGET_PS + OT_TAP_WINDOW_PS on placement RC.
    Mock: clk f1/f2 at 20, far f3 at 80; bound 30 + 20 = 50 -> f1/f2 padded only up to <= 50, f3 left as built."""
    env = ("set ::env(OT_STB_EST) placement\nset ::env(OT_STB_PORTS) clk\n"
           "set ::env(OT_TAP_TARGET_PS) 30\nset ::env(OT_TAP_WINDOW_PS) 20\n")
    out, arr = _run(env)
    assert "OT_STB ERROR" not in out, out
    assert "target 50.0 (latest sink 80.0 over the bound: capped)" in out, out
    assert 50 - 8 - 20 < arr["f1"] <= 50 and arr["f1"] == arr["f2"] and arr["f3"] == 80, (arr, out)
    # slowest mode lifts the base to OT_TAP_SLOWEST_MAX_PS; explicit 0 = the old latest-sink rule
    out2, arr2 = _run(env + "set ::env(OT_TAP_BALANCE_TO) slowest\nset ::env(OT_TAP_SLOWEST_MAX_PS) 70\n")
    assert "OT_STB before clk" in out2 and "latest sink, fixed" in out2 and arr2["f1"] > 50, (arr2, out2)
    out3, arr3 = _run(env + "set ::env(OT_STB_TARGET_MAX_PS) 0\n")
    assert 80 - 8 - 20 < arr3["f1"] <= 80, (arr3, out3)


def test_grt_cap_adds_routed_margin_and_core_kits_are_uncapped():
    env = "set ::env(OT_STB_EST) grt\nset ::env(OT_STB_PORTS) clk\nset ::env(OT_TAP_TARGET_PS) 10\nset ::env(OT_TAP_WINDOW_PS) 0\n"
    out, arr = _run(env + "set ::env(OT_STB_GRT_MARGIN_PS) 40\n")
    assert "target 50.0 (latest sink 80.0 over the bound: capped)" in out, out
    out2, arr2 = _run("set ::env(OT_STB_EST) grt\nset ::env(OT_STB_PORTS) clk\n")      # no OT_TAP_TARGET_PS: old rule
    assert "target 80.0 (latest sink, fixed)" in out2 and 80 - 8 - 20 < arr2["f1"] <= 80, (arr2, out2)
