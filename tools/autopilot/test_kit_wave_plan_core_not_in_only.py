"""KIT-OPS-1 11-12 (CORE-ROWS-1 17:23 class): a plan_core_items core missing from only_items is named
(skip PLAN-CORE-NOT-IN-ONLY + one plan_dies log line per run) instead of a silent "outside configured only_items" drop."""
import unittest
from test_kit_wave import KW, cfg, OWN


class PlanCoreNotInOnly(unittest.TestCase):
    def rows(self):
        return KW.parse_owners(OWN)

    def test_missing_core_is_named_and_still_not_picked(self):
        c = cfg(only_items=["kv3_hg_v1"], plan_core_items=["ot_new_core"], kinds=["type", "core"])
        p, s = KW.select(self.rows(), c, "qwen_kvsys", {}, {"kv3_hg_v1": "a", "ot_new_core": "b"})
        self.assertEqual(s.get(KW.PLAN_CORE_NOT_IN_ONLY), ["ot_new_core"])
        self.assertNotIn("ot_new_core", [r["item"] for r in p])        # visibility only: selection is unchanged
        self.assertIn("ot_new_core", s.get("outside configured only_items", []))

    def test_core_in_only_items_is_silent(self):
        c = cfg(only_items=["ot_new_core"], plan_core_items=["ot_new_core"], kinds=["type", "core"])
        p, s = KW.select(self.rows(), c, "qwen_kvsys", {}, {"ot_new_core": "b"})
        self.assertNotIn(KW.PLAN_CORE_NOT_IN_ONLY, s)
        self.assertIn("ot_new_core", [r["item"] for r in p])

    def test_core_not_in_plan_is_not_this_class(self):
        # not a plan type: select() makes no row for it, so only_items drops nothing
        d = cfg(only_items=["kv3_hg_v1"], plan_core_items=["ot_gone"])["dies"]["qwen_kvsys"]
        self.assertEqual(KW.plan_core_not_in_only(d, {"kv3_hg_v1": "a"}), [])
        self.assertEqual(KW.plan_core_not_in_only(d, None), ["ot_gone"])   # plan unknown: list them all

    def test_no_only_items_is_silent(self):
        d = cfg(plan_core_items=["ot_new_core"])["dies"]["qwen_kvsys"]
        d.pop("only_items", None)
        self.assertEqual(KW.plan_core_not_in_only(d, {"ot_new_core": "b"}), [])

    def test_plan_dies_logs_one_line(self):
        c = cfg(only_items=["kv3_hg_v1"], plan_core_items=["ot_a", "ot_b"])
        got = []
        orig = KW.select
        try:
            KW.select = lambda *a, **k: ([], {KW.PLAN_CORE_NOT_IN_ONLY: ["ot_a", "ot_b"]})
            KW.plan_dies(None, c, {"items": {}}, self.rows(), {}, "intel2", probe=False, log=got.append)
        finally:
            KW.select = orig
        hits = [l for l in got if l.startswith("KIT-WAVE PLAN-CORE-NOT-IN-ONLY qwen_kvsys: 2 ")]
        self.assertEqual(len(hits), 1, got)
        self.assertIn("ot_a ot_b", hits[0])


if __name__ == "__main__":
    unittest.main()
