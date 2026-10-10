"""LIGHT-STAGE DISK FLOOR (drive-0849 2026-10-09): bench / collect / export stages (ram <= LIGHT_STAGE_RAM_GB) are admitted
above LIGHT_DISK_FLOOR_GB of free run-root / disk-root space; routes / calibrates / ECOs keep the host's full floor."""
import unittest
from unittest.mock import patch

import closure_loop as cl


class LightDiskFloor(unittest.TestCase):
    def fits(self, ram, disk=190, roots=None):
        cfg = dict(name='h', label='H', base='/s', max_job_threads=128, max_job_ram_gb=1000, min_free_disk_gb=200,
                   ram_gb=1000)
        fleet = cl.Fleet()
        info = dict(load1=1.0, mem_gb=800, disk_gb=disk, roots_gb=roots or {})
        with patch.object(cl, 'host_cfg', return_value=cfg), \
                patch.object(cl, 'disk_roots', return_value={'/x': 200} if roots else {}), \
                patch.object(fleet, 'probe', return_value=info):
            return fleet.fits('h', 4, ram)

    def test_route_keeps_full_floor(self):
        ok, why = self.fits(40)
        self.assertFalse(ok)
        self.assertIn("< 200", why)

    def test_light_stage_admitted(self):
        self.assertTrue(self.fits(2)[0])
        self.assertTrue(self.fits(cl.LIGHT_STAGE_RAM_GB)[0])

    def test_light_stage_still_has_a_floor(self):
        ok, why = self.fits(2, disk=cl.LIGHT_DISK_FLOOR_GB - 1)
        self.assertFalse(ok)

    def test_disk_roots_light(self):
        self.assertTrue(self.fits(2, disk=500, roots={'/x': 100})[0])
        self.assertFalse(self.fits(40, disk=500, roots={'/x': 100})[0])


if __name__ == "__main__":
    unittest.main()
