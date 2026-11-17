import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("phy_pin_track_form", Path(__file__).with_name("phy_pin_track_form.py"))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def pin(name, layer, x0, x1):
    return (f"  PIN {name}\n    DIRECTION INPUT ;\n    USE SIGNAL ;\n    PORT\n"
            f"      LAYER {layer} ;\n      RECT {x0:.3f} 0.800 {x1:.3f} 0.992 ;\n"
            f"    END\n  END {name}\n")


class TrackForm(unittest.TestCase):
    def test_mixed_original_phases_need_different_moves(self):
        src = ("MACRO phy\n  SIZE 1.000 BY 1.000 ;\n" + pin("clk", "M5", 0, .024)
               + pin("k_v[0]", "M5", .120, .144) + pin("k_v[1]", "M7", .196, .228) + "END phy\n")
        out, receipt = mod.transform(src, (0, 0))
        moves = {r["pin"]: r["centre_shift_nm"] for r in receipt["changes"]}
        self.assertEqual(moves, {"clk": 12, "k_v[0]": -12, "k_v[1]": 12})
        self.assertEqual(receipt["minimum_same_layer_clearance_nm"]["M5"], 72)
        self.assertIn("RECT 0.108 0.800 0.132 0.992", out)
        self.assertIn("RECT 0.208 0.800 0.240 0.992", out)
        self.assertEqual(receipt["added_pin_metal_area_um2"], 0)

    def test_refuses_pin_move_that_creates_a_short(self):
        src = ("MACRO phy\n  SIZE 1.000 BY 1.000 ;\n" + pin("clk", "M5", 0, .024)
               + pin("bad", "M5", .024, .048) + "END phy\n")
        with self.assertRaises(AssertionError):
            mod.transform(src, (0, 0))


if __name__ == "__main__":
    unittest.main()
