"""KW-FIX-46 11-12: an item_inputs private src must hold the die-src required files and dirs"""
import unittest
import kit_wave as K


class ItemSrcRequired(unittest.TestCase):
    def test_item_src_required_paths(self):
        cfg = {"dies": {"qc": {"item_inputs": {"a": {"src": "/x/src28ap", "plan": "/x/src28ap/p/plan.json", "note": "n"}}}}}
        ps = K.item_inputs(cfg, "qc")["a"]
        for r in ("/x/src28ap/tools/die_plan/bind.py", "/x/src28ap/physical/common_flow", "/x/src28ap/tools/die_plan"):
            self.assertIn(r, ps)

    def test_no_src_no_extra(self):
        cfg = {"dies": {"qc": {"item_inputs": {"a": {"plan": "/x/p/plan.json"}}}}}
        self.assertFalse(any("common_flow" in p for p in K.item_inputs(cfg, "qc")["a"]))


if __name__ == "__main__":
    unittest.main()
