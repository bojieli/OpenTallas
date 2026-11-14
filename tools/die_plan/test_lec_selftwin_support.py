"""A rare-control signature collision must not strand an unrelated local pair."""
import collections
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import lec
from test_lec_memory_layout import _seq, _sim_prove

def _design(tmp_path, mutant=False):
    inputs=['rn','data']+[f'{face}_hold{i}' for face in ('a','b') for i in range(24)]
    def make(gold):
        def nxt(m,l):
            result={}
            for face in ('a','b'):
                hold=1
                for i in range(24):hold=m.AND(hold,l[f'{face}_hold{i}'])
                for name in ('e1','re') if gold else (() if face=='b' else ('z',)):
                    key=f'{face}.{name}[0]'
                    value=l['data'] ^ int(mutant and face=='b' and name=='re')
                    result[key]=m.AND(l['rn'],m.AND(m.AND(hold,l[key])^1,m.AND(hold^1,value)^1)^1)
            return result
        return nxt
    g,gm=_seq(tmp_path,'gold',inputs,[f'{f}.{n}[0]' for f in ('a','b') for n in ('e1','re')],make(True))
    t,tm=_seq(tmp_path,'gate',inputs,['a.z[0]'],make(False))
    L=lec.Lec(g,gm,t,tm)
    L.hyp[('gate','ff:u_dut.a.z[0]')]=('eq','gold','ff:u_dut.a.e1[0]',0)
    return L

def test_each_support_class_gets_its_own_representative(tmp_path):
    L=_design(tmp_path)
    lec.self_hold_twin_closure(L,[],collections.Counter())
    assert L.hyp[('gold','ff:u_dut.b.re[0]')]==('eq','gold','ff:u_dut.b.e1[0]',0)
    m,_=L.build(with_compare=False)
    assert set(_sim_prove(m).values())=={'proved'}

def test_wrong_data_does_not_become_an_assumption(tmp_path):
    L=_design(tmp_path,mutant=True)
    lec.self_hold_twin_closure(L,[],collections.Counter())
    assert ('gold','ff:u_dut.b.re[0]') not in L.hyp
