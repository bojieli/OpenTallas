#!/usr/bin/env python3
"""CELLCAP-HOLD (COORD FABLE FLOW REVIEW 11-23 22:50 item 1): a type whose CELL-BUDGET projection is over the 400k OpenROAD cap is
refused at launch even under stops_off, unless a type_split / recorded exception covers it; running kits are not touched."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import kit_wave as KW  # noqa: E402

DIE_PLAN = str(HERE.parent / "die_plan")


def probe(plan):
    with tempfile.TemporaryDirectory() as d:
        pp = Path(d) / "plan.json"
        pp.write_text(json.dumps(plan))
        cache = Path(d) / "cells_cache.json"
        cache.write_text(json.dumps({"cells": {}}))
        env = dict(os.environ, OT_ADV_CELLS_CACHE=str(cache))
        out = subprocess.run([sys.executable, "-c", KW.PROBE_PLAN,
                              json.dumps({"plan": str(pp), "cells_max": 400000, "cells_dir": DIE_PLAN})],
                             capture_output=True, text=True, cwd=d, env=env)
        return json.loads(out.stdout.split("AP_JSON ", 1)[1])


def stations(width, n):
    return [{"name": f"ft{i}", "width": width, "stations": 1} for i in range(n)]


PLAN = {"die": {"name": "x"}, "partition_types": {
    "slotbig": {"ft_slots": stations(1000, 210)},                       # 420k cells of ft stations alone
    "covered": {"ft_slots": stations(1000, 210), "type_split": "covered__a,covered__b"},
    "excepted": {"ft_slots": stations(1000, 210), "cell_cap_exception": "r999"},
    "small": {"ft_slots": stations(1000, 10)},
    "hardt": {"hard": True, "ft_slots": stations(1000, 210)}}}


class Probe(unittest.TestCase):
    def test_probe_flags_cellcap_over_cap_only(self):
        res = probe(PLAN)
        self.assertEqual(res["flags"].get("slotbig"), "cellcap")
        for t in ("covered", "excepted", "small"):
            self.assertNotEqual(res["flags"].get(t), "cellcap", t)
        self.assertEqual(res["cell_budget"]["slotbig"]["est"], 420000)


class Block(unittest.TestCase):
    D = {"_stops_off": True, "_plan_flags": {"a": "cellcap", "b": "split"},
         "_cell_budget": {"a": {"est": 410000, "basis": "retained kit synth 410,000"}}}

    def test_hold_even_under_stops_off(self):
        why = KW.plan_entry_block(dict(self.D), "a")
        self.assertIn("CELLCAP-HOLD", why)
        self.assertIn("410,000", why)
        self.assertIsNone(KW.plan_entry_block(dict(self.D), "b"))       # the cells.py SPLIT note stays a note under stops_off

    def test_recorded_exception_exact_and_glob(self):
        self.assertIsNone(KW.plan_entry_block(dict(self.D, cell_cap_exceptions={"a": "r999"}), "a"))
        self.assertIsNone(KW.plan_entry_block(dict(self.D, cell_cap_exceptions={"a*": "COORD 11-23"}), "a"))
        self.assertIn("CELLCAP-HOLD", KW.plan_entry_block(dict(self.D, cell_cap_exceptions={"z*": "x"}), "a"))

    def test_cached_probe_without_cell_budget_is_rerun(self):
        self.assertIn('"cell_budget" in c', KW.Path(KW.__file__).read_text())


if __name__ == "__main__":
    unittest.main()
