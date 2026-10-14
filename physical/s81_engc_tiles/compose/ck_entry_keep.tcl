# dsfd_engram_c clock entry chains (el1013-s81-engram 2026-10-13): keep the u_hdly_ck_<child> HB4xp67 cells of
# rtl/dsrom_sys/engram/dsfd_engram_c.sv (cells only: the nets stay open to clock-net repair).  Sourced at PRE_FLOORPLAN, PRE_GLOBAL_PLACE,
# PRE_RESIZE, PRE_DETAIL_PLACE (ck_entry_place.tcl), PRE_CTS (OT_CTS_FIX_HOOKS) and PRE_GLOBAL_ROUTE (pre_grt_engc.tcl): this OpenROAD build does not carry
# dont_touch from one ORFS stage to the next (CTS-stop run c2: 20 cells kept through floorplan with the PRE_FLOORPLAN
# hook alone, then "RSZ-0026 Removed 20 buffers" by remove_buffers in 3_3_place_gp).
proc ot_ck_entry_keep {{open_first 0}} {
  set ki 0; set ko 0; set kp 0; set blk [ord::get_db_block]
  foreach i [$blk getInsts] {
    if {![string match *u_hdly_ck_* [$i getName]] || !([string match HB*xp67* [[$i getMaster] getName]] || [string match BUFx* [[$i getMaster] getName]])} { continue }
    # a chain's first cell hangs on the tree CTS builds (root net before CTS, a leaf net after)
    set first 1
    set n [[$i findITerm A] getNet]
    if {$n ne "NULL" && $n ne ""} {
      set d [$n getFirstOutput]
      if {$d ne "NULL" && $d ne "" && [string match *u_hdly_ck_* [[$d getInst] getName]]} { set first 0 }
    }
    # global_connect skips a dont_touch instance (ODB-0383): its supply pins are connected here
    foreach it [$i getITerms] {
      set pn [[$it getMTerm] getName]
      if {($pn eq "VDD" || $pn eq "VSS") && ([$it getNet] eq "NULL" || [$it getNet] eq "")} {
        set pg [$blk findNet $pn]
        if {$pg ne "NULL" && $pg ne ""} { $i setDoNotTouch 0; $it connect $pg; incr kp }
      }
    }
    if {$first && $open_first} { $i setDoNotTouch 0; incr ko } else { $i setDoNotTouch 1; incr ki }
  }
  puts "OT_CK_ENTRY keep: $ki delay cells, $ko first cells open for CTS, $kp supply pins connected"
}
ot_ck_entry_keep
# TritonCTS moves every sink of the root net onto a leaf net (ODB-0370 on a dont_touch first cell, CTS-stop run c3): the
# first cell of each chain is released for the clock_tree_synthesis call only and kept again right after it.
if {[info commands clock_tree_synthesis] ne "" && [info commands ot_ce_cts_orig] eq ""} {
  rename clock_tree_synthesis ot_ce_cts_orig
  proc clock_tree_synthesis {args} {
    ot_ck_entry_keep 1
    set rc [catch {uplevel 1 [list ot_ce_cts_orig {*}$args]} res opt]
    ot_ck_entry_keep
    return -options $opt $res
  }
}
