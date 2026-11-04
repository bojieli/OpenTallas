"""Untrusted state invariants require native reset BASE as well as induction."""
from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parent))
import lec
from test_lec_memory_layout import _seq


def make_model(tmp_path,kind='hold',wrong=False):
    if kind=='hold':
        def gold(m,l):return {'s':l['s'],'o':l['s']}
        def gate(m,l):return {'s':l['s'],'o':1 if wrong else l['s']}
        names=['s','o']
    elif kind=='reset':
        def gold(m,l):return {'s':m.AND(l['rn'],l['s']^1),'o':l['s']}
        def gate(m,l):return {'s':m.AND(l['rn'],l['s']^1),'o':l['s']^(1 if wrong else 0)}
        names=['s','o']
    else:
        def gold(m,l):return {'s0':l['rn'],'s1':l['s0'],'o':l['s1']}
        gate=gold;names=['s0','s1','o']
    g,gm=_seq(tmp_path,'g',['rn'],names,gold)
    t,tm=_seq(tmp_path,'t',['rn'],names,gate)
    return lec.Lec(g,gm,t,tm)


def native_prove(L,path,tag):
    path.mkdir(exist_ok=True)
    m,_=L.build(with_compare=True,with_hyp=True)
    return m,lec.prove(m,path,100,[],tag=tag)


def test_inductive_but_unknown_reset_excluding_constraint_cannot_hide_difference(tmp_path,monkeypatch):
    monkeypatch.setenv('OT_LEC_RESET_CYCLES','4')
    L=make_model(tmp_path,wrong=True)
    baseline=set(L.build()[0].onames)
    L.cons=[('gold',['ff:u_dut.s'],[[1]])]
    # Negative control demonstrates the original preservation-only assumption:
    # s'=s is inductive, but the unknown native reset base also includes s=0.
    with monkeypatch.context() as patch:
        patch.setattr(lec,'filter_cons_bases',lambda L:[])
        old,st=native_prove(L,tmp_path/'old','old')
        assert set(st.values())=={'proved'} and 'cons:gold:ff:u_dut.s' in st
    new,st=native_prove(L,tmp_path/'new','new')
    assert not L.cons and L.cons_base_refused
    assert st['ff:u_dut.o']=='differs'
    assert set(new.onames)==baseline
    assert L.cons_base_refused[0]['unknown_bits']==1
    assert L.cons_base_refused[0]['covered_states']==1


def test_explicit_hint_refuses_known_reset_exclusion_with_reason(tmp_path,monkeypatch):
    monkeypatch.setenv('OT_LEC_RESET_CYCLES','4')
    L=make_model(tmp_path,'reset')
    hints=[['cons','gold',['ff:u_dut.s'],[[1]]]]
    rec=lec.apply_hints(L,hints,tmp_path,100,[],propose_only=True)
    assert not L.cons and rec['applied']==0
    assert rec['cons_base_refused'][0]['values']==[0]
    assert 'native ternary reset-base cube' in rec['cons_base_refused'][0]['why']


@pytest.mark.parametrize('wrong',[False,True])
def test_valid_reset_zero_fsm_still_proves_induction_and_all_design_points(tmp_path,monkeypatch,wrong):
    monkeypatch.setenv('OT_LEC_RESET_CYCLES','4')
    L=make_model(tmp_path,'reset',wrong=wrong)
    baseline=set(L.build()[0].onames)
    rec=lec.apply_hints(L,[['cons','gold',['ff:u_dut.s'],[[0],[1]]]],tmp_path,100,[],propose_only=True)
    assert rec['cons_base'][0]['values']==[0]
    m,st=native_prove(L,tmp_path/'proof','native')
    assert baseline<=set(m.onames) and st['cons:gold:ff:u_dut.s']=='proved'
    assert st['ff:u_dut.o']==('differs' if wrong else 'proved')


def test_unknown_native_base_complete_cover_is_accepted(tmp_path,monkeypatch):
    monkeypatch.setenv('OT_LEC_RESET_CYCLES','4')
    L=make_model(tmp_path)
    rec=lec.apply_hints(L,[['cons','gold',['ff:u_dut.s'],[[0],[1]]]],tmp_path,100,[],propose_only=True)
    assert rec['cons_base'][0]['values']==[None]
    _,st=native_prove(L,tmp_path/'proof','unknown')
    assert st and set(st.values())=={'proved'}


def test_uses_exact_current_reset_window_without_adding_edges(tmp_path,monkeypatch):
    L=make_model(tmp_path,'pipeline')
    hint=[['cons','gold',['ff:u_dut.s1'],[[0]]]]
    monkeypatch.setenv('OT_LEC_RESET_CYCLES','1')
    a=lec.apply_hints(L,hint,tmp_path,100,[],propose_only=True)
    assert a['cons_base_refused'][0]['reset_cycles']==1
    assert a['cons_base_refused'][0]['values']==[None]
    assert not L.cons
    # Only the explicitly changed caller contract permits the second edge.
    monkeypatch.setenv('OT_LEC_RESET_CYCLES','2')
    b=lec.apply_hints(L,hint,tmp_path,100,[],propose_only=True)
    assert b['cons_base'][0]['reset_cycles']==2 and b['cons_base'][0]['values']==[0]


@pytest.mark.parametrize('base,allowed,covered,unknown,count',[
    ([0,None],[[0,0],[0,1]],True,1,2),
    ([0,None],[[0,0],[1,1]],False,1,1),
    ([None],[[0],[0]],False,1,1),
    ([None,None],[[0,0],[0,1],[1,0],[1,1]],True,2,4),
    ([1,0],[[1,0],[1,0]],True,0,1),
])
def test_mask_cardinality_counts_only_distinct_compatible_states(base,allowed,covered,unknown,count):
    result=lec.cons_base_coverage(base,allowed)
    assert (result['covered'],result['unknown_bits'],result['covered_states'])==(covered,unknown,count)


