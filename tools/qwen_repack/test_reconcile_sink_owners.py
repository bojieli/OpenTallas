"""Placement intervals preserve real row phase and exclusive fence boundaries."""
from pathlib import Path
import subprocess
import unittest

SOURCE = Path(__file__).with_name('reconcile_sink_owners.tcl').read_text()
DEFINITIONS = SOURCE.removesuffix('q4r::run\n')


class ReconcileIntervals(unittest.TestCase):
    def query(self, command):
        r = subprocess.run(['tclsh'], input=DEFINITIONS + '\nputs [' + command + ']\n',
                           text=True, capture_output=True, check=True)
        self.assertEqual(r.stderr, '')
        return r.stdout.strip()

    def test_row_lower_bound_keeps_all_fragments_at_same_height(self):
        rows = '{{0 0 100 10 2 R0} {10 0 40 20 2 MX} {10 60 100 20 2 MX} {20 0 100 30 2 R0}}'
        for y, wanted in [(-1, 0), (0, 0), (1, 1), (10, 1), (11, 3), (21, 4)]:
            with self.subTest(y=y):
                self.assertEqual(self.query(f'q4r::lower {rows} {y}'), str(wanted))

    def test_obstacles_cut_intervals_without_reintroducing_sites(self):
        self.assertEqual(self.query('q4r::cut {{0 20} {30 60}} 10 40'), '{0 10} {40 60}')
        self.assertEqual(self.query('q4r::cut {{0 20}} 0 20'), '')
        self.assertEqual(self.query('q4r::cut {{0 20}} 20 40'), '{0 20}')

    def test_sorted_occupancy_matches_independent_integer_site_set(self):
        import random
        rng = random.Random(1016)
        for _ in range(25):
            cuts = [sorted([rng.randrange(-10, 110), rng.randrange(-10, 110)]) for _ in range(12)]
            intervals = [(0, 30), (40, 70), (80, 100)]
            tclcuts = '{' + ' '.join('{%d %d}' % tuple(x) for x in cuts) + '}'
            result = self.query('q4r::subtract_sorted {{0 30} {40 70} {80 100}} ' + tclcuts)
            import re
            actual = set()
            for a, b in re.findall(r'\{(-?\d+) (-?\d+)\}', result):
                actual.update(range(int(a), int(b)))
            expected = {x for a, b in intervals for x in range(a, b)}
            for a, b in cuts:
                expected.difference_update(range(a, b))
            self.assertEqual(actual, expected)

    def test_owned_rows_require_full_height_inside_a_fence(self):
        self.assertEqual(self.query('q4r::allowed {10 0 100 20 2 MX} {{0 100}} {{20 10 60 20}} 0'), '{20 60}')
        self.assertEqual(self.query('q4r::allowed {10 0 100 20 2 MX} {{0 100}} {{20 11 60 20}} 0'), '')

    def test_shared_rows_exclude_every_intersecting_fence(self):
        self.assertEqual(self.query('q4r::allowed {10 0 100 20 2 MX} {{0 100}} {{20 5 40 15} {60 15 80 25}} 1'),
                         '{0 20} {40 60} {80 100}')

    def test_touching_fences_do_not_count_as_overlap(self):
        self.assertEqual(self.query('q4r::overlap {40 10 60 20} {{20 10 40 20}}'), '0')
        self.assertEqual(self.query('q4r::inside {20 10 40 20} {{20 10 40 20}}'), '1')
        self.assertEqual(self.query('q4r::inside {19 10 40 20} {{20 10 40 20}}'), '0')


if __name__ == '__main__':
    unittest.main()
