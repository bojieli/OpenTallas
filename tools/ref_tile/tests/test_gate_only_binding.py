"""Gate-only helpers (native_census.py/.tcl, ref_route.sh) are shipped by every new gate beside the frozen route-plan
overlays but are never route-plan members.  validate() must resolve their effective bytes at the same main head:
s81dvbk_hist32_b0r3 (10-20 01:43, byte-identical helpers at 8608a236c) was refused '... native_census.py ... [blob
unknown]' because the frozen-plan branch captured route helpers only.  A real gate-only helper change still refuses."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(HERE), str(HERE.parent / 'closure_loop')]
import helper_overlay as HO
import pre_route_gate as PG
import source_binding as SB

GATE = 'tools/textbook_lint.py'                 # shipped by the gate AND a route-plan helper
GONLY = 'tools/ref_tile/native_census.py'       # shipped by the gate only
ROUTE = 'tools/closure_loop/ck_insertion.py'    # route-plan helper only


class GateOnlyBinding(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root, self.daemon = Path(self.tmp.name) / 'repo', Path(self.tmp.name) / 'daemon'
        for d in (self.root / 'tools/closure_loop', self.root / 'tools/ref_tile', self.daemon / 'tools/closure_loop',
                  self.daemon / 'tools/ref_tile', self.root / 'kit'):
            d.mkdir(parents=True)
        self.git('init')
        self.git('config', 'user.name', 'Test')
        self.git('config', 'user.email', 'test@example.com')
        (self.root / 'kit/input.v').write_text('module m; endmodule\n')
        self.tip = self.commit({GATE: b'# lint v1\n', ROUTE: b'# ck v1\n', GONLY: b'LIMIT = 32\n'})
        for rel in (GATE, ROUTE, GONLY):
            (self.daemon / rel).write_bytes((self.root / rel).read_bytes())
        self.stack = [patch.object(PG, 'ROOT', self.root), patch.object(PG, 'DAEMON_TREE', self.daemon),
                      patch.object(PG, 'SHIP_HELPERS', (GONLY, GATE)),
                      patch.object(PG, 'GATE_ONLY_HELPERS', (GONLY,)),
                      patch.object(SB, 'GATE_ONLY_HELPERS', (GONLY,)),
                      patch.object(HO, 'HELPERS', ('../textbook_lint.py', 'ck_insertion.py'))]
        for p in self.stack:
            p.start()
        plan, payloads = HO.capture_plan(self.daemon, self.root)
        self.assertNotIn(GONLY, payloads)                       # never a route-plan member
        data = PG.ship_tar({'kit', 'tools'}, payloads, {f['path']: f['mode'] for f in plan['files']},
                           overlay_head=plan['origin_main'])
        self.binding = SB.snapshot(data, self.root, self.tip, self.daemon, None, (GONLY, GATE))
        self.binding.update(route_overlay_plan=plan, remote_archive_verified=True)
        src = {e['path']: e['source'] for e in self.binding['files']}
        self.assertEqual(src[GONLY], 'daemon_overlay')

    def tearDown(self):
        for p in reversed(self.stack):
            p.stop()
        self.tmp.cleanup()

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.root), *args], stderr=subprocess.DEVNULL).decode().strip()

    def commit(self, files):
        for rel, data in files.items():
            (self.root / rel).write_bytes(data)
        self.git('add', '-A')
        self.git('commit', '-m', 'update')
        head = self.git('rev-parse', 'HEAD')
        self.git('update-ref', 'refs/remotes/origin/main', head)
        return head

    def sync_daemon(self, rel, data):
        self.commit({rel: data})
        (self.daemon / rel).write_bytes(data)

    def test_byte_identical_gate_only_helper_is_bound_not_blob_unknown(self):
        ok, why = SB.validate(self.binding, self.root, self.daemon, self.tip)
        self.assertTrue(ok, why)
        self.assertNotIn('blob unknown', why)

    def test_unrelated_main_advance_keeps_gate_only_binding(self):
        self.commit({'kit/other.txt': b'x\n'})
        ok, why = SB.validate(self.binding, self.root, self.daemon, self.tip)
        self.assertTrue(ok, why)

    def test_changed_gate_only_helper_still_refuses_and_names_it(self):
        self.sync_daemon(GONLY, b'LIMIT = 31\n')
        ok, why = SB.validate(self.binding, self.root, self.daemon, self.tip)
        self.assertFalse(ok)
        self.assertIn(GONLY, why)


if __name__ == '__main__':
    unittest.main()
