"""OOMADJ_999_1022: no fleet helper or closure-loop probe sets oom_score_adj -1000 (memcg OOM livelock at the cap).
Die jobs get -999, every other ot-heavy job / container 0 (or its own non-negative value)."""
import importlib.machinery, importlib.util, os, re, subprocess, sys, tempfile, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent
EVID = HERE / "evidence"


def load(name, path):
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    m = importlib.util.module_from_spec(spec)
    loader.exec_module(m)
    return m


INS = load("install_oomadj_999", HERE / "install_oomadj_999.py")
PD = load("ot_protect_die", HERE / "ot-protect-die")


def shim_run(shim_text, args, prio=None, mem="12"):
    d = Path(tempfile.mkdtemp())
    fake = d / "fake"; fake.write_text('#!/bin/bash\nprintf "%s\\n" "$@"\n'); fake.chmod(0o755)
    sh = d / "docker"; sh.write_text(shim_text.replace("REAL=/usr/bin/docker", f"REAL={fake}")); sh.chmod(0o755)
    env = dict(os.environ); env.pop("OT_HEAVY_PRIO", None); env["OT_HEAVY_MEM_GB"] = mem
    if prio: env["OT_HEAVY_PRIO"] = prio
    return subprocess.run([str(sh), *args], capture_output=True, text=True, env=env).stdout.split("\n")[:-1]


def adj_flags(out):
    return [a for a in out if a.startswith("--oom-score-adj=")] + \
           [out[i + 1] for i, a in enumerate(out) if a == "--oom-score-adj"]


class DockerShim(unittest.TestCase):
    LAYOUTS = {"repo": (HERE / "ot-heavy-docker").read_text()}

    @classmethod
    def setUpClass(cls):
        for name, f in (("ep5_die_watchdog", EVID / "oomadj_999_1022/docker.ep5.before"),
                        ("pre_die_watchdog", EVID / "die_watchdog_1021/docker.before")):
            if f.exists():
                cls.LAYOUTS[name] = INS.patch_docker(f.read_text())

    def test_die_container_is_minus_999(self):
        for name, s in self.LAYOUTS.items():
            out = shim_run(s, ["run", "--oom-score-adj", "-1000", "img"], prio="die")
            self.assertEqual(adj_flags(out), ["--oom-score-adj=-999"], name)
            self.assertIn("--label=opentallas.priority=die", out, name)

    def test_non_die_container_is_zero_or_own_non_negative(self):
        for name, s in self.LAYOUTS.items():
            self.assertEqual(adj_flags(shim_run(s, ["run", "img"])), ["--oom-score-adj=0"], name)
            self.assertEqual(adj_flags(shim_run(s, ["run", "--oom-score-adj=-1000", "img"])), ["--oom-score-adj=0"], name)
            self.assertEqual(adj_flags(shim_run(s, ["run", "--oom-score-adj", "-999", "img"])), ["0"], name)
            self.assertEqual(adj_flags(shim_run(s, ["run", "--oom-score-adj", "500", "img"])), ["500"], name)

    def test_patch_idempotent(self):
        for s in self.LAYOUTS.values():
            self.assertEqual(INS.patch_docker(s), s)


class OtHeavy(unittest.TestCase):
    def block_adj(self, start, prio):
        """the ot-heavy OOMADJ block, run in a shell whose oom_score_adj is `start`"""
        script = f"echo {start} > /proc/self/oom_score_adj || exit 9\n" + INS.HEAVY_BLOCK + "cat /proc/self/oom_score_adj\n"
        env = dict(os.environ); env.pop("OT_HEAVY_PRIO", None)
        if prio: env["OT_HEAVY_PRIO"] = prio
        r = subprocess.run(["bash", "-c", script], capture_output=True, text=True, env=env)
        if r.returncode == 9:
            self.skipTest("cannot raise own oom_score_adj here")
        return r.stdout.strip()

    def test_non_die_scope_starts_at_zero(self):
        self.assertEqual(self.block_adj(300, None), "0")

    def test_die_scope_untouched(self):
        self.assertEqual(self.block_adj(300, "die"), "300")

    def test_repo_and_deployed_layouts_patched(self):
        self.assertIn(INS.HEAVY_BLOCK + INS.HEAVY_ANCHOR, (HERE / "ot-heavy").read_text())
        f = EVID / "oomadj_999_1022/ot-heavy.ep5.before"
        p = INS.patch_heavy(f.read_text())
        self.assertIn(INS.HEAVY_BLOCK + INS.HEAVY_ANCHOR, p)
        self.assertTrue(p.index("ot-protect-die --pid") < p.index(INS.HEAVY_BLOCK))
        self.assertEqual(INS.patch_heavy(p), p)
        self.assertTrue(INS.bash_ok(p))


