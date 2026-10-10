
set PLAT /OpenROAD-flow-scripts/flow/platforms/asap7
foreach l [glob $PLAT/lib/NLDM/*RVT_TT* $PLAT/lib/NLDM/*_LVT_TT_* $PLAT/lib/NLDM/*_SLVT_TT_*] {
 if {![string match *FAKE* $l]} {read_liberty $l}
}
foreach l [glob -nocomplain /src/physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/*_tt.lib] {read_liberty $l}
read_db /base/4_1_cts.odb
read_sdc /base/4_cts.sdc
source $PLAT/setRC.tcl
estimate_parasitics -placement
set_propagated_clock [all_clocks]
set fo [open /t/clock_inventory.txt w]
set blk [ord::get_db_block];set dbu [$blk getDbUnitsPerMicron]
set counted [dict create];set cells {}
foreach bt [$blk getBTerms] {
 set n [regsub {\[0\]$} [$bt getName] {}]
 if {![regexp {^ck([wens][0-9]*)?$} $n]} {continue}
 set todo [list [$bt getNet]];set seen [dict create]
 while {[llength $todo]} {
  set net [lindex $todo 0];set todo [lrange $todo 1 end]
  if {$net eq "NULL" || [dict exists $seen [$net getName]]} {continue}
  dict set seen [$net getName] 1
  foreach it [$net getITerms] {
   if {[$it isOutputSignal]} {continue}
   set inst [$it getInst];set m [$inst getMaster]
   if {[$m isSequential]} {continue}
   set nm [$inst getName]
   if {![dict exists $counted $nm]} {
    dict set counted $nm 1
    set area [expr {double([$m getWidth])*[$m getHeight]/$dbu/$dbu}]
    puts $fo "BUFFER $n $nm [$m getName] $area"
    lappend cells [get_cells -quiet $nm]
   }
   foreach o [$inst getITerms] {if {[$o isOutputSignal]} {lappend todo [$o getNet]}}
  }
 }
}
close $fo
set fo [open /t/mapped_inventory.txt w]
foreach inst [$blk getInsts] {
 set m [$inst getMaster];set mn [$m getName]
 if {![regexp {_ASAP7_75t_([A-Z]+)$} $mn -> vt]} {continue}
 puts $fo "$vt $mn [expr {double([$m getWidth])*[$m getHeight]/$dbu/$dbu}]"
}
close $fo
report_power -instances $cells -digits 6 > /t/clock_power.rpt
report_power -digits 6 > /t/component_default_activity_power.rpt
