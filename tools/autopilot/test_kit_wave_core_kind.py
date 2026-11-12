"""KW-FIX-45 11-11 (DIE-HBM-100 hbm-stale-rows): with plan_items_from_allowlist, a name in plan_core_items gets only the
kind=core row, never an additional kind=type row (the type row was picked first and the bind failed: no partition type)."""
import unittest
from test_kit_wave import KW, cfg, OWN


class CoreKind(unittest.TestCase):
    def rows(self):
        return KW.parse_owners(OWN)

    def test_plan_core_item_gets_only_the_core_row(self):
        c = cfg(only_items=["zz_core_a", "zz_type_b"], plan_items_from_allowlist=True, plan_core_items=["zz_core_a"], kinds=["core", "type"])
        p, s = KW.select(self.rows(), c, "qwen_kvsys", {}, {"zz_core_a": "a" * 12, "zz_type_b": "b" * 12})
        kinds = {r["item"]: r["kind"] for r in p}
        self.assertEqual(kinds, {"zz_core_a": "core", "zz_type_b": "type"})
        self.assertEqual([r["item"] for r in p].count("zz_core_a"), 1)

    def test_without_plan_core_items_the_allowlist_item_is_a_type(self):
        c = cfg(only_items=["zz_type_b"], plan_items_from_allowlist=True, kinds=["core", "type"])
        p, s = KW.select(self.rows(), c, "qwen_kvsys", {}, {"zz_type_b": "b" * 12})
        self.assertEqual([(r["item"], r["kind"]) for r in p], [("zz_type_b", "type")])


if __name__ == "__main__":
    unittest.main()
