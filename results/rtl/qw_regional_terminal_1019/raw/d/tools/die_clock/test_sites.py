"""Exact placement regression against the pre-cache nearest-site search."""
import heapq
import random
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build import Sites, XPITCH, YPITCH

class Grid:
    nx = ny = 1000
    def free(self, p):
        return p not in {(2, 2), (2, 3), (3, 2)}

class Reference(Sites):
    def take(self, x0, y0):
        s = (min(self.nx - 1, max(0, round(x0 / XPITCH))), min(self.ny - 1, max(0, round(y0 / YPITCH))))
        q, seen = [(0.0, s)], {s}
        while q:
            _, (ix, iy) = heapq.heappop(q)
            if self.legal(ix, iy):
                self.occ.add((ix, iy))
                return round(ix * XPITCH, 3), round(iy * YPITCH, 3)
            for n in ((ix - 1, iy), (ix + 1, iy), (ix, iy - 1), (ix, iy + 1)):
                if 0 <= n[0] < self.nx and 0 <= n[1] < self.ny and n not in seen:
                    seen.add(n)
                    heapq.heappush(q, (abs(n[0] * XPITCH - x0) + abs(n[1] * YPITCH - y0), n))
        raise ValueError('no legal clock site')

def compare(origins, W=160, H=100, taken=()):
    old, new = Reference(Grid(), W, H, taken), Sites(Grid(), W, H, taken)
    for i, xy in enumerate(origins):
        assert old.take(*xy) == new.take(*xy), (i, xy)
        assert old.occ == new.occ
    return old, new

def test_repeated_leaf_pads():
    compare([(80.11, 50.09)] * 500, taken={(49, 185), (50, 185)})

def test_interleaved_origins_and_obstacles():
    r = random.Random(123)
    origins = []
    for _ in range(25):
        xy = r.choice([(30.1, 30.1), (0, 0), (160, 100), (80.11, 50.09)])
        origins.extend([xy] * r.randint(1, 12))
    compare(origins)

def test_external_occupancy_and_corner_exhaustion():
    old, new = compare([(0, 0)] * 4, W=6.48, H=1.08)
    # Another allocator may occupy an unvisited frontier site between calls.
    old.occ.add((2, 0)); new.occ.add((2, 0))
    while True:
        try:
            p = old.take(0, 0)
        except ValueError:
            try:
                new.take(0, 0)
            except ValueError:
                break
            raise AssertionError('cache allocated an exhausted site')
        assert new.take(0, 0) == p

def test_negative_control_obstacle_and_occupancy_matter():
    _, new = compare([(30.1, 30.1)] * 20)
    assert not new.legal(*next(iter(new.occ)))
    assert not new.legal(13, 80)  # inside a blocked 10-um grid square

def test_negative_control_lost_successful_frontier_is_detected():
    import inspect
    import build
    source = inspect.getsource(build.Sites)
    source = source.replace('            available = self.legal(ix, iy)',
        '            available = self.legal(ix, iy)\n'
        '            if available:\n'
        '                self.occ.add((ix, iy))\n'
        '                return round(ix * XPITCH, 3), round(iy * YPITCH, 3)')
    scope = dict(build.__dict__)
    exec(source, scope)
    broken = scope['Sites'](Grid(), 160, 100, ())
    old = Reference(Grid(), 160, 100, ())
    # Without expanding a successful pop, the saved frontier can exhaust or
    # skip the next closest site. The sequence oracle must reject that mutant.
    try:
        for _ in range(20):
            assert broken.take(80.11, 50.09) == old.take(80.11, 50.09)
    except (AssertionError, ValueError):
        return
    raise AssertionError('lost-frontier mutant escaped the sequence oracle')

if __name__ == '__main__':
    import time
    tests = [v for k, v in list(globals().items()) if k.startswith('test_')]
    for f in tests:
        f()
        print(f.__name__, 'PASS', flush=True)
    xy = (80.11, 50.09)
    for cls in (Reference, Sites):
        s = cls(Grid(), 160, 100, ())
        t = time.perf_counter()
        seq = [s.take(*xy) for _ in range(500)]
        print(cls.__name__, '500 pads seconds', round(time.perf_counter() - t, 6), flush=True)
