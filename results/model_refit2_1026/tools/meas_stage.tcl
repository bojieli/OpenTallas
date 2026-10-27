# MODEL-REFIT-2 read-only stage decomposition: for every ot_ms_* clock buffer: input/output arrival+slew (rise/fall,
# max/min) and per clock-net wire/pin cap (report_net). GRT parasitics (rc_cal 0.8,0.9) or SPEF. Env ODB SDC OT_CORNER OUT [SPEF]
set C $::env(OT_CORNER); set c [string tolower $C]
set L /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
foreach f [lsort [glob $L/asap7sc7p5t_*_RVT_${C}_nldm_*.lib*]] { read_liberty $f }
foreach f [glob -nocomplain /work/macros/*_${c}.lib] { read_liberty $f }
read_db $::env(ODB)
read_sdc $::env(SDC)
if {[info exists ::env(SPEF)] && $::env(SPEF) ne ""} { read_spef $::env(SPEF); set basis "RCX" } else {
  set ::env(OT_RC_CAL) 0.8,0.9; source /work/cf/rc_cal.tcl; estimate_parasitics -global_routing; set basis GRT }
set_propagated_clock [all_clocks]
report_checks -path_delay min -group_path_count 1 > /dev/null
set f [open $::env(OUT) w]
puts $f "# basis $basis corner $C"
foreach i [get_cells ot_ms_*] {
  set n [get_full_name $i]
  foreach pn {A Y} {
    set p [get_pins -quiet $n/$pn]
    if {$p eq ""} continue
    set dir [get_property $p direction]
    set v {}
    foreach k {arrival_max_rise arrival_max_fall slew_max_rise slew_max_fall arrival_min_rise arrival_min_fall} {
      if {[catch {set a [get_property $p $k]}] || $a eq ""} { set a nan }
      lappend v $a
    }
    set net [get_nets -quiet -of_objects $p]
    set nn [expr {$net eq "" ? "-" : [get_full_name $net]}]
    puts $f "PIN\t$n\t[get_property $p lib_pin_name]\t$dir\t$nn\t[get_property [get_lib_cells -of_objects $i] name]\t[join $v \t]"
  }
}
close $f
foreach net [get_nets ot_ms_*] { set nn [get_full_name $net]; puts "NETRPT $nn"; report_net -digits 4 $nn }
puts "STAGE_DONE"
exit
