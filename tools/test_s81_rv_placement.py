#!/usr/bin/env python3
"""Physical regression: immutable landing dimensions and reserved payload corridors."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 's81_dv'))
from dv_rvcase import Placer, landing_footprint, reserve_lanes

class PlacementTests(unittest.TestCase):
    def test_closed_landing_never_uses_estimated_or_rotated_size(self):
        sizes = {'dsfd_dvland_276': (36.72, 51.84), 'dsfd_dvland_682': (41.04, 114.48)}
        for master in sizes:
            for face in 'SNEW':
                self.assertEqual(landing_footprint(master, sizes, 276, 2, face), sizes[master])

    def test_adjacent_landings_reserve_actual_bodies(self):
        placer = Placer(500, 500)
        w, h = landing_footprint('land', {'land': (36.72,51.84)}, 276, 2, 'W')
        x, y, _ = placer.put(100, 100, w, h)
        a, b, displacement = placer.put(100, 134, w, h)
        self.assertGreater(displacement, 0)
        self.assertFalse(a < x+w+.5 and x < a+w+.5 and b < y+h+.5 and y < b+h+.5)

    def test_reset_avoids_lane_between_sparse_stations(self):
        placer = Placer(500, 500)
        reserve_lanes(placer, {'data': {'bits': 276, 'hops': [[10,250,490,250,276]]}})
        x,y,_ = placer.put(240,240,17.28,17.28,step=4)
        self.assertTrue(y+17.28 <= 250-(276*.096/2+1.5)-.5 or y >= 250+(276*.096/2+1.5)+.5)

    def test_exact_edges_find_real_narrow_corridor_with_strict_reach(self):
        placer=Placer(500,500)
        placer.add((1.2,1.2,498.8,200.0))
        placer.add((1.2,218.8,498.8,498.8))
        x,y,d=placer.put(240,212.36,17.28,17.28,step=4,rmax=20,max_distance=20,exact_edges=True,origin_grid=(.048,.048,0,0))
        self.assertGreaterEqual(y,200.5)
        self.assertLessEqual(y+17.28,218.3)
        self.assertLessEqual(d,20)
        self.assertAlmostEqual(x/.048,round(x/.048))
        self.assertAlmostEqual(y/.048,round(y/.048))

    def test_exact_edges_do_not_relax_manhattan_distance_or_body_keepout(self):
        placer=Placer(100,100)
        placer.add((1.2,1.2,70,70))
        with self.assertRaises(ValueError):
            placer.put(50,50,10,10,rmax=30,max_distance=10,exact_edges=True)

    def test_continuous_only_pocket_refuses_off_grid_origin(self):
        placer=Placer(500,500)
        placer.add((1.2,1.2,498.8,200.007))
        placer.add((1.2,218.297,498.8,498.8))
        with self.assertRaises(ValueError):
            placer.put(240,212.36,17.28,17.28,step=4,rmax=20,max_distance=20,
                       exact_edges=True,origin_grid=(.048,.048,0,0))

    def test_impossible_placement_fails_instead_of_emitting_overlap(self):
        placer = Placer(100,100)
        placer.add((1.2,1.2,98.8,98.8))
        with self.assertRaises(ValueError):
            placer.put(40,40,10,10,rmax=20)

if __name__ == '__main__':
    unittest.main()
