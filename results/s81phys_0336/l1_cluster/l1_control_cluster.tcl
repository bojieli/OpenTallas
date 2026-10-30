# Private measured-failure repair: existing87control FFs only, unchanged pins/RTL/cycles.
# PLACE-only. Fresh actual sink census and balanced family tree required before CTS.
uplevel #0 {
set cc_b [ord::get_db_block]
set cc_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set cc_core [$cc_b getCoreArea]
set cc_rows [$cc_b getRows]
set cc_site [[lindex $cc_rows 0] getSite]
set cc_sw [$cc_site getWidth]
set cc_rh [$cc_site getHeight]
set cc_pad [expr {2*$cc_sw}]
set cc_orient {}
foreach cc_r $cc_rows {dict set cc_orient [lindex [$cc_r getOrigin] 1] [$cc_r getOrient]}
set cc_targets {
 {{ct_b\[0\]$_DFF_P_} 88.306 211.54500000000002}
 {{ct_b\[100\]$_DFF_P_} 129.022 211.27499999999998}
 {{ct_b\[10\]$_DFF_P_} 106.72 211.27499999999998}
 {{ct_b\[11\]$_DFF_P_} 107.206 211.005}
 {{ct_b\[12\]$_DFF_P_} 108.50200000000001 210.735}
 {{ct_b\[13\]$_DFF_P_} 107.854 210.465}
 {{ct_b\[14\]$_DFF_P_} 107.25999999999999 209.925}
 {{ct_b\[15\]$_DFF_P_} 109.25800000000001 209.925}
 {{ct_b\[16\]$_DFF_P_} 107.25999999999999 210.195}
 {{ct_b\[17\]$_DFF_P_} 109.582 210.195}
 {{ct_b\[18\]$_DFF_P_} 107.74600000000001 209.655}
 {{ct_b\[19\]$_DFF_P_} 133.18 210.195}
 {{ct_b\[1\]$_DFF_P_} 86.524 211.54500000000002}
 {{ct_b\[20\]$_DFF_P_} 130.102 209.925}
 {{ct_b\[21\]$_DFF_P_} 132.1 209.925}
 {{ct_b\[22\]$_DFF_P_} 134.584 210.195}
 {{ct_b\[23\]$_DFF_P_} 133.45 209.925}
 {{ct_b\[24\]$_DFF_P_} 135.394 209.925}
 {{ct_b\[25\]$_DFF_P_} 134.476 209.655}
 {{ct_b\[26\]$_DFF_P_} 136.42 209.655}
 {{ct_b\[27\]$_DFF_P_} 133.504 209.385}
 {{ct_b\[28\]$_DFF_P_} 135.34 209.385}
 {{ct_b\[29\]$_DFF_P_} 137.5 209.655}
 {{ct_b\[2\]$_DFF_P_} 88.95400000000001 211.005}
 {{ct_b\[30\]$_DFF_P_} 133.612 209.115}
 {{ct_b\[31\]$_DFF_P_} 136.582 208.845}
 {{ct_b\[32\]$_DFF_P_} 138.418 209.115}
 {{ct_b\[33\]$_DFF_P_} 133.18 208.845}
 {{ct_b\[34\]$_DFF_P_} 135.718 209.115}
 {{ct_b\[35\]$_DFF_P_} 138.58 208.575}
 {{ct_b\[36\]$_DFF_P_} 139.228 209.385}
 {{ct_b\[37\]$_DFF_P_} 141.01 209.115}
 {{ct_b\[38\]$_DFF_P_} 141.01 208.575}
 {{ct_b\[39\]$_DFF_P_} 138.364 208.305}
 {{ct_b\[3\]$_DFF_P_} 87.82 211.27499999999998}
 {{ct_b\[42\]$_DFF_P_} 144.52 209.385}
 {{ct_b\[43\]$_DFF_P_} 146.68 209.115}
 {{ct_b\[4\]$_DFF_P_} 88.414 210.735}
 {{ct_b\[5\]$_DFF_P_} 105.1 209.385}
 {{ct_b\[6\]$_DFF_P_} 107.098 209.115}
 {{ct_b\[77\]$_DFF_P_} 127.834 210.465}
 {{ct_b\[78\]$_DFF_P_} 122.488 210.735}
 {{ct_b\[79\]$_DFF_P_} 126.75399999999999 210.195}
 {{ct_b\[7\]$_DFF_P_} 103.48 209.385}
 {{ct_b\[80\]$_DFF_P_} 124.864 210.465}
 {{ct_b\[81\]$_DFF_P_} 126.75399999999999 210.465}
 {{ct_b\[82\]$_DFF_P_} 124.756 210.195}
 {{ct_b\[83\]$_DFF_P_} 126.7 209.655}
 {{ct_b\[84\]$_DFF_P_} 128.914 209.925}
 {{ct_b\[85\]$_DFF_P_} 125.62 209.655}
 {{ct_b\[86\]$_DFF_P_} 126.7 209.925}
 {{ct_b\[87\]$_DFF_P_} 129.4 209.385}
 {{ct_b\[88\]$_DFF_P_} 125.836 209.385}
 {{ct_b\[89\]$_DFF_P_} 127.132 209.385}
 {{ct_b\[8\]$_DFF_P_} 105.964 208.845}
 {{ct_b\[90\]$_DFF_P_} 131.992 209.385}
 {{ct_b\[91\]$_DFF_P_} 128.86 209.115}
 {{ct_b\[92\]$_DFF_P_} 132.316 209.115}
 {{ct_b\[93\]$_DFF_P_} 130.156 208.845}
 {{ct_b\[94\]$_DFF_P_} 123.46000000000001 210.195}
 {{ct_b\[95\]$_DFF_P_} 131.236 209.115}
 {{ct_b\[96\]$_DFF_P_} 127.294 209.115}
 {{ct_b\[97\]$_DFF_P_} 130.102 209.115}
 {{ct_b\[98\]$_DFF_P_} 130.858 208.575}
 {{ct_b\[99\]$_DFF_P_} 127.834 208.845}
 {{ct_b\[9\]$_DFF_P_} 107.206 208.845}
 {{fault$_DFF_PN0_} 111.364 209.925}
 {{ra\[0\]$_DFF_P_} 317.5 110.875}
 {{ra\[3\]$_DFF_P_} 317.554 91.975}
 {{sa_r\[0\]$_DFF_P_} 340.038 79.715}
 {{sa_r\[1\]$_DFF_P_} 337.554 78.905}
 {{sa_r\[2\]$_DFF_P_} 340.632 79.445}
 {{sa_r\[3\]$_DFF_P_} 337.446 79.445}
 {{sa_r\[4\]$_DFF_P_} 338.52599999999995 79.445}
 {{sa_r\[5\]$_DFF_P_} 337.446 80.525}
 {{we\[10\]$_DFF_PN0_} 315.47 210.195}
 {{we\[11\]$_DFF_PN0_} 314.822 209.925}
 {{we\[12\]$_DFF_PN0_} 315.47 210.465}
 {{we\[13\]$_DFF_PN0_} 315.47 210.735}
 {{we\[14\]$_DFF_PN0_} 315.092 211.005}
 {{we\[15\]$_DFF_PN0_} 314.12 211.27499999999998}
 {{we\[1\]$_DFF_PN0_} 315.47 208.845}
 {{we\[2\]$_DFF_PN0_} 314.282 209.115}
 {{we\[4\]$_DFF_PN0_} 314.282 209.385}
 {{we\[5\]$_DFF_PN0_} 315.038 209.655}
 {{we\[8\]$_DFF_PN0_} 313.094 210.735}
 {{we\[9\]$_DFF_PN0_} 313.418 209.925}
}
# Release only the exact87targets before allocation; protect all other FIRM/LOCKED cells.
foreach cc_entry $cc_targets {
 lassign $cc_entry cc_n cc_tx cc_ty
 set cc_i [$cc_b findInst $cc_n]
 if {$cc_i eq "NULL" || $cc_i eq ""} {error "CTRL_CLUSTER: exact existing target missing $cc_n"}
 if {![string match DFF* [[$cc_i getMaster] getName]]} {error "CTRL_CLUSTER: target is not existing DFF $cc_n"}
 if {[$cc_i getPlacementStatus] eq "FIRM"} {$cc_i setPlacementStatus PLACED}
}
set cc_log [open $::env(RESULTS_DIR)/ot_control_cluster.txt w]
set cc_count 0
foreach cc_entry $cc_targets {
 lassign $cc_entry cc_n cc_tx cc_ty
 set cc_i [$cc_b findInst $cc_n]
 set cc_w [[$cc_i getMaster] getWidth];set cc_h [[$cc_i getMaster] getHeight]
 set cc_x0 [$cc_core xMin];set cc_y0 [$cc_core yMin]
 set cc_col [expr {int(round(($cc_tx*$cc_dbu-$cc_w/2.0-$cc_x0)/$cc_sw))}]
 set cc_row [expr {int(round(($cc_ty*$cc_dbu-$cc_h/2.0-$cc_y0)/$cc_rh))}]
 set cc_found 0
 for {set cc_rad 0} {$cc_rad<=12 && !$cc_found} {incr cc_rad} {
  foreach cc_dr [lsort -unique [list $cc_rad [expr {-$cc_rad}]]] {
   set cc_y [expr {$cc_y0+($cc_row+$cc_dr)*$cc_rh}]
   if {![dict exists $cc_orient $cc_y]} continue
   for {set cc_dc 0} {$cc_dc<=12 && !$cc_found} {incr cc_dc} {
    foreach cc_dd [lsort -unique [list $cc_dc [expr {-$cc_dc}]]] {
     set cc_x [expr {$cc_x0+($cc_col+$cc_dd)*$cc_sw}]
     if {$cc_x<$cc_x0 || $cc_x+$cc_w>[$cc_core xMax] || $cc_y+$cc_h>[$cc_core yMax]} continue
     set cc_bad 0
     foreach cc_j [$cc_b getInsts] {
      if {$cc_j eq $cc_i || [$cc_j getPlacementStatus] ni {FIRM LOCKED COVER}} continue
      set cc_bb [$cc_j getBBox]
      if {[$cc_bb xMin]<$cc_x+$cc_w+$cc_pad && [$cc_bb xMax]>$cc_x-$cc_pad && [$cc_bb yMin]<$cc_y+$cc_h && [$cc_bb yMax]>$cc_y} {set cc_bad 1;break}
     }
     if {$cc_bad} continue
     $cc_i setOrient [dict get $cc_orient $cc_y]
     $cc_i setLocation $cc_x $cc_y
     $cc_i setPlacementStatus FIRM
     puts $cc_log "$cc_n\t[expr {$cc_x/double($cc_dbu)}]\t[expr {$cc_y/double($cc_dbu)}]\tFIRM"
     set cc_found 1;incr cc_count;break
    }
   }
  }
 }
 if {!$cc_found} {error "CTRL_CLUSTER: no free padded site near bounded target $cc_n"}
}
close $cc_log
if {$cc_count!=87} {error "CTRL_CLUSTER: target count $cc_count !=87"}
puts "CTRL_CLUSTER:87 existing control FFs, unchanged pins/RTL/cycles; PLACE-only, fresh clock model required"
}
