"""Exercise wrapper failures without EDA jobs or modification of frozen runs."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'physical/s81_ph_views/common/route_view.sh'


class RouteEvidenceTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='.s81-route-test-', dir=ROOT)
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.src = self.base / 'src'
        ports = self.src / 'physical/s81_ph_views/ports/contract/test'
        ports.mkdir(parents=True)
        (ports / 'ports.json').write_text('{"w_um": 100, "h_um": 100}')
        (ports / 'io_place.tcl').write_text('# test\n')
        common = self.src / 'physical/s81_ph_views/common'
        common.mkdir(parents=True)
        (common / 'io_vclk_m_770.sdc').write_text('# test\n')
        (self.src / 'SOURCE_COMMIT').write_text('test-source\n')
        bindir = self.base / 'bin'
        bindir.mkdir()
        mock = bindir / 'python3'
        mock.write_text(f'''#!{sys.executable}
import os, sys
from pathlib import Path
if sys.argv[1] == '-c':
    os.execv({sys.executable!r}, [{sys.executable!r}] + sys.argv[1:])
name = Path(sys.argv[1]).name
stage = {{'run_abi3_physical.py':'route', 'corner_sta.py':'corner',
         'hbm_fmax_attn_abstract.py':'export', 's81_ph_views.py':'check'}}[name]
with open(os.environ['CALLS'], 'a') as f: f.write(stage + '\\n')
if stage == 'route': Path(sys.argv[sys.argv.index('--output')+1]).write_text('{{"frozen":true}}')
print(stage + ' diagnostic')
sys.exit(37 if os.environ.get('FAIL_STAGE') == stage else 0)
''')
        mock.chmod(0o755)
        admit = bindir / 'admit.sh'
        admit.write_text('#!/bin/bash\nshift 2\nexec "$@"\n')
        admit.chmod(0o755)
        self.script = self.base / 'route.sh'
        self.script.write_text(SCRIPT.read_text().replace('/srv/opentallas-scratch/admit.sh', str(admit)))
        self.calls = self.base / 'calls'
        self.env = dict(os.environ, SRC=str(self.src), OUT=str(self.base / 'out'),
                        PATH=str(bindir)+os.pathsep+os.environ['PATH'], CALLS=str(self.calls))
        self.run_dir = self.base / 'out/test'

    def run_route(self, fail='', calibrate=False):
        args = ['bash', str(self.script), 'test', 'contract', 'test', 'test.sv']
        if calibrate:
            args += ['--pnr-stop-after', 'cts']
        return subprocess.run(args, env=dict(self.env, FAIL_STAGE=fail), capture_output=True, text=True)

    def test_route_failure_and_immutable_retry(self):
        self.assertEqual(self.run_route('route').returncode, 37)
        self.assertEqual(self.calls.read_text(), 'route\n')
        before = {p.name: p.read_bytes() for p in self.run_dir.iterdir() if p.is_file()}
        retry = self.run_route()
        self.assertEqual(retry.returncode, 73, retry.stderr)
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.run_dir.iterdir() if p.is_file()})
        self.assertEqual(self.calls.read_text(), 'route\n')

    def test_calibration_failure(self):
        self.assertEqual(self.run_route('route', calibrate=True).returncode, 37)
        self.assertEqual((self.run_dir / 'exit').read_text(), 'rc=37\n')

    def test_calibration_success(self):
        result = self.run_route(calibrate=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.calls.read_text(), 'route\n')

    def test_corner_failure(self):
        self.assertEqual(self.run_route('corner').returncode, 37)
        self.assertEqual(self.calls.read_text(), 'route\ncorner\n')

    def test_export_failure(self):
        self.assertEqual(self.run_route('export').returncode, 37)
        self.assertEqual(self.calls.read_text(), 'route\ncorner\nexport\n')

    def test_check_failure(self):
        self.assertEqual(self.run_route('check').returncode, 37)
        self.assertIn('check_rc=37', (self.run_dir / 'exit').read_text())

    def test_success(self):
        result = self.run_route()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.run_dir / 'exit').read_text(),
                         'rc=0\ncorner_rc=0\nexport_rc=0\ncheck_rc=0\nDONE\n')


if __name__ == '__main__':
    unittest.main()
