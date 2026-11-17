import importlib.machinery, importlib.util, os, pathlib, subprocess, tempfile, unittest, sys

H = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(H))
loader = importlib.machinery.SourceFileLoader("olc", str(H / "ot-lane-clone"))
M = importlib.util.module_from_spec(importlib.util.spec_from_loader("olc", loader)); loader.exec_module(M)
import block_raw_rm as B


class Lane(unittest.TestCase):
    def test_plan_first_clone_then_fetch_never_a_plain_checkout(self):
        w = tempfile.mkdtemp()
        p = M.plan("/srv/opentallas-scratch2/claude/l1", "main", ["tools", "rtl"], warm=w + "/none.git", origin="o")
        self.assertEqual(p[0][:4], ["git", "clone", "--bare", "--filter=blob:none"]); self.assertIn("--no-checkout", p[1])
        os.mkdir(w + "/w.git")
        p = M.plan("/srv/opentallas-scratch2/claude/l1", "main", ["tools"], warm=w + "/w.git", origin="o")
        self.assertIn("fetch", p[0]); self.assertEqual(p[3], ["git", "-C", "/srv/opentallas-scratch2/claude/l1", "sparse-checkout", "set", "tools"])

    def test_refusals(self):
        self.assertIn("under /srv/opentallas-scratch", M.check("/tmp/x"))
        self.assertIn("free", M.check("/srv/opentallas-scratch2/claude/none", min_free=10 ** 9))
        d = tempfile.mkdtemp(); open(d + "/f", "w").close()
        M.check.__globals__["os"]            # keep module import honest
        self.assertEqual(M.check("/srv/opentallas-scratch2/claude/__none__", min_free=0), "") if os.path.isdir("/srv/opentallas-scratch2") else None

    def test_end_to_end_with_a_local_origin(self):
        d = pathlib.Path(tempfile.mkdtemp()); g = ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "init.defaultBranch=main"]
        o = d / "o.git"; subprocess.run(g + ["init", "-q", "--bare", str(o)], check=True)
        w = d / "w"; subprocess.run(g + ["clone", "-q", str(o), str(w)], check=True, capture_output=True)
        for sub in ("tools", "rtl", "physical"):
            (w / sub).mkdir(); (w / sub / "f").write_text(sub)
        subprocess.run(g + ["add", "-A"], cwd=w, check=True); subprocess.run(g + ["commit", "-qm", "x"], cwd=w, check=True)
        subprocess.run(g + ["push", "-q", "origin", "main"], cwd=w, check=True)
        M.WARM = str(d / "warm.git"); M.ORIGIN = str(o)
        dest = d / "lane"
        steps = M.plan(str(dest), "main", ["tools", "rtl"], warm=M.WARM, origin=M.ORIGIN)
        for s in steps:
            subprocess.run(s[:1] + ["-c", "protocol.file.allow=always"] + s[1:], check=True, capture_output=True)
        self.assertTrue((dest / "tools" / "f").exists() and (dest / "rtl" / "f").exists()); self.assertFalse((dest / "physical").exists())

    def test_hook_blocks_raw_full_checkouts_on_scratch(self):
        for c in ("git clone git@github.com:x/OpenTallas.git /srv/opentallas-scratch2/claude/lane1/repo",
                  "git -C /srv/opentallas-scratch2/claude/l worktree add /srv/opentallas-scratch2/claude/l2 main"):
            self.assertTrue(B.blocked(c), c)
        for c in ("ot-lane-clone /srv/opentallas-scratch2/claude/lane1", "git clone --filter=blob:none --sparse x /srv/opentallas-scratch2/claude/a", "git status", "git clone x /tmp/y",
                  "git -C /srv/opentallas-scratch2/claude/l sparse-checkout set tools"):
            self.assertFalse(B.blocked(c), c)
