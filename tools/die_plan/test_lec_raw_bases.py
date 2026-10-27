"""Universal raw-D bases: RTL X and state remain independent Boolean inputs."""
import collections
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lec
from test_lec_memory_layout import _seq


def _exact(m, *args, **kwargs):
    """Exhaust all inputs on these tiny cones; never implement RTL X masking."""
    assert m.ni <= 8
    result = {n: "proved" for n in m.onames}
    for bits in range(1 << m.ni):
        values = [0] + [(bits >> i) & 1 for i in range(m.ni)]
        for i in range(len(m.ands) // 2):
            a, b = m.ands[2*i:2*i+2]
            values.append((values[a >> 1] ^ (a & 1)) & (values[b >> 1] ^ (b & 1)))
        for n, lit in zip(m.onames, m.outs):
            if values[lit >> 1] ^ (lit & 1):
                result[n] = "differs"
    return result


def _case(tmp_path, nonconstant=False, feedback=False):
    def gold(m, l):
        x, a = l["x"], l["a"]
        # (x|a)&(x|!a)&!x is universally zero, but ternary propagation cannot
        # establish it with x unknown. Correlated Boolean logic is required.
        u = m.AND(x ^ 1, a ^ 1) ^ 1
        v = m.AND(x ^ 1, a) ^ 1
        z = m.AND(m.AND(u, v), x ^ 1)
        return {"q": l["q"] if feedback else x if nonconstant else z, "o": l["q"]}
    g, gm = _seq(tmp_path, "gold", ["x", "a"], ["q", "o"], gold)
    t, tm = _seq(tmp_path, "gate", ["x", "a"], ["o"], lambda m, l: {"o": 0})
    del gm["input"][0]                       # actual anonymous RTL X input
    del tm["input"][0]
    L = lec.Lec(g, gm, t, tm)
    L.hyp[("gold", "ff:u_dut.q")] = ("const", 0)
    return L


def test_boolean_constant_with_every_x_and_state_free(tmp_path, monkeypatch):
    L = _case(tmp_path)
    monkeypatch.setattr(lec, "prove", _exact)
    k = "ff:u_dut.q"
    assert lec.latch_cone(L, "gold", k) is None
    lec.noreset_filter(L, [], collections.Counter(), tmp_path, 100)
    assert L.raw_constant_status[("gold", k, 0)] == "proved"
    assert lec.noreset_sound(L)[("gold", k)] == 1
    assert lec.noreset_report(L)["n_universal_raw_D"] == 1
    m, _ = L.build(with_compare=True, with_hyp=True)
    assert set(_exact(m).values()) == {"proved"}


def test_nonconstant_x_is_never_a_base(tmp_path, monkeypatch):
    L = _case(tmp_path, nonconstant=True)
    monkeypatch.setattr(lec, "prove", _exact)
    lec.noreset_filter(L, [], collections.Counter(), tmp_path, 100)
    assert L.raw_constant_status[("gold", "ff:u_dut.q", 0)] == "differs"
    assert ("gold", "ff:u_dut.q") not in L.hyp


def test_wrong_constant_control_is_refuted(tmp_path, monkeypatch):
    L = _case(tmp_path)
    L.hyp[("gold", "ff:u_dut.q")] = ("const", 1)
    monkeypatch.setattr(lec, "prove", _exact)
    lec.noreset_filter(L, [], collections.Counter(), tmp_path, 100)
    assert L.raw_constant_status[("gold", "ff:u_dut.q", 1)] == "differs"
    assert ("gold", "ff:u_dut.q") not in L.hyp


def test_undecided_never_establishes_a_base(tmp_path, monkeypatch):
    L = _case(tmp_path)
    monkeypatch.setattr(lec, "prove", lambda m, *a, **k: {n: "undecided" for n in m.onames})
    lec.noreset_filter(L, [], collections.Counter(), tmp_path, 100)
    assert ("gold", "ff:u_dut.q") not in L.hyp


def test_base_does_not_use_a_current_q_constant_hypothesis(tmp_path, monkeypatch):
    L = _case(tmp_path, feedback=True)
    monkeypatch.setattr(lec, "prove", _exact)
    # Q holds itself. Even a supplied Q==0 hypothesis cannot establish its base.
    lec.raw_constant_bases(L, tmp_path, 100, [])
    assert L.raw_constant_status.get(("gold", "ff:u_dut.q", 0), "differs") != "proved"


def test_cached_status_is_reused_without_another_solver(tmp_path, monkeypatch):
    L = _case(tmp_path)
    monkeypatch.setattr(lec, "prove", _exact)
    lec.raw_constant_bases(L, tmp_path, 100, [])
    monkeypatch.setattr(lec, "prove", lambda *a, **k: (_ for _ in ()).throw(AssertionError("reproved")))
    lec.raw_constant_bases(L, tmp_path, 100, [])
