import os,json,hashlib,importlib.util,collections,time
from pathlib import Path
r=Path('/srv/opentallas-scratch2/claude/qc-pinaccess-o/coll_n_hold80_1116');out=r/'lec5_diag3_512_1117';out.mkdir(exist_ok=True)
tool=r/'lec_kit/lec.py';s=importlib.util.spec_from_file_location('saved_lec',tool);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
p=r/'lec5/miter.aig';d=m.read_aig(p);assert d['L']==0
ids=[13676,13684,16032];names=['epoch_abort','fault_cause[0]','rx_v'];roots=[d['outputs'][i] for i in ids];I=d['I'];a=d['ands']
def closure(ls):
 seen=set();pis=set();stack=[x>>1 for x in ls]
 while stack:
  v=stack.pop()
  if not v:continue
  if v<=I:pis.add(v);continue
  if v in seen:continue
  seen.add(v);k=v-I-1;stack.extend([a[2*k]>>1,a[2*k+1]>>1])
 return seen,pis
seen,pis=closure(roots)
os.environ['OT_LEC_PARITY_TERMS']='512';b=m.Aig();mp={0:0}
for v in range(1,I+1):mp[v]=b.add_input('original_miter_pi_'+str(v))
counts=collections.Counter();orig=b.XOR
# Instrument request size without changing the existing tool's operations.
def counted(x,y):
 n=len(b._parity(x)[0])+len(b._parity(y)[0]);counts[n]+=1
 return orig(x,y)
b.XOR=counted
lit=lambda x:mp[x>>1]^(x&1)
t=time.time()
for v in sorted(seen):
 k=v-I-1;mp[v]=b.AND(lit(a[2*k]),lit(a[2*k+1]))
nroots=[lit(x) for x in roots]
rec=dict(schema='opentallas.lec.saved_cones.normalization.v1',source=str(p),source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),tool=str(tool),tool_sha256=hashlib.sha256(tool.read_bytes()).hexdigest(),setting={'OT_LEC_PARITY_TERMS':512},output_ids=ids,points=names,original_roots=roots,normalized_roots=nroots,cone_original_ands=len(seen),cone_original_pis=len(pis),normalization_s=time.time()-t,normalized_ands=len(b.ands)//2,max_requested_parity_terms=max(counts,default=0),fallback_requests=sum(c for n,c in counts.items() if n>512),histogram=dict(sorted(counts.items())),scope='Only exact existing 3 saved miter output cones; all original inputs arbitrary. Existing23124proved context untouched. OriginalUNPROVEN remains immutable; no source RTL edits or fullLEC retry.')
b.outs=nroots;b.onames=names;b.write(out/'three_normalized.aig')
(out/'receipt.json').write_text(json.dumps(rec,indent=2)+'\n');print(json.dumps({k:v for k,v in rec.items() if k not in ['histogram']},indent=2),flush=True)
if nroots==[0,0,0]:
 # Mutate ONE existing primary-input bit in ONE side of the actual fault_cause comparator.
 root=roots[1];v=root>>1;k=v-I-1;x0,x1=a[2*k],a[2*k+1]
 assert x0&1 and x1&1
 q0,q1=(x0>>1)-I-1,(x1>>1)-I-1
 left=list(a[2*q0:2*q0+2]);right=list(a[2*q1:2*q1+2]);assert set(left)=={z^1 for z in right}
 branch=left[0];other=left[1];cs,cp=closure([branch]);pi=sorted(cp)[len(cp)//2]
 mm={v:mp[v]^(1 if v==pi else 0) for v in range(I+1)}
 ml=lambda z:mm[z>>1]^(z&1)
 for v in sorted(cs):
  k=v-I-1;mm[v]=b.AND(ml(a[2*k]),ml(a[2*k+1]))
 mutant=b.XOR(ml(branch),lit(other))^(root&1)
 b.outs=[mutant];b.onames=['fault_cause0_real_pi_bitflip'];b.write(out/'mutant.aig')
 rec['mutant']=dict(original_pi_index=pi,mutation='Invert existing original_miter_pi only within one actual comparator branch; opposite branch unchanged',mutant_root=mutant,branch_source_literal=branch)
 (out/'receipt.json').write_text(json.dumps(rec,indent=2)+'\n');print('MUTANT_ROOT',mutant,flush=True)
