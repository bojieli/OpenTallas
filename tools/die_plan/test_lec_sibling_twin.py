"""LEC-SIBLING-TWIN (DIE-HBM-97 11-09, HBM q_b100 a9 NOT EQUIVALENT 3/101212: u_bout_L1200_o.q[3302..3304]).
The RTL drives the 4 bits of keep_keys from one shared expression (!ke_r || kb_r[bi_r]), and a no-reset delay
pipeline carries them, so synthesis merges bits 0..2 of every stage into bit 3 of the SAME register.  The twin
sits at another bit index, which the same-index scope search never tries, so the gold bits stayed free and the
outputs fed by them 'differed'.  sibling_twin_search pairs them by next-state signature, stage by stage, and
auto_twins proves the proposals by induction.  Mutants: a gold bit that is NOT the shared expression is never
kept and still differs; a gate that drives an output from the wrong stage still differs.
    python3 -m pytest -q tools/die_plan/test_lec_sibling_twin.py"""
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lec  # noqa: E402
from test_lec_memory_layout import _seq, _sim_prove  # noqa: E402

S1 = [f"s1[{i}]" for i in range(4)]
S2 = [f"s2[{i}]" for i in range(4)]
Y = [f"y[{i}]" for i in range(4)]


def _or(m, a, b):
    return m.AND(a ^ 1, b ^ 1) ^ 1


def _design(tmp_path, gold_shared=True, gate_ok=True):
    """gold: s1[k] <= ke_n | kb (one expression per bit, all equal), s2[k] <= s1[k], y[k] <= s2[k].
    gate: s1[0..2], s2[0..2] merged into bit 3; y[k] <= s2[3].
    gold_shared=False: gold s1[1] <= ke_n & kb (not a twin).  gate_ok=False: gate y[2] <= s1[3] (one stage short)."""
    def gold(m, l):
        d = {S1[k]: _or(m, l["ke_n"], l["kb"]) for k in range(4)}
        if not gold_shared:
            d[S1[1]] = m.AND(l["ke_n"], l["kb"])
        d.update({S2[k]: l[S1[k]] for k in range(4)})
        d.update({Y[k]: l[S2[k]] for k in range(4)})
        return d

    def gate(m, l):
        d = {S1[3]: _or(m, l["ke_n"], l["kb"]), S2[3]: l[S1[3]]}
        d.update({Y[k]: l[S2[3]] for k in range(4)})
        if not gate_ok:
            d[Y[2]] = l[S1[3]]
        return d

    g, gm = _seq(tmp_path, "gold", ["ke_n", "kb"], S1 + S2 + Y, gold)
    t, tm = _seq(tmp_path, "gate", ["ke_n", "kb"], [S1[3], S2[3]] + Y, gate)
    return lec.Lec(g, gm, t, tm)


def _differs(L):
    m, _ = L.build(with_compare=True, with_hyp=True)
    return sorted(n for n, s in _sim_prove(m).items() if s == "differs")


def test_merged_bits_differ_without_the_pass(tmp_path):
    L = _design(tmp_path)
    assert {"ff:u_dut.s1[0]", "ff:u_dut.s2[2]"} <= set(L.gonly)
    assert "ff:u_dut.y[0]" in _differs(L)              # the q_b100 bout symptom


def test_sibling_twins_proposed(tmp_path):
    # first pass: s1[k] = s1[3] by signature; the same-index search also pairs s2[k] with y[k] (a circular trial
    # that induction drops), so s2 is found in the next auto_twins pass (end-to-end test below)
    L = _design(tmp_path)
    log = []
    hints = lec.scope_twin_proposals(L, log)
    want = [["gold", f"ff:u_dut.s1[{k}]", ["eq", "gold", "ff:u_dut.s1[3]", 0]] for k in range(3)]
    assert [h for h in hints if h[1].startswith("ff:u_dut.s1[")] == want
    assert not L.hyp                                    # trial bindings never stay
    assert "3 sibling-bit" in log[-1]


def test_sibling_search_follows_the_pipeline(tmp_path):
    L = _design(tmp_path)
    found = {}
    rv = lambda k: None
    n = lec.sibling_twin_search(L, [f"ff:u_dut.{r}[{k}]" for r in ("s1", "s2") for k in range(3)], found, rv)
    assert n == 6 and found == {f"ff:u_dut.{r}[{k}]": (f"ff:u_dut.{r}[3]", 0) for r in ("s1", "s2") for k in range(3)}
    assert not L.hyp


def test_not_a_sibling_twin_is_not_proposed(tmp_path):
    L = _design(tmp_path, gold_shared=False)
    found = {}
    lec.sibling_twin_search(L, [f"ff:u_dut.{r}[{k}]" for r in ("s1", "s2") for k in range(3)], found, lambda k: None)
    assert "ff:u_dut.s1[1]" not in found and "ff:u_dut.s2[1]" not in found
    assert found["ff:u_dut.s1[0]"] == ("ff:u_dut.s1[3]", 0)


