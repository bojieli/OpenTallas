"""SIGN-PERIOD + SIGN-INHERIT in the counter (OWNER 2026-11-20 (1) and (3))."""
import hashlib
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import release_tree_plan as R  # noqa: E402

CS = R._PROV_NS["counts_signed"]


def rec(tt=-30.0, period=None, sp=None):
    d = dict(checks=dict(drc=dict(count=0), setup_tt=dict(wns_ps=tt), hold_ff=dict(wns_ps=1.0)))
    if period is not None:
        d["corners"] = dict(tt=dict(periods=dict(clk=period, gen=0.0)))
    if sp is not None:
        d["signed_period_ps"] = sp
    return d


def test_counts_signed_period_rules():
    assert CS(rec())                                   # 833 record, no periods recorded (old records)
    assert CS(rec(period=833.0))
    assert not CS(rec(period=900.0))                   # relaxed clock without a declared period
    assert CS(rec(period=900.0, sp=900))
    assert not CS(rec(period=905.0, sp=900))           # declared != measured
    assert not CS(rec(period=1100.0, sp=1100))         # over the 1000 cap
    assert not CS(rec(tt=-50.0, period=900.0, sp=900))


def test_type_and_die_period():
    st = {"a": ["h:/x PERIOD 900", "h:/y"], "b": ["h:/z PERIOD 950"], "c": ["h:/q"]}
    tp = R.type_periods(st)
    assert tp == {"a": 833.0, "b": 950.0, "c": 833.0} and R.die_period(tp) == 950.0 and R.die_period({}) == 833.0


def inherit_row(tmp_path, schema, iso=True, credit=True):
    rec = dict(schema=schema, sibling="m", representative="o", credit=credit, proof=dict(isomorphic=iso))
    p = tmp_path / ("r_%s_%s.json" % (schema[-14:], iso))
    p.write_bytes(json.dumps(rec).encode())
    return dict(die="s81", member="m", rep="o", record=str(p), sha=hashlib.sha256(p.read_bytes()).hexdigest())


def test_netlist_inherit_credit_reason(tmp_path):
    st = {"o": ["h:/o/signoff.json SIGNED-NO-TAG PERIOD 915"]}
    tm = {"o": "mo", "m": "mm"}
    done = R.inherit_credit("s81", st, tm, [inherit_row(tmp_path, R.NETLIST_INHERIT_SCHEMA)])
    assert done == ["m"] and "INHERIT o" in st["m"][0] and "PERIOD 915" in st["m"][0]
    assert R.type_periods(st)["m"] == 915.0           # an inheritor runs at its representative's period


def test_netlist_inherit_needs_proof_and_credit(tmp_path):
    tm = {"o": "mo", "m": "mm"}
    for row in (inherit_row(tmp_path, R.NETLIST_INHERIT_SCHEMA, iso=False), inherit_row(tmp_path, R.NETLIST_INHERIT_SCHEMA, credit=False)):
        st = {"o": ["h:/o"]}
        assert R.inherit_credit("s81", st, tm, [row]) == [] and "m" not in st
    st = {}
    assert R.inherit_credit("s81", st, tm, [inherit_row(tmp_path, R.NETLIST_INHERIT_SCHEMA)]) == []   # representative not counted
