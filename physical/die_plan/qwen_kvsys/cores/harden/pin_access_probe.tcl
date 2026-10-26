# Diagnostic only: native placement/PDN/all cells, route only data-pin landing nets.
# inputs /work/{3_place.odb,3_place.sdc,ot_face_flops.txt,pin_controls.tcl}
set P /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
foreach l [glob $P/asap7sc7p5t_*RVT_TT_*.lib*] {
  if {![string match *FAKE* $l]} { read_liberty $l }
}
read_db /work/3_place.odb
read_sdc /work/3_place.sdc
source /work/pin_controls.tcl
set pa_block [ord::get_db_block]
set pa_targets {}
set fh [open /work/ot_face_flops.txt r]
foreach line [split [read $fh] \n] {
  set fields [split $line \t]
  if {[llength $fields] >= 5} { dict set pa_targets [lindex $fields 4] [lindex $fields 0] }
}
close $fh
set pa_nets {}
proc pa_buf {inst} { return [regexp {^(BUF|INV|HB)} [[$inst getMaster] getName]] }
proc pa_walk {net target input depth seen} {
  global pa_nets
  if {$net eq "NULL" || $net eq "" || $depth > 32 || [dict exists $seen [$net getName]]} { return 0 }
  dict set seen [$net getName] 1
  dict set pa_nets [$net getName] 1
  foreach it [$net getITerms] {
    set mt [$it getMTerm]
    if {($input && [$mt getIoType] ne "INPUT") || (!$input && [$mt getIoType] ne "OUTPUT")} continue
    set inst [$it getInst]
    if {[$inst getName] eq $target} {
      if {[$mt getName] in {CLK clk CK ck RESETN SETN RN SN}} { error "data pin lands on control pin $target/[$mt getName]" }
      return 1
    }
    if {![pa_buf $inst]} continue
    foreach next [$inst getITerms] {
      if {[$next getSigType] ni {SIGNAL CLOCK}} continue
      if {($input && [[$next getMTerm] getIoType] ne "OUTPUT") || (!$input && [[$next getMTerm] getIoType] ne "INPUT")} continue
      if {[pa_walk [$next getNet] $target $input [expr {$depth+1}] $seen]} { return 1 }
    }
  }
  return 0
}
set pa_count 0
foreach bt [$pa_block getBTerms] {
  if {[$bt getSigType] ne "SIGNAL"} continue
  set name [$bt getName]
  regsub {\[[0-9]+\]$} $name {} base
  if {$base in $pa_controls} continue
  if {![dict exists $pa_targets $name]} { error "no dedicated landing record for $name" }
  set target [dict get $pa_targets $name]
  if {![pa_walk [$bt getNet] $target [expr {[$bt getIoType] eq "INPUT"}] 0 {}]} {
    error "pin $name cannot reach its dedicated flop $target through buffers"
  }
  incr pa_count
}
if {$pa_count != $pa_expected_ports} { error "data pin count $pa_count != expected $pa_expected_ports" }
puts "PIN_ACCESS_PROBE ports $pa_count native_cells [llength [$pa_block getInsts]] nets [dict size $pa_nets]"
set_routing_layers -signal M2-M7
foreach L {M2 M3 M4 M5 M6 M7} { set_global_routing_layer_adjustment $L 0.4 }
set_nets_to_route [dict keys $pa_nets]
set begin [clock seconds]
global_route -congestion_iterations 50 -allow_congestion -verbose -congestion_report_file /work/congestion.rpt
puts "OT_GRT_S [expr {[clock seconds]-$begin}]"
puts "PIN_ACCESS_PROBE_DONE ports $pa_count nets [dict size $pa_nets] capacity_reservation 0.4 original_capacity_utilization_upper_bound 0.6_if_zero_overflow"
