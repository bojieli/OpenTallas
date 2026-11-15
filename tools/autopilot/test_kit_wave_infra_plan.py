"""INFRA relaunch reads the plan before launching: a planned-core type must get provisional views (KW-FIX-8 11-04)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave as KW  # noqa: E402


class AP:
    def __init__(self, out):
        self.out, self.calls = out, 0

    def rpy(self, host, code, args, timeout=0):
        self.calls += 1
        return self.out


def die():
    return {"gen_host": "h", "plan": "/p.json", "event": "e"}


class EnsurePlanView(unittest.TestCase):
    def test_planned_type_is_provisional_after_read(self):
        d = die()
        self.assertFalse(KW.prov_item(d, "cb"))
        ap = AP({"plan_sha": "abc", "flags": {"cb": "planned"}, "blocks": {"cb": "1"}})
        self.assertTrue(KW.ensure_plan_view(ap, {}, d))
        self.assertTrue(KW.prov_item(d, "cb"))
        self.assertEqual(d["_plan_sha"], "abc")

    def test_second_call_does_not_probe(self):
        d = die()
        ap = AP({"plan_sha": "abc", "flags": {}})
        KW.ensure_plan_view(ap, {}, d)
        KW.ensure_plan_view(ap, {}, d)
        self.assertEqual(ap.calls, 1)

    def test_unreadable_plan_says_no(self):
        d = die()
        self.assertFalse(KW.ensure_plan_view(AP({"error": "x"}), {}, d))
        self.assertNotIn("_plan_flags", d)

    def test_unknown_die_says_no(self):
        self.assertFalse(KW.ensure_plan_view(AP({}), {}, None))


if __name__ == "__main__":
    unittest.main()
