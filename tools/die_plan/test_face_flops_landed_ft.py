"""FLOW-KITFAIL-2 10-29: ft stations of a slot whose input lands on a clock-landing ring (u_cland_*).

Runs the REAL face_flops.tcl walkers and the REAL ft-station pass (tclsh, OpenDB mocked) on a landed slot
in -> u_cland ring (logic) -> s0 -> INV -> s1 -> BUF -> s2 -> out and on the same slot without a ring.
Before the fix the landed slot placed no station (HEAD hd_st_m: 130 missing, collapse 111)."""
import re
import subprocess
from pathlib import Path

SRC = Path(__file__).with_name("face_flops.tcl").read_text()

MOCK = r'''
proc object {name entries} {
 set ::props($name) $entries
 proc $name {method args} {return [dict get [set ::props([lindex [info level 0] 0])] $method]}
}
proc mt {name io sig nm} { object $name [dict create getIoType $io getSigType $sig getName $nm] }
mt mi INPUT SIGNAL A; mt mo OUTPUT SIGNAL Y; mt mD INPUT SIGNAL D; mt mQ OUTPUT SIGNAL QN; mt mC INPUT CLOCK CLK
foreach {m n} {mff DFFHQNx1_ASAP7_75t_R mbuf BUFx2_ASAP7_75t_R minv INVx1_ASAP7_75t_R mlog AO22x1_ASAP7_75t_R} {
 object $m [dict create getName $n getWidth 1080]
}
# net -> iterms built incrementally
proc conn {net it} { lappend ::nets($net) $it; object $net [dict create getITerms $::nets($net)] }
proc cell {name master ins outs} {
 set its {}
 foreach {pin net} $ins { set it ${name}.$pin; object $it [dict create getInst $name getMTerm [expr {$pin eq "D" ? "mD" : ($pin eq "CLK" ? "mC" : "mi")}] getSigType [expr {$pin eq "CLK" ? "CLOCK" : "SIGNAL"}] getNet $net]; conn $net $it; lappend its $it }
 foreach {pin net} $outs { set it ${name}.$pin; object $it [dict create getInst $name getMTerm [expr {$pin eq "QN" ? "mQ" : "mo"}] getSigType SIGNAL getNet $net]; conn $net $it; lappend its $it }
 object $name [dict create getName $name getMaster $master getITerms $its]
}
proc bbox {name x y} { object $name [dict create xMin $x xMax $x yMin $y yMax $y] }
# slot tx: k=3, W face -> E face, pins at y=50 um, frame 0..300 um
proc design {landed {pfx ""}} {
 if {$landed} {
  cell "${pfx}u_cland_tx_i/u_ring/dch\[0\].y\[0\]\$_DFF_P_" mff {D n_in CLK clkf} {QN n_r0}
  cell "${pfx}u_cland_tx_i/u_ring/rd_mux\[0\]" mlog {A n_r0} {Y n_land}
  set d0 n_land
 } else { cell buf_in mbuf {A n_in} {Y n_b}; set d0 n_b }
 cell {u_ft_tx_s0/q[0]$_DFF_P_} mff [list D $d0 CLK clk] {QN n_s0}
 cell inv01 minv {A n_s0} {Y n_s0b}
 cell {u_ft_tx_s1/q[0]$_DFF_P_} mff {D n_s0b CLK clk} {QN n_s1}
 cell buf12 mbuf {A n_s1} {Y n_s1b}
 cell {u_ft_tx_s2/q[0]$_DFF_P_} mff {D n_s1b CLK clk} {QN n_out}
 bbox bbi 0 50000; bbox bbo 300000 50000
 object bti [dict create getSigType SIGNAL getIoType INPUT getName {tx_i[0]} getNet n_in getBBox bbi]
 object bto [dict create getSigType SIGNAL getIoType OUTPUT getName {tx_o[0]} getNet n_out getBBox bbo]
 object blk [dict create getBTerms {bti bto}]
 proc blk {method args} { if {$method eq "findBTerm"} { return [expr {[lindex $args 0] eq {tx_o[0]} ? "bto" : "NULL"}] }; return [dict get $::props(blk) $method] }
}
set ff_blk blk; set ff_dbu 1000; set ff_out stdout
set ff_ft [dict create tx [list 3 W E {}]]
'''


