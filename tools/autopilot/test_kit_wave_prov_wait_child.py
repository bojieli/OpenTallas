import unittest
import kit_wave as KW


class ProvWaitChild(unittest.TestCase):
    def test_missing_children_are_listed(self):
        spec = {"modules": ["a", "b", "c"], "cands": {"a": [{"x": 1}], "b": []}}
        self.assertEqual(KW.prov_missing_cands(spec), ["b", "c"])

    def test_all_children_routed_or_no_children(self):
        self.assertEqual(KW.prov_missing_cands({"modules": ["a"], "cands": {"a": [1]}}), [])
        self.assertEqual(KW.prov_missing_cands({}), [])
        self.assertEqual(KW.prov_missing_cands(None), [])


if __name__ == "__main__":
    unittest.main()
