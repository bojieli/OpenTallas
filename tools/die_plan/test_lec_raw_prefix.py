"""Finite raw prefixes never constrain initial state, RTL X, reset, or future inputs."""
import collections
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lec
from test_lec_memory_layout import _seq
from test_lec_raw_bases import _exact
from test_lec_release_edges import _design


def _prefix(L, k, value, steps, tmp_path, monkeypatch):
    monkeypatch.setattr(lec, "prove", _exact)
    lec.raw_prefix_bases(L, [("gold", k, value)], steps, tmp_path, 100, [])
    return L.raw_prefix_status[("gold", k, value, steps)]


def test_six_edges_from_arbitrary_state_and_one_short_control(tmp_path, monkeypatch):
    L = _design(tmp_path, chain=6)
    k = "ff:u_dut.k6"
    assert _prefix(L, k, 0, 6, tmp_path, monkeypatch) == "proved"
    assert _prefix(L, k, 0, 5, tmp_path, monkeypatch) == "differs"
    assert _prefix(L, k, 1, 6, tmp_path, monkeypatch) == "differs"
    assert L.raw_prefix_edges[("gold", k, 0)] == 6


def test_late_base_still_requires_no_early_observation(tmp_path, monkeypatch):
    k = "ff:u_dut.k6"
    for relay, accepted in ((True, True), (False, False)):
        L = _design(tmp_path, chain=6, relay=relay)
        L.hyp = {("gold", f"ff:u_dut.k{i}"): ("const", 0) for i in range(1, 7)}
        assert _prefix(L, k, 0, 6, tmp_path, monkeypatch) == "proved"
        lec.noreset_filter(L, [], collections.Counter())
        assert (("gold", k) in L.hyp) is accepted


def test_independent_time_inputs_cannot_cancel_each_other(tmp_path, monkeypatch):
    def gold(m, l):
        return {"p": l["x"], "q": m.XOR(l["p"], l["x"])}
    g, gm = _seq(tmp_path, "time_inputs", ["x"], ["p", "q"], gold)
    del gm["input"][0]                     # anonymous RTL X must be fresh each edge
    L = lec.Lec(g, gm, g, gm)
    assert _prefix(L, "ff:u_dut.q", 0, 2, tmp_path, monkeypatch) == "differs"


def test_supplied_current_state_constant_does_not_seed_prefix(tmp_path, monkeypatch):
    g, gm = _seq(tmp_path, "self", [], ["q"], lambda m, l: {"q": l["q"]})
    L = lec.Lec(g, gm, g, gm)
    k = "ff:u_dut.q"; L.hyp[("gold", k)] = ("const", 0)
    assert _prefix(L, k, 0, 6, tmp_path, monkeypatch) == "differs"


def test_logical_q_polarity_is_preserved(tmp_path, monkeypatch):
    L = _design(tmp_path, chain=6)
    k = "ff:u_dut.k6"
    L.gp[k] ^= 1; L.gc[k] ^= 1
    assert _prefix(L, k, 1, 6, tmp_path, monkeypatch) == "proved"
    assert _prefix(L, k, 0, 6, tmp_path, monkeypatch) == "differs"


def test_matched_register_never_takes_a_late_prefix(tmp_path, monkeypatch):
    L = _design(tmp_path, chain=6)
    k = "ff:u_dut.k6"
    assert _prefix(L, k, 0, 6, tmp_path, monkeypatch) == "proved"
    L.matched.append(k)                    # even side-specific hints are excluded
    L.hyp = {("gold", f"ff:u_dut.k{i}"): ("const", 0) for i in range(1, 7)}
    assert ("gold", k) not in lec.noreset_sound(L)


def test_undecided_proof_does_not_supply_any_base(tmp_path, monkeypatch):
    L = _design(tmp_path, chain=6)
    monkeypatch.setattr(lec, "prove", lambda m, *a, **kw: {n: "undecided" for n in m.onames})
    lec.raw_prefix_bases(L, [("gold", "ff:u_dut.k6", 0)], 6, tmp_path, 100, [])
    assert L.raw_prefix_edges == {}


def test_invalid_prefix_depth_is_rejected(tmp_path):
    L = _design(tmp_path)
    with pytest.raises(ValueError):
        lec.raw_prefix_miter(L.gold, [L.gc["ff:u_dut.k6"]], 0)
