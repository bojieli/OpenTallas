"""LAND-RING-2 11-12: _compact_bank_boxes is the old compact-bank scan of _storage_band, same list in the same order."""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import clock_landing_plan as C  # noqa: E402


def _reference(xs, ys, bw, bh, w, h, margin, px, py, obstacles):
    out = []
    for x0 in xs:
        for y0 in ys:
            box = [x0, y0, x0 + bw, y0 + bh]
            if x0 < margin or y0 < margin or box[2] > w - margin or box[3] > h - margin:
                continue
            if max(abs(x - px) + abs(y - py) for x in (box[0], box[2]) for y in (box[1], box[3])) > 405 - 2.16:
                continue
            if any(min(box[2], o[2]) > max(box[0], o[0]) + 1e-6 and min(box[3], o[3]) > max(box[1], o[1]) + 1e-6
                   for o in obstacles):
                continue
            out.append(box)
    return out


def test_identical_to_the_old_scan_on_random_floorplans():
    rnd = random.Random(1112)
    for trial in range(60):
        w, h = rnd.choice([(622.08, 1339.2), (1278.72, 1520.64), (400.0, 300.0)])
        margin = 17.28
        obstacles = []
        for _ in range(rnd.randint(0, 60)):
            x0, y0 = rnd.uniform(0, w), rnd.uniform(0, h)
            obstacles.append([x0, y0, x0 + rnd.uniform(1, 250), y0 + rnd.uniform(1, 250)])
        px, py = rnd.uniform(0, w), rnd.choice([0.0, h, rnd.uniform(0, h)])
        for bw, bh in [(8.64, 84.24), (84.24, 8.64), (2.16 * rnd.randint(5, 40), 2.16 * rnd.randint(5, 40))]:
            xs = {margin, w - bw - margin, max(margin, min(w - bw - margin, px - bw / 2))}
            ys = {margin, h - bh - margin, max(margin, min(h - bh - margin, py - bh / 2))}
            for o in obstacles:
                xs.update((o[0] - bw - 2.16, o[2] + 2.16)); ys.update((o[1] - bh - 2.16, o[3] + 2.16))
            want = _reference(xs, ys, bw, bh, w, h, margin, px, py, obstacles)
            got = C._compact_bank_boxes(xs, ys, bw, bh, w, h, margin, px, py, obstacles)
            assert got == want, (trial, bw, bh)


def test_reach_is_judged_on_the_farthest_corner():
    # one candidate exactly at the reach limit and one just past it
    R = 405 - 2.16
    got = C._compact_bank_boxes({100.0}, {100.0, 100.01}, 10.0, 10.0, 2000, 2000, 17.28, 100.0 + 10.0 - R + 110.0, 0.0, [])
    assert [b[1] for b in got] == [b[1] for b in _reference({100.0}, {100.0, 100.01}, 10.0, 10.0, 2000, 2000, 17.28,
                                                                  100.0 + 10.0 - R + 110.0, 0.0, [])]
