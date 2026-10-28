# PG-ACTIVITY-5 (10-27): QC dense-core below-M7 slice on a signed QC hard core (read-only 6_final odb/sdc/spef).
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
set target [expr {$ar*0.5823}]; set area 0.0; set cells {}
foreach i [$b getInsts] {
 set m [$i getMaster]; set ty [$m getType]
 if {![string match CORE* $ty] || $ty in {CORE_SPACER CORE_WELLTAP CORE_ANTENNACELL}} {continue}
 set a [expr {double([$m getWidth])*[$m getHeight]}]; lappend cells [list [$i getName] $a]; set area [expr {$area+$a}]
}
foreach z $cells {lassign $z n a; set_pdnsim_inst_power -inst $n -power [expr {$target*$a/$area}]}
puts "QCB_CANON area_mm2=$ar target_w=$target cells=[llength $cells] cell_area_um2=[expr {$area/$dbu/$dbu}]"
analyze_power_grid -net $NN -source_type FULL -voltage_file /o/A/ir_$NN.csv
puts "QCB_DONE_A $NN"
exit
