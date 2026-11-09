"""LEC-SCOPE-TWIN (HBM-HARD-6-KSH 11-08, kshare v8e478a NOT EQUIVALENT: lane[0].u_fill.rd_gray[2..3] differed with
the gold-only rd_bin[3] left free).  A gray-pointer FIFO loads rd_bin <= rd_next and rd_gray <= gray(rd_next) on
the same fire, both reset 0, so rd_bin[msb] == rd_gray[msb] and synthesis merges rd_bin[msb] into rd_gray[msb].
Both are self-holding, so their next-state signatures differ under random state; scope_twin_proposals tries every
still-free gold-only register against the matched registers of its own scope with the same bit index (trial binding
applied, D must simulate equal, reset values must agree) and auto_twins proves the survivors by induction
(apply_hints).  Mutants: a gold rd_bin[3] that is not a twin is never kept; a gate that computes rd_gray wrongly
still differs.
    python3 -m pytest -q tools/die_plan/test_lec_scope_twin.py"""
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lec  # noqa: E402
from test_lec_memory_layout import _seq, _sim_prove  # noqa: E402


def _xor(m, a, b):
    return m.AND(m.AND(a, b ^ 1) ^ 1, m.AND(a ^ 1, b) ^ 1) ^ 1


def _mux(m, s, a, b):                                  # s ? a : b
    return m.AND(m.AND(s, a) ^ 1, m.AND(s ^ 1, b) ^ 1) ^ 1


B = [f"rd_bin[{i}]" for i in range(4)]
G = [f"rd_gray[{i}]" for i in range(4)]


def _design(tmp_path, gold_twin=True, gate_ok=True):
    """gold: rd_bin[0..3], rd_gray[0..3] (rd_bin <= rd_bin + fire, rd_gray <= gray of that, both on fire).
    gate: rd_bin[3] merged into rd_gray[3] (it reads rd_gray[3] as the binary MSB).
    gold_twin=False: gold rd_bin[3] loads on !fire (not a twin).  gate_ok=False: gate rd_gray[2] uses the wrong
    MSB (rd_gray[1]) for the next pointer."""
    def regs(m, l, msb, fire_msb):
        bits = [l[B[0]], l[B[1]], l[B[2]], msb]
        c, nx = l["fire"], []
        for i in range(4):
            nx.append(_xor(m, bits[i], c))
            c = m.AND(c, bits[i])
        d = {B[i]: _mux(m, l["fire"], nx[i], l[B[i]]) for i in range(3)}
        d.update({G[i]: _mux(m, l["fire"], _xor(m, nx[i], nx[i + 1]), l[G[i]]) for i in range(3)})
        d[G[3]] = _mux(m, l["fire"], nx[3], l[G[3]])
        return d, nx

    def gold(m, l):
        d, nx = regs(m, l, l[B[3]], l["fire"])
        en = l["fire"] if gold_twin else l["fire"] ^ 1
        d[B[3]] = _mux(m, en, nx[3], l[B[3]])
        return d

    def gate(m, l):
        return regs(m, l, l[G[3]] if gate_ok else l[G[1]], l["fire"])[0]

    g, gm = _seq(tmp_path, "gold", ["fire"], B + G, gold)
    t, tm = _seq(tmp_path, "gate", ["fire"], B[:3] + G, gate)
    return lec.Lec(g, gm, t, tm)


def _differs(L):
    m, _ = L.build(with_compare=True, with_hyp=True)
    return sorted(n for n, s in _sim_prove(m).items() if s == "differs")


def test_free_msb_differs_without_the_pass(tmp_path):
    L = _design(tmp_path)
    assert "ff:u_dut.rd_bin[3]" in L.gonly
    assert "ff:u_dut.rd_gray[3]" in _differs(L)       # the kshare lane 0 symptom


def test_twin_proposed_in_scope(tmp_path):
    L = _design(tmp_path)
    log = []
    hints = lec.scope_twin_proposals(L, log)
    assert hints == [["gold", "ff:u_dut.rd_bin[3]", ["eq", "gold", "ff:u_dut.rd_gray[3]", 0]]]
    assert not L.hyp                                    # trial bindings never stay
    assert "scope twins" in log[-1]


def test_not_a_twin_is_not_proposed(tmp_path):
    L = _design(tmp_path, gold_twin=False)
    assert lec.scope_twin_proposals(L, []) == []


@pytest.mark.parametrize("gold_twin,gate_ok,eq", [
    (True, True, True),        # the kshare form: closes
    (True, False, False),      # mutant gate: still differs
    (False, True, False),      # mutant gold (rd_bin[3] not a twin): no proposal kept, differs
])
def test_auto_twins_end_to_end_and_mutants(tmp_path, monkeypatch, gold_twin, gate_ok, eq):
    monkeypatch.setattr(lec, "prove", _sim_prove)
    L = _design(tmp_path, gold_twin, gate_ok)
    rec = {}
    lec.auto_twins(L, rec, tmp_path, 100, [])
    assert rec["auto_twins"].get("kept", 0) == (1 if gold_twin else 0)
    assert (not _differs(L)) == eq
