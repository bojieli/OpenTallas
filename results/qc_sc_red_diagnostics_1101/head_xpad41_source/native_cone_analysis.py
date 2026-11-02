"""Read-only names/Boolean cones of retained native41 outputs; no solver/proof."""
from pathlib import Path
import json,hashlib,shutil,random
P=Path(__file__).parent;T=Path('/srv/opentallas-scratch/claude/codex-head-typed70-0248');A=P.parent/'head_replica_prep'
shutil.copy2(T/'lec.py',P/'lec.py')
if not(P/'subject').exists():(P/'subject').symlink_to(T/'subject',target_is_directory=True)
s=(T/'replay_r4.py').read_text().split('F.noreset_classify(L)')[0].replace("w=pathlib.Path('/out')",'w=pathlib.Path('+repr(str(P))+')',1);ns={};exec(compile(s,'LABEL_RECONSTRUCTION_ONLY','exec'),ns)
F,L,prior=ns['F'],ns['L'],ns['prior'];assert len(L.matched)==58437 and len(prior)==12732
# Reproduce only input enumeration, not transition construction or new assumptions.
hd=dict(prior)
for row in json.load(open(T/'UNTRUSTED_collective_hints.json')):
 if row[0]!='cons'and row[2][0]=='cube':
  sd,key,h=row;hd[sd,key]=tuple(h)
for f in json.load(open(T/'UNTRUSTED_typed70_candidate.json'))['fields']:hd.setdefault(('gate',f['gate']),('eq','gold',f['gold'],f['proposed_xor']))
inames=[k for k in L.matched if('both',k)not in hd];matched_n=len(inames)
unwritten={k for k in L.gonly if k.startswith('ff:')and L.gc.get(k)==L.gp[k]}
for sd,ks in [('gold',L.gonly),('gate',L.tonly)]:
 for k in ks:
  h=hd.get((sd,k))
  if sd=='gold'and k in unwritten:inames.append('gold:'+k)
  elif h and h[0]in('const','eq','cube'):continue
  else:inames.append(sd+':'+k)
for sd,xs,anon in [('gold',L.gx,L.ganon),('gate',L.tx,L.tanon)]:
 inames +=[sd+':x'+str(lit>>1)for lit in xs];inames +=[sd+':anon'+str(lit>>1)for lit,_ in anon]
keys={k:i+1 for i,k in enumerate(inames)};inv={v:k for k,v in keys.items()};assert len(keys)==len(inames)
f=A/'original_469_plus_82_proved_relations.aig';sha=hashlib.sha256(f.read_bytes()).hexdigest();assert sha=='dd83b6002f6a7d4942dc0b322b95d05833915a6e6f3d388d33d8f291557a7649'
d=F.read_aig(f);I=d['I'];assert I==len(inames)==144687;ands=d['ands'];outs=d.get('outputs',d.get('outs'))
old=json.load(open(T/'subject/lec/lec.json'));allres=json.load(open(A/'RESIDUAL_RESULT.json'))['residuals'];names=sorted(x['point']for x in allres);rows=[x for x in old['failing']if x['cone_unmatched_keys']];assert len(rows)==41
pairs=[('ff:u_dut.u_core.u_la.u_ln.u.u_ep.rep_ra['+str(i)+']','ff:u_dut.u_core.u_la.u_ln.u.u_ep.u_k_rep_o.q')for i in[0,1]]+ [('ff:u_dut.u_core.u_lb.u_ln.u.u_ep.ok_f','ff:u_dut.u_core.u_lb.u_ln.u.u_ep.g_fcopy.u_k_ok_f3.q')]
pairs += [('ff:u_dut.u_core.u_la.u_ln.u.u_ep.ok_f','ff:u_dut.u_core.u_la.u_ln.u.u_ep.g_fcopy.u_k_ok_f3.q')]
mask=(1<<1024)-1;result=[]
for ix,row in enumerate(rows):
 point=row['point'];index=names.index(point);out=outs[index];todo=[out>>1];seen=set();inputs=set()
 while todo:
  v=todo.pop()
  if not v or v in seen:continue
  seen.add(v)
  if v<=I:inputs.add(v);continue
  j=v-I-1;todo.extend([ands[2*j]>>1,ands[2*j+1]>>1])
 order=sorted(v for v in seen if v>I);rng=random.Random(4410+ix);vals={v:rng.getrandbits(1024)for v in inputs}
 for v in inputs:
  k=inv[v]
  if k.startswith('ff:')and '.u_ep.'not in k and '.u_wtx.'not in k and '.body['not in k and not k.endswith('.iss_q'):vals[v]=mask
  if 'u_gb.hunt'in k:vals[v]=0
 if point.endswith('.fault')and point in keys:vals[keys[point]]=0
 def evaluate(vs):
  z={0:0,**vs}
  for v in order:
   j=v-I-1;r0,r1=ands[2*j:2*j+2];z[v]=(z[r0>>1]^(mask if r0&1 else 0))&(z[r1>>1]^(mask if r1&1 else 0))
  return z[out>>1]^(mask if out&1 else 0)
 bad=evaluate(vals);cf=dict(vals)
 for a,b in pairs:
  if keys[a]in inputs:cf[keys[a]]=vals.get(keys[b],0)
 after=evaluate(cf);xx=[v for v in inputs if inv[v].startswith('gold:x')];flip=dict(vals)
 for v in xx:flip[v]^=mask
 xbad=evaluate(flip)
 rec={'point':point,'class':'gold_literal_X'if xx else'padding_hold_state','native_output_index':index,'native_output_literal':out,'cone_ANDs':len(order),'cone_inputs':len(inputs),'input_names':[inv[v]for v in sorted(inputs)],'literal_X_names':[inv[v]for v in xx],'original_bad_bits':bad.bit_count(),'after_source_correspondence_candidate_cofactors_bad_bits':after.bit_count(),'literal_X_flip_changed_bits':(bad^xbad).bit_count(),'finite_samples':1024,'proof':False}
 if '.u_wtx.oq_p['in point:
  bit=int(point.split('[')[-1].rstrip(']'));goldhold='gold:ff:u_dut.u_core.u_wtx.g_multi.hold['+str(bit)+']';assert keys[goldhold]in inputs
  values={v:0 for v in inputs}
  for v in inputs:
   k=inv[v]
   if k.startswith('ff:')and k not in ['ff:u_dut.u_core.iss_q','ff:u_dut.u_core.u_wtx.owe']and '.body['not in k:values[v]=mask
  values[keys[goldhold]]=mask
  idle_bad=evaluate(values);assert idle_bad==mask,(point,'idle_witness_not_observed')
  reset=dict(values);reset[keys[goldhold]]=0;assert evaluate(reset)==0
  rec['idle_native_witness']={'input_values':{inv[v]:1 if x==mask else 0 for v,x in values.items()},'bad':1,'cofactor_only_unreset_hold_pad_to0_bad':0,'next_valid_from_source':0,'next_beatindex_from_source':0,'meaning':'No first-word write; rawidlepayloadfreedom. Not a valid-data mismatch.'}
 result.append(rec)
(P/'native41_cones.json').write_text(json.dumps({'scope':'READONLY_SAVED_NATIVE41_CONES_BOOLEAN_SAMPLES_NOT_PROOF_OR_MASK','native_AIG_sha256':sha,'full_input_names_reconstructed':I,'original41counts_unchanged':True,'rows':result},indent=1)+'\n')
print([(x['point'].split('.u_ep.')[-1],x['class'],x['original_bad_bits'],x['after_source_correspondence_candidate_cofactors_bad_bits'],x['literal_X_flip_changed_bits'])for x in result])
