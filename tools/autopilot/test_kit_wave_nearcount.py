#!/usr/bin/env python3
"""NEAR-COUNT (COORD 11-01 KIT-WAVE-16 (6)): cores/types in lanes/NEAR-COUNT.tsv launch with ot-run --priority die --crit"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import autopilot as AP  # noqa: E402
import kit_wave as KW  # noqa: E402


def cfg(near=None):
    d = {"enabled": True, "event": "e1", "gate": {"g0c": "PASS", "bind": "PASS", "clock": "PASS", "evidence": "x"},
         "plan": "/srv/p/plan.json", "gen_host": "intel1", "src": "/srv/wt/kw", "src_sha": "620077f42",
         "owner_lane": "DIE-KV-43"}
    c = {"enabled": True, "max_inflight": 40, "max_launch_per_tick": 6, "dies": {"qwen_kvsys": d, "s81": dict(d)}}
    if near is not None:
        c["_near_count"] = near
    return c


TSV = """# NEAR-COUNT -- SIGNOFF-SPRINT-19
die\tcore\tstage\tnote
qwen_kvsys\tkv3_pc\tsignoff\t1 short
s81\tslice_station\troute\tparent type

*\tqkd_hr_cdc_ci\tlec\tany die
"""


class Parse(unittest.TestCase):
    def test_header(self):
        self.assertEqual(AP.parse_near_count(TSV), {("qwen_kvsys", "kv3_pc"), ("s81", "slice_station"),
                                                    ("*", "qkd_hr_cdc_ci")})

    def test_headerless_and_empty(self):
        self.assertEqual(AP.parse_near_count("# c\nhbm\tlanes8_11\textra\n"), {("hbm", "lanes8_11")})
        self.assertEqual(AP.parse_near_count(""), set())
        self.assertEqual(AP.parse_near_count(None), set())

    def test_item_column(self):
        self.assertEqual(AP.parse_near_count("item\tdie\nkv3_pc\tqwen_kvsys\n"), {("qwen_kvsys", "kv3_pc")})

    def test_args(self):
        near = AP.parse_near_count(TSV)
        self.assertEqual(AP.near_count_args(near, "qwen_kvsys", "kv3_pc"), ["--priority", "die", "--crit"])
        self.assertEqual(AP.near_count_args(near, "s81", "kv3_pc"), [])
        self.assertEqual(AP.near_count_args(near, "hbm", None, "qkd_hr_cdc_ci"), ["--priority", "die", "--crit"])
        self.assertEqual(AP.near_count_args(set(), "qwen_kvsys", "kv3_pc"), [])


class Spec(unittest.TestCase):
    def test_item_parent_core(self):
        near = AP.parse_near_count(TSV)
        self.assertTrue(KW.spec_for(cfg(near), "qwen_kvsys", "kv3_pc", "intel2")["crit"])
        self.assertTrue(KW.spec_for(cfg(near), "s81", "slice_station__t12", "intel2", parent="slice_station")["crit"])
        self.assertFalse(KW.spec_for(cfg(near), "s81", "kv3_pc", "intel2")["crit"])
        self.assertTrue(KW.spec_for(cfg(near), "s81", "qkd_hr_cdc_ci", "intel2", kind="core")["crit"])

    def test_default_off(self):
        sp = KW.spec_for(cfg(), "qwen_kvsys", "kv3_pc", "intel2")
        self.assertFalse(sp["crit"])
        self.assertEqual(KW.crit_args(sp), [])
        self.assertEqual(KW.crit_args({"crit": True}), ["--priority", "die", "--crit"])


if __name__ == "__main__":
    unittest.main()
