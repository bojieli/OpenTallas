"""DIE-S81-85 11-09 MOVES-SPLIT: OT_MACRO_MOVES rows written before a core split keep working as a rigid group move."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_phys as G  # noqa: E402


def _core(inst, x, y, w, h, off=(0.108, 0.012), orient="R0"):
    return {"inst": inst, "origin_um": [x, y], "outline_um": [w, h], "track_offset_um": list(off), "orient": orient}


# col_h9_r0_p1__t1 subset (plan 65648816 / af2abcca): u_e1 split into u_w + u_e, u_e abutted through offset 0.684.
TYPE = {"outline_um": [1442.88, 1226.88], "hard_cores": [
    _core("u_r0.u_e0.u_e", 285.12, 216.0, 268.38, 221.4, (0.684, 0.012)),
    _core("u_r0.u_e1.u_w", 578.88, 216.0, 268.38, 221.4),
    _core("u_r0.u_e1.u_e", 846.72, 216.0, 268.38, 221.4, (0.684, 0.012)),
    _core("u_r0.u_cf", 1131.84, 604.8, 280.8, 69.12),
    _core("u_r0.u_t0", 1140.48, 250.56, 84.24, 30.24),
]}
ROW = "u_r0.u_e1:596.16:216.0,u_r0.u_cf:1149.12:604.8,u_r0.u_t0:1157.76:250.56"


class MovesSplit(unittest.TestCase):
    def test_group_move_keeps_halves_abutted(self):
        m = G.macro_move_table(TYPE, "t", {"OT_MACRO_MOVES": ROW})
        self.assertEqual(sorted(m), ["u_r0.u_cf", "u_r0.u_e1.u_e", "u_r0.u_e1.u_w", "u_r0.u_t0"])
        self.assertEqual(m["u_r0.u_e1.u_w"]["to"], [596.16, 216.0])
        self.assertEqual(m["u_r0.u_e1.u_e"]["to"], [864.0, 216.0])
        # placed boxes shift by exactly the group delta (+17.28, 0): plan offsets kept
        self.assertAlmostEqual(m["u_r0.u_e1.u_w"]["x"], 578.88 + 0.108 + 17.28, places=6)
        self.assertAlmostEqual(m["u_r0.u_e1.u_e"]["x"], 846.72 + 0.684 + 17.28, places=6)

    def test_unknown_name_still_refused(self):
        with self.assertRaisesRegex(ValueError, "not inst:x:y"):
            G.macro_move_table(TYPE, "t", {"OT_MACRO_MOVES": "u_r0.u_e9:596.16:216.0"})
        with self.assertRaisesRegex(ValueError, "not inst:x:y"):  # prefix must end at a hierarchy dot
            G.macro_move_table(TYPE, "t", {"OT_MACRO_MOVES": "u_r0.u_e:596.16:216.0"})

    def test_group_orient_refused(self):
        with self.assertRaisesRegex(ValueError, "split core group"):
            G.macro_move_table(TYPE, "t", {"OT_MACRO_MOVES": "u_r0.u_e1:596.16:216.0:MY"})

    def test_group_overlap_and_outline_checked(self):
        with self.assertRaisesRegex(ValueError, "overlap"):  # group onto u_cf/u_t0 at plan sites
            G.macro_move_table(TYPE, "t", {"OT_MACRO_MOVES": "u_r0.u_e1:620.0:216.0"})
        with self.assertRaisesRegex(ValueError, "leaves the outline"):
            G.macro_move_table(TYPE, "t", {"OT_MACRO_MOVES": "u_r0.u_e1:1000.0:216.0"})

    def test_single_core_unchanged(self):
        m = G.macro_move_table(TYPE, "t", {"OT_MACRO_MOVES": "u_r0.u_t0:1157.76:250.56"})
        self.assertEqual(m["u_r0.u_t0"], {"inst": "u_r0.u_t0", "from": [1140.48, 250.56], "to": [1157.76, 250.56],
                                          "orient": "R0", "x": 1157.76 + 0.108, "y": 250.56 + 0.012})
        self.assertEqual(G.macro_move_table(TYPE, "t", {}), {})

    def test_reorient_takes_table_offset(self):
        m = G.macro_move_table(TYPE, "t", {"OT_MACRO_MOVES": "u_r0.u_e0.u_e:285.12:216.0:MY"})
        self.assertAlmostEqual(m["u_r0.u_e0.u_e"]["x"], 285.12 + 0.132, places=6)
        m = G.macro_move_table(TYPE, "t", {"OT_MACRO_MOVES": "u_r0.u_e0.u_e:285.12:216.0"})
        self.assertAlmostEqual(m["u_r0.u_e0.u_e"]["x"], 285.12 + 0.684, places=6)


if __name__ == "__main__":
    unittest.main()
