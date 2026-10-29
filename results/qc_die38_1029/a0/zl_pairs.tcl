# DIE-QC-38 A0: every zero-logic register pair (capture D/SETN-free data pin driven by a launch register output through
# BUF/INV only) -> TSV launch_ck_pin capture_ck_pin (STA names). Netlist only; no timing.
read_db $::env(ODB)
set L /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
foreach f [lsort [glob $L/asap7sc7p5t_*_RVT_FF_nldm_*.lib*]] { read_liberty $f }
foreach f [glob -nocomplain /work/macros/*_ff.lib] { read_liberty $f }
set fh [open $::env(OUT) w]
set n 0
foreach r [all_registers -edge_triggered] {
  set m [get_property $r ref_name]
  if {![regexp {^DFF} $m]} continue
  set d [get_pins -quiet -of_objects $r -filter "lib_pin_name==D"]
  if {$d eq ""} continue
  set net [get_nets -quiet -of_objects $d]; set k 0
  while {$net ne "" && $k < 8} {
    set dp [get_pins -quiet -of_objects $net -filter "direction==output"]
    if {$dp eq ""} break
    set i [get_cells -of_objects [lindex $dp 0]]; set im [get_property $i ref_name]
    if {[regexp {^(BUF|INV|HB)} $im]} { incr k; set net [get_nets -quiet -of_objects [get_pins -of_objects $i -filter "lib_pin_name==A"]]; continue }
    if {[regexp {^DFF} $im] && $i ne $r} { puts $fh "[get_full_name $i]/CLK\t[get_full_name $r]/CLK\t$k"; incr n }
    break
  }
}
close $fh
puts "OT38_PAIRS $n"
