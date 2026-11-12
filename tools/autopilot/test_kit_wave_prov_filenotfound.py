#!/usr/bin/env python3
"""KW-FIX-45 11-12: a prov_view crash on a missing staged input is INFRA, a real view failure stays PLAN."""
import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit_wave as kw

class T(unittest.TestCase):
    def test_classes(self):
        fnf = ("PROVISIONAL view FAIL (KW-PROV-1): prov_view.py crashed on kv3_hub_C: FileNotFoundError: [Errno 2] "
               "No such file or directory: '/srv/x/dkv98/vF/pins/a.json'")
        cls, why = kw.classify("prov_views", fnf)
        self.assertEqual(cls, "INFRA")
        cls, why = kw.classify("prov_views", "PROVISIONAL view FAIL (KW-PROV-1): no provisional abstract for a child of T")
        self.assertEqual(cls, "PLAN")
        cls, why = kw.classify("prov_views", "PROVISIONAL view FAIL (KW-PROV-1): prov_view.py crashed on T: KeyError: 'x'")
        self.assertEqual(cls, "PLAN")

if __name__ == "__main__":
    unittest.main()
