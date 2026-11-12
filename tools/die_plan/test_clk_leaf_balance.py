"""CLK-LEAF-BAL-1 11-11: delay-aware clkleafrep sizing (OT_CLK_LEAF_REPEAT_BALANCE=1, default off).

Local, no Docker/OpenROAD: the Tcl runs under tclsh with mocked odb / sta commands.  Off = the hook's output and
command log are unchanged; on = every clkleafrep group (cousins under one grandparent net + siblings) is balanced by
sizing the faster members toward the slowest one at both scenes, inside the slew limit."""
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import test_clk_leaf_repeat_default as T  # noqa: E402

CLR = T.CLR


# ------------------------------------------------------------------------------------------------ off = unchanged
@pytest.mark.parametrize("body", [T.DEFAULT, T.GRT_RUN])
@pytest.mark.parametrize("slew", [358.0, 10.0])
def test_off_is_identical(tmp_path, body, slew):
    (tmp_path / "unset").mkdir()
    ref = T.tcl(tmp_path / "unset", body, design=T.DESIGN, slew=slew)
    for k, v in enumerate(("0", "", "no")):
        d = tmp_path / f"v{k}"
        d.mkdir()
        got = T.tcl(d, body, env={"OT_CLK_LEAF_REPEAT_BALANCE": v}, design=T.DESIGN, slew=slew)
        assert got == ref
    assert "OT_CLK_LEAF_BALANCE" not in ref[0]


def test_every_balance_call_is_gated():
    src = CLR.read_text().splitlines()
    calls = [k for k, ln in enumerate(src) if "[clr_balance " in ln and not ln.lstrip().startswith(("#", "proc "))]
    assert len(calls) == 1                                       # CTS pass only (no GRT-pass balance)
    for k in calls:
        assert any("[clr_bal_on]" in src[j] for j in range(k - 3, k)), src[k]


# ------------------------------------------------------------------------------------------------ on: wiring
WIRE_MOCK = r"""
proc all_clocks {} { return {} }
proc worst_slack {args} { L worst_slack {*}$args; return 0 }
"""


def test_cts_balance_runs_after_legal_tree(tmp_path):
    out, log = T.tcl(tmp_path, WIRE_MOCK + T.DEFAULT, env={"OT_CLK_LEAF_REPEAT_BALANCE": "1"}, design=T.DESIGN)
    # a repeater went in (mock DB has no clkleafrep instance to measure): balance called on the legal tree, no resize,
    # so no second legalization
    assert "OT_CLK_LEAF_BALANCE cts done: 0 groups, 0 repeaters resized" in out
    tail = log[next(k for k, x in enumerate(log) if x.startswith("insert_buffer")):]
    # the balance re-estimates (swapMaster drops estimated parasitics): start of round 1 + final
    assert [x for x in tail if x.startswith(("dpl", "check_placement", "est"))][-5:] == \
        ["dpl", "check_placement", "check_placement", "est -placement", "est -placement"], log


def test_grt_balance_without_groups_is_silent(tmp_path):
    out, log = T.tcl(tmp_path, WIRE_MOCK + T.GRT_RUN, env={"OT_CLK_LEAF_REPEAT_BALANCE": "1"}, design=T.DESIGN, slew=120.0)
    assert "OT_CLK_LEAF_BALANCE" not in out and not any(x.startswith("global_route") for x in log)


# ------------------------------------------------------------------------------------------------ on: algorithm
# delay model: leaf arrival max = wire(inst) + cell(master), min = 0.9 x max; slew = slew(master)
ALGO = r"""
namespace eval ord {}; namespace eval sta {}
set ::env(OT_CLK_LEAF_REPEAT) 0
source @CLR@
set ::log {}
proc L {args} { lappend ::log [join $args " "] }
array set ::cell {BUFx24 3 BUFx8 8 BUFx4 15 HB4 25 BUFx2 30}
array set ::sl {BUFx24 10 BUFx8 20 BUFx4 40 HB4 60 BUFx2 120}
foreach m [array names ::cell] { proc m_$m {op args} "return $m" }
proc mkrep {name wire m} {
  set ::wire($name) $wire; set ::mst($name) m_$m
  proc $name {op args} "switch \$op { getName { return $name } getMaster { return \$::mst($name) } swapMaster { set ::mst($name) \[lindex \$args 0\]; L swap $name \[lindex \$args 0\] } }"
}
proc blk {op args} { if {$op eq "findInst"} { return [lindex $args 0] } }
proc ord::get_db_block {} { return blk }
proc clr_bal_masters {m} { return {m_BUFx24 m_BUFx8 m_BUFx4 m_HB4 m_BUFx2} }
proc clr_sta_refresh {} {}
proc all_clocks {} { return {} }
proc clr_rep_meas {i} {
  set m [$::mst($i) getName]; set d [expr {$::wire($i) + $::cell($m)}]
  return [list $d [expr {0.9 * $d}] $::sl($m) 4]
}
@DESIGN@
set n [clr_balance $::groups test]
puts "N=$n"
foreach r [lsort [array names ::mst]] { puts "M $r [$::mst($r) getName]" }
"""


