"""Exercise actual CLI placement without creating remote jobs or waiters (v6 2026-10-18: no load hold, rebalance)."""
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


class NoLoadHold(unittest.TestCase):
    """ot-run v6 (owner 2026-10-18): CPU load never holds a job; memory is the only admission limit."""
    def setUp(self):
        self.module = load(Path(__file__).with_name('ot-run'))

    def test_overloaded_memory_fit_host_runs_at_once(self):
        r = exercise(self.module, dict(epyc=row(20,70,128),pve=row(104,43,28)))
        self.assertEqual(r['host'],'pve',r)
        self.assertNotIn('load hold',r['log'])

    def test_every_host_over_any_cpu_line_still_runs(self):
        r = exercise(self.module, dict(epyc=row(100,200,128),pve=row(104,43,28)))
        self.assertFalse(r['held'],r)
        self.assertEqual(r['host'],'epyc',r)          # load only orders the fits: 204/128 < 47/28

    def test_override_env_is_harmless(self):
        r = exercise(self.module, dict(epyc=row(20,70,128),pve=row(104,43,28)),override=True)
        self.assertEqual(r['host'],'pve',r)

    def test_no_memory_fit_uses_memory_queue(self):
        r = exercise(self.module, dict(epyc=row(40,70,128),pve=row(20,10,28)))
        self.assertEqual(r['host'],'epyc',r)
        self.assertIn('will queue',r['log'])

    def test_pick_names_the_overloaded_memory_fit_host(self):
        r = exercise(self.module, dict(epyc=row(20,70,128),pve=row(104,43,28)),extra=('--pick',))
        self.assertFalse(r['held'],r)
        self.assertNotIn('status',r)
        self.assertIn('-> pve',r['log'])

    def test_cpu_load1_key_orders(self):
        rows = dict(a={**row(500,0,128),'cpu_load1':120.0}, b={**row(500,0,128),'cpu_load1':10.0})
        self.assertEqual(exercise(self.module, rows)['host'],'b')


class Rebalance(unittest.TestCase):
    """v6 REBALANCE: an unstarted waiter is re-placed after REQUEUE_S on whichever qualifying host admits it."""
    def test_requeue_moves_to_host_that_freed_memory(self):
        module = load(Path(__file__).with_name('ot-run'))
        seq = [dict(a=row(40,10,128),b=row(10,10,128)), dict(a=row(40,10,128),b=row(200,10,128))]
        calls = []
        def probe(h, d):
            return h, seq[min(len(calls), 1)][h]
        def run(host, mem, cmd, d=None, max_wait=None, env="", quiet=False, quiet_notrun=False):
            calls.append((host, max_wait))
            return (75, False) if len(calls) == 1 else (0, True)
        with patch.object(module, 'HOSTS', ['a','b']), patch.object(module, 'probe', side_effect=probe), \
             patch.object(module, 'run', side_effect=run), patch.object(module.sys, 'argv', ['ot-run','--mem','80','--','true']), \
             patch.dict(os.environ, {}, clear=True), contextlib.redirect_stderr(io.StringIO()) as err:
            with self.assertRaises(SystemExit) as ex:
                module.main()
        self.assertEqual(ex.exception.code, 0)
        self.assertEqual(calls, [('a', module.REQUEUE_S), ('b', module.REQUEUE_S)])
        self.assertIn('REBALANCE', err.getvalue())

    def test_single_host_waits_unbounded_and_max_wait_is_kept(self):
        module = load(Path(__file__).with_name('ot-run'))
        calls = []
        def run(host, mem, cmd, d=None, max_wait=None, env="", quiet=False, quiet_notrun=False):
            calls.append(max_wait); return (75, False)
        for extra, want in [((), [None]), (('--max-wait','900'), [900])]:
            calls.clear()
            with patch.object(module, 'HOSTS', ['a']), patch.object(module, 'probe', return_value=('a', row(10,0,128))), \
                 patch.object(module, 'run', side_effect=run), patch.object(module.sys, 'argv', ['ot-run','--mem','80',*extra,'--','true']), \
                 patch.dict(os.environ, {}, clear=True), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as ex:
                    module.main()
            self.assertEqual(ex.exception.code, 75)
            self.assertEqual(calls, want)

    def test_die_like_commands_get_die_priority(self):
        module = load(Path(__file__).with_name('ot-run'))
        self.assertTrue(module.die_like(['bash','run_die_sta.sh'], None))
        self.assertTrue(module.die_like(['bash','x'], '/srv/x/die_gen1'))
        self.assertFalse(module.die_like(['bash','tools/s81_slice/leaf_bench.sh'], '/srv/s81die5/pvrd'))


