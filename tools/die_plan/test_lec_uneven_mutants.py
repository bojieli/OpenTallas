"""LEC-REVIEW-R1 11-27 (lec-uneven-memory @5a7729a9c34, PASS-WITH-TESTS): mutants for the uneven widened-memory layout
(l5f: 14 words x 25 b mapped by yosys as 8 + 6) and the unique power-of-two widening factor.
    python3 -m pytest -q tools/die_plan/test_lec_uneven_mutants.py"""
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lec  # noqa: E402
from test_lec_memory_layout import _seq, _sim_prove  # noqa: E402

W, S, F = 25, 14, 8


def _gold(words=(200, 150), w=W):
    return {f"g{a}:{b}": (a, b) for a, n in enumerate(words) for b in range(n)}


def _gate(w=W, s=S, o=0):
    return {f"t{a}:{b}": (a, b) for a in range(o, o + s) for b in range(w)}


def _expect(w=W, s=S, o=0, f=F):
    return {f"t{a}:{b}": f"g{(a - o) // f}:{((a - o) % f) * w + b}" for a in range(o, o + s) for b in range(w)}


# -------------------------------------------------------------------------------- layout level
def test_full_350_key_bijection_and_logged_factor():
    info = {}
    mp = lec.memory_layout(_gold(), _gate(), (W, S, 0), info)
    assert len(mp) == 350 and len(set(mp.values())) == 350
    assert mp == _expect() and info["F"] == 8
    assert mp["t7:24"] == "g0:199" and mp["t8:0"] == "g1:0" and mp["t13:24"] == "g1:149"   # the 8|6 boundary


def test_gate_also_widened_is_refused():
    gate = {f"t{a}:{b}": (a, b) for a in range(2) for b in range(200)}
    assert lec.memory_layout(_gold(), gate, (W, S, 0)) is None


def test_s15_with_200_and_100_is_ambiguous():
    # F = 8, 9 and 10 all fit gold words of 200 and 100 bits in a 15-word memory
    assert lec.memory_layout(_gold((200, 100)), _gate(s=15), (W, 15, 0)) is None


def test_dividing_branch_refuses_when_more_than_one_factor_fits():
    g = {f"g{a}:{b}": (a, b) for a in range(2) for b in range(2)}   # S = 8 divides by 2 words: F = 4, but 1..7 fit
    t = {"x": (0, 0)}
    assert lec.memory_layout(g, t, (2, 8, 0)) is None


@pytest.mark.parametrize("w, s, words", [(4, 6, (12, 12)),          # non dividing: F = 3 forced
                                         (2, 9, (6, 6, 6))])        # dividing: F = 3 forced
def test_non_power_of_two_factor_is_refused(w, s, words):
    g = {f"g{a}:{b}": (a, b) for a, n in enumerate(words) for b in range(n)}
    assert lec.memory_layout(g, {"x": (0, 0)}, (w, s, 0)) is None


def test_power_of_two_factor_is_accepted_and_logged():
    info = {}
    g = {f"g{a}:{b}": (a, b) for a in range(2) for b in range(8)}   # W = 2, S = 8: F = 4 forced by 8 bits
    mp = lec.memory_layout(g, {"x": (0, 0), "y": (7, 1)}, (2, 8, 0), info)
    assert mp == {"x": "g0:0", "y": "g1:7"} and info["F"] == 4


def test_width_one_and_eleven_exact():
    g1 = _gold((8, 6), 1)
    mp = lec.memory_layout(g1, {f"t{a}": (a,) for a in range(14)}, (1, 14, 0))
    assert mp == {f"t{a}": f"g{a // 8}:{a % 8}" for a in range(14)}
    g11 = _gold((88, 66), 11)
    assert lec.memory_layout(g11, _gate(11), (11, 14, 0)) == _expect(11)


def test_nonzero_offset_is_never_misplaced():
    # gate elements are named by the declared index (offset .. offset + S - 1); a placement that ignores the offset
    # would pair address a with gold address a (wrong), so the result must be exact or a refusal
    mp = lec.memory_layout(_gold(), _gate(o=3), (W, S, 3))
    assert mp is None or mp == _expect(o=3)


# ------------------------------------------------------------------------------- end to end mutants
w2, s2 = 2, 7                                           # the same 8 | 6 shape at W = 2, S = 7 (F = 4)


def _design(tmp_path, mut):
    """Every element bit loads its own input and is observed on its own output flop obs_a_b <= m(a, b) & y_a_b, so a
    permutation or inversion of the layout is a real difference (a shared parity output would hide a swap)."""
    elems = [(a, b) for a in range(s2) for b in range(w2)]
    xs = [f"x{a}_{b}" for a, b in elems] + [f"y{a}_{b}" for a, b in elems]
    gkeys = {(a, b): (a // 4, (a % 4) * w2 + b) for a, b in elems}
    gn = {e: f"m[{gkeys[e][0]}][{gkeys[e][1]}]" for e in elems}
    obs = [f"obs{a}_{b}" for a, b in elems]
    gold, gm = _seq(tmp_path, "gold", xs, list(gn.values()) + obs, lambda m, l: {
        **{gn[e]: l[f"x{e[0]}_{e[1]}"] for e in elems},
        **{f"obs{a}_{b}": m.AND(l[gn[(a, b)]], l[f"y{a}_{b}"]) for a, b in elems}})
    load = {e: e for e in elems}
    keep = list(elems)
    inv = None
    if mut == "word_swap":                              # the two words that meet at the 8 | 6 boundary
        load.update({(3, b): (4, b) for b in range(w2)} | {(4, b): (3, b) for b in range(w2)})
    elif mut == "bit_swap":
        load.update({(2, 0): (2, 1), (2, 1): (2, 0)})
    elif mut == "inversion":
        inv = (5, 1)
    elif mut == "dropped_bit":
        keep.remove((6, 1))
    elif mut == "dropped_word":
        keep = [e for e in elems if e[0] != 6]
    tn = {e: f"m[{e[0]}][{e[1]}]" for e in keep}

    def nxt(m, l):
        d = {tn[e]: l[f"x{load[e][0]}_{load[e][1]}"] ^ int(e == inv) for e in keep}
        for a, b in elems:
            d[f"obs{a}_{b}"] = m.AND(l[tn[(a, b)]], l[f"y{a}_{b}"]) if (a, b) in tn else 0
        return d
    gate, tm = _seq(tmp_path, "gate", xs, list(tn.values()) + obs, nxt)
    (tmp_path / "gold.aliases.json").write_text(json.dumps({"modules": {"lec_top": {
        "memories": {"u_dut.m": {"width": w2, "size": s2, "start_offset": 0}}, "cells": {}, "netnames": {}}}}))
    return lec.Lec(gold, gm, gate, tm)


@pytest.mark.parametrize("mut", [None, "word_swap", "bit_swap", "inversion", "dropped_bit", "dropped_word"])
def test_uneven_layout_end_to_end_mutants_stay_differences(tmp_path, monkeypatch, mut):
    monkeypatch.setattr(lec, "prove", _sim_prove)
    L = _design(tmp_path, mut)
    log = []
    lec.correspond(L, tmp_path, 100, log)
    m, _ = L.build(with_compare=True, with_hyp=True)
    st = _sim_prove(m)
    assert ("differs" in set(st.values())) == (mut is not None), (mut, log, st)
    if mut is None:
        assert any("widening F=4" in x for x in log), log
