"""lec.py array-index-aware pairing of a widened RTL memory whose LAST wide word is partial and whose gate kept
far fewer bits than the gold memory (hcp_sys1 u_div r_rem [0:26] x 25 b, gold opt_mem_widen x16 -> r_rem[0][0..399]
+ r_rem[1][0..274]; gate r_rem#t[a][b] 313 of 675 bits: 313 gate-only flops stayed unpaired, LEC-TOOL-3 10-27).
Mutant: the gate swaps two elements' indices -> must stay a difference.
    python3 -m pytest -q tools/die_plan/test_lec_array_index.py"""
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lec  # noqa: E402
from test_lec_memory_layout import _seq, _sim_prove  # noqa: E402


def test_partial_last_wide_word_layout():
    # reg [24:0] r [0:26]: widened x16, word 0 = addresses 0..15 (400 b), word 1 = addresses 16..26 (275 b)
    g = {f"ff:u.r[{w}][{j}]": (w, j) for w, n in ((0, 400), (1, 275)) for j in range(n)}
    t = {f"ff:u.r#t[{a}][{b}]": (a, b) for a in range(27) for b in range(25 - a % 3)}
    mp = lec.memory_layout(g, t, (25, 27, 0))
    assert mp and len(mp) == len(t) and len(set(mp.values())) == len(t)
    assert mp["ff:u.r#t[0][0]"] == "ff:u.r[0][0]"
    assert mp["ff:u.r#t[15][24]"] == "ff:u.r[0][399]"
    assert mp["ff:u.r#t[16][0]"] == "ff:u.r[1][0]"                # first address of the partial word
    assert mp["ff:u.r#t[26][3]"] == "ff:u.r[1][253]"              # (26 - 16) * 25 + 3


@pytest.mark.parametrize("g,t", [
    ({f"ff:u.r[{w}][{j}]": (w, j) for w, n in ((0, 400), (1, 300)) for j in range(n)}, {"ff:u.r#t[0][0]": (0, 0)}),
    ({f"ff:u.r[{w}][{j}]": (w, j) for w, n in ((0, 400), (2, 275)) for j in range(n)}, {"ff:u.r#t[0][0]": (0, 0)}),
    ({f"ff:u.r[{w}][{j}]": (w, j) for w, n in ((0, 400), (1, 275)) for j in range(n)}, {"ff:u.r#t[27][0]": (27, 0)}),
])
def test_partial_word_refuses_inconsistent_geometry(g, t):
    # an address past the memory (1 x 300 b = addresses up to 27), a missing middle word, a gate element past S
    assert lec.memory_layout(g, t, (25, 27, 0)) is None


