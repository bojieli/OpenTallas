import json
from pathlib import Path
import sys
import unittest
from unittest import mock
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import uarch_topk_finite_track_turn_model as M
class FixedTurns(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.model=M.build()
    def test_byte_exact_model(self):
        self.assertEqual(self.model,json.loads((M.BASE/'model_r2.json').read_bytes()))
    def test_fixed_shape(self):
        m=self.model;self.assertEqual(m['selector_state_bits'],698354)
        self.assertEqual(m['selector_slot_DBU'],[1000000,8953200,3125440,9745920])
        self.assertEqual(m['signal_plus_clock_reset_pins'],4212)
        self.assertEqual(m['fixed_geometry'],{'CB':14,'DIG':8,'LDW':4,'N':4,'NBIN':256,'NMAX':2048,'P':64,'PF':64})
    def test_unique_pins_and_layer_tracks(self):
        a=self.model['assignments'];self.assertEqual(len({e['pin'] for e in a}),4212)
        self.assertEqual(len({(e['horizontal_layer'],e['horizontal_y_DBU']) for e in a}),4212)
        self.assertEqual(len({(e['vertical_layer'],e['vertical_x_DBU']) for e in a}),4212)
        self.assertEqual(sum(e['pin']=='clock' for e in a),1);self.assertEqual(sum(e['pin']=='reset' for e in a),1)
    def test_per_tier_capacity_and_transfer(self):
        m=self.model;self.assertEqual(m['tier_half_pool_capacity'],{'M2':2352,'M4':1890,'M3':2430,'M5':1822})
        self.assertEqual(m['mandatory_M4_to_M3_tier_transfer_in_this_half_pool_mapping'],38)
        self.assertEqual(m['remaining_half_pool_tracks'],{'horizontal':30,'vertical':40})
        for layers in ['allocated_horizontal','allocated_vertical']:
            for l,n in m[layers].items():self.assertLessEqual(n,m['tier_half_pool_capacity'][l])
    def test_vias_follow_actual_layer_pairs(self):
        for e in self.model['assignments']:
            self.assertEqual(e['turn_via'],{('M2','M3'):'VIA23',('M4','M3'):'VIA34',('M4','M5'):'VIA45'}[e['horizontal_layer'],e['vertical_layer']])
        self.assertEqual(sum(e['turn_via']=='VIA34' for e in self.model['assignments']),38)
    def test_turn_spacing_control(self):
        self.assertTrue(self.model['turn_screen_pass'])
        bad=[{'pin':'a','bbox':[0,0,40,40]},{'pin':'b','bbox':[39,39,79,79]}]
        self.assertEqual(M.overlaps(bad)['pairs'],1)
        self.assertEqual(M.overlaps([bad[0],{'pin':'b','bbox':[40,40,80,80]}])['pairs'],0)
    def test_reserve_not_borrowed(self):
        self.assertEqual(M.selected_half(list(range(7))),[0,2,4])
        self.assertFalse(self.model['pin_aliasing'])
    def test_route_price_replaces_rectangle_lowerbound(self):
        m=self.model;p=m['source_transport_price'];route=m['full_allocated_lane_path']
        self.assertEqual(route['wireonly_segments_each_direction'],20)
        self.assertEqual(p['additional_cycles_per_call'],43)
        self.assertEqual(p['additional_FF_bits'],90555)
        self.assertEqual(p['ninecall_additional_cycles'],387)
        self.assertEqual(p['retirement_extra_edges'],p['formed_VM_write_delay_edges'])
        self.assertAlmostEqual(p['latest_owner_plus_transport_FF_floor_mm2']-p['latest_owner_screen_already_including_corridor_mm2'],90555*0.2916/0.5/1e6)
    def test_finite_station_coordinates_are_contained_not_cell_placement(self):
        for entry in self.model['assignments']:
            stations=M.station_coordinates(entry,3125440,16000000,20)
            self.assertEqual(len(stations),19)
            path=[[3125440,entry['horizontal_y_DBU']]]+stations+[[entry['vertical_x_DBU'],16000000]]
            lengths=[abs(a[0]-b[0])+abs(a[1]-b[1]) for a,b in zip(path,path[1:])]
            self.assertAlmostEqual(min(lengths),max(lengths),places=6)
            self.assertLessEqual(max(lengths)/1000,753.27945+1e-9)
            for x,y in stations:
                self.assertTrue((3125440<=x<=11149840 and 8953200<=y<=9134640) or
                                (10974880<=x<=11149840 and 8953200<=y<=16000000))
        self.assertFalse(self.model['corridor_centerline']['actual_stations_placed'])
    def test_archive_only_origins(self):
        with mock.patch.object(M.F.A.SourceArchive,'commit_available',side_effect=AssertionError('no git probe')):
            self.assertEqual(M.build(),self.model)
    def test_no_false_physical_credit(self):
        m=self.model;self.assertFalse(m['actual_selector_PG_overlay_bound'])
        self.assertFalse(m['LEF58_cut_corner_EOL_and_pin_escape_checked'])
        self.assertFalse(m['actual_clock_tree_and_slew_checked'])
        self.assertFalse(m['G0']['RTL_admitted']);self.assertFalse(m['G0']['PR_admitted'])
        self.assertEqual(m['jobs_launched'],0);self.assertEqual(m['new_PVE2_PVE3_jobs'],0)
if __name__=='__main__':unittest.main()
