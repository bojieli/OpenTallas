"""TYPE-REDUCE-2: one pin table per template (pin_template.py) + type census (type_census.py)."""
from fractions import Fraction

from tools.die_plan import pin_template as PT


def test_m3_m5_never_mirror_compatible_m5_m7_are():
    assert PT.compatible(["M3", "M5"], 0.108, 172.8)[0] is False
    ok, delta, per = PT.compatible(["M5"], 0.108, 172.8)
    assert ok and delta == Fraction("0.024")
    ok, delta, per = PT.compatible(["M5", "M7"], 0.108, 172.8)
    assert ok and per == Fraction("0.192")


def _tpl():
    W, H, toff = 172.8, 345.6, 0.108
    pins = [dict(name=f"a[{i}]", layer="M3" if i % 2 else "M5", x=10 + 0.5 * i, y=0.019) for i in range(40)]
    pins += [dict(name=f"b[{i}]", layer="M4", x=0.042, y=10 + i) for i in range(5)]
    return W, H, toff, pins, PT.make_template(pins, W, H, toff, ("M5",))


def test_template_keeps_order_and_lands_on_tracks_in_both_orients():
    W, H, toff, pins, (tpl, worst) = _tpl()
    s = sorted((p for p in tpl if p["name"].startswith("a")), key=lambda p: p["x"])
    assert [p["name"] for p in s] == [f"a[{i}]" for i in range(40)]
    assert all(p["layer"] == "M5" for p in s) and worst < 0.2
    ok, delta, _ = PT.compatible(["M5"], toff, W)
    for p in s:
        assert PT.on_track("M5", 0 + toff + p["x"])                      # R0 at origin 0
        assert PT.on_track("M5", 0 + toff + float(delta) + W - p["x"])    # MY with the solved offset
    assert [p for p in tpl if p["name"].startswith("b")] == [p for p in pins if p["name"].startswith("b")]


def test_relation_detects_mirror():
    W, H, toff, pins, (tpl, _) = _tpl()
    mir = [dict(p, x=W - p["x"]) for p in tpl]
    assert PT.relation(tpl, mir, W, H)[0] == "mirror-x"
    assert PT.relation(tpl, tpl, W, H)[0] == "same"