def test_large_unknown_cube_does_not_enumerate_reset_assignments():
    result=lec.cons_base_coverage([None]*4096,[[0]*4096,[1]*4096])
    assert not result['covered'] and result['unknown_bits']==4096 and result['covered_states']==2


@pytest.mark.parametrize('wrong',[False,True])
def test_nontrivial_reset_zero_mod3_fsm_cover_and_negative(tmp_path,monkeypatch,wrong):
    monkeypatch.setenv('OT_LEC_RESET_CYCLES','4')
    def gold(m,l):
        return {'s0':m.AND(l['rn'],m.AND(l['s0']^1,l['s1']^1)),
                's1':m.AND(l['rn'],m.AND(l['s0'],l['s1']^1)),
                'o':m.XOR(l['s0'],l['s1'])}
    def gate(m,l):
        out=gold(m,l)
        if wrong:out['o']=l['s0']
        return out
    g,gm=_seq(tmp_path,'gold',['rn'],['s0','s1','o'],gold)
    t,tm=_seq(tmp_path,'gate',['rn'],['s0','s1','o'],gate)
    L=lec.Lec(g,gm,t,tm)
    baseline=set(L.build()[0].onames)
    hints=[['cons','gold',['ff:u_dut.s0','ff:u_dut.s1'],[[0,0],[1,0],[0,1]]]]
    rec=lec.apply_hints(L,hints,tmp_path,100,[],propose_only=True)
    assert rec['cons_base'][0]['values']==[0,0]
    m,st=native_prove(L,tmp_path/'proof','mod3')
    assert baseline<=set(m.onames)
    assert st['cons:gold:ff:u_dut.s0']=='proved'
    assert st['ff:u_dut.o']==('differs' if wrong else 'proved')


def test_direct_malformed_constraint_refused_before_miter(tmp_path):
    L=make_model(tmp_path)
    baseline=set(L.build()[0].onames)
    L.cons=[('gold',)]
    m,_=L.build()
    assert not L.cons and set(m.onames)==baseline
    assert L.cons_base_refused[0]['why']=='malformed constraint'


def test_cached_ff_alias_uses_current_literal_polarity(tmp_path,monkeypatch):
    monkeypatch.setenv('OT_LEC_RESET_CYCLES','4')
    L=make_model(tmp_path,'reset')
    assert lec.cons_base_check(L,'gold',['ff:u_dut.s'],[[0]])['covered']
    L.gp['ff:u_dut.alias']=L.gp['ff:u_dut.s']^1
    result=lec.cons_base_check(L,'gold',['ff:u_dut.alias'],[[1]])
    assert result['covered'] and result['values']==[1]


def test_changed_reset_pi_projection_cannot_reuse_cached_base(tmp_path,monkeypatch):
    monkeypatch.setenv('OT_LEC_RESET_CYCLES','1')
    monkeypatch.setenv('OT_LEC_RESET_POLARITY','name')
    L=make_model(tmp_path,'pipeline')
    assert lec.cons_base_check(L,'gold',['ff:u_dut.s0'],[[0]])['covered']
    reset=next(k for k in L.gp if k.startswith('pi:') and 'rn' in k)
    L.gp[reset]^=1
    L._release_states={'stale': 'old native base'}
    result=lec.cons_base_check(L,'gold',['ff:u_dut.s0'],[[0]])
    assert not result['covered'] and result['values']==[1]
    assert result['reset_cycles']==1 and not hasattr(L,'_release_states')


def test_failed_refresh_never_publishes_partial_or_old_stamp(tmp_path,monkeypatch):
    monkeypatch.setenv('OT_LEC_RESET_CYCLES','4')
    monkeypatch.setenv('OT_LEC_RESET_POLARITY','name')
    L=make_model(tmp_path,'reset')
    assert lec.cons_base_check(L,'gold',['ff:u_dut.s'],[[0]])['covered']
    previous=L._rst_state
    native=lec.reset_state
    def fail_gate(graph,reset,cycles):
        if graph is L.gate:raise ValueError('deliberate gate reset failure')
        return native(graph,reset,cycles)
    monkeypatch.setattr(lec,'reset_state',fail_gate)
    with pytest.raises(ValueError,match='gate reset failure'):lec.noreset_classify(L)
    assert not hasattr(L,'_rst_stamp') and L._rst_state is previous
    result=lec.cons_base_check(L,'gold',['ff:u_dut.s'],[[0]])
    assert not result['covered'] and 'unavailable' in result['why']


def test_replaced_raw_graph_invalidates_cached_reset(tmp_path,monkeypatch):
    monkeypatch.setenv('OT_LEC_RESET_CYCLES','4')
    L=make_model(tmp_path,'reset')
    assert lec.cons_base_check(L,'gold',['ff:u_dut.s'],[[0]])['covered']
    stamp=L._rst_stamp
    L.gold=dict(L.gold)
    assert lec.cons_base_check(L,'gold',['ff:u_dut.s'],[[0]])['covered']
    assert L._rst_stamp!=stamp


def test_aliased_unknown_bits_are_conservatively_overapproximated(tmp_path,monkeypatch):
    monkeypatch.setenv('OT_LEC_RESET_CYCLES','4')
    L=make_model(tmp_path)
    L.gp['ff:u_dut.inverse']=L.gp['ff:u_dut.s']^1
    result=lec.cons_base_check(L,'gold',['ff:u_dut.s','ff:u_dut.inverse'],[[0,1],[1,0]])
    assert not result['covered'] and result['values']==[None,None]
    assert result['unknown_bits']==2  # no unstated relational base assumption
