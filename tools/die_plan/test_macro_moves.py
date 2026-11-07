"""S81-TYPES-2: OT_MACRO_MOVES is off by default, moves named hard cores, mirrors with the track offset of the orient."""
import copy
import unittest

import gen_phys as G

T = {"outline_um": [100.0, 100.0], "hard_cores": [
    {"inst": "u.a", "origin_um": [10.0, 10.0], "outline_um": [10.0, 10.0], "orient": "MY", "track_offset_um": [0.132, 0.012]},
    {"inst": "u.b", "origin_um": [50.0, 50.0], "outline_um": [10.0, 10.0], "orient": "R0", "track_offset_um": [0.108, 0.012]}]}


class MacroMoves(unittest.TestCase):
    def test_off(self):
        t = copy.deepcopy(T)
        self.assertEqual(G.apply_macro_moves(t, "x", {}), [])
        self.assertEqual(t, T)

    def test_move_flip(self):
        t = copy.deepcopy(T)
        r = G.apply_macro_moves(t, "x", {"OT_MACRO_MOVES": "u.a:20:30:R0,u.b:60:60"})
        self.assertEqual(len(r), 2)
        a, b = t["hard_cores"]
        self.assertEqual((a["origin_um"], a["orient"], a["track_offset_um"]), ([20.0, 30.0], "R0", [0.108, 0.012]))
        self.assertEqual((b["origin_um"], b["orient"], b["track_offset_um"]), ([60.0, 60.0], "R0", [0.108, 0.012]))

    def test_refuse(self):
        for bad in ("u.c:1:1", "u.a:95:1", "u.a:50:50", "u.a:1:1:R7", "u.a:1"):
            with self.assertRaises(ValueError):
                G.apply_macro_moves(copy.deepcopy(T), "x", {"OT_MACRO_MOVES": bad})


if __name__ == "__main__":
    unittest.main()
