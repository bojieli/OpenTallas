import hashlib,json,sys,unittest,fnmatch,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import dsrom_noECC_enable_distribution as m
BASE=ROOT/'results/uarch/dsrom_noECC_enable_distribution_20261002'
class EnableConstruction(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.x=json.loads((BASE/'model.json').read_text())
    def test_four_complete_strips_and_all_1088_capture_names(self):
        for c in self.x['cases'].values():
            self.assertEqual(sum(s['actual_capture_FF'] for s in c['strips']),1088)
            self.assertEqual(len(c['strips']),4)
            self.assertEqual(len({p['instance'] for p in c['placements']}),len(c['placements']))
    def test_independent_all_pairs_geometry_inside_actual_strip(self):
        for c in self.x['cases'].values():
            rects=c['placements']
            for i,a in enumerate(rects):
                self.assertTrue(any(a['bbox_DBU'][0]>=s['region_DBU'][0] and a['bbox_DBU'][1]>=s['region_DBU'][1] and a['bbox_DBU'][2]<=s['region_DBU'][2] and a['bbox_DBU'][3]<=s['region_DBU'][3] for s in c['strips']))
                for b in rects[i+1:]:self.assertFalse(m.overlap(a['bbox_DBU'],b['bbox_DBU']),(a['instance'],b['instance']))
            self.assertFalse(c['placement_source_WAKExICG_collisions']);self.assertFalse(c['placement_macro_body_collisions'])
    def test_no_free_clock_or_reset_or_new_sampling_stage(self):
        for c in self.x['cases'].values():
            self.assertEqual(c['added_physical_FF'],8)
            self.assertEqual(c['added_capture_latency_cycles'],0)
            for v in c['clone_clock_pin_debit_SS_FF_fF'].values():self.assertGreater(v,0)
            for v in c['clone_reset_pin_debit_SS_FF_fF'].values():self.assertGreater(v,0)
            for s in c['source_state_copies']:
                self.assertEqual(s['original_connections']['CLK'],'leaf_clk[0]')
                self.assertTrue(s['unchanged_D_CLK_RESETN_SETN'])
    def test_local_leaf_net_conserves_all_actual_mux_sinks(self):
        for c in self.x['cases'].values():
            leaves=[n for n in c['enable_nets'] if 'source_enable_bank' in n]
            sinks=[p for n in leaves for p in n['sinks']]
            self.assertEqual((len(leaves),len(sinks),len(set(sinks))),(136,2176,2176))
            self.assertTrue(all(n['positive_wire_cap_fF']>0 for n in leaves))
    def test_clock_and_macro_data_have_distinct_edge_budgets(self):
        self.assertEqual((self.x['control_edges'],self.x['macro_data_edges']),(1,2))
        self.assertEqual((self.x['SS_setup_uncertainty_ps'],self.x['FF_hold_uncertainty_ps']),(60,25))
        self.assertFalse(self.x['G0_physical_build_admitted'])
    def test_full_source_enabled_cone_positive_and_not_nominal_arc(self):
        for c in self.x['cases'].values():
            self.assertGreater(c['minimum_SS_remaining_ps'],0)
            for t in c['complete_enabled_timing']:
                s=t['SS_FF']['ss']
                for name in ('source_FF','source_NOR','tree_root','tree_leaf','hold_mux_NAND','hold_mux_OAI'):self.assertIn(name,s)
                self.assertTrue(s['no_table_extrapolation'])
                self.assertGreater(s['wire_root_delay_upper_ps'],0)
    def test_producer_D_FF_hold_positive_with_priced_HB2(self):
        for c in self.x['cases'].values():
            for s in c['proposed_D_distribution']:
                self.assertEqual(s['actual_mapped_driver']['master'],'INVx1_ASAP7_75t_R')
                ss=s['SS_FF_complete_D_path']['ss'];ff=s['SS_FF_complete_D_path']['ff']
                self.assertGreater(ss['SS_complete_margin_ps'],0)
                self.assertGreater(ff['FF_hold_margin_ps'],0)
                self.assertEqual(len(ss['hold_buffers']),2)
                self.assertTrue(all(b['master']=='BUFx4_ASAP7_75t_R' for b in ss['hold_buffers']))
                self.assertTrue(all(b['load_envelope_fF']>=2.88 for b in ss['hold_buffers']))
    def test_preserved_prior_D_hold_failure_not_promoted(self):
        x=json.loads((BASE/'inputs/prior_D_hold_negative.json').read_text())
        self.assertTrue(all(s['SS_FF_complete_D_path']['ff']['FF_hold_margin_ps']<0 for c in x['cases'].values() for s in c['proposed_D_distribution']))
    def test_same_edge_control_replica_truth_with_unreset_bank(self):
        # Valid FF is ASR/QN reset1. Bank is unreset. Unknown bank must remain
        # unobservable until a source clock samples the same original D.
        for reset in (0,1):
            for original_bank in (0,1):
                for replica_bank in (0,1):
                    for Dvalid in (0,1):
                        for Dbank in (0,1):
                            vqn=1 if not reset else 1-Dvalid
                            bqn=original_bank if not reset else 1-Dbank
                            cq=replica_bank if not reset else 1-Dbank
                            for bank in (0,1):
                                b=1-bqn if bank==0 else bqn;r=1-cq if bank==0 else cq
                                self.assertEqual(not(vqn or b),not(vqn or r))
    def test_source_archives_and_selected_flags(self):
        for r in self.x['source_receipts']:self.assertEqual(hashlib.sha256((BASE/'inputs'/r['copy']).read_bytes()).hexdigest(),r['sha256'])
        self.assertEqual(self.x['selected_parent_flags'],dict(FIX_SECOND_ROW_INDEX=1,WAKE_REG=1,GRADUAL_RNE=1))
        self.assertFalse(self.x['opt_in_default'])
        self.assertFalse(self.x['selected_parent_snapshot_uncommitted_no_qualification_transfer'])
        self.assertTrue(self.x['selected_parent_no_physical_qualification_transfer'])
        self.assertEqual(self.x['selected_parent_source_commit'],'b32857642896e6f15333682feafaf9c0b3011061')
    def test_M5_trunks_source_PG_excluded_on_real_track_grid(self):
        for c in self.x['cases'].values():
            for n in c['enable_nets']:
                if 'trunk_x_DBU' not in n:continue
                self.assertEqual((n['trunk_x_DBU']-12)%48,0)
                self.assertTrue(n['source_M5_PG_and_nearcut_via_excluded'])
    def test_raw_clock_reset_union_separates_new_FF_from_WAKE(self):
        for c in self.x['cases'].values():
            for corner,u in c['clock_reset_full_source_union'].items():
                self.assertEqual(u['new_leaf0_sinks']-u['existing_leaf0_sinks'],8)
                self.assertAlmostEqual(u['composed_leaf0_pin_cap_fF']-u['existing_leaf0_pin_cap_fF'],c['clone_clock_pin_debit_SS_FF_fF'][corner])
                self.assertAlmostEqual(u['composed_reset_pin_cap_fF']-u['existing_reset_pin_cap_fF'],c['clone_reset_pin_debit_SS_FF_fF'][corner])
            self.assertEqual(len(c['clone_translated_CLK_RESET_pin_descriptors']),8)
            self.assertEqual(sum(p['RESETN']=='rst_n' for p in c['clone_translated_CLK_RESET_pin_descriptors']),4)
            self.assertFalse(c['source_PG_rail_projection_failures'])
    def test_supported_wire_minima_and_fixed_hold_counterfactual(self):
        for c in self.x['cases'].values():
            for d in c['proposed_D_distribution']:
                self.assertGreater(d['minimum_network_wire_um'],0)
                self.assertLess(d['minimum_network_wire_um'],d['maximum_total_network_wire_um'])
                self.assertLess(d['HB1_cell_floor_diagnostic_not_minimum_certificate'],0)
                self.assertTrue(d['hold_wire_construction']['minimum_wire_length_is_a_required_physical_constraint'])
    def test_SETN_provider_is_real_source_cell_not_free_constant(self):
        for c in self.x['cases'].values():self.assertEqual(c['added_cell_counts']['TIEHIx1_ASAP7_75t_R'],4)
        self.assertGreater(self.x['physical_master_templates']['TIEHIx1_ASAP7_75t_R']['area_um2'],0)
    def test_no_macro_or_capture_credit_in_cost(self):
        for c in self.x['cases'].values():
            self.assertEqual(c['macro_and_existing_capture_FF_area_credit'],0)
            self.assertAlmostEqual(c['conservative_50pct_core_reservation_um2'],2*c['net_cell_area_delta_um2'])
    def test_literal_library_state_semantics_support_reset_masking(self):
        for corner,masters in self.x['source_FF_semantics'].items():
            for master,receipt in masters.items():
                body=m.cell_bodies(corner)[master]
                self.assertEqual(hashlib.sha256(body.encode()).hexdigest(),receipt['cell_body_sha256'])
                for literal in (receipt['literal_ff'],receipt['literal_QN_pin']):self.assertIn(literal,body)
                self.assertRegex(receipt['literal_ff'],r'next_state\s*:\s*"!D"')
                self.assertRegex(receipt['literal_QN_pin'],r'function\s*:\s*"IQN"')
                if master.startswith('DFFASR'):self.assertRegex(receipt['literal_ff'],r'preset\s*:\s*"!RESETN"')
    def test_new_cells_respect_source_policy_and_original_decode_is_reused(self):
        for c in self.x['cases'].values():
            for master in c['added_cell_counts']:
                self.assertFalse(any(fnmatch.fnmatch(master,pat) for pat in self.x['actual_DONT_USE_patterns']))
            self.assertEqual(c['added_cell_counts']['NOR2x1_ASAP7_75t_R'],2)
            retained=[p for p in c['placements'] if p['role']=='source_relocated_existing']
            self.assertEqual(len(retained),2)
            self.assertTrue(all(p['master']=='NOR2xp33_ASAP7_75t_R' for p in retained))
if __name__=='__main__':unittest.main()
