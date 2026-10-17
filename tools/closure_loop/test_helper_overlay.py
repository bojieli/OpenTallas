"""Actual gate packing and route helper transport share frozen effective contents."""
import hashlib
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

    def test_later_main_drift_reuses_exact_committed_execution_without_writes(self):
        _, binding = self.gate()
        job = {'freeze_helper_overlay': True, 'route_overlay_plan': binding['route_overlay_plan']}
        run = Path(self.tmp.name) / 'run'
        CL.ship_helpers('local', str(run), job)
        before = (run / 'cl/orfs_hold_mm.tcl').read_bytes()
        self.commit_helper(b'# helper changed after gate and first route ship\n')
        self.assertFalse(SB.validate(binding, self.root, self.daemon, self.tip)[0])
        mtime = (run / 'cl/orfs_hold_mm.tcl').stat().st_mtime_ns
        CL.ship_helpers('local', str(run), job)
        self.assertEqual((run / 'cl/orfs_hold_mm.tcl').read_bytes(), before)
        self.assertEqual((run / 'cl/orfs_hold_mm.tcl').stat().st_mtime_ns, mtime)
        self.assertFalse(job['helper_overlay_verification']['mutation'])
        self.assertEqual(job['route_overlay_plan']['origin_main'], self.tip)

    def test_bench_relocation_preserves_executed_helpers_after_main_changes(self):
        job, original = self.installed_job()
        before = (original / 'cl/orfs_hold_mm.tcl').read_bytes()
        mtime = (original / 'cl/orfs_hold_mm.tcl').stat().st_mtime_ns
        self.commit_helper(b'# later main must not enter the old bench\n')
        destination = Path(self.tmp.name) / 'bench'
        relocated = dict(job, bench_helper_origin=dict(host='local', run=str(original)))
        CL.ship_helpers('local', str(destination), relocated)
        self.assertEqual((destination / 'cl/orfs_hold_mm.tcl').read_bytes(), before)
        self.assertEqual((original / 'cl/orfs_hold_mm.tcl').stat().st_mtime_ns, mtime)
        self.assertEqual(HO.verify_installed_plan(destination / 'cl', job['route_overlay_plan'])['status'],
                         'verified_original')

    def test_bench_relocation_refuses_changed_original_helpers(self):
        job, original = self.installed_job()
        (original / 'cl/orfs_hold_mm.tcl').write_bytes(b'# corrupted executed helper\n')
        destination = Path(self.tmp.name) / 'bench'
        relocated = dict(job, bench_helper_origin=dict(host='local', run=str(original)))
        with self.assertRaisesRegex(ValueError, 'FROZEN_HELPER_OVERLAY.*bytes mismatch'):
            CL.ship_helpers('local', str(destination), relocated)
        self.assertFalse((destination / 'cl').exists())

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
        CL.ship_helpers('local', str(run), job)
        (run / 'cl/orfs_hold_mm.tcl').chmod(0o755)
        with self.assertRaisesRegex(ValueError, 'FROZEN_HELPER_OVERLAY.*mode mismatch'):
            CL.ship_helpers('local', str(run), job)
        damaged = dict(frozen, content_sha256='not-the-original-digest')
        current, _ = HO.capture_plan(self.daemon, self.root)
        self.assertFalse(HO.compare_plans(damaged, current)[0])

    def installed_job(self):
        _, binding = self.gate()
        job = {'freeze_helper_overlay': True, 'route_overlay_plan': binding['route_overlay_plan']}
        run = Path(self.tmp.name) / 'run'
        CL.ship_helpers('local', str(run), job)
        return job, run

    def test_missing_or_tampered_executed_helper_is_not_repaired(self):
        for damaged in (None, b'# different executed helper\n'):
            with self.subTest(damaged=damaged):
                job, run = self.installed_job()
                path = run / 'cl/orfs_hold_mm.tcl'
                path.unlink() if damaged is None else path.write_bytes(damaged)
                with self.assertRaisesRegex(ValueError, 'FROZEN_HELPER_OVERLAY.*(missing|bytes mismatch)'):
                    CL.ship_helpers('local', str(run), job)
                self.assertEqual(path.read_bytes() if path.exists() else None, damaged)
                # Restore this test fixture only before the next independent case.
                path.write_bytes(self.new)

    def test_missing_sidecar_cannot_relabel_existing_files(self):
        job, run = self.installed_job()
        (run / 'cl/helper_overlay_plan.json').unlink()
        with self.assertRaisesRegex(ValueError, 'sidecar is missing'):
            CL.ship_helpers('local', str(run), job)

    def test_missing_job_plan_cannot_overwrite_executed_helpers(self):
        job, run = self.installed_job()
        before = (run/'cl/orfs_hold_mm.tcl').read_bytes()
        del job['route_overlay_plan']
        self.commit_helper(b'# later current helper\n')
        with self.assertRaisesRegex(ValueError, 'original job helper plan is missing'):
            CL.ship_helpers('local', str(run), job)
        self.assertEqual((run/'cl/orfs_hold_mm.tcl').read_bytes(),before)

    def test_missing_directory_reinstalls_exact_committed_bytes(self):
        # el1014-root-frozen-helper: move_to_other_host gives an installed job a fresh run directory.
        import shutil
        job, run = self.installed_job()
        before = (run/'cl/orfs_hold_mm.tcl').read_bytes()
        self.commit_helper(b'# later main must not enter the reinstall\n')
        shutil.rmtree(run/'cl')
        moved = Path(self.tmp.name)/'moved'
        CL.ship_helpers('local', str(moved), job)
        self.assertEqual((moved/'cl/orfs_hold_mm.tcl').read_bytes(), before)
        self.assertEqual(HO.verify_installed_plan(moved/'cl', job['route_overlay_plan'])['status'], 'verified_original')
        self.assertEqual(job['helper_overlay_reinstalls'][-1]['source'], 'committed_origin')
        CL.ship_helpers('local', str(moved), job)   # the reinstalled directory then verifies without writes
        self.assertFalse(job['helper_overlay_verification']['mutation'])

    def test_missing_directory_reinstalls_daemon_only_bytes_from_content_store(self):
        import shutil
        literal = b'# genuine daemon-only bytes\n'
        (self.daemon / self.rel).write_bytes(literal)
        job = {'freeze_helper_overlay': True}
        run = Path(self.tmp.name)/'run'
        CL.ship_helpers('local', str(run), job)
        self.assertTrue((CL.HELPER_STORE/hashlib.sha256(literal).hexdigest()).exists())
        (self.daemon / self.rel).write_bytes(b'# daemon changed later\n')
        shutil.rmtree(run/'cl')
        CL.ship_helpers('local', str(run), job)
        self.assertEqual((run/'cl/orfs_hold_mm.tcl').read_bytes(), literal)
        self.assertEqual(job['helper_overlay_reinstalls'][-1]['source'], 'content_store')

    def test_missing_directory_refuses_when_bytes_unrecoverable(self):
        import shutil
        literal = b'# daemon-only bytes never stored\n'
        (self.daemon / self.rel).write_bytes(literal)
        job = {'freeze_helper_overlay': True}
        run = Path(self.tmp.name)/'run'
        CL.ship_helpers('local', str(run), job)
        (CL.HELPER_STORE/hashlib.sha256(literal).hexdigest()).write_bytes(b'# tampered store\n')
        shutil.rmtree(run/'cl')
        with self.assertRaisesRegex(ValueError, 'directory is missing and its exact bytes are not recoverable'):
            CL.ship_helpers('local', str(run), job)
        self.assertFalse((run/'cl/orfs_hold_mm.tcl').exists())

    def test_valid_digest_does_not_hide_committed_tree_mismatch(self):
        job, run = self.installed_job()
        original = job['route_overlay_plan']
        other = self.commit_helper(b'# different committed path\n')
        damaged = dict(original, origin_main=other)
        job['route_overlay_plan'] = damaged
        (run / 'cl/helper_overlay_plan.json').write_text(__import__('json').dumps(damaged))
        with self.assertRaisesRegex(ValueError, 'committed tree mismatch'):
            CL.ship_helpers('local', str(run), job)

    def test_missing_tree_and_blob_hash_tampering_are_refused(self):
        _, binding = self.gate()
        frozen = binding['route_overlay_plan']
        with self.assertRaisesRegex(ValueError, 'committed tree unavailable'):
            HO.committed_frozen_payloads(self.root, dict(frozen, origin_main='0'*40))
        damaged = __import__('copy').deepcopy(frozen)
        damaged['files'][0]['sha256'] = '0'*64
        damaged['content_sha256'] = HO.digest(damaged['files'])
        with self.assertRaisesRegex(ValueError, 'bytes missing or tampered'):
            HO.committed_frozen_payloads(self.root, damaged)

    def test_new_job_still_resolves_current_helpers_and_old_uninstalled_plan_refuses(self):
        _, binding = self.gate()
        self.commit_helper(b'# new current helper\n')
        job = {'name': 'u', 'events': [], 'freeze_helper_overlay': True, 'route_overlay_plan': binding['route_overlay_plan']}
        with patch.object(CL, 'HELPER_STORE', Path(self.tmp.name)/'store'):          # AUTO FROZEN-REPLAY of the gate's set
            CL.ship_helpers('local', str(Path(self.tmp.name)/'uninstalled'), job)
        self.assertEqual((Path(self.tmp.name)/'uninstalled/cl/orfs_hold_mm.tcl').read_bytes(), self.new)
        self.assertTrue(job['helper_overlay_replays'])
        fresh = {'freeze_helper_overlay': True}
        run = Path(self.tmp.name)/'fresh'
        CL.ship_helpers('local', str(run), fresh)
        self.assertEqual((run/'cl/orfs_hold_mm.tcl').read_bytes(), b'# new current helper\n')

    def test_lint_only_drift_ships_frozen_bytes(self):
        _, binding = self.gate()
        frozen_plan = binding['route_overlay_plan']
        self.commit_helper(b'# lint constants changed after the gate\n')
        job = {'name': 'lint-t', 'events': [], 'freeze_helper_overlay': True, 'route_overlay_plan': frozen_plan}
        run = Path(self.tmp.name)/'lintrun'
        with patch.object(HO, 'LINT_ONLY', (self.rel,)), patch.object(CL, 'HELPER_STORE', Path(self.tmp.name)/'store'):
            CL.ship_helpers('local', str(run), job)
        self.assertEqual((run/'cl/orfs_hold_mm.tcl').read_bytes(), self.new)            # the frozen bytes, not main's
        self.assertEqual(job['route_overlay_plan']['content_sha256'], frozen_plan['content_sha256'])
        self.assertEqual(job['helper_overlay_sanctioned'][0]['kind'], 'lint_frozen')
        self.assertEqual(HO.verify_installed_plan(run/'cl', job['route_overlay_plan'])['status'], 'verified_original')

    def test_frozen_replay_ships_gate_bytes_after_any_main_drift(self):
        _, binding = self.gate()
        frozen_plan = binding['route_overlay_plan']
        self.commit_helper(b'# behaviour change after the gate\n')
        job = {'name': 'replay-t', 'events': [], 'freeze_helper_overlay': True, 'route_overlay_plan': frozen_plan}
        job['replay_frozen_helpers'] = {'at': 'now'}
        run = Path(self.tmp.name)/'r1'
        with patch.object(CL, 'HELPER_STORE', Path(self.tmp.name)/'store'):
            CL.ship_helpers('local', str(run), job)
        self.assertEqual((run/'cl/orfs_hold_mm.tcl').read_bytes(), self.new)
        self.assertEqual(HO.verify_installed_plan(run/'cl', frozen_plan)['status'], 'verified_original')

    def test_lint_only_foreign_blob_still_refuses(self):
        _, binding = self.gate()
        self.commit_helper(b'# later main\n')
        (self.daemon/self.rel).write_bytes(b'# daemon-only edit\n')
        job = {'name': 'l2', 'events': [], 'freeze_helper_overlay': True, 'route_overlay_plan': binding['route_overlay_plan']}
        with patch.object(HO, 'LINT_ONLY', (self.rel,)), patch.object(CL, 'HELPER_STORE', Path(self.tmp.name)/'store'):
            CL.ship_helpers('local', str(Path(self.tmp.name)/'lint2'), job)          # not lint-sanctioned: full replay
        self.assertEqual((Path(self.tmp.name)/'lint2/cl/orfs_hold_mm.tcl').read_bytes(), self.new)
        self.assertTrue(job['helper_overlay_replays'])

    def test_negative_metrics_are_still_rejected_after_honest_recovery(self):
        job, run = self.installed_job()
        self.commit_helper(b'# unrelated later tool fix\n')
        CL.ship_helpers('local', str(run), job)
        for metrics in ({'tt_ps':-55.31,'ff_ps':4.38,'drc':0},
                        {'tt_ps':20,'ff_ps':-0.4,'drc':0},
                        {'tt_ps':1e16,'ff_ps':10,'drc':0}):
            self.assertFalse(CL.eco_passes(metrics, 0), metrics)
        self.assertTrue(CL.eco_passes({'tt_ps':0,'ff_ps':0,'drc':0},0))

    def recovered_gate(self):
        import hashlib
        data, binding = self.gate()
        staged = Path(self.tmp.name)/'staged'
        staged.mkdir()
        with tarfile.open(fileobj=io.BytesIO(data)) as archive:
            archive.extractall(staged)
        script = b'original executed gate script'
        binding['remote_script_sha256'] = hashlib.sha256(script).hexdigest()
        identity = binding.get('commit') or 'snapshot-sha256:'+binding['manifest_sha256']
        (staged/'SOURCE_COMMIT').write_text(identity)
        log = ('GATE_SOURCE_ARCHIVE_SHA256='+binding['archive_sha256']+'\n').encode()
        recovered = SB.recover_verified_snapshot(binding,staged,log,script)
        receipt = HO.verify_staged_helpers(staged,binding['route_overlay_plan'],[self.rel])
        receipt['manifest_sha256'] = binding['manifest_sha256']
        recovered['helper_recovery'] = receipt
        return staged,recovered

    def test_explicit_gate_recovery_preserves_old_identity_but_new_submission_stays_current(self):
        staged,binding = self.recovered_gate()
        before = binding['identity'],binding['start_commit'],binding['commit'],binding['manifest_sha256']
        self.commit_helper(b'# later effective main change\n')
        self.assertFalse(SB.validate(binding,self.root,self.daemon,self.tip)[0])
        self.assertTrue(SB.validate(binding,self.root,self.daemon,self.tip,frozen_recovery=True)[0])
        self.assertEqual(before,(binding['identity'],binding['start_commit'],binding['commit'],binding['manifest_sha256']))
        self.assertFalse(SB.validate(binding,self.root,self.daemon,self.tip,route_overlay=False,frozen_recovery=True)[0])

    def test_gate_original_helper_missing_bytes_mode_and_forged_receipt_refuse(self):
        staged,binding = self.recovered_gate()
        plan = binding['route_overlay_plan']
        path = staged/self.rel
        path.write_bytes(b'# changed actual gate bytes\n')
        with self.assertRaisesRegex(ValueError,'bytes mismatch'):
            HO.verify_staged_helpers(staged,plan,[self.rel])
        path.unlink()
        with self.assertRaisesRegex(ValueError,'missing'):
            HO.verify_staged_helpers(staged,plan,[self.rel])
        path.write_bytes(self.new);path.chmod(0o755)
        with self.assertRaisesRegex(ValueError,'mode mismatch'):
            HO.verify_staged_helpers(staged,plan,[self.rel])
        binding['helper_recovery']['manifest_sha256'] = '0'*64
        self.assertFalse(SB.validate(binding,self.root,self.daemon,self.tip,frozen_recovery=True)[0])

    def test_daemon_only_snapshot_cannot_gain_committed_recovery_identity(self):
        (self.daemon/self.rel).write_bytes(b'# uncommitted original daemon helper\n')
        _,binding = self.recovered_gate()
        self.assertIsNone(binding['commit'])
        self.assertFalse(SB.validate(binding,self.root,self.daemon,self.tip,frozen_recovery=True)[0])

    def test_gate_recovery_does_not_waive_changed_producer_source(self):
        (self.root/'tools/producer.v').write_text('module producer; endmodule\n')
        self.git('add','tools/producer.v');self.git('commit','-m','producer input')
        self.tip = self.git('rev-parse','HEAD')
        self.git('update-ref','refs/remotes/origin/main',self.tip)
        _,binding = self.recovered_gate()
        original = self.tip
        (self.root/'tools/producer.v').write_text('module producer; wire changed; endmodule\n')
        self.git('add','tools/producer.v');self.git('commit','-m','different producer')
        later = self.git('rev-parse','HEAD')
        self.git('update-ref','refs/remotes/origin/main',later)
        self.assertFalse(SB.validate(binding,self.root,self.daemon,later,frozen_recovery=True)[0])
        self.assertTrue(SB.validate(binding,self.root,self.daemon,original,frozen_recovery=True)[0])

    def test_original_tree_must_be_committed_main_history_not_an_unmerged_branch(self):
        _,binding = self.gate()
        self.git('checkout','-b','private-tool-change')
        (self.root/self.rel).write_bytes(b'# private helper\n')
        self.git('add',self.rel);self.git('commit','-m','not on main')
        private = self.git('rev-parse','HEAD')
        frozen,_ = HO.capture_plan(self.daemon,self.root,head=private)
        with self.assertRaisesRegex(ValueError,'not retained main history'):
            HO.committed_frozen_payloads(self.root,frozen)

    def test_existing_live_job_without_freeze_marker_is_not_rewritten(self):
        job = {'status': 'RUNNING'}
        run = Path(self.tmp.name) / 'legacy-live'
        CL.ship_helpers('local', str(run), job)
        self.assertEqual(job, {'status': 'RUNNING'})
        self.assertEqual((run / 'cl/orfs_hold_mm.tcl').read_bytes(), self.new)


    def test_fleet_run_helper_drift_to_main_is_sanctioned_and_recorded(self):
        _, binding = self.gate()
        gate_plan = binding['route_overlay_plan']
        newest = b'# fleet copy fix on main\n'
        tip = self.commit_helper(newest)
        job = {'freeze_helper_overlay': True, 'route_overlay_plan': gate_plan}
        run = Path(self.tmp.name) / 'sanctioned'
        with patch.object(HO, 'FLEET_RUN', (self.rel,)), patch.object(CL, 'event'):
            CL.ship_helpers('local', str(run), job)
        self.assertEqual((run / 'cl/orfs_hold_mm.tcl').read_bytes(), newest)
        self.assertEqual(job['route_overlay_plan_gate'], gate_plan)
        self.assertEqual(job['route_overlay_plan']['origin_main'], tip)
        row = job['helper_overlay_sanctioned'][0]
        self.assertEqual((row['path'], row['frozen_git_blob'], row['current_git_blob']),
                         (self.rel, HO.blob_id(self.new), HO.blob_id(newest)))
        self.assertEqual(row['current_sha256'], hashlib.sha256(newest).hexdigest())
        # the executed (re-frozen) plan now verifies in place without mutation
        CL.ship_helpers('local', str(run), job)
        self.assertFalse(job['helper_overlay_verification']['mutation'])

    def test_fleet_run_sanction_refuses_frozen_blob_outside_main_history(self):
        foreign = b'# never on main\n'
        (self.daemon / self.rel).write_bytes(foreign)
        frozen, _ = HO.capture_plan(self.daemon, self.root)          # daemon_only resolution
        (self.daemon / self.rel).write_bytes(self.old)
        current, _ = HO.capture_plan(self.daemon, self.root)
        with patch.object(HO, 'FLEET_RUN', (self.rel,)):
            ok, why, rows = HO.compare_plans_sanctioned(frozen, current, self.root)
        self.assertFalse(ok)
        self.assertIn('not an earlier main revision', why)
        self.assertEqual(rows, [])

    def test_snapshot_refresh_copies_only_main_bytes(self):
        sh = CL.snapshot_refresh_sh('/run')
        sha = hashlib.sha256(self.new).hexdigest()
        self.assertIn(f'= {sha} ]', sh)
        self.assertIn('/run/cl/orfs_hold_mm.tcl', sh)
        self.assertNotIn('for fd in', sh)

if __name__ == '__main__':
    unittest.main()


class FrozenReplayUnrecoverable(unittest.TestCase):
    def test_unrecoverable_frozen_set_still_refuses(self):
        frozen = {'schema': HO.SCHEMA, 'origin_main': '0'*40, 'files': [{'path': 'tools/x.tcl', 'sha256': '1'*64,
                  'git_blob': '2'*40, 'mode': 420, 'resolution': 'same'}]}
        frozen['content_sha256'] = HO.digest(frozen['files'])
        with self.assertRaises(ValueError):
            HO.recover_frozen_payloads(Path(tempfile.mkdtemp()), None, frozen)
