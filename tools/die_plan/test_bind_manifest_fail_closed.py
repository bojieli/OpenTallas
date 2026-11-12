#!/usr/bin/env python3
"""Fail-closed source-identity gate for as-built bind manifests (manifest_src_gate.py + bind.py wiring)."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bind as BD  # noqa: E402
import manifest_src_gate as G  # noqa: E402


def git(repo, *a):
    return subprocess.run(["git", "-C", str(repo), *a], check=True, capture_output=True, text=True).stdout.strip()


class Case(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.root = Path(self.td.name)
        self.repo = self.root / "tree"
        (self.repo / "rtl").mkdir(parents=True)
        (self.repo / "rtl/kit.sv").write_text("module kit; // fixed\nendmodule\n")
        (self.repo / "rtl/other.sv").write_text("module other; endmodule\n")
        git(self.repo, "init", "-q")
        git(self.repo, "config", "user.email", "t@t")
        git(self.repo, "config", "user.name", "t")
        git(self.repo, "add", "rtl")
        git(self.repo, "commit", "-q", "-m", "main")
        self.sha = git(self.repo, "rev-parse", "HEAD")
        # an old frozen tree holding an OLD kit with the same basename
        self.old = self.root / "frozen"
        (self.old / "rtl").mkdir(parents=True)
        (self.old / "rtl/kit.sv").write_text("module kit; // OLD skew kit\nendmodule\n")
        (self.old / "rtl/other.sv").write_text("module other; endmodule\n")

    def tearDown(self):
        self.td.cleanup()

    def ab(self, **kw):
        d = dict(files=["rtl/other.sv"], prefer=["rtl/kit.sv"], src_sha=self.sha)
        d.update(kw)
        return d

    def run_check(self, ab, base=None):
        return G.check(ab, base or self.repo, self.repo, ab.get("src_sha"))

    def test_matching_passes(self):
        r = self.run_check(self.ab())
        self.assertEqual(r["errors"], [])
        self.assertEqual(r["checked"], 2)
        self.assertEqual(r["overrides"], [])

    def test_absolute_old_kit_fails(self):
        r = self.run_check(self.ab(prefer=[str(self.old / "rtl/kit.sv")]))
        self.assertEqual(len(r["errors"]), 1)
        self.assertIn("outside the bind source tree", r["errors"][0])
        self.assertIn("rtl/kit.sv main", r["errors"][0])

    def test_relative_path_against_old_base_fails(self):
        r = self.run_check(self.ab(), base=self.old)
        self.assertTrue(any("base:" in e for e in r["errors"]))
        self.assertTrue(any("rtl/kit.sv sha256" in e and "differs" in e for e in r["errors"]))
        self.assertFalse(any("rtl/other.sv" in e for e in r["errors"]))

    def test_declared_override_passes_and_is_reported(self):
        old = str(self.old / "rtl/kit.sv")
        r = self.run_check(self.ab(prefer=[old], declared_overrides=[dict(path=old, reason="bring-up kit")]))
        self.assertEqual(r["errors"], [])
        self.assertEqual([o["reason"] for o in r["overrides"]], ["bring-up kit"])
        # a declared sha-differing repo-relative file
        (self.repo / "rtl/kit.sv").write_text("module kit; // edited, uncommitted\nendmodule\n")
        r = self.run_check(self.ab())
        self.assertEqual(len(r["errors"]), 1)
        r = self.run_check(self.ab(declared_overrides=[dict(path="rtl/kit.sv", reason="wip")]))
        self.assertEqual(r["errors"], [])
        o = r["overrides"][0]
        self.assertNotEqual(o["actual"], o["main"])

    def test_override_needs_reason(self):
        old = str(self.old / "rtl/kit.sv")
        r = self.run_check(self.ab(prefer=[old], declared_overrides=[dict(path=old, reason=" ")]))
        self.assertTrue(any("non-empty `reason`" in e for e in r["errors"]))
        self.assertTrue(any("outside" in e for e in r["errors"]))

    def test_base_other_tree_fails_unless_declared(self):
        r = self.run_check(self.ab(files=[], prefer=[]), base=self.old)
        self.assertTrue(any(e.startswith("base:") for e in r["errors"]))
        r = self.run_check(self.ab(files=[], prefer=[], declared_overrides=[dict(path="base", reason="diag")]),
                           base=self.old)
        self.assertEqual(r["errors"], [])
        self.assertEqual(r["overrides"][0]["path"], "base")

    def test_tree_head_not_src_sha_fails(self):
        (self.repo / "rtl/new.sv").write_text("module n; endmodule\n")
        git(self.repo, "add", "rtl/new.sv")
        git(self.repo, "commit", "-q", "-m", "next")
        r = self.run_check(self.ab())
        self.assertTrue(any(e.startswith("tree:") for e in r["errors"]))

    def test_unknown_sha_fails(self):
        r = G.check(self.ab(), self.repo, self.repo, "deadbeef" * 5)
        self.assertTrue(any("not a commit" in e for e in r["errors"]))

    def test_read_back_sources(self):
        out = self.root / "out"
        out.mkdir()
        (out / "stub.sv").write_text("generated\n")
        srcs = dict(full=[str(self.repo / "rtl/other.sv"), str(self.old / "rtl/kit.sv")], lib=[str(out / "stub.sv")])
        r = G.check_read(self.ab(), self.repo, self.repo, self.sha, srcs, out)
        self.assertEqual(len(r["errors"]), 1)
        self.assertIn("kit.sv", r["errors"][0])

    def test_cli_exit_codes(self):
        m = self.root / "m.json"
        m.write_text(json.dumps(self.ab()))
        self.assertEqual(G.main([str(m), "--repo", str(self.repo)]), 0)
        m.write_text(json.dumps(self.ab(prefer=[str(self.old / "rtl/kit.sv")])))
        self.assertEqual(G.main([str(m), "--repo", str(self.repo)]), 1)

    # ---- bind.py wiring
    def plan(self, ab):
        p = self.root / "plan.json"
        p.write_text(json.dumps(dict(asbuilt=ab, die=dict(name="x"))))
        return p

    def test_no_key_manifest_unchanged(self):
        ab = dict(files=["rtl/other.sv"], prefer=[str(self.old / "rtl/kit.sv")])  # old kit, no src_sha: untouched
        BD._AB_OVERRIDE.clear()
        BD._AB_OVERRIDE.update(path=None, allow_external_paths=False, src_sha=None)
        raw = BD.load_plan(self.plan(ab))        # outside the repo: path-shape gate not applied, no new gate
        self.assertEqual(raw["asbuilt"], ab)
        self.assertIsNone(BD._AB_OVERRIDE.get("src_gate"))
        self.assertIsNone(BD._gate_sources(raw, self.plan(ab)))
        self.assertEqual(BD._gate_summary(), {})

    def test_bind_load_plan_fails_closed(self):
        ab = self.ab(prefer=[str(self.old / "rtl/kit.sv")])
        BD._AB_OVERRIDE.clear()
        BD._AB_OVERRIDE.update(path=None, allow_external_paths=False, src_sha=None)
        p = self.plan(ab)
        raw = BD.load_plan(p)
        with unittest.mock.patch.object(BD.E, "REPO", self.repo):
            with self.assertRaises(BD.BindError) as cm:
                BD._gate_sources(raw, p)
        self.assertIn("outside the bind source tree", str(cm.exception))

    def test_bind_cli_flag_enables_gate(self):
        ab = dict(files=["rtl/other.sv"], prefer=["rtl/kit.sv"])
        BD._AB_OVERRIDE.clear()
        BD._AB_OVERRIDE.update(path=None, allow_external_paths=False, src_sha=self.sha)
        p = self.plan(ab)
        raw = BD.load_plan(p)
        raw["asbuilt"]["base"] = str(self.repo)
        with unittest.mock.patch.object(BD.E, "REPO", self.repo):
            BD._gate_sources(raw, p)
        s = BD._gate_summary()
        self.assertEqual(s["src_sha"], self.sha)
        self.assertEqual(s["overrides"], [])


import unittest.mock  # noqa: E402

if __name__ == "__main__":
    unittest.main()
