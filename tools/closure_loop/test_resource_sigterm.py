"""EARLYOOM-SIGTERM 2026-10-16: an earlyoom SIGTERM of a stage wrapper is a resource crash, not a flow error."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import closure_loop as cl  # noqa: E402


class ResourceSigterm(unittest.TestCase):
    def test_bash_terminated_line_is_resource(self):
        tail = ("hold_corners_patch: already supports OT_ROUTE_HOLD_CORNERS (hook-aware, mm)\n"
                "Terminated                 python3 tools/run_abi3_physical.py --view asap7 --top x\n"
                "OT_ROUTE_HOLD_CORNERS=mm: repair scenes WC,BC (SS setup + FF hold), FF SDCs [/src/s.sdc]\n")
        self.assertTrue(cl.RESOURCE_RE.search(tail))

    def test_status_rc_143_is_resource(self):
        self.assertTrue(cl.RESOURCE_RE.search("flow_rc=143\ncorner_rc=1\n"))

    def test_mm_banner_alone_is_not_resource(self):
        self.assertIsNone(cl.RESOURCE_RE.search(
            "OT_ROUTE_HOLD_CORNERS=mm: repair scenes WC,BC (SS setup + FF hold), FF SDCs [/src/s.sdc]\n"
            "flow_rc=1\ncorner_rc=1\nterminated by GRT-0116\n"))


if __name__ == "__main__":
    unittest.main()
