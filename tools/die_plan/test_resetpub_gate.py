"""RESETPUB-1122 (COORD): a published reset tree that differs from the tree the bind emits is refused before the bind; retap
republishes it when clock keys change without a tap-set change."""
import copy
import json
import sys
from pathlib import Path

H = Path(__file__).resolve().parent
sys.path.insert(0, str(H))
import plan_gate_pre as G  # noqa: E402
import retap  # noqa: E402
from test_retap import NEW_TREE, OLD_TREE, emitted, sc_type  # noqa: E402
from reset_consumers import localize  # noqa: E402


def write(tmp_path, t, name="p.json"):
    p = tmp_path / name
    p.write_text(json.dumps({"partition_types": {"sle_sc_v1__cl7479a5ec": t}}))
    return str(p)


def test_stale_published_tree_is_resetpub_fail(tmp_path):
    t = sc_type()                                              # publishes OLD_TREE, the tools now solve NEW_TREE
    f = G.check_resetpub(str(tmp_path), write(tmp_path, t), tree_fn=lambda tn: copy.deepcopy(NEW_TREE), solve=True)
    assert len(f) == 1 and f[0].startswith("FAIL RESETPUB sle_sc_v1__cl7479a5ec:") and "a1" not in f[0].split(":", 1)[0]
    assert "rst_n_t0 published d=a0 depth=2, solved d=b0 depth=2" in f[0] and "--republish-reset" in f[0]


def test_current_tree_passes_and_solve_error_is_unchecked(tmp_path):
    t = sc_type()
    assert G.check_resetpub(str(tmp_path), write(tmp_path, t), tree_fn=lambda tn: copy.deepcopy(OLD_TREE), solve=True) == []
    f = G.check_resetpub(str(tmp_path), write(tmp_path, t), tree_fn=lambda tn: 1 / 0, solve=True)
    assert f[0].startswith("FAIL RESETPUB-UNCHECKED sle_sc_v1__cl7479a5ec")
    t2 = sc_type()
    t2["reset"]["consumer_localization"] = []                  # nothing localized: nothing checked
    assert G.check_resetpub(str(tmp_path), write(tmp_path, t2), tree_fn=lambda tn: 1 / 0, solve=True) == []


def _tree_by_slowest(r, _p):
    """a stand-in reset solve that depends on a clock key, not on the taps (the TAP-GRID-R5 case)"""
    return lambda tn: copy.deepcopy(NEW_TREE if r["partition_types"][tn]["clock"].get("tap_balance_to") == "slowest" else OLD_TREE)


def test_retap_republishes_when_clock_keys_change_without_tap_change():
    old = {"partition_types": {"T": sc_type()}}
    new = copy.deepcopy(old)
    new["partition_types"]["T"]["clock"]["tap_balance_to"] = "slowest"
    new["partition_types"]["T"]["clock"]["tap_slowest_max_ps"] = 265
    same = lambda r, _p: (lambda tn: [("clk_t0", 0.0, 0.0)])  # noqa: E731  (tap set unchanged)
    rep = retap.repoint(old, new, taps_fn=same, tree_fn=_tree_by_slowest)
    pub = new["partition_types"]["T"]["clock"]["landing_contract"]["collector_tree"]
    assert pub == NEW_TREE and rep["T"][0][0] == "landing_contract.collector_tree"
    t = new["partition_types"]["T"]
    localize(emitted(NEW_TREE), t["reset"]["consumer_localization"], pub)        # the bind's EMIT check now passes
    old2 = copy.deepcopy(old)                                                    # unchanged inputs: byte-identical
    new2 = copy.deepcopy(old)
    assert retap.repoint(old2, new2, taps_fn=same, tree_fn=_tree_by_slowest) == {} and new2 == old


def test_retap_republish_reset_flag_fixes_an_already_stale_tree():
    old = {"partition_types": {"T": sc_type()}}
    old["partition_types"]["T"]["clock"]["tap_balance_to"] = "slowest"           # already stale: published OLD, solves NEW
    new = copy.deepcopy(old)
    same = lambda r, _p: (lambda tn: [("clk_t0", 0.0, 0.0)])  # noqa: E731
    assert retap.repoint(old, copy.deepcopy(new), taps_fn=same, tree_fn=_tree_by_slowest) == {}
    retap.repoint(old, new, taps_fn=same, tree_fn=_tree_by_slowest, republish_reset=True)
    assert new["partition_types"]["T"]["clock"]["landing_contract"]["collector_tree"] == NEW_TREE


def test_default_solves_only_types_whose_inputs_moved_but_tree_did_not(tmp_path):
    """the V3 case: base -> plan adds clock.tap_balance_to / tap_slowest_max_ps, collector_tree byte-identical -> refused without a solve
    (the die solve took > 3400 s on QC); an unchanged type or a republished tree passes; solve=True proves by the solved tree"""
    calls = []
    fn = lambda tn: calls.append(tn) or copy.deepcopy(NEW_TREE)  # noqa: E731
    base = write(tmp_path, sc_type(), "base.json")
    t = sc_type()
    t["clock"]["tap_balance_to"] = "slowest"
    t["clock"]["tap_slowest_max_ps"] = 265.0
    f = G.check_resetpub(str(tmp_path), write(tmp_path, t), tree_fn=fn, base=base)
    assert calls == [] and f[0].startswith("FAIL RESETPUB sle_sc_v1__cl7479a5ec: clock / reset inputs changed vs base "
                                           "(clock.tap_balance_to,clock.tap_slowest_max_ps)")   # refused in seconds, nothing solved
    assert "--republish-reset" in f[0]
    calls.clear()
    assert G.check_resetpub(str(tmp_path), write(tmp_path, sc_type()), tree_fn=fn, base=base) == [] and calls == []   # unchanged
    t2 = copy.deepcopy(t)
    t2["clock"]["landing_contract"]["collector_tree"] = copy.deepcopy(NEW_TREE)                                      # republished
    assert G.check_resetpub(str(tmp_path), write(tmp_path, t2), tree_fn=fn, base=base) == [] and calls == []
    assert G.check_resetpub(str(tmp_path), write(tmp_path, t), tree_fn=fn) == [] and calls == []                     # no base: not solved
    assert G.check_resetpub(str(tmp_path), write(tmp_path, sc_type()), tree_fn=fn, solve=True)[0].startswith("FAIL RESETPUB ")
