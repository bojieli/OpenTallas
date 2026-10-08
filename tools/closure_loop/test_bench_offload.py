import unittest
from unittest.mock import patch

import closure_loop as C

SPEC = {"stages": {"bench": [{"name": "b", "cmd": "true"}], "route": {"cmd": "r"}}}


class BenchOffload(unittest.TestCase):
    def test_main_track_needs_exclude_benches(self):
        self.assertIn("verilator", C.job_needs(SPEC))
        self.assertEqual(C.job_needs(SPEC, benches=False), {"orfs"})
        self.assertEqual(C.bench_needs(SPEC), {"verilator", "iverilog", "yosys"})

    def test_offload_host_compatible_for_orfs_only_main_track(self):
        f = C.Fleet()
        hosts = [dict(name="lh", caps=["orfs"], bench_offload=True), dict(name="nb", caps=["orfs"])]
        with patch.object(C, "hosts_table", return_value=hosts), \
             patch.object(f, "toolchain", return_value={"img_latest": "x"}), patch.object(C, "bare_image_ids", return_value=[]):
            self.assertTrue(f.compatible("lh", SPEC))
            self.assertFalse(f.compatible("nb", SPEC))


if __name__ == "__main__":
    unittest.main()
