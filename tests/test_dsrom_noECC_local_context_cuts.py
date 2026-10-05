import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from dsrom_noECC_local_context_cuts import build,pdn
class LocalCuts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.m=build()
    def test_frame_growth_and_no_clock_cell_doublecount(self):
        q=self.m['cases']['q'];self.assertEqual(q['outline_DBU'],[0,0,510840,151200])
        self.assertAlmostEqual(q['residual_after_pin_buffer_floor_um2'],399.3753599547,places=6)
        for c in self.m['cases'].values():self.assertTrue(c['no_WAKEDFF_or_ICG_doublecharge'])
    def test_expanded_PDN_reaches_actual_q_bottom(self):
        q=self.m['cases']['q'];self.assertEqual(max(s['bbox_DBU'][3] for s in q['expanded_source_PDN_rectangles']),151200)
        self.assertTrue(any(s['bbox_DBU'][1]>=144720 for s in q['expanded_source_PDN_rectangles'] if s['layer']=='M2'))
    def test_bijection_from_actual_FF_through_inverter_toENA(self):
        for c in self.m['cases'].values():
            b=c['actual_WAKEDFF_to_leafENA_bijection'];self.assertEqual(set(b),set(range(8)));self.assertEqual(len(set(b.values())),8)
            self.assertEqual(len(c['source_clock_cell_slots']),16)
    def test_cut_lanes_are_disjoint_and_spacing_excluded(self):
        for c in self.m['cases'].values():
            lanes=c['clock_cut_lanes'];self.assertEqual(len(lanes),6)
            ys=sorted(s['center_y_DBU'] for s in lanes)
            self.assertTrue(all(b-a>=144 for a,b in zip(ys,ys[1:])))
            for s in lanes:
                for v in c['source_via_enclosures_near_cut']:
                    if v['layer']=='M4':self.assertFalse(v['bbox_DBU'][1]-96<=s['center_y_DBU']<=v['bbox_DBU'][3]+96)
    def test_construction_is_prebuild_not_installed_claim(self):
        self.assertTrue(self.m['installed_CTS_PDN_not_prebuild_requirement']);self.assertFalse(self.m['PnR_admitted'])
    def test_macro_ss_clkq_is_full_loaded_table_not_744_headline(self):
        t=self.m['actual_macro_timing_source'];self.assertAlmostEqual(t['ss']['clkQ_max_ps'],839.0934)
        self.assertAlmostEqual(t['ss']['minimum_period_ps'],711.852)
        self.assertAlmostEqual(t['constraints']['SS_data_budget_before_capture_setup_mux_wire_and_skew_ps'],767.5732666667)
        self.assertEqual(t['constraints']['capture_to_lane_setup_edges'],1)
if __name__=='__main__':unittest.main()
