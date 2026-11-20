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
# pin name of an iterm: D for an input and Y for an output unless "pin inst net NAME" says otherwise
set ::pins {}
proc pin {inst net name} { dict set ::pins $inst,$net $name }
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
          getInst { return "I:$a" } getNet { return "N:$b" }
          getMTerm { if {[dict exists $::pins $a,$b]} { return "P:[dict get $::pins $a,$b]" }; return [expr {$c eq "out" ? "P:Y" : "P:D"}] } } }
    P { switch [lindex $args 0] { getName { return $a } } }
    N { switch [lindex $args 0] { getITerms { lassign [dict get $::nets $a] drv sinks; set r [list "T:$drv:$a:out"]
          foreach s $sinks { lappend r "T:$s:$a:in" }; return $r } getSigType { return SIGNAL } } }
    B { set x [lindex [dict get $::cells $a] 1]; set y [lindex [dict get $::cells $a] 2]
        switch [lindex $args 0] { xMin - xMax { return $x } yMin - yMax { return $y } } }
    default { return [uplevel 1 [list ::unk_orig $cmd {*}$args]] }
  }
}
proc nc_mov {inst} { return [expr {[$inst getPlacementStatus] ni {FIRM LOCKED COVER}}] }
'''
PROCS = ["nc_isbuf", "nc_ctr", "nc_load_terms", "nc_data_pin", "nc_median_pt", "nc_clamp_box", "nc_buf_neigh", "nc_join_cone",
         "nc_stretched", "nc_tree_stretch"]


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


# FLOW-QC-N 11-17 (FABLE-FIX-QC-N, cbn_q01 n1b): reset-relay sinks are not boundary registers; filled buffers sit with their nets
def test_data_pin_excludes_clock_and_async_reset_set():
    out = run(r"""
puts "P [nc_data_pin D] [nc_data_pin RESETN] [nc_data_pin SETN] [nc_data_pin CLK] [nc_data_pin A]"
""")
    assert "P 1 0 0 0 1" in out


def test_an_outside_register_reached_at_resetn_blocks_the_join_and_a_member_does_not():
    out = run(r"""
mk m1 DFFASRHQNx1 600 700; mk r1 BUFx6f 610 720; mk r2 BUFx6f 598 758; mk far DFFASRHQNx1 18 217; mk o DFFHQNx1 40 2101
conn n1 r1 m1; pin m1 n1 RESETN
conn n2 r2 far; pin far n2 RESETN
set nx_in [dict create m1 1]
puts "OWN [llength [nc_join_cone I:r1 $nx_in]]"
puts "RELAY [llength [nc_join_cone I:r2 $nx_in]]"
mk d1 BUFx3 1 1; conn n4 d1 o
puts "DATA [llength [nc_join_cone I:d1 $nx_in]]"
""")
    assert "OWN 1" in out        # a reset buffer that feeds only members still joins
    assert "RELAY 0" in out      # the relay towards another block's reset pins does not
    assert "DATA 1" in out       # an outside flop at its D pin is the output pipe: joinable as before


def test_load_terms_keep_the_pin_through_buffers():
    out = run(r"""
mk s DFFHQNx1 0 0; mk b BUFx3 1 1; mk i INVx1 2 2; mk f1 DFFASRHQNx1 3 3; mk f2 DFFHQNx1 4 4; mk g NAND2x1 5 5
conn q s b g; conn n1 b i f2; conn n2 i f1; pin f1 n2 RESETN; pin g q B
set r {}; foreach t [nc_load_terms I:s] { lappend r "[[$t getInst] getName]/[[$t getMTerm] getName]" }
puts "LT [lsort $r]"
""")
    assert "LT f1/RESETN f2/D g/B" in out


def test_median_point_and_clamp():
    out = run(r"""
puts "M3 [nc_median_pt {{1167 1923} {1164 1965} {1204 2272}}]"
puts "M2 [nc_median_pt {{0 0} {10 4}}]"
puts "M4 [nc_median_pt {{0 0} {10 4} {2 8} {4 100}}]"
puts "M0 [llength [nc_median_pt {}]]"
puts "C [nc_clamp_box 5 50 10 20 30 40] [nc_clamp_box 15 25 10 20 30 40]"
""")
    assert "M3 1167 1965" in out
    assert "M2 5.0 2.0" in out
    assert "M4 3.0 6.0" in out
    assert "M0 0" in out
    assert "C 10 40 15 25" in out


# the cbn_q01 x_1_3 b_d[383] shape (um): the fill put the QN inverter 51 um east of its head and of its NAND load
B383 = r"""
set nc_blk "K:blk"
set nc_dbu 1
proc K:blk {m} { set r {}; dict for {n v} $::cells { lappend r I:$n }; return $r }
mk x.u_st.b_d\[383\] DFFHQNx1 1167 1923; mk inv INVx1 1218 1951; mk nand NAND2x1 1164 1965; mk and3 AND3x1 1158 1947
mk ist DFFHQNx2 1204 2272 FIRM
conn qn x.u_st.b_d\[383\] inv and3; conn n1 inv nand ist
"""


def test_filled_inverter_at_the_median_of_driver_and_loads_removes_the_stretch():
    out = run(B383 + r"""
puts "BEFORE [nc_tree_stretch]"
puts "NEIGH [lsort [nc_buf_neigh I:inv]]"
lassign [nc_median_pt [nc_buf_neigh I:inv]] x y
lassign [nc_clamp_box $x $y 1158 1757 1231 2065] x y
puts "AT $x $y"
dict set ::cells inv [list INVx1 $x $y PLACED]
puts "AFTER [nc_tree_stretch]"
""")
    assert "BEFORE 3 1 1" in out             # 147 built for a 45 pair
    assert "NEIGH {1164 1965} {1167 1923} {1204 2272}" in out
    assert "AT 1167 1965" in out
    assert "AFTER 3 0 0" in out


def test_fill_second_pass_and_reset_sink_count_are_wired_and_printed():
    i = SRC.index("nc_put $i $x $y; incr nx_cells; incr nx_k")
    j = SRC.index("set nx_far {}", i)
    assert "set nx_pts [nc_buf_neigh $i]" in SRC[i:j] and "nc_median_pt $nx_pts" in SRC[i:j]
    assert "nc_clamp_box $x $y $wx0 $wy0 $wx1 $wy1" in SRC[i:j]
    k = SRC.index("OT_XSTN_KEEP $nx_cl")
    assert "reset_sinks_excluded $nx_rst" in SRC[k:k + 300]
    k = SRC.index('puts "OT_XSTN_SITE xstn')
    assert "fill_bufs_resited $nx_rebuf reset_sinks_excluded $nx_rst_all" in SRC[k:k + 500]
    # a boundary register needs the D pin, direct or through buffers
    assert SRC.count("if {[nc_data_pin [[$l getMTerm] getName]]} { lappend nx_bnd $li } else { incr nx_rst }") == 1
    assert SRC.count("if {[nc_data_pin [[$xt getMTerm] getName]]} { lappend nx_bnd $xi } else { incr nx_rst }") == 1


def test_xstn_stretch_is_advisory_by_default():
    """SONNET-FIX-QC 11-19: the b_d stretch count stops the kit only with OT_NK_STRETCH_STOP=1 (default report-only)."""
    assert 'eq "1"} {\n    error "OT_XSTN_STRETCH' in SRC
    assert "OT_XSTN_STRETCH ADVISORY" in SRC
    assert 'ne "0")} {\n    error "OT_XSTN_STRETCH' not in SRC
