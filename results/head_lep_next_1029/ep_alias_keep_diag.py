#!/usr/bin/env python3
"""Diagnostic exact miter using preserved AIGs and previously proved hypotheses.
Not a complete kit signoff: KEEP retention and source regeneration remain separate.
"""
import sys,json,collections,hashlib,time
from pathlib import Path
sys.path.insert(0,'/src/tools/die_plan')
import lec
src=Path('/baseline'); out=Path('/out'); out.mkdir(exist_ok=True)
L=lec.Lec(lec.read_aig(src/'gold.aig'),lec.read_map(src/'gold.map'),lec.read_aig(src/'gate.aig'),lec.read_map(src/'gate.map'),None)
prelog=[]
lec.normalize_gold_elements(L,lec.slang_elements(src/'gold.aliases.json'),prelog)
lec.json_alias_keys(L,prelog,work=src)
lec.slang_element_keys(L,prelog,work=src)
lec.alias_arrays(L,prelog,work=src)
lec.relayout(L,prelog)
lec.renamed(L,prelog)
L.hyp={(sd,k):tuple(h) for sd,k,h in json.loads((src/'hyp.json').read_text())}
g=[f'ff:u_dut.u_lane.u.u_gb.hunt[{i}]' for i in range(2)]
t=[f'ff:u_dut.u_lane.u.u_gb.hunt#t[{i}]' for i in range(3)]
# Evidence: gate mapped DFF reset=001, gate D1=hunt_n[1], D2=hunt_n[0].
for code,bit in [(0,0),(1,2),(2,1)]:
    assert t[bit] in L.tonly
    L.hyp[('gate',t[bit])]=('cube','gold',g,[(code>>i)&1 for i in range(2)])
L.cons=[('gold',g,[[0,0],[1,0],[0,1]])]
# Same-edge p_take replicas: both candidates remain ordinary proof obligations.
ep='ff:u_dut.u_lane.u.u_ep.'
assert ep+'ok_f' in L.matched
assert ep+'g_fcopy.u_k_ok_f3.q' in L.matched
L.hyp[('both',ep+'g_fcopy.u_k_ok_f3.q')]=('eq','gold',ep+'ok_f',0)
alias_pairs=[('u_ep.in_ready','u_ep.rdy_k[3]'),
 ('u_gb.g_pc[0].g_b[0].a0','u_gb.g_pc[0].ps[5]'),
 ('u_gb.g_pc[11].g_b[280].a2','u_gb.g_pc[11].ps[3]'),
 ('u_gb.g_pc[5].g_b[140].a1','u_gb.g_pc[5].ps[4]')]
pre='ff:u_dut.u_lane.u.'
for gate,gold in alias_pairs:
 assert pre+gate in L.tp and pre+gold in L.gp
 L.hyp[('gate',pre+gate)]=('eq','gold',pre+gold,0)
import pickle
with (out/'state.pkl').open('wb') as f:pickle.dump(L,f)
m,kind=L.build(with_compare=True,with_hyp=True)
log=[]; st=lec.prove(m,out,1000,log,tag='seed_exact')
rec={'kind':'DIAGNOSTIC_EXACT_MITER_NOT_KIT_SIGNOFF','inputs':{f:hashlib.sha256((src/f).read_bytes()).hexdigest() for f in ['gold.aig','gold.map','gate.aig','gate.map','hyp.json']},'seed':{'0':0,'1':2,'2':1},'counts':dict(collections.Counter(st.values())),'failed':{k:v for k,v in st.items() if v!='proved'},'seed_hypotheses':{k:st.get('hyp:gate:'+k) for k in t},'constraint':st.get('cons:gold:'+g[0])}
decl,missing,const=lec.kept_registers(L,src/'gold.keep');rec['kept']={'declared':len(decl),'missing':missing,'constant':len(const)}
(out/'receipt.json').write_text(json.dumps(rec,indent=2)+'\n'); (out/'proof.log').write_text('\n'.join(log)+'\n')
print(json.dumps(rec,indent=2))

# Wrong retained-ready polarity must fail ordinary induction; no retention waiver.
L.hyp[('gate',pre+'u_ep.in_ready')]=('eq','gold',pre+'u_ep.rdy_k[3]',1)
mut,_=L.build(with_compare=True,with_hyp=True)
ml=[]; mst=lec.prove(mut,out,1000,ml,tag='wrong_ready_control')
mutrec={'counts':dict(collections.Counter(mst.values())),'wrong_ready':mst.get('hyp:gate:'+pre+'u_ep.in_ready')}
(out/'mutant.json').write_text(json.dumps(mutrec,indent=2)+'\n')
assert mutrec['wrong_ready']=='differs',mutrec
