import pathlib,json,importlib.util,hashlib,os,time
r=pathlib.Path('/subject/lec');w=pathlib.Path('/out');old=json.loads((r/'lec.json').read_text());os.environ['OT_LEC_RESET_CYCLES']=str(old['reset_contract']['used']);t=time.time();logs=[]
s=importlib.util.spec_from_file_location('F','/out/lec.py');F=importlib.util.module_from_spec(s);s.loader.exec_module(F)
L=F.Lec(F.read_aig(r/'gold.aig'),F.read_map(r/'gold.map'),F.read_aig(r/'gate.aig'),F.read_map(r/'gate.map'));L.kit_reset_ports=old['kit_reset_ports']
F.normalize_gold_elements(L,F.slang_elements(r/'gold.aliases.json'),logs);F.json_alias_keys(L,logs,work=r);F.slang_element_keys(L,logs,work=r);F.alias_arrays(L,logs,work=r)
profile=json.loads((r/'hyp.json').read_text());prior={(sd,k):tuple(h) for sd,k,h in profile};missing=[]
for (sd,k),h in prior.items():
 p=L.gp if sd in ('gold','both') else L.tp
 if k not in p:missing.append([sd,k,'key'])
 if h[0]=='eq' and h[2] not in (L.gp if h[1]=='gold' else L.tp):missing.append([sd,k,'partner',h[2]])
gold='ff:u_dut.u_leaf.u_pc.u_pce.u_path.u_calendar.active_row[6]';gate='ff:u_dut.u_leaf.u_pc.u_pce.u_path.u_calendar.static_cmd_owner'
meta=dict(classification='SINGLE_MERGED_STATE_LEMMA_ONLY_NOT_FULL_EQ',original_verdict=old['verdict'],original_counts=old['counts'],reset_contract=old['reset_contract'],missing_prior=missing,prior_count=len(prior),input_sha256={n:hashlib.sha256((r/n).read_bytes()).hexdigest() for n in ['gold.aig','gate.aig','gold.map','gate.map','gold.aliases.json','hyp.json','lec.json']},checker_sha256=hashlib.sha256(pathlib.Path(F.__file__).read_bytes()).hexdigest())
(w/'CONTEXT.json').write_text(json.dumps(meta,indent=2)+'\n')
assert not missing
# Native BASE uses raw AIG reset propagation with NO hints or legal-state constraints.
F.noreset_classify(L)
def native(sd,k):
 lit=(L.gp if sd=='gold' else L.tp)[k];state=L._rst_state[sd]
 return None if lit>>1 not in state else state[lit>>1]^(lit&1)
base=dict(gold=native('gold',gold),gate=native('gate',gate),reset_cycles=old['reset_contract']['used'])
(w/'BASE.json').write_text(json.dumps(base,indent=2)+'\n');assert base['gold']==base['gate']==0
L.hyp=dict(prior);hint=['gold',gold,['eq','gate',gate,0]]
rec=F.apply_hints(L,[hint],w,1000,logs,propose_only=True);assert ('gold',gold) in L.hyp
m,_=L.build(with_compare=False,with_hyp=True);idx=m.onames.index('hyp:gold:'+gold);m.outs=[m.outs[idx]];m.onames=[m.onames[idx]]
st=F.prove(m,w,1000,logs,tag='merged_row6',single_cap=1000)
(w/'RESULT.json').write_text(json.dumps(dict(meta,hint=hint,base=base,statuses=st,constraints=len(L.cons),original_profile_unchanged=all(L.hyp.get(k)==h for k,h in prior.items()),elapsed_s=time.time()-t,no_remaining_compare_replay=True),indent=2)+'\n');(w/'LEMMA.log').write_text('\n'.join(logs));print(st,flush=True)
