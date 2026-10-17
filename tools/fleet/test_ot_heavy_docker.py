"""ot-heavy-docker shim: every docker run under an ot-heavy unit is capped at the declared memory."""
import os, stat, subprocess, tempfile, unittest
from pathlib import Path
SHIM = Path(__file__).resolve().parent / 'ot-heavy-docker'


class Shim(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        fake = self.d / 'fake'; fake.write_text('#!/bin/bash\nprintf "%s\\n" "$@"\n'); fake.chmod(0o755)
        sh = self.d / 'docker'; sh.write_text(SHIM.read_text().replace('REAL=/usr/bin/docker', f'REAL={fake}')); sh.chmod(0o755)
        self.sh = sh

    def run_(self, *a, mem='12'):
        env = dict(os.environ); env.pop('OT_HEAVY_MEM_GB', None)
        if mem: env['OT_HEAVY_MEM_GB'] = mem
        return subprocess.run([str(self.sh), *a], capture_output=True, text=True, env=env).stdout.split('\n')[:-1]

    def test_default_cap(self):
        self.assertEqual(self.run_('run', '--rm', '-v', 'a:b', 'img', 'python', '-m', 'x'),
                         ['run', '--memory-swap=12g', '--memory=12g', '--rm', '-v', 'a:b', 'img', 'python', '-m', 'x'])

    def test_larger_lowered_smaller_kept(self):
        self.assertIn('12g', self.run_('run', '-e', 'A=1', '-m', '200g', 'img'))
        out = self.run_('run', '--memory=4g', 'img')
        self.assertIn('--memory=4g', out); self.assertIn('--memory-swap=4g', out)

    def test_passthrough(self):
        self.assertEqual(self.run_('ps', '-a'), ['ps', '-a'])
        self.assertEqual(self.run_('run', 'img', mem=''), ['run', 'img'])


if __name__ == '__main__':
    unittest.main()
