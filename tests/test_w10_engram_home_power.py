from decimal import Decimal as D
import json
from pathlib import Path
import unittest


class EngramPowerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.x=json.loads(Path('results/uarch/w10_engram_home_power_r1/budget.json').read_text())

    def test_complete_source_inventory_no_active_home_discount(self):
        self.assertEqual(len(self.x['homes']),96)
        self.assertEqual(sum(h['macros'] for h in self.x['homes']),1500067)
        self.assertEqual(sum(h['ungated_priced_reservation']['FF_bits'] for h in self.x['homes']),2073575326)
        total=sum(D(h['ungated_priced_reservation']['ungated_clock_W']) for h in self.x['homes'])
        self.assertEqual(total,D(self.x['all96_component_totals_W']['ungated_clock_W']))
        self.assertGreater(total,D(41000))

    def test_actual_HQN_type_area_and_held_state_mux(self):
        self.assertEqual(self.x['storage_cell_type'],'DFFHQNx1_ASAP7_75t_R')
        self.assertEqual(D(self.x['typed_HQN_area_um2']),D('.2916'))
        for h in self.x['homes']:
            p=h['ungated_priced_reservation']
            self.assertEqual(p['total_NAND2_cells'],4*(p['FF_bits']+h['response_MUX2_bits'])+2*h['request_demux_gate_bit_equivalents'])
            self.assertGreater(D(p['all_state_leakage_upper_W']),0)

    def test_area_clock_bounds_do_not_erase_geometry_or_provider_failures(self):
        self.assertFalse(self.x['physical_admission'])
        self.assertFalse(self.x['retained_hub_placement_fit'])
        self.assertFalse(self.x['standalone_table_home_floorplan_qualified'])
        self.assertEqual(self.x['hub_removal_credit'],0)
        for h in self.x['homes']:self.assertFalse(h['clock_or_data_physical_minimum_claim'])
        self.assertEqual(self.x['root_stop_credit'],0)


if __name__=='__main__':unittest.main()
