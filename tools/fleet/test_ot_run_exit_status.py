"""P-FALSE-GREEN: the real exit code (1, 3) of a job comes back through ot-heavy-exit; the false-green command shapes are linted."""
import importlib.machinery, importlib.util, os, subprocess, tempfile, unittest
from pathlib import Path

HERE = Path(__file__).parent
loader = importlib.machinery.SourceFileLoader('ot_run_es', str(HERE / 'ot-run'))
spec = importlib.util.spec_from_loader(loader.name, loader)
m = importlib.util.module_from_spec(spec)
loader.exec_module(m)


class ExitStatus(unittest.TestCase):
    def run_exit(self, rc):
        with tempfile.TemporaryDirectory() as t:
            env = dict(os.environ)
            # ot-heavy-exit uses /var/tmp/ot-heavy; the status path under test is the child's wait status
            r = subprocess.run(['bash', str(HERE / 'ot-heavy-exit'), f'oth-test-{os.getpid()}-{rc}', 'bash', '-c', f'exit {rc}'],
                               capture_output=True, text=True, env=env)
            try:
                os.unlink(f'/var/tmp/ot-heavy/completions/oth-test-{os.getpid()}-{rc}')
            except OSError:
                pass
            return r.returncode

    def test_real_codes(self):
        for rc in (1, 3):
            self.assertEqual(self.run_exit(rc), rc)

    def test_lint(self):
        self.assertTrue(m.pipe_lint(['bash', '-c', 'python3 x.py | tee log']))
        self.assertTrue(m.pipe_lint(['bash', '-c', 'python3 x.py; echo GEN_RC=$?']))
        self.assertFalse(m.pipe_lint(['bash', '-c', 'set -o pipefail; python3 x.py | tee log']))
        self.assertFalse(m.pipe_lint(['bash', '-c', 'python3 x.py; rc=$?; echo done; exit $rc']))
        self.assertFalse(m.pipe_lint(['python3', 'x.py']))

    def test_script_file(self):
        with tempfile.TemporaryDirectory() as t:
            Path(t, 'gen.sh').write_text('#!/bin/bash\nfalse\necho GEN_RC=$?\n')
            self.assertTrue(m.pipe_lint(['bash', 'gen.sh'], t))
            Path(t, 'ok.sh').write_text('#!/bin/bash\nset -e\nfalse\necho x\n')
            self.assertFalse(m.pipe_lint(['bash', 'ok.sh'], t))


if __name__ == '__main__':
    unittest.main()
