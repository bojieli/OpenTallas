from decimal import Decimal as D
import json
from pathlib import Path
import unittest


class StagingCorrectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old=json.loads(Path('results/uarch/w10_crom_buffer_budget_r1/budget.json').read_text())
        cls.x=json.loads(Path('results/uarch/w10_crom_staging_correction_r1/budget.json').read_text())

    def test_two_operand_two_slot_capacity(self):
        self.assertEqual(self.x['total_storage_bits'],475402)
        self.assertEqual(self.x['storage_bits_by_purpose']['two_operands_FP32_two_emit_slots'],131072)
        self.assertEqual(self.x['staging_correction']['extra_FF_bits'],24576)
        self.assertEqual(self.old['total_storage_bits'],450826)

    def test_extra_clock_enable_mux_and_data_charges(self):
        c=self.x['staging_correction']
        self.assertEqual(c['extra_NAND2_write_enable_cells'],4*24576)
        self.assertGreater(c['extra_clock_buffers'],0)
        for k,v in c['delta_components_W'].items():
            self.assertGreater(D(v),0)
            self.assertEqual(D(self.x[k])-D(self.old[k]),D(v))

    def test_missing_credit_provider_never_becomes_zero_cost_admission(self):
        self.assertIsNone(self.x['credit_route_clock_reservation']['clock_W'])
        self.assertFalse(self.x['credit_route_clock_reservation']['whole_CROM_budget_ready'])
        self.assertFalse(self.x['physical_admission'])
        self.assertEqual(self.x['root_stop_credit'],0)


if __name__=='__main__':unittest.main()
