"""Six binary states versus five one-hot bits with an all-zero idle code."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lec
from test_lec_memory_layout import _seq
def _exact(m):
    assert m.ni <= 12
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


def _mux(m, s, a, b):
    return m.AND(m.AND(s, a) ^ 1, m.AND(s ^ 1, b) ^ 1) ^ 1


def _design(tmp_path, mutant=False):
    gs = [f"st[{i}]" for i in range(3)]
    ts = [f"st[{i}]" for i in range(1, 6)]

    def gold(m, l):
        def code(c):
            v = 1
            for i, k in enumerate(gs):
                v = m.AND(v, l[k] ^ (1 ^ ((c >> i) & 1)))
            return v
        result = {"o": code(3)}
        for i, k in enumerate(gs):
            v = 0
            for c in range(6):
                if ((c + 1) % 6) >> i & 1:
                    v = m.AND(v ^ 1, code(c) ^ 1) ^ 1
            result[k] = m.AND(l["rn"], _mux(m, l["en"], v, l[k]))
        return result

    def gate(m, l):
        idle = 1
        for k in ts:
            idle = m.AND(idle, l[k] ^ 1)
        result = {"o": l["st[3]"]}
        for i, k in enumerate(ts, 1):
            prev = idle if i == 1 else l[f"st[{i-1}]"]
            if mutant and i == 3:
                prev = l["st[1]"]              # wrong transition, not an encoding permutation
            result[k] = m.AND(l["rn"], _mux(m, l["en"], prev, l[k]))
        return result

    g, gm = _seq(tmp_path, "gold", ["rn", "en"], gs + ["o"], gold)
    t, tm = _seq(tmp_path, "gate", ["rn", "en"], ts + ["o"], gate)
    return lec.Lec(g, gm, t, tm)


def test_zero_hot_idle_is_proposed_and_inductively_proved(tmp_path):
    L = _design(tmp_path)
    log = []
    assert lec.fsm_proposals(L, log) == 5
    assert any("all-zero" in s for s in log)
    assert len(L.cons) == 1 and len(L.cons[0][2]) == 6
    m, _ = L.build(with_compare=True, with_hyp=True)
    assert set(_exact(m).values()) == {"proved"}


def test_wrong_cube_mapping_fails_induction(tmp_path):
    L = _design(tmp_path)
    assert lec.fsm_proposals(L, []) == 5
    sk = min(L.hyp)
    h = L.hyp[sk]
    bits = list(h[3]); bits[0] ^= 1
    L.hyp[sk] = (*h[:3], bits)
    m, _ = L.build(with_compare=True, with_hyp=True)
    assert "differs" in _exact(m).values()


def test_wrong_transition_mutant_is_not_accepted(tmp_path):
    L = _design(tmp_path, mutant=True)
    lec.fsm_proposals(L, [])
    m, _ = L.build(with_compare=True, with_hyp=True)
    assert "differs" in _exact(m).values()
