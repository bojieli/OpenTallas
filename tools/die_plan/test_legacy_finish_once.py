"""Run the generated legacy runner tail: one final report per route/finish goal.

A real native_e finish repeated RC extraction and a 45-minute IR solve through
an extra unconditional do-finish. Exercise the real shell with a make fixture
whose finish goal already performs final reporting, as ORFS does.
"""
import ast
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "physical/die_plan/s81/cores/legacy/gen_core_kit_legacy.py"


def tail():
    tree = ast.parse(SOURCE.read_text())
    runner = next(ast.literal_eval(n.value) for n in tree.body
                  if isinstance(n, ast.Assign)
                  and any(isinstance(t, ast.Name) and t.id == "RUN_KIT" for t in n.targets))
    begin = runner.index("  if [ \\$rc = 0 ]; then \\$M $GOAL;")
    end = runner.index("  if [ \\$rc = 0 ] && [ $GOAL = place ];", begin)
    return runner[begin:end].replace("\\\n", "\n").replace("\\$", "$")


class LegacyFinishOnce(unittest.TestCase):
    def run_goal(self, goal, fail=""):
        with tempfile.TemporaryDirectory() as d:
            trace = Path(d)/"trace"
            script = r"""
make() {
  printf '%s\n' "$1" >> "$TRACE"
  [ "$1" != "$FAIL" ] || return 9
  case "$1" in finish|do-finish) printf 'final_report\n' >> "$TRACE";; esac
}
rc=0
M=make
"""
            p = subprocess.run(["bash", "-c", script+tail()+"exit $rc"],
                               env=dict(os.environ, GOAL=goal, TRACE=str(trace), FAIL=fail),
                               capture_output=True, text=True)
            return p.returncode, trace.read_text().splitlines(), p.stderr

    def test_finish_reports_once_and_still_exports_abstract(self):
        rc, calls, err = self.run_goal("finish")
        self.assertEqual((rc, calls), (0, ["finish", "final_report", "do-generate_abstract"]), err)

    def test_route_finalizes_once_and_exports_abstract(self):
        rc, calls, err = self.run_goal("route")
        self.assertEqual((rc, calls), (0, ["route", "do-finish", "final_report", "do-generate_abstract"]), err)

    def test_nonfinal_goals_do_not_report_or_export(self):
        for goal in ("place", "cts", "grt"):
            with self.subTest(goal=goal):
                rc, calls, err = self.run_goal(goal)
                self.assertEqual((rc, calls), (0, [goal]), err)

    def test_failed_route_or_finish_stops_finalization(self):
        for goal in ("route", "finish"):
            with self.subTest(goal=goal):
                rc, calls, err = self.run_goal(goal, goal)
                self.assertEqual((rc, calls), (9, [goal]), err)

    def test_failed_final_report_does_not_export_abstract(self):
        rc, calls, err = self.run_goal("route", "do-finish")
        self.assertEqual((rc, calls), (9, ["route", "do-finish"]), err)


if __name__ == "__main__":
    unittest.main()
