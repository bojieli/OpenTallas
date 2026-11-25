"""BIND-SPEED-1124 #2: reset_tree._route's per-row / per-column edge test returns exactly the paths of the original
per-edge _seg_hits scan (the reference below is the original function, verbatim)"""
import heapq
import random
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reset_tree as RT  # noqa: E402
from reset_tree import _man, _seg_hits  # noqa: E402,F401

def _route_ref(a, b, boxes, box_out, cap=250000, faces=None):
    """shortest rectilinear path a -> b outside the interior of every box (Hanan grid of the box faces, `faces` when
    given; ties: fewer bends), collinear points merged.  None when no path exists or the grid exceeds `cap` points."""
    fb = boxes if faces is None else faces
    xs = sorted({a[0], b[0]} | {v for bx in fb for v in (bx[0], bx[2])} | ({box_out[0], box_out[2]} if box_out else set()))
    ys = sorted({a[1], b[1]} | {v for bx in fb for v in (bx[1], bx[3])} | ({box_out[1], box_out[3]} if box_out else set()))
    if box_out:
        xs = [x for x in xs if box_out[0] - 1e-9 <= x <= box_out[2] + 1e-9]
        ys = [y for y in ys if box_out[1] - 1e-9 <= y <= box_out[3] + 1e-9]
    if len(xs) * len(ys) > cap:
        return None
    xi, yi = {x: i for i, x in enumerate(xs)}, {y: j for j, y in enumerate(ys)}
    if a[0] not in xi or a[1] not in yi or b[0] not in xi or b[1] not in yi:
        return None
    s0, t0 = (xi[a[0]], yi[a[1]]), (xi[b[0]], yi[b[1]])
    dist = {(s0, -1): (0.0, 0)}
    prev = {}
    pq = [(0.0, 0, s0, -1)]
    while pq:
        d, nb, u, dr = heapq.heappop(pq)
        if dist.get((u, dr), (1e30, 0)) < (d, nb):
            continue
        if u == t0:
            path, k = [], (u, dr)
            while k in prev or k[0] == s0:
                path.append((xs[k[0][0]], ys[k[0][1]]))
                if k not in prev:
                    break
                k = prev[k]
            path = path[::-1]
            out = [path[0]]
            for k2, pt in enumerate(path[1:], 1):
                if pt == out[-1]:
                    continue
                if (len(out) >= 2 and k2 < len(path) and
                        ((out[-2][0] == out[-1][0] == pt[0]) or (out[-2][1] == out[-1][1] == pt[1]))):
                    out[-1] = pt                         # collinear: extend the segment
                else:
                    out.append(pt)
            return out
        for nd, (di, dj) in enumerate(((1, 0), (-1, 0), (0, 1), (0, -1))):
            v = (u[0] + di, u[1] + dj)
            if not (0 <= v[0] < len(xs) and 0 <= v[1] < len(ys)):
                continue
            p, q = (xs[u[0]], ys[u[1]]), (xs[v[0]], ys[v[1]])
            if _seg_hits(p, q, boxes):
                continue
            c = (d + _man(p, q), nb + (dr >= 0 and dr // 2 != nd // 2))
            if c < dist.get((v, nd), (1e30, 0)):
                dist[(v, nd)] = c
                prev[(v, nd)] = (u, dr)
                heapq.heappush(pq, (c[0], c[1], v, nd))
    return None



def _case(rng, nb, grid):
    pick = (lambda: rng.randrange(grid)) if grid else (lambda: round(rng.uniform(0, 400), 3))
    boxes = []
    for _ in range(nb):
        x0, y0 = pick(), pick()
        boxes.append((x0, y0, x0 + 1 + abs(pick()) / 4, y0 + 1 + abs(pick()) / 4))
    return boxes, (pick(), pick()), (pick(), pick())


@pytest.mark.parametrize("seed", range(60))
def test_route_equals_original(seed):
    rng = random.Random(seed)
    boxes, a, b = _case(rng, rng.randrange(0, 40), 50 if seed % 2 else 0)
    box_out = (min(a[0], b[0]) - 30, min(a[1], b[1]) - 30, max(a[0], b[0]) + 30, max(a[1], b[1]) + 30) if seed % 3 == 0 else None
    faces = boxes[: len(boxes) // 2] + [(a[0] - 5, a[1] - 5, a[0] + 5, a[1] + 5)] if seed % 4 == 1 else None
    for cap in (250000, 200):
        assert RT._route(a, b, boxes, box_out, cap=cap, faces=faces) == _route_ref(a, b, boxes, box_out, cap=cap, faces=faces)


def test_route_touching_and_degenerate_boxes():
    boxes = [(10, 0, 20, 10), (20, 0, 30, 10), (10, 10, 20, 20), (15, 15, 15, 30), (0, 5, 40, 5)]
    for a, b in (((0, 0), (40, 20)), ((15, 0), (15, 30)), ((0, 10), (40, 10)), ((20, 0), (20, 20))):
        assert RT._route(a, b, boxes, None) == _route_ref(a, b, boxes, None)
