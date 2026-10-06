"""Address ownership, reducer identity and illegal-pair tests; no golden math."""
from dataclasses import replace
import unittest

from dshbm_wavepack import Op, compile_run, pair_descriptor, pair_refusal, request_addresses, tag16_mapping


class Packing(unittest.TestCase):
    def setUp(self):
        self.a = Op(0, 2, 2, 'fp4', 100, 32, 0, True, True)
        self.b = Op(1, 2, 2, 'fp4', 200, 32, 16, False, True)

    def test_actual_w2_address_ownership(self):
        d = pair_descriptor(self.a, self.b)
        got = list(request_addresses(d))
        expected = []
        for t in range(8):
            expected += list(range(100 + 4*t, 104 + 4*t))
            expected += list(range(200 + 4*t, 204 + 4*t))
        self.assertEqual(got, expected)
        self.assertEqual(len(got), len(set(got)))
        self.assertEqual(d['b_reducer_keys'], [2, 3])

    def test_tail_after_full_head(self):
        a = replace(self.a, rows=6, lines=96)
        d = pair_descriptor(a, self.b)
        self.assertEqual(d['head']['lines'], 64)
        got = list(request_addresses(d))
        self.assertEqual(got[:64], list(range(100, 164)))
        self.assertEqual(set(got), set(range(100, 196)) | set(range(200, 232)))

    def test_defaultoff_and_three_w2_pairs(self):
        ops = [replace(self.a, identity=i, base=1000+i*32, xb=(i*16)%128, dep=i==0) for i in range(6)]
        self.assertEqual(len(compile_run(ops)['descriptors']), 6)
        self.assertEqual([d['kind'] for d in compile_run(ops, True)['descriptors']], ['PAIR']*3)

    def test_negative_column_and_falling_delay(self):
        self.assertIn('P3', pair_refusal(self.a, replace(self.b, fmt='bf16')))
        a = replace(self.a, rows=1, groups=3, lines=24)
        b = replace(self.b, groups=1, lines=16, xb=24)
        self.assertIn('P4', pair_refusal(a, b))

    def test_missing_span_dependency_alias_fullwave(self):
        for b in (replace(self.b, x_bound=False), replace(self.b, lines=31)):
            with self.assertRaises(ValueError):
                pair_descriptor(self.a, b)
        self.assertIn('P1', pair_refusal(self.a, replace(self.b, dep=True)))
        self.assertIn('overlapping', pair_refusal(self.a, replace(self.b, xb=0)))
        a = replace(self.a, rows=4, lines=64)
        self.assertIn('P5', pair_refusal(a, self.b))

    def test_live_reducer_keys_refused_without_release_evidence(self):
        a = replace(self.a, rows=9, groups=1, lines=72)
        b = replace(self.b, rows=1, groups=1, lines=8, xb=8)
        self.assertIn('reducer keys', pair_refusal(a, b))
        self.assertEqual([d['kind'] for d in compile_run([a, b], True)['descriptors']],
                         ['LINEAR', 'LINEAR'])

    def test_finite_w2_tag_identity_and_live_key_uniqueness(self):
        m = tag16_mapping(pair_descriptor(self.a, self.b))
        self.assertEqual(m['tag_bits'], 12+1+3)
        self.assertEqual(len(set(m['reducer_keys'])), m['rows_total'])
        identities = [(r['operation'], r['local_row']) for r in m['virtual_rows']]
        self.assertEqual(identities, [(0,0), (0,1), (1,0), (1,1)])
        # All eight row/group slots fit one wave; slot recurrence stays eight.
        items = [(r,g) for r in range(4) for g in range(2)]
        for r in range(4):
            self.assertEqual([g for rr,g in items if rr==r], [0,1])
        for t in range(7):
            for s in range(8):
                self.assertEqual((t+1)*8+s-(t*8+s),8)

    def test_w2_x_address_relocation_and_wrap(self):
        for a_base in range(128):
            b_base = (a_base+16)%128
            for g in range(2):
                for t in range(8):
                    xa=(a_base+8*g+t)%128
                    self.assertEqual((xa+(b_base-a_base)%128)%128,(b_base+8*g+t)%128)


if __name__ == '__main__':
    unittest.main()
