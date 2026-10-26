"""Q-NETLIST 10-16: sys_face_image calendar compiler (bursts, END rule, class placement) and the ROM via map."""
import unittest

from qwen_split import sys_face_image as S


class SysFaceImage(unittest.TestCase):
    def test_burst_and_end(self):
        t = S.compile_cal('T', [(10, 0, 128), (20, 0, 65), (30, 1, 4)])
        self.assertEqual(len(t), 3)
        self.assertEqual(t[-1] >> 17 & 1, 1)                      # last entry carries the last bit
        self.assertEqual(t[0] >> 18, 10 - S.CAL_OUT_EDGES)        # dt from the start edge
        q = S.compile_cal('L', [(20 + b, 2, b) for b in range(32)])
        self.assertEqual(len(q), 1)                               # one 32-beat Q burst
        self.assertEqual(q[0] & 31, 31)

    def test_rejects(self):
        with self.assertRaises(ValueError):
            S.compile_cal('T', [(10, 0, 1)])                      # no END
        with self.assertRaises(ValueError):
            S.compile_cal('L', [(10, 6, 0)])                      # embedding class outside E
        with self.assertRaises(ValueError):
            S.compile_cal('E', [(10, 7, 0), (10, 6, 1)])          # two events on one edge

    def test_viamap_roundtrip(self):
        rows = {0: 0x123456789abcdef, 7: (1 << 71) | 5, 2048: (15 << 68)}
        text = S.viamap(rows).split()
        phys = [int(x, 16) for x in text]
        for a, w in rows.items():
            got = sum(((phys[a // 8] >> (b * 8 + a % 8)) & 1) << b for b in range(72))
            self.assertEqual(got, w)

    def test_digest_matches_ledger_rule(self):
        p = S.bench_program()
        d = S.SEED
        for i, w in enumerate(p):
            d = ((d << 7) | (d >> 57)) & (2**64 - 1)
            d ^= w ^ (i if i < 1024 else 1024 + (i - 1024))
        self.assertEqual(S.image_digest(p), d)


if __name__ == '__main__':
    unittest.main()
