"""Fail-closed external command and preserved-checkpoint checks."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).with_name('resume_check.sh')


class ResumeCheck(unittest.TestCase):
    def run_check(self, output, rc=0, checkpoint=True):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root/'results').mkdir()
            if checkpoint:
                (root/'results/4_1_cts.odb').write_text('retained checkpoint')
            mock = root/'docker'
            mock.write_text('#!/bin/bash\nprintf "%s\\n" "$MOCK_OUTPUT"\nexit "$MOCK_RC"\n')
            mock.chmod(0o755)
            return subprocess.run(['bash', str(SCRIPT), td, td], text=True, capture_output=True,
                env=dict(os.environ, PATH=td+':'+os.environ['PATH'], MOCK_OUTPUT=output, MOCK_RC=str(rc)))

    def test_failed_make_cannot_pass_despite_stage_output(self):
        r=self.run_check('do-5_1_grt', 7)
        self.assertEqual(r.returncode,7)
        self.assertNotIn('RESUME_OK=1',r.stdout)

    def test_empty_output_cannot_pass(self):
        r=self.run_check('')
        self.assertNotEqual(r.returncode,0)
        self.assertIn('RESUME_OK=0',r.stdout)

    def test_checkpoint_required(self):
        self.assertNotEqual(self.run_check('do-5_1_grt',checkpoint=False).returncode,0)

    def test_no_pre_route_rerun(self):
        self.assertNotEqual(self.run_check('do-3_1_place').returncode,0)

    def test_valid_route_resume(self):
        r=self.run_check('do-5_1_grt\ndo-5_2_route')
        self.assertEqual(r.returncode,0,r.stderr)
        self.assertIn('RESUME_OK=1',r.stdout)


if __name__=='__main__':
    unittest.main()
