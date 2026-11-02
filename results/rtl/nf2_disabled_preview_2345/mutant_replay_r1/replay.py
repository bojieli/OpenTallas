import pathlib,json,importlib.util,hashlib,os,time
subject=pathlib.Path('/subject');r=subject/'proof/mutant';w=pathlib.Path('/out');old=json.load(open(r/'lec.json'));used=old['reset_contract']['used'];os.environ['OT_LEC_RESET_CYCLES']=str(used);t=time.time();logs=[]
s=importlib.util.spec_from_file_location('F','/out/lec.py');F=importlib.util.module_from_spec(s);s.loader.exec_module(F)
L=F.Lec(F.read_aig(r/'gold.aig'),F.read_map(r/'gold.map'),F.read_aig(r/'gate.aig'),F.read_map(r/'gate.map'));L.kit_reset_ports=old['kit_reset_ports']
F.normalize_gold_elements(L,F.slang_elements(r/'gold.aliases.json'),logs);F.json_alias_keys(L,logs,work=r);F.slang_element_keys(L,logs,work=r);F.alias_arrays(L,logs,work=r)
assert r.name=='mutant';assert hashlib.sha256((r/'hyp.json').read_bytes()).hexdigest()=='a19a51d48ace12b67176667d69b83c6c65d82628f83ecfa723aeb4b60303066b';profile=json.load(open(r/'hyp.json'));assert len(profile)==945;prior={(sd,k):tuple(h) for sd,k,h in profile};missing=[]
for (sd,k),h in prior.items():
 p=L.gp if sd in ('gold','both') else L.tp
 if k not in p:missing.append([sd,k,'key'])
 if h[0]=='eq' and h[2] not in (L.gp if h[1]=='gold' else L.tp):missing.append([sd,k,'partner',h[2]])
meta=dict(classification='MUTANT_ONLY_RETAINED_PROFILE_FAULT_DIAGNOSTIC',checker_commit='0c84369b0',checker_sha256=hashlib.sha256(pathlib.Path(F.__file__).read_bytes()).hexdigest(),prior_sha256=hashlib.sha256((r/'hyp.json').read_bytes()).hexdigest(),prior_count=len(prior),missing_prior=missing,reset_contract=old['reset_contract'],native_verdict_unchanged=old['counts'],no_full_comparepoint_proof=True)
(w/'CONTEXT.json').write_text(json.dumps(meta,indent=1)+'\n')
if missing:raise SystemExit('exact retained prior missing keys; refuse changed context')
L.hyp=dict(prior);keys=['ff:u_dut.u_leaf.u_core.gqv_groups['+str(i)+']' for i in [2]+list(range(5,21))];target='ff:u_dut.u_leaf.u_core.gqv[2]';hint=['gate',target,['cube','gold',keys,[0]*len(keys),1]]
rec=F.apply_hints(L,[hint],w,1000,logs,propose_only=True)
(w/'BASE.json').write_text(json.dumps(rec,indent=1)+'\n');assert rec['inverse_cube_base'][0]['covered'] and ('gate',target) in L.hyp
before=dict(prior)
F.prove_profile(L,w,1000,logs,rounds=32,single_cap=1000)
profile_stable=all(L.hyp.get(k)==v for k,v in before.items())
m,_=L.build(with_compare=True,with_hyp=False)
point='ff:u_dut.u_leaf.u_core.fault';idx=m.onames.index(point);m.outs=[m.outs[idx]];m.onames=[point]
st=F.prove(m,w,1000,logs,tag='pending_fault',single_cap=1000)
(w/'RESULT.json').write_text(json.dumps(dict(meta,hint=hint,pending_point_statuses=st,base=rec['inverse_cube_base'],all_hypotheses_jointly_reproved=True,original_profile_unchanged=profile_stable,inverse_relation_retained=('gate',target) in L.hyp,classification=('INEFFECTIVE_MUTANT' if st.get(point)=='proved' and profile_stable and ('gate',target) in L.hyp else 'REVIEW_NATIVE_RESULT'),final_hypotheses=len(L.hyp),original_hypotheses=len(prior),constraints=len(L.cons),elapsed_s=time.time()-t,no_comparepoint_reduction_claim=True),indent=1)+'\n');(w/'LEMMA.log').write_text('\n'.join(logs));(w/'FINAL_PROFILE.json').write_text(json.dumps([[sd,k,list(h)] for (sd,k),h in sorted(L.hyp.items())])+'\n');print('PENDING_FAULT',st,'ORIGINAL_PROFILE_UNCHANGED',profile_stable,flush=True)
