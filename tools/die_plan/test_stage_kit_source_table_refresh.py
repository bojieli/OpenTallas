#!/usr/bin/env python3
import copy
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stage_kit_source_table_refresh as S  # noqa: E402


def plan(fixed, n=1, native=False, spine=False):
    return {
        "partition_types": {"src": {"buses": [{"name": "o0", "dir": "out"}],
                                    "internal_stations": [{"conn": "bus:o0", "regs_um": [[0, 0]] * n}]},
                            "rx": {"buses": [{"name": "i0", "dir": "in"}]}},
        "partitions": [{"name": "p", "type": "src"}, {"name": "q", "type": "rx"}],
        "ports": [{"id": "L__0", "src": {"part": "p", "bus": "o0"}, "dst": {"part": "q", "bus": "i0"}}],
        "lanes": [dict({"id": "L", "ports": ["L__0"]}, **({"fixed_cycles": fixed} if fixed is not None else {}),
                       **({"spine": True} if spine else {}))],
        "latency": {"lanes": {"L": {"cycles": 5 + (fixed or 0), "fixed": fixed or 0, "natural": 5 + (fixed or 0), "pad": 0}}},
    }


class T(unittest.TestCase):
    def run_main(self, d, native=(), expect=None):
        with tempfile.TemporaryDirectory() as t:
            p, a, o, r = (os.path.join(t, x) for x in ("p.json", "a.json", "o.json", "r.json"))
            json.dump(d, open(p, "w")); json.dump({"internal_stations_types": list(native)}, open(a, "w"))
            args = [p, a, o, r] + (["--expect", str(expect)] if expect is not None else [])
            S.main(args)
            return json.load(open(o)), json.load(open(r))

    def test_unpriced_refreshed(self):
        o, r = self.run_main(plan(None, n=1), expect=1)
        self.assertEqual(o["lanes"][0]["fixed_cycles"], 1)
        row = o["latency"]["lanes"]["L"]
        self.assertEqual((row["fixed"], row["cycles"], row["natural"]), (1, 6, 6))
        self.assertEqual(r["cycles_added"], 1)

    def test_partial_fixed_n2(self):
        o, _ = self.run_main(plan(1, n=2))
        self.assertEqual(o["lanes"][0]["fixed_cycles"], 3)
        self.assertEqual(o["latency"]["lanes"]["L"]["cycles"], 8)

    def test_priced_lane_untouched(self):
        d = plan(2, n=1); o, r = self.run_main(copy.deepcopy(d))
        self.assertEqual(r["lanes"], 0); self.assertEqual(o["lanes"], d["lanes"]); self.assertEqual(o["latency"], d["latency"])

    def test_native_and_spine_skipped(self):
        self.assertEqual(self.run_main(plan(None), native=["src"])[1]["lanes"], 0)
        self.assertEqual(self.run_main(plan(None, spine=True))[1]["lanes"], 0)

    def test_expect_refuses(self):
        with self.assertRaises(SystemExit):
            self.run_main(plan(None), expect=2)

    def test_idempotent(self):
        o, _ = self.run_main(plan(None, n=2))
        _, r2 = self.run_main(o)
        self.assertEqual(r2["lanes"], 0)

    def test_table_mismatch_refuses(self):
        d = plan(None); d["latency"]["lanes"]["L"]["fixed"] = 1
        with self.assertRaises(SystemExit):
            self.run_main(d)


if __name__ == "__main__":
    unittest.main()
