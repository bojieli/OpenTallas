read_db /gate/routes/gate/work/orfs/results/asap7/opentallas_ot_pdie_serdes_col_lp_asap7_ref_gate/base/2_3_floorplan_tapcell.odb
set b [ord::get_db_block]
puts "AUDIT_SCOPE pre_PDN_stage_only_not_final"
foreach i [$b getInsts] {
 set m [$i getMaster]
 if {![$m isBlock]} {continue}
 puts "HARD [$i getName] [$m getName]"
 foreach t [$i getITerms] {
  set mt [$t getMTerm]
  set st [$mt getSigType]
  if {$st ne "POWER" && $st ne "GROUND"} {continue}
  set nn NONE
  set n [$t getNet]
  if {$n ne "NULL"} {set nn [$n getName]}
  set nr 0
  set ls {}
  foreach mp [$mt getMPins] {
   foreach box [$mp getGeometry] {
    incr nr
    set l [$box getTechLayer]
    lappend ls [$l getName]
   }
  }
  puts "SUPPLY [$i getName]/[$mt getName] type=$st net=$nn rectangles=$nr layers=[lsort -unique $ls]"
 }
}
puts AUDIT_DONE
