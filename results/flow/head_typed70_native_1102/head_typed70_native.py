"""One default-off HEAD70 diagnostic; no accepted hints/full comparison."""
import pathlib,json,hashlib,importlib.util,copy,gc
w=pathlib.Path('/out')
# Exact original-context construction already measured by R4. No discovery loop.
prefix=(w/'replay_r4.py').read_text().split('F.noreset_classify(L)')[0]
exec(compile(prefix,str(w/'replay_r4.py'),'exec'),globals())
F.PROVE_JOBS=2
F.noreset_classify(L)
spec=importlib.util.spec_from_file_location('I',w/'initial_set_projection.py');I=importlib.util.module_from_spec(spec);spec.loader.exec_module(I)
assert old['reset_contract']['used']==64 and len(L.matched)==58437 and len(prior)==12732
prior=copy.deepcopy(prior)
assert hashlib.sha256((w/'UNTRUSTED_typed70_candidate.json').read_bytes()).hexdigest()=='974733f86c0b87928cf9bfd2a74a665174628a35171ffbf971787acc3ef65a7d'
candidate=json.load(open(w/'UNTRUSTED_typed70_candidate.json'));fields=candidate['fields'];correlations=candidate['expected_projected_reset_image']['correlations']
expected=set();expected_gate=set()
for lane in ['a','b']:
 b=f'ff:u_dut.u_core.u_l{lane}.u_t3.g_txs[7].u_s.'
 expected|={b+f'q{j}[{i}]' for j in range(3) for i in range(9)}
 expected|={b+f'ld[{i}]' for i in range(8)}
 expected_gate|={b+f'q{j}#t[{i}]' for j in range(3) for i in range(9)}
 expected_gate|={b+f'ld#t[{i}]' for i in range(8)}
assert len(fields)==70 and {f['gold'] for f in fields}==expected
assert {f['gate'] for f in fields}==expected_gate
assert sum(f['kind']=='slot' for f in fields)==54 and sum(f['kind']=='load' for f in fields)==16
assert len(correlations)==16 and len({c['load'] for c in correlations})==16
assert {c['load'] for c in correlations}=={f['gold'] for f in fields if f['kind']=='load'}
for c in correlations:assert c['equals']==c['load'].replace('.u_s.ld[','.u_s.q0[')
for f in fields:
 assert ('.u_s.ld[' in f['gold'])==(f['kind']=='load')
 assert f['source_reset'] is None and f['source_clock']=='posedge ck; exact failing instance binds ck=clk'
 assert f['primitive']['type']=='DFFHQNx1_ASAP7_75t_R'
 assert set(f['primitive']['pins'])=={'CLK','D','QN'} and f['primitive']['pins']['CLK']=='ck'
 assert f['kind'] in ('slot','load') and f['proposed_xor']==0
resolved,transition_receipt=I.validate_native_bijection(L,fields,prior)
assert len(resolved)==70 and transition_receipt['independent_slots']==54
result=dict(status='CANDIDATE_ONLY_IN_PROGRESS',default_gate_changed=False,accepted_hints=False,original_verdict_unchanged=True,reset_contract=old['reset_contract'],matched_original=old['keypoints']['matched'],prior_count=len(prior),transition_compatibility=transition_receipt,images=[],controls=[])
def save():
 (w/'TYPED70_RESULT.json').write_text(json.dumps(result,indent=1)+'\n')
save()
def model(fs,sd):
 rows={f['gold']:f for f in fs};p=L.gp if sd=='gold' else L.tp
 def val(f):return p[f[sd]]^(f['proposed_xor'] if sd=='gate' else 0)
 slots={f['gold']:val(f) for f in fs if f['kind']=='slot'}
 cs=[(c['load'],val(rows[c['load']]),c['equals']) for c in correlations]
 return slots,cs

def native_reset(sd):
 d=L.gold if sd=='gold' else L.gate;p=L.gp if sd=='gold' else L.tp
 R=F.reset_vars(d,p,asserted=L.rst_asserted[sd],levels={},declared=L.kit_reset_ports)
 return d,R

