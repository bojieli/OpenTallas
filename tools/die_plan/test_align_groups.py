"""tests for tools/die_plan/align_groups.py (BIND-EQDEPTH 11-23): equal-depth align groups, a hard bind gate.

A toy split seam: piece B (type tB) leaf u_kv drives busy[0] + data[3:0] into piece A (type tA) leaf u_sl on cut lanes,
and A drives req[1:0] back into u_kv.  The binder state (sinks / bitcyc / bitpos) is built by hand, as the binder
leaves it after routing; the negative case is one output bit riding a lane one stage short."""
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent))
import align_groups as AG  # noqa: E402
import schema  # noqa: E402


def cell(path, ports):
    return SimpleNamespace(path=path, ports={p: list(range(w)) for p, w in ports.items()})


def toy(out_cycles=None, in_cycles=None, local_bit=None):
    """B0 (tB): u_kv busy[0], data[3:0] -> A0 (tA) u_sl.sel / u_sl.d; A0 u_sl.req[1:0] -> B0 u_kv.req.
    out_cycles {(port, bit): cycles} overrides the default 2 per output bit; in_cycles the same for req."""
    out_cycles, in_cycles = out_cycles or {}, in_cycles or {}
    F = SimpleNamespace(cells=[cell("top.b0.u_kv", {"busy": 1, "data": 4, "req": 2}),
                               cell("top.a0.u_sl", {"sel": 1, "d": 4, "req": 2})])
    kv, sl = 0, 1
    B = SimpleNamespace(F=F, cpart={kv: "B0", sl: "A0"}, parts={"B0": {"type": "tB"}, "A0": {"type": "tA"}},
                        sinks={}, bitcyc={}, bitpos={}, ab={})
    B.rel_of = lambda ci: {kv: "u_kv", sl: "u_sl"}[ci]
    lanes = {}

    def route(sp, dp, sci, spn, sb, dci, dpn, db, cyc):
        lid = f"L_{sp}_{dp}_{cyc}"
        lanes.setdefault(lid, dict(lane=lid))
        key = (sp, dp, sci, spn, sb)
        B.bitcyc[key], B.bitpos[key] = cyc, (lanes[lid], sb)
        B.sinks[(dci, dpn, db)] = ("x", sp, sci, spn, sb, 1, dp, 0)
    route("B0", "A0", kv, "busy", 0, sl, "sel", 0, out_cycles.get(("busy", 0), 2))
    for b in range(4):
        if (("data", b)) == local_bit:
            B.sinks[(sl, "d", b)] = ("int", kv, "data", b, 0)
            continue
        route("B0", "A0", kv, "data", b, sl, "d", b, out_cycles.get(("data", b), 2))
    for b in range(2):
        route("A0", "B0", sl, "req", b, kv, "req", b, in_cycles.get(b, 2))
    return B


def plan(**over):
    g = {"t2B_out": {"type": "tB", "sources": ["u_kv.busy", "u_kv.data[3:0]"], "max_total": 4,
                     "max_total_with": "t2B_in"},
         "t2B_in": {"type": "tB", "sinks": ["u_kv.req"]}}
    for k, v in over.items():
        g[k] = v
    return {"latency": {"lanes": {}, "align_groups": g}}


def run(B, p, la=None):
    groups, derr = AG.parse(p)
    m, cerr = AG.collect(B, groups, {r["lane"]: r["delta"] for r in la or []}, extra=lambda *_: 0)
    recs, gerr = AG.check(groups, m)
    return recs, derr + cerr + gerr


def test_equal_depth_passes():
    recs, errs = run(toy(), plan())
    assert errs == []
    out = next(r for r in recs if r["group"] == "t2B_out")
    assert out["verdict"] == "PASS" and out["depth"] == 2 and out["bits"] == 5
    assert out["budget"] == dict(max_total=4, own=2, partner="t2B_in", partner_depth=2, total=4, verdict="PASS")


def test_one_output_lane_a_stage_short_fails():
    """the negative case the lane asked for: data[2] rides a lane one stage short -> hard FAIL naming the bit + lane"""
    recs, errs = run(toy(out_cycles={("data", 2): 1}), plan())
    out = next(r for r in recs if r["group"] == "t2B_out")
    assert out["verdict"] == "FAIL" and out["majority"] == 2 and out["depths"] == {1: 1, 2: 4}
    e = [x for x in errs if x.startswith("ALIGN_GROUP tB/t2B_out")]
    assert len(e) == 1 and "u_kv.data[2]=1 (lane L_B0_A0_1 -> top.a0.u_sl.d[2])" in e[0]
    assert "busy" not in e[0].split("off-majority:")[1]


