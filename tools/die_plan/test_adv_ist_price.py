"""pytest: ADV-IST-PRICE judge on the KV A3c positive (COORD 11-23 20:3x: A3c strict stopped on 'native stations exceed priced lane depth')
and the regenerated A3b/A3d negatives."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import adv_ist_price as A  # noqa: E402


def test_a3c_l816_flagged():
    # A3c lane L816: table stations 23 / cycles 41, live ft stations 24 (GROWHOPS), landing 15, source stations 1
    why = A.judge({"stations": 23, "clock_landing": 15, "cycles": 41}, 24, 15, 1)
    assert any(w.startswith("STALE-TABLE stations") for w in why)
    assert any(w.startswith("PRICE-SHORT") and "= 42" in w for w in why)


def test_a3c_l736_flagged_with_source_depth():
    why = A.judge({"stations": 4, "clock_landing": 4, "cycles": 19}, 5, 4, 9)
    assert any("= 20" in w for w in why)


def test_regenerated_lane_passes():
    # A3b/A3d shape: table matches live counts and carries cycles >= 2 + ft + landing + source stations
    assert A.judge({"stations": 24, "clock_landing": 15, "cycles": 42}, 24, 15, 1) == []
    assert A.judge({"stations": 6, "clock_landing": 4, "cycles": 21}, 6, 4, 9) == []


def test_never_raises():
    assert A.findings(None, "p")[0].startswith("WARN ADV-IST-PRICE not checked")


class _Sch:
    DIE_PART = "__die__"


class _P:
    lanes = {"L415": {"ports": ["p0"], "fixed_cycles": 10}, "L9": {"ports": ["p1"], "fixed_cycles": 3}}
    ports = {"p0": {"src": {"part": "a", "bus": "o"}, "dst": {"part": "b", "bus": "i"}},
             "p1": {"src": {"part": "a", "bus": "o2"}, "dst": {"part": "b", "bus": "i2"}}}
    parts = {"a": {"type": "ta"}, "b": {"type": "tb"}}


def _types():
    rows = lambda bus, n: {"conn": "bus:" + bus, "regs_um": list(range(n))}  # noqa: E731
    return {"ta": {"internal_stations": [rows("o", 6), rows("o2", 3)]}, "tb": {"internal_stations": [rows("i", 5), rows("i2", 0)]}}


def test_native_fixed_split_a2f_l415():
    """A2f strict refusal: 'native stations L415: fixed_cycles must equal source 6 + destination 5' (fixed was 10)."""
    ab = {"internal_stations_types": ["ta"]}
    bad = A.native_fixed(_P, _Sch, _types(), ab, None)
    assert bad == {"L415": (10, 6, 5)}              # L9: 3 == 3 + 0 passes


def test_native_fixed_split_skips_non_native():
    assert A.native_fixed(_P, _Sch, _types(), {"internal_stations_types": ["other"]}, None) == {}


def test_native_out_lanes_flags_missing_lane():
    class P2(_P):
        lanes = {"L1": {"ports": ["p0"], "fixed_cycles": 11}}
        parts = {"a": {"type": "ta"}}
    ty = {"ta": {"buses": [{"name": "o", "dir": "out"}, {"name": "o2", "dir": "out"}],
                 "internal_stations": [{"conn": "bus:o", "regs_um": [1]}, {"conn": "bus:o2", "regs_um": [1]}]}}
    ab = {"internal_stations_types": ["ta"]}
    # o has lane L1 (src a.o); o2 has none -> flagged with 0 lanes
    assert A.native_out_lanes(P2, _Sch, ty, ab) == [("a", "o2", 0)]


def test_not_run_headline_without_asbuilt():
    """COORD 11-23 22:xx: c8 IST-PRICE without an as-built silently skipped FIXED-SPLIT/OUT-LANES (missed dn_s_3N_L3):
    the summary line must say NOT-RUN up front."""
    import types as _t
    src = open(A.__file__).read()
    assert "NOT-RUN: FIXED-SPLIT and OUT-LANES" in src
    assert 'nr = "" if isinstance(ab, dict)' in src


def test_die_io_lane_has_one_boundary_flop():
    """ISTPRICE-IO-1124: a die-IO lane (one partition flop) priced 1 cycle is not PRICE-SHORT; a partition-to-partition lane still needs 2"""
    assert A.judge({"stations": 0, "clock_landing": 0, "cycles": 1}, 0, 0, 0, 1) == []
    assert any("PRICE-SHORT" in w for w in A.judge({"stations": 0, "clock_landing": 0, "cycles": 1}, 0, 0, 0, 2))
    assert any("PRICE-SHORT" in w for w in A.judge({"stations": 0, "clock_landing": 0, "cycles": 1}, 0, 0, 0))
