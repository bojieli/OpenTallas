import json
from decimal import Decimal as D
from pathlib import Path
import unittest
from tools.w10_crom_control_reservation import read
class ActualStageBudgetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.x=json.loads(Path('results/uarch/w10_crom_actual_stage_budget_r1/budget.json').read_text())
    def test_sources_and_catalog_dimensions(self):
        self.assertEqual(len(self.x['cases']),12)
        for r in self.x['cases']:
            pin=self.x['source_pins'][str(r['parameter_banks'])];c,_=read(pin['commit'],pin['path'])
            if r['parameter_banks']!=45:self.assertEqual(r['macro_count'],c['regular_element']['total_macros_per_home'])
            else:self.assertEqual(r['catalog_banks'],c['regular_catalog']['existing4096x274_catalog_macros'])
            self.assertEqual(r['fresh_declared_reservation']['FF_bits'],sum(r['FF_by_role'].values()))
            self.assertEqual(r['FF_by_role']['retained_staging'],475402)
            self.assertEqual(r['landing_selector_MUX2_bits'],16*(r['landing_words']-1)*32)
    def test_actual_calendar_not_scaled_power_or_latency(self):
        r={c['parameter_banks']:c for c in self.x['cases'] if c['credits']==128}
        self.assertEqual(D(r[45]['finite_coefficient_only_calendar_us']),D('199.655'))
        self.assertGreater(D(r[6]['finite_coefficient_only_calendar_us']),D(r[16]['finite_coefficient_only_calendar_us']))
        self.assertEqual(self.x['fastest_enumerated_coefficient_only_banks'],45)
        self.assertEqual(self.x['gamma_three_bank_read_floor_before_conflicts_cycles'],569)
        self.assertEqual(self.x['small_macro_power_transfer_credit'],0)
    def test_slot_failure_is_chosen_inventory_not_minimum(self):
        for r in self.x['cases']:
            self.assertGreater(D(r['exclusive_SU_slot_area_deficit_mm2']),0)
            self.assertFalse(r['physical_admission'])
            self.assertFalse(r['effective_fulltoken_latency_qualified'])
        self.assertFalse(self.x['physical_admission'])
        self.assertFalse(self.x['L1_complete_image_valid'])
        self.assertFalse(self.x['actual_physical_catalog_published'])
        self.assertIsNone(self.x['whole_point_power_margin_W'])
        self.assertIsNone(self.x['whole_token_latency_cycles'])
