# PATH-QC-RP1-F59 review dump (TT, GRT RC + measure-basis tap correction, as measure.tcl): every register / macro clock
# pin: instance, location (um), clock arrival (ps), its region tap (walk up the clock tree to ot_ctap_*), leaf net.
#   env MC ODB SDC OUT
set C $::env(MC)
foreach l [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*_RVT_${C}_*] {read_liberty $l}
read_liberty /work/macros/ot_sram_1r1w_1024x256_m2_r2c2_[string tolower $C].lib
read_db $::env(ODB)
read_sdc $::env(SDC)
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
source /work/rc_cal.tcl
set_global_routing_layer_adjustment * 0.3
set_routing_layers -signal M2-M5 -clock M2-M5
set_macro_extension 2
global_route -congestion_iterations 30
estimate_parasitics -global_routing
set_propagated_clock [all_clocks]
source /work/ctap_corr.tcl
ot_ctap_assign [list [list $ot_ctap_corr_meas [expr {$C eq "FF"}] {} max]]
foreach c [all_clocks] { if {[llength [get_property $c sources]]} { set_clock_latency -source 0 $c } }
set blk [ord::get_db_block]; set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
proc tapof {inst} {
  set i $inst
  for {set d 0} {$d < 16} {incr d} {
    if {[regexp {^ot_ctap_([A-Za-z0-9]+)$} [$i getName] -> r]} { return $r }
    set n ""
    foreach it [$i getITerms] { if {[$it isInputSignal] || [[$it getMTerm] getSigType] eq "CLOCK"} { if {[[$it getMTerm] getIoType] eq "INPUT" && [$it getNet] ne "NULL"} { set n [$it getNet]; break } } }
    if {$n eq ""} { return "ROOT" }
    set drv ""
    foreach x [$n getITerms] { if {[[$x getMTerm] getIoType] eq "OUTPUT"} { set drv [$x getInst] } }
    if {$drv eq ""} { return "ROOT" }
    set i $drv
  }
  return "?"
}
set fh [open $::env(OUT) w]
set cnt [dict create]
proc bump {k} { global cnt; dict incr cnt $k }
foreach p [all_registers -clock_pins] {
  set n [get_full_name $p]; set inm [string map {"\\" ""} [regsub {/[^/]+$} $n {}]]
  set inst [sta::sta_to_db_inst [get_cells -of_objects $p]]; if {$inst eq "NULL" || $inst eq ""} { bump noinst; continue }; set inm [$inst getName]
  set a [get_property $p arrival_max_rise]; if {$a eq ""} { bump noarr; continue }
  bump ok
  set it [$inst findITerm [regsub {^.*/} $n {}]]
  set net [$it getNet]; set drv ""
  foreach x [$net getITerms] { if {[[$x getMTerm] getIoType] eq "OUTPUT"} { set drv [$x getInst] } }
  set tap [expr {$drv eq "" ? "ROOT" : [tapof $drv]}]
  lassign [$inst getLocation] x y
  puts $fh [format "%s\t%s\t%.2f\t%.2f\t%.2f\t%s\t%s" [expr {[[$inst getMaster] isBlock] ? "M" : "F"}] $inm [expr {$x/double($dbu)}] [expr {$y/double($dbu)}] $a $tap [$net getName]]
}
close $fh
puts "CKDBG $cnt"
puts "CKDUMP done $::env(OUT)"
exit
