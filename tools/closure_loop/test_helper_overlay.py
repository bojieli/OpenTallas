"""Actual gate packing and route helper transport share frozen effective contents."""
import io
import os
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault('CL_STATE', tempfile.mkdtemp(prefix='helper-overlay-tests-'))
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent / 'ref_tile'), str(HERE.parent)]
import closure_loop as CL
import helper_overlay as HO
import pre_route_gate as PG
import source_binding as SB


class HelperOverlay(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / 'repo'
        self.daemon = Path(self.tmp.name) / 'daemon'
        (self.root / 'tools').mkdir(parents=True)
        (self.daemon / 'tools/closure_loop').mkdir(parents=True)
        self.rel = 'tools/orfs_hold_mm.tcl'
        self.git('init')
        self.git('config', 'user.name', 'Test')
        self.git('config', 'user.email', 'test@example.com')
        self.old = b'# older main helper\n'
        self.new = b'# newer main helper\n'
        self.commit_helper(self.old)
        (self.daemon / self.rel).write_bytes(self.old)
        self.tip = self.commit_helper(self.new)
        self.stack = []
        for p in (patch.object(CL, 'HERE', self.daemon / 'tools/closure_loop'), patch.object(CL, 'REPO', self.root),
                  patch.object(CL, 'HELPERS', ('../orfs_hold_mm.tcl',)), patch.object(HO, 'HELPERS', ('../orfs_hold_mm.tcl',)),
                  patch.object(CL, '_ovl_head', side_effect=lambda: HO.main_head(self.root)),
                  patch.object(CL, '_OVL', {'head': None, 'head_at': 0., 'hist': {}, 'said': set(), 'check_at': 0.}),
                  patch.object(CL, 'log'), patch.object(CL, 'is_local', return_value=True),
                  patch.object(PG, 'ROOT', self.root), patch.object(PG, 'DAEMON_TREE', self.daemon),
                  patch.object(PG, 'SHIP_HELPERS', (self.rel,))):
            p.start()
            self.stack.append(p)

    def tearDown(self):
        for p in reversed(self.stack):
            p.stop()
        self.tmp.cleanup()

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.root), *args], stderr=subprocess.DEVNULL).decode().strip()

    def commit_helper(self, data):
        (self.root / self.rel).write_bytes(data)
        self.git('add', self.rel)
        self.git('commit', '-m', 'helper update')
        head = self.git('rev-parse', 'HEAD')
        self.git('update-ref', 'refs/remotes/origin/main', head)
        return head

    def gate(self):
        plan, payloads = HO.capture_plan(self.daemon, self.root)
        data = PG.ship_tar({'tools'}, payloads)
        binding = SB.snapshot(data, self.root, self.tip, self.daemon, None, (self.rel,))
        binding['route_overlay_plan'] = plan
        return data, binding

    def test_stale_literal_gate_and_route_both_ship_effective_newer_main(self):
        data, binding = self.gate()
        self.assertEqual(CL._ovl_resolve(self.rel), (self.new, 'stale'))
        with tarfile.open(fileobj=io.BytesIO(data)) as tf:
            self.assertEqual(tf.extractfile(self.rel).read(), self.new)
        self.assertTrue(SB.validate(binding, self.root, self.daemon, self.tip)[0])
        job = {'freeze_helper_overlay': True, 'route_overlay_plan': binding['route_overlay_plan']}
        run = Path(self.tmp.name) / 'run'
        CL.ship_helpers('local', str(run), job)
        self.assertEqual((run / 'cl/orfs_hold_mm.tcl').read_bytes(), self.new)
        # Provenance differs from literal daemon; exact content must not claim daemon HEAD.
        self.assertIsNone(binding['commit'])

    def test_later_effective_drift_rejected_before_refresh_changes_existing_run(self):
        _, binding = self.gate()
        job = {'freeze_helper_overlay': True, 'route_overlay_plan': binding['route_overlay_plan']}
        run = Path(self.tmp.name) / 'run'
        CL.ship_helpers('local', str(run), job)
        before = (run / 'cl/orfs_hold_mm.tcl').read_bytes()
        self.commit_helper(b'# helper changed after gate and first route ship\n')
        self.assertFalse(SB.validate(binding, self.root, self.daemon, self.tip)[0])
        with self.assertRaisesRegex(ValueError, 'FROZEN_HELPER_OVERLAY.*drift'):
            CL.ship_helpers('local', str(run), job)
        self.assertEqual((run / 'cl/orfs_hold_mm.tcl').read_bytes(), before)
        self.assertEqual(job['route_overlay_plan']['origin_main'], self.tip)

    def test_unrelated_main_commit_does_not_relabel_or_invalidate_plan(self):
        _, binding = self.gate()
        (self.root / 'unrelated.txt').write_text('unrelated\n')
        self.git('add', 'unrelated.txt')
        self.git('commit', '-m', 'unrelated change')
        self.git('update-ref', 'refs/remotes/origin/main', self.git('rev-parse', 'HEAD'))
        current, _ = HO.capture_plan(self.daemon, self.root)
        self.assertTrue(HO.compare_plans(binding['route_overlay_plan'], current)[0])
        self.assertEqual(binding['route_overlay_plan']['origin_main'], self.tip)

    def test_daemon_only_exact_content_remains_legal_but_later_edit_refuses(self):
        literal = b'# genuine daemon-only bytes\n'
        (self.daemon / self.rel).write_bytes(literal)
        data, binding = self.gate()
        self.assertEqual(CL._ovl_resolve(self.rel), (literal, 'daemon_only'))
        self.assertTrue(SB.validate(binding, self.root, self.daemon, self.tip)[0])
        self.assertIsNone(binding['commit'])
        (self.daemon / self.rel).write_bytes(b'# changed daemon-only bytes\n')
        self.assertFalse(SB.validate(binding, self.root, self.daemon, self.tip)[0])

    def test_mode_drift_and_tampered_plan_are_refused(self):
        _, binding = self.gate()
        frozen = binding['route_overlay_plan']
        job = {'freeze_helper_overlay': True, 'route_overlay_plan': frozen}
        run = Path(self.tmp.name) / 'run'
        CL.ship_helpers('local', str(run), job)
        self.assertEqual((run / 'cl/helper_overlay_plan.json').read_text().strip(), __import__('json').dumps(frozen, indent=1))
        (self.daemon / self.rel).chmod(0o755)
        with self.assertRaisesRegex(ValueError, 'FROZEN_HELPER_OVERLAY.*drift'):
            CL.ship_helpers('local', str(run), job)
        damaged = dict(frozen, content_sha256='not-the-original-digest')
        current, _ = HO.capture_plan(self.daemon, self.root)
        self.assertFalse(HO.compare_plans(damaged, current)[0])

    def test_existing_live_job_without_freeze_marker_is_not_rewritten(self):
        job = {'status': 'RUNNING'}
        run = Path(self.tmp.name) / 'legacy-live'
        CL.ship_helpers('local', str(run), job)
        self.assertEqual(job, {'status': 'RUNNING'})
        self.assertEqual((run / 'cl/orfs_hold_mm.tcl').read_bytes(), self.new)


if __name__ == '__main__':
    unittest.main()
