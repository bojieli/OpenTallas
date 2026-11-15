#!/usr/bin/env python3
"""KW-FIX-32 11-07 (OWNER 17:4x): die option types_before_die_clock lets a die whose only non-PASS gate is the die
clock build types as well as cores; default off keeps the cores-only mode (12.22 item 4)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave as KW  # noqa: E402


def _hbm(clock="UNMEASURED", **opt):
    d = {"enabled": True, "coord_enable": "COORD", "event": "d44f", "plan": "/srv/p/d44f/die_plan.json",
         "gen_host": "intel2", "src": "/srv/wt/kw", "kinds": ["core", "type"],
         "gate": {"g0c": "PASS", "bind": "PASS", "clock": clock},
         "core_kit": {"item_args": {}}}
    d.update(opt)
    return {"enabled": True, "dies": {"hbm": d}}


class TypesBeforeDieClock(unittest.TestCase):
    def test_default_stays_cores_only(self):
        c = _hbm()
        self.assertTrue(KW.gate(c, "hbm")[0])
        self.assertTrue(c["dies"]["hbm"]["_cores_only"])

    def test_option_builds_types_too(self):
        c = _hbm(types_before_die_clock=True)
        ok, why = KW.gate(c, "hbm")
        self.assertTrue(ok, why)
        self.assertNotIn("_cores_only", c["dies"]["hbm"])

    def test_option_never_waives_g0c_or_bind(self):
        for k in ("bind",):                 # WF-1 11-14 (owner #7): g0c is no longer a plan gate; bind still is
            c = _hbm(types_before_die_clock=True)
            c["dies"]["hbm"]["gate"][k] = "FAIL"
            self.assertFalse(KW.gate(c, "hbm")[0])

    def test_option_without_core_kit(self):
        c = _hbm(types_before_die_clock=True)
        del c["dies"]["hbm"]["core_kit"]
        self.assertTrue(KW.gate(c, "hbm")[0])
        self.assertNotIn("_cores_only", c["dies"]["hbm"])
        c = _hbm()
        del c["dies"]["hbm"]["core_kit"]
        self.assertFalse(KW.gate(c, "hbm")[0])        # no option, no core_kit: the die clock still gates


if __name__ == "__main__":
    unittest.main()
