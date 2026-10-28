# DIE-QC-12: clock arrivals at every sequential/child clock pin + every trunk/cluster-root pin (placement RC, propagated)
source /w/common.tcl
read_db $::env(ODB)
set blk [ord::get_db_block]
set gi [$blk findInst a0t_icg]
if {$gi ne "NULL"} { [$gi findITerm ENA] disconnect; [$gi findITerm SE] disconnect; puts "ICG ENA/SE left open for STA (no constant sim on the gating arcs; trial ties are logic 1/0)" }
read_sdc /p/constraint.sdc
set_propagated_clock [all_clocks]
source /p/setRC_rcx.tcl
estimate_parasitics -placement
set fh [open $::env(OUT) w]
foreach p [get_pins -hier * -filter "is_clock==1"] {
  set inst [get_cells -of_objects $p]; set m [get_property $inst ref_name]
  set n [get_full_name [get_nets -of_objects $p]]
  puts $fh "S [get_full_name $p] $m $n [get_property $p arrival_max_rise] [get_property $p arrival_max_fall] [get_property $p arrival_min_rise]"
}
foreach i [get_cells -hier {a0cl*_root a0t_*}] {
  foreach pn {A Y GCLK CLK} {
    set p [get_pins -quiet [get_full_name $i]/$pn]
    if {$p ne ""} { puts $fh "T [get_full_name $p] [get_property $p arrival_max_rise] [get_property $p arrival_max_fall] [get_property $p arrival_min_rise]" }
  }
}
close $fh
