# S81-CORE-LAT-R10: per-sink clock-pin arrival on a legacy S81 kit's 5_1_grt.odb (model-refit2 meas_ck.tcl form;
# RC = the kit's own setRC_rcx.tcl, GRT basis).  Env: ODB, SDC, OT_CORNER TT|FF, OUT.  Read-only on the kit.
set C $::env(OT_CORNER)
set L /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
foreach f [lsort [glob $L/asap7sc7p5t_*_RVT_${C}_nldm_*.lib*]] { read_liberty $f }
read_db $::env(ODB)
read_sdc $::env(SDC)
source /work/setRC_rcx.tcl
estimate_parasitics -global_routing
set_propagated_clock [all_clocks]
set f [open $::env(OUT) w]
puts $f "# basis GRT estimate_parasitics -global_routing kit setRC_rcx.tcl corner $C"
set n 0
foreach p [all_registers -clock_pins] {
  set v {}
  foreach k {arrival_max_rise arrival_max_fall arrival_min_rise arrival_min_fall} {
    if {[catch {set a [get_property $p $k]}] || $a eq ""} { set a nan }
    lappend v $a
  }
  puts $f "[get_full_name $p]\t[get_full_name [get_nets -of_objects $p]]\t[join $v \t]"; incr n
}
close $f
puts "MEAS_DONE $C $n pins"
exit
