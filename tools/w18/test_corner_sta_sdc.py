"""Focused selected-SDC compatibility checks; no physical timing claims."""
import argparse
import contextlib
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.w18 import corner_sta as sta


class SelectedSdcTest(unittest.TestCase):
    def test_default_and_selected_provenance(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            base = root / 'results/asap7/test/base'
            base.mkdir(parents=True)
            for name in ('6_final.odb', '6_final.spef', '6_final.sdc', '6_signoff.sdc'):
                (base / name).write_text(name)
            output = root / 'receipt.json'
            fake = type('Result', (), {'stdout': 'OT_WS 1e-11\nOT_TNS 0\n', 'returncode': 0, 'stderr': ''})()
            for selected in ('6_final.sdc', '6_signoff.sdc'):
                args = ['--orfs-dir', str(root), '--output', str(output)]
                if selected != '6_final.sdc':
                    args += ['--sdc-name', selected]
                with patch.object(sta.subprocess, 'run', return_value=fake) as docker, contextlib.redirect_stdout(io.StringIO()):
                    sta.main(args)
                self.assertEqual(docker.call_count, 2)
                rec = json.loads(output.read_text())
                self.assertEqual(rec['sdc'], selected)
                self.assertEqual(rec['sdc_name'], selected)
                for corner in ('ss', 'ff'):
                    record = rec['setup_ss' if corner == 'ss' else 'hold_ff']
                    self.assertEqual(record['sdc_sha256'], hashlib.sha256(selected.encode()).hexdigest())
                    self.assertIn('/base/' + selected, (root / f'w18_sta_{corner}.tcl').read_text())
            (base / '6_signoff.sdc').unlink()
            with patch.object(sta.subprocess, 'run') as docker:
                with self.assertRaises(FileNotFoundError):
                    sta.run(root, 'ss', [], sdc_name='6_signoff.sdc')
                docker.assert_not_called()

    def test_safe_basename_and_existing_script_behavior(self):
        for bad in ('../x', '/x', '.', '..', 'a b', 'a;exit', 'a[exit]', 'a$env', 'a\\b', 'a\nb'):
            with self.assertRaises(argparse.ArgumentTypeError):
                sta.script('ss', '/work/base', [], sdc_name=bad)
        text = sta.script('ss', '/work/base', [], ['constraints/post.sdc'], '6_signoff.sdc')
        self.assertLess(text.index('set_propagated_clock'), text.index('read_sdc /src/constraints/post.sdc'))
        self.assertIn('foreach ot_path $pr', text)
        self.assertIn('foreach ot_path $pi', text)


if __name__ == '__main__':
    unittest.main()
