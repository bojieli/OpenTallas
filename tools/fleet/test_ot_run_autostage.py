"""AUTOSTAGE-1630: a --dir job whose lane root cannot spill (too big) stages --dir alone after the wait and spills; no --dir / young waiter / other reasons stay as before."""
import importlib.machinery
import importlib.util
import pathlib
import unittest
from unittest import mock

loader = importlib.machinery.SourceFileLoader("ot_run_autostage", str(pathlib.Path(__file__).with_name("ot-run")))
spec = importlib.util.spec_from_loader(loader.name, loader)
m = importlib.util.module_from_spec(spec)
loader.exec_module(m)

BIG = (None, "/srv/opentallas-scratch2/claude/wt total 1500 GB > OT_RUN_SPILL_MAX_GB 40", True)
OK = (("epyc7", ["/srv/x/k"], 1.0), "", False)


class AutoStage(unittest.TestCase):
    def setUp(self):
        m.STAGE.clear()
        self.addCleanup(m.STAGE.clear)

    def call(self, now, d="/srv/opentallas-scratch2/claude/wt/k/run", plan_fn=None):
        seen = []

        def fake(*a, **k):
            seen.append(list(m.STAGE))
            return plan_fn(len(seen)) if plan_fn else (BIG if not m.STAGE else OK)
        with mock.patch.object(m, "_spill_plan", fake):
            return m.spill_plan("epyc10", d, ["bash", "x"], 36, 8, False, 20, set(), lambda s: None, now=now), seen

    def test_young_waiter_keeps_waiting_and_says_why(self):
        (plan, why, perm), seen = self.call(m.T_START + 10)
        self.assertIsNone(plan)
        self.assertFalse(perm)
        self.assertIn("staged alone after", why)
        self.assertEqual(seen, [[]])

    def test_old_waiter_stages_dir_and_spills(self):
        (plan, why, perm), seen = self.call(m.T_START + 301)
        self.assertEqual(plan[0], "epyc7")
        self.assertEqual(seen, [[], ["/srv/opentallas-scratch2/claude/wt/k/run"]])
        self.assertEqual(m.STAGE, ["/srv/opentallas-scratch2/claude/wt/k/run"])

    def test_staging_refused_too_clears_stage_and_keeps_reason(self):
        (plan, why, perm), seen = self.call(m.T_START + 301, plan_fn=lambda n: BIG if n == 1 else (None, "command names /srv/a outside the --stage paths", True))
        self.assertIsNone(plan)
        self.assertTrue(perm)
        self.assertIn("also refused", why)
        self.assertEqual(m.STAGE, [])

    def test_no_dir_or_other_reason_or_explicit_stage_unchanged(self):
        (p, w, _), seen = self.call(m.T_START + 999, d="")
        self.assertEqual(seen, [[]])
        (p, w, _), seen = self.call(m.T_START + 999, plan_fn=lambda n: (None, "no spill host admits it now", False))
        self.assertEqual(seen, [[]])
        m.STAGE.append("/srv/a")
        (p, w, _), seen = self.call(m.T_START + 999)
        self.assertEqual(seen, [["/srv/a"]])


if __name__ == "__main__":
    unittest.main()
