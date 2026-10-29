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
import shutil
for fn in ['gold.aliases.json','gold.keep']:
    shutil.copyfile(src/fn,out/fn)
progress=[]
lec.correspond(L,out,1000,progress,rounds=2,sim_iters=2,words=2)
(out/'correspond.log').write_text('\n'.join(progress)+'\n')
m,kind=L.build(with_compare=True,with_hyp=True)
log=[]; st=lec.prove(m,out,1000,log,tag='seed_exact')
rec={'kind':'DIAGNOSTIC_EXACT_MITER_NOT_KIT_SIGNOFF','inputs':{f:hashlib.sha256((src/f).read_bytes()).hexdigest() for f in ['gold.aig','gold.map','gate.aig','gate.map','hyp.json']},'seed':{'0':0,'1':2,'2':1},'counts':dict(collections.Counter(st.values())),'failed':{k:v for k,v in st.items() if v!='proved'},'seed_hypotheses':{k:st.get('hyp:gate:'+k) for k in t},'constraint':st.get('cons:gold:'+g[0]),'failed_support':{n:sorted({str(kind[v]) for v in m.cone_inputs(m.outs[m.onames.index(n)]) if kind[v][0] not in ('matched','paired')}) for n,vv in st.items() if vv!='proved'}}
(out/'receipt.json').write_text(json.dumps(rec,indent=2)+'\n'); (out/'proof.log').write_text('\n'.join(log)+'\n')
print(json.dumps(rec,indent=2))