class PickEligibility(unittest.TestCase):
    def test_status_respects_quarantine_and_explicit_override(self):
        module = load(Path(__file__).with_name('ot-run'))
        rows = dict(epyc=row(500, 40, 128), agi=row(100, 0, 64))
        for override, expected in [(False, 'epyc'), (True, 'agi')]:
            output = io.StringIO()
            env = {'OT_RUN_INCLUDE_HELD': '1'} if override else {}
            with patch.object(module, 'held_hosts', return_value={'agi': 'unstable host'}), \
                 patch.object(module, 'probe', side_effect=lambda h,d: (h,rows[h])), \
                 patch.dict(os.environ, env, clear=True), contextlib.redirect_stdout(output):
                module.status(list(rows))
            self.assertIn('job -> ' + expected, output.getvalue())
            self.assertEqual('agi HELD (unstable host)' in output.getvalue(), not override)

    def test_status_with_every_host_quarantined_has_no_next_host(self):
        module = load(Path(__file__).with_name('ot-run'))
        output = io.StringIO()
        with patch.object(module, 'held_hosts', return_value={'agi': 'unstable host'}), \
             patch.object(module, 'probe', return_value=('agi', row(100, 0, 64))), \
             patch.dict(os.environ, {}, clear=True), contextlib.redirect_stdout(output):
            module.status(['agi'])
        self.assertIn('no eligible host', output.getvalue())
        self.assertNotIn('job ->', output.getvalue())

    def test_status_advertises_overloaded_memory_fit_host(self):
        module = load(Path(__file__).with_name('ot-run'))
        rows = dict(epyc=row(20, 70, 128), pve=row(104, 43, 28))
        output = io.StringIO()
        with patch.object(module, 'probe', side_effect=lambda h,d: (h,rows[h])), \
             patch.dict(os.environ, {}, clear=True), contextlib.redirect_stdout(output):
            module.status(list(rows))
        self.assertIn('-> pve', output.getvalue())
        self.assertNotIn('load held', output.getvalue())

    def test_large_request_never_queues_on_physically_incapable_idle_host(self):
        module = load(Path(__file__).with_name('ot-run'))
        rows = dict(epyc={**row(-40, 90, 128), 'total_gb': 1008, 'floor_gb': 202},
                    agi={**row(28, 10, 64), 'total_gb': 126, 'floor_gb': 25})
        result = exercise(module, rows, mem=168)
        self.assertEqual(result['host'], 'epyc', result)
        self.assertIn('will queue', result['log'])

    def test_incapable_host_never_takes_the_queue_even_when_capable_host_is_loaded(self):
        module = load(Path(__file__).with_name('ot-run'))
        rows = dict(epyc={**row(-40, 200, 128), 'total_gb': 1008, 'floor_gb': 202},
                    agi={**row(28, 10, 64), 'total_gb': 126, 'floor_gb': 25})
        result = exercise(module, rows, mem=168)
        self.assertEqual(result['host'], 'epyc', result)
        self.assertIn('will queue', result['log'])

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

    def test_pick_and_run_agree_and_count_fresh_launches(self):
        module = load(Path(__file__).with_name('ot-run'))
        rows = dict(epyc={**row(104,180,128), 'fresh':10},pve=row(104,43,28))
        picked = exercise(module,rows,extra=('--pick',))
        actual = exercise(module,rows)
        self.assertIn('-> pve',picked['log'])        # fresh launches count in the ORDER (no hold): 344/128 > 47/28
        self.assertEqual(actual['host'],'pve')

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
