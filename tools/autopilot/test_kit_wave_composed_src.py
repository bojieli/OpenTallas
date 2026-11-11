"""KW-FIX-36 11-08 (e): composed queue_src -> one provable commit for the queue row (real git, no mocks of git itself)."""
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from test_kit_wave import KW, cfg


def g(repo, *a):
    return subprocess.run(["git", "-C", str(repo), *a], check=True, capture_output=True, text=True).stdout.strip()


class AP:
    DRY = False

    def __init__(self, d, repo, enqueue_rc=0):
        self.AP_DIR = Path(d); self.REPO = repo; self.enqueue_rc = enqueue_rc; self.calls = []; self.logs = []; self.appends = []

    def log(self, x): self.logs.append(x)
    def coord_append(self, *a): self.appends.append(a)

    def sh(self, cmd, timeout=0, input=None):
        if cmd[0] == "git":
            r = subprocess.run(cmd, capture_output=True, text=True)
            return r.returncode, r.stdout, r.stderr
        self.calls.append(cmd)
        return self.enqueue_rc, "", ""


class Composed(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory(); self.addCleanup(td.cleanup)
        self.d = Path(td.name); r = self.repo = self.d / "repo"; r.mkdir()
        g(r, "init", "-q", "-b", "main"); g(r, "config", "user.email", "a@b"); g(r, "config", "user.name", "a")
        self.commit("base.txt"); self.base = g(r, "rev-parse", "HEAD")
        self.intg = self.branch("int", "physical/kit.v")
        self.tool = self.branch("toolfix", "tools/autopilot/prov_view.py")
        self.kit = self.branch("kitfix", "physical/other.v")
        g(r, "checkout", "-q", "int"); g(r, "merge", "-q", "--no-edit", "toolfix"); self.merged = g(r, "rev-parse", "HEAD")
        g(r, "update-ref", "refs/remotes/origin/int", self.merged)
        self.spec = self.d / "spec"; self.spec.mkdir()

    def commit(self, name):
        p = self.repo / name; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(name)
        g(self.repo, "add", name); g(self.repo, "commit", "-q", "-m", name)

    def branch(self, name, f):
        g(self.repo, "checkout", "-q", "-b", name, self.base); self.commit(f); return g(self.repo, "rev-parse", "HEAD")

    def src(self, qs, sha, **die):
        ap = AP(self.d, self.repo)
        return KW.enqueue_src(ap, dict(queue_src=qs, src_sha=sha), die)

    def test_free_text_label_becomes_branch_at_sha(self):
        # KW-FIX-45 11-11: a GRT-ARM pins its sibling's free-text queue_src; the queue refused it (src must be branch@sha)
        ap = AP(self.d, Path("/nonexistent"))
        got = KW.enqueue_src(ap, dict(queue_src="main 730345725942 (QC 12:00 event aa80315f8fd4 landed)", src_sha="7" * 40), {})
        self.assertEqual(got, "main@730345725942")
        self.assertEqual(KW.enqueue_src(ap, dict(queue_src="no sha here", src_sha="7" * 40), {}), "no sha here")

    def test_single_source_unchanged_without_git(self):
        ap = AP(self.d, Path("/nonexistent"))
        self.assertEqual(KW.enqueue_src(ap, dict(queue_src="a/b@abc1234", src_sha="f" * 40), {}), "a/b@abc1234")
        self.assertEqual(KW.enqueue_src(ap, dict(src_sha="abc1234"), {}), "main@abc1234")

    def test_all_parts_in_the_commit(self):
        qs = f"int@{self.intg[:10]}+toolfix@{self.tool[:10]}"
        self.assertEqual(self.src(qs, self.merged), f"int@{self.merged}")

    def test_spaces_in_the_composition(self):
        qs = f"int@{self.intg[:10]} + toolfix@{self.tool[:10]}"
        self.assertEqual(self.src(qs, self.merged), f"int@{self.merged}")

    def test_tools_only_part_outside_the_commit_is_allowed(self):
        qs = f"int@{self.intg[:10]}+toolfix@{self.tool[:10]}"
        self.assertEqual(self.src(qs, self.intg), f"int@{self.intg}")

    def test_kit_content_part_outside_the_commit_is_refused(self):
        qs = f"int@{self.intg[:10]}+kitfix@{self.kit[:10]}"
        with self.assertRaisesRegex(ValueError, "kitfix.*kit content"):
            self.src(qs, self.intg)

    def test_operator_exact_map_wins(self):
        qs = f"int@{self.intg[:10]}+kitfix@{self.kit[:10]}"
        self.assertEqual(self.src(qs, self.intg, queue_src_exact={qs: "cap/x@1234567"}), "cap/x@1234567")
        with self.assertRaisesRegex(ValueError, "not branch@sha"):
            self.src(qs, self.intg, queue_src_exact={qs: "bad row"})

    def test_not_a_composition_or_not_a_commit(self):
        self.assertEqual(self.src("/frozen/queue-source", self.intg), "/frozen/queue-source")   # the queue's own check judges it
        with self.assertRaisesRegex(ValueError, "not a composition"):
            self.src("a+b", self.intg)
        with self.assertRaisesRegex(ValueError, "not a commit"):
            self.src(f"int@{self.intg[:10]}+toolfix@{self.tool[:10]}", "0" * 40)

    def rec(self, qs, sha, reason=KW.SRC_REFUSED + "\n", **over):
        (self.spec / "spec.json").write_text(json.dumps(dict(queue_src=qs, src_sha=sha)))
        r = dict(die="qwen_kvsys", item="kv3_hg_v1", attempt=2, dir=str(self.spec), event="e", geom_dir="/g", kit="intel1:/k/x",
                 cells=100, status="FAIL", reason=reason, stage="geom")
        r["class"] = "FLOW"
        r.update(over)
        return r

    def retry(self, r, ap, c=None):
        return KW.retry_enqueue(ap, c or cfg(), {"items": {r["item"]: r}, "pass_n": 0}, {})

    def test_refused_row_is_resent_once_with_one_commit(self):
        qs = f"int@{self.intg[:10]}+toolfix@{self.tool[:10]}"
        r = self.rec(qs, self.merged); ap = AP(self.d, self.repo)
        self.assertEqual(self.retry(r, ap), 1)
        self.assertEqual(r["status"], "ENQUEUED")
        self.assertEqual(ap.calls[0][ap.calls[0].index("--src") + 1], f"int@{self.merged}")
        self.assertEqual(self.retry(r, ap), 0)
        self.assertEqual(len(ap.calls), 1)

    def test_no_single_commit_fails_on_its_own_reason_and_stops(self):
        qs = f"int@{self.intg[:10]}+kitfix@{self.kit[:10]}"
        r = self.rec(qs, self.intg); ap = AP(self.d, self.repo)
        self.retry(r, ap)
        self.assertEqual((r["status"], r["class"]), ("FAIL", "FLOW"))
        self.assertIn("enqueue source identity", r["reason"]); self.assertEqual(ap.calls, [])
        self.assertEqual(self.retry(r, ap), 0)

    def test_other_enqueue_refusals_stay_failed(self):
        r = self.rec(f"int@{self.intg[:10]}+toolfix@{self.tool[:10]}", self.merged, reason="enqueue rc 1: enqueue: REFUSED: bad row\n")
        ap = AP(self.d, self.repo)
        self.assertEqual(self.retry(r, ap), 0)
        self.assertEqual(r["status"], "FAIL"); self.assertEqual(ap.calls, [])

    def test_hold_items_wait(self):
        r = self.rec(f"int@{self.intg[:10]}+toolfix@{self.tool[:10]}", self.merged); ap = AP(self.d, self.repo)
        self.assertEqual(self.retry(r, ap, cfg(hold_items={"kv3_*": "die owner hold"})), 0)
        self.assertEqual(ap.calls, []); self.assertEqual(r["status"], "PASS"); self.assertTrue(r["enqueue_pending"])


if __name__ == "__main__":
    unittest.main()
