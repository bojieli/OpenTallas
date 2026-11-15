#!/usr/bin/env python3
"""PROV-PINS-BUS (11-05): plan pin tables with {bus, bit} rows give named contract pins; a pinless dump row loads."""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import prov_view as P
import geom_rules as G


class PlanPins(unittest.TestCase):
    def _pins(self, body):
        with tempfile.TemporaryDirectory() as d:
            open(os.path.join(d, "p.json"), "w").write(json.dumps(body))
            return P.plan_pins({"pins_file": "p.json"}, d)

    def test_bus_bit_rows(self):
        got = self._pins([{"bus": "l_out", "bit": 3, "layer": "M4", "x": 1.0, "y": 2.0, "face": "E"},
                          {"bus": "clk", "layer": "M5", "x": 0.0, "y": 1.0}])
        self.assertEqual([p["name"] for p in got], ["l_out[3]", "clk"])
        self.assertEqual(got[0]["layer"], "M4")

    def test_named_rows_unchanged(self):
        got = self._pins({"pins": [{"name": "a[0]", "layer": "M4", "x": 1, "y": 1}, "junk"]})
        self.assertEqual([p["name"] for p in got], ["a[0]"])

    def test_no_pins_file(self):
        self.assertIsNone(P.plan_pins({}, "/nonexistent"))


class GeomLoadPinless(unittest.TestCase):
    def test_pinless_master_row(self):
        with tempfile.TemporaryDirectory() as d:
            f = os.path.join(d, "g.tsv")
            open(f, "w").write("I\tm_pinless\t\nI\tm_two\ta:INPUT\tb:OUTPUT\n")
            ex = {}
            try:
                G.load(f, ex)
            except Exception as e:  # later fields (no D/R rows) may be required; only the I rows are under test
                if isinstance(e, ValueError) and "dictionary update" in str(e):
                    raise
            self.assertEqual(ex["macro_ports"]["m_pinless"], {})
            self.assertEqual(ex["macro_ports"]["m_two"], {"a": "INPUT", "b": "OUTPUT"})


if __name__ == "__main__":
    unittest.main()
