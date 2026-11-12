"""KW-FIX-46 11-12: cfg src_retired dirs are never a source for a new row"""
import unittest
import kit_wave as K


class SrcRetired(unittest.TestCase):
    def test_hit(self):
        cfg = {"src_retired": ["/x/src28ap/"]}
        self.assertEqual(K.retired_src_hit(cfg, ["/x/src28ap/p/plan.json"]), "/x/src28ap/p/plan.json")
        self.assertEqual(K.retired_src_hit(cfg, ["/x/src28ap"]), "/x/src28ap")
        self.assertEqual(K.retired_src_hit(cfg, ["/x/src28apX/a", None]), "")
        self.assertEqual(K.retired_src_hit({}, ["/x/src28ap"]), "")

    def test_spec_retired(self):
        cfg = {"src_retired": ["/x/src28ap"]}
        self.assertTrue(K.spec_retired(cfg, {"src": "/d", "plan": "/d/p.json", "kit_rtl": {"bind_out": "/x/src28ap/b"}}))
        self.assertFalse(K.spec_retired(cfg, {"src": "/d", "plan": "/d/p.json", "kit_rtl": {}}))


if __name__ == "__main__":
    unittest.main()
