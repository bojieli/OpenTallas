"""KW-FIX-24 (COORD 11-06 13:2x item 4, OWNER: a hold miss only on io ports is NEEDS_PARENT): an FF hold FAIL whose every
violator starts at an input port -> LOCAL_PASS_NEEDS_PARENT with the io_hold_parent obligation; any register-launched
(or unclassified) violator keeps FAIL; no violators / no census = verdict unchanged."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import signoff  # noqa: E402
import resign  # noqa: E402
from test_signoff import record, session_text  # noqa: E402


def rec_with(census=None, ports="a b", kit=None, **kw):
    r = record(**kw)
    t = session_text(**{k: v for k, v in kw.items() if k == "ff_hold"})["ff"]
    if census is not None:
        t += f"\nSO STD_MIN_START {census}\nSO STD_MIN_START_PORTS {ports}"
    ff = signoff.corner_result(signoff.parse_session(t))
    ff.update(corner="ff", macro_missing=[])
    r["corners"]["ff"] = ff
    if kit:
        r["inputs"] = dict(kit=str(kit))
    return r


def test_census_parsed():
    r = rec_with("port 1 other 0 reg 0 trunc 0 err 0", ff_hold=-4.0)
    assert r["corners"]["ff"]["std_min_start"] == dict(port=1.0, other=0.0, reg=0.0, trunc=0.0, err=0.0, ports=["a", "b"])


def test_all_port_start_violators_need_parent(tmp_path):
    (tmp_path / "budget.json").write_text(json.dumps(dict(die="hbm", type="ot_hgi_gq_aq_tile",
                                                          io_hold=dict(plan_sha256="p1"))))
    r = signoff.evaluate(rec_with("port 1 other 0 reg 0 trunc 0 err 0", ports="a", kit=tmp_path, ff_hold=-4.0))
    assert r["local_verdict"] == "SIGNED" and r["verdict"] == "LOCAL_PASS_NEEDS_PARENT", r["reasons"]
    h = r["checks"]["hold_ff"]
    assert h["verdict"] == "PASS" and h["local_raw_verdict"] == "FAIL" and h["port_only_needs_parent"]
    assert h["wns_ps"] == -4.0 and h["port_start_ports"] == ["a"]
    pol = r["io_hold"]
    assert pol["input_ports"] == ["a"] and pol["die"] == "hbm" and pol["receiver_type"] == "ot_hgi_gq_aq_tile"
    assert pol["plan_sha256"] == "p1" and pol["mode"] == "sender_min" and pol["basis"] == "ff_hold_port_start_only"
    assert r["checks"]["io_hold_parent"]["required"] and r["checks"]["io_hold_parent"]["verdict"] == "NOT RUN"
    assert r["parent_qualification"]["status"] == "NEEDS_PARENT"
    assert all(x.startswith("io_hold_parent") for x in r["reasons"])
    # the auto re-sign counts it (needs_parent_only + every required gate PASS)
    assert resign.needs_parent_only(r)
    assert all(v == "PASS" for v in resign.signoff_gates(r).values())
    # re-evaluating the stored record is stable
    again = signoff.evaluate(json.loads(json.dumps(r)))
    assert again["verdict"] == "LOCAL_PASS_NEEDS_PARENT" and again["io_hold"]["input_ports"] == ["a"]


def test_one_register_start_violator_stays_fail():
    r = signoff.evaluate(rec_with("port 1 other 0 reg 1 trunc 0 err 0", ff_hold=-4.0))
    assert r["verdict"] == "NOT SIGNED" and r["checks"]["hold_ff"]["verdict"] == "FAIL"
    assert "io_hold" not in r and any(x.startswith("hold_ff: FAIL") for x in r["reasons"])


def test_worst_path_from_non_port_stays_fail():
    for census in ("port 0 other 1 reg 0 trunc 0 err 0", "port 1 other 0 reg 0 trunc 1 err 0",
                   "port 1 other 0 reg 0 trunc 0 err 1", "port 0 other 0 reg 0 trunc 0 err 0"):
        r = signoff.evaluate(rec_with(census, ff_hold=-4.0))
        assert r["checks"]["hold_ff"]["verdict"] == "FAIL" and r["verdict"] == "NOT SIGNED", census


def test_no_census_unchanged():
    r = signoff.evaluate(record(ff_hold=-4.0))
    assert r["verdict"] == "NOT SIGNED" and r["checks"]["hold_ff"]["verdict"] == "FAIL" and "io_hold" not in r


def test_no_violators_unchanged():
    r = signoff.evaluate(rec_with(None, ff_hold=3.0))
    assert r["verdict"] == "SIGNED" and "io_hold" not in r and "port_only_needs_parent" not in r["checks"]["hold_ff"]


def test_port_only_hold_with_other_failure_not_signed():
    r = signoff.evaluate(rec_with("port 1 other 0 reg 0 trunc 0 err 0", ff_hold=-4.0, tt_setup=-1.0))
    assert r["verdict"] == "NOT SIGNED" and any(x.startswith("setup_tt: FAIL") for x in r["reasons"])
    assert not resign.needs_parent_only(r)


def test_session_tcl_carries_census():
    t = signoff.session_tcl("ff", [], True)
    i, j = t.index("so_timing STD\n"), t.index("so STD_MIN_START port")
    assert i < j < t.index("# ---- DRV ----")
    assert "-from $so_hs_regs" in t and "is_top_level_port" in t
