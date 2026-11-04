import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import pytest
import bind_elab as E
from bind_compose import compose, CompositionError
from test_bind_compose import Rules, fixture


def test_absent_member_params_is_byte_identical():
    f1,s1=fixture(); a,_=compose(f1,Rules(),s1,E.Cell)
    f2,s2=fixture(); s2['cores'][0]['member_params']=None; s2['cores'][0].pop('member_params')
    b,_=compose(f2,Rules(),s2,E.Cell)
    assert a==b


def test_member_params_specialise_only_named_leaf():
    f,s=fixture(); s['cores'][0]['member_params']={'lane':{'PORT_REGS':1,'S3_COPY':1}}
    src,r=compose(f,Rules(),s,E.Cell); rtl=src[0][1]
    assert 'lane #(.PORT_REGS(1), .S3_COPY(1)) m2' in rtl
    assert 'front #(.W(2)) m0' in rtl and 'regpair #(.W(2)) m1' in rtl
    assert r['cores'][0]['member_params']=={'top.lane':{'PORT_REGS':'1','S3_COPY':'1'}}


def test_member_params_equal_existing_value_ok_conflict_fails():
    f,s=fixture(); s['cores'][0]['member_params']={'front':{'W':2}}
    compose(f,Rules(),s,E.Cell)
    f,s=fixture(); s['cores'][0]['member_params']={'front':{'W':3}}
    with pytest.raises(CompositionError,match='conflicts with bound value'): compose(f,Rules(),s,E.Cell)
    assert len(f.cells)==3


def test_member_params_unknown_module_or_unsafe_value_fails():
    f,s=fixture(); s['cores'][0]['member_params']={'nosuch':{'X':1}}
    with pytest.raises(CompositionError,match='matches no member'): compose(f,Rules(),s,E.Cell)
    f,s=fixture(); s['cores'][0]['member_params']={'lane':{'X':'1); evil'}}
    with pytest.raises(CompositionError,match='unsafe'): compose(f,Rules(),s,E.Cell)
    f,s=fixture(); s['cores'][0]['member_params']={}
    with pytest.raises(CompositionError,match='non-empty'): compose(f,Rules(),s,E.Cell)
