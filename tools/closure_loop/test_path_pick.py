"""PATHPICK (ROOT-2130 2026-10-18): fleet-path picks in stage scripts are pipefail-safe, and a stage whose required
fleet path is absent fails loudly (OT_FLOW_MISSING, rc 97) instead of routing without its TT overlay / CTS hooks."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import closure_loop as cl


def run_script(body):
    return subprocess.run(["bash", "-c", body], capture_output=True, text=True)


class PathPickTest(unittest.TestCase):
    def setUp(self):
        self.td = Path(tempfile.mkdtemp())
        self.a = self.td / "a"          # only the FIRST candidate exists on this "host" (ot-epyc5 shape)
        self.a.mkdir()
        self.b = self.td / "missing"

    def tearDown(self):
        shutil.rmtree(self.td)

    def script(self, cmd):
        cmd, picks = cl.path_picks_safe(cl.tt_overlay_fallback(cmd))
        return f"set -o pipefail\n{cl.OT_PICK_FN}{cl.path_pick_precheck(picks)}{cmd}\n", picks

    def test_old_pattern_skips_chain_under_pipefail(self):
        # the bug itself: the && chain after the assignment does not run when one candidate is missing
        r = run_script(f"set -o pipefail\nT=$(ls -d {self.a} {self.b} 2>/dev/null | head -1) && echo CHAIN; echo ROUTE")
        self.assertNotIn("CHAIN", r.stdout)
        self.assertIn("ROUTE", r.stdout)

    def test_assignment_chain_runs_with_one_candidate(self):
        for first, second in ((self.a, self.b), (self.b, self.a)):
            body, picks = self.script(f"T=$(ls -d {first} {second} 2>/dev/null | head -1) && echo CHAIN=$T; echo ROUTE")
            self.assertEqual(picks, [(str(first), str(second))])
            r = run_script(body)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn(f"CHAIN={self.a}\n", r.stdout)

    def test_grep_echo_fallback_is_one_line(self):
        body, _ = self.script(f"echo \"[$(ls -d {self.a} {self.b} 2>/dev/null | head -1 | grep . || echo rel)]\"")
        r = run_script(body)
        self.assertEqual(r.stdout.strip(), f"[{self.a}]")

    def test_missing_path_fails_loudly(self):
        body, _ = self.script(f"T=$(ls -d {self.b} {self.td}/nope 2>/dev/null | head -1) && echo CHAIN; echo ROUTE")
        r = run_script(body)
        self.assertEqual(r.returncode, cl.OT_FLOW_MISSING_RC)
        self.assertIn("OT_FLOW_MISSING", r.stdout)
        self.assertNotIn("ROUTE", r.stdout)
        self.assertRegex(r.stdout, cl.RESOURCE_RE)   # crash() treats it as a flow (host) failure, not a design one

    def test_tt_overlay_pick_is_required(self):
        out = cl.tt_overlay_fallback("cd {SRC} && python3 tools/closure_loop/tt_overlay.py {SRC} && route")
        self.assertNotIn("echo tools/closure_loop/tt_overlay.py", out)
        cmd, picks = cl.path_picks_safe(out)
        self.assertEqual(picks, [cl.TT_OVERLAY_FLEET])
        self.assertIn(f"$(ot_pick {' '.join(cl.TT_OVERLAY_FLEET)})", cmd)

    def test_globs_and_placeholders_untouched(self):
        for c in ("B=$(ls -d {RUN}/route/results/asap7/*/base | tail -1)",
                  "VB=$(ls -d /x/orfs/results/asap7/*/base | head -1)"):
            self.assertEqual(cl.path_picks_safe(c), (c, []))

    def test_overlay_skipped_verdict_is_flow_failure(self):
        j = dict(host="h", run="/r", spec=dict(stages=dict(route=dict(
            cmd="TTB=$(ls -d /a /b 2>/dev/null | head -1) && export OT_TTB_CORNER_MARK={CL}/ttb_corner.txt && x"))))
        with patch.object(cl, "ssh", return_value=Mock(stdout="NOMARK\n", returncode=0)):
            self.assertTrue(cl.overlay_skipped(j))
        with patch.object(cl, "ssh", return_value=Mock(stdout="MARK\n", returncode=0)):
            self.assertFalse(cl.overlay_skipped(j))
        j["spec"]["stages"]["route"]["cmd"] = "route only"
        self.assertFalse(cl.overlay_skipped(j))

    def test_overlay_skipped_reads_newest_route_log(self):
        run = self.td / "run"
        (run / "cl").mkdir(parents=True)
        j = dict(host="h", run=str(run), spec=dict(stages=dict(route=dict(
            cmd="export OT_TTB_CORNER_MARK={CL}/ttb_corner.txt && python3 tools/closure_loop/tt_overlay.py {SRC}"))))
        local = lambda host, cmd, **kw: subprocess.run(["bash", "-c", cmd], capture_output=True, text=True)  # noqa: E731
        with patch.object(cl, "ssh", side_effect=local):
            self.assertTrue(cl.overlay_skipped(j))                       # no mark
            (run / "cl/ttb_corner.txt").write_text("TC 1 smh_config\n")
            (run / "cl/route.a1.log").write_text("route ok\n")
            self.assertFalse(cl.overlay_skipped(j))                      # mark, clean log
            (run / "cl/route.a2.log").write_text("python3: can't open file '/x/tt_overlay.py\\ntools/x': [Errno 2]\n")
            self.assertTrue(cl.overlay_skipped(j))                       # resumed attempt's overlay failed


if __name__ == "__main__":
    unittest.main()
