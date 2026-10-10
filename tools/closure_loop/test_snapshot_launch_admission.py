"""Charge actual launches only until a fresh measurement observes the completed launch."""
import threading
import unittest
from unittest.mock import patch
import closure_loop as cl

class SnapshotLaunchAdmission(unittest.TestCase):
    def setUp(self):
        self.fleet = cl.Fleet()
        self.info = dict(mem_gb=70, load1=1, disk_gb=1000, admission_measured_at=100)
        cfg = dict(label='remote', max_job_threads=128, max_job_ram_gb=1000,
                   min_free_ram_gb=16, min_free_disk_gb=0)
        for p in [patch.object(cl, 'host_cfg', return_value=cfg),
                  patch.object(cl, 'disk_roots', return_value={}),
                  patch.object(self.fleet, 'probe', side_effect=lambda host: self.info)]:
            p.start(); self.addCleanup(p.stop)

    def test_simultaneous_reservations_cannot_spend_one_snapshot_twice(self):
        barrier = threading.Barrier(2); outcomes = []
        def admit(name):
            barrier.wait()
            with cl.FLEET_LOCK:
                ok, why = self.fleet._fits('remote', 16, 40, name)
                if ok:self.fleet._launched('remote', 16, 40, name, actual=True)
                outcomes.append(ok)
        ts = [threading.Thread(target=admit, args=(str(i),)) for i in range(2)]
        for t in ts:t.start()
        for t in ts:t.join()
        self.assertEqual(sorted(outcomes), [False, True])

    def test_waiting_claims_never_reserve_ram(self):
        self.fleet.launched('remote', 128, 1000, 'waiting')
        self.assertTrue(self.fleet._fits('remote', 16, 40)[0])

    def test_refresh_during_launch_keeps_inflight_charge(self):
        token = self.fleet._launched('remote', 16, 40, 'actual', actual=True)
        self.info['admission_measured_at'] = token + 1
        self.assertFalse(self.fleet._fits('remote', 16, 40)[0])
        self.fleet.launch_complete('remote', token)
        self.info['admission_measured_at'] = token + 100
        self.assertTrue(self.fleet._fits('remote', 16, 40)[0])
        self.assertEqual(self.fleet.inflight_launches['remote'], [])

    def test_completed_launch_still_charged_to_old_measurement(self):
        self.fleet.launched('remote', 16, 40, 'actual', actual=True)
        self.assertFalse(self.fleet._fits('remote', 16, 40)[0])

    def test_launch_invalidates_cache_before_and_after(self):
        self.fleet.probe_cache['remote'] = (100, self.info)
        token = self.fleet._launched('remote', 16, 40, actual=True)
        self.assertNotIn('remote', self.fleet.probe_cache)
        self.fleet.probe_cache['remote'] = (101, self.info)
        self.fleet.launch_complete('remote', token)
        self.assertNotIn('remote', self.fleet.probe_cache)

if __name__ == '__main__':unittest.main()
