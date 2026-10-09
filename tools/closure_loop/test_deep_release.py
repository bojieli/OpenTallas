"""disk-1210 2026-10-09 DEEP RELEASE: CLOSED-on-main jobs keep only the accepted 6_final.* + logs/reports; terminal
failures older than 6 h lose ORFS intermediates, objects/, the src snapshot and bench builds; near misses on open
elements keep their re-STA / ECO inputs; receipt-referenced paths are never deleted."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

import closure_loop as cl

NOW = 2_000_000_000.0
OLD = "2033-05-17T00:00:00-07:00"      # > 6 h before NOW
NEW = "2033-05-18T03:00:00+00:00"      # 30 min before NOW


def job(name, status="NEEDS_RTL", tt=-400.0, ff=-3.0, at=OLD, block="blk", **kw):
    j = dict(name=name, status=status, host="ot-epyc1tb", run=f"/srv/x/{name}", spec={"block": block},
             events=[f"{at} {status}: verdict"], metrics=dict(ss_ps=tt, ff_ps=ff, drc=0, orfs_dir=f"/srv/x/{name}/cl/eco/pass1/orfs"))
    j.update(kw)
    return j


EV = dict(sha="f" * 40, files="results/x/rec_on_main.json\n", recs="", refs=[])


class ModeTests(unittest.TestCase):
    def mode(self, j, closed=frozenset()):
        with patch.object(cl, "revoked_closures", return_value=(set(), set())):
            return cl.deep_release_mode(j, set(closed), EV, now=NOW)

    def test_modes(self):
        self.assertEqual(self.mode(job("a")), "fail")
        self.assertIsNone(self.mode(job("a", at=NEW)))                              # < 6 h since the verdict
        self.assertEqual(self.mode(job("a", tt=-40.0)), "nearmiss")                  # open element near miss
        self.assertEqual(self.mode(job("a", tt=-40.0), closed={"blk"}), "fail")      # element closed since
        self.assertEqual(self.mode(job("a", status="EARLY_FAIL_HOLD")), "fail")
        self.assertEqual(self.mode(job("a", status="CANCELLED")), "fail")
        self.assertIsNone(self.mode(job("a", status="RUNNING")))
        self.assertIsNone(self.mode(job("a", status="SMOKE_OK")))
        self.assertIsNone(self.mode(job("a", deep_released={"at": OLD})))
        self.assertEqual(self.mode(job("rec_on_main", status="CLOSED", tt=20, ff=20)), "closed")
        self.assertIsNone(self.mode(job("not_recorded", status="CLOSED", tt=20, ff=20)))

    def test_release_bookkeeping_does_not_reset_the_age(self):
        j = job("a")
        j["events"].append(f"{NEW} route bulk released (cancelled; MB before/after 1 1)")
        self.assertGreater(cl._terminal_age_h(j, NOW), 6)

    def test_revoked_closure_is_a_failure(self):
        j = job("rev", status="CLOSED", tt=20, ff=20)
        with patch.object(cl, "revoked_closures", return_value=({"rev"}, set())):
            self.assertEqual(cl.deep_release_mode(j, set(), EV, now=NOW), "fail")


class ScriptTests(unittest.TestCase):
    """DEEP_RELEASE_PY on a real temp tree"""
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.R = Path(self.tmp.name) / "run"
        base = "routes/r/work/orfs/results/asap7/d/base"
        eco = "cl/eco/pass1/orfs/results/asap7/d/base"
        eco2 = "cl/eco/pass2/orfs/results/asap7/d/base"
        self.files = [f"{base}/{f}" for f in ("1_synth.v", "3_place.odb", "4_cts.odb", "5_2_route.odb", "6_final.odb",
                                              "6_final.spef", "6_final.sdc", "6_final.gds", "6_final.odb.pre_eco")]
        self.files += [f"{eco}/6_final.odb", f"{eco2}/6_final.odb", f"{eco2}/6_final.v",
                       "routes/r/work/orfs/objects/asap7/d/base/lib.lib", "routes/r/work/orfs/logs/asap7/d/base/5_2_route.log",
                       "routes/r/work/orfs/reports/asap7/d/base/6_finish.rpt", "routes/r/corner_sta.json",
                       "src/SOURCE_COMMIT", "src/rtl/a.sv", "bench_src_a1/rtl/b.sv", "bench/obj/Vtb.mk", "bench/obj/Vtb__pch.h.gch",
                       "bench/obj/Vtb", "bench/tb.sv", "bench/sim.log", "cl/route.log"]
        for f in self.files:
            p = self.R / f
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("abc123\n" if f == "src/SOURCE_COMMIT" else "x" * 5000)
        self.eco = str(self.R / "cl/eco/pass1/orfs")

    def run_mode(self, mode, src_commit="abc123", refs=()):
        arg = dict(run=str(self.R), mode=mode, src_commit=src_commit, refs=[str(self.R / r) for r in refs],
                   final_dirs=[self.eco] if mode == "closed" else [])
        r = subprocess.run([sys.executable, "-c", cl.DEEP_RELEASE_PY], env={**os.environ, "OT_DR": json.dumps(arg)},
                           capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("DEEP_FREED", r.stdout)
        return {f for f in self.files if (self.R / f).exists()}

    def common_kept(self, left):
        for f in ("routes/r/work/orfs/logs/asap7/d/base/5_2_route.log", "routes/r/work/orfs/reports/asap7/d/base/6_finish.rpt",
                  "routes/r/corner_sta.json", "bench/tb.sv", "bench/sim.log", "cl/route.log"):
            self.assertIn(f, left)
        for f in ("bench/obj/Vtb__pch.h.gch", "bench/obj/Vtb", "bench/obj/Vtb.mk", "bench_src_a1/rtl/b.sv"):
            self.assertNotIn(f, left)
        for f in left:
            self.assertFalse(f.endswith(("3_place.odb", "4_cts.odb", "1_synth.v", "6_final.gds", ".pre_eco")), f)

    def test_fail(self):
        left = self.run_mode("fail")
        self.common_kept(left)
        self.assertNotIn("routes/r/work/orfs/results/asap7/d/base/5_2_route.odb", left)
        self.assertIn("routes/r/work/orfs/results/asap7/d/base/6_final.odb", left)
        self.assertIn("cl/eco/pass2/orfs/results/asap7/d/base/6_final.odb", left)
        self.assertNotIn("src/rtl/a.sv", left)
        self.assertNotIn("routes/r/work/orfs/objects/asap7/d/base/lib.lib", left)

    def test_closed_keeps_only_accepted_and_route_finals(self):
        left = self.run_mode("closed")
        self.common_kept(left)
        self.assertIn("cl/eco/pass1/orfs/results/asap7/d/base/6_final.odb", left)
        self.assertIn("routes/r/work/orfs/results/asap7/d/base/6_final.spef", left)
        self.assertNotIn("cl/eco/pass2/orfs/results/asap7/d/base/6_final.odb", left)
        self.assertNotIn("routes/r/work/orfs/results/asap7/d/base/5_2_route.odb", left)

    def test_nearmiss_keeps_reSTA_inputs(self):
        left = self.run_mode("nearmiss")
        self.common_kept(left)
        for f in ("routes/r/work/orfs/results/asap7/d/base/5_2_route.odb", "routes/r/work/orfs/objects/asap7/d/base/lib.lib",
                  "src/rtl/a.sv", "cl/eco/pass2/orfs/results/asap7/d/base/6_final.odb"):
            self.assertIn(f, left)

    def test_src_kept_unless_commit_matches(self):
        self.assertIn("src/rtl/a.sv", self.run_mode("fail", src_commit="other"))
        self.assertIn("src/rtl/a.sv", self.run_mode("fail", src_commit=""))

    def test_receipt_refs_are_kept(self):
        left = self.run_mode("fail", refs=["routes/r/work/orfs/results/asap7/d/base/5_2_route.odb", "bench_src_a1",
                                           "src/rtl/a.sv"])
        self.assertIn("routes/r/work/orfs/results/asap7/d/base/5_2_route.odb", left)
        self.assertIn("bench_src_a1/rtl/b.sv", left)
        self.assertIn("src/rtl/a.sv", left)

    def test_generic_ref_keeps_finals_in_closed_mode(self):
        left = self.run_mode("closed", refs=["cl/eco/pass2/orfs"])
        self.assertIn("cl/eco/pass2/orfs/results/asap7/d/base/6_final.odb", left)


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        p = patch.object(cl, "STATE", Path(self.tmp.name))
        p.start()
        self.addCleanup(p.stop)

    def release(self, jobs, out=Mock(returncode=0, stdout="DEEP_FREED 1234\n")):
        with patch.object(cl, "closed_blocks", return_value=set()), \
                patch.object(cl, "hosts_table", return_value=[dict(name="ot-epyc1tb")]), \
                patch.object(cl, "revoked_closures", return_value=(set(), set())), \
                patch.object(cl, "_main_evidence", return_value=EV), \
                patch.object(cl, "load_job", side_effect=lambda n: next(j for j in jobs if j["name"] == n)), \
                patch.object(cl, "save_job"), patch.object(cl, "ssh", return_value=out) as ssh:
            cl.release_deep(jobs, now=NOW)
        return ssh

    def test_marks_and_passes_mode(self):
        jobs = [job("a")]
        ssh = self.release(jobs)
        ssh.assert_called_once()
        self.assertIn('"mode": "fail"', ssh.call_args.args[1].split("\n", 1)[0].replace("\\", ""))
        self.assertEqual(jobs[0]["deep_released"]["freed_mb"], 1234)

    def test_live_run_is_not_marked(self):
        jobs = [job("a")]
        self.release(jobs, out=Mock(returncode=3, stdout="LIVE pid 7"))
        self.assertNotIn("deep_released", jobs[0])

    def test_sibling_on_same_run_dir_blocks(self):
        sib = job("b", status="RUNNING")
        sib["run"] = "/srv/x/a"
        ssh = self.release([job("a"), sib])
        ssh.assert_not_called()

    def test_per_tick_cap(self):
        ssh = self.release([job(f"j{i}") for i in range(10)])
        self.assertEqual(ssh.call_count, cl.DEEP_RELEASE_PER_TICK)


if __name__ == "__main__":
    unittest.main()
