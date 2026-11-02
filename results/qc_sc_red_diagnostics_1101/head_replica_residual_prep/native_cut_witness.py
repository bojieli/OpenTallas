"""Read-only bit evaluation of retained native AIG, no solver/proof/CAD."""
from pathlib import Path
import json,hashlib,shutil,random
P=Path(__file__).parent;oldroot=Path('/srv/opentallas-scratch/claude/codex-head-typed70-0248')
assert hashlib.sha256((oldroot/'head_typed70_native.py').read_bytes()).hexdigest()=='4eb5de7a9bae505741c04c96fde10c811e28772f1dca515ff9bb7370ad359131'
shutil.copy2(oldroot/'lec.py',P/'lec.py')
if not (P/'subject').exists():(P/'subject').symlink_to(oldroot/'subject',target_is_directory=True)
s=(oldroot/'replay_r4.py').read_text().split('F.noreset_classify(L)')[0]
s=s.replace("w=pathlib.Path('/out')",'w=pathlib.Path('+repr(str(P))+')',1)
ns={};exec(compile(s,'EXACT_LABEL_RECONSTRUCTION_NO_BUILD_NO_RESET_NO_SOLVER','exec'),ns)
F,L,prior=ns['F'],ns['L'],ns['prior'];assert len(L.matched)==58437 and len(prior)==12732
# Native Aig.build creates these matched free inputs first. None of the added
# hunt/typed hypotheses target 'both'; retained prior and native build stay unchanged.
prefix=[k for k in L.matched if ('both',k) not in prior]
keys={k:i+1 for i,k in enumerate(prefix)}
a='ff:u_dut.u_core.u_la.u_ln.u.u_ep.rep_ra[0]';b='ff:u_dut.u_core.u_la.u_ln.u.u_ep.u_k_rep_o.q'
assert a in keys and b in keys
r=json.load(open(P/'RESIDUAL_RESULT.json'));res=r['residuals'];names=sorted(x['point']for x in res);point='ff:u_dut.u_core.u_la.u_ln.u.u_ep.a_v';idx=names.index(point)
d=F.read_aig(P/'original_469_plus_82_proved_relations.aig');assert d['O']==551
out=d['outputs'][idx] if 'outputs'in d else d['outs'][idx]
I=d['I'];ands=d['ands'];todo=[out>>1];seen=set();inputs=set()
while todo:
 v=todo.pop()
 if v in seen or v==0:continue
 seen.add(v)
 if v<=I:inputs.add(v);continue
 j=v-I-1;todo.extend([ands[2*j]>>1,ands[2*j+1]>>1])
assert keys[a]in inputs and keys[b]in inputs
order=sorted(v for v in seen if v>I);rng=random.Random(419);mask=(1<<256)-1
vals={v:rng.getrandbits(256)for v in sorted(inputs)}
def evalout(vals):
 z={0:0,**vals}
 for v in order:
  j=v-I-1;r0,r1=ands[2*j:2*j+2];z[v]=(z[r0>>1]^(mask if r0&1 else 0))&(z[r1>>1]^(mask if r1&1 else 0))
 return z[out>>1]^(mask if out&1 else 0)
bad=evalout(vals);equal=dict(vals);equal[keys[a]]=equal[keys[b]];eqbad=evalout(equal);witness=bad&~eqbad&mask
assert witness,'no causal random native cut witness found; no solver called'
lane=(witness&-witness).bit_length()-1
assign={v:(x>>lane)&1 for v,x in vals.items()}
key_by_var={v:k for k,v in keys.items()}
known={key_by_var[v]:x for v,x in assign.items()if v in key_by_var}
original=json.load(open(oldroot/'subject/lec/lec.json'))
pointrow=next(x for x in original['failing']if x['point']==point)
assert set(known)=={x.removeprefix('matched:')for x in pointrow['cone_state_keys']}
assert len(known)==pointrow['cone_support_count']==13
result={'scope':'ACTUAL_RETAINED_NATIVE_INDUCTION_CUT_BOOLEAN_WITNESS_NOT_REACHABLE_SEQUENCE','solver_or_native_job_called':False,'aig_sha256':hashlib.sha256((P/'original_469_plus_82_proved_relations.aig').read_bytes()).hexdigest(),'point':point,'native_output_index':idx,'native_output_literal':out,'native_inputs':I,'reachable_cone_ands':len(order),'cone_input_count':len(inputs),'native_input_indices':assign,'matched_input_names':known,'replica_indices':{a:keys[a],b:keys[b]},'original_bad':1,'cofactor_only_rep_ra_equals_rep_o_bad':0,'all_other_native_inputs_default':0,'limits':'Full native prior/typed/hunt context is encoded by the retained miter. This demonstrates one actual Boolean cut witness and causal cofactor only; it is not a solver replay, all256 closure, BASE/STEP proof, or reachable DUT trace.'}
(P/'native_cut_witness.json').write_text(json.dumps(result,indent=1)+'\n')
print({k:v for k,v in result.items()if k not in ['native_input_indices','matched_input_names']});print('states',known)
