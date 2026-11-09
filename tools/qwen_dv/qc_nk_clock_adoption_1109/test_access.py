"""Bounded source-witness controls for the NK clock-pin event; no routed DRC or parent sign-off claim."""
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[3]
ART = ROOT / 'results/physical/qc_nk_clock_adoption_1109'
POR = ROOT / 'physical/die_plan/qwen_compute/plan_of_record'
s = importlib.util.spec_from_file_location('prepare_access', Path(__file__).with_name('prepare_access.py'))
A = importlib.util.module_from_spec(s); s.loader.exec_module(A)
ROI = json.loads((ART / 'native_roi.json').read_text())
ADO = json.loads((ART / 'access_v1/adoption.json').read_text())
ACC = (ART / 'access_v1/qfd_tile_nk_a0c.access.lef').read_text()
BLANKET = '     RECT  0 4.297 457.92 1153.463 ;'


def original_from_access(text):
    """undo exactly the two OBS splits: the four pieces of M6 and of M7 collapse back to the blanket line."""
    out, skip = [], 0
    for line in text.splitlines():
        if skip:
            skip -= 1; continue
        if line.startswith('      RECT 0.000000 4.297000 '):
            out.append(BLANKET); skip = 3; continue
        out.append(line)
    return '\n'.join(out) + '\n'


class Windows(unittest.TestCase):
    def test_windows_reproduce_from_native_roi(self):
        w, _ = A.derive_windows(ROI)
        self.assertEqual({f'M{k}': list(v) for k, v in w.items()}, ADO['native_obs_windows_child_um'])

    def test_windows_hold_no_native_shape(self):
        w, _ = A.derive_windows(ROI)
        for sh in ROI['shapes']:
            L = int(sh['layer'][1:]) if re.fullmatch(r'M\d', sh['layer']) else None
            if L in w and sh['kind'] != 'bterm':
                self.assertFalse(A.overlaps(tuple(v / 1000 for v in sh['bbox']), w[L]), sh)

    def test_pin_centre_m7_track_is_foreign(self):
        # the parent M7 track over the pin centre (child x 228.960) sits on the foreign NK M7 net15753
        fp = (228.944, 578.496, 228.976, 579.264)
        hit = [sh['net'] for sh in ROI['shapes'] if sh['layer'] == 'M7' and sh['net'] != 'ck'
               and A.overlaps(tuple(v / 1000 for v in sh['bbox']), fp)]
        self.assertEqual(hit, ['net15753'])

    def test_footprint_on_native_shape_rejected(self):
        old = A.FP_CHILD[7]
        try:
            A.FP_CHILD[7] = [(228.944, 578.496, 228.976, 579.264)]
            with self.assertRaises(ValueError): A.derive_windows(ROI)
        finally:
            A.FP_CHILD[7] = old


class Lef(unittest.TestCase):
    def test_only_two_obs_rects_split(self):
        orig = original_from_access(ACC)
        self.assertEqual(hashlib.sha256(orig.encode()).hexdigest(), ADO['original_lef_sha256'])
        self.assertEqual(hashlib.sha256(ACC.encode()).hexdigest(), ADO['access_lef_sha256'])
        w, _ = A.derive_windows(ROI)
        self.assertEqual(A.abstract(orig, w), ACC)


class Event(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = json.loads((POR / 'plan_qc53v4nS_mem9_vml_nkck.json').read_text())
        cls.orig = original_from_access(ACC)

    def test_every_nk_core_enters_on_tracks(self):
        n = 0
        for tn, t in self.plan['partition_types'].items():
            taps = {x['name']: x for x in (t.get('clock') or {}).get('taps', [])}
            for c in t.get('hard_cores', []):
                if c.get('module') != A.MASTER: continue
                n += 1
                acc = c['clock_entry_access']; fp = {int(k[1:]): v for k, v in acc['footprints_um'].items()}
                site = (round(c['origin_um'][0] + c['track_offset_um'][0], 6), round(c['origin_um'][1] + c['track_offset_um'][1], 6), c['orient'])
                x, y = taps[c['inst'] + '.ck']['xy']
                box = (x - .016, y - .384, x + .016, y + .384)
                self.assertTrue(A.G.validate_access(ACC, A.MASTER, acc, 7, site, box))
                b, tg, _ = A.G.geometry(self.orig, A.MASTER, 'ck', 7, site)
                self.assertFalse(A.G.entry_clear(fp, b, tg, 7))
                self.assertTrue(A.on_track(x, 'M7') and A.on_track((fp[5][0][0] + fp[5][0][2]) / 2, 'M5')
                                and A.on_track((fp[6][0][1] + fp[6][0][3]) / 2, 'M6'))
                self.assertTrue(fp[5][0][1] <= y <= fp[5][0][3])
                self.assertEqual(c['pins_file'], A.NEW_PINS)
                self.assertEqual((taps[c['inst'] + '.ck']['insertion_ps'], taps[c['inst'] + '.ck']['insertion_ff_ps']), (733.25, 586.0))
        self.assertEqual(n, 62)

    def test_pin_table_one_row(self):
        a = json.loads((POR / 'cores/a0_nk_pins.json').read_text()); b = json.loads((POR / A.NEW_PINS).read_text())
        d = [(x, y) for x, y in zip(a['pins'], b['pins']) if x != y]
        self.assertEqual(d, [({'name': 'ck', 'layer': 'M4', 'x': 457.824, 'y': 668.076}, {'name': 'ck', 'layer': 'M5', 'x': 228.972, 'y': 578.88})])


if __name__ == '__main__':
    unittest.main()
