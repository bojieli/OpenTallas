"""PIN-ON-TRACK submit lint (track_lint.py, fe-push-hphys-1010 2026-10-10)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import submit_lint as S  # noqa: E402
import track_lint as T  # noqa: E402

LEF = """MACRO lane
  SIZE 10 BY 20 ;
  PIN a[0]
    DIRECTION INPUT ;
    USE SIGNAL ;
    PORT
      LAYER M4 ;
        RECT  0 4.992 0.084 5.016 ;
    END
  END a[0]
  PIN b
    DIRECTION INPUT ;
    USE SIGNAL ;
    PORT
      LAYER M6 ;
        RECT  0 6.400 0.084 6.432 ;
    END
  END b
  PIN VDD
    USE POWER ;
  END VDD
END lane
"""


class FakeGit:
    def __init__(self, files):
        self.files = files

    def show(self, commit, path):
        return self.files.get(path)

    def blob(self, commit, path):
        return "x" if path in self.files or path == "" else None


def spec(cmd="bash t/route.sh L"):
    return {"name": "j", "source": {"commit": "c"}, "stages": {"route": {"cmd": cmd}},
            "verdict": {"macros": ["t/lane"]}}


SCRIPT = "T=${TILED:-t/d}\npython3 run.py --orfs-var IO_CONSTRAINTS=/src/$T/io.tcl --macro-view lane=t/lane " \
         "--orfs-var MACRO_PLACEMENT_TCL=/src/$T/m.tcl\n"


def files(io, mac):
    return {"t/route.sh": SCRIPT, "t/d/io.tcl": io, "t/d/m.tcl": mac, "t/lane/lane.lef": LEF}


class Track(unittest.TestCase):
    def test_on_track(self):
        self.assertTrue(T.on_track("M5", 0.540, 0.0))
        self.assertFalse(T.on_track("M5", 0.528, 0.0))
        self.assertTrue(T.on_track("M7", 0.656, 0.0))
        self.assertFalse(T.on_track("M7", 0.640, 0.0))
        self.assertTrue(T.on_track("M4", 0.0, 2.028))
        self.assertFalse(T.on_track("M4", 0.0, 2.0))
        self.assertTrue(T.on_track("M3", 0.513, 0.0))

    def test_su_tile_class_refused(self):
        io = "place_pin -pin_name {bc_in[0]} -layer M5 -location {0.5280 0.0960} -pin_size {0.0240 0.1920}\n"
        mac = "place_macro -macro_name {u_lane} -location {100.224 1.080} -orientation R0 -exact\n"
        r = T.check(spec(), FakeGit(files(io, mac)))
        self.assertEqual(r["verdict"], "REFUSE")
        self.assertIn("bc_in[0] M5", r["message"])
        self.assertIn("macro u_lane", r["message"])
        io_ok = "place_pin -pin_name {bc_in[0]} -layer M5 -location {0.5400 0.0960}\n"
        self.assertEqual(T.check(spec(), FakeGit(files(io_ok, mac)))["verdict"], "WARN")   # macro alone warns

    def test_on_grid_passes(self):
        io = "place_pin -pin_name {bc_in[0]} -layer M5 -location {0.5400 0.0960} -pin_size {0.0240 0.1920}\n"
        mac = "place_macro -macro_name {u_lane} -location {100.224 0.960} -orientation R0 -exact\n"
        r = T.check(spec(), FakeGit(files(io, mac)))
        self.assertEqual(r["verdict"], "PASS", r["message"])

    def test_mirrored_macro(self):
        # MX: y' = H - y.  The M4 pin centre 5.004 -> 14.996 + oy: on track (0.012 + 0.048k) at oy = 1.000, not at 0.960
        lef = LEF.split("  PIN b")[0] + "  PIN VDD\n    USE POWER ;\n  END VDD\nEND lane\n"
        io = "place_pin -pin_name {x} -layer M5 -location {0.5400 0.0960}\n"
        f = files(io, "place_macro -macro_name {u_lane} -location {100.224 1.000} -orientation MX\n")
        f["t/lane/lane.lef"] = lef
        self.assertEqual(T.check(spec(), FakeGit(f))["verdict"], "PASS")
        f["t/d/m.tcl"] = "place_macro -macro_name {u_lane} -location {100.224 0.960} -orientation MX\n"
        self.assertEqual(T.check(spec(), FakeGit(f))["verdict"], "WARN")

    def test_cmd_env_overrides_script_default(self):
        io = "place_pin -pin_name {p} -layer M7 -location {0.6400 0.0960}\n"
        f = files("", "")
        f["t/e/io.tcl"] = io
        r = T.check(spec("TILED=t/e bash t/route.sh L"), FakeGit(f))
        self.assertEqual(r["verdict"], "REFUSE")

    def test_skip_without_static_tcl(self):
        r = T.check({"name": "j", "source": {"commit": "c"}, "stages": {"route": {"cmd": "python3 gen.py"}}}, FakeGit({}))
        self.assertEqual(r["verdict"], "SKIP")

    def test_own_frame_offgrid_macro_not_refused(self):
        lef = LEF.replace("4.992 0.084 5.016", "5.000 0.084 5.010").replace("PIN b", "PIN c").replace("END b", "END c")
        lef = lef.replace("6.400 0.084 6.432", "6.380 0.084 6.390")
        f = files("place_pin -pin_name {x} -layer M5 -location {0.5400 0.0960}\n",
                  "place_macro -macro_name {u_lane} -location {100.224 0.960} -orientation R0\n")
        f["t/lane/lane.lef"] = lef
        lp = T.lef_pins(lef)
        bad = len(T.macro_offtrack(lp, 100.224, 0.960, "R0"))
        r = T.check(spec(), FakeGit(f))
        if T.best_offtrack(lp, 100.224, 0.960, "R0") >= bad:
            self.assertEqual(r["verdict"], "PASS", r["message"])

    def test_submit_lint_refuses(self):
        io = "place_pin -pin_name {bc_in[0]} -layer M5 -location {0.5280 0.0960}\n"
        r = S.check(spec(), FakeGit(files(io, "")))
        self.assertEqual(r["verdict"], "REFUSE")
        self.assertEqual(r["pin_track"]["verdict"], "REFUSE")


if __name__ == "__main__":
    unittest.main()
