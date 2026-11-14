"""Unnamed native QN state must bind its reset-qualified same-side Q first."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import lec
from test_lec_memory_layout import _seq,_sim_prove

def _design(tmp_path,wrong_data=False,unreset=False,all_hidden=False):
    def gold(m,l):return {'local':m.AND(l['rst_n'],l['d'])}
    def gate(m,l):
        d=l['native'] if unreset else m.AND(l['rst_n'],l['d'])
        other=m.AND(l['rst_n'],l['other']) if wrong_data else d
        return {'native':d,'hidden':other^1}
    ins=['rst_n','d','other']
    g,gm=_seq(tmp_path,'g',ins,['local'],gold)
    t,tm=_seq(tmp_path,'t',ins,['native','hidden'],gate)
    for i,names in list(tm['latch'].items()):
        if any('hidden' in name for name,bit in names):tm['latch'].pop(i)
    if all_hidden:tm['latch'].clear()
    L=lec.Lec(g,gm,t,tm);L.kit_reset_ports=['rst_n']
    if not all_hidden:L.hyp['gate','ff:u_dut.native']=('eq','gold','ff:u_dut.local',0)
    return L

def _promote(L):
    anon=[]
    for lit,nxt in L.tanon:
        key=f'ff:__gate_anon_{lit>>1}';L.tp[key]=lit;L.tc[key]=nxt;L.tonly.append(key);anon.append(('gate',key))
    L.tanon=[];return anon

def test_native_partner_can_already_have_cross_side_correspondence(tmp_path):
    L=_design(tmp_path);anon=_promote(L)
    assert len(anon)==1 and lec.native_anonymous_aliases(L,anon,[])==1
    assert L.hyp[anon[0]]==('eq','gate','ff:u_dut.native',1)
    m,_=L.build(with_compare=False)
    assert set(_sim_prove(m).values())=={'proved'}

def test_wrong_data_cannot_use_the_native_alias_rule(tmp_path):
    L=_design(tmp_path,wrong_data=True);anon=_promote(L)
    assert lec.native_anonymous_aliases(L,anon,[])==0
    assert anon[0] not in L.hyp

def test_unknown_reset_base_cannot_use_the_native_alias_rule(tmp_path):
    L=_design(tmp_path,unreset=True);anon=_promote(L)
    assert lec.native_anonymous_aliases(L,anon,[])==0

def test_wrong_polarity_is_still_a_proof_obligation(tmp_path):
    L=_design(tmp_path);anon=_promote(L)
    lec.native_anonymous_aliases(L,anon,[])
    L.hyp[anon[0]]=('eq','gate','ff:u_dut.native',0)
    m,_=L.build(with_compare=False)
    assert 'differs' in _sim_prove(m).values()

def test_public_register_of_the_other_side_is_never_a_native_alias(tmp_path):
    L=_design(tmp_path,all_hidden=True);anon=_promote(L)
    assert lec.native_anonymous_aliases(L,anon,[])==0
    assert not L.hyp

def test_anonymous_promotion_uses_native_alias_before_signatures(tmp_path,monkeypatch):
    L=_design(tmp_path)
    monkeypatch.setattr(lec,'prove',_sim_prove)
    rec=lec.apply_hints(L,[],tmp_path,1000,[],rounds=1)
    assert rec['native_anon_aliases']==1
    key=next(hk for hk in L.hyp if '__gate_anon_' in hk[1])
    assert L.hyp[key]==('eq','gate','ff:u_dut.native',1)
