"""job-dir placement: the scratch root with the most USABLE free space takes new job dirs (scratch3 included), the per-disk floors stay (COORD 11-17)."""
import contextlib, importlib.machinery, importlib.util, os, pathlib, subprocess, tempfile, unittest, io, json, base64, sys, types
from unittest import mock
import test_ot_run_scratch_disk as T

m = T.m
S2, S3 = "/srv/opentallas-scratch2", "/srv/opentallas-scratch3"


def probe(s2, s3, root_free=None):
    return (f"OT_SCRATCH_FREE {S2} {s2} 0\nOT_SCRATCH_FREE {S3} {s3} 1\nOT_ROOTFS 9 {root_free or s3}\nOT_DIR_ONROOT 0\n")


class Admission(unittest.TestCase):
    def test_scratch3_with_far_more_room_takes_the_job_dirs_and_keeps_the_root_floor(self):
        row = m.scratch_disk({"disk_gb": 55}, None, probe(55, 619), host="epyc2")
        self.assertTrue(row.get("scratch_second")); self.assertEqual(row["scratch_disk"], S3)
        self.assertEqual(row["scratch_disk_gb"], 619 - m.root_floor("epyc2"))          # usable = root free - the 150 GB root floor
        self.assertEqual(m.host_refusal(row), "")

    def test_a_close_scratch2_keeps_the_job_dirs(self):
        row = m.scratch_disk({"disk_gb": 400}, None, probe(400, 450), host="epyc2")    # usable scratch3 300 < 400 + 50
        self.assertFalse(row.get("scratch_second")); self.assertEqual(row["scratch_disk"], S2)

    def test_scratch3_without_usable_room_is_never_chosen(self):
        row = m.scratch_disk({"disk_gb": 200}, None, probe(200, 160), host="epyc7")    # 160 - 150 = 10 < the 20 GB second floor
        self.assertFalse(row.get("scratch_second")); self.assertEqual(row["scratch_disk"], S2)

    def test_every_build_host_with_scratch3_is_authorized(self):
        for h in ("epyc2", "intel1", "epyc7", "epyc8", "epyc9", "epyc10"):
            self.assertIn(S3, m.second_roots(h), h)

    def test_the_scratch2_floor_still_refuses_when_nothing_else_has_room(self):
        row = m.scratch_disk({"disk_gb": 30}, None, probe(30, 100), host="epyc7")      # scratch3 usable negative
        self.assertTrue(m.host_refusal(row))


class Shell(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="otplace3-"); self.addCleanup(self.temp.cleanup)
        self.base = pathlib.Path(self.temp.name)
        self.s2, self.s3 = self.base / "srv/opentallas-scratch2", self.base / "srv/opentallas-scratch3"
        for r in (self.s2, self.s3): (r / "claude").mkdir(parents=True)

    def ot_scratch(self, free2, free3):
        env = T.fake_bin(self.base, {str(self.s2): 2, str(self.s3): 1}, {str(self.s2): free2, str(self.s3): free3}, 9)
        sh = m.scratch_env("epyc2").replace("/srv/opentallas-scratch", str(self.base) + "/srv/opentallas-scratch")
        return subprocess.run(["bash", "-c", sh + 'echo "$OT_SCRATCH"'], capture_output=True, text=True, env=env).stdout.strip()

    def test_ot_scratch_picks_the_most_usable_free_root(self):
        self.assertEqual(self.ot_scratch(55, 619), str(self.s3))
        self.assertEqual(self.ot_scratch(835, 619), str(self.s2))
        self.assertEqual(self.ot_scratch(400, 450), str(self.s2))

    def test_the_host_placer_uses_the_same_margin_rule(self):
        self.assertIn("max(second.values()) > max(disk.values()) + SMARGIN", m.SCRATCH_PLACE_PY)
        self.assertIn("bs>bd+mg", m.scratch_env("epyc2"))
