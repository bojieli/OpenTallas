import importlib.util
from pathlib import Path
import pytest
import initial_set_projection as P
import lec as F


def design(reset_fixed_slot=False):
    # PI1 reset; latch2 slot holds arbitrary startup; latch3 copies slot.
    return dict(I=1,L=2,A=0,ands=[],latches=[0 if reset_fixed_slot else 4,4])


def proved_exhaustively(m):
    assert m.ni < 16
    for bits in range(1 << m.ni):
        val=[0]+[(bits >> i)&1 for i in range(m.ni)]
        for k in range(len(m.ands)//2):
            a,b=m.ands[2*k:2*k+2];val.append((val[a>>1]^(a&1))&(val[b>>1]^(b&1)))
        if any(val[x>>1]^(x&1) for x in m.outs):return False
    return True


def test_correlated_image_is_two_fields_one_free_coordinate():
    for onto in [False,True]:
        m,r=P.reset_image_miter(F,design(),{1:0},2,{'slot':4},[('load',6,'slot')],onto=onto)
        assert proved_exhaustively(m)
        assert r['independent_coordinates']==1 and r['load_correlations']==1
        assert r['no_hypotheses'] and r['no_constraints']


def test_wrong_correlation_and_wrong_polarity_do_not_prove():
    d=dict(I=1,L=3,A=0,ands=[],latches=[4,6,4])
    for onto in [False,True]:
        m,_=P.reset_image_miter(F,d,{1:0},2,{'a':4,'b':6},[('load',8,'b')],onto=onto)
        assert not proved_exhaustively(m)
        m,_=P.reset_image_miter(F,d,{1:0},2,{'a':4,'b':6},[('load',9,'a')],onto=onto)
        assert not proved_exhaustively(m)


def test_duplicate_or_reset_mixed_coordinate_refuses():
    with pytest.raises(ValueError,match='injective'):
        P.reset_image_miter(F,design(),{1:0},2,{'a':4,'alias':5},[])
    with pytest.raises(ValueError,match='reset-fixed'):
        P.reset_image_miter(F,design(True),{1:0},2,{'slot':4},[('load',6,'slot')])
    with pytest.raises(ValueError,match='distinct'):
        P.reset_image_miter(F,design(),{1:0},2,{'slot':4},[('load',4,'slot')])


def test_prefixes_match_existing_native_ternary_reset():
    d=dict(I=1,L=3,A=2,ands=[4,2,6,2],latches=[8,10,6])
    g=P.reset_prefixes(d,{1:0})
    assert next(g)=={}
    for n in range(1,5):assert next(g)==F.reset_state(d,{1:0},n)[0]


def test_inverted_native_literal_is_logical_seed_not_assumed_polarity():
    d=dict(I=1,L=2,A=0,ands=[],latches=[4,5])
    for onto in [False,True]:
        m,_=P.reset_image_miter(F,d,{1:0},2,{'slot':5},[('load',6,'slot')],onto=onto)
        assert proved_exhaustively(m)


def fixture():
    from types import SimpleNamespace
    return SimpleNamespace(gold=design(),gate=design(),gp={'s':4,'l':6},tp={'s#':4,'l#':6},matched=[])


def fields():
    return [{'gold':'s','gate':'s#','kind':'slot','proposed_xor':0},
            {'gold':'l','gate':'l#','kind':'load','proposed_xor':0}]


def test_bijection_prior_compatibility_is_not_base_acceptance():
    r,receipt=P.validate_native_bijection(fixture(),fields(),{('gate','s#'):('eq','gold','s',0)})
    assert len(r)==2 and not receipt['base_accepted']
    with pytest.raises(ValueError,match='conflicts'):
        P.validate_native_bijection(fixture(),fields(),{('gate','s#'):('eq','gold','s',1)})
    with pytest.raises(ValueError,match='collapses'):
        P.validate_native_bijection(fixture(),fields(),{('gold','s'):('const',0)})


def test_nonbijective_native_alias_and_unknown_key_refuse():
    f=fields();f[1]['gate']='s#'
    with pytest.raises(ValueError,match='nonbijective'):
        P.validate_native_bijection(fixture(),f,{})
    f=fields();f[1]['gate']='unknown'
    with pytest.raises(ValueError,match='missing'):
        P.validate_native_bijection(fixture(),f,{})


def test_existing_same_name_correspondence_cannot_be_silently_replaced():
    L=fixture();L.tp={'s':4,'l':6};L.matched=['s','l'];f=fields()
    f[0]['gate']='l';f[1]['gate']='s'
    # Existing shared-state identity plus a swapped mapping collapses the two
    # slots if both are claimed independent. The caller cannot erase it.
    f.append({'gold':'extra','gate':'extra','kind':'slot','proposed_xor':0})
    L.gold=dict(I=1,L=3,A=0,ands=[],latches=[4,6,8]);L.gate=dict(L.gold);L.gp['extra']=8;L.tp['extra']=8
    L.matched.append('extra')
    f[1]['kind']='slot';f[2]['kind']='load'
    with pytest.raises(ValueError,match='collapses'):
        P.validate_native_bijection(L,f,{})


def test_native_constant_alias_is_global_zero_not_free_state():
    L=fixture();L.gp['zero']=0;L.gp['one']=1
    for constant in ['zero','one']:
        with pytest.raises(ValueError,match='collapses'):
            P.validate_native_bijection(L,fields(),{('gold','s'):('eq','gold',constant,0)})


def test_predicate_rejection_follows_complete_equality_closure():
    L=fixture();L.gold=dict(I=1,L=3,A=0,ands=[],latches=[4,6,8]);L.gate=dict(L.gold)
    L.gp['alias']=8;L.tp['shadow']=8
    # Distinct named alias is tied to the independent slot by a retained eq.
    # Its cube cannot be silently dropped by direct-key-only membership.
    prior={('gold','alias'):('eq','gold','s',0),
           ('gate','shadow'):('cube','gold',['alias'],[1])}
    with pytest.raises(ValueError,match='closure'):
        P.validate_native_bijection(L,fields(),prior)


def test_empty_or_unknown_typed_domains_refuse():
    with pytest.raises(ValueError,match='nonempty'):
        P.validate_native_bijection(fixture(),[],{})
    f=fields();f[0]['kind']='arbitrary'
    with pytest.raises(ValueError,match='typed'):
        P.validate_native_bijection(fixture(),f,{})
    with pytest.raises(ValueError,match='nonempty'):
        P.reset_image_miter(F,design(),{1:0},2,{},[])


def test_combinational_native_alias_is_not_an_independent_parity_atom():
    L=fixture();L.gp['comb']=8
    with pytest.raises(ValueError,match='combinational'):
        P.validate_native_bijection(L,fields(),{('gold','comb'):('eq','gold','s',0)})
