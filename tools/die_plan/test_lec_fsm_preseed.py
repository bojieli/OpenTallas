"""Explicit FSM seeds use ordinary ABC obligations; bad seeds cannot gate failures away."""
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parent))
import lec
from test_lec_memory_layout import _seq


def _run(tmp_path, bad=None):
    def gold(m,l):
        return {'s0':m.AND(l['rn'],l['s0']^1),
                's1':m.AND(l['rn'],m.XOR(l['s0'],l['s1'])),
                'o':m.AND(l['s0'],l['s1'])}
    def gate(m,l):
        z=m.AND(m.AND(l['t1']^1,l['t2']^1),l['t3']^1)
        return {'t1':m.AND(l['rn'],z),'t2':m.AND(l['rn'],l['t1']),
                't3':m.AND(l['rn'],l['t2']),'o':l['t3']}
    g,gm=_seq(tmp_path,'gold',['rn'],['s0','s1','o'],gold)
    t,tm=_seq(tmp_path,'gate',['rn'],['t1','t2','t3','o'],gate)
    L=lec.Lec(g,gm,t,tm)
    S=['ff:u_dut.s0','ff:u_dut.s1']
    hints=[['gate',f'ff:u_dut.t{c}',['cube','gold',S,[c&1,c>>1]]] for c in (1,2,3)]
    allowed=[[0,0],[1,0],[0,1],[1,1]]
    if bad=='encoding':hints[0][2][3]=[0,1]
    if bad=='reachable_state':allowed.pop() # state3 is reached from2
    hints.append(['cons','gold',S,allowed]);L.fsm_hints=hints
    log=[]
    # Zero discovery rounds: the explicit seed still enters the normal proof/refinement.
    lec.correspond(L,tmp_path,100,log,rounds=0,sim_iters=0,words=1)
    m,_=L.build(with_compare=True,with_hyp=True)
    st=lec.prove(m,tmp_path,100,log,tag='final')
    return L,st,log


def test_explicit_seed_proves_normal_abc_miter(tmp_path):
    L,st,log=_run(tmp_path)
    assert st and set(st.values())=={'proved'}
    assert len([h for h in L.hyp.values() if h[0]=='cube'])==3
    assert any('explicit untrusted hints seeded' in x for x in log)


@pytest.mark.parametrize('bad',['encoding','reachable_state'])
def test_bad_seed_is_dropped_and_function_still_fails(tmp_path,bad):
    L,st,log=_run(tmp_path,bad)
    assert st['ff:u_dut.o']=='differs'
    if bad=='encoding':assert ('gate','ff:u_dut.t1') not in L.hyp
    else:assert not L.cons
