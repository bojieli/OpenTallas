#!/usr/bin/env python3
"""ot_autoclean.signed_record: an ECO-signed kit (eco_*/i*/signoff/signoff.json SIGNED, kit-top signoff NOT SIGNED) is a
signed kit, the newest SIGNED record wins, and its ECO DB is kept (AUTO-EXPORT 11-25, sle_st_b_v2__clfde1249e)."""
import json
import os
import shutil
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ot_autoclean as ac


def put(p, obj, age_s):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as f:
        f.write(json.dumps(obj) if not isinstance(obj, str) else obj)
    t = time.time() - age_s
    os.utime(p, (t, t))


class T(unittest.TestCase):
    def setUp(self):
        self.k = os.path.join(tempfile.mkdtemp(prefix="aceco"), "gen", "kitA")
        os.makedirs(os.path.join(self.k, "run", "results"))

    def tearDown(self):
        shutil.rmtree(os.path.dirname(os.path.dirname(self.k)))

    def test_eco_signed_over_unsigned_top(self):
        put(os.path.join(self.k, "signoff/signoff.json"), dict(verdict="NOT SIGNED", tag="base"), 7200)
        eco_odb = os.path.join(self.k, "eco_20261125_091937_1/i1/run/results/asap7/d/base/6_final.odb")
        put(os.path.join(self.k, "eco_20261125_091937_1/i1/signoff/signoff.json"),
            dict(verdict="SIGNED", tag="eco", inputs=dict(odb=eco_odb)), 600)
        rec = ac.signed_record(self.k)
        self.assertIsNotNone(rec)
        self.assertEqual(rec["tag"], "eco")
        self.assertIn(ac.norm(eco_odb), ac.must_keep(self.k, rec, set()))

    def test_newest_signed_wins(self):
        put(os.path.join(self.k, "signoff/signoff.json"), dict(verdict="SIGNED", tag="base"), 7200)
        put(os.path.join(self.k, "eco_1/i1/signoff/signoff.json"), dict(verdict="SIGNED", tag="eco1"), 3600)
        put(os.path.join(self.k, "eco_2/i2/signoff/signoff.json"), dict(verdict="SIGNED", tag="eco2"), 60)
        self.assertEqual(ac.signed_record(self.k)["tag"], "eco2")

    def test_newer_unsigned_eco_falls_back_to_signed(self):
        put(os.path.join(self.k, "signoff/signoff.json"), dict(verdict="SIGNED", tag="base"), 7200)
        put(os.path.join(self.k, "eco_2/i1/signoff/signoff.json"), dict(verdict="NOT SIGNED", tag="eco"), 60)
        put(os.path.join(self.k, "signoff_eco_9/signoff.json"), "{broken", 30)
        self.assertEqual(ac.signed_record(self.k)["tag"], "base")

    def test_nothing_signed(self):
        put(os.path.join(self.k, "signoff/signoff.json"), dict(verdict="NOT SIGNED"), 60)
        put(os.path.join(self.k, "eco_2/i1/signoff/signoff.json"), dict(verdict="FAIL"), 30)
        self.assertIsNone(ac.signed_record(self.k))
        shutil.rmtree(os.path.join(self.k, "signoff"))
        shutil.rmtree(os.path.join(self.k, "eco_2"))
        self.assertIsNone(ac.signed_record(self.k))


if __name__ == "__main__":
    unittest.main()
