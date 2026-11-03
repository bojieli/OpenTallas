"""DIE-HBM-58/LEC (HBM kshare splitstrap v700685 / v8e478a LEC NOT EQUIVALENT 10-31): the per-lane VM state machine
st (NORM/PEND/ISSUE/WAIT/WPEND/WB, 3 gold bits) is recoded one-hot by yosys fsm (6 gate st#t bits).  Its transitions
fire on rare conditions (j == 15, got == 63), so 128 random lanes per state saw none: every permutation of the
self-looping states explained all 768 sampled transitions ('no unique encoding (best 768, next 768)') and lanes 1..3
got no hypothesis -> rd_gray readers differ.  fsm_proposals now re-samples with more lanes when the map is not
unique; the induction still decides, a wrong map only fails."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lec  # noqa: E402
from test_lec import _sim_prove  # noqa: E402
from test_lec_memory_layout import _seq  # noqa: E402

A_BITS = 8


def _rare(m, l):
    a = l['a0']
    for i in range(1, A_BITS):
        a = m.AND(a, l[f'a{i}'])
    return a                                  # all eight inputs 1: p = 1/256 per lane


def _gold(m, l):
    A, nr = _rare(m, l), l['reset'] ^ 1
    s0 = m.AND(l['g0'] ^ 1, l['g1'] ^ 1)
    s1 = m.AND(l['g0'], l['g1'] ^ 1)
    mux = lambda c, x, y: m.AND(m.AND(c, x) ^ 1, m.AND(c ^ 1, y) ^ 1) ^ 1
    return {'g0': m.AND(nr, mux(A, s0, l['g0'])), 'g1': m.AND(nr, mux(A, s1, l['g1']))}


def _gate(m, l, mutant=False):
    A, nr = _rare(m, l), l['reset'] ^ 1
    hold = lambda t: m.AND(t, A ^ 1)
    go = lambda t: m.AND(t, A)
    t0 = m.AND(l['reset'] ^ 1, m.AND(go(l['t2']) ^ 1, hold(l['t0']) ^ 1)) ^ 1
    t1 = m.AND(nr, m.AND(go(l['t2'] if mutant else l['t0']) ^ 1, hold(l['t1']) ^ 1) ^ 1)
    t2 = m.AND(nr, m.AND(go(l['t1']) ^ 1, hold(l['t2']) ^ 1) ^ 1)
    return {'t0': t0, 't1': t1, 't2': t2}


def _design(tmp_path, mutant=False):
    ins = ['reset'] + [f'a{i}' for i in range(A_BITS)]
    g, gm = _seq(tmp_path, 'gold', ins, ['g0', 'g1'], _gold)
    t, tm = _seq(tmp_path, 'gate', ins, ['t0', 't1', 't2'], lambda m, l: _gate(m, l, mutant))
    gm['latch'] = {i: [(f'u_dut.st[{i}]$_DFF_P_.lecq', 0)] for i in gm['latch']}
    tm['latch'] = {i: [(f'u_dut.st#t[{i}]$_DFF_P_.lecq', 0)] for i in tm['latch']}
    return lec.Lec(g, gm, t, tm)


def test_rare_transition_fsm_gets_unique_map_and_proves(tmp_path):
    L = _design(tmp_path)
    log = []
    assert lec.fsm_proposals(L, log) == 3, log
    m, _ = L.build(with_compare=True, with_hyp=True)
    assert set(_sim_prove(m).values()) == {'proved'}, log


def test_rare_transition_mutant_never_proves(tmp_path):
    L = _design(tmp_path, mutant=True)
    log = []
    lec.fsm_proposals(L, log)
    if any(h[0] == 'cube' for h in L.hyp.values()):
        m, _ = L.build(with_compare=True, with_hyp=True)
        assert 'differs' in _sim_prove(m).values()
