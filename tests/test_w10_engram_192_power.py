from decimal import Decimal as D
import json
from pathlib import Path
import unittest

class Engram192Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.x=json.loads(Path('results/uarch/w10_engram192_power_r1/budget.json').read_text())
    def test_full_integer_inventory_and_total_clock(self):
        self.assertEqual(len(self.x['homes']),192)
        self.assertEqual(sum(h['macros'] for h in self.x['homes']),1500067)
        self.assertEqual(sum(h['priced_reservation']['FF_bits'] for h in self.x['homes']),2073429886)
        total=sum(D(h['priced_reservation']['ungated_clock_W']) for h in self.x['homes'])
        self.assertEqual(total,D(self.x['all192_component_totals_W']['ungated_clock_W']))
        self.assertGreater(total,D(41000))
    def test_uneven_shards_are_priced_from_actual_counts(self):
        a,b=self.x['homes'][0],self.x['homes'][3]
        self.assertEqual(a['macros'],8192)
        self.assertEqual(b['macros'],6675)
        self.assertGreater(D(a['clock_plus_leak_W']),D(b['clock_plus_leak_W']))
        for h in self.x['homes']:
            p=h['priced_reservation']
            self.assertEqual(p['total_NAND2_cells'],4*(p['FF_bits']+h['response_MUX2_bits'])+2*h['request_demux_AND2_bits'])
    def test_grid_screen_is_not_physical_or_power_admission(self):
        self.assertFalse(self.x['physical_admission'])
        self.assertFalse(self.x['all_other_obstacles_CTS_PG_PHY_cleared'])
        self.assertEqual(self.x['hub_removal_credit'],0)
        self.assertEqual(self.x['storage_cell_type'],'DFFHQNx1_ASAP7_75t_R')
        self.assertEqual(D(self.x['storage_area_um2']),D('.2916'))

if __name__=='__main__':unittest.main()
