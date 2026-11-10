"""KW-FIX-44 11-10 (COORD): which prd_run.sh containers run as the host user.

The count container (openroad reads the routed DB, may write the RCX SPEF into /work, no chown after it) runs as
--user $(id -u):$(id -g), so it leaves no root-owned file.  The pass / finish containers must stay root: they patch
ORFS scripts inside the image (orfs_hold_mm.py, kwrs_busfit.py patch util.tcl; root 0664 in openroad/orfs:asap7lock,
measured 11-10 on intel2: util_NOT_writable as uid 1000), and each is followed by a root chown of /work."""
import re
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent


def runs():
    """every '$DK run' command of prd_run.sh, continuation lines joined"""
    text = (HERE / "prd_run.sh").read_text().replace("\\\n", " ")
    return [ln.strip() for ln in text.splitlines() if re.match(r"\s*\$DK run\b", ln)]


class ContainerUser(unittest.TestCase):
    def test_count_runs_as_host_user(self):
        count = [r for r in runs() if "--name prd-count-" in r]
        self.assertEqual(len(count), 1, runs())
        self.assertIn('--user "$(id -u):$(id -g)"', count[0])

    def test_patching_containers_stay_root_and_are_chowned(self):
        rs = runs()
        patching = [r for r in rs if "$PATCH" in r]
        self.assertEqual(len(patching), 2, rs)          # pass loop + finish
        for r in patching:
            self.assertNotIn("--user", r)
        chown = [r for r in rs if re.search(r'"\$IMAGE" chown -R \$\(id -u\):\$\(id -g\) /work', r)]
        self.assertEqual(len(chown), 2, rs)            # one root chown after each patching container
        for r in chown:
            self.assertNotIn("--user", r)
        text = (HERE / "prd_run.sh").read_text()
        self.assertIn("/OpenROAD-flow-scripts/flow/scripts/util.tcl", text)   # the in-image patch that needs root
        self.assertIn("orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts", text)


def trap_block():
    t = (HERE / "prd_run.sh").read_text()
    a = t.index("prd_own_back() {")
    b = t.index("\n", t.index("trap 'prd_own_back; trap - EXIT; exit 130' INT"))
    assert t.index('DK=docker;') < a < t.index("D=$D0; P=1"), "trap set after DK, before the first pass"
    return t[a:b + 1]


class OwnBackTrap(unittest.TestCase):
    """the trap runs the root chown on the current pass dir (and FINAL) on EXIT / TERM / INT, only when needed"""

    def run_case(self, body, foreign):
        import os
        import subprocess
        import tempfile
        with tempfile.TemporaryDirectory() as t:
            t = Path(t)
            log, d, fin, stub = t / "dk.log", t / "pass1", t / "fin", t / "bin"
            d.mkdir(); fin.mkdir(); stub.mkdir()
            (t / "dk").write_text(f'#!/bin/bash\necho "$@" >> {log}\n')
            (t / "dk").chmod(0o755)
            if foreign:      # a non-root test cannot make a root-owned file: find reports one
                (stub / "find").write_text('#!/bin/bash\necho "$1/run/x"\n')
                (stub / "find").chmod(0o755)
            script = f'DK={t}/dk; IMAGE=img; D={d}; FINAL=\n' + trap_block() + body
            env = dict(os.environ, PATH=f"{stub}:{os.environ['PATH']}")
            p = subprocess.run(["bash", "-uo", "pipefail", "-c", script], env=env, capture_output=True, text=True,
                               timeout=30)
            calls = log.read_text().splitlines() if log.exists() else []
            return p.returncode, calls, str(d)

    def test_exit_chowns_current_pass_dir_and_keeps_rc(self):
        rc, calls, d = self.run_case("exit 3\n", foreign=True)
        self.assertEqual(rc, 3)
        self.assertEqual(len(calls), 1, calls)
        self.assertIn(f"run --rm -v {d}:/work img chown -R", calls[0])

    def test_term_chowns_once_and_exits_143(self):
        rc, calls, _ = self.run_case("kill -TERM $$\nsleep 5\nexit 0\n", foreign=True)
        self.assertEqual(rc, 143)
        self.assertEqual(len(calls), 1, calls)

    def test_int_exits_130(self):
        rc, calls, _ = self.run_case("kill -INT $$\nsleep 5\nexit 0\n", foreign=True)
        self.assertEqual(rc, 130)
        self.assertEqual(len(calls), 1, calls)

    def test_no_container_when_every_file_is_ours(self):
        rc, calls, _ = self.run_case("exit 0\n", foreign=False)
        self.assertEqual((rc, calls), (0, []))


if __name__ == "__main__":
    unittest.main()
