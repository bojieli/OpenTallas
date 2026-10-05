import unittest
from decimal import Decimal as D
from tools.w10_q_gated_clock_ledger import charge_cycles
class GatedClockTest(unittest.TestCase):
    def test_existing_leaf_stop_keeps_root_and_icg(self):
        self.assertEqual(charge_cycles(100,0,D(2),D(3),D('.1'),D('.2'),D(10)),D(22))
    def test_enabled_and_drain_interval_charged_once(self):
        self.assertEqual(charge_cycles(100,50,D(2),D(3),D('.1'),D('.2'),D(10)),D('36.5'))
    def test_forged_extra_leaf_cycles_fail(self):
        for roots,leaf in ((10,11),(-1,0),(10,-1)):
            with self.assertRaises(ValueError):charge_cycles(roots,leaf,D(1),D(1),D(1),D(1),D(1))
if __name__=='__main__':unittest.main()
