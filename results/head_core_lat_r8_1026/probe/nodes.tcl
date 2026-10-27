# HEAD-CORE-LAT-R8 read-only probe: per tree-buffer location + clock arrival (GRT basis, rc_cal 0.8,0.9). UNCHECKED.
set C $::env(OT_CORNER); set c [string tolower $C]
set L /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
foreach f [lsort [glob $L/asap7sc7p5t_*_RVT_${C}_nldm_*.lib*]] { read_liberty $f }
foreach f [glob -nocomplain /work/macros/*_${c}.lib] { read_liberty $f }
read_db $::env(ODB)
read_sdc $::env(SDC)
set ::env(OT_RC_CAL) 0.8,0.9
source /work/cf/rc_cal.tcl
estimate_parasitics -global_routing
set_propagated_clock [all_clocks]
report_worst_slack -max
set f [open $::env(OUT) w]
set blk [ord::get_db_block]
set dbu [$blk getDefUnits]
foreach inst [$blk getInsts] {
  set n [$inst getName]
  if {![string match "ot_ms_*" $n]} continue
  set loc [$inst getLocation]
  set ip ""; set op ""; set fo 0
  foreach it [$inst getITerms] { set mt [$it getMTerm]; set io [$mt getIoType]; set nm [$mt getName]
    if {$io eq "INPUT" && [$it getNet] ne "NULL" && [[$it getNet] getSigType] ne "POWER" && [[$it getNet] getSigType] ne "GROUND"} {set ip "$n/$nm"}
    if {$io eq "OUTPUT" && [$it getNet] ne "NULL"} {set op "$n/$nm"; set fo [expr [llength [[$it getNet] getITerms]] - 1]} }
  set ai nan; set ao nan; set si nan
  catch {set ai [get_property [get_pins $ip] arrival_max_rise]}
  catch {set ao [get_property [get_pins $op] arrival_max_rise]}
  catch {set si [get_property [get_pins $ip] slew_max_rise]}
  puts $f "$n\t[expr [lindex $loc 0]*1.0/$dbu]\t[expr [lindex $loc 1]*1.0/$dbu]\t[[$inst getMaster] getName]\t$ai\t$ao\t$si\t$fo"
}
close $f
puts NODES_DONE
exit
