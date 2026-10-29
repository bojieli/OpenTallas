# DIE-QC-36 A0 DIAGNOSTIC ONLY (diag copies): after the plan-owned TritonCTS call, print the worst FF hold / SS setup
# paths (full clock path) and clock skew so the OT_HOLD_STRUCTURAL failure can be classified. No edits.
if {![llength [info commands ::ot_diag_hold_inner]]} {
  rename ::clock_tree_synthesis ::ot_diag_hold_inner
  proc ::clock_tree_synthesis {args} {
    ::ot_diag_hold_inner {*}$args
    estimate_parasitics -placement
    puts "OT_DIAG_HOLD_BEGIN"
    catch {report_checks -path_delay min -path_group_count 1 -group_path_count 6 -format full_clock_expanded -fields {fanout} -digits 1} e; puts $e
    catch {report_checks -path_delay max -group_path_count 3 -format full_clock_expanded -digits 1} e; puts $e
    catch {report_clock_skew -digits 1} e; puts $e
    catch {report_clock_skew -hold -digits 1} e; puts $e
    puts "OT_DIAG_HOLD_END"
  }
}
