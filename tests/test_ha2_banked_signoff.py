import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("owned_signoff", ROOT / "physical/hbm_ha2_owner_banked_20261006/signoff.py")
S = importlib.util.module_from_spec(spec)
spec.loader.exec_module(S)


class SignoffTest(unittest.TestCase):
    def test_margin_boundary_and_missing_reports(self):
        self.assertTrue(all(S.acceptance(15, 15)[k] for k in ('SS_ok', 'FF_ok')))
        self.assertFalse(S.acceptance(15 - .01, 15)['SS_ok'])
        self.assertFalse(S.acceptance(15, 14.99)['FF_ok'])
        for value in (None, float('nan'), float('inf'), -1):
            self.assertFalse(S.acceptance(value, value)['SS_ok'])
            self.assertFalse(S.acceptance(value, value)['FF_ok'])

    def test_tool_error_after_positive_report_is_not_pass(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            for rc, suffix in [(1, ''), (0, '\n[ERROR STA-0001] failed')]:
                result = subprocess.CompletedProcess([], rc, 'WORST max 100\nWORST min 100' + suffix, '')
                with patch.object(S.subprocess, 'run', return_value=result):
                    with self.assertRaises(RuntimeError):
                        S.sta(d, d/'final.odb', d/'in.sdc', d/'final.spef', 'SS', 'max')

    def test_failed_timing_returns_nonzero_and_keeps_record(self):
        with tempfile.TemporaryDirectory() as td:
            run = Path(td)
            case = run/'work/orfs'
            base = case/'results/asap7/dut/base'
            base.mkdir(parents=True)
            (base/'6_final.odb').touch()
            (case/'config.mk').touch()
            log = 'LATBEGIN\nrise -> rise\n 100.00 200.00 latency\nLATEND\nWORST max -1.00\nWORST min 14.99\n'
            with patch('sys.argv', ['signoff.py', '--run', td]), patch.object(S, 'sta', return_value=log), patch.object(S.subprocess, 'run'):
                self.assertEqual(S.main(), 1)
            result = json.loads((run/'signoff.json').read_text())
            self.assertFalse(result['accept']['SS_ok'])
            self.assertFalse(result['accept']['FF_ok'])

    def test_preserve_failed_verdict(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)/'signoff.json'
            p.write_text('{"accept": {"SS_ok": false}}\n')
            original = p.read_bytes()
            with patch('sys.argv', ['signoff.py', '--run', td]):
                with self.assertRaisesRegex(SystemExit, 'refusing overwrite'):
                    S.main()
            self.assertEqual(original, p.read_bytes())


if __name__ == '__main__':
    unittest.main()
