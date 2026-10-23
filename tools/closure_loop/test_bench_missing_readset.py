"""Only the exact missing historical S81 bench dependency may be restored."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent))
import bench_rebind as B


class MissingReadset(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name); self.repo = self.root / 'repo'; self.repo.mkdir()
        self.g('init', '-q')
        (self.repo / 'design.sv').write_text('module design; endmodule\n')
        for reader in B.MISSING_READERS:
            p = self.repo / reader; p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text('#!/bin/bash\nsource ' + B.MISSING_DEP + '\necho unchanged-checker\n')
        self.commit(); self.old = self.g('rev-parse', 'HEAD').strip()
        self.body = b"SRCS='design.sv'\n"
        p = self.repo / B.MISSING_DEP; p.parent.mkdir(parents=True); p.write_bytes(self.body)
        self.commit(); self.new = self.g('rev-parse', 'HEAD').strip()
        self.blob = self.g('rev-parse', self.new + ':' + B.MISSING_DEP).strip()
        patches = patch.multiple(B, MISSING_HISTORY=self.new, MISSING_BLOB=self.blob,
                                 MISSING_SHA256=hashlib.sha256(self.body).hexdigest())
        patches.start(); self.addCleanup(patches.stop)
        self.run = self.root / 'run'
        self.stages = {k: dict(key=k, kind='bench', cmd='bash ' + B.MISSING_READERS[i] + ' {RUN}/' + k + ' 0')
                       for i, k in enumerate(('bench_bad', 'bench_next'))}
        self.job = dict(name='job', status='NEEDS_RTL', reason='missing source-list', stage_key='verdict',
                        stage_idx=11, bench_par=True, source_synced=True, freeze_helper_overlay=True,
                        route_overlay_plan={'frozen': 'unchanged'}, commit_full=self.old,
                        attempt=1, route_attempt=1, host='host', run=str(self.run),
                        spec={'block': 'dsfd_coll_lane_w_safe8_ntf'},
                        benches={'bench_bad': dict(ok=False, rc=1)},
                        btrack={'bench_bad': dict(state='done', n=1)}, finished_at='before')

    def g(self, *args):
        return subprocess.check_output(['git', '-C', str(self.repo), *args], text=True)

    def commit(self):
        self.g('add', '.')
        self.g('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '-qm', 'fixture')

    def plan(self, target=None):
        return B.plan(self.repo, self.job, target or self.new, list(self.stages), self.stages)

    def test_exact_addition_preserves_all_existing_objects_and_scope(self):
        row = self.plan()
        self.assertEqual(row['recovery_kind'], 'missing_bench_readset')
        self.assertIsNone(row['old_sha256'])
        self.assertEqual(row['historical_blob'], self.blob)
        self.assertEqual(row['new_sha256'], hashlib.sha256(self.body).hexdigest())
        old = copy.deepcopy(self.job)
        row.update(id='recovery', source_path=str(self.run / 'bench_rebind/recovery/source'))
        B.apply_state(self.job, row, self.stages)
        for key in ('commit_full', 'route_attempt', 'route_overlay_plan', 'spec', 'host', 'run'):
            self.assertEqual(old[key], self.job[key])
        self.assertFalse(self.job['bench_rebind_history'][0]['benches']['bench_bad']['ok'])

    def test_any_physical_source_constraint_or_helper_delta_refuses(self):
        for name in ('design.sv', 'clock.sdc', 'child.lib', 'tools/helper.py'):
            p = self.repo / name; p.parent.mkdir(parents=True, exist_ok=True); p.write_text('changed\n')
            self.commit(); target = self.g('rev-parse', 'HEAD').strip()
            with self.assertRaisesRegex(ValueError, 'route inputs'):
                self.plan(target)
            self.g('reset', '--hard', self.new)

    def test_wrong_historical_blob_or_hash_refuses(self):
        (self.repo / B.MISSING_DEP).write_text('different source list\n'); self.commit()
        with self.assertRaisesRegex(ValueError, 'historical blob'):
            self.plan(self.g('rev-parse', 'HEAD').strip())
        self.g('reset', '--hard', self.new)
        with patch.object(B, 'MISSING_SHA256', '0' * 64):
            with self.assertRaisesRegex(ValueError, 'SHA mismatch'):
                self.plan()
        with patch.object(B, 'MISSING_BLOB', '0' * 40):
            with self.assertRaisesRegex(ValueError, 'historical blob'):
                self.plan()

    def test_existing_file_or_nonmissing_target_refuses(self):
        self.job['commit_full'] = self.new
        (self.repo / B.MISSING_DEP).write_text('replacement\n'); self.commit()
        with self.assertRaisesRegex(ValueError, 'existing file overwrite'):
            self.plan(self.g('rev-parse', 'HEAD').strip())
        with self.assertRaisesRegex(ValueError, 'route inputs'):
            self.plan(self.new)

    def test_wrong_lane_or_undeclared_reader_refuses(self):
        self.job['spec']['block'] = 'different-block'
        with self.assertRaisesRegex(ValueError, 'scoped'):
            self.plan()
        self.job['spec']['block'] = 'dsfd_coll_lane_w_safe8_ntf'
        self.stages['bench_next']['cmd'] = 'bash arbitrary.sh {RUN}/bench_next'
        with self.assertRaisesRegex(ValueError, 'not declared'):
            self.plan()

    def remote(self, payload, ok=True):
        r = subprocess.run([sys.executable, '-c', B.REMOTE], input=json.dumps(payload), text=True, capture_output=True)
        self.assertEqual(r.returncode == 0, ok, r.stderr)
        return json.loads(r.stdout) if ok else r.stderr

    def fixture(self):
        p = self.plan(); p.update(route_tag='route.a1', id='recovery', outputs=['bench_bad'])
        src = self.run / 'src'; src.mkdir(parents=True); (src / 'design.sv').write_text('frozen RTL\n')
        (self.run / 'cl').mkdir(); (self.run / 'cl/route.a1.rc').write_text('0\n')
        base = self.run / 'routes/design/base'; base.mkdir(parents=True)
        for name in ('6_final.odb', '6_final.sdc', '6_final.spef', '5_route.odb'):
            (base / name).write_text(name + '\n')
        out = self.run / 'bench_bad'; out.mkdir(); (out / 'failure.log').write_text('original failure\n')
        return p, src, base

    def test_private_addition_keeps_original_source_route_and_failure(self):
        p, src, base = self.fixture(); p.update(self.remote(dict(p, action='inspect')))
        before = {x.name: x.read_bytes() for x in base.iterdir()}
        receipt = self.remote(dict(p, action='prepare'))
        private = Path(receipt['source_path'])
        self.assertFalse((src / B.MISSING_DEP).exists())
        self.assertEqual((private / B.MISSING_DEP).read_bytes(), self.body)
        self.assertEqual((private / 'design.sv').read_bytes(), (src / 'design.sv').read_bytes())
        self.assertEqual(before, {x.name: x.read_bytes() for x in base.iterdir()})
        self.assertEqual(subprocess.run(['bash', '-c', B.launch_guard(receipt)], capture_output=True).returncode, 0)
        (private / B.MISSING_DEP).write_text('wrong\n')
        self.assertEqual(subprocess.run(['bash', '-c', B.launch_guard(receipt)], capture_output=True).returncode, 97)
        self.assertEqual((self.run / 'bench_rebind/recovery/previous_outputs/bench_bad/failure.log').read_text(),
                         'original failure\n')

    def test_remote_existing_file_and_symlink_refuse(self):
        for kind in ('file', 'symlink'):
            p, src, base = self.fixture()
            dep = src / B.MISSING_DEP; dep.parent.mkdir(parents=True)
            if kind == 'file': dep.write_bytes(self.body)
            else: dep.symlink_to('missing-target')
            self.assertIn('already exists', self.remote(dict(p, action='inspect'), ok=False))
            self.assertFalse((self.run / 'bench_rebind').exists())
            import shutil
            shutil.rmtree(self.run)

    def test_changed_route_artifact_refuses(self):
        p, src, base = self.fixture(); p.update(self.remote(dict(p, action='inspect')))
        (base / '6_final.sdc').write_text('changed uncertainty\n')
        self.assertIn('SHA changed', self.remote(dict(p, action='prepare'), ok=False))
        self.assertFalse((self.run / 'bench_rebind').exists())


if __name__ == '__main__':
    unittest.main()
