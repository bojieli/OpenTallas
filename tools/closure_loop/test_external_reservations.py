"""Long-lived externally admitted jobs retain their not-yet-resident peak."""
import os
import shlex
import subprocess
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import closure_loop as cl


class ExternalReservationTests(unittest.TestCase):
    def test_admission_is_measured_memory_plus_fixed_safety(self):
        # drive-resume 2026-10-09 (owner: never reserve for future growth): external remaining peaks, recent claims and
        # a %-of-RAM headroom are NOT subtracted; admit iff MemAvailable >= request + ADMIT_SAFETY_GB (16)
        cfg = dict(name='remote', label='remote', max_job_threads=128,
                   max_job_ram_gb=1000, min_free_disk_gb=10, ram_gb=1000)
        fleet = cl.Fleet()
        info = dict(load1=10000, mem_gb=400, disk_gb=1000,
                    roots_gb={}, external_remaining_gb=300)
        fleet.pending['remote'] = [(__import__('time').time(), 16, 224, 'other-job')]
        with patch.object(cl, 'host_cfg', return_value=cfg), patch.object(fleet, 'probe', return_value=info):
            self.assertTrue(fleet.fits('remote', 16, 384)[0])
            ok, why = fleet.fits('remote', 16, 385)
            self.assertFalse(ok)
            self.assertIn("MemAvailable 400 GB < 385+16", why)

    def test_live_command_identity_has_measured_remaining_peak(self):
        cfg = dict(name='remote', base='/scratch', external_jobs=[dict(name='large', pid=os.getpid(),
                   command_match='unittest', peak_ram_gb=250)])
        fleet = cl.Fleet()
        def remote(host, command, **kwargs):
            code = shlex.split(command.split('; python3 -c ', 1)[1])[0]
            result = subprocess.run([sys.executable, '-c', code], check=True, capture_output=True, text=True)
            return SimpleNamespace(returncode=0, stdout='1 1 1 1/1 1\n400\n1000\n'+result.stdout)
        with patch.object(cl, 'host_cfg', return_value=cfg), patch.object(cl, 'disk_roots', return_value={}), \
                patch.object(cl, 'ssh', side_effect=remote):
            info = fleet._probe_once('remote')
            self.assertEqual(info['external_jobs'][0]['pid'], os.getpid())
            self.assertGreater(info['external_remaining_gb'], 249)
            cfg['external_jobs'][0]['command_match'] = 'not-this-process'
            self.assertEqual(fleet._probe_once('remote')['external_remaining_gb'], 0)

    def test_missing_external_probe_fails_admission_closed(self):
        cfg = dict(name='remote', base='/scratch', external_jobs=[dict(name='large', pid=1,
                   command_match='expected-command', peak_ram_gb=250)])
        fleet = cl.Fleet()
        with patch.object(cl, 'host_cfg', return_value=cfg), patch.object(cl, 'disk_roots', return_value={}), \
                patch.object(cl, 'ssh', return_value=SimpleNamespace(returncode=0, stdout='1 1 1 1/1 1\n400\n1000\n')):
            self.assertIsNone(fleet._probe_once('remote'))


if __name__ == '__main__':
    unittest.main()
