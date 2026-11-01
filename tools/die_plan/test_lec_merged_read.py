"""Gold-only register merged by synthesis into a register that READS it (HBM async FIFO, KIT-TRIAGE-1 11-01:
rd_gray[MSB] <= rd_bin_next[MSB] reads rd_bin[MSB], rd_bin[MSB] reads itself, so opt_merge keeps one flop; the
gold-only rd_bin[MSB] was left free and the FIFO's gray/empty points differed).  merged_proposals now compares the
two next-state supports with the pair read as one register (both directions); the proposal is still proved by
induction, so a register that is NOT a merge stays free and the mutants still differ.
    python3 -m pytest -q tools/die_plan/test_lec_merged_read.py"""
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lec  # noqa: E402
from test_lec_memory_layout import _seq, _sim_prove  # noqa: E402


def _xor(m, a, b):
    return m.AND(m.AND(a, b ^ 1) ^ 1, m.AND(a ^ 1, b) ^ 1) ^ 1


def _design(tmp_path, kept="gray", mutant=False):
    """gold: 2-bit binary counter b0/b1 advanced by i, gray MSB g1 <= next b1; o <= (the merged-away one) ^ b0.
    kept='gray': the gate keeps g1 (b1 merged into it, g1 <= g1 ^ (b0 & i)); kept='bin': the gate keeps b1.
    mutant: the gate's kept MSB toggles on b0 alone (ignores i): NOT a merge, must differ."""
    def nb1(m, l, q):
        return _xor(m, q, l["b0"] if mutant else m.AND(l["b0"], l["i"]))
    gold = lambda m, l: {"b0": _xor(m, l["b0"], l["i"]), "b1": _xor(m, l["b1"], m.AND(l["b0"], l["i"])),
                         "g1": _xor(m, l["b1"], m.AND(l["b0"], l["i"])),
                         "o": _xor(m, l["b1" if kept == "gray" else "g1"], l["b0"])}
    g, gm = _seq(tmp_path, "gold", ["i"], ["b0", "b1", "g1", "o"], gold)
    q = "g1" if kept == "gray" else "b1"
    gate = lambda m, l: {"b0": _xor(m, l["b0"], l["i"]), q: nb1(m, l, l[q]), "o": _xor(m, l[q], l["b0"])}
    t, tm = _seq(tmp_path, "gate", ["i"], ["b0", q, "o"], gate)
    return lec.Lec(g, gm, t, tm)


@pytest.mark.parametrize("kept,gonly,partner", [
    ("gray", "ff:u_dut.b1", "ff:u_dut.g1"),     # the matched register reads the gold-only one
    ("bin", "ff:u_dut.g1", "ff:u_dut.b1"),      # the gold-only register reads the matched one
])
def test_merge_across_read_is_proposed(tmp_path, kept, gonly, partner):
    L = _design(tmp_path, kept)
    log = []
    lec.merged_proposals(L, log)
    assert L.hyp[("gold", gonly)] == ("eq", "gold", partner, 0)
    assert "merged across a read" in log[-1]


@pytest.mark.parametrize("kept,mutant,differs", [
    ("gray", False, False),    # EQ (b1 left free before this fix)
    ("bin", False, False),
    ("gray", True, True),      # mutant: the kept MSB is not the merged register
    ("bin", True, True),
])
def test_end_to_end_and_mutants(tmp_path, monkeypatch, kept, mutant, differs):
    monkeypatch.setattr(lec, "prove", _sim_prove)
    L = _design(tmp_path, kept, mutant)
    lec.correspond(L, tmp_path, 100, [])
    m, _ = L.build(with_compare=True, with_hyp=True)
    st = _sim_prove(m)
    # b1 == g1 holds in the gold design, so the mutant's divergence shows on the kept register's own point
    assert ("differs" in st.values()) == differs
    if not differs:
        assert set(st.values()) == {"proved"} and "ff:u_dut.o" in st


def test_default_has_no_cap():
    import inspect
    assert inspect.signature(lec.merged_proposals).parameters["cap"].default is None
