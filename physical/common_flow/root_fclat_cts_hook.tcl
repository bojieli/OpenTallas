# root_fclat_cts_hook.tcl ([cg-hc] 2026-10-10; = vm/vcut8/tap_fclat_cts_hook.tcl of claude/hbmphys-vm8-20261010 on
# root_fclat.tcl): OT_CTS_FIX_HOOKS member (list it LAST).  After clock_tree_synthesis builds the per-root trees, every
# root port (OT_FCL_TAP_RE, e.g. ^ck[0-9]+$ on a hub quarter) gets set_clock_latency -source REF - its mean insertion
# (REF = max root / core mean) before any CTS-stage repair, so the repair and the written SDCs see the roots balanced the
# way the die balances them, and the xroot negedge lockups hand off between balanced roots.
if {![info exists ::env(OT_FCL_TAP_RE)]} { set ::env(OT_FCL_TAP_RE) {^ck[0-9]+$} }
if {[info procs clock_tree_synthesis] ne "" && [info procs ot_fcl_cts_orig] eq ""} {
  rename clock_tree_synthesis ot_fcl_cts_orig
  proc clock_tree_synthesis {args} {
    ot_fcl_cts_orig {*}$args
    estimate_parasitics -placement
    set_propagated_clock [all_clocks]
    source /src/physical/common_flow/root_fclat.tcl
    ot_fcl_apply cts
  }
}
