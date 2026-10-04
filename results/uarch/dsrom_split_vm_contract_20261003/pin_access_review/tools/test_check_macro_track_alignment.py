#!/usr/bin/env python3
"""Guards for tools/check_macro_track_alignment.py (mirrored-macro pin access, dsrom_qframe A_r1/B_r1)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_macro_track_alignment as C  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
ROM = REPO / "physical/asap7_memory_macros/ot_rom_4096x274_m8/ot_rom_4096x274_m8.lef"
TRACKS_COPY = REPO / "results/uarch/dsrom_noECC_production_context_20261002/inputs/make_tracks.tcl"

SYNTH = """VERSION 5.7 ;
PROPERTYDEFINITIONS
  MACRO width INTEGER ;
END PROPERTYDEFINITIONS
MACRO t
  CLASS BLOCK ;
  SYMMETRY X Y ;
  SIZE 10.000 BY %s ;
  PIN a
    USE SIGNAL ;
    PORT
      LAYER M4 ;
      RECT 0.000 0.768 0.024 0.792 ;
    END
  END a
  PIN b
    USE SIGNAL ;
    PORT
      LAYER M4 ;
      RECT 9.976 0.864 10.000 0.888 ;
    END
  END b
  OBS
    LAYER M3 ;
    RECT 0 0 10.000 %s ;
  END
END t
END LIBRARY
"""


def audit(text):
    ms = [m for m in C.parse_lef(text) if m["class"] == "BLOCK"]
    assert len(ms) == 1
    return C.audit_macro(ms[0], C.ASAP7_TRACKS_NM, C.ASAP7_LAYERS), ms[0]


class TrackAlignment(unittest.TestCase):
    def test_embedded_tracks_match_archived_orfs_copy(self):
        if not TRACKS_COPY.exists():
            self.skipTest("archived make_tracks.tcl absent")
        parsed = C.parse_tracks(str(TRACKS_COPY))
        parsed.pop("Pad", None)
        self.assertEqual(parsed, C.ASAP7_TRACKS_NM)

    def test_propertydefinitions_are_not_macros(self):
        ms = C.parse_lef(ROM.read_text())
        self.assertEqual([m["name"] for m in ms], ["ot_rom_4096x274_m8"])
        self.assertEqual(len([p for p in ms[0]["pins"] if p["use"] not in ("POWER", "GROUND")]), 288)

    def test_rom_4096x274_mirror_rule(self):
        rec, _ = audit(ROM.read_text())
        rule = rec["summary"]["M4"]["origin_rule_mod_track_nm"]
        self.assertEqual(rule, {"R0": [0], "MX": [42], "MY": [0], "R180": [42]})
        self.assertEqual(rec["summary"]["M4"]["offtrack_under_origin_0_snap"], ["MX", "R180"])
        mx = rec["orientations"]["M4"]["MX"]
        self.assertEqual(mx["naive_snap_origin_0_mod_track"], {"offtrack_pins": 288, "max_offset_nm": 6.0})
        par = rec["dimension_parity"]["M4"]
        self.assertEqual(par["dim_mod_track_pitch_nm"], 30)
        self.assertEqual(par["mirror_residue_shift_nm"], 6)
        self.assertEqual(par["fix"]["grow_dimension_free"]["new_dim_nm"], 62952)
        self.assertEqual(par["fix"]["grow_dimension_on_snap_grid"]["new_dim_nm"], 63720)
        self.assertEqual(par["fix"]["shift_pins_keep_dim"]["pin_shift_options_nm"], [-21, 3])
        # MX origins must lie on the joint 0.27 um row / 0.048 um track lattice: one per 2.16 um
        j = mx["joint_with_row"]
        self.assertEqual(j["joint_period_nm"], 2160)
        self.assertEqual(len(j["legal_origins_mod_joint_nm"]), 1)
        self.assertEqual(j["legal_origins_mod_joint_nm"][0] % 48, 42)

    def test_qframe_placements(self):
        m = C.parse_lef(ROM.read_text())[0]
        # A_r1 hook: MX origin snapped to 0 mod 0.048 -> every pin 6 nm off; A_r2 hook: 0.042 mod 0.048 -> on track
        y_r1 = C.snap_joint_nm(89370, 270, 270, 0, 48)
        y_r2 = C.snap_joint_nm(89370, 270, 270, 42, 48)
        self.assertEqual((y_r1, y_r2), (88560, 89370))
        r1 = C.check_placement(m, "MX", 10800, y_r1)["layers"]["M4"]
        r2 = C.check_placement(m, "MX", 10800, y_r2)["layers"]["M4"]
        self.assertEqual((r1["offtrack"], r1["max_offset_nm"]), (288, 6.0))
        self.assertEqual(r2["offtrack"], 0)
        self.assertEqual(C.check_placement(m, "R0", 10800, 25920)["layers"]["M4"]["offtrack"], 0)

    def test_height_parity_decides_invariance(self):
        # pin centres 0.012 mod 0.048: H = 0.024 mod 0.048 keeps one origin rule for all orientations
        inv, _ = audit(SYNTH % ("20.520", "20.520"))
        self.assertTrue(inv["summary"]["M4"]["orientation_invariant"])
        self.assertEqual(inv["summary"]["M4"]["offtrack_under_origin_0_snap"], [])
        var, _ = audit(SYNTH % ("20.250", "20.250"))
        self.assertFalse(var["summary"]["M4"]["orientation_invariant"])
        self.assertEqual(var["summary"]["M4"]["origin_rule_mod_track_nm"]["MX"], [(12 - (20250 - 780)) % 48])

    def test_mixed_phases_have_no_legal_origin(self):
        bad = (SYNTH % ("20.520", "20.520")).replace("RECT 9.976 0.864 10.000 0.888", "RECT 9.976 0.870 10.000 0.894")
        rec, _ = audit(bad)
        self.assertEqual(rec["summary"]["M4"]["no_legal_origin"], ["R0", "MX", "MY", "R180"])

    def test_pin_checks(self):
        rec, _ = audit(ROM.read_text())
        pc = rec["pin_checks"]["M4"]
        self.assertEqual(pc["below_min_area"], 288)        # 24x24 nm pins vs 2000 nm^2 M4 min area
        self.assertEqual(pc["same_layer_obs_min_gap_nm"], 48)
        self.assertEqual(pc["same_layer_obs_overlap_or_within_spacing"], 0)
        self.assertEqual(pc["adjacent_layer_obs_covers_pin"], {"M5": 0, "M3": 288})


if __name__ == "__main__":
    unittest.main()