def prove_exact(m,tag,allow_failure=False):
 names=list(m.onames);assert len(names)==len(set(names)) and names
 stats=F.prove(m,w,1000,logs,tag=tag,single_cap=1000)
 assert set(stats)==set(names),(tag,'proof output coverage differs',len(stats),len(names))
 passed=all(v=='proved' for v in stats.values())
 (w/'LEMMA.log').write_text('\n'.join(logs))
 return passed,stats

for sd in ['gold','gate']:
 d,R=native_reset(sd);slots,cs=model(fields,sd)
 for onto in [False,True]:
  m,receipt=I.reset_image_miter(F,d,R,64,slots,cs,onto=onto)
  expect=70 if onto else 16;assert len(m.onames)==expect
  tag=('onto_' if onto else 'upper_')+sd
  passed,stats=prove_exact(m,tag)
  result['images'].append(dict(side=sd,tag=tag,receipt=receipt,statuses=stats,passed=passed));save()
  del m;gc.collect()
  if not passed:
   result['status']='REFUSED_NATIVE_RESET_IMAGE';save();raise SystemExit(2)
# Initial-only facts never enter transition assumptions.
constants={};image_relations=[];bygold={f['gold']:f for f in fields}
for sd in ['gold','gate']:
 d,R=native_reset(sd);constants[sd]={**R,**L._rst_state[sd]}
 for c in correlations:
  a,b=bygold[c['load']],bygold[c['equals']]
  image_relations.append((sd,a[sd],b[sd],(a['proposed_xor']^b['proposed_xor']) if sd=='gate' else 0))
_,base_compat=I.validate_native_bijection(L,fields,prior,initial_image=dict(native_constants=constants,correlations=image_relations))
result['reset_image_prior_compatibility']=base_compat;save()
# Malformed-state controls refuse; no added constraints to make them pass.
for label,mutate in [('nonbijective',lambda fs:fs[1].update(gate=fs[0]['gate'])),('resetmixed',lambda fs:fs[0].update(source_reset='arst_n'))]:
 fs=copy.deepcopy(fields);mutate(fs)
 try:
  assert all(f['source_reset'] is None for f in fs)
  I.validate_native_bijection(L,fs,prior)
 except (AssertionError,ValueError) as e:
  result['controls'].append(dict(kind=label,rejected=True,reason=str(e)));continue
 raise RuntimeError(label+' negative unexpectedly accepted')
# Native wrong-slot/polarity controls target q0, so they must violate its
# proved reset correlation to ld. They never become accepted hypotheses.
for label in ['wrongslot','wrongpolarity']:
 fs=copy.deepcopy(fields);by={f['gold']:f for f in fs}
 b='ff:u_dut.u_core.u_la.u_t3.g_txs[7].u_s.'
 if label=='wrongslot':by[b+'q0[0]']['gate'],by[b+'q1[0]']['gate']=by[b+'q1[0]']['gate'],by[b+'q0[0]']['gate']
 else:by[b+'q0[0]']['proposed_xor']=1
 slots,cs=model(fs,'gate');d,R=native_reset('gate')
 m,receipt=I.reset_image_miter(F,d,R,64,slots,cs,onto=False)
 passed,stats=prove_exact(m,'negative_'+label)
 result['controls'].append(dict(kind=label,rejected=any(v=='differs' for v in stats.values()),statuses=stats));save()
 del m;gc.collect()
 if not any(v=='differs' for v in stats.values()):raise RuntimeError(label+' native negative lacks actual counterexample')
