import unittest
import numpy as np
from h4_c0_ds_pc10_golden import assemble


class GoldenGroupTreeTests(unittest.TestCase):
    def parts(self):
        return {r: np.zeros(1024, dtype=np.float32) for r in range(64)}

    def test_original_tree_not_sequential_or_reassociated(self):
        p = self.parts()
        for r, value in enumerate([1e20, 1, -1e20, 1]):
            p[r][:] = value
        z = assemble(p)
        self.assertTrue(np.all(z[:1024].view(np.uint32) == 0))
        # Sequential accumulation of these four values would yield1.
        self.assertEqual(z.shape, (8192,))

    def test_group_rank_order_and_one_final_ties_to_even_round(self):
        p = self.parts()
        for group in range(8):
            p[8 * group][:] = np.float32(group + 1)
        p[0][:] = np.float32(1.00390625)  # BF16 tie at1: rounds to even1.
        z = assemble(p).reshape(8, 1024)
        for group in range(8):
            self.assertTrue(np.all(z[group] == np.float32(group + 1)))

    def test_missing_wrong_shape_or_nonfinite_source_fails(self):
        p = self.parts()
        del p[63]
        with self.assertRaises(ValueError): assemble(p)
        p = self.parts(); p[0] = np.zeros(128, dtype=np.float32)
        with self.assertRaises(ValueError): assemble(p)
        p = self.parts(); p[0][0] = np.nan
        with self.assertRaises(ValueError): assemble(p)


if __name__ == '__main__':
    unittest.main()
