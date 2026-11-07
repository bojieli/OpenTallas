import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pose_spread as P


def site(x, y, o=None, m="DFFHQNx1"):
    return (x, y, 1.08, 0.27, o or ("R0" if round(y / 0.27) % 2 == 0 else "MX"), m)


def test_spread_scales_about_centroid_keeps_others_and_row_orientation():
    s = {"u_a/f0": site(10.8, 27.0), "u_a/f1": site(21.6, 27.27), "u_b/f": site(5.4, 2.7)}
    rows = [round(k * 0.27, 4) for k in range(400)]
    new, st = P.spread(s, r"u_a", 2.0, (100.0, 100.0), rows)
    assert new["u_b/f"] == s["u_b/f"]
    assert new["u_a/f1"][0] - new["u_a/f0"][0] == pytest.approx(21.6, abs=0.06)
    for x, y, w, h, o, m in new.values():
        assert o == ("R0" if round(y / 0.27) % 2 == 0 else "MX") and m == "DFFHQNx1"
        assert abs(x / P.SITE_W - round(x / P.SITE_W)) < 1e-6
    assert st["u_a"]["ffs"] == 2


def test_box_at_edge_shifts_inward_not_clamped():
    s = {"u_a/f0": site(0.054, 54.0), "u_a/f1": site(20.0 // P.SITE_W * P.SITE_W, 54.0)}
    new, _ = P.spread(s, r"u_a", 3.0, (100.0, 100.0), [round(k * 0.27, 4) for k in range(400)])
    assert new["u_a/f0"][0] >= 0 and new["u_a/f1"][0] - new["u_a/f0"][0] == pytest.approx((s["u_a/f1"][0] - s["u_a/f0"][0]) * 3, abs=0.06)


def test_mixed_row_orientation_refused():
    with pytest.raises(ValueError, match="one family per row parity"):
        P.row_orients({"a": site(0, 2.7, "R0"), "b": site(5, 2.7, "MX")})


def test_row_change_keeps_x_flip():
    s = {"u_a/f0": site(10.8, 27.0, "MY"), "u_a/f1": site(21.6, 27.54, "R0")}
    new, _ = P.spread(s, r"u_a", 1.5, (100.0, 100.0), [round(k * 0.27, 4) for k in range(400)])
    for n in s:
        same = round(new[n][1] / 0.27) % 2 == round(s[n][1] / 0.27) % 2
        assert new[n][4] == (s[n][4] if same else P.ROW_FLIP[s[n][4]])


def test_far_outlier_move_capped():
    s = {f"u_a/f{i}": site(50.004 + i * 1.08, 54.0) for i in range(50)}
    s["u_a/far"] = site(400.0 // P.SITE_W * P.SITE_W, 54.0)
    new, _ = P.spread(s, r"u_a", 2.0, (900.0, 900.0), [round(k * 0.27, 4) for k in range(3000)], max_move=60.0)
    assert abs(new["u_a/far"][0] - s["u_a/far"][0]) <= 60.1
