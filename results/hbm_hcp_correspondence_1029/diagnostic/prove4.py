import os,json,collections,hashlib,pickle
from pathlib import Path
os.environ.setdefault('OT_LEC_RESET_CYCLES','4')
import lec_engine as lec
r=Path(__file__).parent;src=r/'inputs';out=r/'proof4';out.mkdir(exist_ok=True);log=[]
# Cached normalization of the immutable retained AIGs, aliases, original474
# hypotheses and zero state constraints. Created before any new hint in prove3.
with (r/'normalized.pkl').open('rb') as f:L=pickle.load(f)
p='ff:u_dut.u_fcore.u_core.u_core.'
keys=[p+'nlast_r[%d]'%k for k in range(8)]+[p+'d0[%d]'%k for k in range(6,14)]
for k in keys:
 assert k in L.gonly,k
 assert L.rst_val.get(('gold',k),(None,None))[0]==0,(k,L.rst_val.get(('gold',k)))
 L.hyp['gold',k]=('const',0)
held=lec.noreset_sound(L);base={k:held.get(('gold',k)) for k in keys}
assert all(e is not None for e in base.values()),base
assert not L.cons,'no new state constraints permitted in this target proof'
print('HCP_CANDIDATES',len(keys),'RESET_BASE',base,flush=True)
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
assert all(v=='proved' for v in st.values()),'full compare failed'
hints=[['gold',k,['const',0]] for k in keys]
(out/'hints.json').write_text(json.dumps(hints,indent=1)+'\n')
# A wrong source-constant is refuted by exactly the same induction engine.
L.hyp['gold',keys[0]]=('const',1)
mm,_=L.build(with_compare=False,with_hyp=True)
idx=mm.onames.index('hyp:gold:'+keys[0]);mm.outs=[mm.outs[idx]];mm.onames=[mm.onames[idx]]
wrong=lec.prove(mm,out,1000,log,tag='wrong_const',single_cap=200)
(out/'wrong_const.json').write_text(json.dumps(wrong))
print('WRONG_CONST',wrong,flush=True)
assert list(wrong.values())==['differs'],wrong
(out/'proof.log').write_text('\n'.join(log))
(out/'receipt.json').write_text(json.dumps(dict(status='ALL_COMPARE_AND_HYPOTHESES_PROVED',counts=dict(collections.Counter(st.values())),new_constant_facts=len(keys),replaced_equality_facts=8,reset_cycles=4,reset_base=base,wrong_const=wrong,source_aigs={n:hashlib.sha256((src/n).read_bytes()).hexdigest() for n in ('gold.aig','gate.aig','gold.map','gate.map','gold.aliases.json','hyp.json')}),indent=1)+'\n')
print('HCP_PROOF_DONE',flush=True)
