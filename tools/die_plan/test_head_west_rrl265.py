"""C-RRL265-WEST (HEAD-INT-R2 11-26): head_west_rrl265.tcl re-derived from the netlist structure (default off; staged only with
OT_HEAD_WEST_RRL265=1 on hd_lep0N_w).  Plan side (gen_phys wiring) and the Tcl side (check mode) in tclsh with OpenDB mocked, plus
mutants of the Tcl text that each one scenario must catch.  The apply path is proven on the real W11 3_4 odb (replay post)."""
import shutil
import subprocess
from pathlib import Path

import pytest

import gen_phys

HERE = Path(__file__).resolve().parent
HOOK = HERE / "head_west_rrl265.tcl"
needs_tcl = pytest.mark.skipif(shutil.which("tclsh") is None, reason="tclsh not installed")

MOCK = r'''
array set ::D {}
set ::n 0
proc obj {id m args} {
    switch -- $m {
        getName - getMaster - getBBox - getNet - getInst - getMTerm - getIoType - getWire - getITerms - getWidth - getHeight - getOrient {
            return $::D($id,[string tolower [string range $m 3 end]]) }
        isBlock { return $::D($id,isblock) }
        getLocation { return [list $::D($id,x) $::D($id,y)] }
        getPlacementStatus { return PLACED }
        findITerm { foreach t $::D($id,iterms) { if {[[$t getMTerm] getName] eq [lindex $args 0]} { return $t } }; return NULL }
        getSigType { return SIGNAL }
        isSpecial - isSoft { return 0 }
        getBTerms { return {} }
        xMin { return [lindex $::D($id,box) 0] }
        yMin { return [lindex $::D($id,box) 1] }
        xMax { return [lindex $::D($id,box) 2] }
        yMax { return [lindex $::D($id,box) 3] }
        getOrigin { return [list 4320 $::D($id,y)] }
        getSpacing { return 54 }
        getSite { return $::SITE }
        getSiteCount { return 16000 }
        getRows { return $::rows }
        getInsts { return $::insts }
        getBlockages { return {} }
        getDbUnitsPerMicron { return 1000 }
        findInst { foreach i $::insts { if {[$i getName] eq [lindex $args 0]} { return $i } }; return NULL }
        findNet { return NULL }
        findMaster { return $::BUF }
        default { error "mock: $id $m" }
    }
}
proc mk {kind props} { set id ${kind}[incr ::n]; foreach {k v} $props { set ::D($id,$k) $v }; proc $id args "obj $id {*}\$args"; return $id }
proc mkmaster {name block w h} { mk master [list name $name isblock $block width $w height $h] }
proc inst {name master x y} {
    set b [mk box [list box [list $x $y [expr {$x+[$master getWidth]}] [expr {$y+[$master getHeight]}]]]]
    mk inst [list name $name master $master x $x y $y bbox $b iterms {}]
}
proc pin {i name io} {
    set t [mk iterm [list inst $i mterm [mk mterm [list name $name]] iotype $io net NULL]]
    lappend ::D($i,iterms) $t
    return $t
}
proc connect {netname args} {
    set n [mk net [list name $netname wire NULL iterms $args]]
    foreach t $args { set ::D($t,net) $n }
    return $n
}
proc um {v} { expr {round($v*1000)} }
namespace eval ord {}
proc ord::get_db_block {} { return $::BLK }
proc ord::get_db {} { return $::BLK }
set ::insts {}
set ::rows {}
set ::BLK [mk block {}]
set ::BUF [mkmaster BUFx6f_ASAP7_75t_R 0 1080 270]
set ::SITE [mk site {height 270}]
for {set y 1100000} {$y < 1420000} {incr y 270} {
    lappend ::rows [mk row [list y $y orient [expr {(($y/270)%2) ? "MX" : "R0"}]]]
}
proc macro {x0 y0 x1 y1} { set m [mkmaster BLK 1 [expr {$x1-$x0}] [expr {$y1-$y0}]]; lappend ::insts [inst macro$::n $m $x0 $y0] }
proc blocker {x0 y0 x1 y1} { set m [mkmaster STDBLK 0 [expr {$x1-$x0}] [expr {$y1-$y0}]]; lappend ::insts [inst fill$::n $m $x0 $y0] }
# gate g (um), buffers {{x y master} ...}, capture c (um): the West tap 61 reset branch
proc build {g bufs c} {
    set and [mkmaster AND2x4_ASAP7_75t_R 0 540 270]
    set dff [mkmaster DFFHQNx1_ASAP7_75t_R 0 1080 270]
    set inv [mkmaster INVx1_ASAP7_75t_R 0 270 270]
    set gate [inst u_rrl_265/_3_ $and [um [lindex $g 0]] [um [lindex $g 1]]]
    set a [pin $gate A INPUT]; set b [pin $gate B INPUT]; set y [pin $gate Y OUTPUT]
    set cp [inst {u_rrl_265/q$_DFF_P_} $dff [um [lindex $c 0]] [um [lindex $c 1]]]
    set d [pin $cp D INPUT]; set qn [pin $cp QN OUTPUT]
    set out [inst u_rrl_265/_2_ $inv [um 700] [um 1370]]
    set oa [pin $out A INPUT]; set oy [pin $out Y OUTPUT]
    set ra [pin [inst u_rrl_264/_1_ $inv 0 0] Y OUTPUT]
    set rb [pin [inst u_srl_264/_1_ $inv 0 0] Y OUTPUT]
    connect rst_rl_264 $ra $a
    connect rn_rst_rl_264 $rb $b
    connect u_rrl_265/_1_ $qn $oa
    connect rst_n_t61 $oy
    lappend ::insts $gate $cp $out
    set prev $y
    set k 0
    foreach bd $bufs {
        lassign $bd bx by mname
        incr k
        set bi [inst u_rrl_265/place$k [mkmaster $mname 0 540 270] [um $bx] [um $by]]
        lappend ::insts $bi
        set ba [pin $bi A INPUT]; set bo [pin $bi Y OUTPUT]
        connect u_rrl_265/n$k $prev $ba
        set prev $bo
    }
    connect u_rrl_265/nlast $prev $d
    return [list $gate $cp]
}
proc runcheck {} { if {[catch {west_d51_265_buffer check} e]} { puts "RESULT ERROR $e" } else { puts "RESULT ok" } }
'''

