"""LEC-FPREG-4 (L3 u_rw.st 10-27): yosys fsm one-hot recoding may encode one state (the reset / idle state) as NO bit
set ("zero-hot"): 3 gold state bits -> 5 gate st#t bits for 6 states.  fsm_proposals then finds no unique one-hot map
(every transition into the zero state looked non-one-hot).  When the one-hot search has no unique map, a zero-hot
search adds one code as the all-zero gate state; the cubes are proved by the same induction, a wrong map fails.
A plain one-hot FSM keeps its earlier map (the zero-hot search never runs)."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lec  # noqa: E402
from test_lec import _sim_prove  # noqa: E402


def design(gate, mutant=False):
    """gold: 2-bit counter 0 -> 1 -> 2 -> 3 -> 0 (reset -> 0); gate: t1/t2/t3 one-hot for 1/2/3, state 0 = no bit.
    mutant: the gate skips state 2 (t1 -> t3), so no map can hold."""
    m = lec.Aig()
    reset = m.add_input('reset')
    q = [m.add_input(str(i)) for i in range(3 if gate else 2)]
    nr = reset ^ 1
    if gate:
        zero = m.AND(m.AND(q[0] ^ 1, q[1] ^ 1), q[2] ^ 1)
        nxt = [m.AND(nr, zero), m.AND(nr, 0 if mutant else q[0]), m.AND(nr, q[0] if mutant else q[1])]
        keys = [f'u_dut.st#t[{i}]' for i in range(3)]
    else:
        nxt = [m.AND(nr, q[0] ^ 1), m.AND(nr, m.XOR(q[0], q[1]))]
        keys = [f'u_dut.st[{i}]' for i in range(2)]
    d = dict(I=1, L=len(q), O=0, A=len(m.ands) // 2, latches=nxt, outputs=[], ands=m.ands)
    mp = {'input': {0: [('reset', 0)]}, 'output': {},
          'latch': {i: [(k + '$_DFF_P_.lecq', 0)] for i, k in enumerate(keys)}}
    return d, mp


def test_zero_hot_fsm_is_proposed_and_proved():
    g, gm = design(False)
    t, tm = design(True)
    L = lec.Lec(g, gm, t, tm)
    log = []
    assert lec.fsm_proposals(L, log) == 3, log
    assert any("zero-hot" in x for x in log), log
    assert [c for c in L.cons if c[0] == "gold"][0][2] and len([c for c in L.cons if c[0] == "gold"][0][2]) == 4
    m, _ = L.build(with_compare=True, with_hyp=True)
    assert set(_sim_prove(m).values()) == {'proved'}
    # wrong map: flip one cube's code -> the induction fails
    key = next(k for k, h in L.hyp.items() if h[0] == 'cube')
    h = L.hyp[key]
    L.hyp[key] = (h[0], h[1], h[2], [v ^ 1 for v in h[3]])
    m, _ = L.build(with_compare=True, with_hyp=True)
    assert 'differs' in _sim_prove(m).values()


def test_zero_hot_mutant_fsm_is_not_proved():
    g, gm = design(False)
    t, tm = design(True, mutant=True)
    L = lec.Lec(g, gm, t, tm)
    log = []
    lec.fsm_proposals(L, log)
    if any(h[0] == 'cube' for h in L.hyp.values()):
        m, _ = L.build(with_compare=True, with_hyp=True)
        assert 'differs' in _sim_prove(m).values()