class ProtectDie(unittest.TestCase):
    def test_target_is_minus_999(self):
        self.assertEqual(PD.TARGET, "-999")
        src = (HERE / "ot-protect-die").read_text()
        self.assertNotRegex(src, r"write_text\(\s*'-1000")

    def test_legacy_minus1000_left_alone(self):
        self.assertFalse(PD.wants_write("-999", False))
        self.assertTrue(PD.wants_write("0", False))
        self.assertTrue(PD.wants_write("-1000", False))   # -1000 inherited after the cutoff -> -999
        self.assertFalse(PD.wants_write("-1000", True))   # legacy (possibly livelocked): report only

    def test_legacy_set(self):
        bt, hz = PD.boot_time(), os.sysconf("SC_CLK_TCK")
        tick = lambda epoch: str(int((epoch - bt) * hz))
        rows = {1: dict(ppid=0, adj="-1000", start=tick(bt + 100)),     # before cutoff
                2: dict(ppid=1, adj="-1000", start=tick(bt + 500)),     # later child of a legacy tree
                3: dict(ppid=0, adj="-1000", start=tick(bt + 500)),     # later, own tree
                4: dict(ppid=1, adj="0", start=tick(bt + 500))}
        self.assertEqual(PD.legacy_set(rows, bt + 200), {1, 2})
        self.assertEqual(PD.legacy_set(rows, None), {1, 2, 3})        # no cutoff file: every -1000 is legacy


class ClosureLoopProbe(unittest.TestCase):
    def test_die_probe_writes_minus_999(self):
        sys.path.insert(0, str(TOOLS / "closure_loop"))
        src = (TOOLS / "closure_loop" / "closure_loop.py").read_text()
        m = re.search(r"\nDIE_OOM_SCORE_ADJ = (-?\d+)\n", src)
        self.assertEqual(m and m.group(1), "-999")
        block = src[src.index("\nDIE_OOM_SCORE_ADJ"):src.index("\nEMERGENCY_FREE_GB")]
        ns = {"DIE_CONTAINER_RE": "x", "DIE_MOUNT_RE": "y"}
        exec(block.split("# HOST-EMERGENCY")[0], ns)
        probe = ns["DIE_OOM_PROBE"]
        self.assertIn("echo -999 | sudo -n tee /proc/$p/oom_score_adj", probe)
        self.assertNotIn("echo -1000", probe)
        self.assertEqual(subprocess.run(["bash", "-n", "-c", probe]).returncode, 0)


# writes of -1000 as an OOM adjustment: echo/tee/write_text, docker flag, systemd property, choom
SET_MINUS_1000 = re.compile(
    r"(oom[-_]score[-_]adj[= ]+[\"']?-1000|OOMScoreAdjust\s*=\s*-1000|choom\s+-n\s*-1000"
    r"|echo\s+-1000\b[^\n]*oom_score_adj|write_text\(\s*['\"]-1000)")


class GrepGuard(unittest.TestCase):
    def test_no_minus_1000_oom_adj_in_tools(self):
        # the installer names the old -1000 text it replaces
        skip = {HERE / "evidence", Path(__file__).resolve(), HERE / "install_oomadj_999.py"}
        bad = []
        for p in TOOLS.rglob("*"):
            if not p.is_file() or p.suffix in (".json", ".jsonl", ".log", ".c", ".md", ".before") or \
                    any(s == p or s in p.parents for s in skip) or p.stat().st_size > 4_000_000:
                continue
            try:
                t = p.read_text()
            except (UnicodeError, OSError):
                continue
            for m in SET_MINUS_1000.finditer(t):
                line = t[:m.start()].count("\n") + 1
                bad.append(f"{p.relative_to(TOOLS)}:{line}: {m.group(0)}")
        self.assertEqual(bad, [], "oom_score_adj -1000 makes a job un-killable by its own memcg OOM (livelock at cap); use -999")

    def test_guard_regex_catches_known_forms(self):
        for s in ("echo -1000 | sudo -n tee /proc/$p/oom_score_adj", "--oom-score-adj=-1000", "--oom-score-adj -1000",
                  "OOMScoreAdjust=-1000", "choom -n -1000 -p 1", "Path(x).write_text('-1000\\n')"):
            self.assertRegex(s, SET_MINUS_1000)
        self.assertNotRegex("[ \"$a\" = -1000 ] && continue", SET_MINUS_1000)


if __name__ == "__main__":
    unittest.main()
