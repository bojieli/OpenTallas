import unittest
from tools.w10_q_constructive_area_bound import count_gates
class ConstructionTest(unittest.TestCase):
    def test_output_width_prices_signed_multiply(self):
        self.assertEqual(count_gates({'type':'$mul','parameters':{'Y_WIDTH':'1000'},'connections':{}}),704)
    def test_wide_shift_detection_not_free(self):
        c={'type':'$shiftx','connections':{'A':list(range(48)),'B':list(range(32)),'Y':list(range(4))}}
        self.assertEqual(count_gates(c),2080)
    def test_unrecognized_cells_fail_closed(self):
        with self.assertRaises(ValueError):count_gates({'type':'$unpriced_operator'})
if __name__=='__main__':unittest.main()
