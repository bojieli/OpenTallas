import json,hashlib,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from dsrom_noECC_slew_enable_diagnosis import lookup
BASE=ROOT/'results/uarch/dsrom_noECC_slew_enable_diagnosis_20261002'
class EnableCause(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.x=json.loads((BASE/'model.json').read_text())
    def test_different_arcs_explain_graph_slew_without_tuning(self):
        p=self.x['source_interpolation']
        self.assertAlmostEqual(p['data_arc_A']['value_ps'],32.284248,places=3)
        self.assertAlmostEqual(p['enable_arc_B']['value_ps'],1826.792236,places=2)
        self.assertFalse(p['data_arc_A']['extrapolation'])
        self.assertTrue(p['enable_arc_B']['extrapolation'])
        self.assertTrue(self.x['no_delay_calculator_or_Liberty_tuning'])
    def test_actual_graph_merge_semantics_pinned(self):
        s=(BASE/'inputs/OpenSTA_GraphDelayCalc_aa598a2f14.cc').read_text()
        self.assertIn('delayGreater(gate_slew, drvr_slew, slew_min_max, this)',s)
        self.assertIn('graph_->setSlew(drvr_vertex, drvr_rf, ap_index, gate_slew)',s)
    def test_544_bits_have_two_real_enable_sink_pins_each(self):
        for case in self.x['cases'].values():
            self.assertEqual(len(case['controls']),2)
            for c in case['controls']:
                self.assertEqual(c['sink_count'],1088)
                self.assertEqual(sum(s['pin']=='B' for s in c['sinks']),544)
                self.assertEqual(sum(s['pin']=='A2' for s in c['sinks']),544)
                self.assertAlmostEqual(c['SS_mean_pin_cap_fF'],392.441056,places=5)
                self.assertGreater(c['source_cap_overload_ratio'],17)
    def test_finite_wire_debit_not_free_tree_or_timing_admission(self):
        for case in self.x['cases'].values():
            for c in case['controls']:
                f=c['finite_leaf_floor']
                self.assertGreater(f['positive_wire_budget_fF'],0)
                self.assertGreaterEqual(f['leaf_cells_lowerbound']*f['pin_budget_fF'],c['worst_SS_FF_pin_cap_fF'])
                self.assertTrue(f['no_complete_tree_fit_or_deadline_claim'])
        self.assertFalse(self.x['PnR_admitted'])
    def test_full_source_control_cone_not_nominal_data_arc(self):
        paths=self.x['complete_enabled_control_paths']
        self.assertEqual(len(paths),4)
        for p in paths:
            rows=p['source_FF_enable_mux_rows']
            self.assertEqual([r['master'] for r in rows],['DFFASRHQNx1_ASAP7_75t_R','NOR2xp33_ASAP7_75t_R','OAI21xp33_ASAP7_75t_R'])
            self.assertAlmostEqual(sum(r['delay_ps'] for r in rows),p['arrival_ps'],places=2)
            self.assertAlmostEqual(p['slack_ps'],2500/3-60-p['setup_ps']-p['arrival_ps'],places=2)
            self.assertGreater(rows[1]['slew_ps'],16000)
            self.assertGreater(rows[1]['load_fF'],392)
            self.assertTrue(p['overloaded_extrapolation_NOT_context_closure'])
    def test_control_not_given_macro_two_edge_exception(self):
        self.assertEqual(self.x['control_setup_edges'],1)
        self.assertEqual(self.x['macro_data_setup_edges'],2)
        self.assertTrue(all(s<0 for s in self.x['raw_control_to_capture_one_cycle_slack_ps']))
        self.assertTrue(self.x['no_new_pipeline_cycle_selected'])
    def test_cfg_register_and_final_word_schema_not_nominal_clip(self):
        c=self.x['parent_cfg_schema']
        self.assertEqual((c['CW'],c['logical_DEPTH'],c['AW']),(25,25600,15))
        self.assertIn('resettable',c['c_v'])
        self.assertIn('ONLY when ld_k==2*NSEG',c['cfg_word_final_modification'])
        self.assertTrue(c['nominal_clip_driver_not_source_proof'])
        for n in ('FIX_SECOND_ROW_INDEX','WAKE_REG','GRADUAL_RNE'):
            self.assertEqual(self.x['parent_selected_passthrough'][n],1)
    def test_external_source_receipts_and_WIP_label(self):
        r=json.loads((BASE/'inputs/receipts.json').read_text())
        for v in r.values():self.assertEqual(hashlib.sha256((BASE/'inputs'/v['copy']).read_bytes()).hexdigest(),v['sha256'])
        self.assertTrue(r['Maxwell_parent_IO']['uncommitted_WIP_NOT_admitted_source_pin'])
    def test_all_raw_library_units_thresholds_checked(self):
        u=self.x['unit_identity']
        self.assertEqual(len(u['checked_sources']),12)
        self.assertEqual((u['time'],u['capacitance'],u['slew_derate']),('1ps','1fF',1))
        for r in u['checked_sources']:
            self.assertEqual(hashlib.sha256((ROOT/r['source']).read_bytes()).hexdigest(),r['sha256'])
if __name__=='__main__':unittest.main()
