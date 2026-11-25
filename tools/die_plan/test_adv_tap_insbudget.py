import adv_tap_insbudget as T


def plan(taps, mode="explicit", outline=(100.0, 100.0)):
    return {"partition_types": {"x": {"outline_um": list(outline), "clock": {"tap_mode": mode, "taps": taps}}}}


def cache(bins, die=(100.0, 100.0)):
    return {"placed_bins": {"x": {"die_um": list(die), "bins": bins, "kit": "k"}}}


def test_bands():
    assert T.verdict(1000) == "OK" and T.verdict(3000) == "OK"
    assert T.verdict(4000) == "WARN"
    assert T.verdict(5001) == "FAIL" and T.verdict(27453) == "FAIL"
    assert T.predict(20000) == (1048.0, 323.0)


def test_overloaded_tap_fails():
    raw = plan([{"name": "clk", "xy": [10, 10]}, {"name": "clk_t1", "xy": [90, 90]}])
    lines = T.findings(raw, cache=cache([[5, 5, 6000], [95, 95, 100]]))
    assert lines[0].startswith("FAIL ADV-TAP-INSBUDGET x: tap clk 6,000")
    assert "1 FAIL" in lines[-1]


def test_split_taps_pass_and_core_taps_ignored():
    raw = plan([{"name": "clk", "xy": [10, 10]}, {"name": "clk_t1", "xy": [90, 90]},
                {"name": "clk_c0", "xy": [5, 5], "kind": "core"}])
    lines = T.findings(raw, cache=cache([[5, 5, 2000], [95, 95, 2000]]))
    assert len(lines) == 1 and "0 FAIL" in lines[0]


def test_outline_mismatch_and_density_not_judged():
    raw = plan([{"name": "clk", "xy": [10, 10]}])
    assert "1 not judged" in T.findings(raw, cache=cache([[5, 5, 9000]], die=(50.0, 100.0)))[-1]
    raw = plan([{"name": "clk", "xy": [10, 10]}], mode="density")
    assert "1 not judged" in T.findings(raw, cache=cache([[5, 5, 9000]]))[-1]
