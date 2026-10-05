import json,sys,unittest,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import dsrom_noECC_strip_clock_construction as g
from dsrom_noECC_hold_station_geometry import pin_rects,length
class StripClock(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.x=json.loads((g.BASE/'model.json').read_text());cls.e=json.loads(g.ENABLE.read_text());cls.h=json.loads(g.HOLD.read_text())
    def test_exact_candidate_sources_and_policy(self):
        self.assertEqual(self.x['candidate'],self.e['candidate']);self.assertEqual(self.x['source_hold_model_sha256'],g.sha(g.HOLD));self.assertEqual(self.x['source_enable_model_sha256'],g.sha(g.ENABLE))
        self.assertEqual(self.x['period_ps'],2500/3);self.assertEqual(self.x['SS_setup_uncertainty_ps'],60);self.assertEqual(self.x['FF_hold_uncertainty_ps'],25)
    def test_no_dropped_capture_bits_or_unmatched_extra_stage(self):
        for case,c in self.x['cases'].items():
            expected={p['instance'] for p in self.e['cases'][case]['placements'] if p['role'] in ('control_state_replica','retained_capture_FF')}
            # Independent use of source strip bit records when the role is not
            # specified by the earlier placement producer.
            from dsrom_noECC_enable_distribution import trace
            _,ps,groups,_=trace(case);expected={v['FF'] for a in groups.values() for v in a}|{p['instance'] for p in self.e['cases'][case]['placements'] if p['role']=='control_state_replica'}
            actual=[s['instance'] for n in c['clock_leaf_nets'] for s in n['sinks']]
            self.assertEqual(len(actual),1100);self.assertEqual(len(set(actual)),1100)
            self.assertEqual(set(actual),expected|{p['instance'] for p in c['retained_original_scalar_placements']});self.assertEqual(len(expected),1096)
            self.assertEqual(c['matching_clock_levels_local_root_to_capture'],2)
            self.assertTrue(c['source_original_scalar_clock_route_constructed'])
    def test_clock_tree_topology_has_one_parent_per_leaf(self):
        for c in self.x['cases'].values():
            leafs={n['source']['instance'] for n in c['clock_leaf_nets']}
            sinks=[s['instance'] for n in c['clock_spine_nets'] for s in n['sinks']]
            self.assertEqual(set(sinks),leafs);self.assertEqual(len(sinks),len(leafs));self.assertEqual(len(leafs),69)
    def test_legal_disjoint_sites_and_positive_area(self):
        for c in self.x['cases'].values():
            self.assertEqual(c['clock_buffer_count'],73);self.assertFalse(c['body_collisions']);self.assertFalse(c['PG_rail_projection_failures'])
            for p in c['new_clock_buffer_placements']+c['retained_original_scalar_placements']:
                self.assertEqual(p['bbox_DBU'][0]%54,0);self.assertEqual(p['bbox_DBU'][1]%270,0)
            self.assertAlmostEqual(c['clock_cell_area_um2'],73*.10206);self.assertEqual(c['credit_against_other_Maxwell_clock_cells'],0)
    def test_all_literal_pins_independent_translation(self):
        for case,c in self.x['cases'].items():
            placements={p['instance']:p for p in self.e['cases'][case]['placements']+c['new_clock_buffer_placements']+c['retained_original_scalar_placements']}
            for n in c['clock_leaf_nets']+c['clock_spine_nets']:
                for s in [n['source']]+n['sinks']:
                    p=placements[s['instance']];rects=pin_rects(p,self.e['physical_master_templates'][p['master']],s['pin'])
                    self.assertIn(s['literal_rectangle'],rects)
    def test_positive_rc_and_finite_joint_via_budget(self):
        for c in self.x['cases'].values():
            for n in c['clock_leaf_nets']+c['clock_spine_nets']:
                self.assertGreater(n['access_L1_um'],0)
                for v in n['corners'].values():
                    self.assertGreater(v['wire_cap_fF'],0);self.assertGreater(v['wire_RC_upper_ps'],0)
                    self.assertGreater(v['native_via_C_budget_fF'],0);self.assertGreater(v['native_via_extra_R_budget_kohm_at_full_C_budget'],0)
                    self.assertAlmostEqual(v['native_via_C_budget_fF']+v['total_cap_before_native_vias_fF'],34.56)
                    self.assertLessEqual(v['output_slew_plus_ln10RC_ps'],320);self.assertFalse(v['native_via_R_C_included'])
    def test_upper_planes_disjoint_from_existing_D_and_PG(self):
        for c in self.x['cases'].values():
            self.assertFalse(c['upper_plane_PG_via_exclusion_intersections']);self.assertFalse(c['upper_plane_clock_and_D_inter_net_guard_conflicts'])
            for n in c['clock_spine_nets']:
                for s in n['segments']:self.assertEqual((s['points_DBU'][0][0]-16)%64,0)
    def test_every_actual_spine_tap_projection_is_connected(self):
        for c in self.x['cases'].values():
            for n in c['clock_spine_nets']:
                a,b=n['segments'][0]['points_DBU']
                for pin in [n['source']]+n['sinks']:
                    self.assertLessEqual(a[1],pin['point_DBU'][1]);self.assertGreaterEqual(b[1],pin['point_DBU'][1])
                self.assertAlmostEqual(n['layer_wire_um']['M7'],length([a,b])/1000)
    def test_exact_original_source_fanout_and_reset_scope(self):
        for c in self.x['cases'].values():
            self.assertEqual(len(c['source_original_QN_fanout_contracts']),4)
            self.assertTrue(all(v['retained_sinks'] for v in c['source_original_QN_fanout_contracts']))
            self.assertEqual(len(c['reset_literal_endpoints']),6);self.assertFalse(c['reset_waveform_provider_bound'])
            self.assertAlmostEqual(c['source_RESETN_constraints']['ff']['FF_removal_with25_hold_and25_skew_ps'],117.5064)
    def test_no_physical_credit_or_selector_PG_transfer(self):
        self.assertFalse(self.x['physical_build_admitted']);self.assertEqual(self.x['added_capture_edges'],0)
        self.assertEqual(self.x['selector_successor']['commit'],'3ea65964199521f67724386dfd59c184afe9a745');self.assertTrue(self.x['selector_successor']['element_PG_not_transferred'])
if __name__=='__main__':unittest.main()
