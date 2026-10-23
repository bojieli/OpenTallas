"""Path-only recovery must preserve route identity, failures and the frozen source."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parent))
import bench_rebind as B


class Rebind(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.root / 'repo'; self.repo.mkdir()
        self.old_text = 'module tb;\n    reg [1023:0] dir, mufile, cfgfile;\n    initial $display("checks unchanged");\nendmodule\n'
        p = self.repo / B.TB; p.parent.mkdir(parents=True); p.write_text(self.old_text)
        (self.repo / 'design.sv').write_text('module design; endmodule\n')
        self.g('init', '-q'); self.commit(); self.old = self.g('rev-parse', 'HEAD').strip()
        p.write_text(self.old_text.replace('    reg [1023:0] dir, mufile, cfgfile;\n', B.NOTE + '    string dir, mufile, cfgfile;\n'))
        self.commit(); self.new = self.g('rev-parse', 'HEAD').strip()
        self.run = self.root / 'run'
        self.stages = {k: dict(key=k, kind='bench', cmd='run {RUN}/' + k) for k in ('bench_bad', 'bench_next')}
        self.job = dict(name='job', status='NEEDS_RTL', reason='bench_bad expected PASS but rc=1', stage_key='verdict',
                        stage_idx=11, bench_par=True, source_synced=True, freeze_helper_overlay=True,
                        route_overlay_plan={'frozen': 'unchanged'}, commit_full=self.old, attempt=1, route_attempt=1,
                        host='host', run=str(self.run), spec={'all_checks': 'unchanged'},
                        benches={'bench_bad': dict(ok=False, rc=1), 'bench_pass': dict(ok=True, rc=0)},
                        btrack={'bench_bad': dict(state='done', n=1, tag='bench_bad.a1b1')}, finished_at='before')

    def g(self, *args):
        return subprocess.check_output(['git', '-C', str(self.repo), *args], text=True)

    def commit(self):
        self.g('add', '.')
        self.g('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '-qm', 'fixture')

    def plan(self):
        return B.plan(self.repo, self.job, self.new, list(self.stages), self.stages)

    def test_exact_path_change_and_all_other_git_objects(self):
        p = self.plan()
        self.assertEqual(p['route_commit'], self.old)
        self.assertEqual(p['source_commit'], self.new)
        self.assertNotEqual(p['old_sha256'], p['new_sha256'])
        for path in ('design.sv', 'clock.sdc', 'child.lib', 'params.json'):
            q = self.repo / path; previous = q.read_text() if q.exists() else None
            q.write_text('unexpected change\n'); self.commit(); changed = self.g('rev-parse', 'HEAD').strip()
            with self.assertRaisesRegex(ValueError, 'route inputs'):
                B.plan(self.repo, self.job, changed, list(self.stages), self.stages)
            self.g('reset', '--hard', self.new)

    def test_changed_checker_or_driver_is_not_a_path_recovery(self):
        p = self.repo / B.TB
        p.write_text(p.read_text().replace('checks unchanged', 'accept without checks'))
        self.commit(); self.new = self.g('rev-parse', 'HEAD').strip()
        with self.assertRaisesRegex(ValueError, 'unsupported testbench'):
            self.plan()

    def test_running_stage_and_successful_receipt_refuse(self):
        self.job['btrack']['bench_bad']['state'] = 'running'
        with self.assertRaisesRegex(ValueError, 'never stops'):
            self.plan()
        self.job['btrack']['bench_bad']['state'] = 'done'
        self.job['benches']['bench_next'] = dict(ok=True)
        with self.assertRaisesRegex(ValueError, 'successful'):
            self.plan()

    def test_state_changes_only_bench_track_and_preserves_old_failure(self):
        p = self.plan(); p.update(id='recovery', source_path=str(self.run / 'bench_rebind/recovery/source'))
        old = copy.deepcopy(self.job)
        B.apply_state(self.job, p, self.stages)
        for field in ('spec', 'host', 'run', 'commit_full', 'attempt', 'route_attempt', 'stage_key', 'stage_idx',
                      'source_synced', 'route_overlay_plan', 'freeze_helper_overlay'):
            self.assertEqual(self.job[field], old[field], field)
        self.assertEqual(self.job['benches']['bench_pass'], old['benches']['bench_pass'])
        self.assertFalse(self.job['bench_rebind_history'][0]['benches']['bench_bad']['ok'])
        self.assertEqual(self.job['status'], 'READY')
        self.assertEqual(self.job['btrack']['bench_bad']['n'], 1)
        self.assertEqual(B.source_for_stage(self.job, 'bench_bad')['source_commit'], self.new)
        self.assertIsNone(B.source_for_stage(self.job, 'bench_pass'))
        self.job['route_attempt'] = 2
        with self.assertRaisesRegex(ValueError, 'different route'):
            B.source_for_stage(self.job, 'bench_bad')

    def remote_fixture(self):
        p = self.plan(); p.update(route_tag='route.a1', id='recovery', outputs=['bench_bad'])
        src = self.run / 'src' / B.TB; src.parent.mkdir(parents=True); src.write_text(self.old_text)
        (self.run / 'cl').mkdir(); (self.run / 'cl/route.a1.rc').write_text('0\n')
        base = self.run / 'routes/design/work/orfs/results/base'; base.mkdir(parents=True)
        for name in ('6_final.odb', '6_final.sdc', '6_final.spef', '5_route.odb'):
            (base / name).write_text(name + '\n')
        out = self.run / 'bench_bad'; out.mkdir(); (out / 'failure.log').write_text('original failed bench\n')
        return p, base

    def remote(self, payload, ok=True):
        r = subprocess.run([sys.executable, '-c', B.REMOTE], input=json.dumps(payload), text=True, capture_output=True)
        self.assertEqual(r.returncode == 0, ok, r.stderr)
        return json.loads(r.stdout) if ok else r.stderr

    def test_real_private_copy_keeps_route_and_frozen_tree_and_old_outputs(self):
        p, base = self.remote_fixture()
        p.update(self.remote(dict(p, action='inspect')))
        before = {x.name: x.read_bytes() for x in base.iterdir()}
        result = self.remote(dict(p, action='prepare'))
        self.assertEqual((self.run / 'src' / B.TB).read_text(), self.old_text)
        self.assertIn('string dir', (Path(result['source_path']) / B.TB).read_text())
        self.assertEqual({x.name: x.read_bytes() for x in base.iterdir()}, before)
        self.assertEqual(result['route_files'], result['route_files_after'])
        self.assertEqual(json.loads((Path(result['source_path']).parent / 'receipt.json').read_text()), result)
        self.assertFalse((self.run / 'bench_bad').exists())
        self.assertEqual((self.run / 'bench_rebind/recovery/previous_outputs/bench_bad/failure.log').read_text(),
                         'original failed bench\n')

    def test_launch_guard_refuses_missing_or_modified_source(self):
        p, base = self.remote_fixture(); p.update(self.remote(dict(p, action='inspect')))
        receipt = self.remote(dict(p, action='prepare'))
        def check():
            return subprocess.run(['bash', '-c', B.launch_guard(receipt)], capture_output=True).returncode
        self.assertEqual(check(), 0)
        tb = Path(receipt['source_path']) / B.TB
        tb.write_text('module bypass; endmodule\n')
        self.assertEqual(check(), 97)
        tb.unlink()
        self.assertEqual(check(), 97)

    def test_route_sha_change_refuses_before_private_copy(self):
        p, base = self.remote_fixture(); p.update(self.remote(dict(p, action='inspect')))
        (base / '6_final.sdc').write_text('changed uncertainty\n')
        self.assertIn('SHA changed', self.remote(dict(p, action='prepare'), ok=False))
        self.assertFalse((self.run / 'bench_rebind').exists())
        self.assertTrue((self.run / 'bench_bad/failure.log').exists())

    def test_failed_route_or_missing_artifact_cannot_rebind(self):
        p, base = self.remote_fixture()
        (self.run / 'cl/route.a1.rc').write_text('1\n')
        self.assertIn('did not complete', self.remote(dict(p, action='inspect'), ok=False))
        (self.run / 'cl/route.a1.rc').write_text('0\n')
        (base / '6_final.spef').unlink()
        self.assertIn('missing/outside', self.remote(dict(p, action='inspect'), ok=False))


if __name__ == '__main__':
    unittest.main()
