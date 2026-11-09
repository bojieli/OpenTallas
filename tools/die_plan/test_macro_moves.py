"""S81-TYPES-3: OT_MACRO_MOVES is off by default, moves named hard cores in the table only, and refuses bad input."""
import copy
import unittest

import gen_phys as G

T = {"outline_um": [100.0, 100.0], "hard_cores": [
    {"inst": "u.a", "physical_inst": "u_bound.u_a", "origin_um": [10.0, 10.0], "outline_um": [10.0, 10.0], "orient": "MY",
     "track_offset_um": [0.132, 0.012]},
    {"inst": "u.b", "origin_um": [50.0, 50.0], "outline_um": [10.0, 10.0], "orient": "R0",
     "track_offset_um": [0.108, 0.012]}]}


class MacroMoves(unittest.TestCase):
    def test_off(self):
        self.assertEqual(G.macro_move_table(copy.deepcopy(T), "t", {}), {})

    def test_move_keeps_plan(self):
        t = copy.deepcopy(T)
        m = G.macro_move_table(t, "t", {"OT_MACRO_MOVES": "u.a:20:30:R0,u.b:60:70"})
        self.assertEqual(t, T)
        self.assertAlmostEqual(m["u_bound.u_a"]["x"], 20.108)
        self.assertEqual(m["u_bound.u_a"]["orient"], "R0")
        self.assertAlmostEqual(m["u.b"]["y"], 70.012)
        self.assertEqual(m["u.b"]["orient"], "R0")

    def test_placed_boxes_abut_through_track_offset(self):
        # origins overlap by 0.888 but the plan's track offsets make the placed edges equal (S81 bf_col3 c / bf16 half)
        t = {"outline_um": [2000.0, 2000.0], "hard_cores": [
            {"inst": "c", "origin_um": [691.2, 950.4], "outline_um": [208.248, 198.72], "orient": "MY",
             "track_offset_um": [0.108, 0.012]},
            {"inst": "ha", "origin_um": [898.56, 950.4], "outline_um": [241.92, 95.04], "orient": "MY",
             "track_offset_um": [0.996, 0.012]},
            {"inst": "m", "origin_um": [10.0, 10.0], "outline_um": [10.0, 10.0], "orient": "R0",
             "track_offset_um": [0.108, 0.012]}]}
        self.assertIn("m", G.macro_move_table(t, "t", {"OT_MACRO_MOVES": "m:30:30"}))

    def test_real_overlap_of_placed_boxes_still_refused(self):
        t = {"outline_um": [100.0, 100.0], "hard_cores": [
            {"inst": "a", "origin_um": [10.0, 10.0], "outline_um": [10.0, 10.0], "orient": "R0",
             "track_offset_um": [0.1, 0.0]},
            {"inst": "b", "origin_um": [20.0, 10.0], "outline_um": [10.0, 10.0], "orient": "R0",
             "track_offset_um": [0.0, 0.0]},
            {"inst": "m", "origin_um": [50.0, 50.0], "outline_um": [10.0, 10.0], "orient": "R0",
             "track_offset_um": [0.108, 0.012]}]}
        with self.assertRaises(ValueError):
            G.macro_move_table(t, "t", {"OT_MACRO_MOVES": "m:30:30"})

    def test_refuses(self):
        for bad in ("u.c:1:1", "u.a:95:1", "u.a:50:50", "u.a:1:1:XX", "u.a:1"):
            with self.assertRaises(ValueError):
                G.macro_move_table(copy.deepcopy(T), "t", {"OT_MACRO_MOVES": bad})


if __name__ == "__main__":
    unittest.main()
