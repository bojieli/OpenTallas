read_db /work/baseline.odb
set b [ord::get_db_block]
set dbu [$b getDbUnitsPerMicron]
set before [llength [$b getInsts]]
remove_fillers
set after [llength [$b getInsts]]
puts "ENTRY_CONTEXT_FILLERS removed=[expr {$before-$after}]"
foreach i [$b getInsts] {$i setPlacementStatus FIRM}
set fm NULL;set im NULL
foreach lib [[ord::get_db] getLibs] {
 if {$fm eq "NULL"} {set fm [$lib findMaster DFFLQNx1_ASAP7_75t_R]}
 if {$im eq "NULL"} {set im [$lib findMaster INVx1_ASAP7_75t_R]}
}
if {$fm eq "NULL" || $im eq "NULL"} {error "ENTRY_CONTEXT missing native fall FF/inverter"}
set changed {}
set out [open /work/new_cells.tsv w]
foreach {tag oldname} {reset {u_rst_in/q$_DFF_P_} start {u_run_in/q$_DFF_P_}} {
 set old [$b findInst $oldname]
 if {$old eq "NULL"} {error "ENTRY_CONTEXT missing old $oldname"}
 if {[[$old getMaster] getName] ne "DFFHQNx1_ASAP7_75t_R"} {error "ENTRY_CONTEXT unexpected old FF"}
 set d [$old findITerm D];set dn [$d getNet];set ck [[$old findITerm CLK] getNet]
 set fn ot_entry_${tag}_fall
 set ivn ot_entry_${tag}_inv
 set ff [odb::dbInst_create $b $fm $fn]
 set iv [odb::dbInst_create $b $im $ivn]
 set nq [odb::dbNet_create $b ${fn}_qn]
 set qp [odb::dbNet_create $b ${fn}_q]
 foreach n [list $nq $qp] {$n setSigType SIGNAL}
 [$ff findITerm D] connect $dn
 [$ff findITerm CLK] connect $ck
 [$ff findITerm QN] connect $nq
 [$iv findITerm A] connect $nq
 [$iv findITerm Y] connect $qp
 $d disconnect;$d connect $qp
 foreach n [list $dn $ck] {
  if {[$n getWire] ne "NULL"} {odb::dbWire_destroy [$n getWire]}
  dict set changed [$n getName] 1
 }
 foreach n [list $nq $qp] {dict set changed [$n getName] 1}
 lassign [$old getLocation] x y
 $ff setOrient [$old getOrient];$iv setOrient [$old getOrient]
 $ff setLocation [expr {$x+round(.216*$dbu)}] [expr {$y+round(.27*$dbu)}]
 $iv setLocation [expr {$x+round(1.35*$dbu)}] [expr {$y+round(.27*$dbu)}]
 $ff setPlacementStatus PLACED;$iv setPlacementStatus PLACED
 puts "ENTRY_CONTEXT $tag old=$oldname d=[$dn getName] clock=[$ck getName]"
}
global_connect
detailed_placement -incremental
check_placement -verbose
foreach name {ot_entry_reset_fall ot_entry_reset_inv ot_entry_start_fall ot_entry_start_inv} {
 set i [$b findInst $name];set box [$i getBBox]
 puts $out "$name\t[[$i getMaster] getName]\t[expr {[$box xMin]/double($dbu)}]\t[expr {[$box yMin]/double($dbu)}]\t[expr {[$box xMax]/double($dbu)}]\t[expr {[$box yMax]/double($dbu)}]"
}
close $out
set f [open /work/changed_nets.txt w];foreach n [dict keys $changed] {puts $f $n};close $f
write_db /work/entry_placed.odb
write_def /work/entry_placed.def
write_verilog -remove_cells {FILLER* DECAP* TAPCELL*} /work/entry_placed.v
# Local rectangles for review of the actual added cells and their neighbours.
set f [open /work/local_rects.tsv w]
foreach i [$b getInsts] {
 set q [$i getBBox];set include 0
 foreach ref {ot_entry_reset_fall ot_entry_start_fall} {
  set r [[$b findInst $ref] getBBox]
  set pad [expr {round(10*$dbu)}]
  if {[$q xMin]<=[$r xMax]+$pad && [$q xMax]>=[$r xMin]-$pad && [$q yMin]<=[$r yMax]+$pad && [$q yMax]>=[$r yMin]-$pad} {set include 1;break}
 }
 if {$include} {puts $f "[$i getName]\t[[$i getMaster] getName]\t[expr {[$q xMin]/double($dbu)}]\t[expr {[$q yMin]/double($dbu)}]\t[expr {[$q xMax]/double($dbu)}]\t[expr {[$q yMax]/double($dbu)}]"}
}
close $f
puts ENTRY_CONTEXT_PLACED
