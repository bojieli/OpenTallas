"""S81-DEC5 2026-10-18: the in-flow textbook_lint clock check matches pre_route_gate for a flop-less parent; the recorded
clock_rule_waiver honoured (<= 2 ps, named pair), insertion guidance only.  s81lk_kp4_dec-p1-860eecb6d was refused
in-flow on its own gate evidence.  OWNER 10-23: the judged number is the related flop-pair skew with CPPR
("<c>_pair_skew_ps", worst pair "<c>_pair_skew_pair"); spreads are information only, the waiver applies to pair skew."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import textbook_lint as TL  # noqa: E402

PAIRS = [{"corner": "tt", "a": "u_dly", "b": "u_out", "ps": 68.5}, {"corner": "ff", "a": "u_dly", "b": "u_syn", "ps": 80.5},
         {"corner": "ff", "a": "u_chn", "b": "u_syn", "ps": 67.3}]
EV = {"max_root_sinks": 4, "tt_insertion_ps": 639.1, "ff_insertion_ps": 507.1, "tt_spread_ps": 116.8,
      "ff_spread_ps": 64.6, "tt_pin_spread_ps": 68.5, "ff_pin_spread_ps": 80.5, "tt_pin_spread_basis": "child_pair",
      "ff_pin_spread_basis": "child_pair", "child_pairs": PAIRS,
      "tt_pair_skew_ps": 68.5, "ff_pair_skew_ps": 80.5, "ff_pair_skew_pair": ["u_dly/q_reg[0]", "u_syn/d_reg[0]"]}
WV = {"pair": "ddly-dsyn", "ff_ps": 80.5, "limit_ps": 80, "by": "coordinator 0ga 10-18"}


def lint(ev=EV, waiver=None):
    res = {"metrics": {"clock_max_root_sinks": 4, "clock_max_root": "port:clk"}, "findings": {}}
    clock = {"enforce": True, "evidence": ev}
    if waiver:
        clock["waiver"] = waiver
    TL.verdict(res, mode="refuse", clock=clock)
    return res


def test_insertion_and_leaf_spread_are_guidance():
    ev = dict(EV, ff_pair_skew_ps=79.0)
    r = lint(ev)          # 639 ps insertion, 116.8 ps leaf spread, 80.5 FF pin spread: pair skew <= 80 passes
    assert r["verdict"] != "REFUSE" and r["clock_rule"]["ok"]
    assert "spread 80.5 ps (info)" in r["clock_rule"]["text"]


def test_spread_alone_never_refuses():
    ev = {k: v for k, v in EV.items() if "pair_skew" not in k}
    r = lint(ev)          # FF pin spread 80.5 > 80, no pair skew measured: WARN, never REFUSE
    assert r["verdict"] != "REFUSE" and "pair skew not measured" in r["clock_rule"]["text"]


def test_pair_over_without_waiver_refuses():
    r = lint()
    assert r["verdict"] == "REFUSE" and "clock_sinks" in r["refusing_checks"]


def test_waiver_honoured():
    r = lint(waiver=WV)
    assert r["verdict"] != "REFUSE" and "WAIVED" in r["clock_rule"]["text"]
    assert "clock_sinks" not in r["findings"] and "clock_guidance" in r["findings"]


def test_waiver_wrong_pair_or_too_big():
    assert lint(waiver=dict(WV, pair="dchn-dsyn"))["verdict"] == "REFUSE"
    ev = dict(EV, ff_pair_skew_ps=82.5)
    assert lint(ev, dict(WV, ff_ps=82.5))["verdict"] == "REFUSE"
    assert lint(dict(EV, ff_pair_skew_pair=["u_chn/q", "u_syn/d"]), WV)["verdict"] == "REFUSE"   # other worst pair
    r = lint(waiver=dict(WV, by=""))
    assert r["verdict"] == "REFUSE" and "NOT applied" in r["clock_rule"]["text"]


def test_relaxing_rule_requirement_honours_waiver():
    sys.path.insert(0, str(Path(__file__).resolve().parent / "ref_tile"))
    import source_binding as SB
    assert not SB.relaxed_rule_requirement(["clock_pin_spread"], EV)[0]
    ok, rows = SB.relaxed_rule_requirement(["clock_pin_spread"], dict(EV, clock_rule_waiver=WV))
    assert ok and "WAIVED" in rows[0]["text"]
    assert not SB.relaxed_rule_requirement(["clock_pin_spread"], dict(EV, clock_rule_waiver=dict(WV, pair="dchn-dsyn")))[0]
