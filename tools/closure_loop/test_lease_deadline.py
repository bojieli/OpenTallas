"""Lease deadlines and bulk transport (FLEET r1, 2026-10-10: EPYC3 lease pool exhausted by source syncs)."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

import ssh_transport as T
import closure_loop as C


class LeaseDeadlineTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        env = patch.dict(os.environ, CL_STATE=self.tmp.name)
        env.start()
        self.addCleanup(env.stop)
        self.root = T._directory()
        self.addCleanup(lambda: shutil.rmtree(self.root, ignore_errors=True))
        T._SEMAPHORES.clear()
        T._BULK_SEMAPHORES.clear()
        self.master = patch.object(T, '_ensure_master', return_value=['ssh', 'mux', 'h'])
        self.ensure = self.master.start()
        self.addCleanup(self.master.stop)

    def _hold(self, n, bulk=False):
        """Hold n leases on host 'h' from other threads until release.set()."""
        release, held = threading.Event(), threading.Barrier(n + 1)
        def holder():
            with T.command('h', bulk=bulk):
                held.wait()
                release.wait(10)
        ts = [threading.Thread(target=holder) for _ in range(n)]
        for t in ts:
            t.start()
        held.wait(5)
        self.addCleanup(lambda: (release.set(), [t.join() for t in ts]))
        return release

    def test_exhausted_pool_times_out_without_starting_a_command(self):
        self._hold(T.CHANNELS)
        self.ensure.reset_mock()
        t0 = time.monotonic()
        with self.assertRaises(subprocess.TimeoutExpired):
            with T.command('h', wait_s=0.2):
                self.fail('body must not run without a lease')
        self.assertLess(time.monotonic() - t0, 2)
        self.ensure.assert_not_called()

    def test_bulk_uses_direct_connection_and_spares_mux_leases(self):
        self._hold(T.CHANNELS)                      # every mux channel busy
        with T.command('h', bulk=True, wait_s=0.2) as base:
            self.assertIn('ControlPath=none', base)
            self.assertEqual(base[-1], 'h')

    def test_bulk_pool_is_bounded(self):
        self._hold(T.BULK_CHANNELS, bulk=True)
        with self.assertRaises(subprocess.TimeoutExpired):
            with T.command('h', bulk=True, wait_s=0.1):
                pass
        with T.command('h', wait_s=0.2):            # control channels stay free
            pass

    def test_ssh_counts_lease_wait_against_its_timeout(self):
        self._hold(T.CHANNELS)
        t0 = time.monotonic()
        with patch.object(C, 'sh', side_effect=AssertionError('no command without a lease')):
            with self.assertRaises(subprocess.TimeoutExpired):
                C.ssh('h', 'true', timeout=0.3)
        self.assertLess(time.monotonic() - t0, 2)

    def test_write_status_never_opens_ssh_with_a_fleet(self):
        fleet = C.Fleet()
        for h in C.hosts_table():
            fleet.last_good[h['name']] = (time.time(), dict(load1=1.0, mem_gb=100))
        out = Path(self.tmp.name) / 'STATUS.md'
        with patch.object(C, 'ssh', side_effect=AssertionError('ssh from the main thread')), \
             patch.object(C, 'STATUS_MD', out), patch.object(C, 'all_jobs', return_value=[]):
            C.write_status(fleet=fleet)
        self.assertIn('100 GB free', out.read_text())


if __name__ == '__main__':
    unittest.main()
