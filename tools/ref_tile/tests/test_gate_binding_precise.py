"""Precise gate binding (2026-10-14): a gate is bound to the exact route source commit and to the daemon overlays it
EXECUTED (pre_route_gate.SHIP_HELPERS); route-only helper drift never invalidates it.  Regressions for the three
refusals diagnosed on 10-14 (el1014-root-gate-binding.log):
  lkep_ctrl_phy_data_ref-statuscut3 / hbm_native_bounded_cdc_w16 clockpath2 (06:39 / 08:08): textbook_lint.py, a
    gate-executed overlay, changed (ab4968944)               -> still refused, message names tools/textbook_lint.py
  qfd_su_lane_t_io-io1 (11:23): textbook_lint.py changed (2a5f2e867)  -> still refused, names it
  hgi_smmv_eng_de-pinreg1 (11:29): route-only ck_insertion.py changed (56937833c) on top of textbook_lint.py
    -> refused only for textbook_lint.py; ck_insertion.py drift alone passes and the route freezes today's plan."""
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

GATE = 'tools/textbook_lint.py'                 # shipped + executed by the gate (SHIP_HELPERS)
ROUTE = 'tools/closure_loop/ck_insertion.py'    # route-plan helper only (the gate runs the source-commit copy)


class PreciseGateBinding(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root, self.daemon = Path(self.tmp.name) / 'repo', Path(self.tmp.name) / 'daemon'
        for d in (self.root / 'tools/closure_loop', self.daemon / 'tools/closure_loop', self.root / 'kit'):
            d.mkdir(parents=True)
        self.git('init')
        self.git('config', 'user.name', 'Test')
        self.git('config', 'user.email', 'test@example.com')
        (self.root / 'kit/input.v').write_text('module m; endmodule\n')
        self.tip = self.commit({GATE: b'# lint v1\n', ROUTE: b'# ck v1\n'})
        for rel in (GATE, ROUTE):
            (self.daemon / rel).write_bytes((self.root / rel).read_bytes())
        self.stack = [patch.object(PG, 'ROOT', self.root), patch.object(PG, 'DAEMON_TREE', self.daemon),
                      patch.object(PG, 'SHIP_HELPERS', (GATE,)),
                      patch.object(HO, 'HELPERS', ('../textbook_lint.py', 'ck_insertion.py'))]
        for p in self.stack:
            p.start()
        plan, payloads = HO.capture_plan(self.daemon, self.root)
        data = PG.ship_tar({'kit', 'tools'}, payloads, {f['path']: f['mode'] for f in plan['files']})
        self.binding = SB.snapshot(data, self.root, self.tip, self.daemon, None, (GATE,))
        self.binding.update(route_overlay_plan=plan, remote_archive_verified=True)
        (self.root / 'kit/gate_result.json').write_text(json.dumps(
            {'source_binding': self.binding, 'clock': {'max_root_sinks': 9000, 'verdict': 'PASS'}}))

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
        """a daemon tool sync: main moves and the daemon copy follows"""
        self.commit({rel: data})
        (self.daemon / rel).write_bytes(data)

    def gate(self):
        g = PG.Gate()
        PG.check_clock_evidence(g, self.root / 'kit', source_commit=self.tip)
        return g

    def test_unchanged_passes_and_keeps_frozen_plan(self):
        ok, why = SB.validate(self.binding, self.root, self.daemon, self.tip)
        self.assertTrue(ok, why)
        g = self.gate()
        self.assertNotEqual(g.verdict, 'FAIL')
        self.assertEqual(g.route_overlay_plan, self.binding['route_overlay_plan'])

    def test_route_only_helper_sync_does_not_invalidate_gate(self):
        # hgi_smmv_eng_de-pinreg1 without the textbook_lint change: only ck_insertion.py (route plan) moved
        self.sync_daemon(ROUTE, b'# ck v2 --raw-source\n')
        ok, why = SB.validate(self.binding, self.root, self.daemon, self.tip)
        self.assertTrue(ok, why)
        self.assertIn(ROUTE, why)
        g = self.gate()
        self.assertNotIn('FAIL', [i['severity'] for i in g.items if i['check'] == 'source_binding'])
        rows = {r['path']: r for r in g.route_overlay_plan['files']}
        self.assertEqual(rows[ROUTE]['git_blob'], HO.blob_id(b'# ck v2 --raw-source\n'))   # route freezes today's helper
        self.assertEqual(g.route_overlay_plan['gate_verified_paths'], [GATE])
        ok, why = HO.compare_plans(g.route_overlay_plan, HO.capture_plan(self.daemon, self.root)[0])
        self.assertTrue(ok, why)                                                            # ship_helpers will accept it

    def test_lkep_statuscut3_gate_executed_overlay_change_still_refuses_and_names_file(self):
        self.sync_daemon(GATE, b'PIN_REGISTER_PAIR_MAX_PS = 600.0\n')       # gate-relevant pin_register constant
        ok, why = SB.validate(self.binding, self.root, self.daemon, self.tip)
        self.assertFalse(ok)
        self.assertIn(GATE, why)
        g = self.gate()
        fail = [i for i in g.items if i['check'] == 'source_binding' and i['severity'] == 'FAIL']
        self.assertTrue(fail and GATE in fail[0]['message'], g.items)

    def test_qfd_su_lane_t_io_second_textbook_change_refuses(self):
        self.sync_daemon(GATE, b'PIN_LAUNCH_MAX_PS = 230.0\n')                # a gate-relevant constant changes
        self.sync_daemon(GATE, b'PIN_LAUNCH_MAX_PS = 240.0\n')
        ok, why = SB.validate(self.binding, self.root, self.daemon, self.tip)
        self.assertFalse(ok)
        self.assertEqual(why, f'gate-executed daemon overlay changed: {GATE}')

    def test_submit_only_lint_change_keeps_the_gate_valid(self):
        self.sync_daemon(GATE, b'# lint v1\nCLOSED_STANDS_KINDS = ("a", "native_capture")\n')
        ok, why = SB.validate(self.binding, self.root, self.daemon, self.tip)
        self.assertTrue(ok, why)
        self.assertIn('lint-only drift tolerated', why)

    def test_hgi_smmv_pinreg1_names_only_the_gate_relevant_file(self):
        self.sync_daemon(GATE, b'PIN_LAUNCH_MAX_PS = 230.0\n')
        self.sync_daemon(ROUTE, b'# ck v2\n')
        ok, why = SB.validate(self.binding, self.root, self.daemon, self.tip)
        self.assertFalse(ok)
        self.assertIn(GATE, why)
        self.assertNotIn(ROUTE, why)

    def test_source_commit_difference_still_refuses_and_names_file(self):
        later = self.commit({'kit/input.v': b'module m2; endmodule\n'})
        ok, why = SB.validate(self.binding, self.root, self.daemon, later)
        self.assertFalse(ok)
        self.assertIn('route source differs from staged snapshot: kit/input.v', why)

    def test_tampered_frozen_plan_still_refuses(self):
        b = json.loads(json.dumps(self.binding))
        b['route_overlay_plan']['files'][0]['sha256'] = '0' * 64
        self.assertFalse(SB.validate(b, self.root, self.daemon, self.tip)[0])

    def test_frozen_plan_disagreeing_with_staged_overlay_refuses(self):
        b = json.loads(json.dumps(self.binding))
        plan = b['route_overlay_plan']
        for f in plan['files']:
            if f['path'] == GATE:
                f['sha256'] = '1' * 64
        plan['content_sha256'] = HO.digest(plan['files'])
        ok, why = SB.validate(b, self.root, self.daemon, self.tip)
        self.assertFalse(ok)
        self.assertIn(GATE, why)


if __name__ == '__main__':
    unittest.main()
