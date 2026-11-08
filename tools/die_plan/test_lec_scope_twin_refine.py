"""A simulated rare-event false twin must not strand its valid alternate."""
import sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import lec
from test_lec_memory_layout import _seq


def _prove(m,*args,**kwargs):
    assert m.ni<=20
    mask=(1 << (1 << m.ni))-1
    values=[0]+[mask//((1 << (1 << i))+1) for i in range(m.ni)]
    get=lambda x:values[x>>1]^(mask if x&1 else 0)
    for i in range(0,len(m.ands),2):values.append(get(m.ands[i])&get(m.ands[i+1]))
    return {n:'proved' if get(o)==0 else 'differs' for n,o in zip(m.onames,m.outs)}


def _design(tmp_path,bug=False):
    inputs=['rn']+[f'p{i}' for i in range(16)]
    k,f,t='rd_bin[3]','rd_bit[3]','rd_gray[3]'
    def nxt(m,l,gate=False):
        rare=1
        for i in range(16):rare=m.AND(rare,l[f'p{i}'])
        q=l[t] if gate else l[k]
        val=m.XOR(q,rare)
        out={f:m.AND(l['rn'],l[f]),t:m.AND(l['rn'],val ^ int(bug and gate))}
        if not gate:out[k]=m.AND(l['rn'],val)
        return out
    g,gm=_seq(tmp_path,'gold',inputs,[k,f,t],lambda m,l:nxt(m,l))
    a,am=_seq(tmp_path,'gate',inputs,[f,t],lambda m,l:nxt(m,l,True))
    return lec.Lec(g,gm,a,am)


def test_rejected_first_twin_is_followed_by_valid_partner(tmp_path,monkeypatch):
    L=_design(tmp_path)
    monkeypatch.setattr(lec,'prove',_prove)
    first=lec.scope_twin_proposals(L,[])
    assert first[0][2][2]=='ff:u_dut.rd_bit[3]'  # actual rare-fire simulation false positive
    rec={};lec.auto_twins(L,rec,tmp_path,100,[])
    assert rec['auto_twins']['passes']>=2
    assert L.hyp[('gold','ff:u_dut.rd_bin[3]')]==('eq','gold','ff:u_dut.rd_gray[3]',0)
    m,_=L.build(with_compare=True,with_hyp=True)
    assert all(x=='proved' for x in _prove(m).values())


def test_gate_bug_still_fails_after_valid_twin(tmp_path,monkeypatch):
    L=_design(tmp_path,bug=True)
    monkeypatch.setattr(lec,'prove',_prove)
    rec={};lec.auto_twins(L,rec,tmp_path,100,[])
    m,_=L.build(with_compare=True,with_hyp=True)
    assert _prove(m)['ff:u_dut.rd_gray[3]']=='differs'
