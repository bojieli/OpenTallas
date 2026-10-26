"""Decision-14 K pacing: compressed controller image preserves every paced RD."""
import os
import unittest
from unittest.mock import patch
from tools.qwen_kv_die import kv_static_programme as C


class CandidatePacing(unittest.TestCase):
    def test_k83_controller_encoding_and_negative_rate_control(self):
        # Full 256-sector PC stream, encoded by the production compiler. Check
        # decoded events independently; a gap=2 mutant exceeds the PHY budget.
        for gap, qualifies in ((3, True), (2, False)):
            want = [120 + i + (i // 8) * gap for i in range(256)]
            runs = C.runs_from_edges(want, 0, 1)
            image = C.CCI.compile_image(runs)
            got = sorted(e for e, v in image['events'].items() if v['mask'] == 1)
            self.assertEqual(got, want)
            self.assertEqual(len(got), 256)
            self.assertEqual(8 / (8 + gap) <= 0.73, qualifies)
            self.assertLessEqual(len(runs), 16)

    def test_explicit_candidate_and_fail_closed_widths(self):
        with patch.dict(os.environ, {'OT_KV_RD_SHAPE_K': '8,3'}):
            self.assertEqual(C.rd_shape_env('OT_KV_RD_SHAPE_K', (8, 2)), (8, 3))
        for raw in ('0,3', '17,3', '8,-1', '8,256', '8/3'):
            with self.subTest(raw=raw), patch.dict(os.environ, {'OT_KV_RD_SHAPE_K': raw}):
                with self.assertRaises(ValueError):
                    C.rd_shape_env('OT_KV_RD_SHAPE_K', (8, 2))