def test_busy_level_off_by_one_fails():
    recs, errs = run(toy(out_cycles={("busy", 0): 3}), plan())
    assert any("u_kv.busy[0]=3" in e for e in errs)


def test_input_group_mismatch_fails():
    _recs, errs = run(toy(in_cycles={1: 3}), plan())
    assert any(e.startswith("ALIGN_GROUP tB/t2B_in") and "u_kv.req[1]=3" in e for e in errs)


def test_bit_on_no_crossing_fails():
    _recs, errs = run(toy(local_bit=("data", 1)), plan())
    assert any("1 bits on no crossing: u_kv.data[1]" in e for e in errs)


def test_budget_in_plus_out():
    _recs, errs = run(toy(), plan(t2B_out={"type": "tB", "sources": ["u_kv.busy", "u_kv.data"], "max_total": 3,
                                           "max_total_with": "t2B_in"}))
    assert errs == ["ALIGN_BUDGET tB/t2B_out: partition B0: depth 2 + t2B_in 2 = 4 > max_total 3"]


def test_latcheck_delta_counts():
    """a lane the kit will lengthen (LATCHECK as-built delta) counts: busy rides 3 on its own lane, data 2 + delta 1"""
    B = toy(out_cycles={("busy", 0): 3})
    _recs, errs = run(B, plan())
    assert any(e.startswith("ALIGN_GROUP tB/t2B_out") for e in errs)
    recs, errs = run(B, plan(), la=[dict(lane="L_B0_A0_2", delta=1)])
    out = next(r for r in recs if r["group"] == "t2B_out")
    assert out["depth"] == 3 and out["budget"]["total"] == 5      # equal now; 3 + 2 over the budget 4
    assert errs == ["ALIGN_BUDGET tB/t2B_out: partition B0: depth 3 + t2B_in 2 = 5 > max_total 4"]


def test_stale_declaration_fails():
    _recs, errs = run(toy(), plan(t2B_in={"type": "tB", "sinks": ["u_kv.gone", "u_old.req"]}))
    assert sum("matches no leaf port" in e for e in errs) == 2
    _recs, errs = run(toy(), plan(t2B_in={"type": "tB", "sinks": ["u_kv.req[5]"]}))
    assert any("has 2 bits, declared bit 5" in e for e in errs)


def test_wrong_type_scope_does_not_match():
    _recs, errs = run(toy(), plan(t2B_in={"type": "tA", "sinks": ["u_kv.req"]}))
    assert any("ALIGN_GROUP_DECL tA/t2B_in" in e for e in errs)


def test_full_path_member_and_no_type():
    recs, errs = run(toy(), {"latency": {"align_groups": {"g": {"sinks": ["top.b0.u_kv.req[1:0]"]}}}})
    assert errs == [] and recs[0]["partition"] == "B0" and recs[0]["bits"] == 2


def test_parse_errors():
    _g, errs = AG.parse({"latency": {"align_groups": {
        "a": {"sources": ["bad member"], "max_total": -1, "bogus": 1},
        "b": {"sinks": ["u.x"], "max_total": 3, "max_total_with": "nope"},
        "c": {"max_total_with": "a"}}}})
    j = " | ".join(errs)
    for s in ("unknown keys ['bogus']", "bad member 'bad member'", "max_total must be an integer",
              "unknown group 'nope'", "c: no sources and no sinks", "max_total_with without max_total"):
        assert s in j, s


def test_no_declaration_is_silent():
    assert AG.bind_check(toy(), {"latency": {"lanes": {}}}) == (None, [])


def test_schema_accepts_declaration():
    """latency.align_groups is a plan field (schema.py), so the split row / plan delta can write it"""
    lat = schema.SCHEMA["properties"]["latency"]["properties"]
    assert "align_groups" in lat
    g = lat["align_groups"]["additionalProperties"]
    assert set(g["properties"]) == AG.KEYS and g["additionalProperties"] is False
