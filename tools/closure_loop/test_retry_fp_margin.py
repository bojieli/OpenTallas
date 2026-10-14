"""flowfix 2026-10-13: `closure_loop.py retry` accepts a FLOORPLAN_MARGIN job: the floorplan / textbook lint is re-run
with the CURRENT tools on the dump the stopped stage left; PASS -> requeued (route slot released), FAIL -> untouched."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent))
import closure_loop as cl  # noqa: E402

# stand-ins for origin/main's lint tools: the verdict is whatever the dump says (the real CLIs: rc 3 + FLOORPLAN_MARGIN /
# TEXTBOOK_LINT lines on a refusal)
FAKE_FP = ("import json,sys\nd=json.load(open(sys.argv[2]))\nprint('fp_margin_lint: %s  util 41.0%% args %s' % "
           "('FAIL' if d.get('fp') else 'PASS', ' '.join(sys.argv[3:])))\n"
           "if d.get('fp'):\n    print('FLOORPLAN_MARGIN: util: utilisation 71.0% > 60%'); sys.exit(3)\n")
FAKE_TB = ("import json,sys\na=sys.argv\nd=json.load(open(a[a.index('--dump')+1]))\n"
           "json.load(open(a[a.index('--cfg')+1])); open(a[a.index('--netlist')+1]).read()\n"
           "if d.get('tb'):\n    print('TEXTBOOK_LINT: high_fanout: reset port rst_n: 21,109 loads > 8,000'); sys.exit(3)\n"
           "print('textbook_lint: PASS')\n")


def job(run, **kw):
    j = cl.JobState(name="x-c1-abcdef123", status="FLOORPLAN_MARGIN", attempt=1, host="localhost", run=str(run),
                    commit_full="c" * 40, stage_idx=1, stage_key="route", stage_tag="route.a1", events=[],
                    reason="util: utilisation 71.0% > 60%",
                    spec={"name": "x-c1-abcdef123", "block": "ot_x", "source": {"commit": "abcdef123456"},
                          "fp_lint": {"set": {"util_max": 0.66}}})
    j.update(kw)
    return j


class Relint(unittest.TestCase):
    """fp_margin_relint against a run directory on this machine (ssh -> bash -s)"""

    def _relint(self, dump, netlist=True, textbook=True):
        with tempfile.TemporaryDirectory() as run:
            base = Path(run) / "routes/L/work/orfs"
            if dump is not None:
                (base / "reports/asap7/d/base").mkdir(parents=True)
                (base / "results/asap7/d/base").mkdir(parents=True)
                (base / "reports/asap7/d/base/fp_margin_lint_dump.json").write_text(json.dumps(dump))
                if netlist:
                    (base / "results/asap7/d/base/1_2_yosys.v").write_text("module x; endmodule\n")
            j = job(run)
            if not textbook:
                j["spec"]["textbook_lint"] = False
            tools = {"tools/fp_margin_lint.py": FAKE_FP.encode(), "tools/textbook_lint.py": FAKE_TB.encode()}
            with patch.object(cl, "_ovl_resolve", side_effect=lambda rel: (tools[rel], "same")), \
                    patch.object(cl, "ssh", side_effect=lambda h, s, timeout=0: subprocess.run(
                        ["bash", "-s"], input=s, capture_output=True, text=True)), \
                    patch.object(cl, "STATE", Path(run) / "state"):
                return cl.fp_margin_relint(j)

    def test_pass_with_current_tools(self):
        v, text = self._relint({})
        self.assertEqual(v, "PASS", text)
        self.assertIn("--set util_max=0.66", text)               # the job's own thresholds reach the lint

    def test_floorplan_lint_still_fails(self):
        v, text = self._relint({"fp": 1})
        self.assertEqual(v, "FAIL")
        self.assertIn("FLOORPLAN_MARGIN: util: utilisation 71.0% > 60%", text)

    def test_textbook_lint_still_refuses(self):
        v, text = self._relint({"tb": 1})
        self.assertEqual(v, "FAIL")
        self.assertIn("TEXTBOOK_LINT: high_fanout", text)
        self.assertEqual(self._relint({"tb": 1}, textbook=False)[0], "PASS")      # spec textbook_lint: false

    def test_no_netlist_and_no_dump(self):
        v, text = self._relint({}, netlist=False)
        self.assertEqual(v, "PASS")
        self.assertIn("textbook lint not re-run", text)
        v, text = self._relint(None)
        self.assertEqual(v, "NODUMP")


class Retry(unittest.TestCase):
    def _retry(self, relint, force=False):
        j, saved, released = job("/r"), {}, []
        with patch.object(cl, "load_job", return_value=j), patch.object(cl, "save_job", side_effect=lambda x: saved.update(x)), \
                patch.object(cl, "ledger"), patch.object(cl, "job_lock", return_value=tempfile.TemporaryFile()), \
                patch.object(cl, "log", create=True), patch.object(cl, "fp_margin_relint", return_value=relint), \
                patch.object(cl, "release_route_key", side_effect=lambda x: released.append(x["name"])):
            cl.cmd_retry(SimpleNamespace(name=j["name"], at=None, keep_resume=False, force=force))
        return saved, released

    def test_pass_requeues_from_the_stopped_stage(self):
        s, released = self._retry(("PASS", "fp_margin_lint: PASS  util 41.0%"))
        self.assertEqual((s["status"], s["attempt"], s["stage_key"], s["stage_idx"]), ("SYNC", 2, "route", 1))
        self.assertEqual(released, ["x-c1-abcdef123"])            # it spent no route: the block@commit slot is free
        self.assertTrue(any("lint re-run with the current tools PASS" in e for e in s["events"]))

    def test_fail_leaves_the_job(self):
        with self.assertRaises(SystemExit) as ex:
            self._retry(("FAIL", "FLOORPLAN_MARGIN: util: utilisation 71.0% > 60%"))
        self.assertIn("still FLOORPLAN_MARGIN with the current lint", str(ex.exception))
        self.assertIn("utilisation 71.0%", str(ex.exception))

    def test_no_dump_needs_force(self):
        with self.assertRaises(SystemExit) as ex:
            self._retry(("NODUMP", "no fp_margin_lint_dump.json under h:/r"))
        self.assertIn("retry --force", str(ex.exception))
        s, released = self._retry(("NODUMP", "no fp_margin_lint_dump.json under h:/r"), force=True)
        self.assertEqual(s["status"], "SYNC")
        self.assertEqual(released, ["x-c1-abcdef123"])
        with self.assertRaises(SystemExit):                       # a lint tool error is never a pass, forced or not
            self._retry(("ERROR", "lint tool error"), force=True)

    def test_other_states_unchanged(self):
        j = job("/r", status="CLOSED")
        with patch.object(cl, "load_job", return_value=j), patch.object(cl, "job_lock", return_value=tempfile.TemporaryFile()):
            with self.assertRaises(SystemExit) as ex:
                cl.cmd_retry(SimpleNamespace(name=j["name"], at=None, keep_resume=False, force=False))
        self.assertIn("FLOORPLAN_MARGIN", str(ex.exception))


if __name__ == "__main__":
    unittest.main()
