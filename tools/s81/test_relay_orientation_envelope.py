#!/usr/bin/env python3
"""Exercise real S81 LEF pins after late relay face selection (bind16 regression)."""
import math
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import dsrom_s81_fulldie as G

# Widths selected in source f859775f1 bind16_x2pair construction_pass0_plan.
BIND16_WIDTHS = (1, 2, 15, 38, 54, 63, 66, 266, 283, 536)


class RelayEnvelopeTest(unittest.TestCase):
    def master(self, bits, faces, dims, k):
        name = f'dsfd_rly_{bits}_{faces}'
        master = G.Q.Master(name, *dims, 3, 'relay orientation regression')
        inst = SimpleNamespace(name='relay', master=name, kind='rly')
        ports = {'i': ('input', bits), 'o': ('output', bits),
                 'ck': ('input', 1), 'rs': ('input', 1)}
        with patch.dict(G.RLY_FACES, {name: tuple(faces)}), patch.object(G, '_LAY_K', [k]):
            G._faces_r8({}, master, inst, ports)
        widths = {p: max(1, math.ceil(w / k)) for p, (_, w) in ports.items()}
        return master, widths

    def test_every_face_fits_actual_full_width_and_bundled_lef(self):
        # Test the superset of selected bind16 faces: all straight and corner
        # choices for each width, both initial search directions and view scales.
        for real in (False, True):
            with patch.object(G, 'RLY_REAL_DIMS', real):
                for bits in BIND16_WIDTHS:
                    for horiz in (False, True):
                        dims = G.relay_dims(bits, horiz)
                        for fi in 'NSEW':
                            for fo in 'NSEW':
                                if fi == fo:
                                    continue
                                for k in (1, 16):
                                    with self.subTest(bits=bits, faces=fi+fo, k=k, real=real, horiz=horiz):
                                        master, widths = self.master(bits, fi+fo, dims, k)
                                        text, count = G.lef_text(master, k, widths)
                                        self.assertEqual(count, 2 * max(1, math.ceil(bits / k)) + 2)
                                        self.assertIn(f'MACRO {master.name}', text)
                                        for name, layer, (x0, y0, x1, y1) in G.pin_rects(master, k, widths):
                                            self.assertGreaterEqual(x0, -1e-6, name)
                                            self.assertGreaterEqual(y0, -1e-6, name)
                                            self.assertLessEqual(x1, master.w + 1e-6, name)
                                            self.assertLessEqual(y1, master.h + 1e-6, name)

    def test_native_wide_envelope_stands(self):
        with patch.object(G, 'RLY_REAL_DIMS', True):
            for bits in (266, 283):
                for horiz in (False, True):
                    self.assertEqual(G.relay_dims(bits, horiz), (34.56, 30.24))

    def test_original_536_sn_failure_is_detected(self):
        master, widths = self.master(536, 'SN', G.stn_dims([536], True), 1)
        with self.assertRaisesRegex(ValueError, '536 pins.*do not fit.*S'):
            G.lef_text(master, 1, widths)


if __name__ == '__main__':
    unittest.main()
