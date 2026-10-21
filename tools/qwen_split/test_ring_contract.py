import copy
from types import SimpleNamespace
import pytest
from ring_contract import contract,native_depth,strap,first_read_edge
from reset_calendar_audit import finalize_model,audit


def model(depth):
    return dict(insts=[SimpleNamespace(name='s',master='qfd_rst_rep'),SimpleNamespace(name='r',master='qfd_rst_rep_p8')],
        buses=[('a','reset',1,[('external','s'),('s','d')]),('b','reset',1,[('external','r'),('r','d')]),
               ('c','reset',1,[('s','q0'),('first','en')]),('d','reset',1,[('r','q0'),('last','rs')])],
        fwd_lanes=dict(lanes=[dict(bid='x',lane='data',n=2,E=2,E_sta=2,K=2,D=depth,stations=['first'],landing='last')]))


def test_explicit_native_capacity_and_epoch():
    assert native_depth(5)==8 and native_depth(6)==8
    assert native_depth(4)==4
    assert first_read_edge(0,8)==18 and first_read_edge(0,4)==10
    assert first_read_edge(14,8)==16
    assert contract(8)==dict(D=8,address_bits=3,K_bits=4,epoch_modulus=16)
    assert strap(2,27,30,8)==15
    assert strap(2,27,30,4)==7
    with pytest.raises(ValueError):native_depth(9)
    for d in [3,5,6]:
        with pytest.raises(ValueError):contract(d)


def test_post_reset_tree_keeps_high_epoch_bit():
    m=model(8);finalize_model(m,{'external.s':24,'external.r':20})
    row=m['fwd_lanes']['lanes'][0]
    assert (row['K'],row['G_reset_tree'],row['R0_reset_tree'])==(15,27,30)
    assert [(i,p) for _,_,_,eps in m['buses'] if eps[0]==('last','tie_hi') for i,p in eps[1:]]==[('last',f'k{x}') for x in range(4)]
    assert 'mod 16' in row['K_basis']
    before=copy.deepcopy(m['buses']);finalize_model(m,{'external.s':24,'external.r':20});assert m['buses']==before


def test_mathematical_capacity_cannot_be_mislabeled_as_native():
    m=model(5);before=copy.deepcopy(m['buses'])
    with pytest.raises(ValueError,match='power-of-two'):finalize_model(m,{'external.s':24,'external.r':20})
    assert m['buses']==before


def test_old_three_bit_landing_cannot_consume_D8():
    netlist='qfd_rlyh0_x first (.en(src));\nqfd_landh_x last (.rs(dst),.k0(lo),.k1(lo),.k2(lo));\n'
    with pytest.raises(ValueError,match='full K strap'):
        audit(netlist,model(8)['fwd_lanes'],{'src':27,'dst':30})
