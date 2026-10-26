import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('measure', Path(__file__).with_name('mtp_fused_measure.py'))
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)


class MeasurementGuard(unittest.TestCase):
    def fixture(self, text):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        (root / 'vec').mkdir()
        case = [0, 0, 1, 0, 20, 0, 8, 0, 1]
        (root / 'vec/fu_case.mem').write_text(''.join(f'{x:08x}' for x in case) + '\n')
        for name, width, count in (('fu_vmi', 16, 20), ('fu_vme', 16, 8), ('fu_hbm', 18, 1),
                                   ('fu_rec', 304, 1), ('fu_exp', 172, 1)):
            (root / f'vec/{name}.mem').write_text(('0' * width + '\n') * count)
        (root / 'vec/fu_sizes.svh').write_text(''.join(
            f'localparam integer {name} = {count};\n' for name, count in
            [('NREC', 1), ('NCASE', 1), ('NVMI', 20), ('NVME', 8), ('NHBM', 1)]))
        (root / 'run.log').write_text(text)
        return root

    def positive(self):
        return ('case 0: 1 records in 2500 cycles (HC engine 2000, mover 20)\n'
                'summary: 1 FUSED data cases through the D1 unit, 8 VM words exact\n'
                'HGI_FUSED_UNIT PASS\n')

    def test_positive_and_numeric_mutant(self):
        self.assertEqual(M.read_run(self.fixture(self.positive()))['measured'][0]['cycles'], 2500)
        mutant = self.positive().replace('HGI_FUSED_UNIT PASS', 'ERR case 0 VM[123] = 00 expected 01\nHGI_FUSED_UNIT FAIL errors=1')
        M.read_run(self.fixture(mutant), mutant=True)

    def test_missing_input_rejects_positive_and_mutant(self):
        for mutant in (False, True):
            with self.assertRaises(AssertionError):
                M.read_run(self.fixture('$readmem file not found\n' + self.positive()), mutant=mutant)

    def test_truncated_or_duplicate_completion_rejected(self):
        for text in (self.positive().replace('8 VM words', '5 VM words'), self.positive() + self.positive()):
            with self.assertRaises(AssertionError):
                M.read_run(self.fixture(text))

    def test_incomplete_or_unknown_image_is_rejected(self):
        for content in ('', '0000\n', 'x' * 16 + '\n'):
            root = self.fixture(self.positive())
            (root / 'vec/fu_vme.mem').write_text(content)
            with self.assertRaises(AssertionError):
                M.read_run(root)

    def test_mutant_requires_numerical_difference(self):
        text = self.positive().replace('HGI_FUSED_UNIT PASS', 'HGI_FUSED_UNIT FAIL errors=1')
        with self.assertRaises(AssertionError):
            M.read_run(self.fixture(text), mutant=True)


if __name__ == '__main__':
    unittest.main()
