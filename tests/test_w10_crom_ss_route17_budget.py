from decimal import Decimal as D
import json
from pathlib import Path
import unittest
from tools.w10_crom_ss_route17_budget import revised_roles,route_basis
class SSRoute17Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.x=json.loads(Path('results/uarch/w10_crom_ss_route17_budget_r1/budget.json').read_text())
    def test_SS_reach_integer_cover(self):
        b=self.x['route_basis'];reach=D(b['source_reach_SS_um']);distance=D(b['source_envelope_um'])
        self.assertEqual(b['forward_fast_stages'],17);self.assertEqual(b['reverse_fast_stages'],17)
        self.assertLess(reach*16,distance);self.assertGreaterEqual(reach*17,distance)
        with self.assertRaises(ValueError):route_basis({'local_manhattan_envelope_um':'8159.616'},'WIRE_REACH_SS_UM = 800.0')
    def test_all_three_routes_and_extra_FF(self):
        self.assertEqual(len(self.x['cases']),12);self.assertEqual(len(self.x['small_macro_alternative_cases']),3)
        for r in self.x['cases']+self.x['small_macro_alternative_cases']:
            s=r['FF_by_role'];self.assertEqual(s['payload_route'],17408)
            self.assertEqual(s['forward_control'],1088);self.assertEqual(s['reverse_control_plusACKserial'],1152)
            self.assertEqual(r['extra_pipeline_FF_vs11'],6912)
            p=r.get('fresh_declared_reservation',r.get('fresh_mixed_reservation'))
            self.assertEqual(p['FF_bits'],sum(s.values()))
            self.assertGreater(D(r['exclusive_SU_slot_area_deficit_mm2']),0)
        with self.assertRaises(ValueError):revised_roles({'payload_route':0,'forward_control':0,'reverse_control_plusACKserial':0},17)
    def test_old_calendar_and_fit_never_qualify(self):
        for r in self.x['cases']+self.x['small_macro_alternative_cases']:
            self.assertIsNone(r['route17_finite_calendar_us'])
            self.assertTrue(r['old11_calendar_not_current']);self.assertFalse(r['physical_admission'])
        self.assertFalse(self.x['actual_1152bit_bus_routing_reach_proven'])
        self.assertFalse(self.x['actual_128bit_CDC_binding'])
        self.assertIsNone(self.x['actual_128bit_CDC_extra_state_bits'])
        self.assertFalse(self.x['complete_inventory']);self.assertIsNone(self.x['whole_point_power_margin_W'])
