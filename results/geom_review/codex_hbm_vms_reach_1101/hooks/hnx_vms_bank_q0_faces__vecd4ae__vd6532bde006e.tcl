# VMS measured existing-register affinity; explicit per-source-view opt-in.
# Source after face/guide releases, before normal DPL; adds no cells/cycles.
namespace eval ::ot_vms_affinity {
set block [ord::get_db_block];set dbu [$block getDbUnitsPerMicron]
set die [$block getDieArea]
if {[$die xMin] != 0 || [$die yMin] != 0 || abs([$die xMax]/double($dbu)-270.0)>0.001 || abs([$die yMax]/double($dbu)-403.92)>0.001} {error "VMS_AFFINITY_OUTLINE_MISMATCH"}
set anchors {
  {u_fcore.u_core.u_ot_pr_core.bank.c_a\[244\]$_DFF_P_} 134.055 157.68
  {u_fcore.u_core.u_ot_pr_core.bank.ce_n_q\[0\]$_DFF_PN0_} 133.92 157.41
  {u_fcore.u_core.u_ot_pr_core.bank.ce_n_q\[1\]$_DFF_PN0_} 133.92 157.14
  {u_fcore.u_core.u_ot_pr_core.bank.ce_n_q\[2\]$_DFF_PN0_} 133.92 157.95
  {u_fcore.u_core.u_ot_pr_core.bank.ce_n_q\[3\]$_DFF_PN0_} 133.92 158.22
  {u_fcore.u_core.u_ot_pr_core.bank.d_dat\[222\]$_DFF_P_} 134.082 156.87
  {u_fcore.u_core.u_ot_pr_core.bank.d_dat\[228\]$_DFF_P_} 134.082 158.49
  {u_fcore.u_core.u_ot_pr_core.bank.d_dat\[233\]$_DFF_P_} 134.082 156.6
  {u_fcore.u_core.u_ot_pr_core.bank.d_dat\[236\]$_DFF_P_} 134.082 158.76
  {u_fcore.u_core.u_ot_pr_core.bank.d_dat\[242\]$_DFF_P_} 134.082 156.33
  {u_fcore.u_core.u_ot_pr_core.bank.d_dat\[244\]$_DFF_P_} 134.082 159.03
  {u_fcore.u_core.u_ot_pr_core.bank.d_dat\[245\]$_DFF_P_} 134.082 156.06
  {u_fcore.u_core.u_ot_pr_core.bank.d_dat\[255\]$_DFF_P_} 136.242 157.68
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[102\]$_DFF_P_} 136.242 157.41
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[110\]$_DFF_P_} 134.082 159.3
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[111\]$_DFF_P_} 134.082 155.79
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[112\]$_DFF_P_} 136.242 157.14
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[183\]$_DFF_P_} 136.242 157.95
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[185\]$_DFF_P_} 134.082 159.57
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[188\]$_DFF_P_} 134.082 155.52
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[224\]$_DFF_P_} 136.242 158.22
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[225\]$_DFF_P_} 136.242 156.87
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[226\]$_DFF_P_} 131.922 157.68
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[227\]$_DFF_P_} 134.082 159.84
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[228\]$_DFF_P_} 134.082 155.25
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[229\]$_DFF_P_} 131.922 157.41
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[233\]$_DFF_P_} 136.242 158.49
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[234\]$_DFF_P_} 136.242 156.6
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[235\]$_DFF_P_} 131.922 157.14
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[236\]$_DFF_P_} 131.922 157.95
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[238\]$_DFF_P_} 134.082 160.11
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[239\]$_DFF_P_} 134.082 154.98
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[241\]$_DFF_P_} 136.242 158.76
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[243\]$_DFF_P_} 136.242 156.33
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[244\]$_DFF_P_} 131.922 158.22
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[245\]$_DFF_P_} 134.082 160.38
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[246\]$_DFF_P_} 134.082 154.71
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[247\]$_DFF_P_} 131.922 156.87
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[248\]$_DFF_P_} 136.242 159.03
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[249\]$_DFF_P_} 136.242 156.06
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[250\]$_DFF_P_} 131.922 158.49
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[251\]$_DFF_P_} 134.082 160.65
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[252\]$_DFF_P_} 134.082 154.44
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[253\]$_DFF_P_} 131.922 156.6
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[254\]$_DFF_P_} 136.242 159.3
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[255\]$_DFF_P_} 136.242 155.79
  {u_fcore.u_core.u_ot_pr_core.bank.d_syn\[50\]$_DFF_P_} 131.922 158.76
  {u_fcore.u_core.u_ot_pr_core.bank.d_syn\[52\]$_DFF_P_} 134.082 154.17
  {u_fcore.u_core.u_ot_pr_core.bank.d_syn\[54\]$_DFF_P_} 131.922 156.33
  {u_fcore.u_core.u_ot_pr_core.bank.pr_d\[222\]$_SDFF_PN0_} 134.082 160.92
  {u_fcore.u_core.u_ot_pr_core.bank.pr_d\[236\]$_SDFF_PN0_} 136.242 159.57
  {u_fcore.u_core.u_ot_pr_core.bank.pr_d\[245\]$_SDFF_PN0_} 136.242 155.52
  {u_fcore.u_core.u_ot_pr_core.bank.pr_d\[255\]$_SDFF_PN0_} 131.922 159.03
  {u_fcore.u_core.u_ot_pr_core.bank.rn$_DFF_PN0_} 133.92 161.19
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[1027\]$_DFF_PN0_} 133.92 153.9
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[1130\]$_DFFE_PP_} 131.922 156.06
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[1138\]$_DFFE_PP_} 138.402 157.68
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[1139\]$_DFFE_PP_} 136.242 159.84
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[1140\]$_DFFE_PP_} 136.242 155.25
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[1211\]$_DFFE_PP_} 138.402 157.41
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[1213\]$_DFFE_PP_} 131.922 159.3
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[1216\]$_DFFE_PP_} 134.082 161.46
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[1264\]$_DFFE_PP_} 134.082 153.63
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[1273\]$_DFFE_PP_} 131.922 155.79
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[1283\]$_DFFE_PP_} 138.402 157.14
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[225\]$_DFFE_PP_} 138.402 157.95
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[226\]$_DFFE_PP_} 136.242 160.11
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[227\]$_DFFE_PP_} 136.242 154.98
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[228\]$_DFFE_PP_} 131.922 159.57
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[233\]$_DFFE_PP_} 134.082 161.73
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[234\]$_DFFE_PP_} 134.082 153.36
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[235\]$_DFFE_PP_} 131.922 155.52
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[236\]$_DFFE_PP_} 138.402 158.22
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[242\]$_DFFE_PP_} 136.242 160.38
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[245\]$_DFFE_PP_} 136.242 154.71
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[247\]$_DFFE_PP_} 138.402 156.87
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[249\]$_DFFE_PP_} 131.922 159.84
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[250\]$_DFFE_PP_} 134.082 162.0
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[251\]$_DFFE_PP_} 134.082 153.09
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[252\]$_DFFE_PP_} 131.922 155.25
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[253\]$_DFFE_PP_} 129.762 157.68
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[254\]$_DFFE_PP_} 129.762 157.41
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[255\]$_DFFE_PP_} 138.402 158.49
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[750\]$_DFFE_PP_} 136.242 160.65
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
