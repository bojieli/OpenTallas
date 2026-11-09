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

    def test_no_host_row_waits_then_retries(self):
        import time
        r = rec("iq", "RETRY-INFRA")
        r["no_host_at"] = time.time()
        self.assertFalse(KW.infra_relaunch_due(self.cfg({}), r))
        r["no_host_at"] = time.time() - KW.NO_HOST_RETRY_S - 1
        self.assertTrue(KW.infra_relaunch_due(self.cfg({}), r))

    def test_no_host_text_is_the_real_ot_run_line(self):
        self.assertTrue(KW.NO_HOST.search("infra @kit_rtl: ot-run: NOT RUN: no host qualifies (epyc4: disk 49 GB < 60)"))
        self.assertTrue(KW.NO_HOST.search("infra @unit: OSError: [Errno 28] No space left on device"))
        self.assertFalse(KW.NO_HOST.search("infra (ssh transport) @relay_bay: Connection closed"))
        self.assertFalse(KW.NO_HOST.search("OSError: [Errno 28] No space left on device"))


if __name__ == "__main__":
    unittest.main()
