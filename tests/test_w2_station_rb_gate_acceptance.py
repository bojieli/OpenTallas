import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('w2_gate', ROOT/'tools/w2_station_rb_gate.py')
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)
S8 = 'S8_rel_q_decision_removed'
ASSERT = 'W2_PROGRESS_MISSING_SM_ACCEPT bound=352 elapsed=352 accepted=03'
ARM = 'W2_PROGRESS_ARM event=tap_accept edge=16 bound=352\n'
LOG = ARM + 'FATAL: /tmp/bench.sv:42: ' + ASSERT + '\n'

class AcceptanceTests(unittest.TestCase):
    def result(self, rc=1, text=LOG):
        return gate.runtime_result(rc, text, 'PASS_NATIVE_QUARTER_PUBLICATION')

    def test_intended_assertion_rejects_mutant(self):
        d = gate.negative_verdict(S8, self.result())
        self.assertTrue(d['failed'])
        self.assertEqual(d['matched_assertions'], [ASSERT])

    def test_positive_is_not_negative_credit(self):
        r = self.result(0, 'PASS_NATIVE_QUARTER_PUBLICATION checks=19\n')
        self.assertTrue(r['passed'])
        self.assertEqual(gate.negative_verdict(S8, r)['outcome'], 'SURVIVED')

    def test_build_and_runtime_infrastructure_cannot_reject(self):
        candidates = [dict(compile_exit=1, passed=False), dict(compile_exit=127, passed=False)]
        candidates += [self.result(rc) for rc in (0, 2, 124, 127, 137, 139, 143, -9, -11)]
        for r in candidates:
            with self.subTest(result=r):
                self.assertFalse(gate.negative_verdict(S8, r)['failed'])

    def test_wrong_assertion_generic_timeout_unarmed_or_pass_marker(self):
        for text in ('FATAL: /tmp/bench.sv:42: timeout\n',
                     LOG.replace(ASSERT, 'unrelated assertion'),
                     LOG.replace(ARM, ''),
                     LOG+'PASS_NATIVE_QUARTER_PUBLICATION\n',
                     LOG.replace('FATAL: /tmp/bench.sv:42:', 'tool says FATAL:'),
                     LOG.replace('elapsed=352', 'elapsed=351')):
            with self.subTest(text=text):
                self.assertFalse(gate.negative_verdict(S8, self.result(text=text))['failed'])

    def test_missing_tool_is_infrastructure(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(gate.subprocess, 'run', side_effect=FileNotFoundError('missing tool')):
            self.assertEqual(gate.run(['vvp'], Path(tmp)/'run.log'), 127)

    def test_no_external_timeout_is_installed(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(gate.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0)) as runner:
            gate.run(['vvp'], Path(tmp)/'run.log')
            self.assertNotIn('timeout', runner.call_args.kwargs)

    def test_cli_distinguishes_intended_rejection_survival_build_failure(self):
        for result, expected_rc, expected_outcome in (
            (self.result(), 1, 'REJECTED'),
            (self.result(0, 'PASS_NATIVE_QUARTER_PUBLICATION\n'), 0, 'SURVIVED'),
            (dict(compile_exit=1, passed=False), 2, 'INFRASTRUCTURE_FAILURE'),
            (self.result(124), 2, 'INFRASTRUCTURE_FAILURE')):
            with self.subTest(outcome=expected_outcome), tempfile.TemporaryDirectory() as tmp:
                output = Path(tmp)/'out'
                with patch.object(gate, 'quarter_bench', return_value=result), patch('sys.argv', ['gate','--safe','--neg-only',S8,'--out',str(output)]):
                    with self.assertRaises(SystemExit) as exc:
                        gate.main()
                self.assertEqual(exc.exception.code, expected_rc)
                self.assertEqual(json.loads((output/'terminal.json').read_text())['outcome'], expected_outcome)

if __name__ == '__main__':
    unittest.main()
