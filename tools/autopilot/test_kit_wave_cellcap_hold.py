#!/usr/bin/env python3
"""CELLCAP-HOLD / CELLCAP-RETRACT (COORD 11-23): a type whose CELL-BUDGET projection is over the 400k cap is refused at launch unless a
type_split / recorded exception covers it; every die carries cell_cap_exceptions {"*": "r703"} (owner r703), so in practice it is a WARN +
one owner post (report only).  Running kits are never touched."""
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

    def test_r703_exception_launches_and_posts_once(self):
        posts, logs = [], []

        class AP:
            DRY = False

            @staticmethod
            def log(m):
                logs.append(m)

            @staticmethod
            def coord_append(f, line):
                posts.append(line)
        d = dict(self.D, cell_cap_exceptions={"*": "r703"}, _plan_sha="abc", die_owner="QC-STB-CAP")
        self.assertIsNone(KW.plan_entry_block(d, "a"))
        cfg, st = {"dies": {"qwen_compute": d}}, {}
        KW.cell_budget_note(AP, cfg, st)
        KW.cell_budget_note(AP, cfg, st)
        self.assertEqual(len(posts), 1)
        self.assertIn("WARN [KIT-WAVE -> QC-STB-CAP]", posts[0])
        self.assertIn("410,000", posts[0])
        self.assertIn("r703", posts[0])

    def test_cached_probe_without_cell_budget_is_rerun(self):
        self.assertIn('"cell_budget" in c', KW.Path(KW.__file__).read_text())


if __name__ == "__main__":
    unittest.main()
