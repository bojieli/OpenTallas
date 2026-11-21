"""FAILLOGS-1630: a failed job keeps the logs/ and reports/ of its work dir after the job dir is deleted."""
import importlib.machinery
import importlib.util
import os
import pathlib
import tempfile
import time
import unittest

HERE = pathlib.Path(__file__).resolve().parent
loader = importlib.machinery.SourceFileLoader("ot_job_faillogs", str(HERE / "ot-job"))
spec = importlib.util.spec_from_loader(loader.name, loader)
m = importlib.util.module_from_spec(spec)
loader.exec_module(m)


class FailLogs(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root = pathlib.Path(t.name)
        self.J = self.root / "claude" / "ot-jobs" / "job1"
        w = self.J / "work" / "run" / "x" / "base"
        for sub, files in (("logs/asap7/gcd/base", {"3_3_place_gp.log": "DPL-0033 here", "big.log": "x" * 5000, "d.odb": "bin"}),
                           ("reports/asap7/gcd/base", {"synth_stat.txt": "stat"}), ("results", {"3_place.odb": "bin"})):
            d = self.J / "work" / "run" / sub
            d.mkdir(parents=True)
            for n, c in files.items():
                (d / n).write_text(c)
        self.dest_root = str(self.root / "claude" / "ot-job-failed-logs")

    def keep(self, rc, **k):
        return m.keep_failed_logs(str(self.J), "serdes_t4", "tag1", rc, dest_root=self.dest_root, **k)

    def test_success_keeps_nothing(self):
        self.assertEqual(self.keep(0), "")
        self.assertFalse(os.path.exists(self.dest_root))

    def test_failure_copies_logs_and_reports_not_databases_or_results(self):
        d = pathlib.Path(self.keep(1))
        self.assertEqual((d / "run/logs/asap7/gcd/base/3_3_place_gp.log").read_text(), "DPL-0033 here")
        self.assertTrue((d / "run/reports/asap7/gcd/base/synth_stat.txt").exists())
        self.assertFalse(list(d.rglob("*.odb")))
        self.assertFalse((d / "run/results").exists())

    def test_size_budget_skips_big_files_and_old_entries_are_pruned(self):
        d = pathlib.Path(self.keep(137, max_bytes=100))
        self.assertFalse((d / "run/logs/asap7/gcd/base/big.log").exists())
        old = pathlib.Path(self.dest_root) / "old-x"
        old.mkdir()
        (old / "f").write_text("1")
        t = time.time() - 15 * 86400
        os.utime(old, (t, t))
        self.keep(1)
        self.assertFalse(old.exists())


if __name__ == "__main__":
    unittest.main()
