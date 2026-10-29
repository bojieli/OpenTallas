"""Prove that a wrong-polarity entry alias is rejected using the retained exact AIGs.
The positive closure is independently recorded by the ordinary LEC stage.
"""
import sys,json,collections
from pathlib import Path
sys.path.insert(0,'/work');import lec
src=Path('/work/lec_ent_hints');out=Path('/control');log=[]
L=lec.Lec(lec.read_aig(src/'gold.aig'),lec.read_map(src/'gold.map'),lec.read_aig(src/'gate.aig'),lec.read_map(src/'gate.map'))
lec.normalize_gold_elements(L,lec.slang_elements(src/'gold.aliases.json'),log)
for f in (lec.json_alias_keys,lec.slang_element_keys,lec.alias_arrays):f(L,log,work=src)
for f in (lec.relayout,lec.renamed,lec.replica_proposals,lec.merged_proposals,lec.register_alias_proposals,lec.fsm_proposals):f(L,log)
# Materialize the anonymous Q keys exactly as apply_hints does before loading its proved profile.
for side in ('gold','gate'):
 points,compare,only=(L.gp,L.gc,L.gonly) if side=='gold' else (L.tp,L.tc,L.tonly)
 for lit,nxt in (L.ganon if side=='gold' else L.tanon):
  key=f'ff:__{side}_anon_{lit >> 1}';points[key],compare[key]=lit,nxt;only.append(key)
L.ganon,L.tanon=[],[]
L.hyp.clear();stale=[]
for sd,k,h in json.loads((src/'hyp.json').read_text()):
 valid=(k in L.gp and k in L.tp) if sd=='both' else k in (L.gp if sd=='gold' else L.tp)
 if h[0]=='eq':valid=valid and h[2] in (L.gp if h[1]=='gold' else L.tp)
 if not valid:stale.append([sd,k,h])
 else:L.hyp[sd,k]=tuple(h)
assert not stale,stale[:2]
k='ff:u_dut.u_fcore.u_wrq.g_sm[0].ent[0][0]';target=('gate',k)
assert L.hyp[target]==('eq','gold','ff:u_dut.u_fcore.u_wrq.g_sm[0].g_e[0].q[0]',0),L.hyp.get(target)
L.hyp[target]=L.hyp[target][:-1]+(1,)
m,_=L.build(with_compare=False,with_hyp=True)
st=lec.prove(m,out,1000,log,tag='wrong_polarity',single_cap=100)
assert st['hyp:gate:'+k]=='differs',st.get('hyp:gate:'+k)
(out/'result.json').write_text(json.dumps({'control':'wrong polarity on exact ent/q bit0','target':'hyp:gate:'+k,'target_result':st['hyp:gate:'+k],'counts':dict(collections.Counter(st.values()))},indent=2)+'\n')
(out/'proof.log').write_text('\n'.join(log))
print('WRQ_WRONG_HINT_CAUGHT',dict(collections.Counter(st.values())))
