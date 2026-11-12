"""DIE-PROTO-1 11-12: die_trial.band_share_compact (opt-in --band-share-form merge / region)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import die_trial as T  # noqa: E402

G = T.GCELL_UM
DIRS = {"M4": "H", "M5": "V"}


def _area(rects):
    return round(sum((c - a) * (d - b) for _, a, b, c, d in rects), 6)


def _stripes():
    f = 0.25 * G
    return [  # M4 (H): row 3, top f, three touching gcell-long pieces + one detached; row 4 same extent (region merges k)
        ("M4", 0.0, 4 * G - f, G, 4 * G), ("M4", G, 4 * G - f, 2 * G, 4 * G), ("M4", 2 * G, 4 * G - f, 3 * G, 4 * G),
        ("M4", 5 * G, 4 * G - f, 6 * G, 4 * G),
        ("M4", 0.0, 5 * G - f, 3 * G, 5 * G),
        # M5 (V): column 7, right f, two touching pieces
        ("M5", 8 * G - f, 0.0, 8 * G, 2 * G), ("M5", 8 * G - f, 2 * G, 8 * G, 3 * G)]


def test_stripe_is_identity():
    s = _stripes()
    assert T.band_share_compact(s, "stripe", DIRS) == (s, [])


def test_merge_exact_union():
    s = _stripes()
    o, r = T.band_share_compact(s, "merge", DIRS)
    assert r == [] and len(o) == 4 and _area(o) == _area(s)
    assert ("M4", 0.0, 4 * G - 0.25 * G, 3 * G, 4 * G) in o and ("M5", 8 * G - 0.25 * G, 0.0, 8 * G, 3 * G) in o


def test_region_fraction_and_gcell_merge():
    o, r = T.band_share_compact(_stripes(), "region", DIRS)
    assert o == []
    m4 = sorted(x for x in r if x[0] == "M4")
    # rows 3 and 4 share extent 0..3G at f 0.25 -> one region over both gcell rows; the detached piece stays alone
    assert ("M4", 0.0, round(3 * G, 3), round(3 * G, 3), round(5 * G, 3), 0.25) in [tuple(round(v, 3) if isinstance(v, float) else v for v in x) for x in m4]
    assert len(m4) == 2
    m5 = [x for x in r if x[0] == "M5"]
    assert len(m5) == 1 and m5[0][5] == 0.25
    # same capacity: sum(region area x f) == stripe area
    assert round(sum((c - a) * (d - b) * f for _, a, b, c, d, f in r), 6) == _area(_stripes())


def test_region_rejects_stripe_across_gcells():
    with pytest.raises(ValueError):
        T.band_share_compact([("M4", 0.0, 0.5 * G, G, 1.5 * G)], "region", DIRS)


def test_bad_form():
    with pytest.raises(ValueError):
        T.band_share_compact([], "nope", DIRS)
