"""Rare counter carries must refute false constants without a SAT round per bit."""
import collections
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lec
from test_lec_memory_layout import _seq, _sim_prove


def _design(tmp_path, active=32, mutant=False, fsm=False):
    qs = [f'q[{i}]' for i in range(32)]
    state = ['s0', 's1'] if fsm else []

    def nxt(step2):
        def make(m, l):
            out = {}
            carry = l['en']
            for i, k in enumerate(qs):
                bit = l[k] if step2 and i == 0 else m.XOR(l[k], carry)
                out[k] = m.AND(l['rn'], bit) if i < active else 0
                if not (step2 and i == 0):
                    carry = m.AND(carry, l[k])
            if fsm:
                out['s0'] = m.AND(l['rn'], l['s0'] ^ 1) ^ 1
                out['s1'] = m.AND(l['rn'], l['s1'])
            return out
        return make

    g, gm = _seq(tmp_path, 'gold', ['rn', 'en'], qs + state, nxt(False))
    t, tm = _seq(tmp_path, 'gate', ['rn', 'en'], qs + state, nxt(mutant))
    L = lec.Lec(g, gm, t, tm)
    L.hyp = {('both', f'ff:u_dut.q[{i}]'): ('const', 0) for i in range(8, 32)}
    if fsm:
        L.cons = [('gold', ('ff:u_dut.s0', 'ff:u_dut.s1'), ((1, 0), (0, 1)))]
    return L


def test_wide_counter_false_constants_refine_to_empty(tmp_path):
    L = _design(tmp_path)
    log = []
    assert lec.sim_refine(L, log, collections.Counter()) == 24
    assert L.hyp == {}
    m, _ = L.build(with_compare=True, with_hyp=True)
    assert set(_sim_prove(m).values()) == {'proved'}


def test_true_constant_high_bits_are_kept_with_legal_fsm_seed(tmp_path):
    L = _design(tmp_path, active=16, fsm=True)
    assert lec.sim_refine(L, [], collections.Counter()) == 8
    assert L.hyp == {('both', f'ff:u_dut.q[{i}]'): ('const', 0) for i in range(16, 32)}


def test_mutant_increment_by_two_still_fails(tmp_path):
    L = _design(tmp_path, mutant=True)
    lec.sim_refine(L, [], collections.Counter())
    m, _ = L.build(with_compare=True, with_hyp=True)
    assert _sim_prove(m)['ff:u_dut.q[0]'] == 'differs'
