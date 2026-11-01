# VMS measured existing-register affinity; explicit per-source-view opt-in.
# Source after face/guide releases, before normal DPL; adds no cells/cycles.
namespace eval ::ot_vms_affinity {
set block [ord::get_db_block];set dbu [$block getDbUnitsPerMicron]
set die [$block getDieArea]
if {[$die xMin] != 0 || [$die yMin] != 0 || abs([$die xMax]/double($dbu)-270.0)>0.001 || abs([$die yMax]/double($dbu)-403.92)>0.001} {error "VMS_AFFINITY_OUTLINE_MISMATCH"}
set anchors {
  {u_fcore.u_core.dq__ot_q\[208\]$_DFF_P_} 134.082 157.68
  {u_fcore.u_core.dq__ot_q\[212\]$_DFF_P_} 134.082 157.41
  {u_fcore.u_core.dq__ot_q\[213\]$_DFF_P_} 134.082 157.14
  {u_fcore.u_core.dq__ot_q\[216\]$_DFF_P_} 134.082 157.95
  {u_fcore.u_core.dq__ot_q\[217\]$_DFF_P_} 134.082 158.22
  {u_fcore.u_core.dq__ot_q\[218\]$_DFF_P_} 134.082 156.87
  {u_fcore.u_core.dq__ot_q\[219\]$_DFF_P_} 134.082 158.49
  {u_fcore.u_core.dq__ot_q\[220\]$_DFF_P_} 134.082 156.6
  {u_fcore.u_core.dq__ot_q\[222\]$_DFF_P_} 134.082 158.76
  {u_fcore.u_core.dq__ot_q\[223\]$_DFF_P_} 134.082 156.33
  {u_fcore.u_core.dq__ot_q\[227\]$_DFF_P_} 134.082 159.03
  {u_fcore.u_core.dq__ot_q\[229\]$_DFF_P_} 134.082 156.06
  {u_fcore.u_core.dq__ot_q\[230\]$_DFF_P_} 136.242 157.68
  {u_fcore.u_core.dq__ot_q\[231\]$_DFF_P_} 136.242 157.41
  {u_fcore.u_core.dq__ot_q\[232\]$_DFF_P_} 134.082 159.3
  {u_fcore.u_core.dq__ot_q\[234\]$_DFF_P_} 134.082 155.79
  {u_fcore.u_core.dq__ot_q\[236\]$_DFF_P_} 136.242 157.14
  {u_fcore.u_core.dq__ot_q\[237\]$_DFF_P_} 136.242 157.95
  {u_fcore.u_core.dq__ot_q\[238\]$_DFF_P_} 134.082 159.57
  {u_fcore.u_core.dq__ot_q\[239\]$_DFF_P_} 134.082 155.52
  {u_fcore.u_core.dq__ot_q\[241\]$_DFF_P_} 136.242 158.22
  {u_fcore.u_core.dq__ot_q\[242\]$_DFF_P_} 136.242 156.87
  {u_fcore.u_core.dq__ot_q\[243\]$_DFF_P_} 131.922 157.68
  {u_fcore.u_core.dq__ot_q\[244\]$_DFF_P_} 134.082 159.84
  {u_fcore.u_core.dq__ot_q\[245\]$_DFF_P_} 134.082 155.25
  {u_fcore.u_core.dq__ot_q\[246\]$_DFF_P_} 131.922 157.41
  {u_fcore.u_core.dq__ot_q\[247\]$_DFF_P_} 136.242 158.49
  {u_fcore.u_core.dq__ot_q\[248\]$_DFF_P_} 136.242 156.6
  {u_fcore.u_core.dq__ot_q\[249\]$_DFF_P_} 131.922 157.14
  {u_fcore.u_core.dq__ot_q\[250\]$_DFF_P_} 131.922 157.95
  {u_fcore.u_core.dq__ot_q\[251\]$_DFF_P_} 134.082 160.11
  {u_fcore.u_core.dq__ot_q\[252\]$_DFF_P_} 134.082 154.98
  {u_fcore.u_core.dq__ot_q\[253\]$_DFF_P_} 136.242 158.76
  {u_fcore.u_core.dq__ot_q\[254\]$_DFF_P_} 136.242 156.33
  {u_fcore.u_core.dq__ot_q\[255\]$_DFF_P_} 131.922 158.22
  {u_fcore.u_core.dq__ot_q\[256\]$_DFF_P_} 134.082 160.38
  {u_fcore.u_core.dq__ot_q\[257\]$_DFF_P_} 134.082 154.71
  {u_fcore.u_core.dq__ot_q\[258\]$_DFF_P_} 131.922 156.87
  {u_fcore.u_core.dq__ot_q\[259\]$_DFF_P_} 136.242 159.03
  {u_fcore.u_core.dq__ot_q\[260\]$_DFF_P_} 136.242 156.06
  {u_fcore.u_core.dq__ot_q\[261\]$_DFF_P_} 131.922 158.49
  {u_fcore.u_core.dq__ot_q\[262\]$_DFF_P_} 134.082 160.65
  {u_fcore.u_core.dq__ot_q\[263\]$_DFF_P_} 134.082 154.44
  {u_fcore.u_core.u_ot_pr_core.bank.d_dat\[205\]$_DFF_P_} 131.922 156.6
  {u_fcore.u_core.u_ot_pr_core.bank.d_dat\[227\]$_DFF_P_} 136.242 159.3
  {u_fcore.u_core.u_ot_pr_core.bank.d_dat\[228\]$_DFF_P_} 136.242 155.79
  {u_fcore.u_core.u_ot_pr_core.bank.d_dat\[229\]$_DFF_P_} 131.922 158.76
  {u_fcore.u_core.u_ot_pr_core.bank.d_dat\[230\]$_DFF_P_} 134.082 154.17
  {u_fcore.u_core.u_ot_pr_core.bank.d_dat\[232\]$_DFF_P_} 131.922 156.33
  {u_fcore.u_core.u_ot_pr_core.bank.d_dat\[233\]$_DFF_P_} 134.082 160.92
  {u_fcore.u_core.u_ot_pr_core.bank.d_dat\[235\]$_DFF_P_} 136.242 159.57
  {u_fcore.u_core.u_ot_pr_core.bank.d_dat\[237\]$_DFF_P_} 136.242 155.52
  {u_fcore.u_core.u_ot_pr_core.bank.d_dat\[238\]$_DFF_P_} 131.922 159.03
  {u_fcore.u_core.u_ot_pr_core.bank.d_dat\[240\]$_DFF_P_} 134.082 161.19
  {u_fcore.u_core.u_ot_pr_core.bank.d_dat\[242\]$_DFF_P_} 134.082 153.9
  {u_fcore.u_core.u_ot_pr_core.bank.d_dat\[249\]$_DFF_P_} 131.922 156.06
  {u_fcore.u_core.u_ot_pr_core.bank.d_dat\[250\]$_DFF_P_} 138.402 157.68
  {u_fcore.u_core.u_ot_pr_core.bank.d_dat\[251\]$_DFF_P_} 136.242 159.84
  {u_fcore.u_core.u_ot_pr_core.bank.d_dat\[252\]$_DFF_P_} 136.242 155.25
  {u_fcore.u_core.u_ot_pr_core.bank.d_dat\[253\]$_DFF_P_} 138.402 157.41
  {u_fcore.u_core.u_ot_pr_core.bank.d_dat\[254\]$_DFF_P_} 131.922 159.3
  {u_fcore.u_core.u_ot_pr_core.bank.d_flip\[248\]$_DFF_P_} 134.082 161.46
  {u_fcore.u_core.u_ot_pr_core.bank.m_mH\[0\]$_SDFF_PN0_} 134.082 153.63
  {u_fcore.u_core.u_ot_pr_core.bank.m_mH\[3\]$_SDFF_PN0_} 131.922 155.79
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[462\]$_DFFE_PP_} 138.402 157.14
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[484\]$_DFFE_PP_} 138.402 157.95
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[485\]$_DFFE_PP_} 136.242 160.11
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[486\]$_DFFE_PP_} 136.242 154.98
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[487\]$_DFFE_PP_} 131.922 159.57
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[489\]$_DFFE_PP_} 134.082 161.73
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[490\]$_DFFE_PP_} 134.082 153.36
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[492\]$_DFFE_PP_} 131.922 155.52
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[494\]$_DFFE_PP_} 138.402 158.22
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[495\]$_DFFE_PP_} 136.242 160.38
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[497\]$_DFFE_PP_} 136.242 154.71
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[499\]$_DFFE_PP_} 138.402 156.87
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[505\]$_DFFE_PP_} 131.922 159.84
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[506\]$_DFFE_PP_} 134.082 162.0
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[507\]$_DFFE_PP_} 134.082 153.09
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[508\]$_DFFE_PP_} 131.922 155.25
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[509\]$_DFFE_PP_} 129.762 157.68
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[510\]$_DFFE_PP_} 129.762 157.41
  {u_fcore.u_core.u_ot_pr_core.bank.rr\[511\]$_DFFE_PP_} 138.402 158.49
  {u_fcore.u_core.u_ot_pr_core.bank.s1w_row\[11\]$_DFF_P_} 136.215 160.65
  {u_fcore.u_core.u_ot_pr_core.bank.wq_done\[0\]$_DFF_PN0_} 136.08 154.44
  {u_fcore.u_core.wq0__ot_q\[163\]$_DFF_P_} 138.402 156.6
  {u_fcore.u_core.wq0__ot_q\[165\]$_DFF_P_} 131.922 160.11
  {u_fcore.u_core.wq0__ot_q\[169\]$_DFF_P_} 131.922 154.98
  {u_fcore.u_core.wq0__ot_q\[171\]$_DFF_P_} 129.762 157.14
  {u_fcore.u_core.wq0__ot_q\[172\]$_DFF_P_} 129.762 157.95
  {u_fcore.u_core.wq0__ot_q\[174\]$_DFF_P_} 138.402 158.76
  {u_fcore.u_core.wq0__ot_q\[175\]$_DFF_P_} 136.242 154.17
  {u_fcore.u_core.wq0__ot_q\[180\]$_DFF_P_} 138.402 156.33
  {u_fcore.u_core.wq0__ot_q\[184\]$_DFF_P_} 136.242 160.92
  {u_fcore.u_core.wq0__ot_q\[186\]$_DFF_P_} 131.922 160.38
  {u_fcore.u_core.wq0__ot_q\[188\]$_DFF_P_} 131.922 154.71
  {u_fcore.u_core.wq0__ot_q\[189\]$_DFF_P_} 129.762 158.22
  {u_fcore.u_core.wq0__ot_q\[190\]$_DFF_P_} 129.762 156.87
  {u_fcore.u_core.wq0__ot_q\[191\]$_DFF_P_} 138.402 159.03
  {u_fcore.u_core.wq0__ot_q\[192\]$_DFF_P_} 136.242 161.19
  {u_fcore.u_core.wq0__ot_q\[193\]$_DFF_P_} 136.242 153.9
  {u_fcore.u_core.wq0__ot_q\[194\]$_DFF_P_} 138.402 156.06
  {u_fcore.u_core.wq0__ot_q\[195\]$_DFF_P_} 131.922 160.65
  {u_fcore.u_core.wq0__ot_q\[196\]$_DFF_P_} 131.922 154.44
  {u_fcore.u_core.wq0__ot_q\[197\]$_DFF_P_} 129.762 158.49
  {u_fcore.u_core.wq0__ot_q\[198\]$_DFF_P_} 129.762 156.6
  {u_fcore.u_core.wq0__ot_q\[199\]$_DFF_P_} 138.402 159.3
  {u_fcore.u_core.wq0__ot_q\[200\]$_DFF_P_} 136.242 161.46
  {u_fcore.u_core.wq0__ot_q\[201\]$_DFF_P_} 136.242 153.63
  {u_fcore.u_core.wq0__ot_q\[202\]$_DFF_P_} 138.402 155.79
  {u_fcore.u_core.wq0__ot_q\[203\]$_DFF_P_} 131.922 154.17
  {u_fcore.u_core.wq0__ot_q\[204\]$_DFF_P_} 129.762 158.76
  {u_fcore.u_core.wq0__ot_q\[205\]$_DFF_P_} 131.922 160.92
  {u_fcore.u_core.wq0__ot_q\[206\]$_DFF_P_} 129.762 156.33
  {u_fcore.u_core.wq0__ot_q\[207\]$_DFF_P_} 138.402 159.57
  {u_fcore.u_core.wq0__ot_q\[208\]$_DFF_P_} 136.242 161.73
  {u_fcore.u_core.wq0__ot_q\[209\]$_DFF_P_} 136.242 153.36
  {u_fcore.u_core.wq0__ot_q\[210\]$_DFF_P_} 138.402 155.52
  {u_fcore.u_core.wq0__ot_q\[211\]$_DFF_P_} 131.922 161.19
  {u_fcore.u_core.wq0__ot_q\[212\]$_DFF_P_} 131.922 153.9
  {u_fcore.u_core.wq0__ot_q\[213\]$_DFF_P_} 129.762 159.03
  {u_fcore.u_core.wq0__ot_q\[214\]$_DFF_P_} 129.762 156.06
  {u_fcore.u_core.wq0__ot_q\[215\]$_DFF_P_} 140.562 157.68
  {u_fcore.u_core.wq0__ot_q\[216\]$_DFF_P_} 138.402 159.84
  {u_fcore.u_core.wq0__ot_q\[217\]$_DFF_P_} 136.242 162.0
  {u_fcore.u_core.wq0__ot_q\[218\]$_DFF_P_} 136.242 153.09
  {u_fcore.u_core.wq0__ot_q\[219\]$_DFF_P_} 138.402 155.25
  {u_fcore.u_core.wq0__ot_q\[220\]$_DFF_P_} 140.562 157.41
  {u_fcore.u_core.wq0__ot_q\[221\]$_DFF_P_} 131.922 161.46
  {u_fcore.u_core.wq0__ot_q\[222\]$_DFF_P_} 131.922 153.63
  {u_fcore.u_core.wq0__ot_q\[223\]$_DFF_P_} 129.762 159.3
  {u_fcore.u_core.wq0__ot_q\[224\]$_DFF_P_} 129.762 155.79
  {u_fcore.u_core.wq0__ot_q\[225\]$_DFF_P_} 140.562 157.14
  {u_fcore.u_core.wq0__ot_q\[226\]$_DFF_P_} 140.562 157.95
  {u_fcore.u_core.wq0__ot_q\[227\]$_DFF_P_} 138.402 160.11
  {u_fcore.u_core.wq0__ot_q\[228\]$_DFF_P_} 138.402 154.98
  {u_fcore.u_core.wq0__ot_q\[229\]$_DFF_P_} 131.922 161.73
  {u_fcore.u_core.wq0__ot_q\[230\]$_DFF_P_} 131.922 153.36
  {u_fcore.u_core.wq0__ot_q\[231\]$_DFF_P_} 129.762 159.57
  {u_fcore.u_core.wq0__ot_q\[232\]$_DFF_P_} 129.762 155.52
  {u_fcore.u_core.wq0__ot_q\[233\]$_DFF_P_} 140.562 158.22
  {u_fcore.u_core.wq0__ot_q\[234\]$_DFF_P_} 138.402 160.38
  {u_fcore.u_core.wq0__ot_q\[235\]$_DFF_P_} 138.402 154.71
  {u_fcore.u_core.wq0__ot_q\[236\]$_DFF_P_} 140.562 156.87
  {u_fcore.u_core.wq0__ot_q\[237\]$_DFF_P_} 131.922 162.0
  {u_fcore.u_core.wq0__ot_q\[238\]$_DFF_P_} 131.922 153.09
  {u_fcore.u_core.wq0__ot_q\[239\]$_DFF_P_} 127.602 157.68
  {u_fcore.u_core.wq0__ot_q\[240\]$_DFF_P_} 129.762 159.84
  {u_fcore.u_core.wq0__ot_q\[241\]$_DFF_P_} 129.762 155.25
  {u_fcore.u_core.wq0__ot_q\[242\]$_DFF_P_} 127.602 157.41
  {u_fcore.u_core.wq0__ot_q\[243\]$_DFF_P_} 140.562 158.49
  {u_fcore.u_core.wq0__ot_q\[244\]$_DFF_P_} 138.402 160.65
  {u_fcore.u_core.wq0__ot_q\[245\]$_DFF_P_} 138.402 154.44
  {u_fcore.u_core.wq0__ot_q\[246\]$_DFF_P_} 140.562 156.6
  {u_fcore.u_core.wq0__ot_q\[247\]$_DFF_P_} 127.602 157.14
  {u_fcore.u_core.wq0__ot_q\[248\]$_DFF_P_} 127.602 157.95
  {u_fcore.u_core.wq0__ot_q\[249\]$_DFF_P_} 129.762 160.11
  {u_fcore.u_core.wq0__ot_q\[250\]$_DFF_P_} 129.762 154.98
  {u_fcore.u_core.wq0__ot_q\[251\]$_DFF_P_} 140.562 158.76
  {u_fcore.u_core.wq0__ot_q\[252\]$_DFF_P_} 138.402 154.17
  {u_fcore.u_core.wq0__ot_q\[253\]$_DFF_P_} 140.562 156.33
  {u_fcore.u_core.wq0__ot_q\[254\]$_DFF_P_} 138.402 160.92
  {u_fcore.u_core.wq0__ot_q\[255\]$_DFF_P_} 127.602 158.22
  {u_fcore.u_core.wq0__ot_q\[256\]$_DFF_P_} 129.762 160.38
  {u_fcore.u_core.wq0__ot_q\[257\]$_DFF_P_} 129.762 154.71
  {u_fcore.u_core.wq0__ot_q\[258\]$_DFF_P_} 127.602 156.87
  {u_fcore.u_core.wq0__ot_q\[259\]$_DFF_P_} 140.562 159.03
  {u_fcore.u_core.wq0__ot_q\[260\]$_DFF_P_} 138.402 161.19
  {u_fcore.u_core.wq0__ot_q\[261\]$_DFF_P_} 138.402 153.9
  {u_fcore.u_core.wq0__ot_q\[262\]$_DFF_P_} 140.562 156.06
  {u_fcore.u_core.wq0__ot_q\[263\]$_DFF_P_} 127.602 158.49
  {u_fcore.u_core.u_ot_pr_core.bank.rst_s1$_DFF_PN0_} 155.52 391.77
  {u_fcore.u_core.u_ot_pr_core.bank.rst_s2$_DFF_PN0_} 155.52 391.5
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
