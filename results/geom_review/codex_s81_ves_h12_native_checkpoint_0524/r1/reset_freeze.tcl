# OWN VEs case only: preserve actual reset wires/masters/poses; no clock reclassification.
set rb [ord::get_db_block]
set rf [open /work/reset_nets.txt r]
set reset_names {}; set reset_objects [dict create]
set reset_clock_nets [ot_clk_dbnets]
while {[gets $rf name] >= 0} {
 if {$name eq ""} continue
 set n [$rb findNet $name]
 if {$n eq "NULL" || [$n getSigType] in {POWER GROUND CLOCK} || $n in $reset_clock_nets} {error "VES_RESET_EXPECTED_DATA_NET $name"}
 dict set reset_objects $name $n; lappend reset_names $name
}
close $rf
if {[llength $reset_names] != 230} {error VES_RESET_INVENTORY_COUNT}
# Independent active-DB seed census refuses a source/manifest mismatch.
set reset_master [dict create]
foreach i [$rb getInsts] {
 set master [$i getMaster]; set mk [$master getName]
 if {![dict exists $reset_master $mk]} {
  set has 0; foreach mt [$master getMTerms] {if {[$mt getName] in {RESETN SETN}} {set has 1}}
  dict set reset_master $mk $has
 }
 if {![string match {u_rst.*} [$i getName]] && ![dict get $reset_master $mk]} continue
 foreach it [$i getITerms] {
  set pin [[$it getMTerm] getName]
  if {$pin in {CLK VDD VSS}} continue
  if {![string match {u_rst.*} [$i getName]] && $pin ni {RESETN SETN}} continue
  set n [$it getNet]
  if {$n eq "NULL" || ![dict exists $reset_objects [$n getName]]} {error "VES_RESET_SEED_MISSING [$i getName]/$pin"}
 }
}
set ri [dict create]; set reset_drivers [dict create]
foreach name $reset_names {
 set n [dict get $reset_objects $name]
 ot_clk_fix_wire $n
 $n setDoNotTouch 1
 if {[$n getWire] ne "NULL" && $name ni $::ot_clk_frozen_nets} {lappend ::ot_clk_frozen_nets $name}
 foreach it [$n getITerms] {
  dict set ri [[$it getInst] getName] [$it getInst]
  if {[$it isOutputSignal]} {dict set reset_drivers [[$it getInst] getName] 1}
 }
}
if {[dict size $ri] != 404} {error "VES_RESET_INCIDENT_COUNT [dict size $ri]"}
dict for {name inst} $ri {
 if {[$inst getPlacementStatus] ni {FIRM LOCKED COVER}} {$inst setPlacementStatus LOCKED}
 # FF leaf sinks retain DATA-pin repair eligibility. Clock-sink master-family
 # guards in the original PRD hook protect their reset/clock pin geometry.
 set master [[$inst getMaster] getName]
 if {![regexp {^(DFF|DLL)} $master] || [dict exists $reset_drivers $name]} {$inst setDoNotTouch 1}
}
# Normal clock dump accepts additional SIGNAL nets without treating them as clocks.
set nf [open $::env(RESULTS_DIR)/clk_freeze_nets.txt a]
foreach name $reset_names {puts $nf $name}
close $nf
ot_clk_dump $::env(RESULTS_DIR)/clk_freeze_pre.tsv pre_clock_and_reset $::env(RESULTS_DIR)/clk_freeze_nets.txt
set ::ves_reset_preserve $reset_names
puts "VES_RESET_PRESERVE nets [llength $reset_names] incident_instances [dict size $ri]; physical wire/master/pose preservation only"
