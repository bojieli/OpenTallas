# S81 measured L0 reset-entry locality repair. Two existing control flops only;
# unchanged RTL, clocks, port positions and reset depth. PLACE-only until the
# actual new sink census has a new balanced family clock plan.
uplevel #0 {
set rp_blk [ord::get_db_block]
set rp_u [[ord::get_db_tech] getDbUnitsPerMicron]
set rp_bt [$rp_blk findBTerm rst_n]
if {$rp_bt eq "NULL" || $rp_bt eq ""} {error "RESET_PAIR: rst_n missing"}
set rp_bb [$rp_bt getBBox]
set rp_py [expr {([$rp_bb yMin]+[$rp_bb yMax])/2}]
set rp_core [$rp_blk getCoreArea]
set rp_rows [$rp_blk getRows]
set rp_site [[lindex $rp_rows 0] getSite]
set rp_sw [$rp_site getWidth]
set rp_rh [$rp_site getHeight]
# Exact floorplan audit: LOCKED endcap TAP occupies x0..x0+0.108 every row.
# Four 0.054 sites leave the tap plus two sites of data-cell padding.
set rp_x [expr {[$rp_core xMin]+4*$rp_sw}]
set rp_y0 [$rp_core yMin]
set rp_r0 [expr {int(round(double($rp_py-$rp_y0)/$rp_rh))}]
set rp_names [list {u_rst.sync_q\[0\]$_DFF_PN0_} {u_rst.sync_q\[1\]$_DFF_PN0_}]
set rp_orient {}
foreach rp_r $rp_rows {dict set rp_orient [lindex [$rp_r getOrigin] 1] [$rp_r getOrient]}
set rp_log [open $::env(RESULTS_DIR)/ot_reset_input_pair.txt w]
foreach rp_n $rp_names {
  set rp_f [$rp_blk findInst $rp_n]
  if {$rp_f eq "NULL" || $rp_f eq ""} {error "RESET_PAIR: exact flop missing: $rp_n"}
  if {![string match DFFASRHQNx1_ASAP7_75t_R [[$rp_f getMaster] getName]]} {error "RESET_PAIR: wrong flop master"}
  set rp_w [[$rp_f getMaster] getWidth]
  set rp_h [[$rp_f getMaster] getHeight]
  set rp_found 0
  for {set rp_rad 0} {$rp_rad <= 48 && !$rp_found} {incr rp_rad} {
    foreach rp_dr [lsort -unique [list $rp_rad [expr {-$rp_rad}]]] {
      set rp_y [expr {$rp_y0+($rp_r0+$rp_dr)*$rp_rh}]
      if {![dict exists $rp_orient $rp_y]} continue
      set rp_bad 0
      foreach rp_i [$rp_blk getInsts] {
        if {$rp_i eq $rp_f || [$rp_i getPlacementStatus] ni {FIRM LOCKED COVER}} continue
        set rp_b [$rp_i getBBox]
        if {[$rp_b xMin] < $rp_x+$rp_w && [$rp_b xMax] > $rp_x && [$rp_b yMin] < $rp_y+$rp_h && [$rp_b yMax] > $rp_y} {set rp_bad 1;break}
      }
      if {$rp_bad} continue
      if {[$rp_f getPlacementStatus] eq "FIRM"} {$rp_f setPlacementStatus PLACED}
      $rp_f setOrient [dict get $rp_orient $rp_y]
      $rp_f setLocation $rp_x $rp_y
      $rp_f setPlacementStatus FIRM
      puts $rp_log "$rp_n\t[expr {$rp_x/double($rp_u)}]\t[expr {$rp_y/double($rp_u)}]\tFIRM"
      set rp_found 1;break
    }
  }
  if {!$rp_found} {error "RESET_PAIR: no clear row within 13um of frozen input"}
}
close $rp_log
puts "RESET_PAIR: two existing sync_q control flops FIRM beside frozen W rst_n input; no cycle or clock change"
}
