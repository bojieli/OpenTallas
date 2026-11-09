"""DIE-S81-85 11-09 native split class fixes: child-root taps, stations_in, per-root clock_entry_access.
    python3 -m pytest -q tools/die_plan/test_native_split_classes.py"""
import copy
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check  # noqa: E402
import schema  # noqa: E402
import taps  # noqa: E402

EX = json.loads((HERE / "examples" / "tiny_plan.json").read_text())


def errs(mut, chk=None):
    p = copy.deepcopy(EX)
    mut(p)
    R, summ = check.run(p, completeness=True)
    return [i["msg"] for i in R.errors() if chk is None or i["check"] == chk], summ


# ---------------------------------------------------------------- 1 child-root taps
def child_parent(p, landing=None, cls=True, tap_xy=None, second=None):
    """type src = a soft parent with two hard children W/E covering it; both children have clock root clk"""
    t = p["partition_types"]["src"]
    t["hard_cores"] = [
        dict(inst="u_w", module="cw", origin_um=[8.64, 8.64], outline_um=[414.72, 846.72], orient="R0",
             track_offset_um=[0.0, 0.0], pins=[dict(name="clk", layer="M7", xy=[200.032, 400.0])]),
        dict(inst="u_e", module="ce", origin_um=[440.64, 8.64], outline_um=[414.72, 846.72], orient="R0",
             track_offset_um=[0.0, 0.0], pins=[dict(name="clk", layer="M7", xy=[10.032, 400.0])])]
    lw = landing or [208.672, 408.64]
    lands = [dict(pin="u_w.clk", xy=lw), dict(pin="u_e.clk", xy=second or [450.672, 408.64])]
    t["clock"].update(tap_mode="explicit", tap_radius_um=300.0,
                      taps=[dict(name="clk", xy=tap_xy or lw, lands_on=lands)])
    if cls:
        t["clock"]["child_root_taps"] = dict(parent_ffs=0, rule="test: parent holds no register")


def test_child_root_tap_lands_inside_its_child():
    p = copy.deepcopy(EX)
    child_parent(p)
    P = schema.Plan(p)
    assert taps.explicit_tap_sites(P, "src") == [("clk", 208.672, 408.64)]
    (name, x, y, n, far), = taps.explicit_taps(P, "src")
    assert n == 2 and abs(far - 242.0) < 1e-6          # second landing by a parent wire, within the radius
    assert check.child_root_landings(P, "src") == []


def test_child_root_tap_fails_closed():
    for mut, msg in ((dict(cls=False), "outline/halo"),                  # without the class: inside a core halo
                     (dict(tap_xy=[208.0, 408.64]), "first landing"),   # the drop is not on the landing
                     (dict(second=[208.672, 408.64]), "outside its child box")):
        p = copy.deepcopy(EX)
        child_parent(p, **mut)
        with pytest.raises(ValueError, match=msg):
            taps.explicit_tap_sites(schema.Plan(p), "src")
    p = copy.deepcopy(EX)
    child_parent(p)
    p["partition_types"]["src"]["clock"]["child_root_taps"]["parent_ffs"] = 1
    with pytest.raises(ValueError, match="parent_ffs 0"):
        taps.explicit_tap_sites(schema.Plan(p), "src")
    p = copy.deepcopy(EX)
    child_parent(p)
    p["partition_types"]["src"]["clock"]["tap_radius_um"] = 100.0
    with pytest.raises(ValueError, match="radius"):
        taps.explicit_taps(schema.Plan(p), "src")


def test_child_root_landing_must_be_the_pin():
    p = copy.deepcopy(EX)
    child_parent(p, landing=[208.0, 408.64], tap_xy=[208.0, 408.64])
    e = check.child_root_landings(schema.Plan(p), "src")
    assert any("!= pin centre" in m for m in e)
    p = copy.deepcopy(EX)
    child_parent(p)
    p["partition_types"]["src"]["clock"]["taps"][0]["lands_on"].pop()
    assert any("u_e" in m and "no tap lands on it" in m for m in check.child_root_landings(schema.Plan(p), "src"))


