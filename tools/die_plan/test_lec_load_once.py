"""Persistent conditional-constant proof: a pulse writes an unreset register.

The ghost distinguishes initial RTL X from retained known data after the pulse.
Mutants exercise wrong value, wrong pulse and a nonconstant later hold/load.
"""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import lec
from test_lec_memory_layout import _seq, _sim_prove


def mux(m,s,a,b):
    return m.AND(m.AND(s,a)^1,m.AND(s^1,b)^1)^1


def design(tmp_path,mutant=None):
    def gold(m,l):
        en=m.AND(l['rn'],l['ld'])
        k=mux(m,en,l['a'] if mutant=='data_load' else 0,
              l['a'] if mutant=='bad_hold' else l['k'])
        return dict(v=en,k=k,o=l['k'])
    def gate(m,l):
        return dict(v=m.AND(l['rn'],l['ld']),o=0)
    g,gm=_seq(tmp_path,'gold',['rn','ld','a'],['v','k','o'],gold)
    t,tm=_seq(tmp_path,'gate',['rn','ld','a'],['v','o'],gate)
    return lec.Lec(g,gm,t,tm)


def run(tmp_path,monkeypatch,mutant=None,value=0,pulse=1):
    monkeypatch.setattr(lec,'prove',_sim_prove)
    L=design(tmp_path,mutant)
    h=['gold','ff:u_dut.k',['load_once',value,[[['ff:u_dut.v',pulse]]]]]
    r=lec.apply_hints(L,[h],tmp_path,100,[])
    a,_=L.build(with_compare=True,with_hyp=True)
    return L,r,_sim_prove(a)


def test_pulse_load_then_hold_proves_initial_x_and_retained_value(tmp_path,monkeypatch):
    L,r,st=run(tmp_path,monkeypatch)
    assert st['ff:u_dut.o']=='proved'
    assert st['hyp:gold:ff:u_dut.k']=='proved'
    assert not r['dropped'] and len(r['load_once'])==1
    assert r['load_once'][0]['base_filled'] is False


def test_wrong_constant_is_refuted(tmp_path,monkeypatch):
    L,r,st=run(tmp_path,monkeypatch,value=1)
    assert 'ff:u_dut.k' in r['dropped']
    assert st['ff:u_dut.o']=='differs'


def test_wrong_enable_cannot_mask_known_data(tmp_path,monkeypatch):
    L,r,st=run(tmp_path,monkeypatch,pulse=0)
    assert 'ff:u_dut.k' in r['dropped']


def test_nonconstant_load_is_refuted(tmp_path,monkeypatch):
    L,r,st=run(tmp_path,monkeypatch,mutant='data_load')
    assert 'ff:u_dut.k' in r['dropped']


def test_later_nonconstant_hold_is_refuted(tmp_path,monkeypatch):
    L,r,st=run(tmp_path,monkeypatch,mutant='bad_hold')
    assert 'ff:u_dut.k' in r['dropped']
