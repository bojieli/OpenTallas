"""A main-route resource retry must not move a log-consuming bench off its producer."""
import copy
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

import closure_loop as C
from test_bench_track import Fleet, job


class BenchArtifactLocation(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.run_a = str(self.root / 'host_a/job')
        self.run_b = str(self.root / 'host_b/job')
        Path(self.run_a).mkdir(parents=True)
        Path(self.run_a, 'vm8_bench.log').write_text('VM_SPLIT8_BENCH PASS\nVM_SPLIT8_NEG_XBUS_DETECTED\n')
        self.j = job(name='job', host='host_a', run=self.run_a, status='RUNNING', bench_par=True,
                     stage_tag='route.a1', stage_key='route', benches={'bench_exact': {'ok': True}},
                     btrack={'bench_exact': {'state': 'done', 'tag': 'bench_exact.a1b1', 'host': 'host_a',
                              'run': self.run_a, 'n': 1}})
        self.j['spec'] = copy.deepcopy(self.j['spec'])
        self.j['spec']['stages']['bench'][1]['cmd'] = 'grep -q VM_SPLIT8_NEG_XBUS_DETECTED {RUN}/vm8_bench.log && echo VM8_XBUS_MUTANT_FAILS && exit 1; exit 0'
        self.stages = C.stage_list(self.j['spec'])

    def test_resource_migration_keeps_negative_on_original_artifacts(self):
        fleet = Fleet(); fleet.choose = Mock(return_value=('host_b', 'ok'))
        fleet.probe = Mock(); fleet._launched = Mock()
        with patch.object(C, 'stage_tail', return_value='Killed'), patch.object(C, 'host_cfg', side_effect=lambda h: {'base': str(self.root/h), 'label': h}), patch.object(C, 'log'):
            C.crash(self.j, {'kind':'route', 'key':'route'}, fleet, 'resource failure')
        self.assertEqual(self.j['host'], 'host_b')
        self.assertEqual(self.j['attempt'], 2)
        self.assertEqual(self.j['status'], 'SYNC')
        self.j['status'] = 'READY'  # destination source synchronization has completed
        launched = []
        def launch(view, stage, cmd):
            result = subprocess.run(['bash','-c', C.subst(cmd, view)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertIn('VM8_XBUS_MUTANT_FAILS', result.stdout)
            self.assertEqual(view['attempt'], '1b1')
            view['stage_tag'] = C.tag(stage, view)
            launched.append(view)
        with patch.object(C, 'launch_stage', side_effect=launch), patch.object(C, 'log'), patch.object(C, 'stop_main_for_bench') as stop:
            C.bench_track(self.j, fleet, self.stages)
        self.assertEqual(launched[0]['host'], 'host_a')
        self.assertEqual(launched[0]['run'], self.run_a)
        self.assertEqual(self.j['btrack']['bench_neg']['host'], 'host_a')
        fleet.probe.assert_called_once_with('host_a')
        self.assertEqual(fleet._launched.call_args.args[0], 'host_a')
        self.assertEqual(self.j['host'], 'host_b')
        stop.assert_not_called()

    def test_original_host_capacity_wait_does_not_relocate_or_stop_route(self):
        self.j.update(host='host_b', run=self.run_b, attempt=2)
        fleet = Fleet(); fleet.fits = Mock(return_value=(False,'producer host unavailable'))
        with patch.object(C, 'launch_stage') as launch, patch.object(C, 'stop_main_for_bench') as stop, patch.object(C, 'log'):
            C.bench_track(self.j, fleet, self.stages)
        self.assertEqual(fleet.fits.call_args.args[0], 'host_a')
        self.assertEqual(self.j['status'], 'RUNNING')
        launch.assert_not_called(); stop.assert_not_called()

    def test_retry_and_legacy_completed_receipts_are_not_rewritten(self):
        self.j.update(host='host_b', run=self.run_b, attempt=2)
        original = copy.deepcopy(self.j['btrack']['bench_exact'])
        self.j['btrack']['bench_neg'] = dict(state='retry',host='host_b',run=self.run_b,n=1,tag='bench_neg.a2b1')
        with patch.object(C, 'launch_stage', side_effect=lambda v,s,c:v.update(stage_tag=C.tag(s,v))) as launch, patch.object(C,'log'):
            C.bench_track(self.j,Fleet(),self.stages)
        self.assertEqual(launch.call_args.args[0]['host'],'host_a')
        self.assertEqual(launch.call_args.args[0]['attempt'],'1b2')
        self.assertEqual(self.j['btrack']['bench_exact'],original)
        self.assertEqual(self.j['benches']['bench_exact'],{'ok':True})


class VanishedBenchLocation(unittest.TestCase):
    """drive-1013: a purged artifact run must not pin the bench chain (qfd_embed_scale_bank_retained-24bd6a53b-tt)."""
    def _job(self):
        j = job(name='job', host='host_b', run='/b/job', status='RUNNING', bench_par=True, stage_tag='route.a5',
                stage_key='route', benches={'bench_exact': {'ok': True}},
                btrack={'bench_exact': {'state': 'done', 'tag': 'bench_exact.a1b1', 'host': 'host_a', 'run': '/a/job-bench', 'n': 1}},
                bench_location={'host': 'host_a', 'run': '/a/job-bench', 'attempt': 1})
        j['spec'] = copy.deepcopy(j['spec'])
        return j

    def _run(self, j, out, rc=0):
        launched = []
        fleet = Fleet(); fleet.probe = Mock(); fleet._launched = Mock()
        def launch(view, stage, cmd):
            view['stage_tag'] = C.tag(stage, view); launched.append(view)
        r = subprocess.CompletedProcess([], rc, stdout=out, stderr='')
        with patch.object(C, 'ssh', return_value=r), patch.object(C, 'launch_stage', side_effect=launch), \
                patch.object(C, 'hosts_table', return_value=[]), patch.object(C, 'log'):
            C.bench_track(j, fleet, C.stage_list(j['spec']))
        return launched

    def test_missing_run_restarts_chain_on_own_run(self):
        j = self._job()
        launched = self._run(j, 'MISSING\n')
        self.assertNotIn('bench_exact', j['benches'])
        self.assertEqual(launched[0]['run'], '/b/job')
        self.assertEqual(launched[0]['host'], 'host_b')

    def test_ssh_failure_keeps_location(self):
        j = self._job()
        launched = self._run(j, '', rc=255)
        self.assertIn('bench_exact', j['benches'])
        self.assertEqual(launched[0]['run'], '/a/job-bench')

    def test_present_run_keeps_location(self):
        j = self._job()
        launched = self._run(j, 'PRESENT\n')
        self.assertEqual(launched[0]['host'], 'host_a')

if __name__ == '__main__':
    unittest.main()
