"""Production TP-96 descriptor, image ordering and consumer checks without loading the checkpoint."""
import unittest
from types import SimpleNamespace
import numpy as np
from hgi_sim import ds_native as N
from hgi_sim.records import encode_program, decode_program


class StackedExperts(unittest.TestCase):
    def setUp(self):
        self.model = SimpleNamespace(k_exp=6, n_exp=384, limit=7, P=lambda L: f'layers.{L}.')
        self.layout, self.man = N.Layout(), N.Manifest()
        c = N.W.Compiler(self.model, 0)
        for slot in range(7):
            fmt = 'fp4' if slot < 6 else 'fp8'
            c.mv(0, (slot, 'w1'), 'linear_q', 'x', f'e{slot}.g', 2304, 5120, fmt)
            c.mv(0, (slot, 'w3'), 'linear_q', 'x', f'e{slot}.u', 2304, 5120, fmt)
            c.local(0, 'swiglu', slot=slot)
        self.ops = c.ops

    def test_production_records_and_consumer(self):
        for fuse in (False, True):
            lower = N.Lower(self.model, 0, self.layout, self.man, fuse=fuse)
            for rank in range(96):
                records = lower.layer(0, self.ops, rank)
                sm = [r for r in records if r.unit == 'SM']
                self.assertEqual(len(sm), 7)
                for slot, rec in enumerate(sm):
                    b, o = rec.desc['B'], rec.desc['O']
                    ent, ex, row, _ = self.man.find(b.base)
                    self.assertEqual((b.m, b.n, row, o.n), (48, 5120, 48 * rank, 48))
                    self.assertEqual(b.indexed, int(slot < 6))
                    self.assertEqual(b.dyn_mul, 4608 * b.stride if slot < 6 else 0)
                    self.assertEqual(o.base, self.layout.vm[f'e{slot}.g'])
                    self.assertEqual(rec.src, (0, 3*slot, [3*slot+1]))
                    self.assertEqual(set(rec.writes), {f'e{slot}.g', f'e{slot}.u'})
                su = [r for r in records if r.family == 'swiglu']
                for rec in su:
                    self.assertEqual(rec.desc['C'].base - rec.desc['A'].base, 24)
                    self.assertEqual(rec.desc['A'].n, 24)
                wire = decode_program(encode_program(records))
                self.assertEqual(len(wire), len(records))
                self.assertEqual(wire[0].desc['B'].dyn_mul, sm[0].desc['B'].dyn_mul)

    def test_weight_image_ranges(self):
        # Checkpoint rows carry matrix, expert, row and column identity. Exact expected
        # image is independent of the production row mapper and includes partial shards.
        class Golden:
            def wrows(self, name, lo, hi):
                mat = 1 if '.w1.' in name else 3
                expert = int(name.split('.')[-3]) if '.experts.' in name else 0
                q = (np.arange(lo, hi)[:,None]*32 + np.arange(32)[None,:] + mat*100000 + expert*1000000)
                return N.V_.Q8(q, np.full((hi-lo,1), mat))
        lower = N.Lower(self.model, 0, self.layout, self.man)
        lower.layer(0, self.ops, 0)
        wrows = N.ds_units(self.model, self.man, Golden())['_wrows']
        for ent in self.man.ent:
            ex = 17 if ent['experts'] > 1 else 0
            want = []
            for rank in range(96):
                for mat in (1,3):
                    want.append(np.arange(rank*24, (rank+1)*24)[:,None]*32 + np.arange(32)[None,:] +
                                mat*100000 + ex*1000000)
            want = np.concatenate(want)
            for lo, n in ((0,4608),(23,27),(48*95,48),(47,3)):
                got = wrows(ent, ex, lo, n, 0, 32, 0)
                np.testing.assert_array_equal(got.q, want[lo:lo+n])
                # Swapping the matrix halves must violate exact row identity.
                if n == 48:
                    self.assertFalse(np.array_equal(got.q, np.roll(want[lo:lo+n],24,axis=0)))

    def test_mismatched_pair_refused(self):
        self.ops[1]['k'] = 2304
        with self.assertRaisesRegex(ValueError, 'matching w1'):
            N.Lower(self.model, 0, self.layout, self.man).layer(0, self.ops, 0)


if __name__ == '__main__':
    unittest.main()
