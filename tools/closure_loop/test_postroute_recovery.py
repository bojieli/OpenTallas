import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

import closure_loop as C
from postroute_recovery import probe, remote_command
from test_bench_track import Fleet, job


class CompletedRouteRecovery(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.base = self.root / 'work/orfs/results/asap7/block/base'
        self.base.mkdir(parents=True)
        self.odb = self.base / '6_final.odb'
        self.odb.write_bytes(b'completed route fixture')
        self.config = dict(route_root=str(self.root), odb_patterns=[str(self.base / '*.odb')])
        (self.root / 'exit').write_text('rc=0\ncorner_rc=1\n')
        (self.root / 'corner.log').write_text("Traceback (most recent call last):\nNameError: name 'sdc' is not defined\n")

    def test_completed_su_and_front_helpers_keep_artifact_evidence(self):
        for marker, text, error in [('exit', 'rc=0\ncorner_rc=1\n', 'NameError: sdc'),
                                    ('status', 'flow_rc=0\nabstract_rc=0\ncorner_rc=2\n',
                                     'corner_sta.py: error: unrecognized arguments: --sdc-name')]:
            with self.subTest(marker=marker):
                (self.root / 'exit').unlink(missing_ok=True)
                (self.root / marker).write_text(text)
                (self.root / 'corner.log').write_text(error)
                out = subprocess.run(remote_command(self.config), shell=True, capture_output=True, text=True)
                self.assertEqual(out.returncode, 0, out.stderr)
                self.assertEqual(json.loads(out.stdout)['artifacts'][0]['path'], str(self.odb))

    def test_real_route_failure_or_missing_artifact_keeps_normal_recovery(self):
        (self.root / 'exit').write_text('rc=2\ncorner_rc=1\n')
        self.assertIsNone(probe(self.config))
        (self.root / 'exit').write_text('rc=0\ncorner_rc=1\n')
        self.odb.unlink()
        self.assertIsNone(probe(self.config))

    def test_timing_failure_is_not_helper_failure(self):
        (self.root / 'corner.log').write_text('SS -30 ps FF -2 ps: not closed')
        self.assertIsNone(probe(self.config))

    def route_job(self):
        j = job(host='ot-epyc1tb', run='/saved/job', bench_par=False, source_synced=True)
        j['spec'] = dict(j['spec'], verdict={'corner_sta': '{RUN}/routes/{LABEL}/corner_sta.json',
                                           'drc_metrics': '{RUN}/routes/{LABEL}/work/orfs/logs/asap7/*/base/5_2_route.json'})
        j.update(stage_tag='route.a1', status='RUNNING', retries_used=0, attempt=1)
        return j

    def test_crash_preserves_stage_host_retry_budget_and_blocks_auto_requeue(self):
        j = self.route_job(); fleet = Fleet(); fleet.choose = Mock()
        before = {k: j.get(k) for k in ('host', 'run', 'stage_idx', 'attempt', 'retries_used')}
        receipt = subprocess.CompletedProcess([], 0, json.dumps(probe(self.config)), '')
        with patch.object(C, 'ssh', return_value=receipt), patch.object(C, 'ledger'), patch.object(C, 'experiment'), patch.object(C, 'log'):
            C.crash(j, {'kind': 'route', 'key': 'route'}, fleet, 'rc=0 ok-check failed')
        self.assertEqual(j['status'], 'NEEDS_HUMAN')
        self.assertEqual(before, {k: j.get(k) for k in before})
        self.assertIn('postroute_repair', j); fleet.choose.assert_not_called()
        j['crashes'] = [{'stage': 'route', 'tail': 'anything'}]
        with patch.object(C, 'job_lock', side_effect=AssertionError('must not requeue preserved route')):
            C.auto_requeue([j])

    def test_actual_route_failure_still_uses_existing_retry(self):
        j = self.route_job(); fleet = Fleet(); fleet.choose = Mock()
        with patch.object(C, 'ssh', return_value=subprocess.CompletedProcess([], 0, 'null', '')), \
             patch.object(C, 'stage_tail', return_value='[ERROR DRT-0305] detailed route aborted'), patch.object(C, 'log'):
            C.crash(j, {'kind': 'route', 'key': 'route'}, fleet, 'rc=2')
        self.assertEqual(j['status'], 'READY')
        self.assertEqual(j['attempt'], 2); self.assertEqual(j['retries_used'], 1)
        self.assertNotIn('postroute_repair', j)

    def test_grt_congestion_is_terminal_not_retried(self):
        # 8740289f6: GRT-0116 is deterministic -> EARLY_FAIL_CONGESTION, no retry, no post-route repair
        j = self.route_job(); fleet = Fleet(); fleet.choose = Mock()
        with patch.object(C, 'ssh', return_value=subprocess.CompletedProcess([], 0, 'null', '')), \
             patch.object(C, 'stage_tail', return_value='[ERROR GRT-0116] routing congestion'), patch.object(C, 'log'):
            C.crash(j, {'kind': 'route', 'key': 'route'}, fleet, 'rc=2')
        self.assertEqual((j['status'], j['retries_used']), ('EARLY_FAIL_CONGESTION', 0))
        self.assertNotIn('postroute_repair', j)

    def test_transport_failure_waits_without_reroute(self):
        j = self.route_job(); fleet = Fleet(); fleet.choose = Mock()
        with patch.object(C, 'ssh', return_value=subprocess.CompletedProcess([], 255, '', 'reset')):
            C.crash(j, {'kind': 'route', 'key': 'route'}, fleet, 'rc=1')
        self.assertEqual(j['status'], 'RUNNING'); self.assertEqual(j['attempt'], 1)
        self.assertIn('evidence unavailable', j['wait']); fleet.choose.assert_not_called()


if __name__ == '__main__':
    unittest.main()
