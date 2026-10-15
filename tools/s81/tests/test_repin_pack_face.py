"""GEO-S 2026-10-15: anchored pins (clock/reset/exempt) are immovable obstacles in the face re-pack."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hub_face_repin_search import pack_face


def _rows():
    # base order: slice A [0,3.4], anchor [3.5,3.6], slice B [3.7,7.1], anchor [7.2,7.3], slice C [7.4,10.8]
    return [dict(width=3.4, desired=20.0, w=70, anchored=False),        # wants to jump past both anchors
            dict(width=0.1, desired=3.5, w=1e9, anchored=True),
            dict(width=3.4, desired=-5.0, w=70, anchored=False),        # wants to jump before the first anchor
            dict(width=0.1, desired=7.2, w=1e9, anchored=True),
            dict(width=3.4, desired=7.4, w=70, anchored=False)]


def test_anchors_never_move_and_slices_never_cross_them():
    for reorder in (False, True):
        rows = _rows()
        new = pack_face(rows, 0.0, 20.0, reorder)
        assert new[1] == 3.5 and new[3] == 7.2
        assert 0.0 <= new[0] and new[0] + 3.4 <= 3.5 + 1e-9          # A stays left of anchor 1
        assert 3.6 - 1e-9 <= new[2] and new[2] + 3.4 <= 7.2 + 1e-9   # B stays between the anchors
        assert 7.3 - 1e-9 <= new[4] and new[4] + 3.4 <= 20.0 + 1e-9
        spans = sorted((x, x + r['width']) for x, r in zip(new, rows))
        assert all(a[1] <= b[0] + 1e-9 for a, b in zip(spans, spans[1:]))


def test_reorder_inside_one_interval():
    rows = [dict(width=1.0, desired=5.0, w=1, anchored=False), dict(width=1.0, desired=0.0, w=1, anchored=False),
            dict(width=0.1, desired=8.0, w=1e9, anchored=True)]
    new = pack_face(rows, 0.0, 10.0, True)
    assert new[1] < new[0] and new[2] == 8.0
