"""The clock search keeps shortest paths and every blocked-span constraint."""
import random
import unittest
from collections import deque

from die_clock_tree import GRID, Grid


def bfs(grid, a, b, bound):
    q = deque([(a, 0, 0)])
    seen = {(a, 0)}
    while q:
        c, run, length = q.popleft()
        if c == b:
            return length
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = c[0] + dx, c[1] + dy
            if not (0 <= n[0] < grid.nx and 0 <= n[1] < grid.ny):
                continue
            nr = 0 if grid.free(n) else run + 1
            if nr <= bound and (n, nr) not in seen:
                seen.add((n, nr))
                q.append((n, nr, length + 1))
    return None


class ClockSearchTest(unittest.TestCase):
    def test_exact_shortest_paths_against_exhaustive_state_bfs(self):
        rng = random.Random(2330)
        cases = 0
        for _ in range(180):
            grid = Grid(8 * GRID, 8 * GRID, [])
            for i in range(len(grid.blk)):
                grid.blk[i] = int(rng.random() < .58)
            a, b = (rng.randrange(8), rng.randrange(8)), (rng.randrange(8), rng.randrange(8))
            grid.blk[a[1] * 8 + a[0]] = 0
            grid.blk[b[1] * 8 + b[0]] = 0
            for bound in (1, 2, 3, 5):
                expected = bfs(grid, a, b, bound)
                if expected is None:
                    with self.assertRaises(SystemExit):
                        grid._route(a, b, bound * GRID)
                else:
                    path = grid._route(a, b, bound * GRID)
                    self.assertEqual((path[0], path[-1], len(path) - 1), (a, b, expected))
                    run = 0
                    for p, n in zip(path, path[1:]):
                        self.assertEqual(abs(p[0] - n[0]) + abs(p[1] - n[1]), 1)
                        run = 0 if grid.free(n) else run + 1
                        self.assertLessEqual(run, bound)
                cases += 1
        self.assertEqual(cases, 720)


if __name__ == '__main__':
    unittest.main()
