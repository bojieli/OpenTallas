import pathlib,json,hashlib,importlib.util,os,time
w=pathlib.Path('/out');r=w/'subject/lec';old=json.load(open(r/'lec.json'));os.environ['OT_LEC_RESET_CYCLES']=str(old['reset_contract']['used']);t=time.time();logs=[]
os.environ['OT_LEC_COMMON_SHAPE']='0';os.environ['OT_LEC_SUPERSET_VEC']='0'
s=importlib.util.spec_from_file_location('F',str(w/'lec.py'));F=importlib.util.module_from_spec(s);s.loader.exec_module(F)
L=F.Lec(F.read_aig(r/'gold.aig'),F.read_map(r/'gold.map'),F.read_aig(r/'gate.aig'),F.read_map(r/'gate.map'));L.kit_reset_ports=old['kit_reset_ports']
F.normalize_gold_elements(L,F.slang_elements(r/'gold.aliases.json'),logs);F.json_alias_keys(L,logs,work=r);F.slang_element_keys(L,logs,work=r);F.alias_arrays(L,logs,work=r)
# Replay accepted label bijections from the ORIGINAL run, never rediscover a layout.
import re
layout=[]
for line in (r/'lec.log').read_text(errors='replace').splitlines():
 hit=re.fullmatch(r'relayout: (.+) \(outer index reversed on the gate side\)',line)
 if hit:
  b=hit[1];ks=[k for k in L.matched if F.IDX.match(k) and F.IDX.match(k).group(1)==b];assert ks,('missing relayout base',b)
  ix={k:tuple(map(int,re.findall(r'\d+',F.IDX.match(k).group(2)))) for k in ks};hi=max(v[0] for v in ix.values());rev={k:b+''.join('['+str(x)+']' for x in (hi-v[0],)+v[1:]) for k,v in ix.items()};assert set(rev.values())==set(ks)
  op={k:L.tp[k] for k in ks};oc={k:L.tc[k] for k in ks if k in L.tc}
  for k in ks:
   L.tp[k]=op[rev[k]]
   if rev[k] in oc:L.tc[k]=oc[rev[k]]
  layout.append(dict(kind='relayout',base=b,count=len(ks)))
 hit=re.match(r'renamed: (.+) \(',line)
 if hit:
  b=hit[1];ks=[k for k in L.matched if F.IDX.match(k) and F.IDX.match(k).group(1)==b];assert ks,('missing renamed base',b)
  for k in ks:
   nk=b+'#t'+k[len(b):];assert nk not in L.tp;L.tp[nk]=L.tp.pop(k)
   if k in L.tc:L.tc[nk]=L.tc.pop(k)
  L.matched=sorted(set(L.gp)&set(L.tp));L.gonly=sorted(set(L.gp)-set(L.tp));L.tonly=sorted(set(L.tp)-set(L.gp));layout.append(dict(kind='renamed',base=b,count=len(ks)))
(w/'EXACT_LAYOUT_REPLAY.json').write_text(json.dumps(dict(original_log_sha256=hashlib.sha256((r/'lec.log').read_bytes()).hexdigest(),operations=layout),indent=1)+'\n')
assert len(L.matched)==old['keypoints']['matched'], ('original matched context differs',len(L.matched),old['keypoints']['matched'])
prior={(sd,k):tuple(h) for sd,k,h in json.load(open(r/'hyp.json'))};missing=[]
for (sd,k),h in prior.items():
 if k not in (L.gp if sd in ('gold','both') else L.tp):missing.append([sd,k,'key'])
 if h[0]=='eq' and h[2] not in (L.gp if h[1]=='gold' else L.tp):missing.append([sd,k,'partner',h[2]])
