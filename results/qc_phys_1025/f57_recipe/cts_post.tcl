# QC-PHYS f57 POST_CTS: (0) macro skew group: every macro leaf placeholder (core_taps.tcl OT_CTAP_MACRO_TAPOUT=1) is
# re-hung on its region tap OUTPUT net -> the macro clock shares the trunk + tap of its interface registers and sits
# one leaf stage after the tap (designed early vs the tap tree depth); (1) F5 tap balance + macro latency match
# (OT_CTAP_MACRO_EARLY) on placement RC; (2) F4 zero-logic leaf affinity (main tools/die_plan/leaf_affinity.tcl);
# then the CTS stop gate.  All global scope (ORFS sources this inside a proc).
uplevel #0 {
if {[info exists ::ot_fc_dt]} { puts "OT_FCAP: dont_touch left lifted on [llength $::ot_fc_dt] flops (hold repair)" }
set ctc_blk [ord::get_db_block]
foreach ctc_n [$ctc_blk getNets] {
  if {![regexp {^ot_cleaf_(.*)_ph$} [$ctc_n getName] -> ctc_m]} continue
  set ctc_leaf [$ctc_blk findInst "ot_cleaf_$ctc_m"]
  if {$ctc_leaf eq "NULL"} { error "OT_CTAP_TAPOUT no leaf for $ctc_m" }
  if {[info exists ::ct_leaf_region_by_leaf] && [dict exists $::ct_leaf_region_by_leaf "ot_cleaf_$ctc_m"]} {
    set ctc_r [dict get $::ct_leaf_region_by_leaf "ot_cleaf_$ctc_m"]
  } else {
    # separate process: nearest region tap buffer to the leaf
    lassign [$ctc_leaf getLocation] ctc_x ctc_y; set ctc_best 1e18; set ctc_r ""
    foreach ctc_i [$ctc_blk getInsts] {
      if {![regexp {^ot_ctap_([A-Z0-9]+)$} [$ctc_i getName] -> ctc_rr]} continue
      lassign [$ctc_i getLocation] ctc_ix ctc_iy; set ctc_d [expr {abs($ctc_ix-$ctc_x)+abs($ctc_iy-$ctc_y)}]
      if {$ctc_d < $ctc_best} { set ctc_best $ctc_d; set ctc_r $ctc_rr }
    }
  }
  set ctc_tn [$ctc_blk findNet "ot_ctap_${ctc_r}_n"]
  if {$ctc_tn eq "NULL"} { error "OT_CTAP_TAPOUT tap net ot_ctap_${ctc_r}_n missing" }
  foreach ctc_it [$ctc_n getITerms] { $ctc_it disconnect; $ctc_it connect $ctc_tn }
  odb::dbNet_destroy $ctc_n
  puts "OT_CTAP_TAPOUT leaf ot_cleaf_$ctc_m -> ot_ctap_${ctc_r}_n (tap fanout [llength [$ctc_tn getITerms]])"
}
}
estimate_parasitics -placement
source /work/core_taps_post.tcl
uplevel #0 [list source /work/leaf_affinity.tcl]
detailed_placement
check_placement -verbose
estimate_parasitics -placement
report_clock_skew -setup
report_clock_skew -hold
source /work/cts_gate.tcl
