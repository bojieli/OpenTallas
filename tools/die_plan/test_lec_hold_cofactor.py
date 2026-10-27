"""Refinement can refill exact twins without reviving a refuted relation."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import lec
from test_lec_unwritten_x import _seq
from test_lec import _exact_prove


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
