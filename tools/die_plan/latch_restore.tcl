# tools/die_plan/latch_restore.tcl (LATCH-SWAP-0045, COORD 11-21): latch -> flop swap-back after every repair pass.
# OpenROAD's resizer treats a transparent latch and the same-pin edge flop as equivalent cells: on S81 t39 proof4 repair_design
# (3_4_place_resized) turned 988 DLLx2 lockup latches into DFFLQx4 falling-edge FLOPS (1_synth/2_floorplan/3_3: 0 DFFLQx4).
# That changes the logic (a latch is a wire in the cycle model, a flop is a register) and LEC on the synth netlist never sees it.
# Synthesis never maps a DFFLQx4 / DFFHQx4 (Q-output x4 flops; dfflibmap emits DFF[HL]QNx1) and no flow script inserts one, so
# every DFFLQx4 here is a swapped DLL latch and every DFFHQx4 a swapped DHL latch: put each back on the x3 latch of its Vt
# (0.918 um <= 1.35 um at the same origin: placement stays legal).  dont_touch is not used: ODB refuses the CLK / D edits of
# synth (ODB-0369), CTS and repair on a dont_touch instance.  Run after POST_FLOORPLAN / POST_RESIZE (gen_phys
# latch_restore_hook_lines) and from cts_post.tcl / grt_post.tcl; at GRT the swap runs inside an incremental global route; a cell
# that cannot be restored stops the stage (functional error).  ::ot_lr_tag names the stage in the log.
proc ot_latch_restore_all {tag} {
  set blk [ord::get_db_block]; set db [ord::get_db]
  set todo {}
  foreach i [$blk getInsts] {
    if {[regexp {^DFF([HL])Qx4_ASAP7_75t_([A-Z]+)$} [[$i getMaster] getName] -> ph vt]} { lappend todo [list $i $ph $vt] }
  }
  set grt [expr {$tag eq "post_grt" && [llength $todo]}]
  if {$grt && [catch {global_route -start_incremental} e]} { puts "OT_LATCH_RESTORE $tag: no incremental GRT ($e)"; set grt 0 }
  set n 0; set miss {}; array set tgt {}
  foreach x $todo {
    lassign $x i ph vt
    set k [expr {$ph eq "L" ? "DLLx3" : "DHLx3"}]_ASAP7_75t_$vt
    if {![info exists tgt($k)]} {
      set tgt($k) NULL
      foreach lib [$db getLibs] { set c [$lib findMaster $k]; if {$c ne "NULL"} { set tgt($k) $c; break } }
    }
    if {$tgt($k) eq "NULL" || [catch {$i swapMaster $tgt($k)}]} { lappend miss [$i getName]; continue }
    incr n
  }
  if {$grt} { global_route -end_incremental }
  puts "OT_LATCH_RESTORE $tag: $n flop(s) swapped back to latches, [llength $miss] failed"
  if {[llength $miss]} {
    set fh [open /work/FAIL_LATCH_SWAP a]; puts $fh "$tag: [llength $miss] latch->flop swaps not restored: [lrange $miss 0 19]"; close $fh
    error "OT_LATCH_RESTORE $tag: [llength $miss] latch->flop swap(s) could not be restored (functional change): [lrange $miss 0 9]"
  }
  return $n
}
ot_latch_restore_all [expr {[info exists ::ot_lr_tag] ? $::ot_lr_tag : "hook"}]
