"""FLOW-QC-CB 11-17 (FABLE-PD-QC-0600): the xstn join test looks through buffers/inverters, and the b_d tree stretch check
counts every terminal load (it printed 0 with 81 stretched paths present)."""
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = (ROOT / "tools/die_plan/core_input_chain.tcl").read_text()


def tcl_procs(names):
    out = []
    for name in names:
        m = re.search(r"^proc " + re.escape(name) + r"\s+\{[^\n]*?\}\s+\{", SRC, re.M)
        assert m, name
        i, depth = m.end(), 1
        while depth:
            c = SRC[i]
            i += 1
            if c == "\\":
                i += 1
                continue
            depth += (c == "{") - (c == "}")
        out.append(SRC[m.start():i])
    return "\n".join(out) + "\n"


# a tiny odb: cells have a name, master, status, x, y; nets connect an output iterm to input iterms
MOCK = r'''
set ::cells {}; set ::nets {}
proc mk {name master x y {status PLACED}} { dict set ::cells $name [list $master $x $y $status]; return $name }
proc conn {net drv args} { dict set ::nets $net [list $drv $args] }
proc iterm {inst net dir} { return [list $inst $net $dir] }
proc cell_master {n} { return [lindex [dict get $::cells $n] 0] }
# object commands: instance "I:name", iterm "T:inst:net:dir", net "N:name", master "M:name"
rename unknown ::unk_orig
proc unknown {cmd args} {
  lassign [split $cmd :] kind a b c
  switch -- $kind {
    I { switch [lindex $args 0] {
          getName { return $a }
          getMaster { return "M:[cell_master $a]" }
          getPlacementStatus { return [lindex [dict get $::cells $a] 3] }
          getBBox { return "B:$a" }
          getITerms { set r {}; dict for {n v} $::nets { lassign $v drv sinks
              if {$drv eq $a} { lappend r "T:$a:$n:out" }
              foreach s $sinks { if {$s eq $a} { lappend r "T:$a:$n:in" } } }; return $r } } }
    M { switch [lindex $args 0] { getName { return $a } isBlock { return [string match "BLK*" $a] } } }
    T { switch [lindex $args 0] { isOutputSignal { return [expr {$c eq "out"}] } isInputSignal { return [expr {$c eq "in"}] }
          getInst { return "I:$a" } getNet { return "N:$b" } } }
    N { switch [lindex $args 0] { getITerms { lassign [dict get $::nets $a] drv sinks; set r [list "T:$drv:$a:out"]
          foreach s $sinks { lappend r "T:$s:$a:in" }; return $r } getSigType { return SIGNAL } } }
    B { set x [lindex [dict get $::cells $a] 1]; set y [lindex [dict get $::cells $a] 2]
        switch [lindex $args 0] { xMin - xMax { return $x } yMin - yMax { return $y } } }
    default { return [uplevel 1 [list ::unk_orig $cmd {*}$args]] }
  }
}
proc nc_mov {inst} { return [expr {[$inst getPlacementStatus] ni {FIRM LOCKED COVER}}] }
'''
PROCS = ["nc_isbuf", "nc_ctr", "nc_join_cone", "nc_stretched", "nc_tree_stretch"]


def run(body):
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "probe.tcl"
        f.write_text(MOCK + tcl_procs(PROCS) + body)
        p = subprocess.run(["tclsh", str(f)], capture_output=True, text=True)
    assert p.returncode == 0, p.stdout + p.stderr
    return p.stdout


# the cbn_q01 b_d[463] shape: trunk buffer t2 drives the AND4 (member) and a second branch buffer -> INV -> FIRM istation flop
SHAPE = r'''
mk and4 AND4x1 74 1920; mk t1 BUFx6f 41 1386; mk t2 BUFx3 39 1857; mk b3 BUFx3 39 1900; mk inv INVx1 39 2000
mk ist DFFHQNx1 40 2101 FIRM
conn n1 t1 t2; conn n2 t2 and4 b3; conn n3 b3 inv; conn n4 inv ist
set nx_in [dict create I:and4 1]
'''


def test_trunk_with_a_buffered_second_branch_joins_with_its_pass_through_cells():
    out = run(SHAPE.replace("set nx_in [dict create I:and4 1]", "") + r'''
proc nm {l} { set r {}; foreach i $l { lappend r [$i getName] }; return [lsort $r] }
''' + r'''
set nx_in [dict create and4 1]
puts "CONE [nm [nc_join_cone I:t2 $nx_in]]"
puts "CONE1 [nm [nc_join_cone I:t1 [dict create and4 1 t2 1]]]"
''')
    assert "CONE b3 inv t2" in out          # t2 + the buffer and the inverter behind its second branch
    assert "CONE1 t1" in out                # then the relay behind it follows (next round)


def test_a_non_flop_non_member_terminal_blocks_the_join():
    out = run(r'''
mk and4 AND4x1 74 1920; mk t2 BUFx3 39 1857; mk other NAND2x1 1 1; mk ist DFFHQNx1 40 2101
conn n2 t2 and4 other
set nx_in [dict create and4 1]
puts "CONE [llength [nc_join_cone I:t2 $nx_in]]"
''')
    assert "CONE 0" in out


def test_a_cell_with_no_terminal_member_or_flop_does_not_join():
    out = run(r'''
mk t2 BUFx3 39 1857; mk t3 BUFx3 39 1900
conn n2 t2 t3
set nx_in [dict create]
puts "CONE [llength [nc_join_cone I:t2 $nx_in]]"
''')
    assert "CONE 0" in out


def test_stretch_predicate_needs_both_3x_and_100um():
    out = run(r'''
puts "S [nc_stretched 3000 1000 1] [nc_stretched 3100 1000 1] [nc_stretched 120 30 1] [nc_stretched 1003 139 1]"
puts "D [nc_stretched 1003 139 1] [nc_stretched 1003000 139000 1000]"
''')
    assert "S 0 1 0 1" in out


def test_tree_stretch_counts_every_terminal_load_of_a_b_d_tree():
    out = run(r'''
set nc_blk "K:blk"
set nc_dbu 1
proc K:blk {m} { set r {}; dict for {n v} $::cells { lappend r I:$n }; return $r }
# b_d head at (76,1783); stranded relay 400 um south then back; second branch to a FIRM flop
mk x.u_st.b_d\[463\] DFFHQNx3 76 1783; mk p1 BUFx6f 41 1386; mk p2 BUFx3 39 1857; mk and4 AND4x1 74 1920; mk b3 BUFx3 39 1900; mk ist DFFHQNx1 40 2101
conn q x.u_st.b_d\[463\] p1; conn n1 p1 p2; conn n2 p2 and4 b3; conn n3 b3 ist
puts "TS [nc_tree_stretch]"
''')
    assert "TS 2 2 1" in out


def test_check_prints_and_stops_with_the_documented_names():
    assert "OT_XSTN_STRETCH b_d_paths" in SRC
    assert "OT_NK_STRETCH_STOP" in SRC and "OT_NK_STRETCH_MAX" in SRC
    i = SRC.index("OT_XSTN_STRETCH b_d_paths")
    assert 'error "OT_XSTN_STRETCH' in SRC[i:i + 900]
    # the old direct-load-only test is gone
    assert "set ok 1; set nl 0" not in SRC
