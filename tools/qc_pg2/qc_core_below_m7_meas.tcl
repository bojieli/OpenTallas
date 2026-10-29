# QC-PG-2 (10-27): = PG-ACTIVITY-5 qc_core_below_m7.tcl with MEASURED activity, B solve only. QC dense-core below-M7 slice on a signed QC hard core (read-only 6_final odb/sdc/spef).
# Method = PG-ACTIVITY-4 kv_below_m7_m7src.tcl: signed core PDN kept, QC partition straps ADDED (same widths/pitches
# as the QC coll_ftm signed partition PDN: M6 0.288@4.32, M7 0.288@8.64), PG pins moved to M7 => -source_type FULL
# makes every M7 node ideal (split point of the above-M7 canonical deck). Two solves per net in one session:
#  B = PSM internal STA power only (vectorless OpenSTA; own power of the core)
#  A = B + explicit canonical 0.5823 W/mm2 x core area, normalized by functional cell area (Codex coll_ftm load form)
# exact canonical-only = A - B per terminal (set_pdnsim_inst_power is ADDITIVE, PG-ACTIVITY-4).
foreach f [lsort [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_*_RVT_TT_nldm_*.lib*]] { read_liberty $f }
read_db /k/6_final.odb
read_sdc /k/6_final.sdc
if {[file exists /k/6_final.spef]} { read_spef /k/6_final.spef }
set_propagated_clock [all_clocks]
set b [ord::get_db_block]
set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set bb [$b getDieArea]
set ar [expr {double([$bb xMax]-[$bb xMin])*([$bb yMax]-[$bb yMin])/$dbu/$dbu/1.e6}]
# QC-PG-2: measured RTL activity (tools/pg_activity/core_power_meas.tcl annotation, /o/act.txt, unmatched regs = matched mean)
set fh [open /o/act.txt r]
while {[gets $fh ln] >= 0} { set A([lindex $ln 0]) [lindex $ln 1] }
close $fh
set nm 0; set nu 0; set sum 0.0; set regs [all_registers]
foreach r $regs {
  set n [get_full_name $r]; regsub {\$_.*$} $n {} k; regsub -all {/} $k {.} k; regsub -all {\\} $k {} k
  regsub {_reg(\[[0-9]+\])?$} $k {\1} k2
  set cands [list $k $k2]; set segs [split $k .]
  for {set j 1} {$j < [llength $segs] - 1} {incr j} { lappend cands [join [lrange $segs $j end] .] }
  foreach kk $cands { if {[info exists A($kk)]} { set R($n) $A($kk); incr nm; set sum [expr {$sum + $A($kk)}]; break } }
}
set def [expr {$nm ? $sum / $nm : 0.5}]
foreach r $regs { set n [get_full_name $r]; if {[info exists R($n)]} { set a $R($n) } else { set a $def; incr nu }
  foreach p [get_pins -quiet -of_objects $r -filter "direction == output"] { set_power_activity -pins $p -activity $a -duty 0.5 } }
set ni 0; set niu 0
foreach p [all_inputs -no_clocks] { set n [get_full_name $p]; if {[info exists A($n)]} { set a $A($n); incr ni } else { set a $def; incr niu }
  set_power_activity -input_ports $p -activity $a -duty 0.5 }
puts "OT_REG_MATCHED $nm OT_REG_DEFAULT $nu OT_REG_TOTAL [llength $regs] OT_REG_MATCHED_MEAN $def OT_IN_MATCHED $ni OT_IN_DEFAULT $niu"
report_power -digits 6
set_voltage_domain -name {CORE} -power {VDD} -ground {VSS}
define_pdn_grid -name {part} -voltage_domains {CORE}
add_pdn_stripe -grid {part} -layer {M6} -width $::env(QCB_W6) -spacing {0.096} -pitch $::env(QCB_P6) -offset {1.968}
add_pdn_stripe -grid {part} -layer {M7} -width $::env(QCB_W7) -spacing {0.096} -pitch $::env(QCB_P7) -offset {4.128}
add_pdn_connect -grid {part} -layers {M5 M6}
add_pdn_connect -grid {part} -layers {M6 M7}
pdngen
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
set tech [ord::get_db_tech]; set m7 [$tech findLayer M7]
foreach nn {VDD VSS} {
  set n [$b findNet $nn]; set bt [$n get1stBTerm]; if {$bt eq "NULL"} { set bt [odb::dbBTerm_create $n $nn] }
  foreach bp [$bt getBPins] { odb::dbBPin_destroy $bp }
  set k 0
  foreach sw [$n getSWires] { foreach w [$sw getWires] { if {![$w isVia] && [$w getTechLayer] eq $m7} {
    set bp [odb::dbBPin_create $bt]; odb::dbBox_create $bp $m7 [$w xMin] [$w yMin] [$w xMax] [$w yMax]; $bp setPlacementStatus FIRM; incr k } } }
  puts "QCB_M7_PINS $nn $k"
}
set NN $::env(QCB_NET)
if {[catch {check_power_grid -net $NN} e]} { puts "QCB_PG_CHECK_FAIL $NN $e" } else { puts "QCB_PG_CHECK_OK $NN" }
analyze_power_grid -net $NN -source_type FULL -voltage_file /o/B/ir_$NN.csv
puts "QCB_DONE_B $NN"
exit
