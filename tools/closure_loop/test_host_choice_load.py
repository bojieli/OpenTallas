"""OWNER 2026-10-13 17:55: a job goes to the host with the lowest projected load1 / cores among those that can admit it;
a small host never gets a job of more than 8 threads while a 128-core host still has cores."""
import unittest
from unittest.mock import patch
import closure_loop as cl

CFG = {
    "e1": dict(name="e1", label="EPYC1", cores=128, cap=141, ram_gb=1133, min_free_disk_gb=0, max_job_threads=128, max_job_ram_gb=1000),
    "e4": dict(name="e4", label="EPYC4", cores=128, cap=141, ram_gb=1133, min_free_disk_gb=0, max_job_threads=128, max_job_ram_gb=1000),
    "e7": dict(name="e7", label="EPYC7", cores=96, cap=106, ram_gb=1000, min_free_disk_gb=0, max_job_threads=96, max_job_ram_gb=900, role="throughput"),
    "pve": dict(name="pve", label="PVE1", cores=28, cap=31, ram_gb=235, min_free_disk_gb=0, min_free_ram_gb=16, max_job_threads=28, max_job_ram_gb=223),
}


class HostChoiceByLoad(unittest.TestCase):
    def choose(self, info, threads=16, ram=48, name="j", hosts=None):
        fleet = cl.Fleet()
        for p in [patch.object(cl, "hosts_table", return_value=[CFG[h] for h in (hosts or ("e1", "e4", "pve"))]),
                  patch.object(cl, "host_cfg", side_effect=lambda h: CFG[h]),
                  patch.object(cl, "host_down", return_value=False),
                  patch.object(cl, "disk_roots", return_value={}),
                  patch.object(cl, "claim_ram", return_value=ram),
                  patch.object(fleet, "compatible", return_value=True),
                  patch.object(fleet, "probe", side_effect=lambda h: dict(disk_gb=1000, **info[h]))]:
            p.start()
            self.addCleanup(p.stop)
        return fleet.choose(dict(name=name, threads=threads))[0]

    def test_measured_1755(self):
        # EPYC1 load 259 with 602 GB available, EPYC4 load 39 with 985 GB, PVE1 nearly idle
        self.assertEqual(self.choose(dict(e1=dict(load1=259, mem_gb=602), e4=dict(load1=39, mem_gb=985),
                                          pve=dict(load1=2, mem_gb=180))), "e4")

    def test_less_loaded_epyc_first_even_with_less_memory(self):
        self.assertEqual(self.choose(dict(e1=dict(load1=20, mem_gb=300), e4=dict(load1=90, mem_gb=900),
                                          pve=dict(load1=0, mem_gb=200))), "e1")

    def test_small_host_takes_small_jobs(self):
        self.assertEqual(self.choose(dict(e1=dict(load1=60, mem_gb=600), e4=dict(load1=70, mem_gb=900),
                                          pve=dict(load1=1, mem_gb=200)), threads=4), "pve")

    def test_small_host_when_both_epycs_are_past_their_cores(self):
        self.assertEqual(self.choose(dict(e1=dict(load1=259, mem_gb=600), e4=dict(load1=140, mem_gb=900),
                                          pve=dict(load1=1, mem_gb=200))), "pve")

    def test_memory_decides_admission(self):
        # the idle host cannot admit 400 GB: the loaded one that can takes it
        self.assertEqual(self.choose(dict(e1=dict(load1=120, mem_gb=600), e4=dict(load1=5, mem_gb=300),
                                          pve=dict(load1=1, mem_gb=200)), ram=400), "e1")


    # FLEET-NEW 2026-10-19: ot-epyc7 (role throughput) takes tile gates/routes/benches first; die jobs avoid it
    E7 = ("e1", "e4", "e7", "pve")

    def test_throughput_host_first_for_tile_jobs(self):
        self.assertEqual(self.choose(dict(e1=dict(load1=10, mem_gb=900), e4=dict(load1=10, mem_gb=900),
                                          e7=dict(load1=60, mem_gb=500), pve=dict(load1=0, mem_gb=200)), hosts=self.E7), "e7")

    def test_throughput_host_past_its_cores_is_ordinary(self):
        self.assertEqual(self.choose(dict(e1=dict(load1=10, mem_gb=900), e4=dict(load1=20, mem_gb=900),
                                          e7=dict(load1=95, mem_gb=500), pve=dict(load1=0, mem_gb=200)), hosts=self.E7), "e1")

    def test_die_job_avoids_throughput_host(self):
        self.assertEqual(self.choose(dict(e1=dict(load1=120, mem_gb=900), e4=dict(load1=110, mem_gb=900),
                                          e7=dict(load1=0, mem_gb=900), pve=dict(load1=0, mem_gb=200)),
                                     name="kvs15_die_sta", hosts=self.E7), "e4")


if __name__ == "__main__":
    unittest.main()
