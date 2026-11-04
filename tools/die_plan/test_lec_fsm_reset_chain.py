"""LEC-FSM-RESET (DH59-LEC 11-03; HEAD hd_mesh / hd_host l48rf KEEP FAIL + NOT EQ, every failing cone on
u_gb.hunt): yosys fsm recodes hunt (0/1/2, code 3 unreachable) one-hot, 0->t0, 1->t2, 2->t1.  Its async reset comes from
a registered relay tree whose levels async2sync ANDs together, so uniform random lanes release reset in 1 of 2^k lanes:
every sampled transition was reset -> (0, t0) and the one-hot search tied ('best 384, next 384').  At the larger lane
count a zero-hot map won on noise (0->t0, 1->zero-hot, 2->t1, 3->t2): it failed induction, hunt stayed free and
218 / 968 points 'differed'.  The search now holds reset controls inactive in 7/8 of the lanes and prefers one-hot;
the map is still only a proposal, proved by the same induction."""
import itertools
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lec  # noqa: E402
from test_lec_memory_layout import _seq  # noqa: E402

LEVELS = 12                                  # real kits: 7; deep enough here that uniform lanes never leave reset
RELAY = [f'r{i}' for i in range(LEVELS)]    # relay-tree registers (matched by name), each a reset level of hunt
INS = ['rst_n', 'bm', 'gb', 'due']


def _sim_prove_deep(m):
    """_sim_prove with enough lanes (1 of 2^LEVELS is out of reset) to see one transition of these tiny cones."""
    val, mask = m.simulate(8192, seed=12345)
    return {n: ("proved" if lec.lit_val(val, mask, o) == 0 else "differs") for n, o in zip(m.onames, m.outs)}


def _or(m, a, b):
    return m.AND(a ^ 1, b ^ 1) ^ 1


def _nreset(m, l):
    nr = l['r0']
    for i in range(1, LEVELS):
        nr = m.AND(nr, l[f'r{i}'])
    return nr


def nxt(c, bm, gb, due, mutant=False):
    """ot_s81ph_link_gbx_safe3 hunt_n.  mutant (gate only): a missing marker while locked re-hunts to 1, not 0."""
    if not gb:
        return c
    if c != 2:
        if bm:
            return 2 if c == 1 and due else 1
        return 0 if c == 1 and due else c
    if bm == due:
        return 2
    return 1 if bm or mutant else 0


def _cases(m, l):
    """(bm, gb, due, literal of that input combination)"""
    for bm, gb, due in itertools.product((0, 1), repeat=3):
        x = m.AND(m.AND(l['bm'] ^ (1 - bm), l['gb'] ^ (1 - gb)), l['due'] ^ (1 - due))
        yield bm, gb, due, x


def _gold(m, l):
    """gold: hunt = {g1, g0}, code 3 unreachable but defined."""
    nr, n = _nreset(m, l), [0, 0]
    for c in range(4):
        st = m.AND(l['g0'] ^ (1 - (c & 1)), l['g1'] ^ (1 - (c >> 1)))
        for bm, gb, due, x in _cases(m, l):
            to = nxt(c, bm, gb, due)
            for b in (0, 1):
                if (to >> b) & 1:
                    n[b] = _or(m, n[b], m.AND(st, x))
    return {'g0': m.AND(nr, n[0]), 'g1': m.AND(nr, n[1]), 'lk': m.AND(nr, m.AND(l['g0'] ^ 1, l['g1'])),
            **{r: l['rst_n'] for r in RELAY}}


def _gate(m, l, mutant=False):
    """gate: yosys fsm one-hot (netlist hunt[0..2]): 0 -> t0 (reset state), 1 -> t2, 2 -> t1."""
    nr, bit = _nreset(m, l), {0: 't0', 1: 't2', 2: 't1'}
    n = dict(t0=0, t1=0, t2=0)
    for c in range(3):
        for bm, gb, due, x in _cases(m, l):
            t = bit[nxt(c, bm, gb, due, mutant)]
            n[t] = _or(m, n[t], m.AND(l[bit[c]], x))
    return {'t0': _or(m, nr ^ 1, n['t0']), 't1': m.AND(nr, n['t1']), 't2': m.AND(nr, n['t2']),
            'lk': m.AND(nr, l['t1']), **{r: l['rst_n'] for r in RELAY}}


def _design(tmp_path, mutant=False):
    g, gm = _seq(tmp_path, 'gold', INS, ['g0', 'g1', 'lk'] + RELAY, _gold)
    t, tm = _seq(tmp_path, 'gate', INS, ['t0', 't1', 't2', 'lk'] + RELAY, lambda m, l: _gate(m, l, mutant))
    for mp, base, n in ((gm, 'hunt', 2), (tm, 'hunt#t', 3)):   # lk (reads hunt, as u_ep does) and the relay keep names
        mp['latch'] = {i: [(f'u_dut.{base}[{i}]$_DFF_P_.lecq', 0)] if i < n else v for i, v in mp['latch'].items()}
    return lec.Lec(g, gm, t, tm)


def test_reset_chain_fsm_gets_true_map_and_proves(tmp_path):
    L = _design(tmp_path)
    log = []
    assert lec.fsm_proposals(L, log) == 3, log
    assert any(x.startswith("fsm:") and "1->ff:u_dut.hunt#t[2]" in x and "zero-hot" not in x for x in log), log
    m, _ = L.build(with_compare=True, with_hyp=True)
    st = _sim_prove_deep(m)
    assert set(st.values()) == {'proved'}, [k for k, v in st.items() if v != 'proved']


def test_reset_chain_mutant_never_proves(tmp_path):
    L = _design(tmp_path, mutant=True)
    log = []
    lec.fsm_proposals(L, log)
    # whatever map is proposed, the difference stays: an induction failure or a differing compare point (with no map
    # at all hunt is free on both sides, so lk differs)
    m, _ = L.build(with_compare=True, with_hyp=True)
    assert 'differs' in _sim_prove_deep(m).values(), log


def test_reset_controls_found_and_data_inputs_not(tmp_path):
    L = _design(tmp_path)
    m, kind = L.build(with_compare=False, with_hyp=False)
    var = {(kd[:4], k): v for v, (kd, k) in kind.items() if kd in ("gold_only", "gate_only")}
    gk = [f'ff:u_dut.hunt[{i}]' for i in range(2)]
    tk = [f'ff:u_dut.hunt#t[{i}]' for i in range(3)]
    dl = [L.dlit[("gold", k)] for k in gk] + [L.dlit[("gate", k)] for k in tk]
    state = {var[("gold", k)] for k in gk} | {var[("gate", k)] for k in tk}
    ctl = lec._fsm_reset_controls(m, state, dl, 2)
    assert sorted(kind[v][1] for v in ctl) == sorted(f'ff:u_dut.{r}' for r in RELAY) and set(ctl.values()) == {1}, ctl