# Joint next-state proof retains original prior plus independently proved
# KEEP/hunt relations. No reset-only ld=q0 relation is assumed here.
L.hyp=copy.deepcopy(prior);L.cons=[]
collect=json.load(open(w/'UNTRUSTED_collective_hints.json'));missing_keep=set(old['kept_registers']['missing']['first'])
keep=[h for h in collect if h[0]!='cons' and h[2][0]=='eq' and h[2][2] in missing_keep]
hunt=[h for h in collect if h[0]=='cons' or h[2][0]=='cube'];assert len(keep)==4 and len(hunt)==8
F.apply_hints(L,hunt,w,1000,logs,propose_only=True)
assert all(k in L.hyp and L.hyp[k]==h for k,h in prior.items()), 'hunt changed original prior'
huntkeys={k for k,h in L.hyp.items() if k not in prior}
assert len(huntkeys)==6 and len(L.cons)==2
# Explicit physical KEEP obligations must not overwrite canonical retained tuples.
def rv(sd,k):
 p=L.gp if sd=='gold' else L.tp;lit=p[k];st=L._rst_state[sd]
 return (st[lit>>1]^(lit&1) if (lit>>1) in st else None),lit
def base_eq_cube(sd,k,h):
 v,lit=rv(sd,k)
 if h[0]=='eq':
  z,ol=rv(h[1],h[2]);return (sd==h[1] and lit==(ol^h[3])) or (v is not None and z is not None and v==(z^h[3]))
 assert h[0]=='cube'
 vals=[rv(h[1],x)[0] for x in h[2]]
 pred=0 if any(a is not None and a!=b for a,b in zip(vals,h[3])) else 1 if all(a is not None for a in vals) else None
 return v is not None and pred is not None and v==pred
base_checks=[dict(side=sd,key=k,covered=base_eq_cube(sd,k,h)) for (sd,k),h in L.hyp.items() if (sd,k) in huntkeys]
for sd,k,h in keep:
 assert sd in ('gold','gate') and h[0]=='eq'
 base_checks.append(dict(side=sd,key=k,covered=base_eq_cube(sd,k,h)))
cons_checks=[F.cons_base_check(L,sd,ks,a) for sd,ks,a in L.cons]
assert len(base_checks)==10 and len(cons_checks)==2
result['keep_hunt_native_base']=dict(relations=base_checks,constraints=cons_checks);save()
assert all(x['covered'] for x in base_checks+cons_checks), 'KEEP/hunt native BASE incomplete'
for f in fields:
 key=('gate',f['gate']);h=('eq','gold',f['gold'],f['proposed_xor'])
 if key not in L.hyp:L.hyp[key]=h
# Guard the full augmented correspondence again, not merely original12732.
I.validate_native_bijection(L,fields,L.hyp)
I.validate_native_bijection(L,fields,L.hyp,initial_image=dict(native_constants=constants,correlations=image_relations))
augmented=copy.deepcopy(L.hyp);augcons=copy.deepcopy(L.cons)
m,_=L.build(with_compare=True,with_hyp=True)
assert L.hyp==augmented and L.cons==augcons, 'build mutated exact augmented context'
assert all(k in L.hyp and L.hyp[k]==h for k,h in prior.items()), 'build changed original prior'
points=[x['point'] for x in old['unproven_points'] if any('.u_s.ld#t[' in k for k in x.get('cone_unmatched_keys',[]))]
assert len(points)==16 and len(set(points))==16
names=set(points)|{'hyp:'+sd+':'+key for sd,key in huntkeys}|{'cons:'+sd+':'+keys[0] for sd,keys,_ in L.cons}
selected=[(n,o) for n,o in zip(m.onames,m.outs) if n in names]
assert {n for n,_ in selected}==names
m.onames=[n for n,_ in selected];m.outs=[o for _,o in selected]
for sd,k,h in keep:
 m.onames.append('keep_next:'+sd+':'+k)
 m.outs.append(m.XOR(L.dlit[sd,k],L.dlit[h[1],h[2]]^h[3]))
for f in fields:
 m.onames.append('typed_next:'+f['gold'])
 m.outs.append(m.XOR(L.dlit['gate',f['gate']],L.dlit['gold',f['gold']]^f['proposed_xor']))
assert len(m.onames)==98
passed,stats=prove_exact(m,'joint_step_and_16_pending')
result.update(status='TYPED70_BOUNDED_DIAGNOSTIC_PASS' if passed else 'REFUSED_JOINT_STEP_OR_PENDING_OUTPUT',joint_statuses=stats,accepted_hints=False,full_proof=False,source_credit=False)
save();print(result['status'],flush=True)
