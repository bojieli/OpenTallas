# MACRO-CLK default (macro-clk-1010, 2026-10-10): SRAM-macro clock sinks get small, local, buffered leaves.
#
# Evidence (ds-1010 s81b-coll_lane_ww lcrph / lcrpw / lcr0ctl; HBM SM tile_eg g363): TritonCTS splits every clock net
# into a macro tree and a register tree.  With its macro clustering defaults (-macro_clustering_size 4, diameter = the
# whole sink region) the H-tree stop criterion (sink-region HPWL < max wirelength, <= 15 sinks) ends the macro tree after
# two levels with NO leaf buffers: the lane's 10 SRAM clock pins hang on 3-4 long nets (383-437 um average sink wire).
# Macro clk slew 115-260 ps; once the macros sit further apart the macro clock lands ~60 ps after the register tree and
# the macro's slew-dependent hold time grows -> SRAM wd_in / addr hold -65..-175 ps that CTS / GRT hold repair cannot
# converge on (EARLY_FAIL_HOLD), even on the recipe that closed on 10-08 with the macros packed closer.
#
# Fix at the source, for every block: at most OT_CTS_MACRO_SIZE (2) macro clock pins per leaf, leaf diameter
# OT_CTS_MACRO_DIAM (40 um).  Each macro then has a short buffered leaf, its slew is bounded, and TritonCTS's macro /
# register latency balancing (CTS-0033) matches a macro tree whose delay it can actually predict.
#
# Installed as a clock_tree_synthesis wrapper, so it applies to ORFS cts.tcl AND to any hook that calls CTS itself, and
# to a recipe's own CTS_ARGS: the macro options are appended unless the caller already names -macro_clustering_*.
# Loaded by tools/orfs_hold_mm.tcl (sourced in every ORFS stage of tools/run_abi3_physical.py and
# tools/hbm_accel_smh_physical.py routes).  No-op for a block with fewer than 2 clocked macros.  Opt out:
# OT_CTS_MACRO_CLUSTER=0.  Constraints, clocks and the register-tree options are untouched.
proc ot_mcc_env {k d} {
  if {[info exists ::env($k)] && $::env($k) ne ""} { return $::env($k) }
  return $d
}
proc ot_mcc_count {} {
  set nm 0
  if {[catch {set blk [ord::get_db_block]}] || $blk eq "NULL" || $blk eq ""} { return 0 }
  foreach inst [$blk getInsts] {
    if {![[$inst getMaster] isBlock]} continue
    foreach it [$inst getITerms] {
      if {![$it isInputSignal] && [[$it getMTerm] getSigType] ne "CLOCK"} continue
      set n [$it getNet]
      if {[[$it getMTerm] getSigType] eq "CLOCK" || ($n ne "NULL" && $n ne "" && [$n getSigType] eq "CLOCK")} { incr nm; break }
    }
  }
  return $nm
}
proc ot_mcc_args {a} {
  if {[ot_mcc_env OT_CTS_MACRO_CLUSTER 1] eq "0"} { puts "OT_MACRO_CTS off (OT_CTS_MACRO_CLUSTER=0)"; return $a }
  if {[lsearch -glob $a -macro_clustering_*] >= 0} { puts "OT_MACRO_CTS kept: the caller names -macro_clustering_*"; return $a }
  set nm [ot_mcc_count]
  if {$nm < 2} { puts "OT_MACRO_CTS skipped: $nm clocked macro(s)"; return $a }
  set size [ot_mcc_env OT_CTS_MACRO_SIZE 2]
  # TritonCTS segfaults on -macro_clustering_size 1 (lcrpx A/B 2026-10-10: macro tree "Sinks 0", SIGSEGV)
  if {![string is integer -strict $size] || $size < 2} { puts "OT_MACRO_CTS size $size -> 2 (TritonCTS needs >= 2)"; set size 2 }
  set diam [ot_mcc_env OT_CTS_MACRO_DIAM 40]
  lappend a -macro_clustering_size $size -macro_clustering_max_diameter $diam
  puts "OT_MACRO_CTS $nm clocked macros: -macro_clustering_size $size -macro_clustering_max_diameter $diam"
  return $a
}
if {[info commands clock_tree_synthesis] ne "" && [info commands ot_mcc_cts_orig] eq ""} {
  rename clock_tree_synthesis ot_mcc_cts_orig
  proc clock_tree_synthesis {args} {
    uplevel 1 [list ot_mcc_cts_orig {*}[ot_mcc_args $args]]
  }
}