def algo(tmp_path, design, env=None):
    if not shutil.which("tclsh"):
        pytest.skip("tclsh unavailable")
    t = tmp_path / "algo.tcl"
    t.write_text(ALGO.replace("@CLR@", str(CLR)).replace("@DESIGN@", design))
    e = {k: v for k, v in os.environ.items() if not k.startswith("OT_CLK_LEAF")}
    p = subprocess.run(["tclsh", str(t)], env=dict(e, **(env or {})), capture_output=True, text=True)
    assert p.returncode == 0, p.stdout + p.stderr
    m = {ln.split()[1]: ln.split()[2] for ln in p.stdout.splitlines() if ln.startswith("M ")}
    n = int(next(ln for ln in p.stdout.splitlines() if ln.startswith("N="))[2:])
    return p.stdout, n, m


def test_short_branch_takes_weaker_master(tmp_path):
    # long branch 50 ps wire + BUFx24 = 53 (reference); short 25 + 3 = 28 -> HB4 (25 + 25 = 50, within 3 ps at both
    # scenes); BUFx2 (55) would also fit but its 120-ps slew exceeds the 80-ps limit
    out, n, m = algo(tmp_path, "mkrep ra 50 BUFx24; mkrep rb 25 BUFx24\nset ::groups {{g {ra rb}}}")
    assert n == 1 and m == {"ra": "BUFx24", "rb": "HB4"}, out
    assert "worst group leaf-arrival spread (max scene) 25.0 -> 3.0 ps" in out


def test_slew_limit_from_env_and_own_slew(tmp_path):
    # OT_CLK_LEAF_SLEW_PS 130 admits BUFx2 (55 vs 53: cost 2 < HB4's 3)
    out, n, m = algo(tmp_path, "mkrep ra 50 BUFx24; mkrep rb 25 BUFx24\nset ::groups {{g {ra rb}}}",
                     env={"OT_CLK_LEAF_SLEW_PS": "130"})
    assert m["rb"] == "BUFx2", out
    # a 30-ps limit keeps BUFx4 (40) as the best admissible
    out, n, m = algo(tmp_path, "mkrep ra 50 BUFx24; mkrep rb 25 BUFx24\nset ::groups {{g {ra rb}}}",
                     env={"OT_CLK_LEAF_SLEW_PS": "30"})
    assert m["rb"] == "BUFx8", out          # 30-ps limit: BUFx4 (40 ps slew) out too; BUFx8 33 beats BUFx24 28


def test_within_tolerance_keeps_masters(tmp_path):
    out, n, m = algo(tmp_path, "mkrep ra 50 BUFx24; mkrep rb 48 BUFx24\nset ::groups {{g {ra rb}}}")
    assert n == 0 and set(m.values()) == {"BUFx24"} and "swap" not in out


def test_mean_target_slows_only_members_below_it(tmp_path):
    # OT_CLK_LEAF_BAL_TARGET=mean (default): the level mean (here 40.5 / 36.45 from the leaves of the whole level,
    # un-repeated cousins included) is the target; ra (53) is above it and keeps BUFx24, rb (28) -> BUFx4 (40 / 36)
    d = ("mkrep ra 50 BUFx24; mkrep rb 25 BUFx24\nset ::groups {{g {ra rb} gnet 0}}\n"
         "proc clr_level_target {g} { return {40.5 36.45} }")
    out, n, m = algo(tmp_path, d)
    assert n == 1 and m == {"ra": "BUFx24", "rb": "BUFx4"}, out
    # max mode ignores the level target (slowest member = reference)
    d2 = d.replace("proc clr_level_target {g} { return {40.5 36.45} }", "")
    out, n, m = algo(tmp_path, d2, env={"OT_CLK_LEAF_BAL_TARGET": "max"})
    assert m["rb"] == "HB4", out


