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
        row = PV.add("s81", "cx", self.td / "out.lef", rc, data=data, allow_unprobed=True)
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

    # KW44-DRT0073-1111 class: ot_s81sl_vs u[235] (west-edge M4 pin 0..0.084) under the bloat-1 M5 OBS 0.048..0.12 and
    # its own bloated M4 wire from 0.06; the exact (bloat 0) metal is M4 from 0.084 and M5 0.072..0.096.
    U235 = "RECT 0.0000 10.0000 0.0840 10.0240"

    def _drt(self, m4, m5, far=True):
        obs = "    LAYER M4 ;\n      RECT %s ;\n" % m4 + ("      RECT 1.0000 1.0000 5.0000 1.0240 ;\n" if far else "")
        obs += "    LAYER M5 ;\n      RECT %s ;\n" % m5
        return detail().replace("RECT 0.0000 10.0000 0.1000 10.0240", self.U235).split("  OBS")[0] + \
            "  OBS\n    LAYER M1 ;\n      RECT 0.0000 0.0000 20.0000 20.0000 ;\n" + obs + "  END\nEND cx\nEND LIBRARY\n"

    def _drt_case(self, exact_m4, exact_m5):
        self.base.write_text(BASE.replace("RECT 0.0000 10.0000 0.1000 10.0240", self.U235).replace(
            "  OBS\n", "  OBS\n    LAYER M3 ;\n      RECT 0.0000 0.0000 20.0000 20.0000 ;\n"))   # kit M3 blanket
        bloat = self._drt("0.0600 9.9760 0.2290 10.0480", "0.0480 9.6970 0.1200 10.3030")
        ex = self.td / "exact.lef"
        ex.write_text(self._drt(exact_m4, exact_m5))
        return bloat, ex

    def test_drt0073_pin_without_access_is_found(self):
        bloat, _ = self._drt_case("0.0840 10.0000 0.2050 10.0240", "0.0720 9.7210 0.0960 10.2790")
        r = self.build(bloat)
        self.assertEqual(r["pin_access"]["without"], ["a"])                # the static model sees the u[235] class

    def _probe_dir(self, sha, log):
        d = self.td / "probe"
        d.mkdir(exist_ok=True)
        (d / "probe.json").write_text(json.dumps(dict(lef_sha256=sha, phase_nm=[12, 12])))
        (d / "probe.log").write_text(log)
        (d / "probe.def").write_text("DESIGN pv_probe ;\n")
        return d

    def test_add_needs_a_passing_probe_of_this_lef(self):
        r = self.build(detail())
        rc = self.td / "r.json"
        rc.write_text(json.dumps(r))
        data = self.td / "data"
        with self.assertRaises(SystemExit):                                   # no probe
            PV.add("s81", "cx", self.td / "out.lef", rc, data=data)
        bad = "[ERROR DRT-0073] No access point for u0/a (cx).\nError: probe.tcl, 5 DRT-0073\n"
        with self.assertRaises(SystemExit):                                   # probe failed
            PV.add("s81", "cx", self.td / "out.lef", rc, data=data, probe_dir=self._probe_dir(r["out_sha256"], bad))
        with self.assertRaises(SystemExit):                                   # probe of another LEF
            PV.add("s81", "cx", self.td / "out.lef", rc, data=data,
                   probe_dir=self._probe_dir("0" * 64, "PV_PROBE_PIN_ACCESS_DONE\n"))
        row = PV.add("s81", "cx", self.td / "out.lef", rc, data=data,
                     probe_dir=self._probe_dir(r["out_sha256"], "[INFO DRT-0166] Complete pin access.\nPV_PROBE_PIN_ACCESS_DONE\n"))
        self.assertEqual(row["pin_access_probe"]["verdict"], "PASS")

    def test_probe_def_puts_pins_on_tracks(self):
        lines = BASE.splitlines(keepends=True)
        self.assertEqual(PV.probe_phase(lines), (12, 44))                     # pin a y centre 10.012 um: 20160 + 44 + 10012 = 24 + 629 * 48
        d, macro = PV.probe_def(lines)
        self.assertEqual(macro, "cx")
        self.assertIn("- u0 cx + FIXED ( 20172 20204 ) N ;", d)
        self.assertIn("- n0_0 ( u0 a ) + USE SIGNAL ;", d)
        self.assertNotIn("VDD", d.split("NETS")[1])

    def test_drt0073_window_restores_access_with_exact_metal_only(self):
        bloat, ex = self._drt_case("0.0840 10.0000 0.2050 10.0240", "0.0720 9.7210 0.0960 10.2790")
        r = self.build(bloat, exact=ex)
        self.assertTrue(r["check_ok"], r["problems"])
        self.assertEqual(r["pin_access"]["without_count"], 0)
        obs = (self.td / "out.lef").read_text().split("  OBS")[1]
        self.assertIn("RECT 0.0720 9.8850 0.0960 10.1390", obs)          # real M5, exact, clipped to the M5 window
        self.assertIn("RECT 0.0840 10.0000 0.1950 10.0240", obs)         # real M4 wire, exact, clipped to the M4 window
        self.assertIn("RECT 0.0480 9.6970 0.1200 9.8850", obs)           # bloat outside the window stays
        self.assertIn("LAYER M4 ;", obs)
        m4 = obs.split("LAYER M4 ;")[1].split("LAYER")[0]
        self.assertIn("RECT 0.0000 10.0000 0.0840 10.0240", m4)          # pin cover: the stub touches the pin -> OBS over it
        self.assertEqual(r["pin_cover"], {"M4": 1})
        self.assertNotIn("RECT 0.0480 9.6970 0.1200 10.3030", obs)       # the bloat over the landing is gone
        self.assertIn("RECT 1.0000 1.0000 5.0000 1.0240", obs)           # metal outside every window untouched
        self.assertEqual((self.td / "out.lef").read_text().split("  OBS")[0], self.base.read_text().split("  OBS")[0])

    def test_drt0073_real_metal_blocking_still_fails(self):
        bloat, ex = self._drt_case("0.0300 9.9900 0.2050 10.0340", "0.0000 9.7000 0.2000 10.3000")
        r = self.build(bloat, exact=ex)
        self.assertEqual(r["pin_access"]["without"], ["a"])
        self.assertEqual(r["kit_fallback"]["pins"], ["a"])                   # its windows keep the kit LEF OBS
        obs = (self.td / "out.lef").read_text().split("  OBS")[1]
        self.assertIn("RECT 0.0000 9.8850 0.1990 10.1390", obs)          # a window never removes real metal

    def test_parse_tech_matches_builtin(self):
        t = self.td / "tech.lef"
        t.write_text("""LAYER M4
  TYPE ROUTING ;
  DIRECTION HORIZONTAL ;
 PITCH 0.048 ;
 WIDTH 0.024 ;
 SPACING 0.024 ;
 PROPERTY LEF58_SPACING "
 SPACING 0.024 ENDOFLINE 0.025 WITHIN 0.04 ENDTOEND 0.04 ; " ;
  SPACINGTABLE
 PARALLELRUNLENGTH 0.0
 WIDTH 0.0 0.024
 WIDTH 0.025 0.072 ;
END M4

LAYER M5
  TYPE ROUTING ;
 PITCH 0.048 ;
 WIDTH 0.024 ;
 SPACING 0.024 ;
 " SPACING 0.024 ENDOFLINE 0.025 WITHIN 0.04 ENDTOEND 0.04 ; " ;
  SPACINGTABLE
 PARALLELRUNLENGTH 0.0
 WIDTH 0.0 0.024
 WIDTH 0.025 0.072 ;
END M5

VIA VIA45 Default
  LAYER M4 ;
 RECT -0.023 -0.012 0.023 0.012 ;
  LAYER M5 ;
 RECT -0.012 -0.023 0.012 0.023 ;
  LAYER V4 ;
 RECT -0.012 -0.012 0.012 0.012 ;
END VIA45
""")
        p = PV.parse_tech(t)
        for l in ("M4", "M5"):
            self.assertEqual(p["layers"][l], PV.TECH_ASAP7["layers"][l])
        self.assertEqual(p["vias"][("M4", "M5")], PV.TECH_ASAP7["vias"][("M4", "M5")])

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
            self.assertEqual((row.get("pin_access_probe") or {}).get("verdict"), "PASS", name)   # KW44-DRT0073 gate


if __name__ == "__main__":
    unittest.main()
