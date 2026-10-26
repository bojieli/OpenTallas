"""OFFLOAD-TRIM (ROOT 2026-10-16): offload / previous-host snapshot cleanup of terminal jobs."""
import json, os, subprocess, sys, tempfile, unittest
from pathlib import Path
os.environ.setdefault('CL_STATE', tempfile.mkdtemp(prefix='offload-trim-tests-'))
sys.path[:0] = [str(Path(__file__).resolve().parent), str(Path(__file__).resolve().parent.parent)]
import closure_loop as CL


class OffloadTrim(unittest.TestCase):
    def test_locations_exclude_own_run_and_done(self):
        j = dict(host='h1', run='/r/closure-loop/j', bench_location=dict(host='h2', run='/r/closure-loop/j-bench'),
                 btrack={'b': dict(host='h2', run='/r/closure-loop/j-bench'), 'c': dict(host='h1', run='/r/closure-loop/j')},
                 bench_helper_relocations=[dict(destination=dict(host='h3', run='/r/closure-loop/j'))])
        self.assertEqual(CL.offload_locations(j), [('h2', '/r/closure-loop/j-bench'), ('h3', '/r/closure-loop/j')])
        j['offload_trimmed'] = [dict(host='h2', run='/r/closure-loop/j-bench')]
        self.assertEqual(CL.offload_locations(j), [('h3', '/r/closure-loop/j')])

    def _run_py(self, run, roots):
        env = dict(os.environ, OT_OT=json.dumps(dict(run=run, roots=roots)))
        return subprocess.run([sys.executable, '-'], input=CL.OFFLOAD_TRIM_PY, text=True, capture_output=True, env=env).stdout

    def test_trim_removes_only_snapshots(self):
        t = Path(tempfile.mkdtemp()) / 'closure-loop' / 'j-bench'
        for d in ('src/tools', 'bench_src_a1/rtl', 'cl', 'record'):
            (t / d).mkdir(parents=True)
        (t / 'src/tools/x.py').write_bytes(b'x' * 4096); (t / 'bench_src_a1/rtl/y.sv').write_text('y')
        (t / 'cl/bench.log').write_text('log'); (t / 'record/r.json').write_text('{}')
        out = self._run_py(str(t), [str(t.parent) + '/'])
        self.assertIn('OFFLOAD_FREED', out)
        self.assertEqual(sorted(p.name for p in t.iterdir()), ['cl', 'record'])

    def test_keep_and_foreign_root_skip(self):
        t = Path(tempfile.mkdtemp()) / 'closure-loop' / 'k'
        (t / 'src').mkdir(parents=True); (t / '.keep').write_text('')
        self.assertIn('OFFLOAD_SKIP', self._run_py(str(t), [str(t.parent) + '/']))
        self.assertTrue((t / 'src').exists())
        u = Path(tempfile.mkdtemp()) / 'closure-loop' / 'u'; (u / 'src').mkdir(parents=True)
        self.assertIn('OFFLOAD_SKIP', self._run_py(str(u), ['/elsewhere/']))
        self.assertTrue((u / 'src').exists())


if __name__ == '__main__':
    unittest.main()
