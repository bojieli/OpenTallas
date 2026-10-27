"""Hold-cofactor discovery remains an untrusted, inductively checked proposal."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import lec
from test_lec_unwritten_x import _seq, _mux
from test_lec import _exact_prove


def _case(tmp_path, mutant=False):
    def gold(m,l):
        return {'array[0][0]': _mux(m,l['en'],l['d'],l['array[0][0]']),
                'array[1][0]': _mux(m,l['en'],l['d']^1,l['array[1][0]'])}
    def gate(m,l):
        return {'array#t[0]': _mux(m,l['en'],l['d'],l['array#t[0]']),
                'array#t[1]': _mux(m,l['en'],l['d']^int(not mutant),l['array#t[1]'])}
    g,gm=_seq(tmp_path,'gold',['en','d'],['array[0][0]','array[1][0]'],gold)
    t,tm=_seq(tmp_path,'gate',['en','d'],['array#t[0]','array#t[1]'],gate)
    return lec.Lec(g,gm,t,tm)


def test_relaid_hold_pair_proved(tmp_path):
    L=_case(tmp_path)
    assert lec.structural_cofactor_pairs(L,[])==2
    m,_=L.build(with_compare=False,with_hyp=True)
    assert set(_exact_prove(m).values())=={'proved'}


def test_refuted_hold_pair_not_retried(tmp_path):
    L=_case(tmp_path)
    rejected={('gate','ff:u_dut.array#t[0]','ff:u_dut.array[0][0]',0):1}
    assert lec.structural_cofactor_pairs(L,[],rejected)==1
    assert ('gate','ff:u_dut.array#t[0]') not in L.hyp


def test_wrong_data_pair_still_fails(tmp_path):
    L=_case(tmp_path,mutant=True)
    L.hyp[('gate','ff:u_dut.array#t[1]')]=('eq','gold','ff:u_dut.array[1][0]',0)
    m,_=L.build(with_compare=False,with_hyp=True)
    assert 'differs' in _exact_prove(m).values()


def test_refuted_twin_is_not_readded_in_refinement(tmp_path):
    g,gm=_seq(tmp_path,'tgold',['d'],['root','copy','out'],
              lambda m,x:{'root':x['d'],'copy':x['d'],'out':x['copy']})
    t,tm=_seq(tmp_path,'tgate',['d'],['root','out'],
              lambda m,x:{'root':x['d'],'out':x['root']})
    L=lec.Lec(g,gm,t,tm)
    rejected={('gold','ff:u_dut.copy','ff:u_dut.root',0):1}
    assert lec.structural_twin_closure(L,[],rejected)==0
    assert not L.hyp
    assert lec.structural_twin_closure(L,[])==1
    m,_=L.build(with_compare=True,with_hyp=True)
    assert set(_exact_prove(m).values())=={'proved'}
