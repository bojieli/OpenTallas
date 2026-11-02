read_db /input/run/results/asap7/kq_qfd_qc_su_lane_w_l7_we89441/base/5_1_grt.odb
set cn 0
set sn 0
foreach n [[ord::get_db_block] getNets] {
 set ty [$n getSigType]
 set degree [expr {[llength [$n getITerms]]+[llength [$n getBTerms]]}]
 if {$ty in {CLOCK SIGNAL} && $degree > 1} {
  if {[$n isSpecial] || [llength [$n getSWires]] || [llength [$n getGuides]] == 0} { error "ACTUAL_FINAL_DB_MISSING_GUIDES [$n getName]" }
  if {$ty eq "CLOCK"} {incr cn} else {incr sn}
 }
}
puts "FINAL_DB_NATIVE_GUIDES CLOCK=$cn SIGNAL=$sn"
write_guides /out/final_native.guide
puts "FINAL_DB_WRITE_GUIDES_DONE"
