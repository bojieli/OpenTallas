"""KW-FIX-44 11-10 (COORD ruling 1): the generator snaps io.tcl pins onto their layer's track grid
(pin_grid_snap.snap_generated in gen_phys write_type_kit; pin_grid_snap.py for other kits); kit_gen_lint pin_grid
reports what is still off-grid as ADVISORY, never a FAIL.  Case: DIE-HBM-97 dma vPose2, N pins at x = 0.048 k on M5 whose kit
tracks are offset 0.024 (10 M5 shorts at detail route)."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import kit_contract as KC  # noqa: E402
import kit_gen_lint as L  # noqa: E402
import pin_grid_snap as S  # noqa: E402

TRACKS = """make_tracks M4 -x_offset 0.024 -x_pitch 0.048 -y_offset 0.024 -y_pitch 0.048
make_tracks M5 -x_offset 0.024 -x_pitch 0.048 -y_offset 0.024 -y_pitch 0.048
"""


def kit(pins, extra_cfg=""):
    d = Path(tempfile.mkdtemp())
    (d / "make_tracks.tcl").write_text(TRACKS)
    (d / "config.mk").write_text("export DESIGN_NAME = t\nexport MAKE_TRACKS = /work/make_tracks.tcl\n" + extra_cfg)
    lines = [f"place_pin -pin_name {{{n}}} -layer {l} -location {{{x:.4f} {y:.4f}}} -pin_size {{{w:.4f} {h:.4f}}}"
             for n, l, x, y, w, h in pins]
    (d / "io.tcl").write_text("# test\n" + "\n".join(lines) + "\n")
    return d


N_OFF = [(f"d[{i}]", "M5", 9.024 + 0.144 * i, 275.304, 0.024, 0.192) for i in range(4)]     # 9.024 = 188 x 0.048
N_ON = [(f"d[{i}]", "M5", 9.0 + 0.144 * i, 275.304, 0.024, 0.192) for i in range(4)]        # 9.0 = 0.024 + 187 x 0.048


class Lint(unittest.TestCase):
    def setUp(self):
        os.environ.pop("OT_GRID_LINT", None)

    def test_off_track_pins_fail(self):
        e, applies = L.pin_grid(kit(N_OFF))
        self.assertTrue(applies)
        self.assertEqual(len(e), 5)
        self.assertIn("4 io.tcl pin(s) off the track grid", e[0])
        self.assertIn("pin d[0] M5 x 9.024 is 24.0 nm off", e[1])

    def test_on_track_pins_pass(self):
        self.assertEqual(L.pin_grid(kit(N_ON)), ([], True))

    def test_cross_direction_stub_not_judged(self):
        # an M4 (horizontal) stub on the N face runs across M4 tracks: counted, not judged
        e, info = KC.io_pin_grid(kit([("a", "M4", 10.0, 275.304, 0.024, 0.192)]))
        self.assertEqual(e, [])
        self.assertEqual(info["across"], 1)

    def test_opt_out(self):
        self.assertEqual(L.pin_grid(kit(N_OFF, "export OT_GRID_LINT = 0\n")), ([], False))
        os.environ["OT_GRID_LINT"] = "0"
        try:
            self.assertEqual(L.pin_grid(kit(N_OFF)), ([], False))
        finally:
            os.environ.pop("OT_GRID_LINT", None)

    def test_lint_runs_both_checks_advisory(self):
        rec = L.lint(kit(N_OFF), yosys=False)
        self.assertEqual(rec["checks"]["pin_grid"]["verdict"], "ADVISORY")
        self.assertIn("macro_grid", rec["checks"])
        self.assertEqual(rec["checks"]["macro_grid"]["verdict"], "NA")     # no macros
        self.assertEqual(rec["verdict"], "PASS")                           # advisory: never fails the kit
        self.assertEqual(rec["issues"], [])
        self.assertEqual(len(rec["advisories"]), 5)

    def test_generation_gate_only(self):
        self.assertNotIn("io_pin_grid", KC.CHECKS)                         # advisory at kit generation, no queue row


class Snap(unittest.TestCase):
    def setUp(self):
        os.environ.pop("OT_GRID_LINT", None)

    def test_snap_moves_onto_tracks_and_lint_passes(self):
        kd = kit(N_OFF)
        (kd / "pins.json").write_text(json.dumps({"pins": [dict(bus="d", bit=i, x=9.024 + 0.144 * i, y=275.304)
                                                          for i in range(4)]}))
        self.assertEqual(S.main([str(kd), "--write"]), 0)
        self.assertEqual(L.pin_grid(kd), ([], True))
        rec = json.loads((kd / "pin_grid_snap.json").read_text())
        self.assertEqual(rec["moved"], 4)
        self.assertEqual(rec["worst_move_nm"], 24.0)
        self.assertEqual(rec["pins_json_moved"], 4)
        xs = [p["x"] for p in json.loads((kd / "pins.json").read_text())["pins"]]
        self.assertTrue(all(KC.track_miss(x, 0.048, (0.024,)) < 1e-6 for x in xs), xs)
        self.assertTrue((kd / "io.tcl").read_text().startswith("# test\n"))

    def test_dry_run_writes_nothing(self):
        kd = kit(N_OFF)
        before = (kd / "io.tcl").read_text()
        self.assertEqual(S.main([str(kd)]), 0)
        self.assertEqual((kd / "io.tcl").read_text(), before)
        self.assertFalse((kd / "pin_grid_snap.json").exists())

    def test_overlap_on_one_track_is_unresolved(self):
        # a (off track) would snap onto b's track at the same y: a is not moved
        kd = kit([("a", "M5", 9.024, 275.304, 0.024, 0.192), ("b", "M5", 9.048, 275.304, 0.024, 0.192)])
        self.assertEqual(S.main([str(kd), "--write"]), 1)
        self.assertEqual(len(L.pin_grid(kd)[0]), 2)



TR = {"M5": ("V", 0.048, 0.024, (0.024,)), "M4": ("H", 0.048, 0.024, (0.024,))}


class Generated(unittest.TestCase):
    """gen_phys hook: io.tcl, pins.json and the plan pin records (freeze pin set) move together"""

    def setUp(self):
        os.environ.pop("OT_PIN_GRID_SNAP", None)

    def _kit(self, pins):
        kd = kit(pins)
        (kd / "pins.json").write_text(json.dumps([dict(bus="d", bit=i, layer="M5", x=p[2], y=275.4, face="N")
                                                  for i, p in enumerate(pins)]) + "\n")
        recs = [dict(name=p[0], layer=p[1], x=p[2], y=p[3]) for p in pins]
        return kd, recs

    def test_on_grid_kit_untouched(self):
        kd, recs = self._kit(N_ON)
        before = {f: (kd / f).read_bytes() for f in ("io.tcl", "pins.json")}
        out, clash, rec = S.snap_generated(kd, TR, recs)
        self.assertEqual((out, clash, rec), (recs, [], None))
        self.assertEqual({f: (kd / f).read_bytes() for f in before}, before)
        self.assertFalse((kd / "pin_grid_snap.json").exists())

    def test_off_grid_moves_io_pins_json_and_records(self):
        kd, recs = self._kit(N_OFF)
        out, clash, rec = S.snap_generated(kd, TR, recs)
        self.assertEqual((clash, rec["moved"], rec["pins_json_moved"]), ([], 4, 4))
        self.assertEqual(L.pin_grid(kd), ([], True))
        placed = {p[0]: p[2] for p in KC.io_pins((kd / "io.tcl").read_text())}
        self.assertEqual({r["name"]: r["x"] for r in out}, placed)            # freeze pin set == io.tcl
        self.assertEqual([r["x"] for r in json.loads((kd / "pins.json").read_text())], [placed[f"d[{i}]"] for i in range(4)])
        self.assertTrue((kd / "pin_grid_snap.json").is_file())

    def test_keep_and_opt_out(self):
        kd, recs = self._kit(N_OFF)
        out, clash, rec = S.snap_generated(kd, TR, recs, keep={"d[0]"})
        self.assertEqual(rec["moved"], 3)
        self.assertEqual(out[0], recs[0])
        kd, recs = self._kit(N_OFF)
        before = (kd / "io.tcl").read_bytes()
        self.assertEqual(S.snap_generated(kd, TR, recs, env={"OT_PIN_GRID_SNAP": "0"}), (recs, [], None))
        self.assertEqual((kd / "io.tcl").read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
