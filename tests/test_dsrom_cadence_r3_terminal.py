import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('analysis', Path(__file__).resolve().parents[1] / 'tools/analyze_dsrom_cadence_r3_terminal.py')
A = importlib.util.module_from_spec(spec)
spec.loader.exec_module(A)


class TerminalAnalysis(unittest.TestCase):
    def test_valid_writes_and_inactive_address(self):
        t = A.loader_trace()
        self.assertEqual([(e['cycle'], e['c_a']) for e in t if e['c_v']], list(zip(range(14,39), range(25))))
        self.assertEqual((t[39]['c_v'], t[39]['c_a']), (0,25))
        self.assertEqual((t[119]['c_v'], t[119]['c_a']), (0,25))

    def test_original_write_bound_rejects_valid_25(self):
        legal = lambda valid, address: not valid or 0 <= address < 25
        self.assertFalse(legal(1,25))
        self.assertTrue(legal(0,25))
        self.assertTrue(legal(1,24))

    def test_immutable_trace_and_classification(self):
        r = A.analyze()
        self.assertEqual(r['status'], 'FAIL_UNQUALIFIED_UNCHANGED')
        self.assertEqual(r['observed']['final_occupancy'],5)
        self.assertEqual(r['observed']['first_overflow'],119)

    def test_occupancy_mutant_is_rejected(self):
        text = (A.EVIDENCE / 'production5_simulate.log').read_text()
        changed = text.replace('cnt=4 npush=1 pop=0 issue=0 hazard=1 gate=1', 'cnt=3 npush=1 pop=0 issue=0 hazard=1 gate=1', 1)
        self.assertNotEqual(text,changed)
        with self.assertRaisesRegex(ValueError,'occupancy discontinuity'):
            A.inspect(changed)


if __name__ == '__main__':
    unittest.main()
