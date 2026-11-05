"""Seq constants (COORD 11-05 15:41, DIE-HEAD-71): a gold-only RTL register with no reset whose every load is the same
constant c (D = en ? c : Q, or D = c) is folded to c by synthesis (HEAD hd_lep0N g_mtx.w_t[0] <= load_tag ? 1 : w_t[0];
hd_ctl beat_tx pad hold; seq_fan constant-data registers).  noreset_filter keeps its constant hypothesis with a
power-up base case (basis 'seq_constant', listed in lec.json).  Mutants: a data load (D = en ? a : Q), a register
the reset state gives the other value, a chain through a data register, and OT_LEC_SEQ_CONSTANT=0 (old rule).
    python3 -m pytest -q tools/die_plan/test_lec_seq_constant.py"""
import collections
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lec  # noqa: E402
from test_lec_memory_layout import _seq, _sim_prove  # noqa: E402

IN = ["rn", "ld", "a"]


def _mux(m, s, a, b):                     # s ? a : b
    return m.AND(m.AND(s, a) ^ 1, m.AND(s ^ 1, b) ^ 1) ^ 1


def _flow(tmp_path, monkeypatch, L):
    """lec.run's order: correspond -> auto_loaded -> noreset_filter -> compare miter."""
    monkeypatch.setattr(lec, "prove", _sim_prove)
    log, rec = [], {}
    lec.correspond(L, tmp_path, 100, log)
    lec.auto_loaded(L, rec, tmp_path, 100, log)
    lec.noreset_filter(L, log, collections.Counter(), tmp_path, 100)
    m, _ = L.build(with_compare=True, with_hyp=True)
    return _sim_prove(m), lec.noreset_report(L)


def _design(tmp_path, c=1, load="const", reset=None, chain=False):
    """gold: k has no reset, k <= ld ? c : k ('data' MUTANT: ld ? a : k); reset 0/1: k <= !rn ? reset : (...);
    chain: j <= ld ? c : j (no reset) and k <= ld ? j : k (k loads j, a seq constant itself: a chain).
    o <= a & (k == c) (no guard: o reads k from power-up).  gate: synthesis folded k (and j) to c: o <= a."""
    def gold(m, l):
        src = 1 if c else 0
        nx = {}
        if chain:
            nx["j"] = _mux(m, l["ld"], src, l["j"])
            src = l["j"]
        k = _mux(m, l["ld"], src if load == "const" else l["a"], l["k"])
        if reset is not None:
            k = _mux(m, l["rn"], k, 1 if reset else 0)
        nx["k"] = k
        nx["o"] = m.AND(l["a"], l["k"] if c else l["k"] ^ 1)
        return nx
    regs = (["j"] if chain else []) + ["k", "o"]
    g, gm = _seq(tmp_path, "gold", IN, regs, gold)
    t, tm = _seq(tmp_path, "gate", IN, ["o"], lambda m, l: {"o": l["a"]})
    return lec.Lec(g, gm, t, tm)


def test_constant_load_hold_is_seq_constant(tmp_path, monkeypatch):
    for c in (1, 0):
        L = _design(tmp_path, c)
        st, rep = _flow(tmp_path, monkeypatch, L)
        assert st["ff:u_dut.o"] == "proved", c
        assert rep["n_seq_constant"] == 1 and rep["seq_constant"][0]["register"] == "ff:u_dut.k"
        assert rep["seq_constant"][0]["value"] == c and rep["seq_constant_enabled"] is True


def test_chain_of_seq_constants(tmp_path, monkeypatch):
    L = _design(tmp_path, 1, chain=True)
    st, rep = _flow(tmp_path, monkeypatch, L)
    assert st["ff:u_dut.o"] == "proved"
    assert {e["register"] for e in rep["seq_constant"]} >= {"ff:u_dut.k"}


def test_mutant_data_load_still_differs(tmp_path, monkeypatch):
    L = _design(tmp_path, 1, load="data")
    st, rep = _flow(tmp_path, monkeypatch, L)
    assert st["ff:u_dut.o"] == "differs" and rep["n_seq_constant"] == 0


def test_mutant_reset_to_other_value_still_differs(tmp_path, monkeypatch):
    L = _design(tmp_path, 1, reset=0)         # resets to 0, loads 1: not constant
    st, rep = _flow(tmp_path, monkeypatch, L)
    assert st["ff:u_dut.o"] == "differs" and rep["n_seq_constant"] == 0


def test_switch_off_is_the_old_rule(tmp_path, monkeypatch):
    monkeypatch.setenv("OT_LEC_SEQ_CONSTANT", "0")
    L = _design(tmp_path, 1)
    st, rep = _flow(tmp_path, monkeypatch, L)
    assert st["ff:u_dut.o"] == "differs" and rep["n_seq_constant"] == 0 and rep["seq_constant_enabled"] is False
    assert ("gold", "ff:u_dut.k") in L.noreset_dropped


def test_seq_const_hold_truth_table():
    """unit: k (latch 3) <= ld ? c : k over inputs rn=1 ld=2 a=... ; data-load and wide-support refusals."""
    m = lec.Aig()
    ld, a, k = m.add_input("ld"), m.add_input("a"), m.add_input("k")
    hold1 = _mux(m, ld, 1, k)
    hold_d = _mux(m, ld, a, k)
    d = dict(I=2, L=1, A=len(m.ands) // 2, ands=m.ands, latches=[hold1])
    assert lec.seq_const_hold(d, k, hold1, 1)
    assert not lec.seq_const_hold(d, k, hold1, 0)
    assert not lec.seq_const_hold(d, k, hold_d, 1)
    assert not lec.seq_const_hold(d, k, hold1, 1, max_support=0)    # refused, never assumed


def test_never_loaded_register_is_not_a_seq_constant():
    """k <= k (no load at all: an uninitialised read) and k <= 1 (no Q in D: the raw-D base case owns it) refused."""
    m = lec.Aig()
    ld, a, k = m.add_input("ld"), m.add_input("a"), m.add_input("k")
    d = dict(I=2, L=1, A=len(m.ands) // 2, ands=m.ands, latches=[k])
    assert not lec.seq_const_hold(d, k, k, 1) and not lec.seq_const_hold(d, k, k, 0)
    assert not lec.seq_const_hold(d, k, 1, 1)
