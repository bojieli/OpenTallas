# [cg-hc] 2026-10-10 hfd_hc R25GQ: per-root die clock balancing (physical/common_flow/root_fclat.tcl) on the eight roots
# ck0..ck7: source latency = REF - root mean insertion of THIS session's tree (corner STA / FF scene / hold ECO).  Read as a
# post-SDC after the budget SDCs.  Ideal clocks or no tree: no change.
set ::env(OT_FCL_TAP_RE) {^ck[0-9]+$}
if {[llength [info commands ord::get_db_block]] && [file exists /src/physical/common_flow/root_fclat.tcl]} {
  if {[catch {source /src/physical/common_flow/root_fclat.tcl; ot_fcl_apply sdc} ot_fcl_e]} { puts "OT_FCL sdc: ERROR $ot_fcl_e" }
}
