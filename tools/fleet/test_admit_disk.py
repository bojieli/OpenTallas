"""admit_disk PER-DISK (drive-1010 2026-10-10): a job is judged by the filesystem its directory lives on."""
import json
import os
import sys
import tempfile
import unittest
from collections import namedtuple
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent))
import admit_disk as A  # noqa: E402

U = namedtuple("U", "total used free")
GB = 2**30


class PerDisk(unittest.TestCase):
    def setUp(self):
        self.t = Path(tempfile.mkdtemp())
        self.table = self.t / "admit_disk.json"
        self.table.write_text(json.dumps({"roots": {"/full": 200, "/": 100}}))
        self.p = patch.object(A, "TABLE", str(self.table)); self.p.start(); self.addCleanup(self.p.stop)
        devs = {"/full": 1, "/full/job": 1, "/big": 2, "/big/job": 2, "/": 3}
        free = {"/full": 133, "/big": 2700, "/": 800, "/big/job": 2700}
        self.d = patch.object(A, "_dev", side_effect=lambda p: devs.get(p.rstrip("/") or "/"))
        self.u = patch.object(A.shutil, "disk_usage", side_effect=lambda p: U(0, 0, free.get(p.rstrip("/") or "/", 2700) * GB))
        self.d.start(); self.u.start(); self.addCleanup(self.d.stop); self.addCleanup(self.u.stop)

    def test_job_on_other_disk_is_admitted(self):
        self.assertEqual(A.short("/big/job"), [])

    def test_job_on_full_disk_waits(self):
        self.assertEqual(A.short("/full/job"), ["/full 133 GB free < 200"])

    def test_all_mode_keeps_old_behaviour(self):
        with patch.dict(os.environ, {"ADMIT_DISK_ALL": "1"}):
            self.assertEqual(A.short("/big/job"), ["/full 133 GB free < 200"])

    def test_untabled_disk_gets_default_floor(self):
        with patch.object(A.shutil, "disk_usage", side_effect=lambda p: U(0, 0, (150 if p == "/big/job" else 800) * GB)):
            self.assertEqual(A.short("/big/job"), ["/big/job 150 GB free < 200"])


if __name__ == "__main__":
    unittest.main()
