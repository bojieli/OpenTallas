# VMS measured existing-register affinity; explicit per-source-view opt-in.
# Source after face/guide releases, before normal DPL; adds no cells/cycles.
namespace eval ::ot_vms_affinity {
set block [ord::get_db_block];set dbu [$block getDbUnitsPerMicron]
set die [$block getDieArea]
if {[$die xMin] != 0 || [$die yMin] != 0 || abs([$die xMax]/double($dbu)-270.0)>0.001 || abs([$die yMax]/double($dbu)-403.92)>0.001} {error "VMS_AFFINITY_OUTLINE_MISMATCH"}
set anchors {
  {u_fcore.u_core.u_ot_pr_core.bank.d_dat\[192\]$_DFF_P_} 134.082 157.68
  {u_fcore.u_core.u_ot_pr_core.bank.d_dat\[199\]$_DFF_P_} 134.082 157.41
  {u_fcore.u_core.u_ot_pr_core.bank.d_dat\[203\]$_DFF_P_} 134.082 157.14
  {u_fcore.u_core.u_ot_pr_core.bank.d_dat\[209\]$_DFF_P_} 134.082 157.95
  {u_fcore.u_core.u_ot_pr_core.bank.d_dat\[210\]$_DFF_P_} 134.082 158.22
  {u_fcore.u_core.u_ot_pr_core.bank.d_dat\[211\]$_DFF_P_} 134.082 156.87
  {u_fcore.u_core.u_ot_pr_core.bank.d_dat\[217\]$_DFF_P_} 134.082 158.49
  {u_fcore.u_core.u_ot_pr_core.bank.d_dat\[218\]$_DFF_P_} 134.082 156.6
  {u_fcore.u_core.u_ot_pr_core.bank.d_dat\[219\]$_DFF_P_} 134.082 158.76
  {u_fcore.u_core.u_ot_pr_core.bank.d_dat\[220\]$_DFF_P_} 134.082 156.33
  {u_fcore.u_core.u_ot_pr_core.bank.d_dat\[221\]$_DFF_P_} 134.082 159.03
  {u_fcore.u_core.u_ot_pr_core.bank.d_dat\[224\]$_DFF_P_} 134.082 156.06
  {u_fcore.u_core.u_ot_pr_core.bank.d_dat\[225\]$_DFF_P_} 136.242 157.68
  {u_fcore.u_core.u_ot_pr_core.bank.d_dat\[228\]$_DFF_P_} 136.242 157.41
  {u_fcore.u_core.u_ot_pr_core.bank.d_dat\[230\]$_DFF_P_} 134.082 159.3
  {u_fcore.u_core.u_ot_pr_core.bank.d_dat\[231\]$_DFF_P_} 134.082 155.79
  {u_fcore.u_core.u_ot_pr_core.bank.d_dat\[233\]$_DFF_P_} 136.242 157.14
  {u_fcore.u_core.u_ot_pr_core.bank.d_dat\[236\]$_DFF_P_} 136.242 157.95
  {u_fcore.u_core.u_ot_pr_core.bank.d_dat\[237\]$_DFF_P_} 134.082 159.57
  {u_fcore.u_core.u_ot_pr_core.bank.d_dat\[239\]$_DFF_P_} 134.082 155.52
  {u_fcore.u_core.u_ot_pr_core.bank.d_dat\[240\]$_DFF_P_} 136.242 158.22
  {u_fcore.u_core.u_ot_pr_core.bank.d_dat\[241\]$_DFF_P_} 136.242 156.87
  {u_fcore.u_core.u_ot_pr_core.bank.d_dat\[242\]$_DFF_P_} 131.922 157.68
  {u_fcore.u_core.u_ot_pr_core.bank.d_dat\[243\]$_DFF_P_} 134.082 159.84
  {u_fcore.u_core.u_ot_pr_core.bank.d_dat\[245\]$_DFF_P_} 134.082 155.25
  {u_fcore.u_core.u_ot_pr_core.bank.d_dat\[246\]$_DFF_P_} 131.922 157.41
  {u_fcore.u_core.u_ot_pr_core.bank.d_dat\[252\]$_DFF_P_} 136.242 158.49
  {u_fcore.u_core.u_ot_pr_core.bank.d_dat\[255\]$_DFF_P_} 136.242 156.6
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[195\]$_DFF_P_} 131.922 157.14
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[200\]$_DFF_P_} 131.922 157.95
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[204\]$_DFF_P_} 134.082 160.11
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[205\]$_DFF_P_} 134.082 154.98
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[206\]$_DFF_P_} 136.242 158.76
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[207\]$_DFF_P_} 136.242 156.33
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[212\]$_DFF_P_} 131.922 158.22
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[213\]$_DFF_P_} 134.082 160.38
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[214\]$_DFF_P_} 134.082 154.71
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[215\]$_DFF_P_} 131.922 156.87
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[216\]$_DFF_P_} 136.242 159.03
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[222\]$_DFF_P_} 136.242 156.06
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[226\]$_DFF_P_} 131.922 158.49
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[227\]$_DFF_P_} 134.082 160.65
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[229\]$_DFF_P_} 134.082 154.44
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[232\]$_DFF_P_} 131.922 156.6
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[234\]$_DFF_P_} 136.242 159.3
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[235\]$_DFF_P_} 136.242 155.79
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[238\]$_DFF_P_} 131.922 158.76
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[244\]$_DFF_P_} 134.082 154.17
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[247\]$_DFF_P_} 131.922 156.33
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[248\]$_DFF_P_} 134.082 160.92
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[249\]$_DFF_P_} 136.242 159.57
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[250\]$_DFF_P_} 136.242 155.52
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[251\]$_DFF_P_} 131.922 159.03
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[253\]$_DFF_P_} 134.082 161.19
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[254\]$_DFF_P_} 134.082 153.9
  {u_fcore.u_core.u_ot_pr_core.bank.d_p\[1\]$_DFF_P_} 131.922 156.06
  {u_fcore.u_core.u_ot_pr_core.bank.rn$_DFF_PN0_} 138.24 157.68
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[1027\]$_DFF_PN0_} 136.08 159.84
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[449\]$_DFFE_PP_} 136.242 155.25
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[452\]$_DFFE_PP_} 138.402 157.41
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[456\]$_DFFE_PP_} 131.922 159.3
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[457\]$_DFFE_PP_} 134.082 161.46
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[460\]$_DFFE_PP_} 134.082 153.63
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[461\]$_DFFE_PP_} 131.922 155.79
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[462\]$_DFFE_PP_} 138.402 157.14
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[463\]$_DFFE_PP_} 138.402 157.95
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[464\]$_DFFE_PP_} 136.242 160.11
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[466\]$_DFFE_PP_} 136.242 154.98
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[467\]$_DFFE_PP_} 131.922 159.57
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[468\]$_DFFE_PP_} 134.082 161.73
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[469\]$_DFFE_PP_} 134.082 153.36
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[470\]$_DFFE_PP_} 131.922 155.52
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[471\]$_DFFE_PP_} 138.402 158.22
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[472\]$_DFFE_PP_} 136.242 160.38
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[473\]$_DFFE_PP_} 136.242 154.71
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[474\]$_DFFE_PP_} 138.402 156.87
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[475\]$_DFFE_PP_} 131.922 159.84
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[476\]$_DFFE_PP_} 134.082 162.0
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[477\]$_DFFE_PP_} 134.082 153.09
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[478\]$_DFFE_PP_} 131.922 155.25
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[479\]$_DFFE_PP_} 129.762 157.68
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[481\]$_DFFE_PP_} 129.762 157.41
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[482\]$_DFFE_PP_} 138.402 158.49
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[483\]$_DFFE_PP_} 136.242 160.65
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[484\]$_DFFE_PP_} 136.242 154.44
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[485\]$_DFFE_PP_} 138.402 156.6
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[486\]$_DFFE_PP_} 131.922 160.11
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[487\]$_DFFE_PP_} 131.922 154.98
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[488\]$_DFFE_PP_} 129.762 157.14
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[489\]$_DFFE_PP_} 129.762 157.95
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[490\]$_DFFE_PP_} 138.402 158.76
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[491\]$_DFFE_PP_} 136.242 154.17
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[492\]$_DFFE_PP_} 138.402 156.33
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[493\]$_DFFE_PP_} 136.242 160.92
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[494\]$_DFFE_PP_} 131.922 160.38
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[495\]$_DFFE_PP_} 131.922 154.71
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[496\]$_DFFE_PP_} 129.762 158.22
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[497\]$_DFFE_PP_} 129.762 156.87
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[498\]$_DFFE_PP_} 138.402 159.03
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[499\]$_DFFE_PP_} 136.242 161.19
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[500\]$_DFFE_PP_} 136.242 153.9
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[501\]$_DFFE_PP_} 138.402 156.06
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[502\]$_DFFE_PP_} 131.922 160.65
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[503\]$_DFFE_PP_} 131.922 154.44
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[504\]$_DFFE_PP_} 129.762 158.49
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[505\]$_DFFE_PP_} 129.762 156.6
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[506\]$_DFFE_PP_} 138.402 159.3
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[507\]$_DFFE_PP_} 136.242 161.46
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[508\]$_DFFE_PP_} 136.242 153.63
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[509\]$_DFFE_PP_} 138.402 155.79
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[510\]$_DFFE_PP_} 131.922 154.17
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[511\]$_DFFE_PP_} 129.762 158.76
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[512\]$_DFFE_PP_} 131.922 160.92
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[774\]$_DFFE_PP_} 129.762 156.33
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[777\]$_DFFE_PP_} 138.402 159.57
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[779\]$_DFFE_PP_} 136.242 161.73
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[781\]$_DFFE_PP_} 136.242 153.36
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[783\]$_DFFE_PP_} 138.402 155.52
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[784\]$_DFFE_PP_} 131.922 161.19
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[787\]$_DFFE_PP_} 131.922 153.9
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[788\]$_DFFE_PP_} 129.762 159.03
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[791\]$_DFFE_PP_} 129.762 156.06
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[792\]$_DFFE_PP_} 140.562 157.68
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[793\]$_DFFE_PP_} 138.402 159.84
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[794\]$_DFFE_PP_} 136.242 162.0
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[795\]$_DFFE_PP_} 136.242 153.09
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[796\]$_DFFE_PP_} 138.402 155.25
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[797\]$_DFFE_PP_} 140.562 157.41
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[798\]$_DFFE_PP_} 131.922 161.46
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[799\]$_DFFE_PP_} 131.922 153.63
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[800\]$_DFFE_PP_} 129.762 159.3
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[801\]$_DFFE_PP_} 129.762 155.79
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[802\]$_DFFE_PP_} 140.562 157.14
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[805\]$_DFFE_PP_} 140.562 157.95
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[807\]$_DFFE_PP_} 138.402 160.11
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[809\]$_DFFE_PP_} 138.402 154.98
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[811\]$_DFFE_PP_} 131.922 161.73
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[814\]$_DFFE_PP_} 131.922 153.36
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[816\]$_DFFE_PP_} 129.762 159.57
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[817\]$_DFFE_PP_} 129.762 155.52
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[823\]$_DFFE_PP_} 140.562 158.22
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[824\]$_DFFE_PP_} 138.402 160.38
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[826\]$_DFFE_PP_} 138.402 154.71
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[827\]$_DFFE_PP_} 140.562 156.87
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[828\]$_DFFE_PP_} 131.922 162.0
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[832\]$_DFFE_PP_} 131.922 153.09
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[838\]$_DFFE_PP_} 127.602 157.68
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[840\]$_DFFE_PP_} 129.762 159.84
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[845\]$_DFFE_PP_} 129.762 155.25
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[851\]$_DFFE_PP_} 127.602 157.41
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[852\]$_DFFE_PP_} 140.562 158.49
  {u_fcore.u_core.u_ot_pr_core.bank.wq_done\[0\]$_DFF_PN0_} 138.24 160.65
  {u_fcore.u_core.wq1__ot_q\[212\]$_DFF_P_} 138.402 154.44
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
