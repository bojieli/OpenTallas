"""bare_face(): a hard macro face with no pin within 200 nm needs no core-edge channel (S81-TILES5 10-17, s81sl_vq)."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import ref_tile as RT

# synthetic macro track (nm): 10 x 8 um, one signal pin on the E face, one PG stripe 2 um inside the N face
TM = {"W": 10000, "H": 8000, "pins": [
    {"rects": [("M4", (9800, 3000, 10000, 3100))]},
    {"rects": [("M5", (4000, 0, 4100, 5800))]},     # touches the S face (y0 = 0), not the N face
]}


def mac(orient="R0", kind="macro"):
    return {"view": "synthetic", "orient": orient, "kind": kind, "_tm": TM}


class BareFace(unittest.TestCase):
    def test_r0_faces(self):
        b = mac()
        self.assertTrue(RT.bare_face(b, "W"))
        self.assertTrue(RT.bare_face(b, "N"))
        self.assertFalse(RT.bare_face(b, "E"))      # signal pin
        self.assertFalse(RT.bare_face(b, "S"))      # PG stripe reaches the face

    def test_mirrors_swap_faces(self):
        self.assertTrue(RT.bare_face(mac("MY"), "E"))
        self.assertFalse(RT.bare_face(mac("MY"), "W"))
        self.assertTrue(RT.bare_face(mac("MX"), "S"))
        self.assertFalse(RT.bare_face(mac("MX"), "N"))
        self.assertTrue(RT.bare_face(mac("R180"), "E"))
        self.assertTrue(RT.bare_face(mac("R180"), "S"))
        self.assertFalse(RT.bare_face(mac("R180"), "W"))
        self.assertFalse(RT.bare_face(mac("R180"), "N"))

    def test_children_and_rotations_keep_channel(self):
        self.assertFalse(RT.bare_face(mac(kind="child"), "W"))
        self.assertFalse(RT.bare_face(mac("R90"), "W"))

    def test_unreadable_view_keeps_channel(self):
        self.assertFalse(RT.bare_face({"view": "/nonexistent/view", "orient": "R0"}, "W"))


if __name__ == '__main__':
    unittest.main()
