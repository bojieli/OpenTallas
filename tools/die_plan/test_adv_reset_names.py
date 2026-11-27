"""adv_reset_names.py (ADV-RESET-NAME, TAP-GRID-R5 11-23).   python3 -m pytest -q tools/die_plan/test_adv_reset_names.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adv_reset_names as A  # noqa: E402
import plan_advisory as PA  # noqa: E402


def _raw():
    return {"partition_types": {
        "kv3_hg": {"clock": {"added_taps": [{"name": "clk_t9"}],
                             "landing_local_resets": [{"raw": "rst_rl_34"}, {"raw": "rst_rl_35"}],
                             "landing_contract": {"pins": [{"source_clock_port": "clk_t3"}]},
                             "collector_tree": {"q": "rst_rl_999"}}},
        "kv3_ok": {"clock": {"landing_local_resets": [{"raw": "rst_rl_1"}]}},
        "kv3_phy": {"hard": True, "clock": {"landing_local_resets": [{"raw": "rst_rl_77"}]}},
        "kv3_none": {"clock": {"tap_mode": "density"}}}}


def test_stale_relay_and_tap_names_named_per_type():
    relays = {"kv3_hg": {"rst_rl_34", "rst_rl_40"}, "kv3_ok": {"rst_rl_1"}}
    taps = {"kv3_hg": {"clk_t0", "clk_t1"}}
    out = A.findings(_raw(), "/x/plan.json", tree_fn=lambda tn: relays[tn], taps_fn=lambda tn: taps[tn])
    hg = [x for x in out if " kv3_hg:" in x]
    assert len(hg) == 1 and "2 of 3" in hg[0] and "rst_rl_35" in hg[0] and "clk_t3" in hg[0] and "rst_rl_34 " not in hg[0]
    assert not any("kv3_ok" in x or "kv3_phy" in x or "kv3_none" in x for x in out)      # clean, hard, no references
    assert "rst_rl_999" not in " ".join(out)                                               # collector_tree defines names
    assert out[-1].startswith("WARN ADV-RESET-NAME summary: 2 of 2") and "1 with stale" in out[-1]


def test_clean_plan_is_silent_and_budget_is_reported():
    ok = A.findings(_raw(), "/x/plan.json", tree_fn=lambda tn: {"rst_rl_34", "rst_rl_35", "rst_rl_1"},
                    taps_fn=lambda tn: {"clk_t3"})
    assert ok == []
    cut = A.findings(_raw(), "/x/plan.json", tree_fn=lambda tn: set(), taps_fn=lambda tn: set(), budget_s=-1)
    assert cut == ["WARN ADV-RESET-NAME summary: 0 of 2 referencing type(s) checked, 0 with stale names, 2 not checked (budget -1 s)"]


def test_tree_error_is_not_checked_not_raised():
    def boom(tn):
        raise ValueError("no tree")
    out = A.findings(_raw(), "/x/plan.json", tree_fn=boom, taps_fn=lambda tn: set())
    assert any(x.startswith("FAIL ADV-RESET-NAME kv3_hg: TREE-ERROR (ValueError") for x in out)     # P-FALSE-GREEN: error, not "not checked"
    assert not any("not checked (ValueError" in x for x in out)
    kept = PA._norm("RESET-NAME", out)
    assert any(x.startswith("FAIL ADV-RESET-NAME ") for x in kept)                                 # the advisory wrapper keeps the FAIL


def test_registered_as_advisory():
    assert ("RESET-NAME", "adv_reset_names") in PA.CHECKS
