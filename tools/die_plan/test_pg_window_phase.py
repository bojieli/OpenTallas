"""Global PG phase and retained-PHY finite-pad guards; no physical solve."""
import copy
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import die_trial as D
import infra_pg as G
import pg_regions as R


def centres(row, origin, length=200):
    """Independent enumeration of fully-contained global lattice stripes."""
    p, off, w = map(R._d, (row['pitch_um'], row['offset_um'], row['width_um']))
    origin, length = R._d(origin), R._d(length)
    nets = row.get('nets', ['VDD', 'VSS'])
    return {(off+i*(p//2)-origin, nets[i % 2]) for i in range(-10000, 10000)
            if 2*origin+w <= 2*(off+i*(p//2)) <= 2*(origin+length)-w}


def emitted(row, length=200):
    sp = R.row_spec(row, [0, 0, R._d(length), R._d(length)], ['VDD', 'VSS'])
    if sp is None:
        return set()
    out, c, i = set(), sp['offset'], 0
    while 2*c+sp['w'] <= 2*R._d(length):
        out.add((c, sp['start'] if i % 2 == 0 else sp['other']))
        c += sp['half']
        i += 1
    return out


GRID = [dict(layer='M8', width_um=.48, pitch_um=4.32, offset_um=2.16, nets=['VDD', 'VSS']),
        dict(layer='M9', width_um=12.96, pitch_um=39.96, offset_um=13.77, nets=['VDD', 'VSS'])]


class Phase(unittest.TestCase):
    def test_five_global_coordinate_and_net_controls(self):
        for row, origin in [(GRID[0], 6433.56), (GRID[1], 6433.56),
                            (GRID[0], 6432), (GRID[1], 6420), (GRID[1], 0)]:
            with self.subTest(layer=row['layer'], origin=origin):
                local = G.window_grid([row], origin, origin)[0]
                self.assertEqual(emitted(local), centres(row, origin))

    def test_independent_directions_dbu_and_source_unchanged(self):
        original = copy.deepcopy(GRID)
        local = G.window_grid(GRID, 6433.56, 6432)
        self.assertEqual(local[0]['offset_um'], 2.64)
        self.assertEqual(local[1]['offset_um'], 13.77)
        self.assertEqual(GRID, original)
        # The first complete M8 stripe in this crop is ground, not power.
        sp = R.row_spec(local[0], [0, 0, 200000, 200000], ['VDD', 'VSS'])
        self.assertEqual(sp['start'], 'VSS')

    def test_wrong_phase_and_wrong_net_mutants_are_caught(self):
        row = GRID[0]
        local = G.window_grid([row], 6433.56, 6433.56)[0]
        expected = centres(row, 6433.56)
        self.assertEqual(emitted(local), expected)
        self.assertNotEqual(emitted(row), expected)  # former crop-reset behavior
        self.assertNotEqual(emitted(dict(local, nets=['VSS', 'VDD'])), expected)

    def test_commensurate_grids_emit_identical_pdn(self):
        for pitches, widths in [((8.64, 8.64), (.48, .48)),
                                 ((4.32, 34.56), (.48, 12.96))]:
            grid = [dict(layer=L, width_um=w, pitch_um=p, offset_um=p/2, nets=['VDD', 'VSS'])
                    for L, p, w in zip(('M8', 'M9'), pitches, widths)]
            p = SimpleNamespace(die={'pg': {'grid': grid}}, W=10000, H=10000)
            local = G.window_grid(grid, 6462.72, 6462.72)
            self.assertEqual(D.psm_pdn_tcl(G._PG(p, grid)), D.psm_pdn_tcl(G._PG(p, local)))

    def window(self, out, io, core, **kwargs):
        p = SimpleNamespace(name='probe', W=10000, H=10000, die={'pg': {'grid': GRID}}, parts={})
        pg = dict(grid=GRID, regions=[], core_w_mm2=1., budget_mv=35,
                  bump_contract=dict(pitch_um=150., pad_um=70.))
        model = dict(loads=[([0, 0, 10000, 10000], 1.)], regions=[], core_parts=[], rects={})
        seen = []
        def bump_grid(global_plan, windows, pitch=None):
            seen.append((global_plan.W, global_plan.H, copy.deepcopy(global_plan.die['pg']['grid'])))
            return core
        with patch.object(G, 'load_model', return_value=model), patch.object(G, '_pg_io', return_value=io), \
                patch.object(G, 'estimate', return_value=({}, 0., {})), \
                patch.object(D, 'coarse_tracks', return_value=''), patch.object(D, 'bump_grid', side_effect=bump_grid):
            m = G.window_kit(p, Path(out), pg, Path(out)/'kit', 'probe', [100, 100, 220, 220], tile=43.2, **kwargs)
        return m, seen

    def test_window_preserves_global_sources_and_translates_pdn(self):
        # The IO rectangle overlaps the crop, but all its actual micro-bumps
        # are outside it. A broad region-overlap rejection would be wrong.
        io = [dict(name='phy', iface='serdes', rect_um=[195, 195, 300, 300])]
        with tempfile.TemporaryDirectory() as tmp:
            m, seen = self.window(tmp, io, [('VDD', 150., 150.)])
            self.assertEqual(seen, [(10000, 10000, GRID)])
            self.assertEqual(m['grid'], GRID)
            self.assertEqual(m['window_grid'][0]['offset_um'], 0.)
            text = (Path(tmp)/'kit/psm/pdn.tcl').read_text()
            self.assertIn('-layer M8 -width 0.48 -pitch 4.32 -offset 2.16 -spacing 1.68 -starts_with GROUND', text)
            self.assertIn('pad_fallback', (Path(tmp)/'kit/psm/bumps.tcl').read_text())

    def test_retained_phy_rejects_uniform_finite_c4_pad(self):
        io = [dict(name='phy', iface='serdes', rect_um=[100, 100, 200, 200])]
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, 'typed PHY pad contract'):
                self.window(tmp, io, [])
            self.assertFalse((Path(tmp)/'kit/psm/psm.tcl').exists())

    def test_phy_guard_legacy_point_and_exact_sources(self):
        io = [dict(name='phy', iface='serdes', rect_um=[100, 100, 200, 200])]
        actual = G._phy_lattice(io[0]['rect_um'], G.phy_pg_pitch('serdes'))[1]
        G.require_typed_phy_pad(actual, io, 0.)
        G.require_typed_phy_pad([('VDD', 12., 12.)], io, 70.)
        with self.assertRaisesRegex(ValueError, 'typed PHY pad contract'):
            G.require_typed_phy_pad(actual, io, 70.)

    def test_die_kit_rejects_actual_phy_sources_before_emission(self):
        io = [dict(name='phy', iface='serdes', rect_um=[100, 100, 200, 200])]
        p = SimpleNamespace(name='probe', W=1000, H=1000, die={'pg': {'grid': GRID}}, parts={})
        pg = dict(grid=GRID, part_w={}, regions=[], bump_contract=dict(pitch_um=150., pad_um=70.))
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)/'kit'
            (out/'abstracts').mkdir(parents=True)
            with patch.object(G, '_pg_io', return_value=io), patch.object(D, 'bump_grid', return_value=[]):
                with self.assertRaisesRegex(ValueError, 'typed PHY pad contract'):
                    G.die_kit(p, out, pg, out, out)
            self.assertFalse((out/'psm/pdn.tcl').exists())


if __name__ == '__main__':
    unittest.main()