def test_three_members_each_sized_to_reference(tmp_path):
    out, n, m = algo(tmp_path, "mkrep ra 60 BUFx24; mkrep rb 48 BUFx24; mkrep rc 40 BUFx24\nset ::groups {{g {rb ra rc}}}")
    # ref ra 63: rb 48 + 15 (BUFx4) = 63; rc 40 + 25 (HB4) = 65 (cost 2 at max, 1.8 at min)
    assert m == {"ra": "BUFx24", "rb": "BUFx4", "rc": "HB4"}, out


# ------------------------------------------------------------------------------------------------ groups from the DB
GROUPS = r"""
namespace eval ord {}; namespace eval sta {}
set ::env(OT_CLK_LEAF_REPEAT) 0
source @CLR@
# objects: inst name -> {in net, out net}; nets: name -> {driver inst, load insts}
proc mkinst {name in out {m BUFx4_ASAP7_75t_R}} {
  set ::io($name) [list $in $out]
  proc m_$m {op args} "return $m"
  proc $name {op args} "switch \$op { getName { return $name } getMaster { return m_$m } getITerms { return {it_${name}_i it_${name}_o} } }"
  proc it_${name}_i {op args} "switch \$op { isInputSignal { return 1 } isOutputSignal { return 0 } getNet { return \[expr {\"$in\" eq {} ? {NULL} : \"n_$in\"}\] } getInst { return $name } }"
  proc it_${name}_o {op args} "switch \$op { isInputSignal { return 0 } isOutputSignal { return 1 } getNet { return n_$out } getInst { return $name } }"
}
proc mknet {name} { proc n_$name {op args} "switch \$op { getName { return $name } getITerms { return \[netits $name\] } }" }
proc netits {n} { set o {}; foreach i [array names ::io] { lassign $::io($i) a b; if {$a eq $n} { lappend o it_${i}_i }; if {$b eq $n} { lappend o it_${i}_o } }; return $o }
foreach n {root g p1 p2 p3 o1 o2 o3 o4 q3 lone} { mknet $n }
mkinst top root g
mkinst d1 g p1; mkinst d2 g p2
mkinst clkleafrep_1 p1 o1; mkinst clkleafrep_3 p1 o3; mkinst clkleafrep_2 p2 o2
mkinst clkleafrep_4 o1 o4
mkinst d3 g p3; mkinst ff3 p3 q3 DFFHQNx1_ASAP7_75t_R
mkinst lb1 o3 lone; mkinst lb2 o2 lone; mkinst lb4 o4 lone
proc blk {op args} { return {top d1 d2 d3 ff3 lb1 lb2 lb4 clkleafrep_1 clkleafrep_2 clkleafrep_3 clkleafrep_4} }
proc ord::get_db_block {} { return blk }
foreach g [clr_bal_groups] {
  puts "G [lindex $g 0] | [lsort [lindex $g 1]] | [lrange $g 2 3]"
  puts "L [lsort [lmap it [clr_level_leaves n_[lindex $g 2] [lindex $g 3]] {$it getInst}]]"
}
"""


def test_groups_are_cousins_and_nested_last(tmp_path):
    if not shutil.which("tclsh"):
        pytest.skip("tclsh unavailable")
    t = tmp_path / "g.tcl"
    t.write_text(GROUPS.replace("@CLR@", str(CLR)))
    e = {k: v for k, v in os.environ.items() if not k.startswith("OT_CLK_LEAF")}
    p = subprocess.run(["tclsh", str(t)], env=e, capture_output=True, text=True)
    assert p.returncode == 0, p.stdout + p.stderr
    g = [ln[2:] for ln in p.stdout.splitlines() if ln.startswith("G ")]
    lv = [ln[2:] for ln in p.stdout.splitlines() if ln.startswith("L ")]
    # clkleafrep_1/_3 (parent p1) and _2 (parent p2) share grandparent g; _4 sits under _1 -> its own group, last
    assert g == ["g (grandparent) | clkleafrep_1 clkleafrep_2 clkleafrep_3 | g 0", "o1 | clkleafrep_4 | o1 1"], p.stdout
    # level leaves of g: through the repeaters (lb1 via _3, lb2 via _2, lb4 via _1 -> _4) AND the un-repeated cousin
    # leaf net p3 (ff3); the nested level o1 holds lb4 only
    assert lv == ["ff3 lb1 lb2 lb4", "lb4"], p.stdout
