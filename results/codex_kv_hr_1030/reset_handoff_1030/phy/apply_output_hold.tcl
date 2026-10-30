# OWN ONE guarded native flow repair. Fixed typed250/202.5 references; no clock/FF changes.
read_db /work/run/results/asap7/hc_qkd_hr_phy_adp__103_68x95_04/base/4_cts.odb
read_sdc /work/run/results/asap7/hc_qkd_hr_phy_adp__103_68x95_04/base/4_cts.sdc
source /work/setRC_rcx.tcl
# ExactTTlibs/M1 are loaded by caller BEFORE this file (sameordinaryclockrecipe).
set ::env(RESULTS_DIR) /work/output_hold1
file mkdir $::env(RESULTS_DIR)
source /work/clk_freeze.tcl
source /work/pg_connect.tcl
set b [ord::get_db_block];set u [$b getDbUnitsPerMicron]
proc oh_pins {} {
 set d {};foreach bt [[ord::get_db_block] getBTerms] {
  set v [list [$bt getIoType] [$bt getSigType]]
  foreach bp [$bt getBPins] {foreach r [$bp getBoxes] {lappend v [list [[$r getTechLayer] getName] [$r xMin] [$r yMin] [$r xMax] [$r yMax]]}}
  dict set d [$bt getName] $v
 };return $d
}
proc oh_pg_wires {} {
 set d {};foreach n [[ord::get_db_block] getNets] {
  if {[$n getSigType] ni {POWER GROUND}} continue
  set v {};foreach sw [$n getSWires] {foreach r [$sw getWires] {
   if {[$r isVia]} {set ty VIA} else {set ty [[$r getTechLayer] getName]}
   lappend v [list $ty [$r xMin] [$r yMin] [$r xMax] [$r yMax]]
  }};dict set d [$n getName] [lsort $v]
 };return $d
}
set original_pins [oh_pins];set original_pg [oh_pg_wires];set old {}
foreach i [$b getInsts] {dict set old [$i getName] [list [[$i getMaster] getName] [$i getOrient] [$i getLocation]]}
write_verilog /work/output_hold1/before.v
ot_clk_freeze
set restore_status {};foreach i [$b getInsts] {dict set restore_status [$i getName] [$i getPlacementStatus]}
foreach i [$b getInsts] {$i setPlacementStatus LOCKED}
# Mechanicalinsert_buffer state only; post-DPLfullplacementRCscreen is separate, no staleRCqualification.
estimate_parasitics -placement
set pmap {};foreach p [all_outputs] {dict set pmap [get_full_name $p] $p}
set homes {};set count 0;set ports {};set seen {};set plan {};set f [open /work/output_hold_plan.tsv]
while {[gets $f line]>=0} {
 lassign [split $line "\t"] ep j x y ori base
 if {![dict exists $pmap $ep]} {error "not actualoutput $ep"}
 if {$j ni {0 1}} {error "per-portHB4budget>2"}
 set prefix ${base}__
 set key [list $ep $j]
 if {[dict exists $seen $key] || [dict exists $homes $prefix]} {error "duplicate output/j or prefix"}
 dict set seen $key 1
 set bt [$b findBTerm $ep];set net [$bt getNet]
 if {[$bt getIoType] ne "OUTPUT" || [$net getSigType] ne "SIGNAL"} {error "selected output net is not DATA SIGNAL"}
 dict set homes $prefix [list $x $y $ori]
 dict incr ports $ep
 lappend plan [list [dict get $pmap $ep] $x $y $prefix]
 incr count
}
close $f
if {$count!=488 || [dict size $ports]!=279} {error "wrongrepairplan count"}
set one 0;set two 0
dict for {ep n} $ports {
 if {![dict exists $seen [list $ep 0]]} {error "missing first buffer"}
 if {$n==1} {incr one} elseif {$n==2 && [dict exists $seen [list $ep 1]]} {incr two} else {error "wrong portchain count"}
}
if {$one!=70 || $two!=209} {error "wrong209x2+70x1 histogram"}
set hb [get_lib_cells -quiet */HB4xp67_ASAP7_75t_R]
if {![llength $hb]} {error "HB4 primitive absent"}
unset_dont_use $hb
foreach row $plan {
 lassign $row port x y prefix
 insert_buffer -buffer_cell HB4xp67_ASAP7_75t_R -load_pins [list $port] -location [list $x $y] -buffer_name $prefix
}
set_dont_use $hb
set newcount 0;set names {};set initial {}
foreach i [$b getInsts] {
 set n [$i getName]
 if {[dict exists $old $n]} continue
 if {![regexp {^(phy_outhp_[0-9]+_[01]__)} $n -> prefix] || ![dict exists $homes $prefix]} {error "unexpectednewcell $n"}
 if {[[$i getMaster] getName] ne "HB4xp67_ASAP7_75t_R"} {error "newnonHB4"}
 lassign [dict get $homes $prefix] x y ori
 $i setOrient $ori;$i setLocation [expr {round($x*$u)}] [expr {round($y*$u)}];$i setPlacementStatus PLACED
 dict set initial $n [$i getLocation];lappend names $n;incr newcount
}
if {$newcount!=488} {error "nativecreated !=488"}
write_db /work/output_hold1/pre_dpl.odb
# OnlynewDATAholdcells movable; oldclock/FF/macros/alllogic remainLOCKED.
detailed_placement -max_displacement {2 2}
# Retain intentional clock/FF freezes; release only temporary nonclock DATA locks.
foreach i [$b getInsts] {if {[dict exists $restore_status [$i getName]]} {$i setPlacementStatus [dict get $restore_status [$i getName]]}}
ot_pg_connect_all phy_output_hold1
ot_pg_require_bound phy_output_hold1
write_db /work/output_hold1/4_cts_outputhold.odb
write_def /work/output_hold1/4_cts_outputhold.def
write_verilog /work/output_hold1/after.v
write_sdc /work/output_hold1/4_cts_outputhold.sdc
check_placement -verbose
ot_clk_freeze_assert post_phy_output_hold1
foreach i [$b getInsts] {
 set n [$i getName]
 if {[dict exists $old $n] && [list [[$i getMaster] getName] [$i getOrient] [$i getLocation]] ne [dict get $old $n]} {error "oldcellidentity/home changed $n"}
}
if {[oh_pins] ne $original_pins} {error "publicpingeometry changed"}
if {[oh_pg_wires] ne $original_pg} {error "PGwires changed"}
set maxdisp 0
foreach n $names {set i [$b findInst $n];lassign [dict get $initial $n] ox oy;lassign [$i getLocation] x y;set maxdisp [expr {max($maxdisp,(abs($x-$ox)+abs($y-$oy))/double($u))}]}
puts "PHY_OUTPUT_HOLD_NATIVE_GUARD_PASS newHB4$newcount uniqueports[dict size $ports] oldcells[dict size $old] alloldhomes_clock_FF_master_pin_PGwires_EXACT maxnewpadDPL_L1_um$maxdisp"
puts PHY_OUTPUT_HOLD_APPLIED_NO_GRT_NO_TIMING_QUALIFICATION
