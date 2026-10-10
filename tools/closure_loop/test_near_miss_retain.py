"""merge-eco 2026-10-09 NEAR-MISS RETENTION: a non-closed route with TT >= -100 and FF >= -100 keeps its route tree
(final odb/spef/sdc and what re-STA reads) until its element closes -- in the loop's bulk release, in BULK_RELEASE_SH
itself, and in the hourly fleet sweeper."""
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

import closure_loop as cl


def job(name, status="NEEDS_RTL", block="blk", tt=-40.0, ff=-3.0):
    return dict(name=name, status=status, host="ot-epyc1tb", run=f"/srv/x/{name}", events=[],
                spec={"block": block, "source": {"commit": "abc"}}, metrics=dict(ss_ps=tt, ff_ps=ff, drc=0))


class NearMissTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        for name, val in (("STATE", Path(self.tmp.name)), ("NEAR_MISS_JSON", Path(self.tmp.name) / "nm.json")):
            p = patch.object(cl, name, val)
            p.start()
            self.addCleanup(p.stop)

    def test_window(self):
        self.assertTrue(cl.near_miss(job("a")))
        self.assertTrue(cl.near_miss(job("a", tt=-100.0, ff=-100.0)))
        self.assertTrue(cl.near_miss(job("a", tt=12.0, ff=-60.0)))      # hold-only near miss
        self.assertFalse(cl.near_miss(job("a", tt=-100.5)))
        self.assertFalse(cl.near_miss(job("a", ff=-140.0)))
        self.assertFalse(cl.near_miss(job("a", tt=3.0, ff=4.0)))         # passing numbers: not a miss
        self.assertFalse(cl.near_miss(job("a", status="CLOSED")))
        self.assertFalse(cl.near_miss(job("a"), closed={"blk"}))         # element closed: released
        j = job("a")
        j["metrics"] = {}
        self.assertFalse(cl.near_miss(j))

    def _release(self, jobs, closed=frozenset()):
        hosts = [dict(name="ot-epyc1tb")]
        with patch.object(cl, "closed_blocks", return_value=set(closed)), patch.object(cl, "hosts_table", return_value=hosts), \
                patch.object(cl, "load_job", side_effect=lambda n: next(j for j in jobs if j["name"] == n)), \
                patch.object(cl, "save_job"), patch.object(cl, "ssh", return_value=Mock(returncode=0, stdout="FREED 10 5")) as ssh:
            cl.release_bulk(jobs)
        return ssh

    def test_release_bulk_keeps_cancelled_near_miss_until_block_closes(self):
        jobs = [job("nm", status="CANCELLED")]
        ssh = self._release(jobs)
        ssh.assert_not_called()
        rows = json.loads(cl.NEAR_MISS_JSON.read_text())["jobs"]
        self.assertEqual([r["job"] for r in rows], ["nm"])
        ssh = self._release(jobs, closed={"blk"})
        ssh.assert_called_once()
        self.assertTrue(ssh.call_args.args[1].startswith("NEAR_MISS_RELEASE=1\n"))
        self.assertEqual(json.loads(cl.NEAR_MISS_JSON.read_text())["jobs"], [])

    def test_far_miss_cancelled_is_released_with_the_script_guard_on(self):
        ssh = self._release([job("far", status="CANCELLED", tt=-400.0)])
        ssh.assert_called_once()
        self.assertFalse(ssh.call_args.args[1].startswith("NEAR_MISS_RELEASE=1"))

    def test_script_refusal_is_remembered(self):
        jobs = [job("x", status="CANCELLED", tt=-400.0)]
        hosts = [dict(name="ot-epyc1tb")]
        with patch.object(cl, "closed_blocks", return_value=set()), patch.object(cl, "hosts_table", return_value=hosts), \
                patch.object(cl, "load_job", return_value=jobs[0]), patch.object(cl, "save_job"), \
                patch.object(cl, "ssh", return_value=Mock(returncode=4, stdout="NEAR_MISS f -5 -5\nRETAIN")):
            cl.release_bulk(jobs)
        self.assertTrue(jobs[0].get("near_miss_retained"))
        self.assertFalse(jobs[0].get("bulk_released"))
        ssh = self._release(jobs)
        ssh.assert_not_called()

    def _tree(self, tt, ff):
        r = Path(self.tmp.name) / "run"
        b = r / "routes/x/work/orfs/results/asap7/d/base"
        b.mkdir(parents=True, exist_ok=True)
        for f in ("5_1_grt.odb", "6_final.odb", "6_final.spef", "6_final.sdc"):
            (b / f).write_text("x")
        (r / "routes/x/corner_sta.json").write_text(json.dumps(dict(setup_tt=dict(worst_slack_ps=tt),
                                                                     hold_ff=dict(worst_slack_ps=ff))))
        return r, b

    def bulk(self, r, env=""):
        return subprocess.run(["bash", "-c", env + cl.BULK_RELEASE_SH % dict(run=str(r))], capture_output=True, text=True)

    def test_bulk_release_script_refuses_near_miss(self):
        r, b = self._tree(-12.5, 18.0)
        out = self.bulk(r)
        self.assertEqual(out.returncode, 4, out.stdout + out.stderr)
        self.assertTrue((b / "5_1_grt.odb").exists())
        out = self.bulk(r, "NEAR_MISS_RELEASE=1\n")
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.assertFalse((b / "5_1_grt.odb").exists())
        for f in ("6_final.odb", "6_final.spef", "6_final.sdc"):
            self.assertTrue((b / f).exists())

    def test_bulk_release_script_releases_far_miss_and_closed(self):
        for tt, ff in ((-250.0, 5.0), (3.0, 4.0)):
            r, b = self._tree(tt, ff)
            self.assertEqual(self.bulk(r).returncode, 0)
            self.assertFalse((b / "5_1_grt.odb").exists())
            self.assertTrue((b / "6_final.odb").exists())


class SweepNearMissTests(unittest.TestCase):
    def test_sweeper_keeps_near_miss_unit_until_design_closes(self):
        with tempfile.TemporaryDirectory() as t:
            unit = Path(t) / "unit/routes/x"
            unit.mkdir(parents=True)
            (unit / "corner_sta.json").write_text(json.dumps(dict(
                sdc="current_design hfd_x\ncreate_clock", setup_tt=dict(worst_slack_ps=-40.0), hold_ff=dict(worst_slack_ps=-3.0))))
            (Path(t) / "root").mkdir()
            (Path(t) / "prot.txt").write_text("")
            sweep = str(cl.HERE.parent / "fleet" / "sweep.py")
            res = {}
            for closed in ("hfd_y", "hfd_x"):
                (Path(t) / "closed.txt").write_text(closed + "\n")
                argv, env = sys.argv, dict(os.environ)
                os.environ.update(SWEEPLOG=f"{t}/log", SWEEP_CLOSED=f"{t}/closed.txt", SWEEP_SKIP=f"{t}/skip")
                sys.argv = ["sweep.py", "test", f"{t}/prot.txt", "plan", f"{t}/root"]
                try:
                    g = runpy.run_path(sweep)
                finally:
                    sys.argv = argv
                    os.environ.clear()
                    os.environ.update(env)
                res[closed] = g["near_miss_unit"](str(Path(t) / "unit"))
            self.assertIn("design hfd_x", res["hfd_y"])
            self.assertEqual(res["hfd_x"], "")


if __name__ == "__main__":
    unittest.main()
