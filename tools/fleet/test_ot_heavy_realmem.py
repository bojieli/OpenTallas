"""REALMEM_1110 (KW-FIX-44, OWNER via COORD 11-10): with REAL_ADMIT=1 admission charges a request its class's measured
peak and counts running units at their real memory; only units younger than 5 min (or admitted, not started) keep a
fresh charge; INV_HEADROOM_GB stays the floor.  REAL_ADMIT absent/0 keeps every older rule byte-for-byte."""
import importlib.machinery
import importlib.util
import os
import unittest
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent


def load():
    ld = importlib.machinery.SourceFileLoader("ot_heavy_reconcile_rm", str(HERE / "ot-heavy-reconcile"))
    m = importlib.util.module_from_spec(importlib.util.spec_from_loader(ld.name, ld))
    ld.exec_module(m)
    return m


R = load()


def unit(now, obs, req, age, grow=0.0, active=True):
    return dict(unit="u", res=req, active=active, file="", file_age=0, req=float(req), now=float(now), obs=float(obs),
                age=float(age), cls="c", grow=float(grow))


# epyc4 at 18:41 in miniature: RAM 755, 184 available, settled units well below their past peaks, one young unit
ROWS = [unit(25, 32, 112, 3637, grow=10.0), unit(11, 12, 64, 31046), unit(5, 31, 48, 108544), unit(4, 87, 96, 101993),
        unit(1, 1, 16, 150, grow=15.0)]
B = dict(grow=53.0, fresh_gb=0.0, settled_floor=0.0)


class RealAdmit(unittest.TestCase):
    def env(self, **k):
        base = dict(INV_HEADROOM_GB="32", INV_PAST_PEAK_FACTOR="1", PHASE_CAP_AVAIL_FRAC="0.10", REAL_ADMIT="0")
        base.update(k)
        p = patch.dict(os.environ, base)
        p.start()
        self.addCleanup(p.stop)

    def test_off_keeps_peak_gap_and_reserve(self):
        self.env()
        inv = R.invariant(ROWS, 755.0, 184.0, B, {})
        self.assertAlmostEqual(inv["held"] - inv["now"], (32 - 25) + (12 - 11) + (31 - 5) + (87 - 4), places=3)
        self.assertGreater(inv["reserve"], 0.0)
        self.assertFalse(inv["real"])

    def test_on_counts_real_memory_and_fresh_only(self):
        self.env(REAL_ADMIT="1")
        inv = R.invariant(ROWS, 755.0, 184.0, B, {})
        self.assertAlmostEqual(inv["held"], inv["now"], places=3)       # no past-peak gap
        self.assertEqual(inv["reserve"], 0.0)                           # no running-growth reserve
        self.assertAlmostEqual(inv["fresh"], 15.0, places=3)            # the < 5 min unit keeps its charge
        # admits while MemAvailable - fresh - request >= 32
        self.assertAlmostEqual(inv["free"], 184.0 - 15.0 - 32.0, places=3)
        self.assertIn("REAL_ADMIT", R.inv_text(inv))

    def test_unstarted_reservation_stays_fresh(self):
        self.env(REAL_ADMIT="1")
        inv = R.invariant(ROWS + [unit(0, 0, 40, 0, grow=40.0, active=False)], 755.0, 184.0, B, {})
        self.assertAlmostEqual(inv["fresh"], 55.0, places=3)

    def test_request_charged_measured_peak(self):
        tab = {"run_kit.sh:route": dict(n=3, proved=0, peak_gb=20.0)}
        self.env(REAL_ADMIT="1")
        res, why = R.admit_size(64, "run_kit.sh:route", tab)
        self.assertEqual(res, 22)                                      # ceil(max(1.1 x 20, 20 + 2))
        self.assertIn("REALMEM", why)
        self.assertIsNone(R.admit_size(21, "run_kit.sh:route", tab))   # never above the declared request
        self.assertIsNone(R.admit_size(64, "unmeasured:x", tab))       # unmeasured class: its request
        os.environ["REAL_ADMIT"] = "0"
        self.assertIsNone(R.admit_size(32, "run_kit.sh:route", tab))   # old rule: only above 2 x peak
        self.assertEqual(R.admit_size(64, "run_kit.sh:route", tab)[0], 30)


if __name__ == "__main__":
    unittest.main()
