"""RC/reference ordering and temporary-scene exception regression (no STA substitute)."""
import subprocess
import tempfile
import unittest
from pathlib import Path

TCL = Path(__file__).resolve().parents[1] / 'orfs_hold_mm.tcl'


def run(body, *, synced=True, enabled=True, stage='3_place.sdc'):
    src = TCL.read_text()
    procs = []
    for name in ('ot_mm_sync', 'ot_mm_unsync', 'ot_rc_cal_hold'):
        a = src.index('proc ' + name + ' ')
        b = src.index('\nproc ', a + 1)
        procs.append(src[a:b])
    with tempfile.TemporaryDirectory() as temp:
        script = '''
set mode ss; set rc platform; set reference platform
set ss_mask 0; set ff_mask 0; set copied_mask 0; set syncs 0
set budgets {C25 U25 Usetup60 HM30 relief0}
proc ot_rc_cal_apply {kind} { if {!$::enabled} {return 0}; set ::rc calibrated; return 1 }
proc ot_rc_cal_mode {} {return -placement}
proc estimate_parasitics {args} {set ::estimated $::rc}
proc ot_rc_cal_restore {} {set ::rc platform}
proc set_mode {m} {set ::mode $m}
proc write_sdc {args} {set ::copied_mask $::ss_mask; close [open [lindex $args end] w]}
proc read_sdc {f} {
  if {$::mode ne "ff"} {error "wrong reference mode"}
  if {[file tail $f] eq "signoff.sdc"} {
    set ::reference $::estimated; incr ::syncs
  } else {set ::ff_mask $::copied_mask}
}
proc all_clocks {} {return core}
proc set_propagated_clock {args} {}
proc ot_mm_scene_shim {n} {}
proc ot_mm_sync_link_periods {} {}
proc set_false_path {args} {if {[lindex $args 0] eq "-hold"} {set ::ss_mask 1}}
proc unset_path_exceptions {args} {set ::ss_mask 0}
proc ot_mm_sc {} {return WC}
proc ot_mm_ws {args} {return 0}
proc check {v msg} {if {![uplevel 1 [list expr $v]]} {error $msg}}
'''
        script += f'\nset enabled {int(enabled)}\nset ::env(RESULTS_DIR) {{{temp}}}\n'
        script += f'set ::ot_mm_active 1\nset ::ot_mm_stage {stage}\n'
        script += f'set ::env(OT_MM_FF_SDC) {{{temp}/signoff.sdc}}\nclose [open {{{temp}/signoff.sdc}} w]\n'
        if synced:
            script += 'set ::ot_mm_synced 1; set ss_mask 1\n'
        script += '\n'.join(procs) + '\n' + body
        # tclsh stdin alone can exit zero on script errors; use an explicit catch.
        wrapped = 'if {[catch {\n' + script + '\n} err opts]} {puts stderr $err; exit 1}\n'
        p = subprocess.run(['tclsh'], input=wrapped, capture_output=True, text=True)
        if p.returncode:
            raise AssertionError(p.stdout + p.stderr)


class ReferenceOrdering(unittest.TestCase):
    def test_calibrated_reference_before_body_and_restored_after(self):
        run('''ot_rc_cal_hold {check {$reference eq "calibrated" && !$ff_mask} stale}
check {$reference eq "platform" && $syncs == 2 && $ss_mask && !$ff_mask} restoration''')

    def test_original_order_negative_is_detected(self):
        run('''ot_rc_cal_apply hold; estimate_parasitics -placement
check {$reference ne $estimated} stale_negative''')

    def test_masked_ss_copy_negative_is_detected(self):
        run('''ot_mm_sync
check {$ff_mask} copied_mask_negative''')

    def test_body_error_still_restores_reference(self):
        run('''set status [catch {ot_rc_cal_hold {error repair_failed}} msg]
check {$status && $msg eq "repair_failed" && $reference eq "platform" && !$ff_mask} error_cleanup''')

    def test_unsynced_scene_is_not_enabled(self):
        run('''ot_rc_cal_hold {check {$rc eq "calibrated"} calibrated}
check {$syncs == 0 && ![info exists ::ot_mm_synced]} unsolicited_scene''', synced=False)

    def test_disabled_calibration_leaves_scene_alone(self):
        run('''ot_rc_cal_hold {check {$reference eq "platform"} disabled}
check {$syncs == 0 && $ss_mask} disabled_refresh''', enabled=False)

    def test_global_route_stage_also_refreshes(self):
        run('''ot_rc_cal_hold {check {$reference eq "calibrated" && !$ff_mask} grt}
check {$syncs == 2} grt_restore''', stage='4_cts.sdc')

    def test_explicit_budgets_and_outer_cleanup_preserved(self):
        run('''set original $budgets
ot_rc_cal_hold {check {$budgets eq $original} changed_budget}
ot_mm_unsync
check {$budgets eq $original && !$ss_mask && !$ff_mask && ![info exists ::ot_mm_synced]} outer_cleanup''')


if __name__ == '__main__':
    unittest.main()
