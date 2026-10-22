"""Gate recovery reuses the canonical checkpoint transaction; no EDA required."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_abi3_physical as R


class Trial(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.case = Path(self.tmp.name) / 'case'
        self.results = self.case / 'results/asap7/design/base'
        self.logs = self.case / 'logs/asap7/design/base'
        self.results.mkdir(parents=True)
        self.logs.mkdir(parents=True)
        (self.results / '4_cts.odb').write_bytes(b'original CTS')
        self.log = self.case.parent / 'grt.log'
        self.log.write_text('original trial failure\n')
        self.commands = []

    def saved_failure(self):
        (self.results / '5_1_grt.grt183_resume.odb').write_bytes(b'resized checkpoint')
        (self.logs / '5_1_grt.log').write_text('[ERROR GRT-0183] net18000\nOT_GRT183_RESUME_SAVED\n')

    def run_trial(self, outcomes, saved=False):
        def run(cmd, stdout, stderr):
            self.commands.append(cmd)
            self.assertIn("GENERATE_ARTIFACTS_ON_FAILURE=1", cmd[-1])
            self.assertIn("GLOBAL_ROUTE_ARGS='-allow_congestion -verbose'", cmd[-1])
            self.assertIn("SKIP_INCREMENTAL_REPAIR=0 grt", cmd[-1])
            if '-o /work/' in cmd[-1]:
                self.assertEqual((self.results / '4_cts.odb').read_bytes(), b'resized checkpoint')
                self.assertIn('SKIP_INCREMENTAL_REPAIR=0 grt', cmd[-1])
            code = outcomes[len(self.commands)-1]
            stdout.write('attempt %d\n' % len(self.commands))
            return subprocess.CompletedProcess(cmd, code)
        with patch.object(R.subprocess, 'run', side_effect=run):
            return R.gate_trial_grt(self.case, self.results, self.case.parent/'src', 'image@sha256:pinned', self.log,
                                    'test_gate', 'SKIP_INCREMENTAL_REPAIR=0 ', saved)

    def test_success_does_not_recover(self):
        self.saved_failure()
        self.assertEqual(self.run_trial([0]), 0)
        self.assertEqual(len(self.commands), 1)
        self.assertFalse((self.results/'5_1_grt.grt183_recovered.json').exists())

    def test_real_failure_retries_once_and_restores_cts_and_logs(self):
        self.saved_failure()
        self.assertEqual(self.run_trial([2, 0]), 0)
        self.assertEqual(len(self.commands), 2)
        self.assertEqual((self.results/'4_cts.odb').read_bytes(), b'original CTS')
        self.assertEqual((self.log.parent/'grt.log.grt183_attempt1').read_text(), 'attempt 1\n')
        self.assertIn('GRT-0183', (self.logs/'5_1_grt.grt183_attempt1.log').read_text())
        self.assertTrue((self.results/'5_1_grt.grt183_recovered.json').exists())

    def test_second_failure_stays_failure_without_third_attempt(self):
        self.saved_failure()
        self.assertEqual(self.run_trial([2, 7]), 7)
        self.assertEqual(len(self.commands), 2)
        self.assertEqual((self.results/'4_cts.odb').read_bytes(), b'original CTS')

    def test_unrelated_failure_never_retries(self):
        self.assertEqual(self.run_trial([9]), 9)
        self.assertEqual(len(self.commands), 1)

    def test_saved_entry_requires_failure_and_refuses_second_recovery(self):
        self.assertEqual(self.run_trial([], saved=True), 1)
        self.assertEqual(self.commands, [])
        self.saved_failure()
        self.assertEqual(self.run_trial([0], saved=True), 0)
        self.assertEqual(len(self.commands), 1)
        self.commands.clear()
        self.assertEqual(self.run_trial([], saved=True), 1)
        self.assertEqual(self.commands, [])
        self.assertEqual((self.log.parent/'grt.log.grt183_attempt1').read_text(), 'original trial failure\n')

    def test_exception_restores_cts(self):
        self.saved_failure()
        with patch.object(R.subprocess, 'run', side_effect=OSError('docker missing')):
            with self.assertRaises(OSError):
                R.gate_trial_grt(self.case, self.results, self.case.parent/'src', 'image', self.log, 'name', resume_saved=True)
        self.assertEqual((self.results/'4_cts.odb').read_bytes(), b'original CTS')

    def test_gate_uses_supported_entry_and_keeps_failure_status(self):
        source = (Path(__file__).parent/'ref_tile/pre_route_gate.py').read_text()
        self.assertIn('gate-trial-grt --case "$C" --results "$B"', source)
        self.assertIn('echo "GATE_GRT_RC=$?', source)


if __name__ == '__main__':
    unittest.main()