@pytest.mark.parametrize("gold_shared,gate_ok,eq", [
    (True, True, True),        # the q_b100 form: closes
    (True, False, False),      # mutant gate: still differs
    (False, True, False),      # mutant gold (s1[1] not the shared expression): s1[1]/s2[1] stay free, differs
])
def test_auto_twins_end_to_end_and_mutants(tmp_path, monkeypatch, gold_shared, gate_ok, eq):
    monkeypatch.setattr(lec, "prove", _sim_prove)
    L = _design(tmp_path, gold_shared, gate_ok)
    rec = {}
    lec.auto_twins(L, rec, tmp_path, 100, [])
    assert (not _differs(L)) == eq
    if gold_shared and gate_ok:
        assert rec["auto_twins"]["kept"] == 6


# ------------------------------------------------------------------ X twins (q_b100 hint-free rerun, 11-09)
def _seq_x(tmp_path, name, inputs, xins, latches, nxt_fn):
    """_seq with extra AIG inputs that have no name in the map: the gold frontend's $anyseq X sources."""
    L, mp = _seq(tmp_path, name, list(inputs) + list(xins), latches, nxt_fn)
    mp["input"] = {i: v for i, v in mp["input"].items() if v[0][0] not in xins}
    return L, mp


def _design_x(tmp_path, gold_shared=True):
    """gold: s1[k] <= ke_n | (sel ? kb : X_k) -- kb_r[bi_r] with bi_r out of range is X, ONE fresh $anyseq per bit --
    s2[k] <= s1[k], y[k] <= s2[k].  gate (X chosen 0, bits merged into bit 3): s1[3] <= ke_n | (sel & kb).
    gold_shared=False: gold s1[1] <= ke_n & (sel ? kb : X_1) (not a twin)."""
    XS = [f"x{k}" for k in range(4)]

    def mux(m, s, a, b):
        return _or(m, m.AND(s, a), m.AND(s ^ 1, b))

    def gold(m, l):
        d = {S1[k]: _or(m, l["ke_n"], mux(m, l["sel"], l["kb"], l[XS[k]])) for k in range(4)}
        if not gold_shared:
            d[S1[1]] = m.AND(l["ke_n"], mux(m, l["sel"], l["kb"], l[XS[1]]))
        d.update({S2[k]: l[S1[k]] for k in range(4)})
        d.update({Y[k]: l[S2[k]] for k in range(4)})
        return d

    def gate(m, l):
        d = {S1[3]: _or(m, l["ke_n"], m.AND(l["sel"], l["kb"])), S2[3]: l[S1[3]]}
        d.update({Y[k]: l[S2[3]] for k in range(4)})
        return d

    g, gm = _seq_x(tmp_path, "gold", ["ke_n", "sel", "kb"], XS, S1 + S2 + Y, gold)
    t, tm = _seq(tmp_path, "gate", ["ke_n", "sel", "kb"], [S1[3], S2[3]] + Y, gate)
    return lec.Lec(g, gm, t, tm)


def test_x_twins_paired_outside_their_x_words(tmp_path):
    """Each copy of the shared expression reads its own X source, so the copies differ on every word where they are
    X; those words are don't-care (gold X), and outside them the bits are the same register."""
    L = _design_x(tmp_path)
    found = {}
    n = lec.sibling_twin_search(L, [f"ff:u_dut.{r}[{k}]" for r in ("s1", "s2") for k in range(3)], found,
                                lambda k: None)
    assert n == 6 and found == {f"ff:u_dut.{r}[{k}]": (f"ff:u_dut.{r}[3]", 0) for r in ("s1", "s2") for k in range(3)}
    assert not L.hyp


def test_x_twin_mutant_not_proposed(tmp_path):
    L = _design_x(tmp_path, gold_shared=False)
    found = {}
    lec.sibling_twin_search(L, [f"ff:u_dut.{r}[{k}]" for r in ("s1", "s2") for k in range(3)], found, lambda k: None)
    assert "ff:u_dut.s1[1]" not in found and found["ff:u_dut.s1[0]"] == ("ff:u_dut.s1[3]", 0)


@pytest.mark.parametrize("gold_shared,eq", [(True, True), (False, False)])
def test_x_twins_end_to_end(tmp_path, monkeypatch, gold_shared, eq):
    monkeypatch.setattr(lec, "prove", _sim_prove)
    L = _design_x(tmp_path, gold_shared)
    rec = {}
    lec.auto_twins(L, rec, tmp_path, 100, [])
    assert (not _differs(L)) == eq
