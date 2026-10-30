# Four existing regional reset relay FFs. Same RTL, reset depth, and boot cycles.
uplevel #0 {
set rr_b [ord::get_db_block];set rr_u [[ord::get_db_tech] getDbUnitsPerMicron]
set rr_core [$rr_b getCoreArea];set rr_rows [$rr_b getRows]
set rr_site [[lindex $rr_rows 0] getSite];set rr_sw [$rr_site getWidth];set rr_rh [$rr_site getHeight]
set rr_orient {};foreach rr_r $rr_rows {dict set rr_orient [lindex [$rr_r getOrigin] 1] [$rr_r getOrient]}
set rr_targets {
 {{u_rst.rst_n\[0\]$_DFF_PN0_} 81.0 108.135}
 {{u_rst.rst_n\[1\]$_DFF_PN0_} 83.16 108.135}
 {{u_rst.rst_n\[2\]$_DFF_PN0_} 81.0 108.67500000000001}
 {{u_rst.rst_n\[3\]$_DFF_PN0_} 83.16 108.67500000000001}
}
# Actual names carry escaped brackets from Yosys; source below replaces target table from the actual census.
foreach rr_e $rr_targets {
 lassign $rr_e rr_n rr_tx rr_ty
 set rr_i [$rr_b findInst $rr_n]
 if {$rr_i eq "NULL" || $rr_i eq ""} {error "REGION_ROOT: missing exact existing data/reset FF $rr_n"}
 if {[[$rr_i getMaster] getName] ne "DFFASRHQNx1_ASAP7_75t_R"} {error "REGION_ROOT: wrong actual FF master $rr_n"}
 if {[$rr_i getPlacementStatus] eq "FIRM"} {$rr_i setPlacementStatus PLACED}
}
set rr_log [open $::env(RESULTS_DIR)/ot_region_roots.txt w]
foreach rr_e $rr_targets {
 lassign $rr_e rr_n rr_tx rr_ty
 set rr_i [$rr_b findInst $rr_n];set rr_w [[$rr_i getMaster] getWidth];set rr_h [[$rr_i getMaster] getHeight]
 set rr_c0 [expr {int(round(($rr_tx*$rr_u-$rr_w/2.0-[$rr_core xMin])/$rr_sw))}]
 set rr_r0 [expr {int(round(($rr_ty*$rr_u-$rr_h/2.0-[$rr_core yMin])/$rr_rh))}]
 set rr_found 0
 for {set rr_rad 0} {$rr_rad<=8 && !$rr_found} {incr rr_rad} {
  foreach rr_dr [lsort -unique [list $rr_rad [expr {-$rr_rad}]]] {
   set rr_y [expr {[$rr_core yMin]+($rr_r0+$rr_dr)*$rr_rh}]
   if {![dict exists $rr_orient $rr_y]} continue
   for {set rr_dc 0} {$rr_dc<=12 && !$rr_found} {incr rr_dc} {
    foreach rr_dx [lsort -unique [list $rr_dc [expr {-$rr_dc}]]] {
     set rr_x [expr {[$rr_core xMin]+($rr_c0+$rr_dx)*$rr_sw}]
     set rr_bad 0
     foreach rr_j [$rr_b getInsts] {
      if {$rr_j eq $rr_i || [$rr_j getPlacementStatus] ni {FIRM LOCKED COVER}} continue
      set rr_box [$rr_j getBBox];set rr_pad [expr {2*$rr_sw}]
      if {[$rr_box xMin]<$rr_x+$rr_w+$rr_pad && [$rr_box xMax]>$rr_x-$rr_pad && [$rr_box yMin]<$rr_y+$rr_h && [$rr_box yMax]>$rr_y} {set rr_bad 1;break}
     }
     if {$rr_bad} continue
     $rr_i setOrient [dict get $rr_orient $rr_y];$rr_i setLocation $rr_x $rr_y;$rr_i setPlacementStatus FIRM
     puts $rr_log "$rr_n\t[expr {$rr_x/double($rr_u)}]\t[expr {$rr_y/double($rr_u)}]\tFIRM"
     set rr_found 1;break
    }
   }
  }
 }
 if {!$rr_found} {error "REGION_ROOT: no clear padded site near bounded region tile for $rr_n"}
}
close $rr_log
puts "REGION_ROOT:4existingregional reset FFs FIRM near centre-left, same logicaldepth/bootcycles; no clockcells invented"
}