def _design(tmp_path, mutant):
    """gold: memory m [0:2] x 3 b widened x2 -> m[0][0..5] (addresses 0, 1) + m[1][0..2] (address 2, partial);
    next state of address a bit b = x[3a + b]; bit 2 of every element constant 0.  Gate keeps elements 1 and 2,
    bits 0..1 only (4 of 9 gold bits: below the guessed-layout size guard).  o <= m(2)[0] & !m(1)[1].
    mutant: the gate swaps the indices of elements 1 and 2 (each loads the other's data)."""
    xs = [f"x{i}" for i in range(9)]
    gk = [f"m[0][{j}]" for j in range(6)] + [f"m[1][{j}]" for j in range(3)]
    flat = lambda k: (lambda w, j: 2 * w + j // 3)(*map(int, k[2:-1].split("][")))
    bit = lambda k: (lambda w, j: j % 3)(*map(int, k[2:-1].split("][")))
    g, gm = _seq(tmp_path, "gold", xs, gk + ["o"],
                 lambda m, l: {**{k: (0 if bit(k) == 2 else l[f"x{3 * flat(k) + bit(k)}"]) for k in gk},
                               "o": m.AND(l["m[1][0]"], l["m[0][4]"] ^ 1)})
    src = (lambda a: 3 - a) if mutant else (lambda a: a)
    tk = [f"m[{a}][{b}]" for a in (1, 2) for b in range(2)]
    t, tm = _seq(tmp_path, "gate", xs, tk + ["o"],
                 lambda m, l: {**{f"m[{a}][{b}]": l[f"x{3 * src(a) + b}"] for a in (1, 2) for b in range(2)},
                               "o": m.AND(l["m[2][0]"], l["m[1][1]"] ^ 1)})
    (tmp_path / "gold.aliases.json").write_text(json.dumps({"modules": {"lec_top": {
        "memories": {"u_dut.m": {"width": 3, "size": 3, "start_offset": 0}}, "cells": {}, "netnames": {}}}}))
    return lec.Lec(g, gm, t, tm)


def test_alias_array_pairs_partial_widened_memory_despite_size_guard(tmp_path):
    L = _design(tmp_path, False)
    assert "ff:u_dut.m#t[1][0]" in L.tonly                          # m[1][0] exists on both sides by accident
    log = []
    lec.alias_arrays(L, log, work=tmp_path)
    assert any("source memory layout (3, 3, 0)" in x for x in log)
    assert L.tp["ff:u_dut.m[0][3]"] is not None and "ff:u_dut.m[1][0]" in L.matched   # element 2 bit 0
    assert not [k for k in L.tonly if k.startswith("ff:u_dut.m")]


@pytest.mark.parametrize("mutant", [False, True])
def test_partial_memory_end_to_end_and_swapped_index_mutant(tmp_path, monkeypatch, mutant):
    monkeypatch.setattr(lec, "prove", _sim_prove)
    L = _design(tmp_path, mutant)
    log = []
    lec.correspond(L, tmp_path, 100, log)
    assert any("source memory layout" in x for x in log)
    m, _ = L.build(with_compare=True, with_hyp=True)
    verdicts = _sim_prove(m)
    assert (verdicts["ff:u_dut.o"] == "differs") == mutant


# ------------------------------------------------------------- reduction-tree arrays (HBM argmax ti / tvl / tk)
def _tree_gold(W, levels, lp, w):
    """gold keys of slang `reg [w-1:0] x [0:levels-1][0:lp-1]` (W = lp * w per level, element 0 at the MSB) where
    level lv keeps lp >> lv elements."""
    return {f"ff:u.x[{lv}][{(lp - 1 - e) * w + b}]": (lv, (lp - 1 - e) * w + b)
            for lv in range(levels) for e in range(lp >> lv) for b in range(w)}


def test_tree_last_level_single_element_is_placed():
    # argmax ti [0:3][0:7] x 18 b: gate keeps level 3 element 0 only = ti#t[24]
    g = _tree_gold(144, 4, 8, 18)
    t = {f"ff:u.x#t[{lv * 8 + e}][{b}]": (lv * 8 + e, b) for lv in range(4) for e in range(8 >> lv) for b in range(18)}
    mp = lec.memory_layout(g, t, (144, 4, 0))
    assert mp and len(mp) == 270
    assert mp["ff:u.x#t[24][0]"] == "ff:u.x[3][126]" and mp["ff:u.x#t[24][17]"] == "ff:u.x[3][143]"
    assert mp["ff:u.x#t[9][3]"] == "ff:u.x[1][111]"                   # level 1 element 1: (7 - 1) * 18 + 3


def test_tree_one_bit_elements_and_missing_last_level():
    # argmax tvl [0:3][0:7] x 1 b, level 3 unused: gate tvl[a] (one index), gold tvl[0..2][j]
    g = _tree_gold(8, 3, 8, 1)
    t = {f"ff:u.x#t[{lv * 8 + e}]": (lv * 8 + e,) for lv in range(3) for e in range(8 >> lv)}
    mp = lec.memory_layout(g, t, (8, 4, 0))
    assert mp and len(mp) == 14
    assert mp["ff:u.x#t[16]"] == "ff:u.x[2][7]" and mp["ff:u.x#t[17]"] == "ff:u.x[2][6]"


def test_tree_inner_count_chosen_by_gold_bits_not_guessed():
    # argmax tk 264 b words, gate element 17 bit 32: K = 6 (44 b) and K = 8 (33 b) both pass the size test,
    # only K = 8 lands on gold bits
    g = _tree_gold(264, 3, 8, 33)
    t = {f"ff:u.x#t[{lv * 8 + e}][{b}]": (lv * 8 + e, b) for lv in range(3) for e in range(8 >> lv) for b in range(33)}
    mp = lec.memory_layout(g, t, (264, 4, 0))
    assert mp and mp["ff:u.x#t[17][32]"] == "ff:u.x[2][230]"         # (7 - 1) * 33 + 32
    # a gold side that cannot tell K apart: refuse
    g2 = {f"ff:u.x[{h}][{j}]": (h, j) for h in range(4) for j in range(264)}
    t2 = {"ff:u.x#t[17][32]": (17, 32), "ff:u.x#t[0][0]": (0, 0)}
    assert lec.memory_layout(g2, t2, (264, 4, 0)) is None


def _tree_design(tmp_path, mutant):
    """gold: slang `reg [1:0] t [0:1][0:1]` -> t[lv][0..3] (element 0 at bits 2..3), level 1 element 0 only.
    level 0: element e <= {x[2e+1], x[2e]}; level 1: e0 <= s ? level0 e0 : level0 e1 (an argmax pick);
    o <= t1e0[0] & !t1e0[1].  Gate (read_verilog): t[0], t[1] = level 0, t[2] = level 1 element 0.
    mutant: the gate's level-1 pick swaps the child indices (s ? e1 : e0)."""
    xs = ["x0", "x1", "x2", "x3", "s"]
    mux = lambda m, c, a, b: m.AND(m.AND(c, a) ^ 1, m.AND(c ^ 1, b) ^ 1) ^ 1
    gk = [f"t[0][{j}]" for j in range(4)] + ["t[1][2]", "t[1][3]"]
    g0 = lambda l, e, b: l[f"t[0][{(1 - e) * 2 + b}]"]
    g, gm = _seq(tmp_path, "gold", xs, gk + ["o"], lambda m, l: {
        **{f"t[0][{(1 - e) * 2 + b}]": l[f"x{2 * e + b}"] for e in range(2) for b in range(2)},
        **{f"t[1][{2 + b}]": mux(m, l["s"], g0(l, 0, b), g0(l, 1, b)) for b in range(2)},
        "o": m.AND(l["t[1][2]"], l["t[1][3]"] ^ 1)})
    pick = (1, 0) if mutant else (0, 1)
    tk = [f"t[{a}][{b}]" for a in range(3) for b in range(2)]
    t, tm = _seq(tmp_path, "gate", xs, tk + ["o"], lambda m, l: {
        **{f"t[{e}][{b}]": l[f"x{2 * e + b}"] for e in range(2) for b in range(2)},
        **{f"t[2][{b}]": mux(m, l["s"], l[f"t[{pick[0]}][{b}]"], l[f"t[{pick[1]}][{b}]"]) for b in range(2)},
        "o": m.AND(l["t[2][0]"], l["t[2][1]"] ^ 1)})
    (tmp_path / "gold.aliases.json").write_text(json.dumps({"modules": {"lec_top": {
        "memories": {"u_dut.t": {"width": 4, "size": 2, "start_offset": 0}}, "cells": {}, "netnames": {}}}}))
    return lec.Lec(g, gm, t, tm)


@pytest.mark.parametrize("mutant", [False, True])
def test_tree_end_to_end_and_swapped_child_mutant(tmp_path, monkeypatch, mutant):
    monkeypatch.setattr(lec, "prove", _sim_prove)
    L = _tree_design(tmp_path, mutant)
    log = []
    lec.correspond(L, tmp_path, 100, log)
    assert any("alias array: gate t#t" in x and "source memory layout (4, 2, 0)" in x for x in log)
    m, _ = L.build(with_compare=True, with_hyp=True)
    verdicts = _sim_prove(m)
    assert ("differs" in verdicts.values()) == mutant
    if mutant:                                                         # the re-keyed level-1 element is a compare point
        assert verdicts["ff:u_dut.t[1][2]"] == "differs"
