import os,sys,json,collections,hashlib
from pathlib import Path
os.environ.setdefault('OT_LEC_RESET_CYCLES','4')
import lec_engine as lec
r=Path(__file__).parent;src=r/'inputs';out=r/'proof2';out.mkdir(exist_ok=True);log=[]
L=lec.Lec(lec.read_aig(src/'gold.aig'),lec.read_map(src/'gold.map'),lec.read_aig(src/'gate.aig'),lec.read_map(src/'gate.map'))
lec.normalize_gold_elements(L,lec.slang_elements(src/'gold.aliases.json'),log)
for f in (lec.json_alias_keys,lec.slang_element_keys,lec.alias_arrays):f(L,log,work=src)
for f in (lec.relayout,lec.renamed,lec.replica_proposals,lec.merged_proposals,lec.register_alias_proposals,lec.fsm_proposals):f(L,log)
L.hyp.clear();dropped=[]
for sd,k,h in json.loads((src/'hyp.json').read_text()):
 valid=(k in L.gp and k in L.tp) if sd=='both' else k in (L.gp if sd=='gold' else L.tp)
 if h[0]=='eq':valid=valid and h[2] in (L.gp if h[1]=='gold' else L.tp)
 if valid:L.hyp[sd,k]=tuple(h)
 else:dropped.append([sd,k,h])
assert not dropped,dropped
p='ff:u_dut.u_fcore.u_core.u_core.'
keys=[p+'nout_r[1]']+[p+'d0[%d]'%k for k in range(6,14)]
lec.noreset_classify(L)
hints=[]
for k in keys:
 side='both' if k in L.matched else 'gold'
 assert (k in L.matched or k in L.gonly),k
 for sd in (('gold','gate') if side=='both' else ('gold',)):
  assert L.rst_val.get((sd,k),(None,None))[0]==0,(sd,k,L.rst_val.get((sd,k)))
 L.hyp[side,k]=('const',0); hints.append([side,k,['const',0]])
held=lec.noreset_sound(L)
base={sd+':'+k:held.get((sd,k)) for side,k,_ in hints for sd in (('gold','gate') if side=='both' else ('gold',))}
assert all(e is not None for e in base.values()),base
print('HCP_CANDIDATES',len(keys),'RESET_BASE',base,'CONS',len(L.cons),flush=True)
(out/'base.json').write_text(json.dumps(base,indent=1)+'\n')
m,_=L.build(with_compare=False,with_hyp=True)
st=lec.prove(m,out,1000,log,tag='joint',single_cap=200)
print('JOINT',len(st),collections.Counter(st.values()),flush=True)
(out/'joint.json').write_text(json.dumps(st))
assert all(v=='proved' for v in st.values()),'joint induction failed'
m,_=L.build(with_compare=True,with_hyp=True)
st=lec.prove(m,out,1000,log,tag='compare',single_cap=200)
print('COMPARE',len(st),collections.Counter(st.values()),flush=True)
(out/'compare.json').write_text(json.dumps(st))
(out/'proof.log').write_text('\n'.join(log))
(out/'hints.json').write_text(json.dumps(hints,indent=1)+'\n')
assert all(v=='proved' for v in st.values()),'full compare failed'
(out/'receipt.json').write_text(json.dumps(dict(status='ALL_COMPARE_AND_HYPOTHESES_PROVED',counts=dict(collections.Counter(st.values())),new_hypotheses=len(keys),reset_base=base,source_aigs={n:hashlib.sha256((src/n).read_bytes()).hexdigest() for n in ('gold.aig','gate.aig','gold.map','gate.map','gold.aliases.json','hyp.json')}),indent=1)+'\n')
# One deliberately wrong new constant must fail the same induction engine.
L.hyp['both',keys[0]]=('const',1)
mm,_=L.build(with_compare=False,with_hyp=True)
idx=mm.onames.index('hyp:both:'+keys[0]);mm.outs=[mm.outs[idx]];mm.onames=[mm.onames[idx]]
wrong=lec.prove(mm,out,1000,log,tag='wrong_const',single_cap=200)
(out/'wrong_const.json').write_text(json.dumps(wrong))
assert list(wrong.values())==['differs'],wrong
print('WRONG_CONST_CAUGHT',wrong,flush=True)
print('HCP_PROOF_DONE',flush=True)
