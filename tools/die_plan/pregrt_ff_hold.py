#!/usr/bin/env python3
"""HEAD-TILE-PREGRT-HOLD (DH59-TILE 11-03, opt-in plan clock.pregrt_ff_hold): placement-basis FF hold repair on 4_cts.odb
before the first GRT, legalized and checked, for a kit whose hold debt is structural (a tap window W_t on every cross-tap
pair: HEAD hd_tile W=130, 11,952 endpoints at -161.8 ps).  The in-flow GRT repair re-routes per iteration (measured:
hd_spn_end 3,730 endpoints / 3,809 buffers in 5.2 h); the same work on placement parasitics took 166 s on hd_tile
(DIE-HEAD-53 V1: +5.00 ps / 0 endpoints, 24,282 buffers).  The in-flow GRT FF repair stays and takes the residual; sign-off FF
hold >= 0 stays the only gate.  Timing context = hold_gate.tcl verbatim (same contract, same overlay), so the kit carries the
head of its own hold_gate.tcl.  Off (the default): no tcl, no config line, the run_kit.sh step is a grep no-op."""
from pathlib import Path

MARK = "# A separate FF-only process: do not impersonate the shared multi-mode context.\n"
CONFIG = "export OT_PREGRT_FF_HOLD = 1"
TAIL = r"""# HEAD-TILE-PREGRT-HOLD: repair + legalize on the context above, then replace 4_cts.odb
set pg_w0 [sta::time_sta_ui [sta::worst_slack_cmd min]]; set pg_n0 [sta::endpoint_violation_count min]
set pg_i0 [llength [[ord::get_db_block] getInsts]]; set pg_t0 [clock seconds]
puts "OT_PREGRT_FF_HOLD before wns $pg_w0 endpoints $pg_n0 insts $pg_i0"
for {set pg_ps 1} {$pg_ps <= 6} {incr pg_ps} {
  set pg_wp [sta::time_sta_ui [sta::worst_slack_cmd min]]
  repair_timing -hold -hold_margin 5
  set pg_wq [sta::time_sta_ui [sta::worst_slack_cmd min]]
  puts "OT_PREGRT_FF_HOLD pass $pg_ps wns $pg_wq endpoints [sta::endpoint_violation_count min] insts [llength [[ord::get_db_block] getInsts]]"
  if {$pg_wq >= 0 || $pg_wq - $pg_wp < 1.0} break
}
# repair_timing seats a hold cell at its driver, on a macro in a macro-dominated tile (V1: 23 cells): legalize all of them
set pg_nh 0
foreach pg_i [[ord::get_db_block] getInsts] {
  if {[string match "hold*" [$pg_i getName]] || [string match "*/hold*" [$pg_i getName]]} { $pg_i setPlacementStatus PLACED; incr pg_nh }
}
detailed_placement
check_placement -verbose
estimate_parasitics -placement
puts "OT_PREGRT_FF_HOLD after wns [sta::time_sta_ui [sta::worst_slack_cmd min]] endpoints [sta::endpoint_violation_count min] hold_cells $pg_nh insts [llength [[ord::get_db_block] getInsts]] setup_wns [sta::time_sta_ui [sta::worst_slack_cmd max]] secs [expr {[clock seconds]-$pg_t0}]"
write_db $::env(ODB)
"""
def tcl_text(hold_gate_text):
    if hold_gate_text.count(MARK) != 1:
        raise ValueError("pregrt_ff_hold: hold_gate.tcl context marker not found exactly once; fails closed")
    return hold_gate_text.split(MARK)[0] + TAIL


def install(t, kd):
    """Kit tcl (run_kit.sh runs it when config.mk says OT_PREGRT_FF_HOLD = 1).  False (no writes) when off."""
    if not t.get("clock", {}).get("pregrt_ff_hold"):
        return False
    kd = Path(kd)
    (kd / "pregrt_ff_hold.tcl").write_text(tcl_text((kd / "hold_gate.tcl").read_text()))
    return True
