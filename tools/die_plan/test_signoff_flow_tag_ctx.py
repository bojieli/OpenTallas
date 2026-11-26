"""KW-FIX-32 11-07 (COORD 19:0x, FLOW-CHILD-ETM-CONTEXT at sign-off, DIE-HBM-89 q_spb2 vE): the kit runners hand the
parent flow tag to signoff.py (--flow-tag), so unexpanded child ETMs can count as SIGNED_CHILD_ETM; no tag = unchanged."""
import os
import subprocess
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
REPO = HERE.parents[1]


def signoff_block():
    import gen_phys
    lines = gen_phys.RUN_KIT.splitlines()
    a = next(i for i, ln in enumerate(lines) if ln.startswith("if [ $rc = 0 ] && { [ $GOAL = route ] || [ $GOAL = finish ]; }; then"))
    b = next(i for i in range(a, len(lines)) if lines[i] == "fi")
    return "\n".join(lines[a:b + 1])


class RunKitSignoffFlowTag(unittest.TestCase):
    def run_block(self, ft):
        d = tempfile.mkdtemp()
        K = Path(d)
        (K / "signoff.py").write_text("import sys\nprint('ARGV', ' '.join(sys.argv[1:]))\n")
        sh = "K=%s\nrc=0\nGOAL=route\nIMAGE=img\nFT=%s\n%s\ncat \"$K/signoff.log\"\n" % (K, ft, signoff_block())
        p = subprocess.run(["bash", "-c", sh], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        return next(ln for ln in p.stdout.splitlines() if ln.startswith("ARGV"))

    def test_tag_passed_when_set(self):
        argv = self.run_block("flow-20261107-ei-hbm")
        self.assertIn("--flow-tag flow-20261107-ei-hbm", argv)
        self.assertIn("--corners tt,ff", argv)

    def test_no_tag_unchanged(self):
        argv = self.run_block("")
        self.assertNotIn("--flow-tag", argv)

    def test_same_ft_as_grt_gate(self):
        import gen_phys
        rk = gen_phys.RUN_KIT
        self.assertLess(rk.index('FT=${OT_FLOW_TAG:-$(head -1 "$K/flow_tag" 2>/dev/null)}'),
                        rk.index('"$K/signoff.py" run'))
        p = subprocess.run(["bash", "-n"], input=rk, capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)


class CoreRunnersSignoffFlowTag(unittest.TestCase):
    def test_core_runners(self):
        for rel in ("physical/die_plan/hbm_arch_cores/run_kit_hbm.sh",
                    "physical/die_plan/qwen_kvsys/cores/harden/run_kit_kv.sh"):
            t = (REPO / rel).read_text()
            i = t.index('"$K/signoff.py" run')
            self.assertIn('${FT:+--flow-tag "$FT"}', t[i:i + 300], rel)
            self.assertIn('FT=${OT_FLOW_TAG:-$(head -1 "$K/flow_tag" 2>/dev/null)}', t[:i], rel)
            p = subprocess.run(["bash", "-n", str(REPO / rel)], capture_output=True, text=True)
            self.assertEqual(p.returncode, 0, p.stderr)


if __name__ == "__main__":
    unittest.main()


class StampFlowTag(unittest.TestCase):
    """P-SIGNED-UNVERSIONED: signoff.json is stamped with the flow tag at sign time"""
    def setUp(self):
        import signoff
        self.S = signoff
        self.old = os.environ.get(signoff.FLOW_TAG_ENV)
        os.environ.pop(signoff.UNRESOLVED_ENV, None)

    def tearDown(self):
        if self.old is None:
            os.environ.pop(self.S.FLOW_TAG_ENV, None)
        else:
            os.environ[self.S.FLOW_TAG_ENV] = self.old

    def test_stamped_when_env_set(self):
        os.environ[self.S.FLOW_TAG_ENV] = "flow-20261117-sg-kv"
        self.assertEqual(self.S.stamp_flow_tag({"verdict": "SIGNED"})["flow_tag"], "flow-20261117-sg-kv")

    def test_unset_or_malformed_unchanged(self):
        os.environ.pop(self.S.FLOW_TAG_ENV, None)
        self.assertNotIn("flow_tag", self.S.stamp_flow_tag({}))
        os.environ[self.S.FLOW_TAG_ENV] = "not-a-tag"
        self.assertNotIn("flow_tag", self.S.stamp_flow_tag({}))

    def test_existing_not_overwritten(self):
        os.environ[self.S.FLOW_TAG_ENV] = "flow-20261117-sg-kv"
        self.assertEqual(self.S.stamp_flow_tag({"flow_tag": "flow-20261113-a-kv"})["flow_tag"], "flow-20261113-a-kv")


class DeriveFlowTag(unittest.TestCase):
    """P-SIGNED-UNVERSIONED forward gap: no --flow-tag -> derived from the kit rt/tree, loud only when nothing is found"""
    def setUp(self):
        import signoff
        self.S = signoff
        self.saved = {k: os.environ.pop(k, None) for k in (signoff.FLOW_TAG_ENV, signoff.SRC_COMMIT_ENV, signoff.UNRESOLVED_ENV)}

    def tearDown(self):
        for k, v in self.saved.items():
            os.environ.pop(k, None)
            if v is not None:
                os.environ[k] = v

    def repo(self, td, tag=None):
        r = Path(td) / "repo"
        (r / "tools" / "die_plan").mkdir(parents=True)
        f = r / "tools" / "die_plan" / "signoff.py"
        f.write_text("x = 1\n")
        g = lambda *x: subprocess.run(["git", "-C", str(r)] + list(x), check=True, capture_output=True,
                                      env=dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t"))
        g("init", "-q")
        g("add", "-A")
        g("commit", "-q", "-m", "c")
        if tag:
            g("tag", tag)
        return r, subprocess.run(["git", "-C", str(r), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()

    def test_kit_pin_with_tag_on_commit(self):
        with tempfile.TemporaryDirectory() as td:
            r, sha = self.repo(td, "flow-20261117-sg-kv")
            kit = Path(td) / "kit"
            kit.mkdir()
            (kit / "freeze.json").write_text('{"repo_rev": "%s"}' % sha)
            d = self.S.derive_flow_tag(kit, r / "tools" / "die_plan")
            self.assertEqual((d["src_commit"], d["flow_tag"]), (sha, "flow-20261117-sg-kv"))

    def test_tree_rev_when_no_kit_pin(self):
        with tempfile.TemporaryDirectory() as td:
            r, sha = self.repo(td, "flow-20261117-sg-kv")
            d = self.S.derive_flow_tag(Path(td) / "nokit", r / "tools" / "die_plan")
            self.assertEqual(d["flow_tag"], "flow-20261117-sg-kv")

    def test_commit_without_tag_keeps_source_commit(self):
        with tempfile.TemporaryDirectory() as td:
            r, sha = self.repo(td)
            d = self.S.derive_flow_tag(None, r / "tools" / "die_plan")
            self.assertEqual((d["src_commit"], d["flow_tag"]), (sha, ""))

    def test_nothing_found_warns_and_stamps_unresolved(self):
        with tempfile.TemporaryDirectory() as td:
            with unittest.mock.patch.object(self.S, "_git", return_value=""), \
                    unittest.mock.patch.object(self.S, "kit_source_shas", return_value=[]):
                try:
                    self.assertEqual(self.S.ensure_flow_tag(Path(td)), "")
                    self.assertEqual(self.S.stamp_flow_tag({})["flow_tag"], "UNRESOLVED")
                    self.assertNotIn(self.S.FLOW_TAG_ENV, os.environ)
                finally:
                    os.environ.pop(self.S.UNRESOLVED_ENV, None)

    def test_explicit_env_wins(self):
        os.environ[self.S.FLOW_TAG_ENV] = "flow-20261117-sg-kv"
        self.assertEqual(self.S.ensure_flow_tag(None), "flow-20261117-sg-kv")
