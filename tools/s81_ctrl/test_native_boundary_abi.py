import unittest
from native_boundary_abi import D, pack, unpack


class BoundaryABI(unittest.TestCase):
    def setUp(self):
        self.h = [[(e*37+k*7919)&65535 for e in range(D)] for k in range(4)]
        # Distinct sign, NaN payload, signed zero and arbitrary subnormal bits
        # make numeric conversion or stale/default PF visible.
        self.pf = [0x80000000, 0x7fc01234, 0x3f812345, 0x00000007]

    def test_wire_order_and_exact_pf_bits(self):
        rows = pack(self.h, self.pf)
        self.assertEqual(len(rows), 641)
        self.assertEqual(rows[0]&65535, self.h[0][0])
        self.assertEqual((rows[0]>>16)&65535, self.h[1][0])
        self.assertEqual(rows[640], sum(v<<(32*k) for k,v in enumerate(self.pf)))
        self.assertEqual(unpack(rows), (self.h, self.pf))

    def test_pure_h_cannot_pass_canonical_codec(self):
        with self.assertRaisesRegex(ValueError, 'omits PF'):
            unpack(pack(self.h, self.pf)[:640])

    def test_wrong_pf_is_observable_without_h_change(self):
        rows = pack(self.h, self.pf); rows[-1] ^= 1<<65
        h, pf = unpack(rows)
        self.assertEqual(h, self.h)
        self.assertNotEqual(pf, self.pf)

    def test_padding_cannot_hide_extra_state(self):
        rows = pack(self.h, self.pf); rows[-1] |= 1<<128
        with self.assertRaisesRegex(ValueError, 'padding'): unpack(rows)


if __name__ == '__main__': unittest.main()
