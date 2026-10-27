# QC-SU-KITS-3 measurement (read-only on the kit): per-sink clock-pin arrival, rise/fall min/max, on GRT parasitics
# (estimate_parasitics -global_routing, cf/rc_cal.tcl OT_RC_CAL 0.8,0.9) or on RCX SPEF (env SPEF).  Env: ODB, SDC, OT_CORNER TT|FF, OUT.
set C $::env(OT_CORNER); set c [string tolower $C]
set L /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
foreach f [lsort [glob $L/asap7sc7p5t_*_RVT_${C}_nldm_*.lib*]] { read_liberty $f }
foreach f [glob -nocomplain /work/macros/*_${c}.lib] { read_liberty $f }
read_db $::env(ODB)
read_sdc $::env(SDC)
if {[info exists ::env(SPEF)] && $::env(SPEF) ne ""} {
  read_spef $::env(SPEF); set basis "RCX $::env(SPEF)"
} else {
  set ::env(OT_RC_CAL) 0.8,0.9
  source /work/cf/rc_cal.tcl
  estimate_parasitics -global_routing; set basis "GRT estimate_parasitics -global_routing rc_cal 0.8,0.9"
}
set_propagated_clock [all_clocks]
set f [open $::env(OUT) w]
puts $f "# basis $basis corner $C"
set n 0
foreach p [all_registers -clock_pins] {
  set net [get_nets -of_objects $p]
  set nn [get_full_name $net]
  set v {}
  foreach k {arrival_max_rise arrival_max_fall arrival_min_rise arrival_min_fall} {
    if {[catch {set a [get_property $p $k]}] || $a eq ""} { set a nan }
    lappend v $a
  }
  puts $f "[get_full_name $p]\t$nn\t[join $v \t]"; incr n
}
close $f
puts "MEAS_DONE $C $n pins"
exit
