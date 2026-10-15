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

    def test_full_actual_geometry_and_masks(self):
        for model, vectors, sectors in [('qwen', 'qwen_full', 12725), ('deepseek', 'deepseek_full', 5617)]:
            with self.subTest(model=model):
                result = module.inventory(HERE / 'inputs' / vectors)
                comparison = module.compare_canonical(result, model, ROOT / 'results/arch/hgi_programs_20261010/inputs/ds_rank0_program.json')
                self.assertTrue(comparison['all_included_record_geometries_match'])
                self.assertEqual(result['golden_output_mask_sectors_verified'], sectors)
                expected = ['head_scale', 'swiglu'] if model == 'qwen' else [f'route.gather{i}' for i in range(6)]
                self.assertEqual(comparison['canonical_SU_SFU_tags_absent_from_included_program'], expected)

    def test_scaled_records_do_not_qualify_as_full(self):
        for model, vectors in [('qwen', 'q_s4'), ('deepseek', 'd_s4')]:
            with self.subTest(model=model):
                result = module.inventory(HERE / 'inputs' / vectors)
                comparison = module.compare_canonical(result, model, ROOT / 'results/arch/hgi_programs_20261010/inputs/ds_rank0_program.json')
                self.assertFalse(comparison['all_included_record_geometries_match'])
                self.assertTrue(any(r.get('differences') for r in comparison['included_records']))

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
