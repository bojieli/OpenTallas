"""Regional clock-landing nominal cycles are priced BEFORE the binder builds its phase graph (QC 2026-10-26).

The landing ring adds a nominal +3 data cycles per physical forward-clock crossing.  It must be in
schema.Plan.lane_natural (so latency / R8 groups / bitcyc / bus_groups / DAG see it), repeated crossings of one
lane SUM, native fixed_cycles stays untouched, and lane_pad() must not add the receiver delay a second time."""
import copy
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import bind  # noqa: E402
import clock_landings as CL  # noqa: E402
import schema  # noqa: E402
import gen  # noqa: E402

TINY = json.loads((HERE / "examples" / "tiny_plan.json").read_text())


def edge(P, pid):
    p = P["ports"][[q["id"] for q in P["ports"]].index(pid)]
    return dict(id=f"cland_clk__{pid}", kind="clock", width=1,
                src=dict(part=p["src"]["part"], bus="fclk_out_" + p["src"]["bus"]),
                dst=dict(part=p["dst"]["part"], bus="fclk_in_" + p["dst"]["bus"]))


def with_network(raw, pids, monitor=True):
    raw = copy.deepcopy(raw)
    edges = [edge(raw, pid) for pid in pids]
    if monitor:     # monitor/status ring edges add boot time only, never data cycles
        edges.append(dict(id="cland_up__pm1", kind="ctl", width=1, src=dict(part="pm1", bus="cland_up_ready"),
                          dst=dict(part="pa", bus="cland_dn_ready_0")))
    raw.setdefault("clock", {})["landing_network"] = dict(edges=edges, data_cycles_per_crossing=3)
    return raw


def test_lane_natural_prices_each_crossing_and_sums_repeats():
    base = schema.Plan(TINY).lane_natural("x")
    one = schema.Plan(with_network(TINY, ["x1"])).lane_natural("x")
    two = schema.Plan(with_network(TINY, ["x0", "x2"])).lane_natural("x")
    assert one["cycles"] == base["cycles"] + 3 and one["clock_landing"] == 3
    assert two["cycles"] == base["cycles"] + 6 and two["clock_landing"] == 6        # repeated crossings SUM
    for d in (one, two):                                                              # native fields untouched
        assert (d["fixed"], d["stations"], d["boundary"]) == (base["fixed"], base["stations"], base["boundary"])
    other = schema.Plan(with_network(TINY, ["x0", "x2"]))
    for lid in other.lanes:
        if lid != "x":
            assert other.lane_natural(lid) == schema.Plan(TINY).lane_natural(lid)
    lat = gen.latency_table(other)["x"]
    assert lat["cycles"] == lat["natural"] == base["cycles"] + 6 and lat["clock_landing"] == 6


def test_fixed_cycles_preserved_and_added_on_top():
    raw = with_network(TINY, ["x1"])
    raw["lanes"][[l["id"] for l in raw["lanes"]].index("x")]["fixed_cycles"] = 2
    d = schema.Plan(raw).lane_natural("x")
    assert d["fixed"] == 2 and d["clock_landing"] == 3
    assert d["cycles"] == d["boundary"] + d["stations"] + 2 + 3


@pytest.mark.parametrize("mut,msg", [
    (lambda r: r["clock"]["landing_network"]["edges"].append(dict(r["clock"]["landing_network"]["edges"][0])),
     "stale/duplicate"),
    (lambda r: r["clock"]["landing_network"]["edges"][0].update(id="cland_clk__nope"), "stale/duplicate"),
    (lambda r: r["clock"]["landing_network"]["edges"][0]["dst"].update(part="pb"), "endpoints changed"),
    (lambda r: r["clock"]["landing_network"].update(data_cycles_per_crossing=2), "nominal \\+3"),
    (lambda r: r["lanes"].append(dict(id="x_dup", ports=["x1"])), "exactly one logical lane"),
])
def test_network_fails_loudly(mut, msg):
    raw = with_network(TINY, ["x1"])
    mut(raw)
    with pytest.raises(CL.LandingError, match=msg):
        CL.network_lane_cycles(raw)


class _Rows:
    def __init__(self, rows):
        self.rows = rows


def _binder(raw, rows):
    B = bind.Binder.__new__(bind.Binder)
    ports = {p["id"]: p for p in raw["ports"]}
    raw = dict(raw, lanes=[l for l in raw["lanes"]         # the binder's plans carry partition-to-partition lanes
                           if schema.DIE_PART not in (ports[l["ports"][0]]["src"]["part"], ports[l["ports"][-1]]["dst"]["part"])])
    B.plan, B.errors = raw, []
    if rows is not None:
        B.clock_landings = _Rows(rows)
    return B


def _priced(pids):
    raw = with_network(TINY, pids)
    raw["latency"] = dict(lanes=gen.latency_table(schema.Plan(raw)))
    return raw


def test_plan_lanes_carry_landing_into_phase_graph_cycles():
    """plan_lanes() feeds build_buses: recv/bitcyc = upstream stages + L['cycles'], so the landing must be in
    L['cycles'] here (before build_buses), and lane_pad must leave it to the landing hardware."""
    raw = _priced(["x0", "x2"])
    rows = [dict(port="x0", lane="x", added_cycles=3), dict(port="x2", lane="x", added_cycles=3)]
    B = _binder(raw, rows)
    lanes = {L["id"]: L for ls in B.plan_lanes().values() for L in ls}
    assert not B.errors
    nat = schema.Plan(TINY).lane_natural("x")["cycles"]
    L = lanes["x"]
    assert L["cycles"] == nat + 6 and L["clock_landing_cycles"] == 6
    L = dict(L, lane="x")
    assert bind.lane_pad(L) == nat - 2 - sum(h["stations"] for h in L["ft"])      # no double receiver delay
    bound = 2 + sum(h["stations"] for h in L["ft"]) + bind.lane_pad(L) + L["clock_landing_cycles"]
    assert bound == L["cycles"]                                                    # LANE_CYCLES closes exactly
    R8 = dict(L, cycles=L["cycles"] + 2)                                           # R8 pad still realised as pad
    assert bind.lane_pad(R8) == bind.lane_pad(L) + 2


def test_plan_lanes_reject_unpriced_or_unbound_landing():
    stale = copy.deepcopy(TINY)                       # latency NOT regenerated: binder must not silently pad
    stale["latency"] = dict(lanes=gen.latency_table(schema.Plan(TINY)))
    B = _binder(stale, [dict(port="x1", lane="x", added_cycles=3)])
    B.plan_lanes()
    assert any(e.startswith("LANE_LANDING_LATENCY x:") for e in B.errors)
    B = _binder(_priced(["x1"]), None)                # priced landing but no landing hardware bound
    B.plan_lanes()
    assert any("no clock_landing_table bound" in e for e in B.errors)
