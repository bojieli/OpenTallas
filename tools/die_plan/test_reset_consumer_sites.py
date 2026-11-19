"""RESET-KEY 11-19 (FABLE-FIX-S81-LEAF): type.reset.consumer_sites_um freezes the reset consumers, so the reset tree no longer
follows the clock tap table.  S81 leaf t16 / t21 with added clock taps: gen phys refused the kit ('physical collector_tree
differs from captured bound reset identity') because every added tap is a new reset leaf; with the frozen list of the bound
plan the solve equals the captured tree again (t16 + 200 taps: '25 collectors = bound RTL').
    python3 -m pytest -q tools/die_plan/test_reset_consumer_sites.py"""
import sys
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import reset_tree as RT  # noqa: E402
import schema  # noqa: E402


def _plan(reset=None, n=3):
    t = {"clock": {"tap_mode": "grid"}, "outline_um": [400.0, 400.0]}
    if reset is not None:
        t["reset"] = reset
    return SimpleNamespace(types={"t": t}), [("clk" if i == 0 else f"clk_t{i}", 50.0 + 60.0 * i, 80.0) for i in range(n)]


def test_frozen_sites_are_the_reset_view_clock_taps_stay_real(monkeypatch):
    P, grid = _plan()
    monkeypatch.setattr(RT, "_S_TAP_GRID", lambda p, tn: list(grid))
    RT._TAPS.clear()
    assert RT._taps(P, "t") == grid == RT._clock_taps(P, "t")          # no key: one table, as before
    frozen = [[n, x, y] for n, x, y in grid]
    Q, more = _plan(reset={"consumer_sites_um": frozen}, n=7)           # the same type after 4 added clock taps
    monkeypatch.setattr(RT, "_S_TAP_GRID", lambda p, tn: list(more))
    RT._TAPS.clear()
    assert RT._taps(Q, "t") == grid                                    # reset view: as bound, no new leaf, no renumbering
    assert RT._clock_taps(Q, "t") == more and len(more) == 7           # clock ports / landings: every tap


def test_clock_landing_reads_the_clock_taps():
    src = (HERE / "clock_landings.py").read_text()
    assert "RT._clock_taps(e[1], tn)" in src and "RT._taps(e[1], tn)" not in src


def test_kit_reset_hook_uses_nearest_reset_leaf_when_frozen():
    src = (HERE / "gen_phys.py").read_text()
    assert 't.get("reset", {}).get("local_taps_um") or t.get("reset", {}).get("consumer_sites_um")' in src
    tcl = (HERE / "reset_taps.tcl").read_text()
    assert "rt_consumer_taps_um" in tcl                                 # the existing nearest-leaf path of local reset taps


def test_reach_fix_freezes_before_it_appends(monkeypatch):
    import reach_fix as RF
    P, grid = _plan()
    monkeypatch.setattr(RT, "_S_TAP_GRID", lambda p, tn: list(grid))
    monkeypatch.setattr(RT, "pipelined", lambda p: True)
    RT._TAPS.clear()
    t, rec = P.types["t"], {"changes": []}
    RF._freeze_reset_consumers(P, "t", t, rec)
    assert t["reset"]["consumer_sites_um"] == [[n, x, y] for n, x, y in grid] and rec["changes"] == [["reset.consumer_sites_um", 0, 3]]
    RF._freeze_reset_consumers(P, "t", t, rec)                          # second round of the same fix: unchanged
    assert len(rec["changes"]) == 1
    t2, rec2 = {"clock": {}}, {"changes": []}
    monkeypatch.setattr(RT, "pipelined", lambda p: False)
    monkeypatch.setattr(RT, "wavefront", lambda p: False)
    RF._freeze_reset_consumers(P, "t", t2, rec2)
    assert "reset" not in t2 and not rec2["changes"]                    # no synchronous reset tree: nothing written


def test_schema_knows_the_key():
    src = (HERE / "schema.py").read_text()
    assert '"consumer_sites_um"' in src and '"consumer_sites_um"' in (HERE / "die_plan.schema.json").read_text()
