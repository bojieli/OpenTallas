"""added_tap_recentre: frozen reset contract guard + collector_tree republish (DIE-S81-49 11-02)."""
import copy
import json

import pytest

import added_tap_recentre as A
import pin_template as PT
import reset_tree as RT


def _tree(**kw):
    t = dict(root=[10.0, 20.0], entry="relayed", sync_stages=2, depth=3, own_depth=3, tap_depth={"0": 1, "1": 2},
             taps=["clk", "clk_t1"], n_clock_taps=2, n_reset_consumers=2, local_reset_taps=False, outs=[[1.0, 2.0]],
             core_resets=[], relays=[dict(name="u_rrl_0", xy=[5.0, 5.0], d="rst_root_n", q="rst_rl_0", depth=1, tap=0)])
    t.update(kw)
    return t


def _raw(tree=None):
    ck = dict(tap_mode="grid+explicit", added_taps=[])
    if tree is not None:
        ck["landing_contract"] = dict(collector_tree=tree, collector_root_node="rst_root_n")
    return dict(partition_types=dict(ty=dict(outline_um=[100.0, 100.0], clock=ck)))


def _solved(monkeypatch, tree):
    # tuples / int keys, as reset_tree returns them
    t = copy.deepcopy(tree)
    t["root"] = tuple(t["root"]); t["tap_depth"] = {int(k): v for k, v in t["tap_depth"].items()}
    monkeypatch.setattr(RT, "for_type", lambda P, tn: copy.deepcopy(t))


def test_guard_without_published_tree_is_open(monkeypatch):
    _solved(monkeypatch, _tree(n_clock_taps=3))
    assert A.reset_guard(None, _raw(), "ty") is None


def test_guard_accepts_resited_relays(monkeypatch):
    raw = _raw(_tree())
    _solved(monkeypatch, _tree(relays=[dict(name="u_rrl_0", xy=[7.0, 5.0], d="rst_root_n", q="rst_rl_0", depth=1, tap=0)]))
    assert A.reset_guard(None, raw, "ty") is None
    assert not A.tree_matches(None, raw, "ty")


def test_guard_rejects_added_tap_renumbering(monkeypatch):
    raw = _raw(_tree())
    _solved(monkeypatch, _tree(n_clock_taps=3, n_reset_consumers=3, taps=["clk", "clk_t1", "clk_t2"]))
    assert A.reset_guard(None, raw, "ty") == "taps"


def test_guard_rejects_depth_change(monkeypatch):
    raw = _raw(_tree())
    _solved(monkeypatch, _tree(tap_depth={"0": 1, "1": 3}))
    assert A.reset_guard(None, raw, "ty") == "tap_depth"


def test_tree_matches_normalises_tuples_and_int_keys(monkeypatch):
    raw = _raw(_tree())
    _solved(monkeypatch, _tree())
    assert A.tree_matches(None, raw, "ty")


def test_republish_plan_and_sidecar(monkeypatch):
    raw = _raw(_tree())
    side = dict(collector=dict(types=dict(ty=dict(tree=_tree()))))
    moved = [dict(name="u_rrl_0", xy=[7.0, 5.0], d="rst_root_n", q="rst_rl_0", depth=1, tap=0),
             dict(name="u_rrl_1", xy=[9.0, 5.0], d="rst_rl_0", q="rst_rl_1", depth=2, tap=1)]
    _solved(monkeypatch, _tree(relays=moved))
    assert A.republish(None, raw, "ty", side) == (1, 2, 2)
    pub = raw["partition_types"]["ty"]["clock"]["landing_contract"]["collector_tree"]
    assert pub["relays"] == moved and pub["root"] == [10.0, 20.0]
    assert side["collector"]["types"]["ty"]["tree"] == pub
    assert A.tree_matches(None, raw, "ty")


def test_republish_refuses_diverged_sidecar(monkeypatch):
    raw = _raw(_tree())
    side = dict(collector=dict(types=dict(ty=dict(tree=_tree(depth=4)))))
    _solved(monkeypatch, _tree())
    with pytest.raises(ValueError, match="sidecar collector tree differs"):
        A.republish(None, raw, "ty", side)


def test_dumps_like_keeps_repo_plan_format():
    raw = dict(schema="x", partition_types=dict(ty=dict(ft_slots=[dict(name="ft0", w=1)], clock=dict(a=[1, 2]))))
    src = PT.dumps(raw)
    raw["partition_types"]["ty"]["clock"]["a"] = [3, 4]
    out = A.dumps_like(raw, src)
    assert out == PT.dumps(raw) and '{"name":"ft0","w":1}' in out
    plain = json.dumps(dict(a=1), indent=1) + "\n"
    assert A.dumps_like(dict(a=2), plain) == json.dumps(dict(a=2), indent=1) + "\n"


def test_cache_reset_clears_reset_tree_tap_memo():
    class P:
        pass
    p = P(); p._reset_tree_cache = {"x": 1}
    RT._TAPS[("k", "ty")] = (p, [])
    A.S_reset_cache(p)
    assert ("k", "ty") not in RT._TAPS and "_reset_tree_cache" not in p.__dict__
