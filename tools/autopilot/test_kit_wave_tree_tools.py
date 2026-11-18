"""TOOLSMOKE-1115 (COORD r152, FABLE-FLOW-1350 class 5): the wave's first commands vs the tools of a die src tree.
Merge gate: a change to the tree-tool command lines of kit_wave.py must keep passing against the oldest live tree fixtures
(live_tree_fixtures.tsv).  An expect=pass fixture that starts failing = the wave outran that tree: red.  An expect=skew fixture
(a live base sha whose own tools lack a flag; the live tree carries a hand overlay) that starts passing = remove the line."""
import json, os, re, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import adopt_guard as AG
import kit_wave as KW
import src_manifest as SM

REPO = HERE.parents[1]
SRC = (HERE / "kit_wave.py").read_text()


def smoke(tree, flags=None):
    r = subprocess.run([sys.executable, "-I", "-c", KW.TREE_TOOL_SMOKE_PY, str(tree), repr(flags or KW.WAVE_TREE_TOOL_FLAGS)],
                       capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def fixtures():
    out = []
    for ln in (HERE / "live_tree_fixtures.tsv").read_text().splitlines():
        if ln.strip() and not ln.startswith("#"):
            f = ln.split("\t")
            out.append((f[0], f[1], f[2]))
    return out


class FlagsMatchCommands(unittest.TestCase):
    def test_every_flag_is_in_the_wave_command_line(self):
        """WAVE_TREE_TOOL_FLAGS is the list the adoption smoke checks: each flag must really be on the wave's command line"""
        cmdline = {("bind.py", "kit-rtl"): re.search(r"tools/die_plan/bind\.py kit-rtl .*?kit_rtl_post_cmd", SRC, re.S),
                   ("gen.py", "phys"): re.search(r"tools/die_plan/gen\.py phys \{q\(plan\)\}.*?\{ov_arg\}", SRC, re.S),
                   ("bind.py", "bind"): re.search(r"python3 tools/die_plan/bind\.py bind \{plan\}.*?--strict", SRC, re.S)}
        for script, sub, flags in KW.WAVE_TREE_TOOL_FLAGS:
            m = cmdline[(script, sub)]
            self.assertIsNotNone(m, f"{script} {sub}: command line not found in kit_wave.py")
            for f in flags:
                if f == "--kit-rtl":                                   # carried by the kit_rtl_arg variable
                    self.assertIn('--kit-rtl {q(T', SRC)
                    continue
                self.assertIn(f, m.group(0), f"{script} {sub}: the wave no longer passes {f} (or the list is stale)")


class MainTools(unittest.TestCase):
    def test_main_tools_accept_the_wave_flags(self):
        rc, txt = smoke(REPO)
        self.assertEqual(rc, 0, txt)

    def test_missing_flag_is_named(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t, "tools", "die_plan")
            d.mkdir(parents=True)
            (d / "bind.py").write_text("import sys\nprint('usage: bind.py kit-rtl --out --asbuilt --type --kit')\n")
            (d / "gen.py").write_text("print('--out --types --rtl-root --kit-rtl')\n")
            (d / "kit_topology.py").write_text("X=1\n")
            rc, txt = smoke(t)
            self.assertEqual(rc, 1)
            self.assertIn("bind.py kit-rtl lacks --src-tree", txt)

    def test_missing_tool_and_broken_help(self):
        with tempfile.TemporaryDirectory() as t:
            rc, txt = smoke(t)
            self.assertEqual(rc, 1)
            self.assertIn("missing", txt)


class OldestLiveTrees(unittest.TestCase):
    def test_fixtures(self):
        for sha, expect, note in fixtures():
            with tempfile.TemporaryDirectory() as t:
                try:
                    SM.git_archive(str(REPO), sha, ["tools/die_plan"], t, lazy=True)
                except SystemExit as e:
                    self.skipTest(f"fixture {sha} not in this clone: {e}")
                rc, txt = smoke(t)
                if expect == "pass":
                    self.assertEqual(rc, 0, f"fixture {sha} ({note}): the wave's command lines outran this live tree:\n{txt}")
                else:
                    self.assertNotEqual(rc, 0, f"fixture {sha} ({note}) now passes: change its expect to pass or remove it")


class AdoptGuardSmoke(unittest.TestCase):
    cfg = {"dies": {"d": {"src": "/srv/s/claude/x/src"}}}

    def test_failure_refuses_and_names_host_and_flag(self):
        lines = []

        def run(argv, timeout=900):
            if argv[-2] == "epyc9":
                return 1, "TOOL_SMOKE FAIL bind.py kit-rtl lacks --src-tree (the wave passes it)\nTOOL_SMOKE FAIL /srv/s/claude/x/src\n"
            return 0, "TOOL_SMOKE OK /srv/s/claude/x/src\n"
        self.assertFalse(AG.tool_smoke(self.cfg, "d", ["epyc8", "epyc9"], run, lines.append))
        self.assertTrue(any("epyc9" in l and "lacks --src-tree" in l for l in lines), lines)
        self.assertTrue(any("FAIL closed" in l for l in lines))

    def test_all_hosts_ok_and_command_carries_exact_flags(self):
        seen = []

        def run(argv, timeout=900):
            seen.append(argv[-1])
            return 0, "TOOL_SMOKE OK\n"
        self.assertTrue(AG.tool_smoke(self.cfg, "d", ["epyc8", "epyc9"], run, lambda l: None))
        self.assertEqual(len(seen), 2)
        self.assertIn("--src-tree", seen[0])
        self.assertIn("/srv/s/claude/x/src", seen[0])

    def test_guard_runs_smoke_and_stops(self):
        calls = []
        old = AG.tool_smoke, AG.manifest_check
        AG.tool_smoke = lambda *a, **k: calls.append("smoke") or False
        AG.manifest_check = lambda *a, **k: True
        try:
            cfg = {"dies": {"d": {"src": "/srv/s/claude/x/src", "gen_hosts": ["epyc8"]}}}
            self.assertFalse(AG.guard(cfg, "d", True, run=lambda *a, **k: (0, ""), log=lambda l: None))
        finally:
            AG.tool_smoke, AG.manifest_check = old
        self.assertEqual(calls, ["smoke"])

    def test_opt_out_is_explicit(self):
        cfg = {"dies": {"d": {"src": "/x", "tool_smoke": False}}}
        self.assertTrue(AG.tool_smoke(cfg, "d", ["epyc8"], lambda *a, **k: (1, ""), lambda l: None))


if __name__ == "__main__":
    unittest.main()
