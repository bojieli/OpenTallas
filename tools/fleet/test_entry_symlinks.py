import os, tempfile, unittest
import entry_symlinks as E


def mk():
    d = tempfile.mkdtemp(); rt = os.path.join(d, "rt"); home = os.path.join(d, "home")
    os.makedirs(os.path.join(rt, "current/tools/fleet")); os.makedirs(os.path.join(rt, "current/tools/autopilot")); os.makedirs(os.path.join(home, ".local/bin"))
    return d, rt, home


class Links(unittest.TestCase):
    def test_check_and_apply(self):
        d, rt, home = mk()
        ent = {"~/.local/bin/ot-run": "tools/fleet/ot-run", "~/.local/bin/ot-job": "tools/fleet/ot-job", "~/.local/bin/ot-x": "tools/fleet/ot-x"}
        open(os.path.join(rt, "current/tools/fleet/ot-run"), "w").write("new")
        open(os.path.join(rt, "current/tools/fleet/ot-job"), "w").write("same")
        open(os.path.join(home, ".local/bin/ot-run"), "w").write("old")
        open(os.path.join(home, ".local/bin/ot-job"), "w").write("same")
        st = {os.path.basename(i): s for s, i, _ in E.check(ent, rt, home)}
        self.assertEqual(st, {"ot-run": "FILE-DIFF", "ot-job": "FILE-SAME", "ot-x": "MISSING"})
        done = E.apply(ent, rt, home, stamp="T")
        self.assertEqual(sorted((os.path.basename(i), r) for i, _, r in done), [("ot-job", "OK"), ("ot-run", "OK")])   # ot-x: no rt target, skipped
        p = os.path.join(home, ".local/bin/ot-run")
        self.assertTrue(os.path.islink(p)); self.assertEqual(open(p).read(), "new")
        self.assertEqual(open(p + ".bak-symlink-T").read(), "old")                 # previous file kept
        self.assertEqual({s for s, i, _ in E.check(ent, rt, home) if "ot-x" not in i}, {"LINK-OK"})
        self.assertEqual(E.apply(ent, rt, home), [])                               # idempotent

    def test_wrong_link_is_repointed_and_only_filters(self):
        d, rt, home = mk()
        ent = {"~/.local/bin/ot-run": "tools/fleet/ot-run", "~/.local/bin/ot-job": "tools/fleet/ot-job"}
        for n in ("ot-run", "ot-job"):
            open(os.path.join(rt, "current/tools/fleet", n), "w").write(n)
            os.symlink("/nonexistent", os.path.join(home, ".local/bin", n))
        done = E.apply(ent, rt, home, only=["ot-job"])
        self.assertEqual([os.path.basename(i) for i, _, _ in done], ["ot-job"])
        self.assertEqual(open(os.path.join(home, ".local/bin/ot-job")).read(), "ot-job")
        self.assertEqual(os.readlink(os.path.join(home, ".local/bin/ot-run")), "/nonexistent")