W11_BUFS = "{{726 1333 BUFx3_ASAP7_75t_R}}"          # post-DPL W11: gate -> BUFx3 -> D, hops 245 / 99 um
SCEN = {
    "W11": f"build {{847 1209}} {W11_BUFS} {{672 1377}}\nruncheck",
    "OLD_SHAPE": "build {847 1209} {{800 1250 BUFx3_ASAP7_75t_R} {720 1300 BUFx16f_ASAP7_75t_R}} {672 1377}\nruncheck",
    "SHORT": "build {847 1209} {{790 1260 BUFx3_ASAP7_75t_R}} {740 1300}\nruncheck",
    "DIRECT": "build {847 1209} {} {800 1300}\nruncheck",
    "NONBUF": f"build {{847 1209}} {{{{726 1333 AND2x4_ASAP7_75t_R}}}} {{672 1377}}\nruncheck",
    "MULTISINK": (f"lassign [build {{847 1209}} {W11_BUFS} {{672 1377}}] g c\n"
                  "set yn [[$g findITerm Y] getNet]\nset x [pin $c Q INPUT]\nset ::D($x,net) $yn\n"
                  "set ::D($yn,iterms) [concat $::D($yn,iterms) $x]\nruncheck"),
    "MACRO": f"macro [um 780] [um 1150] [um 820] [um 1400]\nbuild {{847 1209}} {W11_BUFS} {{672 1377}}\nruncheck",
    # the sites around the ideal seat are taken: the nearest free one breaks the leg bound
    "CROWDED": f"blocker [um 825] [um 1305] [um 870] [um 1360]\nbuild {{847 1209}} {W11_BUFS} {{672 1377}}\nruncheck",
    "BADGATE": "lassign [build {847 1209} {} {800 1300}] g c\nset ::D([$g getMaster],name) AND2x2_ASAP7_75t_R\nruncheck",
}


def run(scen, tmp, hook_text=None):
    (tmp / "mock.tcl").write_text(MOCK)
    (tmp / "hook.tcl").write_text(HOOK.read_text() if hook_text is None else hook_text)
    (tmp / "run.tcl").write_text(f"source {tmp}/mock.tcl\nsource {tmp}/hook.tcl\n{SCEN[scen]}\n")
    p = subprocess.run(["tclsh", str(tmp / "run.tcl")], capture_output=True, text=True, timeout=300)
    return (p.stdout + p.stderr).strip()


def legs(out):
    return [float(x) for x in out.split("new legs ")[1].split(" um")[0].split()]


