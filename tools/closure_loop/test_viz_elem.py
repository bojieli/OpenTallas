"""VIZ-ELEM (owner 2026-10-10): finish(CLOSED) starts the Chip Explorer element-page export detached and never lets it
block or fail a closure; deep release keeps the run dir while a fresh export marker says running."""
import datetime as dt
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("CL_STATE", tempfile.mkdtemp(prefix="vizelem_"))
import closure_loop as cl  # noqa: E402

NOW = 2_000_000_000.0
OLD = "2033-05-17T00:00:00-07:00"      # > 6 h before NOW


def job(name="j1", status="CLOSED", **kw):
    j = dict(name=name, status=status, host="ot-epyc1tb", run=f"/srv/x/{name}", spec={"block": "blk"},
             events=[f"{OLD} {status}: verdict"], metrics=dict(ss_ps=5.0, ff_ps=1.0, drc=0, orfs_dir=f"/srv/x/{name}/o"))
    j.update(kw)
    return j


class VizElem(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.p = [patch.object(cl, "VIZ_ELEM_MARKS", self.d / "marks"), patch.object(cl, "VIZ_ELEM_LOG", self.d / "viz.log"),
                  patch.object(cl, "event", lambda j, t: j.setdefault("ev", []).append(t)),
                  patch.object(cl, "ledger", lambda *a, **k: None), patch.object(cl, "experiment", lambda *a, **k: None)]
        for p in self.p:
            p.start()

    def tearDown(self):
        for p in self.p:
            p.stop()

    def test_finish_closed_starts_detached_export(self):
        j = job()
        with patch.object(cl.subprocess, "Popen") as po:
            cl.finish(j, "CLOSED", "ok", "CLOSED")
        self.assertEqual(j["status"], "CLOSED")
        argv, kw = po.call_args[0][0], po.call_args[1]
        self.assertIn("auto", argv)
        self.assertEqual(argv[argv.index("--job") + 1], "j1")
        self.assertTrue(kw.get("start_new_session"))                         # detached: own session
        m = json.loads((self.d / "marks" / "j1.json").read_text())
        self.assertEqual(m["state"], "running")

    def test_export_failure_never_blocks_closure(self):
        j = job()
        with patch.object(cl.subprocess, "Popen", side_effect=OSError("no fork")):
            cl.finish(j, "CLOSED", "ok", "CLOSED")                          # must not raise
        self.assertEqual(j["status"], "CLOSED")
        self.assertTrue(any("export not started" in e for e in j["ev"]))

    def test_only_closed_and_switch(self):
        with patch.object(cl.subprocess, "Popen") as po:
            cl.finish(job(status="NEEDS_RTL"), "NEEDS_RTL", "x", "x")
            self.assertFalse(po.called)
            with patch.dict(os.environ, {"CL_VIZ_ELEM": "0"}):
                cl.finish(job(), "CLOSED", "ok", "CLOSED")
            self.assertFalse(po.called)

    def _marker(self, state, age_h):
        (self.d / "marks").mkdir(parents=True, exist_ok=True)
        t = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=age_h)
        (self.d / "marks" / "j1.json").write_text(json.dumps(dict(state=state, updated=t.isoformat())))

    def test_running_marker(self):
        self.assertFalse(cl.viz_elem_running(job()))                        # no marker
        self._marker("running", 1)
        self.assertTrue(cl.viz_elem_running(job()))
        self._marker("running", 13)
        self.assertFalse(cl.viz_elem_running(job()))                        # stale exporter is not live
        self._marker("done", 0)
        self.assertFalse(cl.viz_elem_running(job()))

    def test_deep_release_waits_for_export(self):
        j = job(status="NEEDS_RTL", metrics=dict(ss_ps=-400.0, ff_ps=-3.0, drc=0, orfs_dir="/srv/x/j1/o"))
        ev = dict(sha="f" * 40, files="", recs="", refs=[])
        with patch.object(cl, "revoked_closures", return_value=(set(), set())):
            self.assertEqual(cl.deep_release_mode(j, set(), ev, now=NOW), "fail")
            self._marker("running", 0)
            self.assertIsNone(cl.deep_release_mode(j, set(), ev, now=NOW))


if __name__ == "__main__":
    unittest.main()
