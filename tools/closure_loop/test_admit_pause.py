"""ADMIT-PAUSE (drive-resume 2026-10-09): a host whose admit.pause_new.json exists is not admissible for the loop."""
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import closure_loop as cl


class AdmitPause(unittest.TestCase):
    def probe(self, extra):
        cfg = dict(name='remote', label='remote', base='/scratch', max_job_threads=128, max_job_ram_gb=1000,
                   min_free_disk_gb=10, ram_gb=1000)
        fleet = cl.Fleet()
        out = '1 1 1 1/1 1\n800\n1000\n' + extra
        with patch.object(cl, 'host_cfg', return_value=cfg), patch.object(cl, 'disk_roots', return_value={}), \
                patch.object(cl, 'ssh', return_value=SimpleNamespace(returncode=0, stdout=out)) as s:
            info = fleet._probe_once('remote')
            self.assertIn(cl.ADMIT_PAUSE, s.call_args[0][1])
            with patch.object(fleet, 'probe', return_value=info):
                return info, fleet.fits('remote', 16, 40)

    def test_paused_host_refuses(self):
        info, (ok, why) = self.probe('OT_ADMIT_PAUSED {"reason": "owner memory pressure"}\n')
        self.assertFalse(ok)
        self.assertIn("admission paused", why)
        self.assertIn("owner memory pressure", info["admit_paused"])

    def test_unpaused_host_admits(self):
        info, (ok, _) = self.probe('')
        self.assertNotIn("admit_paused", info)
        self.assertTrue(ok)


if __name__ == "__main__":
    unittest.main()
