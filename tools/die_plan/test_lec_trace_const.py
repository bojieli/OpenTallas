"""Trace constant closure (LEC-TOOL-2 10-27): constant-from-reset self-holding registers (HBM hcp_sys1 R5: nout_r[1]
async-resets to 0 and reloads the tied cmd_nout[1] = 0; gate folded the downstream sd_nv[7:0] to 0, gold reads
last_r ? nlast_r : 256 with nlast_r[7:0] == nout_r[1]) are proposed constant from their sequential trace and proved
inductively with every other hypothesis; a register that is not constant is refuted.
    python3 -m pytest -q tools/die_plan/test_lec_trace_const.py"""
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lec  # noqa: E402
from test_lec_memory_layout import _seq, _sim_prove  # noqa: E402


def _mux(m, s, a, b):                     # s ? a : b
    return m.AND(m.AND(s, a) ^ 1, m.AND(s ^ 1, b) ^ 1) ^ 1


def _design(tmp_path, load="zero", gate_o="zero"):
    """both sides: k <= rn ? (ld ? LOAD : k) : 0 (async-reset register as async2sync models it, holding itself);
    LOAD = 0 (tied command field) or x (mutant: a real data register).  gold o <= k & x | y-free; gate o <= 0
    ('zero', synthesis folded k) or o <= k & x ('same')."""
    ld_val = {"zero": lambda m, l: 0, "x": lambda m, l: l["x"]}[load]
    k = lambda m, l: m.AND(l["rn"], _mux(m, l["ld"], ld_val(m, l), l["k"]))
    g, gm = _seq(tmp_path, "gold", ["rn", "ld", "x"], ["k", "o"], lambda m, l: {"k": k(m, l), "o": m.AND(l["k"], l["x"])})
    t, tm = _seq(tmp_path, "gate", ["rn", "ld", "x"], ["k", "o"],
                 lambda m, l: {"k": k(m, l), "o": 0 if gate_o == "zero" else m.AND(l["k"], l["x"])})
    return lec.Lec(g, gm, t, tm)


def _verdict(tmp_path, monkeypatch, L):
    monkeypatch.setattr(lec, "prove", _sim_prove)
    log = []
    lec.correspond(L, tmp_path, 100, log)
    m, _ = L.build(with_compare=True, with_hyp=True)
    return _sim_prove(m)["ff:u_dut.o"], log


def _no_selfhold_const(monkeypatch):
    # the older self-hold cofactor rule also finds this tiny case; switch it off to test the trace rule alone
    real = lec.Lec.build

    def build(self, *a, **kw):
        if kw.get("hold_matched"):
            kw["hold_matched"] = ()
        return real(self, *a, **kw)
    monkeypatch.setattr(lec.Lec, "build", build)


def test_constant_from_reset_is_proved(tmp_path, monkeypatch):
    L = _design(tmp_path)
    st, log = _verdict(tmp_path, monkeypatch, L)
    assert st == "proved" and L.hyp[("both", "ff:u_dut.k")] == ("const", 0)


def test_trace_rule_alone_proves_it(tmp_path, monkeypatch):
    _no_selfhold_const(monkeypatch)
    L = _design(tmp_path)
    st, log = _verdict(tmp_path, monkeypatch, L)
    assert st == "proved" and any("trace constant closure" in x for x in log)


def test_without_any_constant_rule_it_differs(tmp_path, monkeypatch):
    _no_selfhold_const(monkeypatch)
    monkeypatch.setenv("OT_LEC_TRACE_CONST", "0")
    st, _ = _verdict(tmp_path, monkeypatch, _design(tmp_path))
    assert st == "differs"


def test_mutant_data_register_is_not_constant(tmp_path, monkeypatch):
    _no_selfhold_const(monkeypatch)
    L = _design(tmp_path, load="x")
    st, _ = _verdict(tmp_path, monkeypatch, L)
    assert st == "differs" and ("both", "ff:u_dut.k") not in L.hyp


def test_mutant_forged_constant_trace_is_refuted(tmp_path, monkeypatch):
    # the trace is only a candidate filter: forge a constant trace for the data register; induction must refute it
    _no_selfhold_const(monkeypatch)
    real = lec.seq_traces

    def forged(L, log, **kw):
        T = real(L, log, **kw)
        for sd in ("gold", "gate"):
            T[(sd, "ff:u_dut.k")] = None
            L.trace_const[(sd, "ff:u_dut.k")] = 0
        return T
    monkeypatch.setattr(lec, "seq_traces", forged)
    L = _design(tmp_path, load="x")
    st, _ = _verdict(tmp_path, monkeypatch, L)
    assert st == "differs" and ("both", "ff:u_dut.k") not in L.hyp


def test_same_function_needs_no_constant(tmp_path, monkeypatch):
    st, _ = _verdict(tmp_path, monkeypatch, _design(tmp_path, load="x", gate_o="same"))
    assert st == "proved"
