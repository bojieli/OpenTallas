"""die_sta_related.py kit-contract hold bound (INFRA-FIRST-R3b): bound = declared window - hold damage, CPPR at the
last common tree node; zero-logic numbers unchanged."""
import die_sta_related as R

REG = dict(clkq_max_wire_ps=68.0, clkq_min_nowire_ps=46.5, setup_ps=5.6, hold_ps=22.2)


def _taps():
    # region root "h0" range 10 ps; a/b in one partition, c in a neighbour; all in region h0
    return {"a": dict(late_ps=1000.0, early_ps=990.0, cppr_node="h0"),
            "b": dict(late_ps=1050.0, early_ps=1040.0, cppr_node="h0"),
            "c": dict(late_ps=1020.0, early_ps=1010.0, cppr_node="h0")}


def test_contract_bound_intra_and_seam():
    taps, rng = _taps(), {"h0": 10.0, "h": 30.0}
    pairs = [("a", "b", "p"), ("b", "a", "p")]
    r = R.time_class(pairs, taps, rng, REG, 20.0, 833.333, 60.0, 25.0, hold_window=dict(ps=0.0, basis="t"))
    kc = r["kit_contract_hold"]
    # a -> b: damage = b.late - a.early - credit(10) = 1050 - 990 - 10 = 50
    assert kc["window_needed_ps"] == 50.0 and kc["worst_hold_bound_ps"] == -50.0 and kc["verdict"] == "FAIL"
    assert kc["neg_pairs"] == 1
    # zero-logic hold unchanged: 990 + 46.5 - (1050 + 22.2) - 25 + 10
    assert r["worst_hold_slack_ps"] == round(990 + 46.5 - 1050 - 22.2 - 25 + 10, 2)
    r2 = R.time_class([("a", "c", "p->q")], taps, rng, REG, 20.0, 833.333, 60.0, 25.0,
                      hold_window=dict(ps=40.0, basis="legacy"))
    assert r2["kit_contract_hold"]["worst_hold_bound_ps"] == 20.0 and r2["kit_contract_hold"]["verdict"] == "PASS"


def test_no_window_no_contract_block():
    r = R.time_class([("a", "b", "p")], _taps(), {"h0": 10.0}, REG, 20.0, 833.333, 60.0, 25.0)
    assert "kit_contract_hold" not in r
