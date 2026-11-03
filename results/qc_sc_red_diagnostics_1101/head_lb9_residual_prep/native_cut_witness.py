"""Source-only Boolean evaluation of saved native LB9 cut outputs; no solver."""
from pathlib import Path
import json,hashlib,shutil,random
P=Path(__file__).parent;T=Path('/srv/opentallas-scratch/claude/codex-head-typed70-0248');A=P.parent/'head_replica_prep'
shutil.copy2(T/'lec.py',P/'lec.py')
if not (P/'subject').exists():(P/'subject').symlink_to(T/'subject',target_is_directory=True)
s=(T/'replay_r4.py').read_text().split('F.noreset_classify(L)')[0].replace("w=pathlib.Path('/out')",'w=pathlib.Path('+repr(str(P))+')',1)
ns={};exec(compile(s,'PINNED_LABEL_PREFIX_ONLY_NO_BUILD_RESET_OR_SOLVER','exec'),ns)
F,L,prior=ns['F'],ns['L'],ns['prior'];assert len(L.matched)==58437 and len(prior)==12732
keys={k:i+1 for i,k in enumerate(k for k in L.matched if('both',k)not in prior)};inv={v:k for k,v in keys.items()}
a='ff:u_dut.u_core.u_lb.u_ln.u.u_ep.ok_f';b='ff:u_dut.u_core.u_lb.u_ln.u.u_ep.g_fcopy.u_k_ok_f3.q';assert a in keys and b in keys
r=json.load(open(A/'RESIDUAL_RESULT.json'));rows=[x for x in r['residuals']if x['matched_only']and x['native_status']=='differs'and'.u_lb.'in x['point']];assert len(rows)==9
names=sorted(x['point']for x in r['residuals']);old=json.load(open(T/'subject/lec/lec.json'));orig={x['point']:x for x in old['failing']+old['unproven_points']}
f=A/'original_469_plus_82_proved_relations.aig';sha=hashlib.sha256(f.read_bytes()).hexdigest();assert sha=='dd83b6002f6a7d4942dc0b322b95d05833915a6e6f3d388d33d8f291557a7649'
d=F.read_aig(f);I=d['I'];ands=d['ands'];outputs=d.get('outputs',d.get('outs'));mask=(1<<256)-1;results=[]
for ix,row in enumerate(rows):
 point=row['point'];idx=names.index(point);out=outputs[idx];todo=[out>>1];seen=set();inputs=set()
 while todo:
  v=todo.pop()
  if v in seen or not v:continue
  seen.add(v)
  if v<=I:inputs.add(v);continue
  j=v-I-1;todo.extend([ands[2*j]>>1,ands[2*j+1]>>1])
 assert keys[a]in inputs and keys[b]in inputs
 order=sorted(v for v in seen if v>I);rng=random.Random(2209+ix);vals={v:rng.getrandbits(256)for v in sorted(inputs)}
 # Select concrete live reset/interface values; this is an input vector, not an assumption.
 for v in inputs:
  if v not in inv: vals[v]=0
  elif '.u_lb.u_ln.u.u_ep.'not in inv[v]: vals[v]=mask
 vals[keys['ff:u_dut.u_core.u_lb.u_ln.u.u_ep.pv']]=mask
 vals[keys[a]]=mask;vals[keys[b]]=0
 def evaluate(vs):
  z={0:0,**vs}
  for v in order:
   j=v-I-1;r0,r1=ands[2*j:2*j+2];z[v]=(z[r0>>1]^(mask if r0&1 else 0))&(z[r1>>1]^(mask if r1&1 else 0))
  return z[out>>1]^(mask if out&1 else 0)
 bad=evaluate(vals);eq=dict(vals);eq[keys[a]]=eq[keys[b]];eqbad=evaluate(eq);w=bad&~eqbad&mask;print('DIAG',point,'vars',keys[a],keys[b],'bad',bad.bit_count(),'eqbad',eqbad.bit_count(),'fixed',w.bit_count(),flush=True);assert w,point
 lane=(w&-w).bit_length()-1;assign={v:(x>>lane)&1 for v,x in vals.items()};known={inv[v]:x for v,x in assign.items()if v in inv}
 assert set(known)=={x.removeprefix('matched:')for x in orig[point]['cone_state_keys']}
 assert len(known)==orig[point]['cone_support_count']
 results.append({'point':point,'native_output_index':idx,'native_output_literal':out,'cone_ands':len(order),'cone_inputs':len(inputs),'native_input_values':assign,'matched_input_values':known,'bad_before':1,'bad_after_only_ok_f_equals_fcopy3':0,'sample_equal_cofactor_bad_mask':str(eqbad),'sample_bits':256,'limits':'One native cut witness, not a reachable DUT sequence or universal proof.'})
out={'scope':'ACTUAL_NATIVE_LB9_CUT_BOOLEAN_WITNESSES_NO_SOLVER_PROOF_OR_JOB','aig_file':str(f),'aig_sha256':sha,'retained_prior':12732,'matched':58437,'cofactor_candidate':{a:keys[a],b:keys[b]},'other_native_inputs_default':0,'witnesses':results,'all9_have_causal_cut_witness':True,'current297status_unchanged':True}
(P/'native_cut_witnesses.json').write_text(json.dumps(out,indent=1)+'\n');print([(x['point'].split('.u_ep.')[-1],x['cone_ands'],x['cone_inputs'],x['sample_equal_cofactor_bad_mask'])for x in results])
