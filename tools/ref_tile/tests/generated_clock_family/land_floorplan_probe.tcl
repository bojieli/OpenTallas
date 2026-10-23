set corner $::env(PROBE_CORNER)
foreach l [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT_${corner}*] {read_liberty $l}
read_db /base/2_floorplan.odb
read_sdc /base/2_floorplan.sdc
# DIAGNOSTIC PHASE ONLY: topology fixture, not a qualified LAND scenario.
foreach side {w r} root {ot_entry_1 ot_entry_0} port {ck_s ck} {
 for {set b 0} {$b < 4} {incr b} {
  set target [format {u_land.u_gated.u_%sbank%d/u_cg.u_icg/GCLK} $side $b]
  create_generated_clock -name qfd_${side}bank$b -source [get_ports $port] -master_clock $root -edges {1 2 9} [get_pins $target]
 }
}
set_propagated_clock [all_clocks]
source /probe/clock_family.tcl
ot_cf_refresh
foreach root {ot_entry_0 ot_entry_1} {
 lassign [ot_cf_pins [get_clocks $root]] pins owners
 set counts {}; set sampled {}
 foreach p $pins {set cn [get_full_name [dict get $owners [get_full_name $p]]]; dict incr counts $cn; if {![dict exists $sampled $cn]} {puts "SAMPLE $root [get_full_name $p] $cn [ot_cf_wire $p [dict get $owners [get_full_name $p]]]";dict set sampled $cn 1}}
 puts "LAND_FAMILY $root [llength $pins] $counts"
}
exit
