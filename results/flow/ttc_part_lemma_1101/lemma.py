import importlib.util,pathlib,json,hashlib,os,itertools,time
os.environ['OT_LEC_RESET_CYCLES']='64';t=time.time();w=pathlib.Path('/out');r=pathlib.Path('/subject/lec');logs=[]
s=importlib.util.spec_from_file_location('F','/subject/lec.py');F=importlib.util.module_from_spec(s);s.loader.exec_module(F)
L=F.Lec(F.read_aig(r/'gold.aig'),F.read_map(r/'gold.map'),F.read_aig(r/'gate.aig'),F.read_map(r/'gate.map'));L.kit_reset_ports=F.kit_reset_ports(pathlib.Path('/subject'))
# Reproduce the original name/layout normalizations only, without any new FSM discovery.
F.normalize_gold_elements(L,F.slang_elements(r/'gold.aliases.json'),logs)
F.json_alias_keys(L,logs,work=r);F.slang_element_keys(L,logs,work=r);F.alias_arrays(L,logs,work=r)
profile=json.load(open(r/'hyp.json'));prior={(sd,k):tuple(h) for sd,k,h in profile};missing=[]
for (sd,k),h in prior.items():
 side='gold' if sd=='both' else sd
 if k not in (L.gp if side=='gold' else L.tp):missing.append([sd,k,'key'])
 if h[0]=='eq' and h[2] not in (L.gp if h[1]=='gold' else L.tp):missing.append([sd,k,'partner',h[2]])
meta=dict(classification='UNTRUSTED_LEMMA_ONLY',prior_sha256=hashlib.sha256((r/'hyp.json').read_bytes()).hexdigest(),prior_count=len(prior),missing_prior=missing,original_145_unproven_unchanged=True,source_receipt_missing=True,anonymous_synthesis_only_residual_not_addressed=True)
(w/'CONTEXT.json').write_text(json.dumps(meta,indent=1)+'\n')
if missing:raise SystemExit('exact retained prior cannot be restored; refuse a changed context')
F.noreset_classify(L)
p='ff:u_dut.u_bound.u_core.u_gi.g_wtn.u_wtn.u_ctl.part';keys=[p+'['+str(i)+']' for i in range(2)];gkeys=[p+'#t['+str(i)+']' for i in range(3)]
base={k:L.rst_val.get(('gold',k)) for k in keys};gb={k:L.rst_val.get(('gate',k)) for k in gkeys};(w/'BASE.json').write_text(json.dumps(dict(gold=base,gate=gb,used_reset_cycles=64),indent=1)+'\n')
assert [base[k][0] for k in keys]==[0,0]
assert sorted(gb[k][0] for k in gkeys)==[0,0,1]
anchor=next(i for i,k in enumerate(gkeys) if gb[k][0]==1);others=[i for i in range(3) if i!=anchor];results=[]
for j,perm in enumerate(itertools.permutations(others)):
 codebook={0:anchor,1:perm[0],2:perm[1]};L.hyp=dict(prior)
 for code,bit in codebook.items():L.hyp['gate',gkeys[bit]]=('cube','gold',keys,[(code>>i)&1 for i in range(2)])
 L.cons=[('gold',keys,[[0,0],[1,0],[0,1]])]
 m,_=L.build(with_compare=False,with_hyp=True)
 keep=[i for i,n in enumerate(m.onames) if n.startswith('cons:') or (n.startswith('hyp:gate:') and p+'#t[' in n)]
 m.outs=[m.outs[i] for i in keep];m.onames=[m.onames[i] for i in keep];assert len(m.outs)==4
 st=F.prove(m,w,1000,logs,tag='perm'+str(j),single_cap=1000);results.append(dict(codebook=codebook,statuses=st))
 (w/'RESULT.json').write_text(json.dumps(dict(meta,results=results,elapsed_s=time.time()-t),indent=1)+'\n');(w/'LEMMA.log').write_text('\n'.join(logs));print(j,codebook,st,flush=True)
