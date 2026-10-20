import unittest
import f16_calr_edges as F


class T(unittest.TestCase):
    def test_bench_first_age(self):
        # tload bench: request presented at the tload face edge R; first write visible after edge R+4 (= 5th edge)
        first, last = F.table_write_window(cal_edge=0, die_lane_edges=0, slice_index=0)
        self.assertEqual(first - (F.CTLM_TREQ_EDGES), 1 + 1 + 3)
        self.assertEqual(last - first, F.LOADER_LAST_WRITE - F.LOADER_FIRST_WRITE)
        self.assertEqual(F.LOADER_LAST_WRITE - F.LOADER_FIRST_WRITE + 1, F.LOADER_SLOTS)

    def test_row_hops(self):
        a = F.table_write_window(10, 4, 0)
        b = F.table_write_window(10, 4, 5)
        self.assertEqual(b[0] - a[0], 5)

    def test_no_guessed_lane(self):
        with self.assertRaises(ValueError):
            F.table_write_window(0, None, 0)

    def test_wtn(self):
        self.assertEqual(F.wtn_status_edge(100), 102)


if __name__ == "__main__":
    unittest.main()
