"""tools/view_lineage.py: archive re-export receipts bind only while files and the CLOSED job are unchanged."""
import json, shutil, sys, tempfile, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import view_lineage as VL

VIEW = HERE.parent / "physical/s81_die_views/views/dsfd_stnh_566x1"
JOB = "s81-dsfd-stnh-566x1-2e2d7aa3f-arch"


class ViewLineage(unittest.TestCase):
    def setUp(self):
        self.t = Path(tempfile.mkdtemp())
        self.v = self.t / "dsfd_stnh_566x1"
        shutil.copytree(VIEW, self.v)
        (self.v / VL.RECEIPT).unlink(missing_ok=True)
        self.jobs = self.t / "jobs"
        self.jobs.mkdir()
        self.set_job("CLOSED", "CLOSED TT +76.93 / FF +382.33 ps DRC 0")

    def set_job(self, status, reason):
        (self.jobs / f"{JOB}.json").write_text(json.dumps(dict(name=JOB, status=status, reason=reason)))

    def test_archive_reexport_binds_and_drift_unbinds(self):
        r = VL.build_archive_reexport(self.v, None, self.jobs)
        self.assertEqual(r["verdict"], "PASS", r["why"])
        self.assertEqual(r["original_job"], JOB)
        self.assertTrue(r["native_audit"]["pass"])
        (self.v / VL.RECEIPT).write_text(json.dumps(r))
        self.assertTrue(VL.verify(self.v, self.jobs)[0])
        with open(self.v / "dsfd_stnh_566x1.lef", "a") as fh:
            fh.write("# edit\n")
        ok, why, _ = VL.verify(self.v, self.jobs)
        self.assertFalse(ok)
        self.assertIn("changed", why)

    def test_job_not_closed_refused(self):
        self.set_job("NEEDS_RTL", "TT -5 / FF 1 / DRC 0")
        r = VL.build_archive_reexport(self.v, None, self.jobs)
        self.assertEqual(r["verdict"], "FAIL")


if __name__ == "__main__":
    unittest.main()
