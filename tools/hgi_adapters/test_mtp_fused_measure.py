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
        case = [0, 0, 1, 0, 20, 0, 30720, 0, 1]
        (root / 'vec/fu_case.mem').write_text(''.join(f'{x:08x}' for x in case) + '\n')
        for name in ('fu_vmi', 'fu_vme', 'fu_hbm', 'fu_rec'):
            (root / f'vec/{name}.mem').write_text('01\n')
        (root / 'run.log').write_text(text)
        return root

    def positive(self):
        return ('case 0: 1 records in 2500 cycles (HC engine 2000, mover 20)\n'
                'summary: 1 FUSED data cases through the D1 unit, 30720 VM words exact\n'
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
        for text in (self.positive().replace('30720', '5'), self.positive() + self.positive()):
            with self.assertRaises(AssertionError):
                M.read_run(self.fixture(text))

    def test_mutant_requires_numerical_difference(self):
        text = self.positive().replace('HGI_FUSED_UNIT PASS', 'HGI_FUSED_UNIT FAIL errors=1')
        with self.assertRaises(AssertionError):
            M.read_run(self.fixture(text), mutant=True)


if __name__ == '__main__':
    unittest.main()
