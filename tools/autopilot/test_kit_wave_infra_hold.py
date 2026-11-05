#!/usr/bin/env python3
"""A held item is not relaunched by the INFRA path (KW-FIX-10 11-05, serdes__t4 a1 -> a2 past its hold)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit_wave as KW


def rec(item, status="RETRY-INFRA"):
    return {"die": "s81", "item": item, "status": status, "class": "INFRA", "attempt": 1, "infra_base": 0, "event": "e"}


class InfraHold(unittest.TestCase):
    def cfg(self, holds):
        return {"dies": {"s81": {"event": "e", "hold_items": holds}}}

    def test_no_hold_relaunches(self):
        self.assertTrue(KW.infra_relaunch_due(self.cfg({}), rec("serdes__t4")))

    def test_exact_hold_stays(self):
        self.assertFalse(KW.infra_relaunch_due(self.cfg({"serdes__t4": "why"}), rec("serdes__t4")))

    def test_pattern_hold_stays(self):
        self.assertFalse(KW.infra_relaunch_due(self.cfg({"serdes__*": "why"}), rec("serdes__t4", "FAIL")))

    def test_other_item_unaffected(self):
        self.assertTrue(KW.infra_relaunch_due(self.cfg({"serdes__t13": "why"}), rec("serdes__t4")))


if __name__ == "__main__":
    unittest.main()