@needs_tcl
def test_w11_shape_gets_one_buffer_inside_the_bound(tmp_path):
    out = run("W11", tmp_path)
    assert "RESULT ok" in out and "1 buffers" in out and "1 existing buffers" in out, out
    assert max(legs(out)) <= 138.402 and len(legs(out)) == 3, out


@needs_tcl
def test_old_asserted_shape_still_planned(tmp_path):
    out = run("OLD_SHAPE", tmp_path)
    assert "RESULT ok" in out and "2 existing buffers" in out, out
    assert max(legs(out)) <= 138.402, out


@needs_tcl
def test_short_branch_is_left_alone(tmp_path):
    out = run("SHORT", tmp_path)
    assert "RESULT ok" in out and "0 buffers" in out, out


@needs_tcl
def test_direct_gate_to_d_branch(tmp_path):
    out = run("DIRECT", tmp_path)
    assert "RESULT ok" in out and "0 existing buffers" in out, out


@needs_tcl
@pytest.mark.parametrize("scen,msg", [
    ("NONBUF", "West rrl265 unexpected branch destination"),
    ("MULTISINK", "West rrl265 branch is not single-load"),
    ("MACRO", "West rrl265 no macro-clear route"),
    ("CROWDED", "West rrl265 seated legs do not meet the bound"),
    ("BADGATE", "West rrl265 gate identity changed"),
])
def test_structure_changes_fail_closed(tmp_path, scen, msg):
    out = run(scen, tmp_path)
    assert f"RESULT ERROR {msg}" in out, out


MUTANTS = [
    ("drop-single-load", "[llength $sinks] != 1", "0", "MULTISINK", "branch is not single-load"),
    ("accept-any-destination", 'error "West rrl265 unexpected branch destination', 'puts "accept', "NONBUF", "unexpected branch destination"),
    ("no-macro-clear", "if {$clear} { return $corner }", "return $corner", "MACRO", "no macro-clear route"),
    ("one-buffer-short", "int(ceil(double($len)/$leg - 1e-9)) - 1)", "int(ceil(double($len)/$leg - 1e-9)) - 2)", "W11", "1 buffers"),
    ("bound-unchecked", "if {$l > $leg || $l > 405*$dbu ||", "if {0 ||", "CROWDED", "seated legs do not meet the bound"),
    ("no-scope", "string match ${::west_d51_265_scope}* [$inst getName]", "0", "W11", "RESULT ok"),
]


@needs_tcl
@pytest.mark.parametrize("name,old,new,scen,marker", MUTANTS)
def test_mutants_are_caught(tmp_path, name, old, new, scen, marker):
    text = HOOK.read_text()
    assert text.count(old) == 1, f"mutant {name}: anchor not unique"
    (tmp_path / "h").mkdir()
    (tmp_path / "m").mkdir()
    healthy = run(scen, tmp_path / "h")
    mutated = run(scen, tmp_path / "m", text.replace(old, new))
    assert marker in healthy, healthy
    assert marker not in mutated, mutated


def test_gen_phys_wiring_default_off(tmp_path):
    assert gen_phys.post_dpl_hook_lines([], tmp_path, env={}, type_name="hd_lep0N_w") == []
    assert gen_phys.post_dpl_hook_lines([], tmp_path, env={"OT_HEAD_WEST_RRL265": "1"}, type_name="hd_lep0N") == []
    assert gen_phys.post_dpl_hook_lines([], tmp_path, env={"OT_HEAD_WEST_RRL265": "0"}, type_name="hd_lep0N_w") == []
    assert list(tmp_path.iterdir()) == []


def test_gen_phys_wiring_flag_on(tmp_path):
    lines = gen_phys.post_dpl_hook_lines([], tmp_path, env={"OT_HEAD_WEST_RRL265": "1"}, type_name="hd_lep0N_w")
    assert lines == ["export POST_DETAIL_PLACE_TCL = /work/post_dpl_chain.tcl"]
    assert (tmp_path / "head_west_rrl265.tcl").read_text() == HOOK.read_text()
    assert (tmp_path / "head_west_rrl265_apply.tcl").read_text() == "source /work/head_west_rrl265.tcl\nwest_d51_265_buffer apply\n"
    assert "head_west_rrl265_apply.tcl" in (tmp_path / "post_dpl_chain.tcl").read_text()


def test_hook_has_no_fixed_seat_or_branch_shape():
    t = "\n".join(l for l in HOOK.read_text().splitlines() if not l.lstrip().startswith("#"))
    assert "848.934" not in t and "824.958" not in t
    assert "BUFx16f" not in t and "BUFx3_ASAP7" not in t
