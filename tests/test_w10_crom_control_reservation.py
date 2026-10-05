from decimal import Decimal as D
import json
from pathlib import Path
import unittest


class CROMControlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.x=json.loads(Path('results/uarch/w10_crom_control_reservation_r1/budget.json').read_text())

    def test_operands_do_not_absorb_control_tags(self):
        self.assertEqual(self.x['operand_bits_only'],131072)
        self.assertEqual(self.x['tag_state_FF_bits_additional_to_operands'],5372)
        self.assertEqual(self.x['control_raw_capture_FF_bits'],4384)
        self.assertEqual(self.x['control_catalog_tag_reservation']['macros'],16)
        self.assertGreater(D(self.x['control_catalog_tag_reservation']['ungated_clock_W']),0)

    def test_each_credit_route_scenario_pays_all_state_and_clocks(self):
        self.assertEqual([r['credits'] for r in self.x['credit_scenarios']],[2,4,128])
        for r in self.x['credit_scenarios']:
            inventory=r['state_bits_by_purpose']
            self.assertEqual(inventory['route_pipeline_bits'],75*1024)
            self.assertEqual(inventory['TX_fullpacket_bits'],r['credits']*672)
            self.assertEqual(inventory['RX_landing_fullpacket_bits'],r['credits']*672)
            self.assertEqual(r['credit_route_reservation']['FF_bits'],sum(inventory.values()))
            self.assertGreater(D(r['credit_route_reservation']['ungated_clock_W']),0)
            self.assertEqual(r['buffer_plus_catalog_plus_credit_route_FF_bits'],475402+9756+sum(inventory.values()))

    def test_unqualified_provider_never_receives_admission(self):
        self.assertFalse(self.x['physical_admission'])
        self.assertFalse(self.x['actual_provider_instantiated'])
        self.assertFalse(self.x['historical_per_lane_20bit_address_allocation']['actual_implementation_qualified'])
        for r in self.x['credit_scenarios']:self.assertFalse(r['whole_CROM_budget_ready'])
        self.assertEqual(self.x['source_pins']['control_calendar']['commit'],'bc1ec8b8f')


if __name__=='__main__':unittest.main()
