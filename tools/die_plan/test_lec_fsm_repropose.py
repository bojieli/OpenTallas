"""HBM-CORE-LAT-R4 (argmax_sw_vm_r2 LEC crash 10-27): fsm_proposals re-proposing a state vector in a later round
must replace its earlier encoding constraint, not add a second 'cons:gold:<key>' proof output (build() rejects
duplicate output names).  Also: OT_LEC_SUPERSET_VEC=1 keeps common 1-D bit names when the gate kept dead bits."""
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lec  # noqa: E402
from test_lec import _sim_prove  # noqa: E402


def fsm_design(gate):
    m = lec.Aig()
    reset = m.add_input('reset')
    q = [m.add_input(str(i)) for i in range(3 if gate else 2)]
    if gate:
        nxt = [m.AND(reset ^ 1, q[2] ^ 1) ^ 1, m.AND(reset ^ 1, q[0]), m.AND(reset ^ 1, q[1])]
    else:
        nxt = [m.AND(reset ^ 1, m.AND(q[0] ^ 1, q[1] ^ 1)), m.AND(reset ^ 1, m.AND(q[0], q[1] ^ 1))]
    d = dict(I=1, L=len(q), O=0, A=len(m.ands) // 2, latches=nxt, outputs=[], ands=m.ands)
    keys = [f'u_dut.st[{i}]' for i in range(len(q))]
    mp = {'input': {0: [('reset', 0)]}, 'output': {},
          'latch': {i: [(k + '$_DFF_P_.lecq', 0)] for i, k in enumerate(keys)}}
    return d, mp


def test_reproposed_fsm_replaces_its_constraint():
    g, gm = fsm_design(False)
    t, tm = fsm_design(True)
    L = lec.Lec(g, gm, t, tm)
    assert lec.fsm_proposals(L, []) == 3 and len(L.cons) == 1
    for k in [k for k, h in L.hyp.items() if h[0] == 'cube']:   # a correspondence round dropped the cubes
        L.hyp.pop(k)
    log = []
    assert lec.fsm_proposals(L, log) == 3
    assert len(L.cons) == 1, L.cons                                # pre-fix: 2 constraints, same output name
    m, _ = L.build(with_compare=True, with_hyp=True)               # pre-fix: LecError duplicate miter output names
    assert len(m.onames) == len(set(m.onames))
    assert set(_sim_prove(m).values()) == {'proved'}


def test_wrong_reproposal_still_fails():
    g, gm = fsm_design(False)
    t, tm = fsm_design(True)
    L = lec.Lec(g, gm, t, tm)
    lec.fsm_proposals(L, [])
    sd, keys, allowed = L.cons[0]
    L.cons = [(sd, keys, allowed[:1])]                             # too narrow an invariant: must fail, not hide
    m, _ = L.build(with_compare=True, with_hyp=True)
    assert 'differs' in _sim_prove(m).values()


def vec_design(bits):
    m = lec.Aig()
    d0 = m.add_input('d')
    q = [m.add_input(str(i)) for i in range(len(bits))]
    d = dict(I=1, L=len(bits), O=0, A=len(m.ands) // 2, latches=[d0] * len(bits), outputs=[], ands=m.ands)
    mp = {'input': {0: [('d', 0)]}, 'output': {},
          'latch': {i: [(f'u_dut.rec[{b}]$_DFF_P_.lecq', 0)] for i, b in enumerate(bits)}}
    return d, mp


def test_superset_vector_keeps_common_names(monkeypatch):
    g, gm = vec_design([1, 2])
    t, tm = vec_design([0, 1, 2])
    monkeypatch.delenv('OT_LEC_SUPERSET_VEC', raising=False)
    L = lec.Lec(g, gm, t, tm)                                      # default unchanged: whole vector re-keyed
    assert 'ff:u_dut.rec' in L.relaid and 'ff:u_dut.rec#t[1]' in L.tp and 'ff:u_dut.rec[1]' not in L.matched
    monkeypatch.setenv('OT_LEC_SUPERSET_VEC', '1')
    L = lec.Lec(g, gm, t, tm)
    assert {'ff:u_dut.rec[1]', 'ff:u_dut.rec[2]'} <= set(L.matched)
    assert 'ff:u_dut.rec#t[0]' in L.tonly
