"""STALE-SAVE 2026-10-09 (flow-fix-0410): a worker's save never overwrites a newer job file with an older snapshot.

pi-ta15prod hm10/hm25: a hand re-entry (status READY + event) was reverted twice to a ~45-min-old copy by a daemon
worker that had loaded the job before the edit, run a long step and then saved.  Simulated here: a worker loads the job
(load_job / all_jobs), an external writer edits the file WITHOUT the job flock (like a hand edit), then the worker saves.
"""
import json
import os
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import closure_loop as cl


class StaleSaveTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        p = patch.object(cl, "STATE", Path(self.tmp.name))
        p.start()
        self.addCleanup(p.stop)
        lg = patch.object(cl, "log")
        lg.start()
        self.addCleanup(lg.stop)
        cl.save_job(dict(name="ta15", status="NEEDS_RTL", spec={"block": "b"}, events=["routed"], verdict={"v": 1}))

    def hand_edit(self, **fields):
        """an agent's edit: plain read + write of the file, no flock, no daemon helper"""
        p = cl.jpath("ta15")
        time.sleep(0.01)          # distinct mtime_ns even on coarse clocks
        d = json.loads(p.read_text())
        d.update(fields)
        p.write_text(json.dumps(d, indent=1) + "\n")

    def log_text(self):
        f = Path(self.tmp.name) / cl.STALE_SAVE_LOG
        return f.read_text() if f.exists() else ""

    def test_conflicting_stale_save_is_refused_and_logged(self):
        worker = cl.load_job("ta15")                        # daemon worker snapshot (02:14)
        self.hand_edit(status="READY", events=["routed", "hand re-entry"])   # 02:58 hand edit
        worker["status"] = "BENCH"                          # 03:00 worker acts on its old copy and saves
        cl.save_job(worker)
        now = cl.load_job("ta15")
        self.assertEqual(now["status"], "READY")
        self.assertEqual(now["events"], ["routed", "hand re-entry"])
        self.assertEqual(worker["status"], "READY", "the worker's copy is replaced by the file")
        self.assertIn("REFUSED", self.log_text())
        self.assertIn("status", self.log_text())

    def test_disjoint_changes_are_merged(self):
        worker = cl.load_job("ta15")
        self.hand_edit(events=["routed", "hand note"])
        worker["verdict"] = {"v": 2}
        cl.save_job(worker)
        now = cl.load_job("ta15")
        self.assertEqual(now["events"], ["routed", "hand note"])
        self.assertEqual(now["verdict"], {"v": 2})
        self.assertIn("MERGED", self.log_text())

    def test_snapshot_from_all_jobs_is_checked_too(self):
        worker = [j for j in cl.all_jobs() if j["name"] == "ta15"][0]
        self.hand_edit(status="READY")
        worker["status"] = "RUNNING"
        cl.save_job(worker)
        self.assertEqual(cl.load_job("ta15")["status"], "READY")

    def test_unchanged_file_saves_normally_and_repeated_saves_work(self):
        j = cl.load_job("ta15")
        j["status"] = "READY"
        cl.save_job(j)
        j["status"] = "RUNNING"          # second save of the same copy: its version was refreshed by the first
        cl.save_job(j)
        self.assertEqual(cl.load_job("ta15")["status"], "RUNNING")
        self.assertEqual(self.log_text(), "")

    def test_concurrent_worker_threads(self):
        """two daemon threads with copies loaded at the same version: the later save cannot revert the earlier"""
        a, b = cl.load_job("ta15"), cl.load_job("ta15")
        go = threading.Event()

        def first():
            a["status"] = "RUNNING"
            cl.save_job(a)
            go.set()
        t = threading.Thread(target=first)
        t.start()
        go.wait(5)
        t.join()
        b["status"] = "NEEDS_HUMAN"
        cl.save_job(b)
        self.assertEqual(cl.load_job("ta15")["status"], "RUNNING")

    def test_cancelled_stays_absorbing(self):
        worker = cl.load_job("ta15")
        self.hand_edit(status="CANCELLED")
        worker["status"] = "READY"
        cl.save_job(worker)
        self.assertEqual(cl.load_job("ta15")["status"], "CANCELLED")

    def test_plain_dict_keeps_legacy_behaviour(self):
        self.hand_edit(status="READY")
        cl.save_job(dict(name="ta15", status="RUNNING", spec={"block": "b"}))
        self.assertEqual(cl.load_job("ta15")["status"], "RUNNING")


    def test_recovery_pass_does_not_rewrite_its_old_snapshot(self):
        """the actual writer: reevaluate_benches saved its pass-start snapshot on a no-op branch"""
        from unittest.mock import patch as p2
        cl.save_job(dict(cl.load_job("ta15"), status="NEEDS_RTL", reason="bench_exact expected PASS but rc=1",
                         stage_tag="route.a1"))
        snapshot = [j for j in cl.all_jobs() if j["name"] == "ta15"]          # recovery pass start (02:14)
        self.hand_edit(status="READY", reason=None, events=["hand re-entry"])  # 02:58
        with p2.object(cl, "stage_list", return_value=[dict(key="bench_exact", expect="pass")]):
            cl.reevaluate_benches(snapshot)                                     # 03:00
        now = cl.load_job("ta15")
        self.assertEqual((now["status"], now["events"]), ("READY", ["hand re-entry"]))

    def test_recovery_rejudge_acts_on_the_current_file(self):
        from unittest.mock import patch as p2
        cl.save_job(dict(cl.load_job("ta15"), status="NEEDS_RTL", reason="bench_exact expected PASS but rc=1",
                         stage_tag="bench_exact.a1", benches={}))
        snapshot = [j for j in cl.all_jobs() if j["name"] == "ta15"]
        self.hand_edit(status="READY", reason=None)
        with p2.object(cl, "stage_list", return_value=[dict(key="bench_exact", expect="pass")]), \
             p2.object(cl, "bench_outcome", return_value=True), p2.object(cl, "ledger"), p2.object(cl, "experiment"):
            cl.reevaluate_benches(snapshot)
        now = cl.load_job("ta15")
        self.assertEqual(now["status"], "READY")
        self.assertNotIn("fix_requeued", now)


if __name__ == "__main__":
    unittest.main()
