"""CDC batching retains every exact bound and both finite-path obligations."""
import subprocess
import unittest

import cdc_sync_constraints as C


MOCK = r'''
set nset 0
set nquery 0
set missing 0
set nonfinite 0
proc get_cells {args} {return [lindex $args end]}
proc get_full_name {x} {return $x}
proc get_clocks {args} {return core_clk}
proc get_property {obj prop} {
  if {$prop eq "period"} {return 1200}
  if {$::nonfinite} {return Inf}
  return 5
}
proc ot_ce_finite {x} {return [expr {$x ne "Inf"}]}
proc set_max_delay {args} {incr ::nset}
proc set_min_delay {args} {incr ::nset}
proc find_timing_paths {args} {
  if {$::nset != 8} {error "query before ALL 8 constraints were installed"}
  incr ::nquery
  if {$::missing} {return {}}
  return path
}
proc ot_cdc_seam_role {x} {return {bridge bank 0}}
'''


class Batch(unittest.TestCase):
    def run_tcl(self, mode='', verify='ot_cdc_verify; ot_cdc_seam_complete'):
        body = MOCK + C.TCL + C.MIXED_TCL + r'''
set ::ot_cdc_seams [dict create bridge [dict create src core dst serial setup 2 hold 1]]
ot_cdc_bound a b 250
ot_cdc_seam_crossing c d c d core serial
ot_cdc_bound e f 833
ot_cdc_seam_crossing g h g h core serial
if {$nquery != 0} {error "eager timing query"}
''' + mode + '\n' + verify + r'''
puts "COUNTS $nset $nquery"
puts "PENDING [llength $::ot_cdc_pending] [llength $::ot_cdc_seam_pending]"
'''
        p = subprocess.run(['tclsh'], input='if {[catch {\n' + body + '\n} err]} {puts stderr $err; exit 1}\n',
                           text=True, capture_output=True)
        return p

    def test_kept_mapped_hierarchy_name_is_exactly_normalized(self):
        p = subprocess.run(['tclsh'], input=C.FLOW_WRAPPER_TCL + r'''
puts "NAMES [ot_cdc_flow_names {u_ot_pr_core.u_q.req[0].u_q/q}]"
puts "NESTED [ot_cdc_flow_names unrelated.u_ot_pr_core/u_q/q]"
''', text=True, capture_output=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn('u_q.req[0].u_q.q', p.stdout)
        self.assertNotIn('NESTED u_q.q', p.stdout)

    def test_all_pairs_and_bounds_before_queries(self):
        p = self.run_tcl()
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn('COUNTS 8 8', p.stdout)
        self.assertIn('PENDING 0 0', p.stdout)
        self.assertIn('OT_CDC_SEAM STRUCTURAL_PASS', p.stdout)

    def test_missing_path_still_fails(self):
        for verify, prefix in [('ot_cdc_verify', 'OT_CDC:'),
                               ('ot_cdc_seam_complete', 'OT_CDC_SEAM:')]:
            with self.subTest(verify=verify):
                p = self.run_tcl('set missing 1', verify)
                self.assertNotEqual(p.returncode, 0)
                self.assertIn(prefix + ' missing finite bounded max path', p.stderr)

    def test_nonfinite_path_still_fails(self):
        for verify in ['ot_cdc_verify', 'ot_cdc_seam_complete']:
            with self.subTest(verify=verify):
                p = self.run_tcl('set nonfinite 1', verify)
                self.assertNotEqual(p.returncode, 0)
                self.assertIn('missing finite bounded max path', p.stderr)

    def test_only_existing_pre_mm_deferral_allowed(self):
        p = self.run_tcl('set missing 1; set ::env(OT_HOLD_MM) 1')
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn('COUNTS 8 8', p.stdout)
        p = self.run_tcl('set missing 1; set ::env(OT_HOLD_MM) 1; set ::ot_mm_active 1')
        self.assertNotEqual(p.returncode, 0)
        self.assertIn('missing finite bounded max path', p.stderr)


if __name__ == '__main__':
    unittest.main()
