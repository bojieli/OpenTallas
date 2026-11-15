#!/usr/bin/env python3
"""KW-FIX-45 11-11: gate() accepts event labels listed in the die option gate_events_extra besides the code list
GATE_EVENTS[die]['exact'] (S81_HEAD was OFF for 3 h because the cut label hcut1111 is not in the code list)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave as KW  # noqa: E402

GOOD = {"g0c": "PASS", "bind": "PASS", "clock": "PASS"}


def cfg(event, **extra):
    d = {"enabled": True, "event": event, "gate": dict(GOOD), "plan": "/p/plan.json", "gen_host": "epyc8", "src": "/s"}
    d.update(extra)
    return {"enabled": True, "dies": {"s81_head": d}}


class GateEventsExtra(unittest.TestCase):
    def test_code_list_event_passes(self):
        ev = KW.GATE_EVENTS["s81_head"]["exact"][-1]
        self.assertTrue(KW.gate(cfg(ev), "s81_head")[0])

    def test_unknown_label_refused_without_option(self):
        ok, why = KW.gate(cfg("hcut1111"), "s81_head")
        self.assertFalse(ok)
        self.assertIn("not a COORD plan of record", why)

    def test_label_from_config_accepted(self):
        self.assertTrue(KW.gate(cfg("hcut1111", gate_events_extra=["hcut1111"]), "s81_head")[0])

    def test_other_label_still_refused(self):
        self.assertFalse(KW.gate(cfg("hcut9999", gate_events_extra=["hcut1111"]), "s81_head")[0])

    def test_gate_keys_still_apply(self):
        c = cfg("hcut1111", gate_events_extra=["hcut1111"])
        c["dies"]["s81_head"]["gate"]["bind"] = "FAIL"
        self.assertFalse(KW.gate(c, "s81_head")[0])


if __name__ == "__main__":
    unittest.main()
