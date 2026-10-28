"""LEC-FPREG-3 10-27 (KV core nearhbm_prod s1_e[9], 112 differ): a universally constant next state whose cone has
no X source but reads unreset registers (one with an equality hypothesis) gets the universal raw-D base too."""
import collections
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lec
from test_lec_memory_layout import _seq
from test_lec_raw_bases import _exact


def _case(tmp_path, nonconstant=False):
    def gold(m, l):
        x, a = l["c"], l["r"]          # unreset operand registers (no X source); c carries an equality hypothesis
        u = m.AND(x ^ 1, a ^ 1) ^ 1
        v = m.AND(x ^ 1, a) ^ 1
        z = m.AND(m.AND(u, v), x ^ 1)   # universally 0; ternary X with p, r unknown
        return {"p": l["i0"], "r": l["i1"], "c": l["i0"], "q": m.AND(x, a) if nonconstant else z, "o": l["q"]}
    g, gm = _seq(tmp_path, "gold", ["i0", "i1"], ["p", "r", "c", "q", "o"], gold)
    t, tm = _seq(tmp_path, "gate", ["i0", "i1"], ["p", "r", "o"],
                 lambda m, l: {"p": l["i0"], "r": l["i1"], "o": 0})
    L = lec.Lec(g, gm, t, tm)
    L.hyp[("gold", "ff:u_dut.c")] = ("eq", "gold", "ff:u_dut.p", 0)    # the operand is a merged copy of p
    L.hyp[("gold", "ff:u_dut.q")] = ("const", 0)
    return L


def test_reset_x_constant_with_register_cone_gets_universal_base(tmp_path, monkeypatch):
    L = _case(tmp_path)
    monkeypatch.setattr(lec, "prove", _exact)
    k = "ff:u_dut.q"
    assert lec.latch_cone(L, "gold", k) is not None
    lec.noreset_filter(L, [], collections.Counter(), tmp_path, 100)
    assert L.raw_constant_status[("gold", k, 0)] == "proved"
    assert ("gold", k) in L.hyp
    assert lec.noreset_report(L)["n_universal_raw_D"] == 1
    m, _ = L.build(with_compare=True, with_hyp=True)
    assert set(_exact(m).values()) == {"proved"}


def test_mutant_nonconstant_register_cone_is_dropped(tmp_path, monkeypatch):
    L = _case(tmp_path, nonconstant=True)
    monkeypatch.setattr(lec, "prove", _exact)
    lec.noreset_filter(L, [], collections.Counter(), tmp_path, 100)
    assert L.raw_constant_status[("gold", "ff:u_dut.q", 0)] == "differs"
    assert ("gold", "ff:u_dut.q") not in L.hyp
    m, _ = L.build(with_compare=True, with_hyp=True)
    assert _exact(m)["ff:u_dut.o"] == "differs"