def _procs():
    """every proc of the real hook (all are self-contained helpers)."""
    out = []
    for m in re.finditer(r"^proc (\w+) \{", SRC, re.M):
        i = m.start(); depth = 0; groups = 0; k = SRC.index("{", i)
        # walk to the end of the body: the args brace group, then the body brace group
        while groups < 2:
            if SRC[k] == "{":
                depth += 1
            elif SRC[k] == "}":
                depth -= 1
                if depth == 0:
                    groups += 1
            k += 1
        out.append(SRC[i:k])
    return "\n".join(out)


def _station_pass():
    a = SRC.index("set ff_st 0; set ff_st_miss 0")
    return SRC[a:SRC.index("close $ff_out", a)]


def _run(landed, k=3, pfx=""):
    body = (MOCK + _procs() + "\n"
            + "proc ff_put_near {f x y} { return [list [expr {round($x)}] [expr {round($y)}]] }\n"
            + f"design {landed} {{{pfx}}}\nset ff_done {{}}\nset ff_ft [dict create tx [list {k} W E {{}}]]\n" + _station_pass()
            + '\nputs "RESULT st=$ff_st miss=$ff_st_miss lst=[expr {[info exists ff_lst] ? $ff_lst : 0}]"\n')
    r = subprocess.run(["tclsh"], input=body, text=True, capture_output=True)
    assert r.returncode == 0 and not r.stderr, r.stdout + r.stderr
    return r.stdout


def test_landed_slot_places_all_k_stations_after_the_ring():
    out = _run(1)
    assert "RESULT st=0 miss=0 lst=3" in out, out
    rows = [ln.split("\t") for ln in out.splitlines() if "\tlst" in ln]
    assert [r[0] for r in rows] == ["u_ft_tx_s0/q[0]$_DFF_P_", "u_ft_tx_s1/q[0]$_DFF_P_", "u_ft_tx_s2/q[0]$_DFF_P_"]
    # straight W->E slot, L = 300 um: s_j at L*(j+1)/k = 100, 200, 300 um; no ring cell is claimed
    assert [float(r[2]) for r in rows] == [100.0, 200.0, 300.0], rows
    assert not any("u_cland" in r[0] for r in rows)


def test_unlanded_slot_keeps_station_zero_at_face_path():
    out = _run(0)
    # unchanged code path: s1, s2 at L*j/k (station 0 is the in-face register of the face pass)
    assert "RESULT st=2 miss=0 lst=0" in out, out
    rows = [ln.split("\t") for ln in out.splitlines() if "\tst" in ln]
    assert [(r[0], r[1], float(r[2])) for r in rows] == [("u_ft_tx_s1/q[0]$_DFF_P_", "st1", 100.0),
                                                        ("u_ft_tx_s2/q[0]$_DFF_P_", "st2", 200.0)]


def test_landed_slot_fails_closed_when_the_chain_is_not_k_pure_stations():
    # plan says k=4 but only 3 flops sit between the ring read logic and the out port: place nothing, count missing
    out = _run(1, k=4)
    assert "RESULT st=0 miss=1 lst=0" in out, out


def test_landed_slot_inside_a_bound_wrapper():
    # S81 kit-rtl kits: the ring is u_bound.u_cland_<slot>_i (flattened hierarchical name), same station recovery
    for pfx in ("u_bound.", "u_bound/"):
        out = _run(1, pfx=pfx)
        assert "RESULT st=0 miss=0 lst=3" in out, (pfx, out)
