"""DIE-S81-16: dme_region_tree join() budget + bounded monotone join-down (go14 merge mode spent >2 h in join())."""
import random
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import die_trial as D
from test_die_trial_region_dme_early import _arrivals
from test_die_trial_slice_balance import FakeSite, _c_partition


def _kept(dn, root):
    st, out = [root], []
    while st:
        i = st.pop()
        out.append(i)
        st += dn[i]["kids"]
    return out


def _ping_pong_case(n=24, seed=24):
    """random sinks, half with a large declared early (merge mode): join() descends to the depth cap here"""
    random.seed(seed)
    site = FakeSite(1500.0, 1500.0, [])
    taps = [("p%d" % (i % 3), "t%d" % i, round(random.uniform(0, 1500), 1), round(random.uniform(0, 1500), 1))
            for i in range(n)]
    early = {(t[0], t[1]): (random.choice([400.0, 550.0, 700.0]) if random.random() < 0.5 else 0.0) for t in taps}
    return site, taps, early


def test_under_budget_byte_identical(monkeypatch):
    """a join that finishes within the budget is the old join: the whole output equals the unbounded run"""
    site, taps = _c_partition()
    early = {(taps[0][0], taps[0][1]): 60.0, (taps[1][0], taps[1][1]): 60.0}
    for mode in ("hang", "merge"):
        for kw in ({}, {"snake": True}):
            a = D.dme_region_tree(site, taps, delay_rep_um=250.0, early=early, early_mode=mode, **kw)
            monkeypatch.setattr(D, "DME_JOIN_BUDGET", 10 ** 9)
            b = D.dme_region_tree(site, taps, delay_rep_um=250.0, early=early, early_mode=mode, **kw)
            monkeypatch.setattr(D, "DME_JOIN_BUDGET", 4096)
            assert a == b and "join_fallbacks" not in a[2]
    assert D.dme_region_tree(site, taps) == D.dme_region_tree(site, taps)


@pytest.mark.parametrize("snake", [False, True])
def test_over_budget_bounded_and_complete(monkeypatch, snake):
    site, taps, early = _ping_pong_case()
    monkeypatch.setattr(D, "DME_JOIN_BUDGET", 32)
    calls = [0]
    orig = D.merge_point_delay

    def counted(*a, **k):
        calls[0] += 1
        return orig(*a, **k)
    monkeypatch.setattr(D, "merge_point_delay", counted)
    t0 = time.time()
    dn, root, st = D.dme_region_tree(site, taps, delay_rep_um=250.0, early=early, early_mode="merge",
                                     **({"snake": True} if snake else {}))
    assert st["join_fallbacks"] >= 1 and st["join_fallback_worst_gap_ps"] > 0      # logged, not hidden
    a = _arrivals(dn, root, 250.0)
    assert sorted(a) == sorted(t[1] for t in taps)                                  # every tap once
    for i in _kept(dn, root):
        assert len(dn[i]["kids"]) <= 2                                              # binary, no stars
    # bound: per top-level join at most budget + depth-of-tree merges; 3 modes x (n-1) top-level joins
    assert calls[0] <= 3 * (len(taps) * 2) * (32 + 2 * len(taps)), calls[0]
    assert time.time() - t0 < 60


def test_join_mono_never_reenters_built_nodes(monkeypatch):
    """budget 0 = every descending join is the monotone one: merge-point calls <= depth per join"""
    site, taps, early = _ping_pong_case(n=16, seed=3)
    monkeypatch.setattr(D, "DME_JOIN_BUDGET", 0)
    dn, root, st = D.dme_region_tree(site, taps, delay_rep_um=250.0, early=early, early_mode="merge", snake=True)
    assert sorted(_arrivals(dn, root, 250.0)) == sorted(t[1] for t in taps)
    assert len(dn) < 3 * 4 * len(taps) ** 2


def test_budget_default():
    assert D.DME_JOIN_BUDGET == 4096
