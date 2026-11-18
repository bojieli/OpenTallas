"""S81-BANDTAP-1115: tap windows (holes) cut in frozen ring bands for band points no planned tap reaches."""
import band_tap_windows as W


def _area(rs):
    return sum((r[2] - r[0]) * (r[3] - r[1]) for r in rs)


def test_point_already_reached_needs_no_hole():
    new, holes, left = W.plan_type({"b": [[20, 20, 60, 30]]}, [(40, 25)], 100.0)
    assert holes == [] and left == [] and new["b"] == [[20, 20, 60, 30]]


def test_hole_at_rect_end_only_trims_a_thin_band():
    rect = [20, 20, 220, 28.08]                               # 200 x 8.08 channel, nearest tap far away
    new, holes, left = W.plan_type({"b": [rect]}, [(20, 900)], 100.0)
    assert left == [] and holes
    assert all(r[0] >= 20 - 1e-9 and r[2] <= 220 + 1e-9 for r in new["b"])
    assert _area(new["b"]) < _area([rect])


def test_every_point_within_radius_of_a_hole_or_tap_after():
    rects = {"a": [[20, 20, 420, 28.08]], "c": [[20, 100, 28.08, 400]]}
    new, holes, left = W.plan_type(rects, [(900, 900)], 100.0)
    assert left == []
    taps = [tuple(h["tap_xy"]) for h in holes]
    for rs in rects.values():
        for r in rs:
            for p in W.pts_of(r):
                assert any(abs(p[0] - t[0]) + abs(p[1] - t[1]) <= 100.0 for t in taps)


def test_pieces_disjoint_inside_original_and_clear_of_the_hole():
    rect = [20, 20, 220, 120]
    new, holes, left = W.plan_type({"b": [rect]}, [(20, 900)], 100.0)
    rs = new["b"]; hs = [h["hole_um"] for h in holes]
    ov = lambda a, b: min(a[2], b[2]) > max(a[0], b[0]) + 1e-6 and min(a[3], b[3]) > max(a[1], b[1]) + 1e-6
    assert all(not ov(a, b) for i, a in enumerate(rs) for b in rs[i + 1:])
    assert all(not ov(r, h) for r in rs for h in hs)
    assert all(rect[0] <= r[0] and rect[1] <= r[1] and r[2] <= rect[2] and r[3] <= rect[3] for r in rs)
    assert abs(_area(rs) + sum((h[2] - h[0]) * (h[3] - h[1]) for h in hs) - _area([rect])) < 5.0


def test_carve_drops_slivers():
    pieces = W.carve([0, 0, 10, 8.64], [1, 0, 9.5, 8.64])
    assert [1, 0, 9.5, 8.64] not in pieces and all(p[2] - p[0] >= 2.16 for p in pieces)


def test_window_is_a_full_square_even_in_a_thin_channel_rect():
    new, holes, left = W.plan_type({"b": [[20, 20, 220, 28.08]]}, [(20, 900)], 100.0, sites=[(100.0, 24.04), (200.0, 24.04)])
    assert left == []
    for h in (x["hole_um"] for x in holes):
        assert abs((h[2] - h[0]) - 8.64) < 1e-6 and abs((h[3] - h[1]) - 8.64) < 1e-6      # >= 8.64 x 8.64 (4.32 clear on every side)
    ov = lambda a, b: min(a[2], b[2]) > max(a[0], b[0]) + 1e-6 and min(a[3], b[3]) > max(a[1], b[1]) + 1e-6
    assert all(not ov(r, x["hole_um"]) for r in new["b"] for x in holes)


def test_window_is_cut_from_every_band_it_touches():
    rbb = {"a": [[20, 20, 220, 28.08]], "c": [[20, 30, 220, 38.64]]}
    new = W.carve_centres(rbb, [(100.0, 29.0)])
    h = W.site_hole(None, (100.0, 29.0), 8.64)
    ov = lambda a, b: min(a[2], b[2]) > max(a[0], b[0]) + 1e-6 and min(a[3], b[3]) > max(a[1], b[1]) + 1e-6
    assert all(not ov(r, h) for rs in new.values() for r in rs)


def test_points_follow_the_phyt1_40um_grid():
    pts = W.pts_of([0, 0, 100, 8.64])
    assert (0.0, 0.0) in pts and (100.0, 8.64) in pts and len(pts) == 6
