"""Reprove every saved-AIG invariant and compare, then detect one actual output-bit mutation.

Usage: prove_saved.py QUALIFIED_LEC_DIR SAVED_CONTEXT INPUT_AIG_DIR OUTPUT_DIR
The context contains candidates only. No saved proof verdict is trusted.
"""
import sys,pickle,json,collections,hashlib
from pathlib import Path
sys.path.insert(0,sys.argv[1]);import lec as LC
work=Path(sys.argv[4]);work.mkdir(parents=True,exist_ok=True)
with open(sys.argv[2],'rb') as f:L=pickle.load(f)
log=[]
def run(tag,compare):
 m,_=L.build(with_compare=compare,with_hyp=True)
 st=LC.prove(m,work,1000,log,tag=tag)
 rec=dict(collections.Counter(st.values()))
 print(tag,rec,flush=True)
 (work/(tag+'_status.json')).write_text(json.dumps(st))
 return st
hyp=run('all_induction',False)
if any(s!='proved' for s in hyp.values()):raise RuntimeError('induction did not close')
pos=run('all_compare',True)
if any(s!='proved' for s in pos.values()):raise RuntimeError('compare did not close')
target=next(k for k in sorted(L.tc) if k.startswith('po:') and k in L.gc and L.tc[k]>1)
L.tc[target]^=1
mut=run('mutant_output',True)
bad={k:s for k,s in mut.items()if s!='proved'}
if bad!={target:'differs'}:raise RuntimeError('output mutant not caught exactly')
L.tc[target]^=1
base=Path(sys.argv[3]);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
original={(sd,k):h for sd,k,h in json.loads((base/'hyp.json').read_text())}
extra=[[sd,k,h]for(sd,k),h in L.hyp.items()if original.get((sd,k))!=list(h)]
(work/'lec_hints.json').write_text(json.dumps(extra,indent=2))
rec={'schema':1,'kind':'exact_saved_AIG_formal_equivalence','verdict':'PASS',
 'top':'ot_v41_rom_elem_q_qxpq_w10_gb','induction_proved':len(hyp),
 'semantic_compare_proved':len(pos)-len(hyp),'full_miter_proved':len(pos),
 'differs':0,'undecided':0,'supplemental_hints':len(extra),
 'mutant':{'type':'invert one gate output bit','target':target,'caught':True,'differences':bad},
 'inputs':{n:sha(base/n)for n in ('gold.aig','gate.aig','gold.map','gate.map','gold.aliases.json','hyp.json')},
 'qualified_tool_sha256':sha(Path(sys.argv[1])/'lec.py'),
 'original_source_commit':None,'source_provenance':'UNKNOWN: original kit PROVENANCE.json absent; no current-RTL release qualification claimed',
 'rtl_changed':False,'added_cycles':0,
 'proof_scope':'Every current-state relation is included as an obligation and re-proved by lec.py; every original compare point is re-proved. Saved status dictionaries are not evidence inputs.'}
(work/'receipt.json').write_text(json.dumps(rec,indent=2));(work/'proof.log').write_text('\n'.join(log))
print(json.dumps(rec,indent=2),flush=True)
