import json
from pathlib import Path
import unittest
import hashlib
import gzip

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'results/uarch/dsrom_noECC_capture_intrinsic_20261002'
class CaptureTerminal(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.t=json.loads((BASE/'priced_terminal.json').read_text())
        cls.b=json.loads((BASE/'boundary_loads.json').read_text())
    def test_full_scope_and_corners(self):
        self.assertEqual({(r['case'],r['corner']) for r in self.t['results']},{(k,c) for k in ('q','bfcolumn') for c in ('ss','ff')})
        for r in self.t['results']:
            self.assertEqual(r['endpoint_count_each_max_min'],1088)
            self.assertFalse(r['report_errors']);self.assertFalse(r['missing_templates'])
    def test_positive_slack_does_not_admit_out_of_library_slew(self):
        for r in self.t['results']:
            self.assertGreater(r['max_setup_path']['slack_ps'],0)
            self.assertEqual(r['source_max_transition_violation_unique_pin_count'],2176)
            self.assertGreater(r['worst_slew_violations'][0]['max_reported_slew_ps'],320)
        self.assertFalse(self.t['physical_admission'])
    def test_clkq_deducted_once_with_actual_subtotal(self):
        for r in self.t['results']:
            if r['corner']=='ss':
                self.assertAlmostEqual(r['conservative_remaining_wire_skew_ps']+r['capture_setup_plus_mux_subtotal_max_ps'],767.5732666666668)
                self.assertTrue(r['remaining_is_diagnostic_not_admitted_bound'])
    def test_protected_original_failure_records(self):
        receipts=json.loads((BASE/'historical_failure_manifest.json').read_text())
        self.assertEqual({r['name'] for r in receipts},set(self.t['original_failures']))
        for r in receipts:
            packed=(BASE/r['copy']).read_bytes()
            self.assertEqual(hashlib.sha256(packed).hexdigest(),r['archive_sha256'])
            raw=gzip.decompress(packed)
            self.assertEqual(hashlib.sha256(raw).hexdigest(),r['raw_record_sha256'])
            self.assertEqual(json.loads(raw)['status'],'FIRST_FAILURE_PRESERVED')
    def test_no_extra_source_edge_or_zero_parent_IO(self):
        self.assertTrue(self.t['no_new_pipeline_edge'])
        self.assertTrue(self.t['installed_CTS_not_a_prebuild_requirement'])
        self.assertFalse(self.b['physical_admission'])
        self.assertEqual(len(self.b['remaining_required_numeric_parent_endpoints']),4)
    def test_actual_source_receiver_loads_are_not_uniform_proxy(self):
        cases=self.b['cases']
        q=cases['q']['ports'];bf=cases['bfcolumn']['ports']
        self.assertEqual(q['xb_d']['width'],1024)
        self.assertEqual(sum(v['sink_count'] for v in q['xb_d']['actual_pin_loads']['ss']),0)
        self.assertEqual(sum(v['sink_count'] for v in bf['xb_d']['actual_pin_loads']['ss']),1024)
        self.assertGreater(bf['rst_n']['actual_pin_loads']['ss'][0]['load_fF'],q['rst_n']['actual_pin_loads']['ss'][0]['load_fF'])
    def test_cfg_data_actual_bitwise_load_conservation(self):
        for case in self.b['cases'].values():
            p=case['ports']['cfg_d']
            self.assertEqual(p['width'],48)
            for corner in ('ss','ff'):
                for bit in p['actual_pin_loads'][corner]:
                    self.assertAlmostEqual(bit['load_fF'],sum(x['cap_fF'] for x in bit['sinks']))
                    self.assertEqual(bit['sink_count'],len(bit['sinks']))
    def test_no_hardware_failure_inferred_from_tool_or_slew_discrepancy(self):
        d=self.t['same_loaded_source_table_diagnostic']
        self.assertLess(abs(d['Liberty_delay_ps']-d['reported_path_delay_ps']),.0001)
        self.assertLess(d['report_dcalc_Liberty_slew_ps'],320)
        self.assertGreater(d['report_checks_propagated_output_slew_ps'],320)
        self.assertIn('NOT a proven hardware/physical limitation',self.t['blocking_source_fact'])
    def test_actual_parent_source_default_off_gap_not_hidden(self):
        for r in self.b['parent_endpoint_source_receipts']:
            self.assertEqual(hashlib.sha256((ROOT/r['copy']).read_bytes()).hexdigest(),r['sha256'])
        self.assertIn('defaults all three to0',self.b['exact_caller_gap'])
if __name__=='__main__':unittest.main()
