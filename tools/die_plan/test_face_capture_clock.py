"""Execute the actual input-capture walker against data/clock MTerm controls."""
import subprocess
from pathlib import Path

def test_data_capture_never_follows_clock_mterm():
    source=(Path(__file__).with_name("face_flops.tcl")).read_text()
    a=source.index("proc ff_from_in ")
    b=source.index("# output port:",a)
    body=source[a:b]
    fixture=r"""
proc ff_is_ff {i} {return 1}
proc ff_is_buf {i} {return 0}
proc data_net {m} {return data_it}
proc clock_net {m} {return clock_it}
proc mixed_net {m} {return {clock_it data_it}}
proc data_it {m} {if {$m eq "getInst"} {return data_ff}; return data_mt}
proc clock_it {m} {if {$m eq "getInst"} {return clock_ff}; return clock_mt}
proc data_mt {m} {if {$m eq "getIoType"} {return INPUT}; return SIGNAL}
proc clock_mt {m} {if {$m eq "getIoType"} {return INPUT}; return CLOCK}
"""
    checks=r"""
if {[ff_from_in data_net 0] ne "data_ff"} {error "real data capture lost"}
if {[ff_from_in clock_net 0] ne ""} {error "clock incorrectly claimed a capture"}
if {[ff_from_in mixed_net 0] ne "data_ff"} {error "clock won over real data"}
puts "PASS actual ff_from_in data/clock/mixed controls"
"""
    r=subprocess.run(["tclsh"],input=fixture+body+checks,text=True,capture_output=True)
    assert r.returncode==0 and not r.stderr and "PASS actual" in r.stdout, r.stdout+r.stderr


def test_real_face_walkers_match_four_stage_geometry_contract():
    """LP fault BUF10->BUF3->INV->FF must be anchored, never cross logic/clock."""
    source=Path(__file__).with_name('face_flops.tcl').read_text()
    walkers=source[source.index('proc ff_is_ff '):source.index('# CP1 r6:')]
    fixture=r'''
# Generic OpenDB object fixture, using the real three placement walkers.
proc object {name entries} {
 set ::props($name) $entries
 proc $name {method} [format {return [dict get $::props(%s) $method]} $name]
}
proc build {n {kind buf} {clock 0}} {
 for {set i 0} {$i <= $n} {incr i} {
  set master [expr {$i == $n ? "DFFASRHQNx1_ASAP7_75t_R" : ($kind eq "logic" && $i == 1 ? "OR2x1_ASAP7_75t_R" : ($i == 2 ? "INVx1_ASAP7_75t_R" : "BUFx3_ASAP7_75t_R"))}]
  object m$i [dict create getName $master]
  object c$i [dict create getMaster m$i getITerms [list d$i q$i]]
  object md$i [dict create getIoType INPUT getSigType [expr {$i == $n && $clock ? "CLOCK" : "SIGNAL"}]]
  object mq$i [dict create getIoType OUTPUT getSigType SIGNAL]
  object d$i [dict create getInst c$i getMTerm md$i getSigType SIGNAL getNet n$i]
  object q$i [dict create getInst c$i getMTerm mq$i getSigType SIGNAL getNet n[expr {$i+1}]]
 }
 for {set i 0} {$i <= $n+1} {incr i} {
  set ts {}
  if {$i <= $n} {lappend ts d$i}
  if {$i > 0} {lappend ts q[expr {$i-1}]}
  object n$i [dict create getITerms $ts]
 }
}
'''
    checks=r'''
build 3
if {[ff_from_in n0 0] ne "c3"} {error "actual LP three-stage capture missed"}
if {[ff_from_out n4 0] ne "c3"} {error "direct flop output missed"}
# Output chain: c0 is flop, c1..c3 buffers. Swap only actual master typing.
object m0 [dict create getName DFFHQNx1_ASAP7_75t_R]
object m3 [dict create getName INVx1_ASAP7_75t_R]
if {[ff_from_out n4 0] ne "c0"} {error "three-stage output missed"}
if {[ff_chain_out n4 0] ne "c3 c2 c1 c0"} {error "clone chain incomplete"}
build 4
if {[ff_from_in n0 0] ne "c4"} {error "four-stage contract missed"}
build 5
if {[ff_from_in n0 0] ne ""} {error "five-stage capture incorrectly accepted"}
build 3 logic
if {[ff_from_in n0 0] ne ""} {error "logic gate mutant crossed"}
build 3 buf 1
if {[ff_from_in n0 0] ne ""} {error "clock pin mutant captured"}
puts "PASS actual four-stage face walkers and logic/clock/depth mutants"
'''
    r=subprocess.run(['tclsh'],input=fixture+walkers+checks,text=True,capture_output=True)
    assert r.returncode==0 and not r.stderr and 'PASS actual four-stage' in r.stdout,r.stdout+r.stderr
