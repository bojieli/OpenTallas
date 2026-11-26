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
    assert bad == {"L415": (10, 6, 5, 0)}           # L9: 3 == 3 + 0 passes


class _PS(_P):
    # S81 c10b seqhost 7N / 7S shape: native source 2 stations, no destination stations, lep ROS receiver soft_latency.in 3
    lanes = {"unit__seqhost__s_7N_LP": {"ports": ["p0"], "fixed_cycles": 5}, "unit__seqhost__s_7S_LP": {"ports": ["p1"], "fixed_cycles": 5}}


def _soft_types(soft=3):
    rows = lambda bus, n: {"conn": "bus:" + bus, "regs_um": list(range(n))}  # noqa: E731
    return {"ta": {"internal_stations": [rows("o", 2), rows("o2", 2)]},
            "tb": {"soft_latency": {"in": {"i": soft, "i2": soft}, "out": {"k": 3}}}}


def test_native_fixed_counts_declared_soft_receiver_once():
    """PRE-PRICE-ONCE-1125 (c10b R10/R11 PRE: 'fixed_cycles 5 != native source stations 2 + destination 0; fix: fixed_cycles = 2' while
    the strict bind requires source 2 + destination 0 + receiver soft 3): native 2 + declared soft receiver 3 = 5 passes."""
    ab = {"internal_stations_types": ["ta"]}
    assert A.native_fixed(_PS, _Sch, _soft_types(), ab, None) == {}


def test_native_fixed_soft_receiver_not_dropped_or_doubled():
    ab = {"internal_stations_types": ["ta"]}

    class Native2(_PS):         # the old native-only price (2) is now short of the declared receiver
        lanes = {"unit__seqhost__s_7N_LP": {"ports": ["p0"], "fixed_cycles": 2}}

    class Twice(_PS):           # receiver charged twice (2 + 3 + 3)
        lanes = {"unit__seqhost__s_7N_LP": {"ports": ["p0"], "fixed_cycles": 8}}
    assert A.native_fixed(Native2, _Sch, _soft_types(), ab, None) == {"unit__seqhost__s_7N_LP": (2, 2, 0, 3)}
    assert A.native_fixed(Twice, _Sch, _soft_types(), ab, None) == {"unit__seqhost__s_7N_LP": (8, 2, 0, 3)}
    # soft_latency on another bus of the receiver does not price this lane
    ty = _soft_types()
    ty["tb"]["soft_latency"]["in"] = {"other_i": 3}
    assert set(A.native_fixed(_PS, _Sch, ty, ab, None)) == {"unit__seqhost__s_7N_LP", "unit__seqhost__s_7S_LP"}


def test_soft_receiver_matches_bind_rule():
    """the same count the bind uses (core_latency.soft_in_cycles), and the finding text names the receiver term and the fix"""
    import core_latency as CL
    ty = _soft_types()["tb"]
    for bus in ("i", "i2", "absent"):
        assert A.soft_in_cycles(ty, bus) == CL.soft_in_cycles(ty, bus)
    assert A.soft_in_cycles(None, "i") == 0 and A.soft_in_cycles({"soft_latency": None}, "i") == 0
    src = open(A.__file__).read()
    assert 'f" + receiver soft {soft}" if soft else ""' in src and "fix: fixed_cycles = {src + dst + soft}" in src


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
