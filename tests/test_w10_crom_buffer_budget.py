import json
from pathlib import Path
from decimal import Decimal as D
import unittest


class CROMBudgetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.x = json.loads(Path('results/uarch/w10_crom_buffer_budget_r1/budget.json').read_text())

    def test_fp32_gamma_capacity_and_single_home_refill(self):
        self.assertEqual(self.x['storage_bits_by_purpose']['two_gamma_families'], 2*5*1024*32)
        self.assertEqual(self.x['cold_gamma_payload_bits_per_rank'], 81*5120*32)
        self.assertEqual(self.x['total_storage_bits'], 450826)

    def test_finite_writes_clocks_and_data_are_charged(self):
        self.assertEqual(self.x['MUX2_bits_by_purpose']['storage_write_enable'], 450826)
        self.assertGreater(D(self.x['ungated_clock_W']), D(6))
        self.assertGreater(D(self.x['data_pin_upper_W']), D(0))
        total = sum(D(self.x[k]) for k in ('ungated_clock_W', 'all_state_leakage_upper_W',
                    'selected_data_internal_upper_W', 'data_pin_upper_W', 'unresolved_all_output_load_ceiling_W'))
        self.assertEqual(total, D(self.x['priced_all_output_ceiling_subtotal_W']))

    def test_allocation_cannot_become_provider_or_admission(self):
        self.assertFalse(self.x['physical_admission'])
        self.assertFalse(self.x['actual_provider_instantiated'])
        self.assertFalse(self.x['complete_CROM_budget_qualified'])
        self.assertEqual(self.x['root_stop_credit'], 0)
        self.assertEqual(self.x['gamma_all_layer_reuse_credit'], 0)


if __name__ == '__main__':
    unittest.main()
