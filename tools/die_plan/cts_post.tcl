# GENERATED-COPY of tools/die_plan/cts_post.tcl (POST_CTS hook, FLOW 2026-10-25): in-tap subtrees balanced (subtree_balance.tcl,
# DIE-CORETAP-1119), tap trees balanced to the bound insertion (tap_balance.tcl), then register pairs with no logic between them moved onto one clock leaf
# (leaf_affinity.tcl, F4; OT_LEAF_AFFINITY=0 turns it off).
# ORFS sources POST_CTS inside a procedure. Both helpers define global procs
# whose state must live at global scope too.
set cp_dir [file dirname [file normalize [info script]]]
# LOCKUP-STATION-1130 (OT_HOP_LATCH_LEAF=1): parked hop latches onto their launch flop's leaf, before every balance pass
if {[info exists ::env(OT_HOP_LATCH_LEAF)] && $::env(OT_HOP_LATCH_LEAF) eq "1" && [file exists [file join $cp_dir hop_latch_leaf.tcl]]} {
  uplevel #0 [list source [file join $cp_dir hop_latch_leaf.tcl]]; hop_latch_leaf cts
}
# DIE-CORETAP-1119 (FABLE-CLOSURE lever 1, kit side): in-tap range.  TritonCTS balances each tap tree, then the post-CTS
# clock edits (clk_leaf_repeat.tcl repeaters, repair_clock_nets long-wire buffers) add 1-3 stages on SOME branches only; the
# tap balance pads the whole tap at its root and caps the pad at the LATEST sink (target + window), so the unedited majority
# stays early.  S81 D8i col_h9_r1 pve3f8a86c (4_1_cts, placement RC): 11 of 31 taps over 60 ps in-tap range (clk_t9 165,
# clk_t27 107, clk_t14 100); in 10 of the 11 the sinks behind no post-CTS edit span <= 58 ps (clk_t14: 1,000 sinks in 13 ps,
# 15 repeated sinks 100 ps later), FF hold -120.21 on 3,603 ends.  Fix: the subtree latency balance (subtree_balance.tcl,
# default on in core kits and in the GRT-RC pre-pass) runs here first, on placement RC, per tap port: every subtree early by
# a stage or more is padded at its highest editable node up to that tap's latest register (hard-core subtrees fixed: their
# internal latency is the tap pass's job).  Then the tap balance below moves the now-narrow tap as a whole.
# OT_CTS_STB=0 (config.mk) = off (old behaviour).
if {(![info exists ::env(OT_CTS_STB)] || $::env(OT_CTS_STB) ne "0") && [file exists [file join $cp_dir subtree_balance.tcl]]} {
  set cp_stb_env {}
  foreach {k v} {OT_STB_EST placement OT_STB_BLOCK_SINKS fixed OT_STB_TAG c} {
    dict set cp_stb_env $k [expr {[info exists ::env($k)] ? $::env($k) : "OT_UNSET"}]
    set ::env($k) $v
  }
  uplevel #0 [list source [file join $cp_dir subtree_balance.tcl]]
  # restore, so a later in-process pass (rck_balance.tcl) reads its own settings
  dict for {k v} $cp_stb_env { if {$v eq "OT_UNSET"} { unset ::env($k) } else { set ::env($k) $v } }
}
uplevel #0 [list source [file join $cp_dir tap_balance.tcl]]
if {![info exists ::env(OT_LEAF_AFFINITY)] || $::env(OT_LEAF_AFFINITY) ne "0"} { uplevel #0 [list source [file join $cp_dir leaf_affinity.tcl]] }
if {[info exists ::env(OT_HOP_LATCH_LEAF)] && $::env(OT_HOP_LATCH_LEAF) eq "1" && [llength [info procs hop_latch_leaf]]} { hop_latch_leaf after_leaf_affinity }
# S81 AM half-cycle correction, opt-in and guarded by the baseline affinity checks.
if {[info exists ::env(OT_S81_RCK_AM_COHORT)] && $::env(OT_S81_RCK_AM_COHORT) eq "1"} { uplevel #0 [list source [file join $cp_dir rck_am_cohort.tcl]] }
# Kit-built pad-clock trunk (plan die_trunk host type, pad_clock_trunk.tcl at PRE_CTS): report the trunk-end arrival.
if {[llength [info commands pct_report]]} { pct_report }
# S81 rck depth balance (INV-pair pads, span acceptance), opt-in, after the leaf-repeat hook and the tap balance.
if {[info exists ::env(OT_S81_RCK_BALANCE)] && $::env(OT_S81_RCK_BALANCE) eq "1"} { uplevel #0 [list source [file join $cp_dir rck_balance.tcl]] }
# The GPL placement helper is loaded as a library in this fresh CTS process;
# report every actual root14 tail without moving any post-DPL register.
if {[info exists ::env(OT_SERDES_RM_LOCAL)] && $::env(OT_SERDES_RM_LOCAL) eq "1"} {
 set ::env(OT_SERDES_RM_LOCAL) 0
 uplevel #0 [list source [file join $cp_dir serdes_rm_local.tcl]]
 set ::env(OT_SERDES_RM_LOCAL) 1
 uplevel #0 {ot_rm_local::visibility clk_t14}
}
# KV-Q2-CLK-1115 (opt-in, OT_CTS_TAP_CENTROID=1): branch buffers to the centre of their loads (cts_tap_centroid.tcl)
if {[info exists ::env(OT_CTS_TAP_CENTROID)] && $::env(OT_CTS_TAP_CENTROID) eq "1" && [file exists [file join $cp_dir cts_tap_centroid.tcl]]} { uplevel #0 [list source [file join $cp_dir cts_tap_centroid.tcl]] }
# Optional reset FF/driver pairs must retain the registered405um reach after CTS.
if {[info exists ::env(OT_RESET_PAIR_FIXED)] && $::env(OT_RESET_PAIR_FIXED) eq "1"} {
  uplevel #0 [list source [file join $cp_dir reset_pair_place.tcl]]
  ot_reset_pair_verify_hops [ord::get_db_block] 405
}
# WAVE-FLOW-R2 11-17 (COORD lever 6): per-tap insertion after the tap balance, ADVISORY (OT_TAP_INSERTION lines; never an edit, never a gate)
if {[file exists [file join $cp_dir tap_insertion.tcl]]} { uplevel #0 [list source [file join $cp_dir tap_insertion.tcl]] }
# LATCH-SWAP-0045: resizer latch -> flop swaps of this stage's repair passes go back to latches before PG connect (latch_restore.tcl)
if {[file exists [file join $cp_dir latch_restore.tcl]]} { set ::ot_lr_tag post_cts; uplevel #0 [list source [file join $cp_dir latch_restore.tcl]] }
# FLOW 2026-10-26 PG: every clock/pad/leaf cell created up to here gets its supplies before 4_1_cts.odb is written
# (global_connect skips dont_touch cells: s8b ot_ms_* spine buffers), then a hard check (OT_PG_OPEN fails CTS).
uplevel #0 [list source [file join $cp_dir pg_connect.tcl]]
ot_pg_connect_all cts_post
ot_pg_require_bound cts_post
# FWDCLK-1: stop the kit here when a forwarded clock output lost its driver in CTS (generated per kit by gen_phys).
if {[file exists [file join $cp_dir landing_export_check.tcl]]} { uplevel #0 [list source [file join $cp_dir landing_export_check.tcl]] }
# VSN6-B 11-11 S7: loud non-tap cell census against the 400k run cap (cell_census.tcl, ADVISORY)
if {[file exists [file join $cp_dir cell_census.tcl]]} {
  uplevel #0 [list source [file join $cp_dir cell_census.tcl]]; ot_cell_census cts
} else { puts "OT_CELL_CENSUS WARN stage=cts: cell_census.tcl is not in the kit, no recount" }
# CTS-POST-RPT-1 11-19: CTS-stage timing on the post-hook netlist (4_cts_final.rpt is written before this hook)
if {[file exists [file join $cp_dir cts_post_report.tcl]]} { uplevel #0 [list source [file join $cp_dir cts_post_report.tcl]] }
