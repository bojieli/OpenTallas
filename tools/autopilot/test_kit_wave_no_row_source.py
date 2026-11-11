"""WAVE-OPS-1 11-10: an only_items item with no row source is named (skip NO-ROW-SOURCE + a loud plan_dies log line)."""
import unittest
from test_kit_wave import KW, cfg, OWN


class NoRowSource(unittest.TestCase):
    def rows(self):
        return KW.parse_owners(OWN)

    def test_orphan_core_is_named(self):
        # an HBM-like hard core: in the plan and in only_items, but no OWNERS row and not in plan_core_items
        c = cfg(only_items=["kv3_hg_v1", "ot_new_core"])
        p, s = KW.select(self.rows(), c, "qwen_kvsys", {}, {"kv3_hg_v1": "a", "ot_new_core": "b"})
        self.assertEqual(s.get(KW.NO_ROW_SOURCE), ["ot_new_core"])

    def test_plan_core_items_is_a_row_source(self):
        c = cfg(only_items=["ot_new_core"], plan_core_items=["ot_new_core"])
        p, s = KW.select(self.rows(), c, "qwen_kvsys", {}, {"ot_new_core": "b"})
        self.assertNotIn(KW.NO_ROW_SOURCE, s)

    def test_plan_core_item_not_in_plan_is_named(self):
        # ot_hbm_su_pg_lane_full_x_core 11-10: listed, but not a plan type of the wave's plan -> no row
        c = cfg(only_items=["ot_gone"], plan_core_items=["ot_gone"])
        p, s = KW.select(self.rows(), c, "qwen_kvsys", {}, {"kv3_hg_v1": "a"})
        self.assertEqual(s.get(KW.NO_ROW_SOURCE), ["ot_gone"])

    def test_allowlist_types_class_and_core_view_are_sources(self):
        names = {"kv3_hg_v1__clgood": "a", "new_type": "b"}
        c = cfg(only_items=["kv3_hg_v1__clgood", "new_type"], plan_items_from_allowlist=True)
        p, s = KW.select(self.rows(), c, "qwen_kvsys", {}, names)
        self.assertNotIn(KW.NO_ROW_SOURCE, s)                         # class of an OWNERS parent + allowlisted type
        rows = self.rows() + [dict(die="qwen_kvsys", item="ot_core_m", kind="core", state="NEEDS-KIT", owner="X",
                                   live_job="none", last_activity="", next_step="", evidence="", default_owner="",
                                   replicas="1", members="")]
        self.assertEqual(KW.no_row_source(rows, cfg(only_items=["ot_core_m__v0123456789ab"])["dies"]["qwen_kvsys"],
                                          "qwen_kvsys", {"ot_core_m__v0123456789ab": "c"}), [])

    def test_no_plan_or_no_allowlist_is_silent(self):
        d = cfg(only_items=["x"])["dies"]["qwen_kvsys"]
        self.assertEqual(KW.no_row_source(self.rows(), d, "qwen_kvsys", None), [])
        self.assertEqual(KW.no_row_source(self.rows(), cfg()["dies"]["qwen_kvsys"], "qwen_kvsys", {"x": "a"}), [])

    def test_plan_dies_logs_loud_line(self):
        c = cfg(only_items=["ot_new_core"])
        got = []
        orig = KW.select
        try:
            KW.select = lambda *a, **k: ([], {KW.NO_ROW_SOURCE: ["ot_new_core"]})
            KW.plan_dies(None, c, {"items": {}}, self.rows(), {}, "intel2", probe=False, log=got.append)
        finally:
            KW.select = orig
        self.assertTrue(any(l.startswith("KIT-WAVE NO-ROW-SOURCE qwen_kvsys: 1 ") and "ot_new_core" in l for l in got), got)


if __name__ == "__main__":
    unittest.main()
