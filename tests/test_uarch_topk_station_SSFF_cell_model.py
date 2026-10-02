import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import uarch_topk_station_SSFF_cell_model as M
class StationCells(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.model=M.build()
    def test_exact_model(self):self.assertEqual(self.model,json.loads((M.BASE/'model_r3.json').read_bytes()))
    def test_units_clock_and_full_geometry(self):
        m=self.model;self.assertEqual(m['clock'],dict(period_ps=833,setup_uncertainty_ps=60,hold_uncertainty_ps=25,frequency_relaxed=False))
        self.assertEqual(m['geometry'],{'CB':14,'DIG':8,'LDW':4,'N':4,'NBIN':256,'NMAX':2048,'P':64,'PF':64})
        log=(M.BASE/'unit_probe.log').read_text()
        for token in ['time 1ps','capacitance 1fF','distance 1um','sta::capacitance_ui_sta','sta::distance_ui_sta']:self.assertIn(token,log)
    def test_source_logic_polarity(self):
        f=self.model['cell_facts']['SS'];self.assertEqual(f['ff']['output_function'],'IQN');self.assertEqual(f['inv']['output_function'],'!A')
        self.assertTrue(f['ff']['inverted_QN_requires_restoring_INV'])
        self.assertIn('A',f['reset_mask']['output_function']);self.assertIn('B',f['reset_mask']['output_function'])
        self.assertEqual(set(f['reset_mask']['delay_transition_tables']),{pin+'.'+name for pin in ['A','B'] for name in ['cell_rise','cell_fall','rise_transition','fall_transition']})
    def test_multiinput_allarcs_bound(self):
        f=self.model['cell_facts']['SS']['reset_mask'];tables=f['delay_transition_tables']
        values=[max(r[0] for r in t['values']) for name,t in tables.items() if 'cell_' in name]
        self.assertEqual(max(values),92.7815);self.assertEqual(self.model['SS_bounds_ps']['reset_mask_AND'],max(values))
    def test_cap_exposes_20segment_unbuffered_failure(self):
        w=self.model['wire_load'];f=self.model['cell_facts']['SS']['inv']
        self.assertGreater(w['unbuffered20segment_wire_plus_receiver_fF'],f['max_output_cap_fF'])
        self.assertAlmostEqual(w['unbuffered20segment_wire_plus_receiver_fF'],134.93193783875)
        self.assertEqual(w['characterized_slew_safe_INV_load_ceiling_fF'],11.52)
        self.assertFalse(w['20segment_without_repeater_station_load_proof'])
    def test_no_delay_doublecount(self):
        m=self.model;d=m['SS_bounds_ps'];s=m['finite_segmentation'];hop=s['maximum_segment_um']
        self.assertTrue(m['old189_5ps_combined_allowance_replaced_not_added'])
        self.assertAlmostEqual(s['SS_path_plus_setup_uncertainty_ps'],sum(d.values())+0.76*hop+60)
    def test_cap_driven_segment_derivation(self):
        m=self.model;w=m['wire_load'];s=m['finite_segmentation']
        self.assertAlmostEqual(w['cap_limited_hop_um'],(11.52-w['receiver_input_fF'])/0.178475)
        self.assertLess(w['cap_limited_hop_um'],w['timing_limited_hop_um'])
        self.assertEqual(s['segments_each_direction'],244);self.assertEqual(s['formed_write_segments'],69)
        self.assertLessEqual(s['maximum_segment_um']*0.178475+w['receiver_input_fF'],11.52)
    def test_cost_exact_and_not_adopted(self):
        c=self.model['cost'];bits=4210*243+2113*68
        self.assertEqual(c['additional_station_bits'],bits);self.assertEqual(bits,1166714)
        self.assertEqual(c['additional_cycles_per_call'],554);self.assertEqual(c['ninecall_extra_cycles'],4986)
        self.assertAlmostEqual(c['cell_area_per_bit_um2'],0.2916+0.04374+0.08748)
        self.assertAlmostEqual(c['FF_INV_AND_reservation_mm2_at50pct'],0.98662002696)
        self.assertGreater(c['additional_clock_pin_capacitance_fF'],500000)
    def test_hold_not_falsely_closed(self):
        h=self.model['FF_hold_screen'];self.assertAlmostEqual(h['remaining_for_adverse_capture_skew_ps'],-5.84334)
        self.assertTrue(h['even_characterized_zero_wire_screen_requires_hold_repair'])
        self.assertTrue(h['sub0_72fF_load_earliest_arcs_unqualified']);self.assertTrue(h['no_context_hold_claim'])
    def test_reset_and_no_admission(self):
        m=self.model;self.assertTrue(m['reset_contract']['actual_asynchronous_source_reset_requires_immediate_sink_enable_suppression'])
        self.assertFalse(m['G0']['RTL_admitted']);self.assertFalse(m['G0']['PR_admitted']);self.assertEqual(m['physical_jobs_launched'],0)
        self.assertFalse(m['optional_variant_sweep']);self.assertEqual(m['new_PVE2_PVE3_jobs'],0)
    def test_load_outside_table_refused(self):
        with self.assertRaisesRegex(ValueError,'outside characterized'):M.bound(self.model['cell_facts']['SS']['inv']['delay_transition_tables'],'cell_',1000)
    def test_bad_dimensions_refused(self):
        with self.assertRaisesRegex(ValueError,'dimensions changed'):M.table('cell_rise (t) {index_1("1,2"); index_2("1,2"); values("1,2");}','cell_rise')
    def test_nested_quoted_braces(self):
        self.assertEqual(M.group('cell (a) { function : "{x}"; pin (D) { direction : input; } }','cell','a'),' function : "{x}"; pin (D) { direction : input; } ')
        with self.assertRaisesRegex(ValueError,'unbalanced'):list(M.groups('cell (a) {','cell'))
    def test_input_manifest_mutant(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);(p/'unit_probe.log').write_bytes((M.BASE/'unit_probe.log').read_bytes())
            (p/'source_manifest.json').write_bytes((M.BASE/'source_manifest.json').read_bytes()+b' ')
            with mock.patch.object(M,'BASE',p):
                with self.assertRaisesRegex(ValueError,'manifest changed'):M.build()
    def test_origins_do_not_require_git(self):
        with mock.patch.object(M.T.F.A.SourceArchive,'commit_available',side_effect=AssertionError('no history lookup')):self.assertEqual(M.build(),self.model)
if __name__=='__main__':unittest.main()
