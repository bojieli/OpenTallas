#!/usr/bin/env python3
import importlib.util
from pathlib import Path
import shutil
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
spec = importlib.util.spec_from_file_location('inventory', ROOT / 'tools/hbm_static/su_program_inventory.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class InventoryTests(unittest.TestCase):
    def test_actual_frozen_vectors(self):
        for model, count, price, sectors in [('q_s4', 18, 1548, 5173), ('d_s4', 34, 2912, 3429)]:
            with self.subTest(model=model):
                result = module.inventory(HERE / 'inputs' / model)
                self.assertEqual(result['record_count'], count)
                self.assertEqual(result['cases'][0]['summed_model_price'], price)
                self.assertEqual(result['golden_output_mask_sectors_verified'], sectors)
                self.assertFalse(result['calendar_emitted'])

    def test_actual_mask_mutant(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp) / 'vectors'
            shutil.copytree(HERE / 'inputs/q_s4', directory)
            path = directory / 'su_vmg.mem'
            words = path.read_text().split()
            words[0] = f'{int(words[0], 16) ^ 1:02x}'
            path.write_text('\n'.join(words) + '\n')
            with self.assertRaisesRegex(AssertionError, 'golden output mask mismatch'):
                module.inventory(directory)

    def test_actual_output_address_mutant(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp) / 'vectors'
            shutil.copytree(HERE / 'inputs/d_s4', directory)
            path = directory / 'su_rec.mem'
            words = path.read_text().split()
            # First record reduces into R. Flip its effective descriptor base bit0.
            base_lsb = next(lsb for name, lsb, width in __import__('hbm_generic_iface').D_MDESC_FIELDS if name == 'base')
            words[0] = f'{int(words[0], 16) ^ (1 << (384 + 256 * 5 + base_lsb)):0550x}'
            path.write_text('\n'.join(words) + '\n')
            with self.assertRaisesRegex(AssertionError, 'golden output mask mismatch'):
                module.inventory(directory)

    def test_exact_disjoint_and_partial_masks(self):
        self.assertEqual(module.runs({1, 2, 5}), [[1, 2], [5, 5]])
        self.assertEqual(module.mask_runs({3, 4, 8}), [[0, 0, 24], [1, 1, 1]])


if __name__ == '__main__':
    unittest.main(verbosity=2)
