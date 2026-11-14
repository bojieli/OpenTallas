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
        env = dict(os.environ, OT_HEAVY_DOCKER_TRAP='0'); env.pop('OT_HEAVY_MEM_GB', None)   # these cases pin the exec'd argument vector
        if mem: env['OT_HEAVY_MEM_GB'] = mem
        return subprocess.run([str(self.sh), *a], capture_output=True, text=True, env=env).stdout.split('\n')[:-1]

    def test_default_cap(self):
        self.assertEqual(self.run_('run', '--rm', '-v', 'a:b', 'img', 'python', '-m', 'x'),
                         ['run', '--memory-swap=12g', '--oom-score-adj=0', '--memory=12g', '--rm', '-v', 'a:b', 'img', 'python', '-m', 'x'])

    def test_larger_lowered_smaller_kept(self):
        self.assertIn('12g', self.run_('run', '-e', 'A=1', '-m', '200g', 'img'))
        out = self.run_('run', '--memory=4g', 'img')
        self.assertIn('--memory=4g', out); self.assertIn('--memory-swap=4g', out)

    def test_passthrough(self):
        self.assertEqual(self.run_('ps', '-a'), ['ps', '-a'])
        self.assertEqual(self.run_('run', 'img', mem=''), ['run', 'img'])


class Trap(unittest.TestCase):
    """ORPHANSTOP_1114: TERM to the shim stops the named container; normal exit passes the client's status through"""
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.log = self.d / 'calls'
        fake = self.d / 'fake'
        fake.write_text('#!/bin/bash\necho "$*" >> %s\nif [ "$1" = run ]; then case "$*" in *exit7*) exit 7;; esac; sleep 30; fi\n' % self.log)
        fake.chmod(0o755)
        self.sh = self.d / 'docker'
        self.sh.write_text(SHIM.read_text().replace('REAL=/usr/bin/docker', f'REAL={fake}')); self.sh.chmod(0o755)
        self.env = dict(os.environ, OT_HEAVY_MEM_GB='12'); self.env.pop('OT_HEAVY_DOCKER_TRAP', None)

    def test_exit_status_is_passed_through_and_a_name_is_added(self):
        r = subprocess.run([str(self.sh), 'run', '--rm', 'img', 'exit7'], capture_output=True, text=True, env=self.env, timeout=20)
        self.assertEqual(r.returncode, 7)
        self.assertRegex(self.log.read_text(), r'run .*--name=otc-\d+-\d+')

    def test_term_stops_the_named_container(self):
        import signal, time
        p = subprocess.Popen([str(self.sh), 'run', '--rm', '--name', 'mine', 'img'], env=self.env)
        for _ in range(50):
            if self.log.exists() and 'run' in self.log.read_text(): break
            time.sleep(0.1)
        p.send_signal(signal.SIGTERM)
        p.wait(timeout=20)
        self.assertEqual(p.returncode, 143)
        self.assertIn('stop -t 20 mine', self.log.read_text())

    def test_detached_and_interactive_runs_are_exec_d_untouched(self):
        for flag in ('-d', '-i'):
            self.log.write_text('')
            subprocess.run([str(self.sh), 'run', flag, 'img', 'exit7'], capture_output=True, env=self.env, timeout=20)
            self.assertNotIn('--name=otc-', self.log.read_text())


if __name__ == '__main__':
    unittest.main()
