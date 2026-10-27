"""HANDOFF 0ga 2026-10-18: a recorded per-pair clock_rule excess <= 2 ps becomes a printed WARN; anything else FAILs.
OWNER 10-23: the waiver judges the related flop-pair skew with CPPR ("<c>_pair_skew_ps", worst pair "<c>_pair_skew_pair");
spreads are information only."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import pre_route_gate as PRG  # noqa: E402

PAIRS = [{"corner": "ff", "a": "u_dly", "b": "u_syn", "ps": 80.5}, {"corner": "ff", "a": "u_chn", "b": "u_syn", "ps": 67.3}]
W = {"pair": "ddly-dsyn", "ff_ps": 80.5, "limit_ps": 80, "by": "coordinator 0ga 10-18"}


def run(waiver, ff=80.5, pairs=PAIRS):
    g = PRG.Gate()
    worst = max((p for p in pairs if p["corner"] == "ff"), key=lambda p: p["ps"])
    g.clock = {"evidence": {"tt_pin_spread_ps": 68.5, "ff_pin_spread_ps": ff, "tt_pin_spread_basis": "child_pair",
                            "ff_pin_spread_basis": "child_pair", "child_pairs": pairs,
                            "tt_pair_skew_ps": 68.5, "ff_pair_skew_ps": ff,
                            "ff_pair_skew_pair": [f"{worst['a']}/q_reg", f"{worst['b']}/d_reg"]}}
    g.add("FAIL", "clock_rule", "FF pair skew > 80")
    PRG.apply_clock_rule_waiver(g, {"clock_rule_waiver": waiver} if waiver else {})
    return [i for i in g.items if i["check"] == "clock_rule"][0]


def test_waived():
    for pair in ("ddly-dsyn", "dly-syn", "u_syn-u_dly"):
        i = run(dict(W, pair=pair))
        assert i["severity"] == "WARN" and "WAIVED" in i["message"]


def test_wrong_pair():
    assert run(dict(W, pair="dchn-dsyn"))["severity"] == "FAIL"


def test_no_waiver():
    assert run(None)["severity"] == "FAIL"


def test_excess_too_big():
    assert run(dict(W, ff_ps=82.5), ff=82.5, pairs=[dict(PAIRS[0], ps=82.5)])["severity"] == "FAIL"


def test_value_above_recorded():
    assert run(W, ff=81.0, pairs=[dict(PAIRS[0], ps=81.0)])["severity"] == "FAIL"


def test_other_pair_over():
    # the measured worst pair is not the waiver's named pair
    assert run(W, pairs=[PAIRS[1], {"corner": "ff", "a": "u_chn", "b": "u_out", "ps": 80.5}])["severity"] == "FAIL"


def test_spread_over_with_pair_skew_in_limit_needs_no_waiver():
    ev = {"max_root_sinks": 4, "tt_pin_spread_ps": 68.5, "ff_pin_spread_ps": 95.0, "tt_pair_skew_ps": 60.0,
          "ff_pair_skew_ps": 79.9}
    assert PRG.TL.clock_rule_eval(4, ev)[0] == "PASS"
    assert PRG.TL.clock_rule_eval(4, dict(ev, ff_pair_skew_ps=80.1))[0] == "FAIL"


# COORD 10-20 19:25: SCOPED_CLOCK_WAIVER_CAPS (qkd_pv_fin_s32 only, TT 88.4 / FF 84.6)
PV = {"pair": "port:ck-root", "tt_ps": 88.4, "ff_ps": 84.6, "limit_ps": 80, "by": "COORD 10-20 19:25",
      "scope": "qkd_pv_fin_s32"}


def run_pv(waiver, block="qkd_pv_fin_s32", tt=88.4, ff=84.6):
    g = PRG.Gate()
    g.clock = {"evidence": {"tt_pin_spread_ps": tt, "ff_pin_spread_ps": ff, "tt_pair_skew_ps": tt, "ff_pair_skew_ps": ff}}
    g.add("FAIL", "clock_rule", "pair skew > 80")
    PRG.apply_clock_rule_waiver(g, {"block": block, "clock_rule_waiver": waiver})
    return [i for i in g.items if i["check"] == "clock_rule"][0]


def test_scoped_cap_applies_to_its_tile():
    assert run_pv(PV)["severity"] == "WARN"


def test_scoped_cap_refused_on_other_tile():
    assert run_pv(PV, block="qkd_pv_fin_s33")["severity"] == "FAIL"


def test_scoped_cap_exceeded():
    assert run_pv(dict(PV, tt_ps=88.6), tt=88.6)["severity"] == "FAIL"


def test_unscoped_large_excess_still_fails():
    w = {k: v for k, v in PV.items() if k != "scope"}
    assert run_pv(w)["severity"] == "FAIL"


# ROOT takeover: svc4 cap stays tied to the exact gated block and measured TT limit.
def test_native59_scoped_cap_and_causal_refusals():
    w = dict(PV, scope="qfd_native59_svc", tt_ps=84.6, ff_ps=77.5)
    assert run_pv(w, block="qfd_native59_svc", tt=84.6, ff=77.5)["severity"] == "WARN"
    assert run_pv(w, block="qfd_native59_other", tt=84.6, ff=77.5)["severity"] == "FAIL"
    assert run_pv(dict(w, tt_ps=84.7), block="qfd_native59_svc", tt=84.7, ff=77.5)["severity"] == "FAIL"
    assert run_pv(dict(w, ff_ps=82.1), block="qfd_native59_svc", tt=84.6, ff=82.1)["severity"] == "FAIL"
    assert run_pv({k: v for k, v in w.items() if k != "scope"}, block="qfd_native59_svc", tt=84.6, ff=77.5)["severity"] == "FAIL"
