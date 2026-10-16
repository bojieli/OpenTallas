import unittest
from qwen_split.relay_row_gaps import row_gaps, contains_frame

class ActualRowGaps(unittest.TestCase):
    def test_actual_r2f_repack_channel(self):
        # Two columns at three rows, actual 820.8 bodies and 129.6 gaps.
        intervals = [(1641.6 + r*950.4, 2462.4 + r*950.4)
                     for r in range(3) for col in range(2)]
        gaps = row_gaps(intervals)
        self.assertTrue(contains_frame(gaps, 2464.56, 60.48))
        self.assertFalse(contains_frame(gaps, 2400, 60.48))
        self.assertFalse(contains_frame(gaps, 2550, 60.48))
        self.assertFalse(contains_frame(gaps, 0, 60.48))
    def test_staggered_tile_blocks_channel(self):
        gaps = row_gaps([(0,100),(140,240),(90,150)])
        self.assertEqual(gaps, [])
    def test_no_infinite_end_channels(self):
        self.assertEqual(row_gaps([(20,40),(20,40)]), [])
        self.assertFalse(contains_frame([(40,50)], 40, 0))

if __name__ == '__main__': unittest.main()
