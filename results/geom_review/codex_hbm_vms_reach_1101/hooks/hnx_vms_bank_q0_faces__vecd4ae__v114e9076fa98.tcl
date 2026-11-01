# VMS measured existing-register affinity; explicit per-source-view opt-in.
# Source after face/guide releases, before normal DPL; adds no cells/cycles.
namespace eval ::ot_vms_affinity {
set block [ord::get_db_block];set dbu [$block getDbUnitsPerMicron]
set die [$block getDieArea]
if {[$die xMin] != 0 || [$die yMin] != 0 || abs([$die xMax]/double($dbu)-270.0)>0.001 || abs([$die yMax]/double($dbu)-403.92)>0.001} {error "VMS_AFFINITY_OUTLINE_MISMATCH"}
set anchors {
  {u_fcore.u_core.u_ot_pr_core.bank.c_v$_DFF_PN0_} 133.92 157.68
  {u_fcore.u_core.u_ot_pr_core.bank.ce_n_q\[0\]$_DFF_PN0_} 133.92 157.41
  {u_fcore.u_core.u_ot_pr_core.bank.ce_n_q\[1\]$_DFF_PN0_} 133.92 157.14
  {u_fcore.u_core.u_ot_pr_core.bank.ce_n_q\[2\]$_DFF_PN0_} 133.92 157.95
  {u_fcore.u_core.u_ot_pr_core.bank.ce_n_q\[3\]$_DFF_PN0_} 133.92 158.22
  {u_fcore.u_core.u_ot_pr_core.bank.d_dat\[224\]$_DFF_P_} 134.082 156.87
  {u_fcore.u_core.u_ot_pr_core.bank.d_dat\[227\]$_DFF_P_} 134.082 158.49
  {u_fcore.u_core.u_ot_pr_core.bank.d_dat\[233\]$_DFF_P_} 134.082 156.6
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[198\]$_DFF_P_} 134.082 158.76
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[199\]$_DFF_P_} 134.082 156.33
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[201\]$_DFF_P_} 134.082 159.03
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[202\]$_DFF_P_} 134.082 156.06
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[203\]$_DFF_P_} 136.242 157.68
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[209\]$_DFF_P_} 136.242 157.41
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[228\]$_DFF_P_} 134.082 159.3
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[229\]$_DFF_P_} 134.082 155.79
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[239\]$_DFF_P_} 136.242 157.14
  {u_fcore.u_core.u_ot_pr_core.bank.mr_v$_DFF_PN0_} 136.08 157.95
  {u_fcore.u_core.u_ot_pr_core.bank.rn$_DFF_PN0_} 133.92 159.57
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[1027\]$_DFF_PN0_} 133.92 155.52
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[455\]$_DFFE_PP_} 136.242 158.22
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[456\]$_DFFE_PP_} 136.242 156.87
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[458\]$_DFFE_PP_} 131.922 157.68
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[459\]$_DFFE_PP_} 134.082 159.84
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[460\]$_DFFE_PP_} 134.082 155.25
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[466\]$_DFFE_PP_} 131.922 157.41
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[481\]$_DFFE_PP_} 136.242 158.49
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[484\]$_DFFE_PP_} 136.242 156.6
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[485\]$_DFFE_PP_} 131.922 157.14
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[486\]$_DFFE_PP_} 131.922 157.95
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[490\]$_DFFE_PP_} 134.082 160.11
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[496\]$_DFFE_PP_} 134.082 154.98
  {u_fcore.u_core.u_ot_pr_core.bank.wq_done\[0\]$_DFF_PN0_} 136.08 158.76
  {u_fcore.u_core.u_ot_pr_core.bank.x2_d\[16\]$_SDFF_PN0_} 136.242 156.33
  {u_fcore.u_core.u_ot_pr_core.bank.x2_d\[21\]$_SDFF_PN0_} 131.922 158.22
  {u_fcore.u_core.xq2__ot_q\[275\]$_DFF_P_} 134.028 160.38
  {u_fcore.u_core.u_ot_pr_core.bank.rst_s1$_DFF_PN0_} 263.52 301.05
  {u_fcore.u_core.u_ot_pr_core.bank.rst_s2$_DFF_PN0_} 263.52 300.78
}
# Validate the entire exact-name contract before changing the database.
foreach {name x y} $anchors {
  set inst [$block findInst $name]
  if {$inst eq "NULL"} {error "VMS_AFFINITY_INSTANCE_MISSING: $name"}
  if {[[$inst getMaster] isBlock] || [$inst getPlacementStatus] in {FIRM LOCKED COVER}} {error "VMS_AFFINITY_ANCHOR_CONFLICT: $name"}
}
foreach {name x y} $anchors {
  set inst [$block findInst $name]
  $inst setLocation [expr {int(round($x*$dbu))}] [expr {int(round($y*$dbu))}]
  $inst setPlacementStatus PLACED
}
puts "OT_VMS_AFFINITY applied [expr {[llength $anchors]/3}] existing-register anchors"
}
namespace delete ::ot_vms_affinity
