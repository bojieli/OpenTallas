#!/usr/bin/env python3
"""tests for porous_views.py (POROUS-ALL-1): option off = byte-identical, base-sha gating, build guards."""
import gzip
import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import porous_views as PV  # noqa: E402

HEAD = """VERSION 5.8 ;
MACRO cx
  CLASS BLOCK ;
  FOREIGN cx 0 0 ;
  SIZE 20.0 BY 20.0 ;
  PIN a
    DIRECTION INPUT ;
    USE SIGNAL ;
    PORT
      LAYER M4 ;
        RECT 0.0000 10.0000 0.1000 10.0240 ;
    END
  END a
  PIN VDD
    DIRECTION INOUT ;
    USE POWER ;
    PORT
      LAYER M5 ;
        RECT 2.0000 1.0000 2.1000 19.0000 ;
    END
  END VDD
"""
BASE = HEAD + """  OBS
    LAYER M1 ;
      RECT 0.0000 0.0000 20.0000 20.0000 ;
    LAYER M4 ;
      RECT 0.0000 0.0000 20.0000 20.0000 ;
    LAYER M5 ;
      RECT 0.0000 0.0000 20.0000 20.0000 ;
  END
END cx
END LIBRARY
"""


def detail(pin_y=10.0, pg_x1=2.1, pg_extra=True):
    pg = "        RECT 2.0000 0.9800 %.4f 19.0200 ;\n" % pg_x1
    if pg_extra:
        pg += "        RECT 8.0000 1.0000 8.1000 19.0000 ;\n"
    return HEAD.replace("RECT 0.0000 10.0000 0.1000 10.0240", "RECT 0.0000 %.4f 0.1000 %.4f" % (pin_y, pin_y + 0.024)) \
        .replace("        RECT 2.0000 1.0000 2.1000 19.0000 ;\n", pg) + """  OBS
    LAYER M1 ;
      RECT 0.0000 0.0000 20.0000 20.0000 ;
    LAYER M4 ;
      RECT 1.0000 1.0000 5.0000 1.0240 ;
    LAYER M5 ;
      RECT 12.0000 1.0000 12.0240 9.0000 ;
  END
END cx
END LIBRARY
"""


