#!/usr/bin/env python3
"""WAVE-TICK-PAR 11-14: dead-host skip in wave_jobs, rpy per-tick cache + prefetch pool in autopilot, parallel reap actions"""
import os, sys, threading, time, unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import autopilot as AP  # noqa: E402
import kit_wave as KW  # noqa: E402
import wave_jobs as WJ  # noqa: E402


class DeadHost(unittest.TestCase):
    def setUp(self):
        WJ._DEAD.clear()

    def tearDown(self):
        WJ._DEAD.clear()

    def test_connect_failure_skips_host_afterwards(self):
        calls = []

        def sh(cmd, timeout=0, input=None):
            h = cmd[cmd.index('ControlPath=none') + 1] if 'ssh' in cmd else 'hub'
            calls.append(h)
            if h == 'epyc4':
                return 255, '', 'ssh: connect to host epyc4 port 22: Connection timed out'
            return 0, '{"containers": [], "scopes": []}', ''
        r1 = WJ.stop_on_fleet(sh, 'intel2', ['/x'], hosts=['intel2', 'epyc4', 'epyc2'])
        self.assertIn('error', r1['epyc4'])
        n = calls.count('epyc4')
        r2 = WJ.stop_on_fleet(sh, 'intel2', ['/x'], hosts=['intel2', 'epyc4', 'epyc2'])
        self.assertEqual(calls.count('epyc4'), n)           # not probed again
        self.assertIn('skipped', r2['epyc4']['error'])
        self.assertEqual(r2['epyc2'], {'containers': [], 'scopes': []})

    def test_non_transport_error_does_not_mark_dead(self):
        self.assertFalse(WJ.note_conn_failure('h', 1, 'python error'))
        self.assertFalse(WJ.host_dead('h'))

    def test_ttl_expires(self):
        WJ.note_conn_failure('h', 255, 'Connection refused', now=100.0)
        self.assertTrue(WJ.host_dead('h', now=101.0))
        self.assertFalse(WJ.host_dead('h', now=100.0 + WJ.DEAD_TTL_S + 1))


class RpyCache(unittest.TestCase):
    def test_cache_dedups_within_phase_only(self):
        n = []
        real = AP.sh
        AP.sh = lambda cmd, timeout=0, input=None: (n.append(1), (0, 'AP_JSON {"a": 1}\n', ''))[1]
        try:
            AP.rpy('epyc7', 'code', {'k': 1})
            AP.rpy('epyc7', 'code', {'k': 1})
            self.assertEqual(len(n), 2)                    # no cache outside a phase
            AP._RPY_CACHE = {}
            r = AP.rpy('epyc7', 'code', {'k': 1})
            r['a'] = 99                                    # callers may mutate their copy
            self.assertEqual(AP.rpy('epyc7', 'code', {'k': 1}), {'a': 1})
            AP.rpy('epyc7', 'code', {'k': 2})
            AP.rpy('epyc8', 'code', {'k': 1})
            self.assertEqual(len(n), 2 + 3)
        finally:
            AP._RPY_CACHE = None
            AP.sh = real


class Prefetch(unittest.TestCase):
    def test_pool_is_parallel_and_bounded_and_warms_cache(self):
        jobs = {str(i): dict(id=str(i), status='RUNNING', goal='route', unit='u%d' % i, host='epyc7', path='/k/%d' % i, started=1)
                for i in range(16)}
        jobs['x'] = dict(id='x', status='DONE', goal='route', unit='ux', host='epyc7', path='/k/x')
        live = dict(unit_active=AP.unit_active, probe_job=AP.probe_job)
        lock, cur, peak = threading.Lock(), [0], [0]

        def slow_probe(j):
            with lock:
                cur[0] += 1
                peak[0] = max(peak[0], cur[0])
            time.sleep(0.05)
            with lock:
                cur[0] -= 1
            return {}
        AP.unit_active = lambda u: False
        AP.probe_job = slow_probe
        try:
            t = time.time()
            n = AP.prefetch_probes({'jobs': jobs}, pool=8)
            dt = time.time() - t
        finally:
            AP.unit_active, AP.probe_job = live['unit_active'], live['probe_job']
        self.assertEqual(n, 16)
        self.assertGreater(peak[0], 1)
        self.assertLessEqual(peak[0], 8)
        self.assertLess(dt, 16 * 0.05)

    def test_active_unit_needs_no_probe(self):
        jobs = {'1': dict(id='1', status='RUNNING', goal='route', unit='u', host='h', path='/k')}
        real = AP.unit_active
        AP.unit_active = lambda u: True
        try:
            self.assertEqual(AP.prefetch_probes({'jobs': jobs}), 0)
        finally:
            AP.unit_active = real


class ReapParallel(unittest.TestCase):
    def test_run_parallel_order_and_errors(self):
        def f(x):
            if x == 3:
                raise ValueError('boom')
            time.sleep(0.02)
            return x * 2
        r = KW.run_parallel(f, range(6), 4)
        self.assertEqual([x for i, x in enumerate(r) if i != 3], [0, 2, 4, 8, 10])
        self.assertIsInstance(r[3], ValueError)
        self.assertEqual(KW.run_parallel(f, [], 4), [])


if __name__ == '__main__':
    unittest.main()
