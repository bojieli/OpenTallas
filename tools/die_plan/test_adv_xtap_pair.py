import json
import adv_xtap_pair as X


def plan(rows, taps=None, outline=(100.0, 100.0)):
    taps = taps or [{"name": "clk", "xy": [10, 10]}, {"name": "clk_t1", "xy": [90, 90]}]
    return {"clock": {"tap_offset": {"per_port_ps": {"x": rows}}},
            "partition_types": {"x": {"outline_um": list(outline), "clock": {"tap_mode": "explicit", "taps": taps}}}}


def cache(pairs, die=(100.0, 100.0)):
    return {"xtap_pairs": {"x": {"die_um": list(die), "pairs": pairs, "kit": "k"}}}


ROWS = {"clk": {"TT": 0.0, "FF": 0.0, "tol": 15.0}, "clk_t1": {"TT": 30.0, "FF": 25.0, "tol": 20.0}}


def test_est_is_offset_difference_plus_tolerance():
    assert X.est_ps(plan(ROWS), "x", "clk", "clk_t1") == (50.0, [])
    assert X.est_ps(plan(ROWS), "x", "clk_t1", "clk") == (50.0, [])


def test_cross_tap_pair_over_budget_is_flagged():
    lines = X.findings(plan(ROWS), cache=cache([[5, 5, 95, 95, 3], [5, 5, 12, 12, 7]]))
    assert lines[0].startswith("WARN ADV-XTAP-PAIR x: 3 of 10 register pairs cross taps")
    assert "worst clk vs clk_t1 50.0 ps" in lines[0] and "clk->clk_t1 x3" in lines[0]
    assert "1 with cross-tap pairs over 40 ps" in lines[-1]


def test_same_tap_pairs_and_small_spread_pass():
    assert len(X.findings(plan(ROWS), cache=cache([[5, 5, 12, 12, 9]]))) == 1
    rows = {"clk": {"TT": 0.0, "FF": 0.0, "tol": 5.0}, "clk_t1": {"TT": 10.0, "FF": 8.0, "tol": 5.0}}
    out = X.findings(plan(rows), cache=cache([[5, 5, 95, 95, 4]]))
    assert len(out) == 1 and "0 with cross-tap pairs" in out[0]
    assert len(X.findings(plan(ROWS), cache=cache([[5, 5, 95, 95, 4]]), budget_ps=60.0)) == 1


def test_missing_rows_named_and_outline_mismatch_not_judged():
    out = X.findings(plan({"clk": {"TT": 50.0, "FF": 0.0, "tol": 15.0}}), cache=cache([[5, 5, 95, 95, 2]]))
    assert "no tap_offset row: clk_t1" in out[0]
    assert "1 not judged" in X.findings(plan(ROWS), cache=cache([[5, 5, 95, 95, 2]], die=(50.0, 100.0)))[-1]
    assert X.findings(plan(ROWS), cache={})[-1].startswith("WARN ADV-XTAP-PAIR summary: 0 types judged")


def test_build_pairs(tmp_path):
    s = tmp_path / "sinks.txt"
    s.write_text("a/q\\[0\\] DFF 5.0 5.0 clk\nb/q DFF 95.0 95.0 clk_t1\n")
    c = tmp_path / "cone.txt"
    c.write_text("EP cap/q 95.0 95.0\nS cap/q a/q[0] 5.0 5.0\nS cap/q missing 1 1\n")
    doc = X.build_pairs("x", [100.0, 100.0], str(s), str(c))
    assert doc["xtap_pairs"]["x"]["pairs"] == [[5.0, 5.0, 95.0, 95.0, 1]]
    assert X.main(["build-pairs", "--type", "x", "--die", "100,100", "--sinks", str(s), "--cone", str(c), "-o", str(tmp_path / "p.json")]) == 0
    assert json.load(open(tmp_path / "p.json"))["xtap_pairs"]["x"]["die_um"] == [100.0, 100.0]


def test_findings_accepts_plan_advisory_kwargs():
    """plan_advisory.run calls every check as findings(raw, plan_path, tree=...): a missing kwarg is a TypeError that PRE turns
    into FAIL ADV-XTAP-PAIR-UNCHECKED on every plan (HEAD-EAST-R3 11-26)."""
    import adv_xtap_pair
    assert isinstance(adv_xtap_pair.findings({"partition_types": {}}, "p.json", tree="/nonexistent"), list)
