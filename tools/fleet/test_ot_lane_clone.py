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
        self.assertEqual(p[0][:4], ["git", "clone", "--bare", "--filter=blob:none"]); self.assertIn("fetch", p[1]); self.assertIn("--no-checkout", p[2])
        os.mkdir(w + "/w.git")
        p = M.plan("/srv/opentallas-scratch2/claude/l1", "main", ["tools"], warm=w + "/w.git", origin="o")
        self.assertIn("fetch", p[0]); self.assertIn("+refs/heads/*:refs/remotes/origin/*", p[0])           # never into refs/heads
        self.assertEqual(p[1][-1], "refs/remotes/origin/main"); self.assertEqual(p[3], ["git", "-C", "/srv/opentallas-scratch2/claude/l1", "sparse-checkout", "set", "tools"])

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


    def test_a_branch_checked_out_in_an_old_worktree_cannot_block_the_fetch(self):
        d = pathlib.Path(tempfile.mkdtemp()); g = ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "init.defaultBranch=main", "-c", "protocol.file.allow=always"]
        o = d / "o.git"; subprocess.run(g + ["init", "-q", "--bare", str(o)], check=True)
        w = d / "w"; subprocess.run(g + ["clone", "-q", str(o), str(w)], check=True, capture_output=True)
        (w / "tools").mkdir(); (w / "tools" / "f").write_text("1")
        subprocess.run(g + ["add", "-A"], cwd=w, check=True); subprocess.run(g + ["commit", "-qm", "1"], cwd=w, check=True); subprocess.run(g + ["push", "-q", "origin", "main"], cwd=w, check=True)
        warm = str(d / "warm.git")
        run = lambda steps: [subprocess.run(s[:1] + ["-c", "protocol.file.allow=always"] + s[1:], check=True, capture_output=True) for s in steps]
        run(M.plan(str(d / "lane1"), "main", ["tools"], warm=warm, origin=str(o)))
        # an OLD worktree holds a branch of the warm repo checked out (what the retired lane did), and origin moves
        subprocess.run(g + ["-C", warm, "worktree", "add", "-q", str(d / "oldwt"), "main"], check=True, capture_output=True)       # main of the warm repo is checked out there
        old = subprocess.run(g + ["-C", warm, "fetch", "-q", "origin", "+refs/heads/*:refs/heads/*"], capture_output=True, text=True)
        self.assertNotEqual(old.returncode, 0)                  # the OLD refspec is refused while main is checked out in oldwt: the epyc2 failure, reproduced
        (w / "tools" / "f").write_text("2"); subprocess.run(g + ["commit", "-qam", "2"], cwd=w, check=True); subprocess.run(g + ["push", "-q", "origin", "main"], cwd=w, check=True)
        run(M.plan(str(d / "lane2"), "main", ["tools"], warm=warm, origin=str(o)))                    # the new plan fetches and clones anyway
        self.assertEqual((d / "lane2" / "tools" / "f").read_text(), "2")


class WarmGc(unittest.TestCase):
    def test_warm_repo_never_auto_gcs_and_merges_small_packs_geometrically(self):
        w = tempfile.mkdtemp(); pk = os.path.join(w, "objects", "pack"); os.makedirs(pk)
        s = M.warm_gc_steps(w, limit=3)
        self.assertIn(["git", "-C", w, "config", "gc.auto", "0"], s); self.assertIn(["git", "-C", w, "config", "maintenance.auto", "false"], s)
        self.assertFalse(any("repack" in x for x in s))
        for i in range(4): open(os.path.join(pk, "pack-%d.pack" % i), "w").close()
        s = M.warm_gc_steps(w, limit=3)
        self.assertEqual(s[-1], ["git", "-C", w, "repack", "-d", "-l", "--geometric=2"])
        self.assertFalse(any("gc" == x[3] if len(x) > 3 else False for x in s))       # never a full gc
        p = M.plan("/srv/opentallas-scratch2/claude/l1", "main", ["tools"], warm=w, origin="o")
        self.assertIn(["git", "-C", w, "config", "gc.auto", "0"], p)
