"""E-W abutment of two bare faces needs no channel; any pin on a touching face keeps the 20 um rule."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import ref_tile as RT

LSL = 'physical/ref_tile/qfd_tile_lsl_fp1/views/ot_qwen_tile_lsl_fp1'   # every pin on the LEF E face (PG 2.16 um inside)
W = 99.792


def blk(x, orient):
    return {'view': LSL, 'x': x, 'y': 25.92, 'w': W, 'h': 140.4, 'orient': orient, 'kind': 'child'}


class AbuttedRow(unittest.TestCase):
    def gaps(self, a, b):
        gx = max(b['x'] - (a['x'] + a['w']), a['x'] - (b['x'] + b['w']))
        gy = max(b['y'] - (a['y'] + a['h']), a['y'] - (b['y'] + b['h']))
        return gx, gy

    def test_back_to_back_my_r0_abuts(self):
        a, b = blk(100.116, 'MY'), blk(100.116 + W, 'R0')     # MY puts the pins W, R0 puts them E: bare faces touch
        self.assertTrue(RT.abutted_row(a, b, *self.gaps(a, b)))
        self.assertTrue(RT.abutted_row(b, a, *self.gaps(b, a)))

    def test_pin_face_touching_keeps_channel(self):
        a, b = blk(100.116, 'R0'), blk(100.116 + W, 'R0')     # left block's E pin face touches
        self.assertFalse(RT.abutted_row(a, b, *self.gaps(a, b)))
        a, b = blk(100.116, 'MY'), blk(100.116 + W, 'MY')     # right block's (mirrored) pin face touches
        self.assertFalse(RT.abutted_row(a, b, *self.gaps(a, b)))

    def test_gap_or_rotation_keeps_channel(self):
        a, b = blk(100.116, 'MY'), blk(100.116 + W + 1.0, 'R0')
        self.assertFalse(RT.abutted_row(a, b, *self.gaps(a, b)))
        a, b = blk(100.116, 'R90'), blk(100.116 + W, 'R0')
        self.assertFalse(RT.abutted_row(a, b, *self.gaps(a, b)))

    def test_ns_stack_is_not_a_row(self):
        a = blk(100.116, 'MY'); b = dict(blk(100.116, 'R0'), y=25.92 + 140.4)
        self.assertFalse(RT.abutted_row(a, b, *self.gaps(a, b)))


if __name__ == '__main__':
    unittest.main()
