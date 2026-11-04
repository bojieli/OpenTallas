"""LEC-SELFTWIN(-NEAR) + LEC-MATCHED-TWIN (DIE-KV-65/66 LEC, qkd_kvs_ctl 11-04): rare-load hold registers renamed by synthesis
pair on the data they read, and two matched copies read differently by each side are one value; wrong ones stay refuted."""
import collections
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lec
from test_lec_memory_layout import _seq, _sim_prove


def _hold(tmp_path, n=8, swap=False):
    """gold e[i] / gate x[i] <= rare ? d[i] : self, read by matched o[i]; d[i] are matched data flops.  swap: gate x[0] loads d[1]."""
    sel = [f'in{i}' for i in range(24)]
    din = [f'di{i}' for i in range(n)]
    ds, os_ = [f'd[{i}]' for i in range(n)], [f'o[{i}]' for i in range(n)]

    def nxt(own, swp):
        def make(m, l):
            rare = l['rn']
            for s in sel:
                rare = m.AND(rare, l[s])
            out = {}
            for i in range(n):
                out[f'd[{i}]'] = m.AND(l['rn'], l[din[i]])
                src = l[f'd[{1 if swp and i == 0 else i}]']
                hold = m.AND(m.AND(rare, src) ^ 1, m.AND(rare ^ 1, l[f'{own}[{i}]']) ^ 1) ^ 1
                out[f'{own}[{i}]'] = m.AND(l['rn'], hold)
                out[f'o[{i}]'] = m.AND(l['rn'], l[f'{own}[{i}]'])
            return out
        return make
    ins = ['rn'] + sel + din
    g, gm = _seq(tmp_path, 'gold', ins, ds + os_ + [f'e[{i}]' for i in range(n)], nxt('e', False))
    t, tm = _seq(tmp_path, 'gate', ins, ds + os_ + [f'x[{i}]' for i in range(n)], nxt('x', swap))
    return lec.Lec(g, gm, t, tm)


def _closure_proved(L, passes=8):
    tried = collections.Counter()
    for _ in range(passes):
        if not lec.self_hold_twin_closure(L, [], tried):
            break
        while True:
            m, _ = L.build(with_compare=False, with_hyp=True)
            bad = [x for x, v in _sim_prove(m).items() if v != 'proved']
            if not bad:
                break
            for x in bad:
                _, side, k = x.split(':', 2)
                h = L.hyp.pop((side, k))
                tried[(side, k, h[2], h[3])] += 1
    m, _ = L.build(with_compare=True, with_hyp=True)
    return _sim_prove(m)


def test_rare_hold_pairs_on_its_own_data_input(tmp_path):
    L = _hold(tmp_path)
    tried = collections.Counter()
    assert lec.self_hold_twin_closure(L, [], tried) == 8
    for i in range(8):                       # right bit first try, although every name is equally far
        assert L.hyp[('gate', f'ff:u_dut.x[{i}]')] == ('eq', 'gold', f'ff:u_dut.e[{i}]', 0)
    assert set(_closure_proved(L).values()) == {'proved'}


def test_rare_hold_wrong_data_is_not_proved(tmp_path):
    # swap makes gate x[0] a copy of gold e[1]: the relation may pair, but no relation can make o[0] and o[1] both agree
    st = _closure_proved(_hold(tmp_path, swap=True))
    assert 'differs' in st.values()


def test_try_cap_bounds_a_register_with_no_partner(tmp_path):
    L = _hold(tmp_path, swap=True)
    tried = collections.Counter()
    for _ in range(40):
        if not lec.self_hold_twin_closure(L, [], tried):
            break
        for hk in [hk for hk in L.hyp if hk[0] == 'gate']:
            h = L.hyp.pop(hk)
            tried[(hk[0], hk[1], h[2], h[3])] += 1
    assert not lec.self_hold_twin_closure(L, [], tried)
    assert max(v for k, v in tried.items() if k[0] == 'selftwin') <= lec.SELFTWIN_TRIES


def _twins(tmp_path, gate_b_d='a_d'):
    def nxt(read, bsrc):
        def make(m, l):
            return {'a': m.AND(l['rn'], l['a_d']), 'b': m.AND(l['rn'], l[bsrc]),
                    'c': m.AND(l['rn'], l[read])}
        return make
    ins = ['rn', 'a_d', 'b_d']
    g, gm = _seq(tmp_path, 'gold', ins, ['a', 'b', 'c'], nxt('a', 'a_d'))
    t, tm = _seq(tmp_path, 'gate', ins, ['a', 'b', 'c'], nxt('b', gate_b_d))
    return lec.Lec(g, gm, t, tm)


def test_matched_copies_each_side_reads_another_are_one_value(tmp_path):
    L = _twins(tmp_path)
    m, _ = L.build(with_compare=True, with_hyp=True)
    assert _sim_prove(m)['ff:u_dut.c'] == 'differs'
    assert lec.structural_twin_closure(L, []) == 1
    assert L.hyp[('both', 'ff:u_dut.b')] == ('eq', 'gold', 'ff:u_dut.a', 0)
    m, _ = L.build(with_compare=True, with_hyp=True)
    assert set(_sim_prove(m).values()) == {'proved'}
    assert lec.structural_twin_closure(L, []) == 0


def test_matched_registers_of_other_data_are_not_related(tmp_path):
    L = _twins(tmp_path, gate_b_d='b_d')
    assert lec.structural_twin_closure(L, []) == 0
    m, _ = L.build(with_compare=True, with_hyp=True)
    assert 'differs' in _sim_prove(m).values()


def _cone_diff(tmp_path, owner_load='load'):
    """gold s reads gold-only owner, gate s reads matched active; owner == active unless owner loads on something else."""
    def nxt(gold):
        def make(m, l):
            set_hold = lambda q, en: m.AND(l['rn'], m.AND(l[en] ^ 1, l[q] ^ 1) ^ 1)
            out = {'active': set_hold('active', 'load'), 's': m.AND(l['rn'], l['owner' if gold else 'active'])}
            if gold:
                out['owner'] = set_hold('owner', owner_load)
            return out
        return make
    ins = ['rn', 'load', 'other']
    g, gm = _seq(tmp_path, 'gold', ins, ['active', 's', 'owner'], nxt(True))
    t, tm = _seq(tmp_path, 'gate', ins, ['active', 's'], nxt(False))
    return lec.Lec(g, gm, t, tm)


def test_cone_diff_names_the_merged_register(tmp_path):
    L = _cone_diff(tmp_path)
    log, tried = [], collections.Counter()
    assert lec.cone_diff_closure(L, log, tried) == 1
    assert L.hyp[('gold', 'ff:u_dut.owner')] == ('eq', 'gold', 'ff:u_dut.active', 0)
    m, _ = L.build(with_compare=True, with_hyp=True)
    assert set(_sim_prove(m).values()) == {'proved'}


def test_cone_diff_wrong_register_is_refuted(tmp_path):
    L = _cone_diff(tmp_path, owner_load='other')
    tried = collections.Counter()
    assert lec.cone_diff_closure(L, [], tried) == 1                  # a candidate only: simulation of the cone cannot tell
    m, _ = L.build(with_compare=False, with_hyp=True)
    assert 'proved' not in [v for x, v in _sim_prove(m).items() if 'owner' in x]
    for _ in range(lec.CONEDIFF_TRIES + 1):
        L.hyp.pop(('gold', 'ff:u_dut.owner'), None)
        lec.cone_diff_closure(L, [], tried)
    assert tried[('conediff', 'ff:u_dut.owner')] <= lec.CONEDIFF_TRIES
