# VMS measured existing-register affinity; explicit per-source-view opt-in.
# Source after face/guide releases, before normal DPL; adds no cells/cycles.
namespace eval ::ot_vms_affinity {
set block [ord::get_db_block];set dbu [$block getDbUnitsPerMicron]
set die [$block getDieArea]
if {[$die xMin] != 0 || [$die yMin] != 0 || abs([$die xMax]/double($dbu)-270.0)>0.001 || abs([$die yMax]/double($dbu)-403.92)>0.001} {error "VMS_AFFINITY_OUTLINE_MISMATCH"}
set anchors {
  {u_fcore.u_core.u_ot_pr_core.bank.d_dat\[216\]$_DFF_P_} 134.082 157.68
  {u_fcore.u_core.u_ot_pr_core.bank.d_dat\[223\]$_DFF_P_} 134.082 157.41
  {u_fcore.u_core.u_ot_pr_core.bank.d_dat\[226\]$_DFF_P_} 134.082 157.14
  {u_fcore.u_core.u_ot_pr_core.bank.d_dat\[239\]$_DFF_P_} 134.082 157.95
  {u_fcore.u_core.u_ot_pr_core.bank.d_dat\[242\]$_DFF_P_} 134.082 158.22
  {u_fcore.u_core.u_ot_pr_core.bank.d_dat\[243\]$_DFF_P_} 134.082 156.87
  {u_fcore.u_core.u_ot_pr_core.bank.d_dat\[244\]$_DFF_P_} 134.082 158.49
  {u_fcore.u_core.u_ot_pr_core.bank.d_dat\[250\]$_DFF_P_} 134.082 156.6
  {u_fcore.u_core.u_ot_pr_core.bank.d_dat\[252\]$_DFF_P_} 134.082 158.76
  {u_fcore.u_core.u_ot_pr_core.bank.d_dat\[95\]$_DFF_P_} 134.082 156.33
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[202\]$_DFF_P_} 134.082 159.03
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[215\]$_DFF_P_} 134.082 156.06
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[217\]$_DFF_P_} 136.242 157.68
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[218\]$_DFF_P_} 136.242 157.41
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[219\]$_DFF_P_} 134.082 159.3
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[220\]$_DFF_P_} 134.082 155.79
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[221\]$_DFF_P_} 136.242 157.14
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[222\]$_DFF_P_} 136.242 157.95
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[225\]$_DFF_P_} 134.082 159.57
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[228\]$_DFF_P_} 134.082 155.52
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[229\]$_DFF_P_} 136.242 158.22
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[230\]$_DFF_P_} 136.242 156.87
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[231\]$_DFF_P_} 131.922 157.68
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[232\]$_DFF_P_} 134.082 159.84
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[233\]$_DFF_P_} 134.082 155.25
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[234\]$_DFF_P_} 131.922 157.41
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[235\]$_DFF_P_} 136.242 158.49
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[236\]$_DFF_P_} 136.242 156.6
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[237\]$_DFF_P_} 131.922 157.14
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[238\]$_DFF_P_} 131.922 157.95
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[240\]$_DFF_P_} 134.082 160.11
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[241\]$_DFF_P_} 134.082 154.98
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[245\]$_DFF_P_} 136.242 158.76
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[246\]$_DFF_P_} 136.242 156.33
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[247\]$_DFF_P_} 131.922 158.22
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[248\]$_DFF_P_} 134.082 160.38
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[249\]$_DFF_P_} 134.082 154.71
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[251\]$_DFF_P_} 131.922 156.87
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[253\]$_DFF_P_} 136.242 159.03
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[254\]$_DFF_P_} 136.242 156.06
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[255\]$_DFF_P_} 131.922 158.49
  {u_fcore.u_core.u_ot_pr_core.bank.rn$_DFF_PN0_} 133.92 160.65
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[1027\]$_DFF_PN0_} 133.92 154.44
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[1123\]$_DFFE_PP_} 131.922 156.6
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[459\]$_DFFE_PP_} 136.242 159.3
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[472\]$_DFFE_PP_} 136.242 155.79
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[473\]$_DFFE_PP_} 131.922 158.76
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[474\]$_DFFE_PP_} 134.082 154.17
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[475\]$_DFFE_PP_} 131.922 156.33
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[476\]$_DFFE_PP_} 134.082 160.92
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[477\]$_DFFE_PP_} 136.242 159.57
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[478\]$_DFFE_PP_} 136.242 155.52
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[479\]$_DFFE_PP_} 131.922 159.03
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[480\]$_DFFE_PP_} 134.082 161.19
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[482\]$_DFFE_PP_} 134.082 153.9
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[483\]$_DFFE_PP_} 131.922 156.06
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[485\]$_DFFE_PP_} 138.402 157.68
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[486\]$_DFFE_PP_} 136.242 159.84
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[487\]$_DFFE_PP_} 136.242 155.25
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[488\]$_DFFE_PP_} 138.402 157.41
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[489\]$_DFFE_PP_} 131.922 159.3
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[490\]$_DFFE_PP_} 134.082 161.46
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[491\]$_DFFE_PP_} 134.082 153.63
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[492\]$_DFFE_PP_} 131.922 155.79
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[493\]$_DFFE_PP_} 138.402 157.14
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[494\]$_DFFE_PP_} 138.402 157.95
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[495\]$_DFFE_PP_} 136.242 160.11
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[496\]$_DFFE_PP_} 136.242 154.98
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[497\]$_DFFE_PP_} 131.922 159.57
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[498\]$_DFFE_PP_} 134.082 161.73
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[499\]$_DFFE_PP_} 134.082 153.36
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[500\]$_DFFE_PP_} 131.922 155.52
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[501\]$_DFFE_PP_} 138.402 158.22
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[502\]$_DFFE_PP_} 136.242 160.38
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[503\]$_DFFE_PP_} 136.242 154.71
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[504\]$_DFFE_PP_} 138.402 156.87
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[505\]$_DFFE_PP_} 131.922 159.84
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[506\]$_DFFE_PP_} 134.082 162.0
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[507\]$_DFFE_PP_} 134.082 153.09
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[508\]$_DFFE_PP_} 131.922 155.25
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[509\]$_DFFE_PP_} 129.762 157.68
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[510\]$_DFFE_PP_} 129.762 157.41
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[511\]$_DFFE_PP_} 138.402 158.49
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[512\]$_DFFE_PP_} 136.242 160.65
  {u_fcore.u_core.u_ot_pr_core.bank.wq_done\[0\]$_DFF_PN0_} 136.08 154.44
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
