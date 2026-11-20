"""REAL-VIEWS-PORTS 11-19 (COORD): per-port pin-register clock arrivals -- new sign-offs (signoff.py SO_CKP ->
corners.<c>.port_pinflops), existing ones (signoff_ports.py sidecar), and their use as per-port type views."""
import json

import die_sta_related as R
import real_views as V
import signoff as SO
import signoff_ports as SP
from test_die_sta_core_insertion import REG

CKP = """SO_CK 1 410.00 clk
SO_CKP 1 0 410.00 400.00 clk_t1
SO_CKP 0 1 430.00 425.00 clk_t1
SO_CKP 1 1 470.00 460.00 clk_t2
SO_CKP 1 0 455.00 450.00 -
SO DONE 1
"""


def test_session_emits_and_parser_folds_port_pinflops():
    t = SO.session_tcl("tt", [], "/base/6_final.spef")
    assert "SO_CKP" in t and "proc so_ckport_of" in t and "getBTerms" in t
    p = SO.parse_session(CKP)
    assert len(p["ckp"]) == 4
    pp = SO.port_pinflops(p["ckp"])
    assert pp["clk_t1"] == {"n": 2, "min": 400.0, "max": 430.0, "in": {"n": 1, "min": 400.0, "max": 410.0},
                            "out": {"n": 1, "min": 425.0, "max": 430.0}}
    assert pp["clk_t2"]["in"]["n"] == 1 and pp["clk_t2"]["out"]["n"] == 1 and pp["-"]["n"] == 1
    assert SO.port_pinflops([]) is None and "ckp" not in SO.parse_session("SO DONE 1\n")


def test_light_session_keeps_setup_and_clock_block_only():
    full = SO.session_tcl("ff", [], "/base/6_final.spef")
    t = SP.light_session(full)
    assert "read_db /base/6_final.odb" in t and "read_sdc /sdc/golden.sdc" in t and "set_propagated_clock" in t
    assert "SO_CKP" in t and t.rstrip().endswith("exit") and "so_timing SDC" not in t and len(t) < len(full) / 2


def _rec(n=2, mn=400.0, mx=470.0):
    c = lambda: dict(insertion_pinflops=dict(n=n, min=mn, max=mx))
    return {"corners": {"tt": c(), "ff": c()}}


def test_sidecar_check_requires_the_record_insertion():
    ok = {"insertion_pinflops": dict(n=2, min=400.2, max=470.0), "port_pinflops": {"clk_t1": {"n": 2}}}
    assert SP.check(_rec(), "tt", ok)["match"]
    assert not SP.check(_rec(), "tt", dict(ok, insertion_pinflops=dict(n=3, min=400.0, max=470.0)))["match"]
    assert not SP.check(_rec(), "tt", dict(ok, insertion_pinflops=dict(n=2, min=399.0, max=470.0)))["match"]


def _side(verdict="MATCH"):
    pp = {"clk_t1": {"n": 2, "min": 400.0, "max": 430.0}, "-": {"n": 1, "min": 1.0, "max": 2.0}}
    return {"verdict": verdict, "corners": {"TT": pp, "FF": {k: dict(v, min=v["min"] - 100, max=v["max"] - 100)
                                                            for k, v in pp.items()}}}


def test_kit_carries_ports_from_record_or_matching_sidecar_only():
    rec = _rec()
    assert "ports" not in V.kit_from_record(rec)
    k = V.kit_from_record(rec, _side())
    assert set(k["ports"]) == {"clk_t1"} and k["ports"]["clk_t1"]["FF"]["lat_max_ps"] == 330.0
    assert "ports" not in V.kit_from_record(rec, _side("MISMATCH"))
    rec["corners"]["tt"]["port_pinflops"] = {"clk_t9": {"n": 1, "min": 5.0, "max": 6.0}}
    rec["corners"]["ff"]["port_pinflops"] = {"clk_t9": {"n": 1, "min": 4.0, "max": 5.0}}
    assert set(V.kit_from_record(rec, _side())["ports"]) == {"clk_t9"}       # the record's own measurement wins


def test_kit_model_uses_the_tap_port_range():
    kit = {"corners": {"FF": dict(lat_min_ps=40.0, lat_max_ps=260.0)},
           "ports": {"clk_t12": {"FF": dict(lat_min_ps=300.0, lat_max_ps=310.0)}}}
    tap = dict(port="t_pfa__clk_t12", part="pfa")
    assert R.tap_clock_pin(tap) == "clk_t12" and R.tap_clock_pin(dict(port="x", part="pfa")) is None
    m = R.kit_model(kit, "FF", "fa", REG, R.tap_clock_pin(tap))
    assert (m["lat_early"], m["lat_late"], m["name"]) == (300.0, 310.0, "kit:fa:clk_t12")
    m = R.kit_model(kit, "FF", "fa", REG, "clk_t99")                          # port not measured: type-wide bound
    assert (m["lat_early"], m["lat_late"]) == (40.0, 260.0)
