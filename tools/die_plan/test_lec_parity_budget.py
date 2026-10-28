"""Wide parity normalization remains exact without quadratic prefix sets."""
import itertools
import lec


def test_bounded_parity_exact_and_mutant(monkeypatch):
    monkeypatch.setenv("OT_LEC_PARITY_TERMS", "4")
    m = lec.Aig()
    inputs = [m.add_input(str(i)) for i in range(9)]
    y = 0
    for x in inputs:
        y = m.XOR(y, x)
    for bits in itertools.product((0, 1), repeat=len(inputs)):
        vals = lec._sim_given(m, {i+1:b for i,b in enumerate(bits)}, 1)
        result = lec.lit_val(vals, 1, y)
        expected = sum(bits) % 2
        assert result == expected
        assert (result ^ 1) != expected
    assert max(len(terms) for terms,c in m.parity_expr.values()) <= 4


def test_wide_chain_keeps_support_bounded(monkeypatch):
    monkeypatch.setenv("OT_LEC_PARITY_TERMS", "32")
    m = lec.Aig()
    xs = [m.add_input(str(i)) for i in range(4096)]
    y = 0
    for x in xs:
        y = m.XOR(y, x)
    assert max(len(terms) for terms,c in m.parity_expr.values()) <= 32
    assert len(m.ands) < 4096 * 64
