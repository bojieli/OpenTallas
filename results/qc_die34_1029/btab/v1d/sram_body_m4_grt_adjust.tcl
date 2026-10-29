# DIE-QC-35 BTAB QC-014 V1d (kit hook, PRE_GLOBAL_ROUTE; not a check): GRT M4 layer-usage block over every hard-macro body
# INCLUDING its pin-face keep-off strips (sram_edge_m4_keepoff.tcl), region adjustment 1.0 on M4.
# Why (V1c 6_final, CHECKED): 2 nets (_1154_, g_btb[0].m_wa[8]) were globally routed with an M4 guide segment in the
# gcell column that straddles the g_btb[1]/[3] E face (gcell 0.57 um; face 254.664 inside column 254.22-254.79), so DRT
# had to drop V45 inside the face (x 253.488) and run M4 out across the keep-off + macro M4 OBS -> 4 M4 Short + 2 V4 Cut
# Short.  The keep-off obstruction is only GRT capacity, not a guide ban.  With the M4 capacity of every gcell that
# overlaps the macro removed, GRT can only give M4 to a crossing net outside the macro; macro pin nets keep their
# pin-gcell access (pin access is computed before and independent of edge capacity).
# Env: OT_SBM_ADJ (default 1.0), OT_SBM_LAYERS (default M4), OT_SBM_FACE_INSET_UM (default 0: full body; >0 shrinks the
# rectangle on the W/E faces only, diagnostic).
proc ot_sbm_env {k d} { expr {[info exists ::env($k)] && $::env($k) ne "" ? $::env($k) : $d} }
proc ot_sbm_adjust {} {
  set b [ord::get_db_block]; set u [[ord::get_db_tech] getDbUnitsPerMicron]
  set adj [ot_sbm_env OT_SBM_ADJ 1.0]; set lays [ot_sbm_env OT_SBM_LAYERS M4]; set ins [ot_sbm_env OT_SBM_FACE_INSET_UM 0]
  set f [open $::env(RESULTS_DIR)/sram_body_m4_grt_adjust.txt w]; set n 0
  foreach i [$b getInsts] {
    if {![[$i getMaster] isBlock]} continue
    set bb [$i getBBox]
    set x0 [expr {[$bb xMin] / double($u) + $ins}]; set x1 [expr {[$bb xMax] / double($u) - $ins}]
    set y0 [expr {[$bb yMin] / double($u)}]; set y1 [expr {[$bb yMax] / double($u)}]
    foreach ln $lays {
      set_global_routing_region_adjustment [list $x0 $y0 $x1 $y1] -layer $ln -adjustment $adj
      puts $f [format "GRT_REGION_ADJ %s %s %.3f %.3f %.3f %.3f adj %s" [$i getName] $ln $x0 $y0 $x1 $y1 $adj]; incr n
    }
  }
  close $f
  puts "SRAM_BODY_GRT_ADJUST $n region adjustments ($lays, $adj) over hard-macro bodies incl. pin-face strips (inset $ins)"
}
ot_sbm_adjust