meta=dict(classification='UNTRUSTED_BOUNDED_BASE_STEP_ONLY',original_verdict_unchanged=True,original_keep=old['kept_registers'],reset_contract=old['reset_contract'],prior_count=len(prior),matched_original=old['keypoints']['matched'],matched_replay=len(L.matched),common_shape_enabled=False,prior_sha256=hashlib.sha256((r/'hyp.json').read_bytes()).hexdigest(),missing_prior=missing,no_comparepoint_or_full_proof=True)
(w/'CONTEXT.json').write_text(json.dumps(meta,indent=1)+'\n')
if missing:raise SystemExit('cannot restore exact retained prior; no weaker-context relabel')
F.noreset_classify(L)
def rv(sd,k):
 p=L.gp if sd=='gold' else L.tp;lit=p[k];st=L._rst_state[sd]
 return (st[lit>>1]^(lit&1) if (lit>>1) in st else None),lit

def base(sd,k,h):
 sides=['gold','gate'] if sd=='both' else [sd];checks=[]
 for side in sides:
  v,lit=rv(side,k)
  if h[0]=='eq':
   other,olit=rv(h[1],h[2]);identity=side==h[1] and lit==(olit^h[3]);covered=identity or (v is not None and other is not None and v==(other^h[3]));checks.append(dict(side=side,target=v,source=other,native_same_literal=identity,covered=covered,status='PASS' if covered else 'UNKNOWN' if v is None or other is None else 'FAIL'))
  elif h[0]=='cube':
   vals=[rv(h[1],x)[0] for x in h[2]];pred=0 if any(a is not None and a!=b for a,b in zip(vals,h[3])) else 1 if all(a is not None for a in vals) else None;covered=v is not None and pred is not None and v==pred;checks.append(dict(side=side,target=v,source=vals,predicate=pred,covered=covered,status='PASS' if covered else 'UNKNOWN' if v is None or pred is None else 'FAIL'))
 return dict(side=sd,key=k,hint=h,checks=checks)

collect=json.load(open(w/'UNTRUSTED_collective_hints.json'));ld=json.load(open(w/'UNTRUSTED_ld_relations.json'));missing_keep=set(old['kept_registers']['missing']['first'])
keep=[h for h in collect if h[0]!='cons' and h[2][0]=='eq' and h[2][2] in missing_keep];assert len(keep)==4
hunt=[h for h in collect if h[0]=='cons' or h[2][0]=='cube'];assert len(hunt)==8
results=[]
for name,hints in [('keep_and_hunt',keep+hunt),('ld16',ld)]:
 L.hyp=dict(prior);L.cons=[]
 rec=F.apply_hints(L,hints,w,1000,logs,propose_only=True)
 added={k:h for k,h in L.hyp.items() if prior.get(k)!=h};bc=[base(sd,k,h) for (sd,k),h in added.items()];cb=[F.cons_base_check(L,sd,ks,a) for sd,ks,a in L.cons]
 m,_=L.build(with_compare=False,with_hyp=True);names={'hyp:'+sd+':'+k for sd,k in added};names|={'hyp:bothg:'+k for sd,k in added if sd=='both'};names|={'cons:'+sd+':'+ks[0] for sd,ks,a in L.cons};idx=[i for i,n in enumerate(m.onames) if n in names];m.outs=[m.outs[i] for i in idx];m.onames=[m.onames[i] for i in idx]
 st=F.prove(m,w,1000,logs,tag=name,single_cap=1000)
 results.append(dict(case=name,given=len(hints),applied=rec['applied'],skipped=rec['skipped'],base=bc,constraint_bases=cb,statuses=st,joint_step_complete=bool(st) and all(x=='proved' for x in st.values()),native_base_complete=all(all(x['covered'] for x in a['checks']) for a in bc) and all(x['covered'] for x in cb)))
 (w/'RESULT.json').write_text(json.dumps(dict(meta,results=results,elapsed_s=time.time()-t),indent=1)+'\n');(w/'LEMMA.log').write_text('\n'.join(logs));print(name,st,'BASE_COMPLETE',results[-1]['native_base_complete'],flush=True)