# ---------------------------------------------------------------- 2 stations_in
def child_over_mid(p, own=None):
    """a hard child over the whole mid type: its ft stations sit inside it"""
    t = p["partition_types"]["mid"]
    t["hard_cores"] = [dict(inst="u_c", module="cm", origin_um=[8.64, 8.64], outline_um=[846.72, 846.72],
                            orient="R0", track_offset_um=[0.0, 0.0], obs_max="M7",
                            pins=[dict(name="p0", layer="M4", xy=[0.0, 0.024])])]
    for s in t["ft_slots"]:
        if own is not None:
            s["stations_in"] = own


def test_stations_in_accepts_child_stations_only_for_the_named_child():
    base, _ = errs(lambda p: child_over_mid(p), "geometry")
    assert any("intersect physical macros" in m for m in base)
    ok, _ = errs(lambda p: child_over_mid(p, ["u_c"]), "geometry")
    assert not any("intersect physical macros" in m for m in ok)
    bad, _ = errs(lambda p: child_over_mid(p, ["u_x"]), "geometry")
    assert any("stations_in names no hard core" in m for m in bad)
    assert any("intersect physical macros" in m for m in bad)


def test_stations_in_carries_crossing_bits_on_the_child():
    _, s0 = errs(lambda p: child_over_mid(p), "cuts")
    _, s1 = errs(lambda p: child_over_mid(p, ["u_c"]), "cuts")
    assert s0["cuts"]["child_carried"] == []
    got = s1["cuts"]["child_carried"]
    assert got and all(r["child"].endswith("/u_c") and r["bits"] > 0 for r in got)
    # the carried bits leave the parent-track count
    b0 = sum(r["bits"] for r in s0["cuts"]["vertical"])
    b1 = sum(r["bits"] for r in s1["cuts"]["vertical"])
    assert b1 + sum(r["bits"] for r in got if r["orient"] == "vertical") == b0


def test_stations_in_bounded_by_child_ports():
    e, _ = errs(lambda p: child_over_mid(p, ["u_c"]), "cuts")
    assert any("stations_in bits inside child" in m for m in e)     # 1 signal port cannot carry the lane


# ---------------------------------------------------------------- 3 per-root clock_entry_access
def two_roots(entries):
    def m(p):
        t = p["partition_types"]["src"]
        hc = dict(inst="u_core", origin_um=[8.64, 8.64], outline_um=[21.6, 21.6], orient="R0",
                  track_offset_um=[0.012, 0.012],
                  pins=[dict(name="a[0]", layer="M4", xy=[1.0, 0.012]),
                        dict(name="c0", layer="M5", xy=[0.024, 10.0]), dict(name="c1", layer="M5", xy=[0.024, 12.0])])
        if entries is not None:
            hc["clock_entry_access"] = entries
        t["hard_cores"] = [hc]
    return m


def acc(pin, fx=8.664):
    return dict(pin=pin, footprints_um=dict(M5=[[fx - 0.012, 18.6, fx + 0.012, 20.7]], M6=[[8.6, 18.636, 8.7, 18.668]],
                                            M7=[[8.784, 18.3, 8.816, 19.0]]))


def test_clock_entry_access_checks_every_listed_root():
    none, _ = errs(two_roots(None), "hard_cores")
    assert any("pin c0 M5" in m for m in none) and any("pin c1 M5" in m for m in none)
    one, _ = errs(two_roots(acc("c0")), "hard_cores")                 # the single-entry form: c0 only
    assert not any("pin c0 M5" in m for m in one) and any("pin c1 M5" in m for m in one)
    both, _ = errs(two_roots([acc("c0"), acc("c1")]), "hard_cores")
    assert both == []
    off, _ = errs(two_roots([acc("c0"), acc("c1", fx=8.676)]), "hard_cores")   # c1's own footprint off track
    assert any("pin c1 M5" in m for m in off) and not any("pin c0 M5" in m for m in off)
    dup, _ = errs(two_roots([acc("c0"), acc("c0")]), "hard_cores")
    assert any("twice" in m for m in dup)


def test_schema_accepts_the_class_fields():
    p = copy.deepcopy(EX)
    child_parent(p)
    child_over_mid(p, ["u_c"])
    two_roots([acc("c0"), acc("c1")])  # builds a mutator only
    e = schema.validate(p) if hasattr(schema, "validate") else []
    assert not [m for m in e if "child_root_taps" in m or "lands_on" in m or "stations_in" in m]
