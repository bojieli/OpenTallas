"""GEOM-REVIEW intake gate (OWNER RULE 2026-10-23): a ref_tile route of a FAILING element needs an independent visual
geometry review PASS for the kit's content hash before the closure loop takes it."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

_TMP = tempfile.mkdtemp(prefix="geomrev_")
os.environ.setdefault("CL_STATE", _TMP + "/state")
os.environ["GEOM_REVIEW_DIR"] = _TMP + "/verdicts"
os.environ["GEOM_REVIEW_LANE"] = _TMP + "/GEOM-REVIEW.md"
os.environ["GEOM_REVIEW_COORD_VERDICTS"] = _TMP + "/COORD_VERDICTS.tsv"
os.environ["GEOM_REVIEW_ELEMENTS_URL"] = "http://127.0.0.1:9/none"
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE)]
import geom_review_gate as G  # noqa: E402

G.LANE = Path(_TMP + "/GEOM-REVIEW.md")
G.VERDICT_DIR = Path(_TMP + "/verdicts")
G.COORD_VERDICTS = Path(_TMP + "/COORD_VERDICTS.tsv")


def git(repo, *a):
    return subprocess.run(["git", "-C", repo, *a], check=True, capture_output=True, text=True).stdout.strip()


def make_repo():
    repo = tempfile.mkdtemp(prefix="geomrev_repo_")
    git(repo, "init", "-q")
    git(repo, "config", "user.email", "t@t"); git(repo, "config", "user.name", "t")
    kd = Path(repo, "physical/ref_tile/k1")
    (kd / "views").mkdir(parents=True)
    (kd / "kit.env").write_text("TOP=ot_t\nFW=100\n")
    (kd / "spec.json").write_text('{"outline": {"w": 100, "h": 100}}\n')
    (kd / "views" / "ot_t.lef").write_text("LEF v1\n")
    git(repo, "add", "-A"); git(repo, "commit", "-qm", "c1")
    c1 = git(repo, "rev-parse", "HEAD")
    (kd / "views" / "ot_t.lef").write_text("LEF v2\n")          # route output only: same content hash
    git(repo, "commit", "-qam", "c2")
    c2 = git(repo, "rev-parse", "HEAD")
    (kd / "kit.env").write_text("TOP=ot_t\nFW=80\n")             # real change: new hash
    git(repo, "commit", "-qam", "c3")
    c3 = git(repo, "rev-parse", "HEAD")
    return repo, c1, c2, c3


def spec(commit, block="ot_t", kit="k1"):
    return {"name": f"{kit}-x-{commit[:9]}", "block": block, "ref_tile": True, "source": {"commit": commit},
            "stages": {"route": {"cmd": f"SRC={{SRC}} bash tools/ref_tile/ref_route.sh physical/ref_tile/{kit}/kit.env "
                                        f"{{LABEL}} {{RUN}}/routes"}}}


def job(block, status, updated, name=None):
    return {"name": name or f"{block}-{status}-{updated}", "status": status, "updated": updated, "spec": {"block": block}}


class GeomReviewGate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo, cls.c1, cls.c2, cls.c3 = make_repo()

    def setUp(self):
        for p in G.VERDICT_DIR.glob("*.json") if G.VERDICT_DIR.exists() else []:
            p.unlink()
        G.LANE.write_text("# lane\n")

    def test_hash_ignores_views_and_matches_working_tree(self):
        h1 = G.kit_hash_git(self.repo, self.c1, "physical/ref_tile/k1")
        h2 = G.kit_hash_git(self.repo, self.c2, "physical/ref_tile/k1")
        h3 = G.kit_hash_git(self.repo, self.c3, "physical/ref_tile/k1")
        self.assertEqual(h1, h2)
        self.assertNotEqual(h1, h3)
        self.assertEqual(G.kit_hash_fs(str(Path(self.repo, "physical/ref_tile/k1"))), h3)
        self.assertEqual(G.kit_hash(f"physical/ref_tile/k1@{self.c3}", self.repo), h3)

    def test_spec_kit(self):
        self.assertEqual(G.spec_kit(spec(self.c1)), "physical/ref_tile/k1")
        self.assertIsNone(G.spec_kit({"stages": {"route": {"cmd": "make die"}}}))

    def test_failure_history(self):
        self.assertEqual(G.failure_history("ot_t", [], {}, {}), [])
        fails = [job("ot_t", "NEEDS_RTL", "2026-10-22T10:00:00-07:00")]
        self.assertTrue(G.failure_history("ot_t", fails, {}, {})[0].startswith("loop:"))
        # a CLOSED route after the failure: not failing
        self.assertEqual(G.failure_history("ot_t", fails + [job("ot_t", "CLOSED", "2026-10-22T12:00:00-07:00")], {}, {}), [])
        # REFUSED / CANCELLED spent no route
        self.assertEqual(G.failure_history("ot_t", [job("ot_t", "REFUSED", "x"), job("ot_t", "CANCELLED", "y")], {}, {}), [])
        self.assertTrue(G.failure_history("ot_t", [job("ot_t", "EARLY_FAIL_HOLD", "2026-10-22T10:00:00-07:00")], {}, {}))
        api = {"ot_t": {"category": "needs redesign (no live job)", "failed": 2}}
        self.assertTrue(G.failure_history("ot_t", [], api, {})[0].startswith("api:"))
        self.assertEqual(G.failure_history("ot_t", [], {"ot_t": {"category": "closed (TT era)", "failed": 9}}, {}), [])
        coord = {None: 2e9, "ot_t": [("ot_t__k1", "BAD", "oversized")]}
        self.assertTrue(G.failure_history("ot_t", [], {}, coord)[0].startswith("coord:"))
        self.assertEqual(G.failure_history("ot_t", [], {"ot_t": {"category": "closed (TT era)"}}, coord), [])

    def test_coord_bad_parse(self):
        G.COORD_VERDICTS.write_text(
            "element\tdie\tverdict\tfill\tp90\toutline\treason\n"
            "ot_t__k1\tNone\tBAD\t2\t3\t[1,1]\toversized\nother\tNone\tOK\t30\t5\t[1,1]\tfine\n")
        cb = G.coord_bad(G.COORD_VERDICTS)
        self.assertIn("ot_t", cb)
        self.assertNotIn("other", cb)

    def check(self, commit, jobs, verdicts=None):
        return G.check(spec(commit), self.repo, jobs, api={}, coord={}, verdicts=verdicts)

    def test_not_failing_skips(self):
        self.assertEqual(self.check(self.c3, [])["verdict"], "SKIP")
        self.assertEqual(G.check({"block": "x"}, self.repo, [], {}, {})["verdict"], "SKIP")

    def test_failing_needs_pass_for_hash(self):
        fails = [job("ot_t", "NEEDS_RTL", "2026-10-22T10:00:00-07:00")]
        r = self.check(self.c3, fails)
        self.assertEqual(r["verdict"], "REFUSE")
        self.assertIn("REQ ot_t physical/ref_tile/k1@", r["message"])
        h3 = G.kit_hash_git(self.repo, self.c3, "physical/ref_tile/k1")
        G.record("ot_t", f"physical/ref_tile/k1@{self.c1[:9]}", "PASS", G.kit_hash_git(self.repo, self.c1, "physical/ref_tile/k1"),
                 "ok", "-")
        self.assertEqual(self.check(self.c3, fails)["verdict"], "REFUSE")      # PASS for another content
        self.assertEqual(self.check(self.c2, fails)["verdict"], "PASS")        # views-only change keeps the PASS
        G.record("ot_t", f"physical/ref_tile/k1@{self.c3[:9]}", "FAIL", h3, "low fill", "shrink")
        self.assertIn("FAIL", self.check(self.c3, fails)["message"])
        self.assertEqual(self.check(self.c3, fails)["verdict"], "REFUSE")

    def test_lane_verdict_line_and_latest_wins(self):
        fails = [job("ot_t", "NEEDS_HUMAN", "2026-10-22T10:00:00-07:00")]
        h3 = G.kit_hash_git(self.repo, self.c3, "physical/ref_tile/k1")
        G.LANE.write_text(
            f"## Verdicts\n- VERDICT ot_t physical/ref_tile/k1@{self.c3[:9]} FAIL hash={h3[:16]} fill 3% | FIX: shrink\n"
            f"- VERDICT ot_t physical/ref_tile/k1@{self.c3[:9]} PASS hash={h3[:16]} rebuilt | FIX: -\n")
        self.assertEqual(self.check(self.c3, fails)["verdict"], "PASS")
        G.LANE.write_text(
            f"- VERDICT ot_t physical/ref_tile/k1@{self.c3[:9]} PASS hash={h3[:16]} x\n"
            f"- VERDICT ot_t physical/ref_tile/k1@{self.c3[:9]} FAIL hash={h3[:16]} y\n")
        self.assertEqual(self.check(self.c3, fails)["verdict"], "REFUSE")

    def test_pass_conditional_lets_route_run(self):
        fails = [job("ot_t", "NEEDS_RTL", "2026-10-22T10:00:00-07:00")]
        h3 = G.kit_hash_git(self.repo, self.c3, "physical/ref_tile/k1")
        G.LANE.write_text(f"- VERDICT ot_t physical/ref_tile/k1@{self.c3[:9]} PASS-CONDITIONAL hash={h3[:16]} x | FIX: numbers\n")
        r = self.check(self.c3, fails)
        self.assertEqual(r["verdict"], "PASS")
        self.assertTrue(r["conditional"])
        self.assertIn("PASS-CONDITIONAL", r["message"])

    def test_unhashable_kit_refuses_failing(self):
        fails = [job("ot_t", "NEEDS_RTL", "2026-10-22T10:00:00-07:00")]
        r = G.check(spec(self.c3, kit="nokit"), self.repo, fails, {}, {}, verdicts=[])
        self.assertEqual(r["verdict"], "REFUSE")


class IntakeHook(unittest.TestCase):
    """closure_loop.geom_review_at_submit: REFUSED with no compute, mode warn/off honoured, gate errors never block"""
    @classmethod
    def setUpClass(cls):
        sys.path[:0] = [str(HERE.parent), str(HERE.parent / "ref_tile")]
        import closure_loop as cl
        cls.cl = cl

    def j(self):
        return {"name": "k1-x-abc", "status": "QUEUED", "spec": {"block": "ot_t", "ref_tile": True}, "events": []}

    def run_hook(self, res, mode="refuse"):
        j = self.j()
        with patch.object(self.cl, "_state_mode", return_value=mode), \
                patch.object(G, "check", return_value=res), \
                patch.object(self.cl, "ledger", lambda *a, **k: None), \
                patch.object(self.cl, "event", lambda jj, m: jj["events"].append(m)):
            self.cl.geom_review_at_submit(j, [])
        return j

    def test_refuse(self):
        j = self.run_hook({"verdict": "REFUSE", "message": "GEOM_REVIEW: failing", "hash": "ab"})
        self.assertEqual(j["status"], "REFUSED")
        self.assertIn("GEOM_REVIEW", j["reason"])
        self.assertEqual(j["submit_checks"]["geom_review"]["verdict"], "REFUSE")

    def test_warn_and_off(self):
        self.assertEqual(self.run_hook({"verdict": "REFUSE", "message": "m"}, mode="warn")["status"], "QUEUED")
        j = self.run_hook({"verdict": "REFUSE", "message": "m"}, mode="off")
        self.assertEqual(j["status"], "QUEUED")
        self.assertNotIn("submit_checks", j)

    def test_pass_and_error(self):
        self.assertEqual(self.run_hook({"verdict": "PASS", "message": "ok"})["status"], "QUEUED")
        j = self.j()
        with patch.object(self.cl, "_state_mode", return_value="refuse"), \
                patch.object(G, "check", side_effect=RuntimeError("boom")), \
                patch.object(self.cl, "event", lambda jj, m: jj["events"].append(m)):
            self.cl.geom_review_at_submit(j, [])
        self.assertEqual(j["status"], "QUEUED")
        self.assertIn("skipped", j["events"][0])


if __name__ == "__main__":
    unittest.main()
