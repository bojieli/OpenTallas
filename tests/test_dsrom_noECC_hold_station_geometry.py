import gzip,hashlib,json,re,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import dsrom_noECC_hold_station_geometry as g
BASE=ROOT/'results/uarch/dsrom_noECC_hold_station_geometry_20261002'
class HoldGeometry(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.x=json.loads((BASE/'model.json').read_text());cls.source=json.loads((g.ENABLE/'model.json').read_text())
    def test_exact_frozen_source_and_units(self):
        self.assertEqual(self.x['source_enable_model_sha256'],g.sha(g.ENABLE/'model.json'))
        self.assertEqual(self.x['DBU_per_um'],1000)
        self.assertEqual(self.x['candidate'],self.source['candidate'])
    def test_six_already_priced_cells_and_no_ff_or_latency_change(self):
        for c in self.x['cases'].values():
            self.assertEqual(len(c['placements']),6)
            self.assertEqual(sum(p['master'].startswith('BUFx4_') for p in c['placements']),4)
            self.assertEqual(sum(p['master'].startswith('BUFx24_') for p in c['placements']),2)
            self.assertEqual(c['added_cells_beyond_8d_price'],0);self.assertEqual(c['added_capture_cycles'],0)
    def test_independent_station_bodies_and_row_sites(self):
        for c in self.x['cases'].values():
            region=c['station_region_DBU']
            for i,p in enumerate(c['placements']):
                b=p['bbox_DBU'];self.assertTrue(region[0]<=b[0]<b[2]<=region[2] and region[1]<=b[1]<b[3]<=region[3])
                self.assertEqual(b[0]%54,0);self.assertEqual(b[1]%270,0)
                for q in c['placements'][i+1:]:self.assertFalse(g.overlap(b,q['bbox_DBU']))
            self.assertFalse(c['body_collisions']);self.assertFalse(c['PG_rail_projection_failures'])
    def test_literal_pin_translation_independently(self):
        for c in self.x['cases'].values():
            for record in c['pins']:
                p=next(p for p in c['placements'] if p['instance']==record['instance']);master=self.source['physical_master_templates'][p['master']]
                self.assertEqual(record['rectangles'],g.pin_rects(p,master,record['pin']))
    def test_native_pin_landing_contained_and_real_M2_minarea_extension(self):
        for c in self.x['cases'].values():
            self.assertEqual(len(c['hold_pin_native_landing_checks']),8)
            for p in c['hold_pin_native_landing_checks']:
                self.assertTrue(p['literal_M1_landing_contained']);self.assertFalse(p['OBS_PG_intersection_failures'])
                self.assertGreaterEqual(p['M2_minimum_landing_union_length_DBU']*18,666)
                self.assertFalse(p['EOL_spacing_cut_spacing_full_union_qualified'])
            self.assertGreater(sum(p['M2_minarea_extension_DBU'] for p in c['hold_pin_native_landing_checks']),0)
    def test_wire_lengths_count_geometry_and_positive_lower_access(self):
        for c in self.x['cases'].values():
            for h in c['hold_wire_constructions']:
                self.assertAlmostEqual(h['M3_wire_um'],sum(g.length(s) for s in h['M3_segments_DBU'])/1000)
                self.assertGreater(h['M2_wire_um'],0)
                self.assertTrue(h['frozen_nominal_wire_upper_violated'])
            self.assertEqual(c['frozen_nominal_hold_wire_screen'],'FAIL')
    def test_connected_hold_shape(self):
        for c in self.x['cases'].values():
            for h in c['hold_wire_constructions']:
                # Native segments overlap at corners; all segments belong to
                # one component. A disconnected nominal meander would fail.
                segs=h['M3_segments_DBU'];pending=set(range(1,len(segs)));joined={0}
                def touch(a,b):
                    box=lambda s:(min(p[0] for p in s),min(p[1] for p in s),max(p[0] for p in s),max(p[1] for p in s))
                    aa,bb=box(a),box(b);return aa[0]<=bb[2] and bb[0]<=aa[2] and aa[1]<=bb[3] and bb[1]<=aa[3]
                while pending:
                    found={p for p in pending if any(touch(segs[p],segs[j]) for j in joined)}
                    self.assertTrue(found);joined|=found;pending-=found
    def test_source_grid_two_plane_routes_and_wire_bounds(self):
        for c in self.x['cases'].values():
            self.assertFalse(c['inter_net_same_plane_guard_conflicts']);self.assertFalse(c['M8_PG_exclusion_collisions'])
            for p in c['D_distribution_paths']:
                self.assertEqual(len(p['sinks']),4)
                self.assertLess(p['total_L1_wire_um'],400);self.assertLess(p['maximum_pin_to_pin_L1_upper_um'],200)
                for s in p['route_segments']:
                    a,b=s['points_DBU']
                    if s['layer']=='M7':self.assertEqual(a[0],b[0]);self.assertEqual((a[0]-16)%64,0)
                    else:self.assertEqual(a[1],b[1]);self.assertEqual((a[1]-116)%80,0)
    def test_all_M8_negative_not_overwritten_or_adopted(self):
        x=json.loads((BASE/'negative_all_M8_geometry.json').read_text())
        self.assertEqual(x['state'],'FAIL_SAME_LAYER_D_NET_SHORTS')
        self.assertTrue(all(len(c['shorts'])==3 for c in x['cases'].values()))
    def test_loaded_root_table_and_positive_conditional_timing(self):
        for c in self.x['cases'].values():
            for p in c['D_distribution_paths']:
                self.assertGreater(p['remaining_native_via_cap_budget_fF'],0)
                self.assertFalse(p['native_via_RC_provider_qualified'])
            for role,t in c['endpoint_aware_hold_timing'].items():
                self.assertGreater(t['ss']['SS_remaining_ps'],0);self.assertGreater(t['ff']['FF_hold_remaining_ps'],0)
                self.assertEqual(t['ss']['root_input_load_budget_fF'],46.08)
                self.assertLessEqual(t['ss']['sink_data_slew_bound_ps'],320)
                self.assertTrue(t['ss']['native_via_extra_resistance_budget_NOT_bound'])
    def test_no_build_or_selector_PG_transfer(self):
        self.assertFalse(self.x['G0_physical_build_admitted']);self.assertFalse(self.x['new_engine_RTL']);self.assertFalse(self.x['new_PnR'])
        self.assertTrue(any('clock' in s for s in self.x['negative_criteria']))
    def test_native_vias_retain_actual_cut_planes(self):
        v=self.x['physical_native_via_templates']
        self.assertEqual({r['layer'] for r in v['VIA12']},{'M1','M2','V1'})
        self.assertEqual({r['layer'] for r in v['VIA78']},{'M7','M8','V7'})
    def test_reset_constraints_are_literal_pin_specific(self):
        from dsrom_noECC_liberty import cell_bodies
        for corner,c in self.x['source_RESETN_constraints'].items():
            body=cell_bodies(corner)['DFFASRHQNx1_ASAP7_75t_R']
            self.assertIn(c['literal_RESETN_pin'],body)
            self.assertEqual(hashlib.sha256(c['literal_RESETN_pin'].encode()).hexdigest(),c['literal_RESETN_pin_sha256'])
            self.assertFalse(c['provider_reset_edges_bound'])
    def test_source_policy_does_not_gain_new_xp_cells(self):
        import fnmatch
        for c in self.x['cases'].values():
            for p in c['placements']:
                self.assertFalse(any(fnmatch.fnmatch(p['master'],pat) for pat in self.source['actual_DONT_USE_patterns']))
if __name__=='__main__':unittest.main()