class T(unittest.TestCase):
    def setUp(self):
        self.td = Path(tempfile.mkdtemp())
        self.base = self.td / "cx.lef"
        self.base.write_text(BASE)
        os.environ.pop(PV.ENV, None)
        PV.APPLIED.clear(); PV.SKIPPED.clear()

    def build(self, det, **kw):
        d = self.td / "detail.lef"
        d.write_text(det)
        return PV.build(self.base, d, self.td / "out.lef", **kw)

    def test_build_ok_keeps_pins_lower_obs_and_guards_pg(self):
        r = self.build(detail())
        self.assertTrue(r["check_ok"], r["problems"])
        self.assertEqual(r["layers_detailed"], ["M4", "M5"])           # M6/M7 absent from the kit LEF: not touched
        out = (self.td / "out.lef").read_text()
        self.assertIn("RECT 1.0000 1.0000 5.0000 1.0240", out)           # real M4 metal
        self.assertNotIn("LAYER M4 ;\n      RECT 0.0000 0.0000 20.0000 20.0000", out)
        self.assertIn("LAYER M1 ;\n      RECT 0.0000 0.0000 20.0000 20.0000", out)   # M1 blanket kept
        self.assertEqual(out.split("  OBS")[0], BASE.split("  OBS")[0])  # pins / PG pins / SIZE byte-identical
        # PG guard: the second real VDD stripe and the stripe-end extensions are OBS, the kit PG pin is not covered
        self.assertIn("RECT 8.0000 1.0000 8.1000 19.0000", out.split("  OBS")[1])
        self.assertEqual(r["pg_guard_rects"]["M5"], 3)
        self.assertNotIn("RECT 2.0000 1.0000 2.1000 19.0000", out.split("  OBS")[1])

    def test_build_refuses_other_view(self):
        r = self.build(detail(pin_y=12.0))
        self.assertFalse(r["check_ok"])
        self.assertIn("pins/outline differ", r["problems"][0])

    def _store(self):
        r = self.build(detail())
        rc = self.td / "r.json"
        rc.write_text(json.dumps(r))
        data = self.td / "data"
        row = PV.add("s81", "cx", self.td / "out.lef", rc, data=data)
        PV.DATA, PV._map = data, None
        return row

    def test_option_off_is_identity_and_writes_nothing(self):
        self._store()
        self.assertEqual(PV.select(str(self.base), Path), str(self.base))
        kd = self.td / "kit"; kd.mkdir()
        self.assertIsNone(PV.write_receipt(kd, [("u", "cx", str(self.base), None, 0, 0, "R0")]))
        self.assertEqual(list(kd.iterdir()), [])

    def test_option_on_applies_same_basename_and_receipt(self):
        row = self._store()
        os.environ[PV.ENV] = "cx"
        got = PV.select(str(self.base), Path, log=lambda s: None)
        self.assertEqual(Path(got).name, "cx.lef")
        self.assertEqual(hashlib.sha256(Path(got).read_bytes()).hexdigest(), row["sha256"])
        kd = self.td / "kit"; kd.mkdir()
        rec = PV.write_receipt(kd, [("u", "cx", got, None, 0, 0, "R0")])
        self.assertEqual(rec["rows"][0]["sha256"], row["sha256"])
        self.assertTrue((kd / "porous_views.json").is_file())

    def test_option_on_other_module_or_other_base_not_applied(self):
        self._store()
        os.environ[PV.ENV] = "other"
        self.assertEqual(PV.select(str(self.base), Path), str(self.base))
        os.environ[PV.ENV] = "all"
        self.base.write_text(BASE.replace("SIZE 20.0", "SIZE 20.00"))
        self.assertEqual(PV.select(str(self.base), Path, log=lambda s: None), str(self.base))
        self.assertIn("not the base", PV.SKIPPED["cx.lef"]["reason"])

    def test_corrupt_store_stops(self):
        row = self._store()
        (PV.DATA / row["file"]).write_bytes(gzip.compress(b"x", mtime=0))
        os.environ[PV.ENV] = "all"
        with self.assertRaises(ValueError):
            PV.select(str(self.base), Path, log=lambda s: None)

    def test_overlay_matches_this_tree_and_is_idempotent(self):
        here = Path(__file__).resolve().parent / "gen_phys.py"
        cur = here.read_text()
        self.assertEqual(PV.overlay_gen_phys(cur), cur)               # this tree already carries both hooks
        base = cur.replace(PV._HOOK_A2, PV._HOOK_A).replace(PV._HOOK_B2, "")
        self.assertNotEqual(base, cur)
        self.assertEqual(PV.overlay_gen_phys(base), cur)              # the overlay reproduces this tree's gen_phys
        with self.assertRaises(ValueError):
            PV.overlay_gen_phys(base.replace(PV._HOOK_A, ""))

    def test_shipped_map_rows_are_consistent(self):
        data = Path(__file__).resolve().parent / "porous_views_data"
        m = json.loads((data / "map.json").read_text()) if (data / "map.json").is_file() else {}
        for name, row in m.items():
            raw = gzip.decompress((data / row["file"]).read_bytes())
            self.assertEqual(hashlib.sha256(raw).hexdigest(), row["sha256"], name)
            rc = (data / row["receipt"]).read_bytes()
            self.assertEqual(hashlib.sha256(rc).hexdigest(), row["receipt_sha256"], name)
            r = json.loads(rc)
            self.assertTrue(r["check_ok"], name)
            self.assertEqual(r["base_sha256"], row["base_sha256"], name)


if __name__ == "__main__":
    unittest.main()
