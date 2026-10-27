# ORFS step hook (PRE_CTS, PRE_GLOBAL_ROUTE), flow-triage 2026-10-08: repair_timing throws RSZ-0060 ("Max buffer count
# reached") AFTER it has inserted its hold buffers, which kills the stage although the design is whole (ha2_relay pb108w140
# finished at hold WNS +4.1 / TNS 0 and still died).  Continue on the repaired design; constraints and margins are
# unchanged, so the residual hold is reported by the sign-off STA instead of a dead stage.
if {[info procs repair_timing_helper] ne "" && [info procs ot_rsz_orig_rth] eq ""} {
  rename repair_timing_helper ot_rsz_orig_rth
  proc repair_timing_helper {args} {
    if {[catch {ot_rsz_orig_rth {*}$args} m o]} {
      if {[regexp {RSZ-0060} $m]} {
        puts "OT_RSZ_CAP: repair hit the buffer cap (RSZ-0060); continuing on the repaired design, sign-off decides"
        return
      }
      return -options $o $m
    }
  }
}
