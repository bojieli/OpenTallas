# parent_trunk_grt.tcl -- clock-net global route + per-pin clock arrivals for a parent trunk build (OPT-IN shared step,
# DIE-QC-18; upstream of the DIE-QC-15/17 lane grt.tcl).  Signal nets are flagged special so FastRoute routes only the
# clock nets (METHODOLOGY infra-first: clock pre-routed before signals; clock arrivals do not depend on signal routes).
# MODE=full  route every clock net; ODB_OUT (optional) keeps the routes (guides) in the db.
# MODE=inc   read a db routed by this script, load its routes, global_route -start_incremental, source ECO (the
#            parent_trunk_dme.py `eco` output; optional), detailed_placement (DPL=1), global_route -end_incremental:
#            only nets the ECO / legalisation touched are re-routed, every other clock route is kept bit for bit, so
#            arrivals of unchanged legs are reproduced (a corr loop then converges instead of chasing re-route noise).
#            Without ECO it re-measures the stored routes (use it for every corner of an inc step).
# env: ODB, OUT (arrivals: S <pin> <ref> <net> rise_max fall_max rise_min slew / T <trunk pin> ... / MAXSLEW_Y),
#      CORNER (TT|FF, read by the caller's LIBTCL), LIBTCL (libs + setRC loader, default /w/common.tcl),
#      SDC (/p/constraint.sdc), RCTCL (/p/setRC_rcx.tcl), PREFIX (a0t), TPAT (trunk/cluster-root cells for T lines)
proc ptenv {k d} { if {[info exists ::env($k)] && $::env($k) ne ""} { return $::env($k) } ; return $d }
set PRE [ptenv PREFIX a0t]
source [ptenv LIBTCL /w/common.tcl]
read_db $::env(ODB)
set blk [ord::get_db_block]
set gi [$blk findInst ${PRE}_icg]
if {$gi ne "NULL"} { [$gi findITerm ENA] disconnect; [$gi findITerm SE] disconnect }
read_sdc [ptenv SDC /p/constraint.sdc]
set_propagated_clock [all_clocks]
source [ptenv RCTCL /p/setRC_rcx.tcl]
set_global_routing_layer_adjustment M2-M7 0.25
set_routing_layers -signal M2-M7 -clock M4-M7
set nsig 0
foreach n [$blk getNets] { set t [$n getSigType]; if {$t ne "CLOCK" && $t ne "POWER" && $t ne "GROUND" && ![$n isSpecial]} { $n setSpecial; incr nsig } }
puts "signal nets skipped for clock GRT: $nsig"
set MODE [ptenv MODE full]
if {$MODE eq "full"} {
  global_route -allow_congestion -verbose
} elseif {$MODE eq "inc"} {
  # load the stored routes first: without this, end_incremental holds only the re-routed nets and the kept nets
  # lose their parasitics (DIE-QC-18 measured: arrivals -480 ps)
  estimate_parasitics -global_routing
  global_route -start_incremental
  if {[ptenv ECO ""] ne ""} { source $::env(ECO) }
  if {[ptenv DPL 0] eq "1"} { detailed_placement; check_placement }
  global_route -end_incremental -allow_congestion -verbose
} else { error "parent_trunk_grt: MODE $MODE (full|inc)" }
estimate_parasitics -global_routing
set fh [open $::env(OUT) w]
foreach p [get_pins -hier * -filter "is_clock==1"] {
  set inst [get_cells -of_objects $p]; set m [get_property $inst ref_name]
  set n [get_full_name [get_nets -of_objects $p]]
  puts $fh "S [get_full_name $p] $m $n [get_property $p arrival_max_rise] [get_property $p arrival_max_fall] [get_property $p arrival_min_rise] [get_property $p slew_max]"
}
foreach i [get_cells -hier [ptenv TPAT "a0cl*_root ${PRE}_*"]] {
  foreach pn {A Y GCLK CLK} {
    set p [get_pins -quiet [get_full_name $i]/$pn]
    if {$p ne ""} { puts $fh "T [get_full_name $p] [get_property $p arrival_max_rise] [get_property $p arrival_max_fall] [get_property $p arrival_min_rise] [get_property $p slew_max]" }
  }
}
set ms 0; set mp ""
foreach p [get_pins -hier */Y] { set s [get_property $p slew_max]; if {$s ne "" && $s > $ms} { set ms $s; set mp [get_full_name $p] } }
puts $fh "MAXSLEW_Y $mp $ms"
close $fh
report_check_types -max_slew -violators > $::env(OUT).slewviol
if {[ptenv ODB_OUT ""] ne ""} { write_db $::env(ODB_OUT) }
