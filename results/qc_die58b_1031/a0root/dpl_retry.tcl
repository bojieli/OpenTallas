# DIE-QC-58B legalization retry (kit-local, GENERATED into the kit by derive_icg1_kit.py --dpl-retry).
# NL B2 e1 (2026-11-01): CTS hold repair met FF hold (+15.0 ps, 15.2k hold buffers concentrated in the u_me g_tx shift
# chains), then the single post-repair detailed_placement left 27 overlaps there and check_placement stopped the run
# (DPL-0033).  The netlist is final at that point; only legalization did not converge in one pass.  On a failing
# check_placement this re-runs detailed_placement (the negotiation legalizer restarts from the current, mostly legal
# state; from the 2nd retry with a wider search window) up to OT_DPL_RETRY times and checks again; the original error is raised if it never converges.
if {[info procs ot_dpl_cp_orig] eq ""} {
  rename check_placement ot_dpl_cp_orig
  proc check_placement {args} {
    if {![catch {uplevel 1 [list ot_dpl_cp_orig {*}$args]} r opts]} { return $r }
    set n [expr {[info exists ::env(OT_DPL_RETRY)] && [string is integer -strict $::env(OT_DPL_RETRY)] ? $::env(OT_DPL_RETRY) : 3}]
    for {set k 1} {$k <= $n} {incr k} {
      puts "OT_DPL_RETRY $k/$n: check_placement failed ($r); re-running detailed_placement"
      if {$k == 1} { catch {log_cmd detailed_placement} } else { catch {log_cmd detailed_placement -max_displacement {1000 200}} }
      if {![catch {uplevel 1 [list ot_dpl_cp_orig {*}$args]} r2 opts2]} {
        puts "OT_DPL_RETRY: placement legal after retry $k"
        return $r2
      }
      set r $r2; set opts $opts2
    }
    return -options $opts $r
  }
}
