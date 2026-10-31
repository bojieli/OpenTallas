"""Paired root class closure (S81-CORES-KITS-12 10-31, S81 xfin ot_s81dv_eng_finish): gold-only registers of one
function (the five leaf valids of one K=5 slot group load on the same hit) each get their own gate partner, but the
pairing may bind a gate flop to ANOTHER member of the class.  Every pair is true; without a gold-gold tie the compare
sees the gold reader's member and the gate reader's member as two free inputs -> false 'differs'.  The closure
proposes gold == first of class for paired gold-only registers of equal sequential trace; the induction decides.
    python3 -m pytest -q tools/die_plan/test_lec_root_class.py"""
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lec  # noqa: E402
from test_lec_memory_layout import _seq, _sim_prove  # noqa: E402


def _mux(m, s, a, b):                     # s ? a : b
    return m.AND(m.AND(s, a) ^ 1, m.AND(s ^ 1, b) ^ 1) ^ 1


def _design(tmp_path, a1_mode="copy"):
    """gold: a0, a1 (gold-only names) both a0 <= rn ? x : a0 (a1 per a1_mode); o <= a0.
    gate: t0, t1 (gate-only names) with the same functions; o <= t1.  Gate t1 is a copy of gold a0 AND a1, and the
    name pairing binds t1 -> a1, so the gate reader and the gold reader land on different members of the class."""
    a1f = {"copy": lambda m, l, me: _mux(m, l["rn"], l["x"], l[me]),
           "en": lambda m, l, me: _mux(m, m.AND(l["rn"], l["s"]), l["x"], l[me])}[a1_mode]
    g, gm = _seq(tmp_path, "gold", ["rn", "x", "s"], ["a0", "a1", "o"],
                 lambda m, l: {"a0": _mux(m, l["rn"], l["x"], l["a0"]), "a1": a1f(m, l, "a1"), "o": l["a0"]})
    t, tm = _seq(tmp_path, "gate", ["rn", "x", "s"], ["a0_t", "a1_t", "o"],
                 lambda m, l: {"a0_t": _mux(m, l["rn"], l["x"], l["a0_t"]), "a1_t": a1f(m, l, "a1_t"),
                               "o": l["a1_t"]})
    return lec.Lec(g, gm, t, tm)


def _verdict(tmp_path, monkeypatch, L):
    monkeypatch.setattr(lec, "prove", _sim_prove)
    log = []
    lec.correspond(L, tmp_path, 100, log)
    m, _ = L.build(with_compare=True, with_hyp=True)
    return _sim_prove(m)["ff:u_dut.o"], log


def test_rotated_class_members_prove(tmp_path, monkeypatch):
    L = _design(tmp_path)
    st, log = _verdict(tmp_path, monkeypatch, L)
    assert st == "proved"
    assert L.hyp.get(("gold", "ff:u_dut.a1")) == ("eq", "gold", "ff:u_dut.a0", 0)
    assert any("paired root class closure: 1 " in x for x in log)


def test_without_closure_the_class_stays_free(tmp_path, monkeypatch):
    monkeypatch.setenv("OT_LEC_ROOT_CLASS", "0")
    st, _ = _verdict(tmp_path, monkeypatch, _design(tmp_path))
    assert st == "differs"                 # the 10-31 xfin g_grp[10..11] / [40] failure mode


def test_mutant_other_load_condition_is_not_merged(tmp_path, monkeypatch):
    L = _design(tmp_path, a1_mode="en")
    st, _ = _verdict(tmp_path, monkeypatch, L)
    assert st == "differs" and ("gold", "ff:u_dut.a1") not in L.hyp


def test_mutant_with_forged_equal_traces_is_refuted(tmp_path, monkeypatch):
    real = lec.seq_traces

    def forged(L, log, **kw):
        T = real(L, log, **kw)
        T[("gold", "ff:u_dut.a1")] = T[("gold", "ff:u_dut.a0")]
        return T
    monkeypatch.setattr(lec, "seq_traces", forged)
    L = _design(tmp_path, a1_mode="en")
    st, _ = _verdict(tmp_path, monkeypatch, L)
    assert st == "differs" and ("gold", "ff:u_dut.a1") not in L.hyp
