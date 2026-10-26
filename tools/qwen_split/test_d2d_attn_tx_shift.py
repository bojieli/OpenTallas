"""KV-BIND4 10-19: --attn-tx-shift moves the K RESULT burst and STATUS together and prices the edges in the layer window."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import d2d_link_calendar as L  # noqa: E402


class AttnTxShift(unittest.TestCase):
    W = [10, 200, 30, 1800]

    def k(self, m, kind):
        return sorted(x['cyc'] for x in m if x['src'] == 'K' and x['kind'] == kind)

    def test_zero_shift_is_unchanged(self):
        self.assertEqual(L.layer_msgs(0, 0, self.W, 8, 7, 40, 5), L.layer_msgs(0, 0, self.W, 8, 7, 40, 5, 0))

    def test_shift_moves_result_and_status(self):
        m0, l0 = L.layer_msgs(0, 0, self.W, 8, 7, 40, 213, 0)
        m1, l1 = L.layer_msgs(0, 0, self.W, 8, 7, 40, 213, 1)
        self.assertEqual([c + 1 for c in self.k(m0, 3)], self.k(m1, 3))
        self.assertEqual([c + 1 for c in self.k(m0, 4)], self.k(m1, 4))
        self.assertEqual(l1['attn_end'], l0['attn_end'] + 1)
        self.assertEqual([x for x in m0 if x['src'] == 'C'], [x for x in m1 if x['src'] == 'C'])   # compute sends unchanged
        self.assertEqual(self.k(m1, 4)[0] - self.k(m1, 3)[0], 33 + 213)

    def test_negative_refused(self):
        with self.assertRaises(ValueError):
            L.layer_msgs(0, 0, self.W, 8, 7, 40, 0, -1)

    def test_service_pad_preserves_hardware_shift_and_compute_messages(self):
        m0, l0 = L.layer_msgs(0, 0, self.W, 8, 7, 40, 213, 1)
        m1, l1 = L.layer_msgs(0, 0, self.W, 8, 7, 40, 213, 1, 2)
        self.assertEqual(l1['attn_tx_shift'], 1)
        self.assertEqual(l1['attn_service_pad'], 2)
        self.assertEqual(l1['attn_end'], l0['attn_end'] + 2)
        self.assertEqual([x for x in m0 if x['src'] == 'C'], [x for x in m1 if x['src'] == 'C'])
        for kind in (3, 4):
            self.assertEqual([c + 2 for c in self.k(m0, kind)], self.k(m1, kind))


if __name__ == '__main__':
    unittest.main()
