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

    def run_(self, *a, mem='12', **extra):
        env = dict(os.environ); env.pop('OT_HEAVY_MEM_GB', None); env.pop('OT_HEAVY_NETWORK', None)
        env['OT_HEAVY_NETWORK_ALLOW'] = str(self.d / 'allow')
        env.update(extra)
        if mem: env['OT_HEAVY_MEM_GB'] = mem
        return subprocess.run([str(self.sh), *a], capture_output=True, text=True, env=env).stdout.split('\n')[:-1]

    def test_default_cap(self):
        self.assertEqual(self.run_('run', '--rm', '-v', 'a:b', 'img', 'python', '-m', 'x'),
                         ['run', '--memory-swap=12g', '--network=none', '--oom-score-adj=0', '--memory=12g', '--rm', '-v', 'a:b', 'img', 'python', '-m', 'x'])

    def test_larger_lowered_smaller_kept(self):
        self.assertIn('12g', self.run_('run', '-e', 'A=1', '-m', '200g', 'img'))
        out = self.run_('run', '--memory=4g', 'img')
        self.assertIn('--memory=4g', out); self.assertIn('--memory-swap=4g', out)

    def test_passthrough(self):
        self.assertEqual(self.run_('ps', '-a'), ['ps', '-a'])
        self.assertEqual(self.run_('run', 'img', mem=''), ['run', 'img'])


    def test_netnone_default_and_exceptions(self):            # NETNONE_1111
        self.assertIn('--network=none', self.run_('run', 'img', 'yosys'))
        own = self.run_('run', '--network', 'host', 'img')
        self.assertNotIn('--network=none', own); self.assertIn('host', own)
        self.assertNotIn('--network=none', self.run_('run', '--net=bridge', 'img'))
        self.assertNotIn('--network=none', self.run_('run', 'img', OT_HEAVY_NETWORK='1'))
        (self.d / 'allow').write_text('# needs pip\npython:3\\.12 .*pip install\n')
        self.assertNotIn('--network=none', self.run_('run', 'python:3.12', 'bash', '-c', 'pip install x'))
        self.assertIn('--network=none', self.run_('run', 'python:3.12', 'bash', 'x.sh'))
        self.assertEqual(self.run_('run', 'img', mem=''), ['run', 'img'])   # outside ot-heavy: untouched


if __name__ == '__main__':
    unittest.main()
