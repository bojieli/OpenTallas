"""Exercise the production shell selection/finalization on routed result fixtures."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).with_name("hold_eco.sh")

class SelectionTests(unittest.TestCase):
    def run_selection(self, rows):
        source = SCRIPT.read_text()
        selection = source[source.index('  sc=$(python3 -c'):source.index('\ndone\nif [ -z "$best" ];')]
        finalization = source[source.index('if [ -z "$best" ];'):]
        with tempfile.TemporaryDirectory() as root:
            out = Path(root)
            for index, (tt, ff) in enumerate(rows, 1):
                directory = out / f"pass{index}"
                directory.mkdir()
                (directory / "orfs").mkdir()
                result = dict(tt_ps=tt, ss_ps=tt, ff_ps=ff, drc=0,
                              score=min(tt, ff), rank=min(tt, ff))
                (directory / "result.json").write_text(json.dumps(result))
                (directory / "corner_sta.json").write_text('{}')
                (directory / "eco_mm.log").write_text('Number of violations = 0\n')
            setup = 'best=""; bestscore=-1e9; lb=""; lbrank=-1e18; HM=30\n'
            body = setup + f'OUT="{out}"\nfor k in $(seq 1 {len(rows)}); do\nP="$OUT/pass$k"\n'
            body += selection + '\ndone\n' + finalization
            completed = subprocess.run(['bash', '-c', body], capture_output=True, text=True)
            result = json.loads((out / 'result.json').read_text())
            installed = (out / 'orfs').is_symlink()
            return completed.returncode, result, installed

    def test_negative_tt_result_never_installed(self):
        code, result, installed = self.run_selection([(-55.31, 4.38)])
        self.assertEqual(code, 9)
        self.assertEqual(result['chosen'], 'least_bad')
        self.assertEqual(result['tt_ps'], -55.31)
        self.assertFalse(installed)

    def test_negative_hold_result_never_installed(self):
        code, result, installed = self.run_selection([(20, -0.4)])
        self.assertEqual(code, 9)
        self.assertFalse(installed)

    def test_zero_margin_is_accepted(self):
        code, result, installed = self.run_selection([(0, 0)])
        self.assertEqual(code, 0)
        self.assertNotIn('chosen', result)
        self.assertTrue(installed)

    def test_failed_later_pass_keeps_clean_earlier_result(self):
        code, result, installed = self.run_selection([(5.2, 4.4), (-2, 8)])
        self.assertEqual(code, 0)
        self.assertEqual(result['tt_ps'], 5.2)
        self.assertTrue(installed)

    def test_all_failed_preserves_best_failure(self):
        code, result, installed = self.run_selection([(-55.31, 4.38), (-10, 2)])
        self.assertEqual(code, 9)
        self.assertEqual(result['tt_ps'], -10)
        self.assertFalse(installed)

if __name__ == '__main__':
    unittest.main()
