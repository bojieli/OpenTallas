"""--pin-lattice legalizer: actual c19b SU macro, site-incompatible group, collisions, edge-touching depth pins."""
import gzip
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from s81.pin_lattice_legalize import legalize, legal_origins, TRACKS  # noqa: E402


def _lef_rects(text, macro):
    rects, pin, lay, inm, obs, size = [], None, None, False, False, None
    for line in text.splitlines():
        t = line.replace(';', ' ').split()
        if not t:
            continue
        if t[0] == 'MACRO':
            inm = t[1] == macro
            continue
        if not inm:
            continue
        if t[0] == 'SIZE':
            size = (float(t[1]), float(t[3]))
        elif t[0] == 'PIN':
            pin = t[1]
        elif t[0] == 'OBS':
            obs = True
        elif t[0] == 'LAYER':
            lay = t[1]
        elif t[0] == 'RECT' and pin and not obs:
            rects.append((pin, lay, tuple(map(float, t[1:5]))))
        elif t[0] == 'END' and len(t) > 1 and t[1] == macro:
            break
    return size, rects


def _axes_ok(rects):
    for axis in (0, 1):
        lo, hi = (0, 2) if axis == 0 else (1, 3)
        pins = [(ly, round(r[lo] * 1000) + round(r[hi] * 1000)) for _, ly, r in rects
                if ly in TRACKS and TRACKS[ly][0] == axis]
        if pins and not legal_origins(pins, axis):
            return False
    return True


class PinLattice(unittest.TestCase):
    def test_actual_c19b_su(self):
        p = ROOT / 'results/physical/s81_repin_lattice_1417/actual_c19b_su.lef.gz'
        size, rects = _lef_rects(gzip.decompress(p.read_bytes()).decode(), 'dsfd_sp_su_c')
        self.assertFalse(_axes_ok(rects))
        out, rep = legalize('dsfd_sp_su_c', size[0], size[1], rects)
        self.assertTrue(_axes_ok(out))
        self.assertEqual(rep['moved'], 11)
        self.assertEqual(rep['max_move_nm'], 16)
        moved = {nm for (nm, _, a), (_, _, b) in zip(rects, out) if a != b}
        self.assertTrue(all(n.startswith(('c_done', 'c_st')) for n in moved))

    def test_site_incompatible_group_shifts_and_keeps_spacing(self):
        # all pins on one residue that no 270-nm row origin can serve (hr_W2 case): every pin moves, none collide
        rects = [(f'd[{i}]', 'M4', (0.0, 10.005 + 0.048 * i, 0.192, 10.029 + 0.048 * i)) for i in range(20)]
        self.assertFalse(_axes_ok(rects))
        out, rep = legalize('m', 5.0, 30.0, rects)
        self.assertTrue(_axes_ok(out))
        ys = sorted((r[1] + r[3]) / 2 for _, _, r in out)
        self.assertTrue(all(b - a >= 0.048 - 1e-9 for a, b in zip(ys, ys[1:])))
        self.assertLessEqual(rep['max_move_nm'], 24)

    def test_collision_takes_next_track(self):
        # minority pin 16 nm off a majority pin's neighbour track: the nearest legal track is occupied
        rects = [(f'a[{i}]', 'M4', (0.0, 1.0 + 0.048 * i, 0.192, 1.024 + 0.048 * i)) for i in range(5)]
        rects.append(('b[0]', 'M4', (0.0, 1.0 + 0.048 * 2 + 0.016, 0.192, 1.024 + 0.048 * 2 + 0.016)))
        out, rep = legalize('m', 5.0, 30.0, rects)
        self.assertTrue(_axes_ok(out))
        cs = [round((r[1] + r[3]) / 2, 3) for _, _, r in out]
        self.assertEqual(len(set(cs)), len(cs))
        self.assertGreater(rep['max_move_nm'], 16)

    def test_edge_touching_depth_pin_grows_inward(self):
        # N-face M4 pin: its y centre is its depth centre; the outline edge stays, the inner edge moves
        rects = [('c[0]', 'M4', (1.0, 0.0, 1.5, 0.024)), ('n[0]', 'M4', (2.0, 29.81, 2.5, 30.0))]
        out, rep = legalize('m', 5.0, 30.0, rects)
        self.assertTrue(_axes_ok(out))
        r = dict((nm, r) for nm, _, r in out)['n[0]']
        self.assertAlmostEqual(r[3], 30.0)

    def test_legal_master_untouched(self):
        rects = [(f'd[{i}]', 'M5', (0.588 + 0.048 * i, 0.0, 0.612 + 0.048 * i, 0.192)) for i in range(10)]
        out, rep = legalize('m', 5.0, 5.0, rects)
        self.assertEqual(rep['moved'], 0)
        self.assertEqual([r for _, _, r in out], [tuple(round(v, 3) for v in r) for _, _, r in rects])


if __name__ == '__main__':
    unittest.main()
