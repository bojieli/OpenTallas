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

    def run_dest(self, d, native=(), expect=None):
        with tempfile.TemporaryDirectory() as t:
            p, a, o, r = (os.path.join(t, x) for x in ("p.json", "a.json", "o.json", "r.json"))
            json.dump(d, open(p, "w")); json.dump({"internal_stations_types": list(native)}, open(a, "w"))
            S.main([p, a, o, r, "--dest"] + (["--expect", str(expect)] if expect is not None else []))
            return json.load(open(o)), json.load(open(r))

    @staticmethod
    def with_rx(d, m):
        d["partition_types"]["rx"]["internal_stations"] = [{"conn": "bus:i0", "regs_um": [[0, 0]] * m}]
        return d

    def test_dest_both_ends(self):
        # source n=1 already priced (fixed 1), receiver m=1 unpriced -> fixed 2, cycles +1 (LATCHECK up_s_0S_L0 shape)
        o, r = self.run_dest(self.with_rx(plan(1, n=1), 1), expect=1)
        self.assertEqual(o["lanes"][0]["fixed_cycles"], 2)
        row = o["latency"]["lanes"]["L"]
        self.assertEqual((row["fixed"], row["cycles"], row["natural"]), (2, 7, 7))
        self.assertEqual((r["rows"][0]["src_kit"], r["rows"][0]["dst_kit"], r["cycles_added"]), (1, 1, 1))

    def test_dest_only(self):
        d = self.with_rx(plan(None, n=0), 2)
        d["partition_types"]["src"]["internal_stations"] = []
        o, r = self.run_dest(d, expect=1)
        self.assertEqual(o["lanes"][0]["fixed_cycles"], 2)
        self.assertEqual(o["latency"]["lanes"]["L"]["cycles"], 7)

    def test_dest_pad_absorbs(self):
        d = self.with_rx(plan(1, n=1), 1); d["latency"]["lanes"]["L"]["pad"] = 1; d["latency"]["lanes"]["L"]["cycles"] += 1
        o, r = self.run_dest(copy.deepcopy(d))
        self.assertEqual(r["lanes"], 0); self.assertEqual(o["latency"], d["latency"])

    def test_dest_packed_pad_absorbs_deeper_rx(self):
        # receiver pad 1 (fixed 2 - source 1) packs all 3 IN stations (LATCHECK-1 PASS shape up_s_0N_L4): untouched
        self.assertEqual(self.run_dest(self.with_rx(plan(2, n=1), 3))[1]["lanes"], 0)

    def test_dest_native_source_counts_in_pad(self):
        # native source stations are subtracted from the receiver pad too: fixed 1 = native n 1 -> pad 0 -> priced
        o, r = self.run_dest(self.with_rx(plan(1, n=1), 1), native=["src"], expect=1)
        self.assertEqual(o["lanes"][0]["fixed_cycles"], 2)

    def test_dest_native_rx_still_kit(self):
        # IN stations are never native (source_entries is OUT-only): a native receiver type is priced too
        self.assertEqual(self.run_dest(self.with_rx(plan(1, n=1), 1), native=["rx"])[1]["lanes"], 1)

    def test_dest_core_rows_ignored(self):
        d = self.with_rx(plan(1, n=1), 0)
        d["partition_types"]["rx"]["internal_stations"] = [{"conn": "bus:i0", "core": "c0", "regs_um": [[0, 0]]}]
        self.assertEqual(self.run_dest(d)[1]["lanes"], 0)

    def test_dest_off_ignores_rx(self):
        self.assertEqual(self.run_main(self.with_rx(plan(1, n=1), 1))[1]["lanes"], 0)

    def test_dest_idempotent(self):
        o, _ = self.run_dest(self.with_rx(plan(None, n=2), 1))
        self.assertEqual(o["lanes"][0]["fixed_cycles"], 3)
        self.assertEqual(self.run_dest(o)[1]["lanes"], 0)

    def test_table_mismatch_refuses(self):
        d = plan(None); d["latency"]["lanes"]["L"]["fixed"] = 1
        with self.assertRaises(SystemExit):
            self.run_main(d)


if __name__ == "__main__":
    unittest.main()
