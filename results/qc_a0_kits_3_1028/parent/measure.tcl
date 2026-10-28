# QC-A0-KITS-3: parent CTS insertion per corner (placement RC, propagated clock). env CORNER=TT|FF ODB OUT
set C $::env(CORNER); set c [string tolower $C]
set L /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
foreach f [lsort [glob $L/asap7sc7p5t_*_RVT_${C}_nldm_*.lib*]] {read_liberty $f}
foreach f [glob /work/macros/*_${c}.lib] {read_liberty $f}
read_db $::env(ODB)
read_sdc /work/constraint.sdc
set_propagated_clock [all_clocks]
source /work/setRC_rcx.tcl
estimate_parasitics -placement
set fh [open $::env(OUT) w]
set nreg 0
foreach inst [get_cells -hier *] {
  set m [get_property $inst ref_name]
  foreach p [get_pins -of_objects $inst -filter "is_clock==1"] {
    set a [get_property $p arrival_max_rise]; set b [get_property $p arrival_min_rise]
    if {[string match "ot_qwen_tile_*" $m]} {
      puts $fh "CHILD [get_full_name $inst] $m $a $b"
    } else { puts $fh "REG $m $a $b"; incr nreg }
  }
}
close $fh
report_clock_skew -include_internal_latency
report_clock_latency -include_internal_latency
report_cts
puts "NREG $nreg"
puts "CELLS [llength [get_cells -hier *]]"
