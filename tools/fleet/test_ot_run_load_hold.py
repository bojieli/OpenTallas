"""Exercise actual CLI placement without creating remote jobs or waiters."""
import contextlib
import importlib.machinery
import importlib.util
import io
import os
from pathlib import Path
import unittest
from unittest.mock import Mock, patch


def load(path):
    loader = importlib.machinery.SourceFileLoader('ot_run_fixture', str(path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def row(free, load, cores):
    return dict(free_gb=free, load1=load, ncpu=cores, disk_gb=1000, avail_gb=free,
                growth_gb=0, headroom_gb=20, waiting=0, waiting_gb=0, running=1)


class Held(Exception):
    pass


def exercise(module, rows, extra=(), override=False, mem=80):
    run = Mock(return_value=(0, True))
    logs = io.StringIO()
    env = {'OT_RUN_NO_LOAD_HOLD': '1'} if override else {}
    with patch.object(module, 'HOSTS', list(rows)), patch.object(module, 'probe', side_effect=lambda h,d: (h,rows[h])), \
         patch.object(module, 'run', run), patch.object(module.sys, 'argv', ['ot-run','--mem',str(mem),'--threads','4',*extra,'--','true']), \
         patch.object(module.time, 'sleep', side_effect=Held), patch.dict(os.environ,env,clear=True), \
         contextlib.redirect_stderr(logs), contextlib.redirect_stdout(io.StringIO()):
        try:
            module.main()
        except Held:
            return dict(held=True, host=None, log=logs.getvalue())
        except SystemExit as ex:
            if ex.code:
                return dict(held=False, host=None, status=ex.code, log=logs.getvalue())
    return dict(held=False, host=run.call_args.args[0] if run.called else None, log=logs.getvalue())


class LoadHold(unittest.TestCase):
    def setUp(self):
        self.module = load(Path(__file__).with_name('ot-run'))

    def test_underloaded_memory_full_host_cannot_release_hold(self):
        r = exercise(self.module, dict(epyc=row(20,70,128),pve=row(104,43,28)))
        self.assertTrue(r['held'],r)
        self.assertIsNone(r['host'])

    def test_wait_releases_when_a_memory_fit_host_has_acceptable_cpu(self):
        r = exercise(self.module, dict(epyc=row(20,70,128),pve=row(104,41,28)))
        self.assertEqual(r['host'],'pve',r)

    def test_override_really_disables_filtering(self):
        r = exercise(self.module, dict(epyc=row(20,70,128),pve=row(104,43,28)),override=True)
        self.assertEqual(r['host'],'pve',r)

    def test_all_qualifying_hosts_over_cpu_line_still_hold(self):
        r = exercise(self.module, dict(epyc=row(100,200,128),pve=row(104,43,28)))
        self.assertTrue(r['held'],r)

    def test_no_memory_fit_still_uses_memory_queue_under_cpu_limit(self):
        r = exercise(self.module, dict(epyc=row(40,70,128),pve=row(20,10,28)))
        self.assertEqual(r['host'],'epyc',r)
        self.assertIn('will queue',r['log'])

    def test_pick_is_read_only_and_all_held_returns_75_without_sleep(self):
        r = exercise(self.module, dict(epyc=row(20,70,128),pve=row(104,43,28)),extra=('--pick',))
        self.assertFalse(r['held'],r)
        self.assertIsNone(r['host'])
        self.assertEqual(r['status'],75,r)
        self.assertNotIn('-> ',r['log'])
        self.assertIn('retry later',r['log'])


class PickEligibility(unittest.TestCase):
    def test_large_request_never_queues_on_physically_incapable_idle_host(self):
        module = load(Path(__file__).with_name('ot-run'))
        rows = dict(epyc={**row(-40, 90, 128), 'total_gb': 1008, 'floor_gb': 202},
                    agi={**row(28, 10, 64), 'total_gb': 126, 'floor_gb': 25})
        result = exercise(module, rows, mem=168)
        self.assertEqual(result['host'], 'epyc', result)
        self.assertIn('will queue', result['log'])

    def test_incapable_host_cannot_release_capable_host_cpu_hold(self):
        module = load(Path(__file__).with_name('ot-run'))
        rows = dict(epyc={**row(-40, 200, 128), 'total_gb': 1008, 'floor_gb': 202},
                    agi={**row(28, 10, 64), 'total_gb': 126, 'floor_gb': 25})
        result = exercise(module, rows, mem=168)
        self.assertTrue(result['held'], result)

    def test_no_physically_capable_host_never_creates_waiter(self):
        module = load(Path(__file__).with_name('ot-run'))
        result = exercise(module, dict(agi={**row(28, 10, 64), 'total_gb':126, 'floor_gb':25}), mem=168)
        self.assertIsNone(result['host'], result)
        self.assertIn('no host qualifies', result['status'])

    def test_mandatory_headroom_boundary_and_old_probe_compatibility(self):
        module = load(Path(__file__).with_name('ot-run'))
        self.assertTrue(module.physically_capable(dict(total_gb=126, headroom_gb=24, floor_gb=25),101))
        self.assertFalse(module.physically_capable(dict(total_gb=126, headroom_gb=24, floor_gb=25),102))
        self.assertFalse(module.physically_capable(dict(total_gb=126, headroom_gb=30, floor_gb=25),97))
        self.assertTrue(module.physically_capable({},168))

    def test_pick_and_run_prefer_same_cpu_eligible_host_despite_fresh_load(self):
        module = load(Path(__file__).with_name('ot-run'))
        rows = dict(epyc={**row(104,180,128), 'fresh':10},pve=row(104,43,28))
        picked = exercise(module,rows,extra=('--pick',))
        actual = exercise(module,rows)
        self.assertIn('-> epyc',picked['log'])
        self.assertEqual(actual['host'],'epyc')
        self.assertNotIn('-> pve',picked['log'])

    def test_pick_explicit_override_retains_bypass(self):
        module = load(Path(__file__).with_name('ot-run'))
        result = exercise(module,dict(pve=row(104,43,28)),extra=('--pick',),override=True)
        self.assertFalse(result['held'])
        self.assertNotIn('status',result)
        self.assertIn('-> pve',result['log'])

    def test_actual_admission_is_not_blocked_by_unstarted_large_waiters(self):
        module = load(Path(__file__).with_name('ot-run'))
        # Actual 13:37 probe: two large E1 waiters total900; E4 waiter270.
        # Both EPYCs can admit24, while plannedfree onlyfitsCPU-heldPVE.
        rows = dict(e1={**row(-561,93.07,128),'admit_gb':339},
                    e4={**row(-201,124.17,128),'admit_gb':69},
                    pve={**row(156,62.14,28),'admit_gb':156},
                    agi={**row(11,34.9,64),'admit_gb':11})
        for extra in [(),('--pick',)]:
            result=exercise(module,rows,extra=extra,mem=24)
            self.assertFalse(result['held'],result)
            self.assertNotIn('status',result)
            self.assertIn('-> e1',result['log'])
            self.assertNotIn('will queue',result['log'])

    def test_no_actual_fit_preserves_planned_memory_queue(self):
        module = load(Path(__file__).with_name('ot-run'))
        rows=dict(a={**row(-500,40,128),'admit_gb':60},
                  b={**row(10,50,128),'admit_gb':10})
        result=exercise(module,rows)
        self.assertEqual(result['host'],'b',result)
        self.assertIn('will queue',result['log'])

if __name__ == '__main__':
    unittest.main()
