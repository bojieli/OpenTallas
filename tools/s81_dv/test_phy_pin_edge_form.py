import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("phy_pin_edge_form", Path(__file__).with_name("phy_pin_edge_form.py"))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def pin(name, layer, x0, x1, d="INPUT"):
    return (f"  PIN {name}\n    DIRECTION {d} ;\n    USE SIGNAL ;\n    SHAPE ABUTMENT ;\n    PORT\n"
            f"      LAYER {layer} ;\n      RECT {x0:.3f} 9.808 {x1:.3f} 10.000 ;\n"
            f"    END\n  END {name}\n")


SRC = ("MACRO phy\n  SIZE 10.000 BY 10.000 ;\n" + pin("clk", "M5", 1.0, 1.024)
       + "".join(pin(f"k_v[{i}]", "M5", 2 + .2 * i, 2.024 + .2 * i) for i in range(4))
       + "".join(pin(f"kr_v[{i}]", "M7", 5 + .2 * i, 5.032 + .2 * i, "OUTPUT") for i in range(4)) + "END phy\n")
SPEC = {"edge": "E", "layer": "M6", "pitch_nm": 64, "offset_nm": 32, "pin_len_nm": 192, "pin_w_nm": 32,
        "origin_um": [0, 0], "clearance_nm": 72, "pg_bands": [{"period_nm": 4320, "lo_nm": 1968, "hi_nm": 2640}],
        "groups": [{"name": "in", "range_um": [6.0, 9.0], "order": "desc", "bits": [["k_v", 2, 4]]},
                   {"name": "out", "range_um": [0.5, 3.5], "order": "asc", "bits": [["kr_v", 2, 4]]}]}


class EdgeForm(unittest.TestCase):
    def test_moves_only_the_named_channel_onto_the_edge_tracks(self):
        out, rep = mod.transform(SRC, SPEC)
        self.assertEqual(rep["moved_pins"], 4)
        body = {m[2]: m[3] for m in mod.PIN.finditer(out)}
        self.assertIn("LAYER M5", body["k_v[0]"])              # channel kept
        self.assertIn("LAYER M7", body["kr_v[1]"])
        for n in ("k_v[2]", "k_v[3]", "kr_v[2]", "kr_v[3]"):
            self.assertIn("LAYER M6", body[n])
            self.assertIn("RECT 9.808 ", body[n])               # on the E edge
            self.assertNotIn("LAYER M5", body[n])
        ys = {n: float(body[n].split("RECT ")[1].split()[1]) + .016 for n in ("k_v[2]", "k_v[3]", "kr_v[2]", "kr_v[3]")}
        for n, y in ys.items():
            self.assertEqual(round(y * 1000 - 32) % 64, 0)       # on an M6 track
            self.assertFalse(1968 - 88 < round(y * 1000) % 4320 < 2640 + 88)   # clear of the PG band
        self.assertGreater(ys["k_v[2]"], ys["k_v[3]"])         # desc order
        self.assertLess(ys["kr_v[2]"], ys["kr_v[3]"])
        self.assertTrue(6.0 <= ys["k_v[3]"] and ys["k_v[2]"] <= 9.0)

    def test_refuses_more_pins_than_tracks(self):
        s = dict(SPEC, groups=[{"name": "in", "range_um": [6.0, 6.1], "bits": [["k_v", 0, 4]]}])
        with self.assertRaises(AssertionError):
            mod.transform(SRC, s)

    def test_refuses_spec_pin_missing_from_lef(self):
        s = dict(SPEC, groups=[{"name": "in", "range_um": [6.0, 9.0], "bits": [["k_v", 3, 6]]}])
        with self.assertRaises(AssertionError):
            mod.transform(SRC, s)


if __name__ == "__main__":
    unittest.main()
