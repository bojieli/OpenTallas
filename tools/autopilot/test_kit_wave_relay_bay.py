"""SAFE-STATION-1 11-03: relay-bay class default for wire-only station types + its fail class"""
import unittest

import kit_wave as KW


class RelayBayClass(unittest.TestCase):
    def test_default_regex(self):
        import re
        self.assertTrue(re.search(KW.RELAY_BAY_RE["s81"], "slice_station__t30__cl1653104c"))
        self.assertFalse(re.search(KW.RELAY_BAY_RE["s81"], "slice_leaf__t40"))
        for t in ("sle_stm_v2__cl7b3062fa", "slw_fw_v1__cl51d45468", "slw_fe_v2__clf110fab2", "sle_fw_v2__cl69f5e854"):
            self.assertTrue(re.search(KW.RELAY_BAY_RE["qwen_compute"], t), t)
        self.assertFalse(re.search(KW.RELAY_BAY_RE["qwen_compute"], "sle_sc_v1__cl0"))

    def test_classify(self):
        c = KW.classify("relay_bay", "FAIL_PREBUILD relay_bay: t: 2 of 9 hops below +10% of the period (table x)")
        self.assertEqual(c[0], "PLAN")


if __name__ == "__main__":
    unittest.main()
