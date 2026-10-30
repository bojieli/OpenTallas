"""An optional earlier full proof may end discovery; partial proofs/mutants never do."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lec


def design(mutant=False, bad_hyp=False):
    # q loads d (wrong-data mutant flips only q); r and copy independently load e.
    # The redundant-copy invariant remains valid in the output mutant.
    def side(gate):
        a = lec.Aig()
        d, e, q, r, copy = [a.add_input(n) for n in ('d', 'e', 'q', 'r', 'copy')]
        nxt = [d ^ int(gate and mutant), e, e]
        obj = dict(I=2, L=3, O=0, A=0, latches=nxt, outputs=[], ands=a.ands)
        mp = dict(input={0: [('d', 0)], 1: [('e', 0)]}, output={}, latch={
            0: [('u.q$_DFF_P_.lecq', 0)], 1: [('u.r$_DFF_P_.lecq', 0)],
            2: [('u.copy$_DFF_P_.lecq', 0)]})
        return obj, mp
    g, gm = side(False)
    t, tm = side(True)
    L = lec.Lec(g, gm, t, tm)
    L.hyp['both', 'ff:u.copy'] = ('eq', 'gold', 'ff:u.r', int(bad_hyp))
    return L


def exhaustive(m, *_args, **_kwargs):
    # Exact truth table for these tiny circuits; not a sampled simulation oracle.
    values = [0] * (m.ni + len(m.ands) // 2 + 1)
    mask = (1 << (1 << m.ni)) - 1
    for v in range(1, m.ni + 1):
        values[v] = sum(((bits >> (v - 1)) & 1) << bits for bits in range(1 << m.ni))
    for j in range(len(m.ands) // 2):
        a, b = m.ands[2*j:2*j+2]
        av = values[a >> 1] ^ (mask if a & 1 else 0)
        bv = values[b >> 1] ^ (mask if b & 1 else 0)
        values[m.ni+j+1] = av & bv
    return {name: ('proved' if (values[o >> 1] ^ (mask if o & 1 else 0)) == 0 else 'differs')
            for name, o in zip(m.onames, m.outs)}


def test_default_does_not_build_or_prove(monkeypatch, tmp_path):
    monkeypatch.delenv('OT_LEC_EARLY_COMPARE', raising=False)
    L = design()
    monkeypatch.setattr(L, 'build', lambda **kw: pytest.fail('default must not build an extra miter'))
    assert not lec.early_whole_compare(L, tmp_path, 100, [], 0)
    assert not hasattr(L, 'early_compare')


@pytest.mark.parametrize('mutant,bad_hyp,expected', [(False, False, True), (True, False, False), (False, True, False)])
def test_all_comparisons_and_invariants_are_required(monkeypatch, tmp_path, mutant, bad_hyp, expected):
    monkeypatch.setenv('OT_LEC_EARLY_COMPARE', '1')
    monkeypatch.setattr(lec, 'prove', exhaustive)
    L = design(mutant, bad_hyp)
    assert lec.early_whole_compare(L, tmp_path, 100, [], 3) is expected
    assert L.early_compare['complete']
    assert L.early_compare['passed'] is expected


@pytest.mark.parametrize('missing,unknown', [(True, False), (False, True)])
def test_missing_or_undecided_receipt_is_not_an_early_pass(monkeypatch, tmp_path, missing, unknown):
    monkeypatch.setenv('OT_LEC_EARLY_COMPARE', '1')
    def incomplete(m, *args, **kwargs):
        st = exhaustive(m)
        if missing:
            st.pop(next(iter(st)))
        if unknown:
            st[next(iter(st))] = 'undecided'
        return st
    monkeypatch.setattr(lec, 'prove', incomplete)
    L = design()
    assert not lec.early_whole_compare(L, tmp_path, 100, [], 0)


def test_correspond_ends_before_redundant_future_discovery(monkeypatch, tmp_path):
    monkeypatch.setenv('OT_LEC_EARLY_COMPARE', '1')
    calls = []
    def proof(m, *args, **kwargs):
        calls.append(kwargs.get('tag'))
        return exhaustive(m)
    monkeypatch.setattr(lec, 'prove', proof)
    # This future closure could propose redundant alternatives forever. A full
    # miter already proves equivalence, so it must never be reached.
    monkeypatch.setattr(lec, 'structural_constant_closure',
                        lambda *args: pytest.fail('redundant later discovery reached'))
    L = design()
    log = []
    lec.correspond(L, tmp_path, 100, log, rounds=1, sim_iters=1, words=1)
    assert calls[-1] == 'early_compare0'
    assert L.early_compare['passed']
    assert set(exhaustive(L.build(with_compare=True, with_hyp=True)[0]).values()) == {'proved'}
