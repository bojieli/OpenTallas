import os
import subprocess
import tempfile
import unittest
from pathlib import Path

import orfs_hold_mm as mm

STOCK = Path(__file__).with_name('testdata') / 'detail_place_selected_rc.tcl'
LOAD = r'''
proc erase_non_stage_variables {args} {}
proc load_design {args} {
  if {[info exists ::env(SET_RC_TCL)] && $::env(SET_RC_TCL) ne ""} {
    source $::env(SET_RC_TCL)
  } elseif {[info exists ::env(LAYER_PARASITICS_FILE)] && $::env(LAYER_PARASITICS_FILE) ne ""} {
    source $::env(LAYER_PARASITICS_FILE)
  } else { source $::env(PLATFORM_DIR)/setRC.tcl }
}
proc source_step_tcl {args} {}
proc set_placement_padding {args} {}
proc detailed_placement {args} {}
proc optimize_mirroring {args} {}
proc check_placement {args} {return 0}
proc estimate_parasitics {args} {}
proc env_var_or_empty {args} {return {}}
proc log_cmd {cmd args} {uplevel 1 [list $cmd {*}$args]}
proc report_metrics {args} {puts "METRIC_RC=$::rc_marker"}
proc orfs_write_db {args} {}
proc orfs_write_sdc {args} {}
'''


class DetailedPlaceSelectedRC(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.scripts = self.root / 'scripts'
        self.scripts.mkdir()
        self.stage = self.scripts / 'detail_place.tcl'
        self.stage.write_bytes(STOCK.read_bytes())
        (self.scripts / 'load.tcl').write_text(LOAD)
        self.platform = self.root / 'platform'
        self.platform.mkdir()
        (self.platform / 'setRC.tcl').write_text('set ::rc_marker platform\n')
        self.selected = self.root / 'selected.tcl'
        self.selected.write_text('set ::rc_marker calibrated\n')
        self.legacy = self.root / 'legacy.tcl'
        self.legacy.write_text('set ::rc_marker legacy\n')

    def run_stage(self, **overrides):
        env = {k: v for k, v in os.environ.items()
               if k not in ('SET_RC_TCL', 'LAYER_PARASITICS_FILE')}
        env.update(SCRIPTS_DIR=str(self.scripts), PLATFORM_DIR=str(self.platform),
                   RESULTS_DIR=str(self.root), BALANCE_ROWS='0',
                   CELL_PAD_IN_SITES_DETAIL_PLACEMENT='0', ENABLE_DPO='0')
        env.update({k: str(v) for k, v in overrides.items()})
        harness = 'namespace eval utl {proc set_metrics_stage {args} {}; proc info {args} {}}\n'
        harness += 'if {[catch {source {' + str(self.stage) + '}} err]} {puts stderr $err; exit 1}\n'
        return subprocess.run(['tclsh'], input=harness, text=True, env=env, capture_output=True)

    def test_real_stock_reproducer_then_selected_rc_before_metrics(self):
        before = self.run_stage(SET_RC_TCL=self.selected)
        self.assertEqual(before.returncode, 0, before.stderr)
        self.assertIn('METRIC_RC=platform', before.stdout)
        self.assertEqual(mm.patch_dpl_selected_rc(self.scripts), 'patched')
        after = self.run_stage(SET_RC_TCL=self.selected, LAYER_PARASITICS_FILE=self.legacy)
        self.assertEqual(after.returncode, 0, after.stderr)
        self.assertIn('METRIC_RC=calibrated', after.stdout)

    def test_older_layer_parasitics_selection(self):
        mm.patch_dpl_selected_rc(self.scripts)
        result = self.run_stage(LAYER_PARASITICS_FILE=self.legacy)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('METRIC_RC=legacy', result.stdout)

    def test_unset_selection_keeps_platform_default(self):
        mm.patch_dpl_selected_rc(self.scripts)
        result = self.run_stage()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('METRIC_RC=platform', result.stdout)

    def test_missing_explicit_selection_is_not_replaced_with_default(self):
        mm.patch_dpl_selected_rc(self.scripts)
        result = self.run_stage(SET_RC_TCL=self.root / 'missing.tcl')
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('METRIC_RC=', result.stdout)

    def test_patch_idempotence(self):
        mm.patch_dpl_selected_rc(self.scripts)
        first = self.stage.read_bytes()
        self.assertEqual(mm.patch_dpl_selected_rc(self.scripts), 'already patched')
        self.assertEqual(first, self.stage.read_bytes())


if __name__ == '__main__':
    unittest.main()
