"""KIT-OPS-6: die option item_prov_view_sources puts a private view of a child module first for ONE item.
    python3 -m pytest -q tools/autopilot/test_item_prov_views.py"""
import sys
import tempfile
import types
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave as K  # noqa: E402


class ItemViews(unittest.TestCase):
    def spec(self, d, item):
        with tempfile.TemporaryDirectory() as t:
            return K.prov_spec(types.SimpleNamespace(AP_DIR=t), d, "qc", item, "hub")

    def base(self):
        return {"_prov_deps": {"a": ["m"], "b": ["m"]},
                "prov_view_sources": {"m": [{"host": "h1", "dir": "/old", "job": "COUNTED m"}]}}

    def test_only_the_named_item_gets_the_private_view_first(self):
        d = self.base()
        d["item_prov_view_sources"] = {"a": {"m": [{"host": "h2", "dir": "/new", "counted": True}]}}
        a = self.spec(d, "a")["cands"]["m"]
        self.assertEqual([c["dir"] for c in a], ["/new", "/old"])
        self.assertTrue(K.view_priority_candidate(a[0]))
        self.assertEqual([c["dir"] for c in self.spec(d, "b")["cands"]["m"]], ["/old"])

    def test_no_option_is_unchanged(self):
        self.assertEqual([c["dir"] for c in self.spec(self.base(), "a")["cands"]["m"]], ["/old"])


if __name__ == "__main__":
    unittest.main()
