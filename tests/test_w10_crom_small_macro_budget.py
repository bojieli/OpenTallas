import json
from decimal import Decimal as D
from pathlib import Path
import unittest
from tools.w10_crom_small_macro_budget import macro_profile,price
from tools.w10_crom_control_reservation import read
class SmallMacroBudgetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.x=json.loads(Path('results/uarch/w10_crom_small_macro_budget_r1/budget.json').read_text())
        cls.p,_=read('e79394b1c','results/uarch/w10_q_power_envelope_r1/power.json');cls.k,_=read('fea811df4','results/uarch/w10_q_existing_icg_r1/clock.json');cls.a,_=read('6da3c7a60','results/uarch/w10_q_elaboration_inventory_r1/construction.json')
    def test_own_macro_liberty_and_lef(self):
        small=macro_profile('ot_rom_1024x72_m8');big=macro_profile('ot_rom_4096x274_m8')
        self.assertEqual(small,self.x['small_macro_profile']);self.assertEqual(big,self.x['catalog_macro_profile'])
        self.assertEqual(D(small['area_um2']),D('762.35904'))
        self.assertEqual(D(small['CLK_internal_cycle_fJ']),D('628.6649'))
        self.assertEqual(D(big['CLK_internal_cycle_fJ']),D('8425.6441'))
        correct=price(475402,0,[(135,small),(4,big)],self.p,self.k,self.a)
        wrong=price(475402,0,[(139,big)],self.p,self.k,self.a)
        self.assertNotEqual(correct['ungated_clock_W'],wrong['ungated_clock_W'])
        self.assertGreater(D(wrong['macro_area_mm2']),D(correct['macro_area_mm2']))
    def test_all_endpoints_and_padding_charged(self):
        self.assertEqual(self.x['extra_macro_clock_endpoints_vs45'],90)
        self.assertTrue(self.x['padding_output_pin_loads_charged'])
        for r in self.x['rows']:
            p=r['fresh_mixed_macro_reservation']
            self.assertEqual(p['macro_clock_endpoints'],139)
            self.assertEqual(r['FF_by_role']['retained_staging'],475402)
            self.assertEqual(p['FF_bits'],sum(r['FF_by_role'].values()))
            self.assertGreater(D(r['exclusive_SU_slot_area_deficit_mm2']),0)
    def test_no_depth_adoption_or_power_margin(self):
        for k in ('explicit_depth_alternative_adopted','baseline4096_depth_rule_preserved','physical_admission','actual_power_qualified','complete_inventory','SS_contextual_capture_qualified'):self.assertFalse(self.x[k])
        self.assertEqual(self.x['historical_power_subtraction_W'],0)
        self.assertIsNone(self.x['whole_point_power_margin_W'])
