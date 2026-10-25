# S81-CORES/SPLIT probe: per-register clock arrival + clock tree geometry at one stage.
# env: ODB, STAGE (cts|grt|rcx), SPEF (rcx), CORNER (TT|FF), OUT (dir), KIT (/work)
set C $::env(CORNER); set c [string tolower $C]
set L /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
read_db $::env(ODB)
foreach f [lsort [glob $L/asap7sc7p5t_*_RVT_${C}_nldm_*.lib*]] { read_liberty $f }
foreach f [lsort [glob -nocomplain $L/asap7sc7p5t_*_LVT_${C}_nldm_*.lib*]] { read_liberty $f }
foreach f [lsort [glob -nocomplain $L/asap7sc7p5t_*_SLVT_${C}_nldm_*.lib*]] { read_liberty $f }
foreach f [glob -nocomplain /work/macros/*_${c}.lib] { read_liberty $f }
read_sdc /work/constraint.sdc
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
set st $::env(STAGE)
if {$st eq "rcx"} { read_spef $::env(SPEF) } elseif {$st eq "grt"} {
  if {[catch {estimate_parasitics -global_routing} e]} { puts "OT_PROBE grt-est failed ($e): re-running global_route";
    set_routing_layers -signal M2-M5 -clock M2-M5; global_route -congestion_iterations 30 -allow_congestion; estimate_parasitics -global_routing }
} else { estimate_parasitics -placement }
set_propagated_clock [get_clocks clk]
set per [get_property [get_clocks clk] period]
set blk [ord::get_db_block]; set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set fh [open $::env(OUT)/ck_${st}_${c}.tsv w]
foreach p [all_registers -clock_pins] {
  if {[catch {set a [get_property $p arrival_max_rise]}] || $a eq ""} continue
  set i [sta::sta_to_db_inst [$p instance]]
  if {$i eq "NULL" || $i eq ""} continue
  set b [$i getBBox]
  puts $fh "[get_full_name $p]\t[format %.2f [expr {([$b xMin]+[$b xMax])/2.0/$dbu}]]\t[format %.2f [expr {([$b yMin]+[$b yMax])/2.0/$dbu}]]\t[format %.2f $a]\t[[$i getMaster] getName]"
}
close $fh
if {$st eq "rcx" || $st eq "cts"} {
  set fh [open $::env(OUT)/cknets_${st}.tsv w]
  foreach n [$blk getNets] {
    if {[$n getSigType] ne "CLOCK"} continue
    set drv ""; set sinks {}
    foreach it [$n getITerms] { set i [$it getInst]; set b [$i getBBox]
      set xy "[format %.1f [expr {([$b xMin]+[$b xMax])/2.0/$dbu}]],[format %.1f [expr {([$b yMin]+[$b yMax])/2.0/$dbu}]]"
      if {[[$it getMTerm] getIoType] eq "OUTPUT"} { set drv "[$i getName]@[[$i getMaster] getName]@$xy" } else { lappend sinks $xy } }
    foreach bt [$n getBTerms] { set bb [$bt getBBox]; set drv "PORT@[$bt getName]@[format %.1f [expr {([$bb xMin]+[$bb xMax])/2.0/$dbu}]],[format %.1f [expr {([$bb yMin]+[$bb yMax])/2.0/$dbu}]]" }
    puts $fh "[$n getName]\t$drv\t[join $sinks { }]"
  }
  close $fh
  set fh [open $::env(OUT)/insts_${st}.tsv w]
  foreach i [$blk getInsts] { set m [$i getMaster]; set mn [$m getName]
    if {[string match TAPCELL* $mn] || [string match FILL* $mn] || [string match DECAP* $mn]} continue
    set b [$i getBBox]
    puts $fh "[$i getName]\t$mn\t[format %.2f [expr {[$b xMin]/double($dbu)}]]\t[format %.2f [expr {[$b yMin]/double($dbu)}]]\t[format %.2f [expr {[$b xMax]/double($dbu)}]]\t[format %.2f [expr {[$b yMax]/double($dbu)}]]" }
  close $fh
  set fh [open $::env(OUT)/paths_${st}_${c}.txt w]
  puts $fh [report_checks -path_delay min -group_path_count 30 -endpoint_path_count 1 -format end -digits 2]
  close $fh
  report_checks -path_delay min -group_path_count 6 -format full_clock_expanded -fields {slew cap} > $::env(OUT)/minpaths_${st}_${c}.rpt
  report_checks -path_delay max -group_path_count 6 -format full_clock_expanded -fields {slew cap} > $::env(OUT)/maxpaths_${st}_${c}.rpt
}
puts "OT_PROBE_DONE $st $C"
