import hashlib
import importlib.util
import json
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'results/physical/indexer_topk_existing_failure_review_20261002'
s=importlib.util.spec_from_file_location('paths',ROOT/'tools/extract_topk_existing_grt_paths.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class ExistingGRT(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.log=(BASE/'worst_paths.log').read_text();cls.metrics=json.loads((BASE/'5_1_grt.json').read_text());cls.r=m.extract(cls.log,cls.metrics)
    def test_exact_report_reproduction(self):
        self.assertEqual(self.r,json.loads((BASE/'topk_endpoints.json').read_text()))
    def test_worst_path_and_arc_accounting(self):
        p=self.r['paths'][0]
        self.assertEqual(p['startpoint'],'cnt[254][0]$_DFFE_PN0P_');self.assertEqual(p['endpoint'],'suf[0][9]$_DFFE_PP_')
        self.assertEqual(p['combinational_cell_output_arcs'],195);self.assertAlmostEqual(p['slack_ps'],-10228.627,places=3)
        self.assertAlmostEqual(p['data_cell_delay_ps']+p['data_wire_delay_ps'],p['data_path_delay_including_clock_to_Q_ps'],places=2)
    def test_fail_not_physical_adoption(self):
        self.assertFalse(self.r['physical_closure']);self.assertFalse(self.r['new_place_route']);self.assertFalse(self.r['DRT_terminal_claim'])
        r=json.loads((BASE/'topk_baseline_scope.json').read_text());self.assertEqual(r['actual_macros'],0)
        self.assertEqual(r['DIG4_existing']['conditional_extra_cycles'],60);self.assertFalse(r['DIG4_existing']['source_identical_to_GRT'])
    def test_wrong_corner_or_endpoint_refused(self):
        for log in [self.log.replace('Corner: WC','Corner: BC',1),self.log.replace('Endpoint: suf[0]','Endpoint: proxy[0]',1)]:
            with self.assertRaises(ValueError):m.extract(log,self.metrics)
    def test_missing_or_duplicate_paths_refused(self):
        first=self.log.index('Startpoint: ');second=self.log.index('Startpoint: ',first+1)
        for log in [self.log[:first]+self.log[second:],self.log+self.log[first:second],self.log.replace('Endpoint: suf[8][9]','Endpoint: suf[0][9]')]:
            with self.assertRaises(ValueError):m.extract(log,self.metrics)
    def test_wrong_original_slack_refused(self):
        r=dict(self.metrics);r['globalroute__timing__setup__ws']=-1
        with self.assertRaisesRegex(ValueError,'reproduction mismatch'):m.extract(self.log,r)
    def test_analysis_has_no_mutating_flow_commands(self):
        t=(BASE/'extract_existing_grt.tcl').read_text()
        for l in t.splitlines():
            self.assertFalse(l.startswith(('global_route ','detailed_route','place','repair','write_db','synth')))
        self.assertIn('estimate_parasitics -global_routing',t)
        pins=json.loads((BASE/'analysis_admission_and_pins.json').read_text())
        self.assertTrue(pins['remote_ODB_sha256_verified']);self.assertEqual(pins['analysis_cpu'],[2]);self.assertEqual(pins['threads'],1)
    def test_indexer_original_failure_source_and_scope(self):
        r=json.loads((BASE/'kc_kdx2b_physical.json').read_text());a=json.loads((BASE/'indexer_applicability.json').read_text())
        self.assertFalse(a['failure']['timeout']);self.assertIn('exit 2',r['error']);self.assertIn('5057 edge spacing violations and 671 padding',r['error'])
        self.assertIsNone(a['current_fullreticle_verdict'])
        for pin in r['design']['sources']:
            self.assertEqual(hashlib.sha256((BASE/'source'/pin['path']).read_bytes()).hexdigest(),pin['sha256'])
        s=(BASE/'source/rtl/chip/physical/ot_w11_ring_phys.sv').read_text();self.assertIn('.WB(128)',s);self.assertIn('.XP(2)',s)
        s=(BASE/'current_source/rtl/hdc/v41x/ot_hdc_v41x_idx_kstream_ring.sv').read_text();self.assertIn('ot_hdc_v41x_idx_kdata #',s);self.assertNotIn('ot_hdc_v41x_idx_kdata_m #',s)
if __name__=='__main__':unittest.main()
