"""HIER-LINT + MACRO-GRID submit hook (owner 2026-10-11): mode from STATE/hier_lint.json (warn default) and
STATE/macro_grid_lint.json (refuse default); WARN logs + records submit_checks, REFUSE refuses the job."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import closure_loop as cl

sys.path.insert(0, str(Path(cl.__file__).resolve().parent.parent / "hier_contract"))
import hier_submit  # noqa: E402
import macro_grid_lint  # noqa: E402


def job():
    return {"name": "p", "status": "QUEUED", "events": [], "spec": {"name": "p", "block": "b", "source": {"commit": "c"}}}


class HierLintHook(unittest.TestCase):
    def run_hook(self, state, hier, grid):
        with tempfile.TemporaryDirectory() as t:
            for f, v in state.items():
                (Path(t) / f).write_text(json.dumps(v))
            j = job()
            with patch.object(cl, "STATE", Path(t)), patch.object(cl, "ledger"), patch.object(cl, "log"), \
                    patch.object(hier_submit, "check", return_value=hier) as h, \
                    patch.object(macro_grid_lint, "check", return_value=grid):
                cl.hier_lint_at_submit(j)
            return j, h

    def test_warn_mode_default(self):
        j, h = self.run_hook({}, {"verdict": "WARN", "message": "HIER_LINT WARN: x"}, {"verdict": "SKIP"})
        self.assertEqual(j["status"], "QUEUED")
        self.assertEqual(h.call_args[0][2], "warn")
        self.assertEqual(j["submit_checks"]["hier_lint"]["verdict"], "WARN")
        self.assertTrue(any("HIER_LINT WARN" in e for e in j["events"]))

    def test_refuse_mode(self):
        j, h = self.run_hook({"hier_lint.json": {"mode": "refuse"}}, {"verdict": "REFUSE", "message": "HIER_LINT: bloat"},
                             {"verdict": "PASS", "message": "ok"})
        self.assertEqual(h.call_args[0][2], "refuse")
        self.assertEqual(j["status"], "REFUSED")
        self.assertTrue(j["reason"].startswith("SUBMIT_LINT HIER_LINT"))

    def test_macro_grid_refuses_by_default(self):
        j, h = self.run_hook({}, {"verdict": "PASS"}, {"verdict": "REFUSE", "message": "MACRO_GRID: off"})
        self.assertEqual(j["status"], "REFUSED")
        self.assertIn("MACRO_GRID", j["reason"])
        h.assert_not_called()                       # a refused job is not linted further

    def test_macro_grid_warn_mode(self):
        j, _ = self.run_hook({"macro_grid_lint.json": {"mode": "warn"}}, {"verdict": "SKIP"},
                             {"verdict": "REFUSE", "message": "MACRO_GRID: off"})
        self.assertEqual(j["status"], "QUEUED")
        self.assertEqual(j["submit_checks"]["macro_grid"]["verdict"], "WARN")


if __name__ == "__main__":
    unittest.main()
