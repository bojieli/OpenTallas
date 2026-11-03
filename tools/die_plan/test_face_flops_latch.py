"""face_flops.tcl out-face lockup latch (LATCH-FACE, COORD 11-03 08:25): the real output walker passes an ASAP7
DLL / DHL latch through its D pin to the face flop behind it (gunit_l1c RF-1: 316 ports were 'without a flop within
2 buffers'), never through its CLK pin, and still stops at logic."""
import subprocess
from pathlib import Path

SRC = Path(__file__).with_name("face_flops.tcl").read_text()
WALKERS = SRC[SRC.index("proc ff_is_ff "):SRC.index("# CP1 r6:")]

FIXTURE = r'''
proc object {name entries} {
 set ::props($name) $entries
 proc $name {method} [format {return [dict get $::props(%s) $method]} $name]
}
# port net np <- BUF b (A: nl) <- latch L (Q: nl; D: nd, CLK: nc) ; nd <- flop F (QN) ; nc <- decoy flop K (QN)
proc build {lmaster dpin {mid BUFx2_ASAP7_75t_R}} {
 object mF [dict create getName DFFHQNx1_ASAP7_75t_R]
 object mK [dict create getName DFFHQNx1_ASAP7_75t_R]
 object mL [dict create getName $lmaster]
 object mB [dict create getName $mid]
 object tin [dict create getIoType INPUT getSigType SIGNAL getName A]
 object tD [dict create getIoType INPUT getSigType SIGNAL getName $dpin]
 object tC [dict create getIoType INPUT getSigType SIGNAL getName CLK]
 object tout [dict create getIoType OUTPUT getSigType SIGNAL getName Q]
 object F [dict create getMaster mF getName F getITerms {Fq}]
 object K [dict create getMaster mK getName K getITerms {Kq}]
 object L [dict create getMaster mL getName L getITerms {LD LC Lq}]
 object B [dict create getMaster mB getName B getITerms {Ba Bq}]
 object Fq [dict create getInst F getMTerm tout getSigType SIGNAL getNet nd]
 object Kq [dict create getInst K getMTerm tout getSigType SIGNAL getNet nc]
 object LD [dict create getInst L getMTerm tD getSigType SIGNAL getNet nd]
 object LC [dict create getInst L getMTerm tC getSigType SIGNAL getNet nc]
 object Lq [dict create getInst L getMTerm tout getSigType SIGNAL getNet nl]
 object Ba [dict create getInst B getMTerm tin getSigType SIGNAL getNet nl]
 object Bq [dict create getInst B getMTerm tout getSigType SIGNAL getNet np]
 object nd [dict create getITerms {Fq LD}]
 object nc [dict create getITerms {Kq LC}]
 object nl [dict create getITerms {Lq Ba}]
 object np [dict create getITerms {Bq}]
}
'''

CHECKS = r'''
build DLLx1_ASAP7_75t_R D
if {[ff_from_out np 0] ne "F"} {error "flop behind a DLL face latch missed: [ff_from_out np 0]"}
if {[ff_chain_out np 0] ne "B L F"} {error "latch chain incomplete: [ff_chain_out np 0]"}
build DHLx2_ASAP7_75t_SL D
if {[ff_from_out np 0] ne "F"} {error "flop behind a DHL face latch missed"}
build DLLx1_ASAP7_75t_R DX
if {[ff_from_out np 0] ne ""} {error "latch walker followed a non-D pin (CLK side decoy K)"}
build OR2x2_ASAP7_75t_R D
if {[ff_from_out np 0] ne ""} {error "logic gate crossed as a latch"}
build DLLx1_ASAP7_75t_R D AND2x2_ASAP7_75t_R
if {[ff_from_out np 0] ne ""} {error "logic between latch and port crossed"}
puts "PASS face latch walker"
'''


def test_out_face_latch_walker():
    r = subprocess.run(["tclsh"], input=FIXTURE + WALKERS + CHECKS, text=True, capture_output=True)
    assert r.returncode == 0 and not r.stderr and "PASS face latch walker" in r.stdout, r.stdout + r.stderr


def test_clone_keeps_latch_clock_on_original_net():
    i = SRC.index("proc ff_clone_for ")
    body = SRC[i:SRC.index("\n}\n", i)]
    assert '[ff_is_latch $i] && [$mt getName] ne "D"' in body
