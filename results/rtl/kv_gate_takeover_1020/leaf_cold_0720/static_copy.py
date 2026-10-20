import odb,json,sys,re,gzip,hashlib,collections
from pathlib import Path
pre,post,out=map(Path,sys.argv[1:]);out.mkdir(exist_ok=True)
def blocks(s,k):
 for m in re.finditer(r'\b'+k+r'\s*\(([^)]*)\)\s*\{',s):
  a=i=m.end();d=1
  while d:d+=(s[i]=='{')-(s[i]=='}');i+=1
  yield m[1].strip('" '),s[a:i-1]
roles={};libs=[]
for p in Path('/OpenROAD-flow-scripts/flow/platforms/asap7').rglob('*RVT_TT*.lib*'):
 t=gzip.open(p,'rt').read() if p.suffix=='.gz' else p.read_text();libs.append({'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
 for mn,body in blocks(t,'cell'):
  pins={};seq=[]
  for pn,b in blocks(body,'pin'):
   dr=re.search(r'\bdirection\s*:\s*(\w+)',b);fn=re.search(r'\bfunction\s*:\s*"([^"]+)"',b);pins[pn]={'direction':dr[1] if dr else None,'function':fn[1] if fn else None,'clock':bool(re.search(r'\bclock\s*:\s*true',b))}
  for kind in ['ff','latch']:
   for state,bb in blocks(body,kind):
    q={'kind':kind,'state_variables':state}
    for key in ['clocked_on','next_state','clear','preset','clear_preset_var1','clear_preset_var2']:
     m=re.search(r'\b'+key+r'\s*:\s*"?([^;"\n]+)"?\s*;',bb);q[key]=m[1].strip() if m else None
    seq.append(q)
  ip=[k for k,v in pins.items() if v['direction']=='input'];op=[k for k,v in pins.items() if v['direction']=='output'];unary=None
  if len(ip)==len(op)==1 and pins[op[0]]['function'] is not None:
   f=re.sub(r'[()\s]','',pins[op[0]]['function'])
   if f in [ip[0],'!'+ip[0],ip[0]+"'"]:unary={'input':ip[0],'output':op[0],'invert':int(f!=ip[0])}
  roles[mn]={'pins':pins,'seq':seq,'unary':unary}
db0=odb.dbDatabase.create();odb.read_db(db0,str(pre));b0=db0.getChip().getBlock();baseline={i.getName():i.getMaster().getName() for i in b0.getInsts() if roles.get(i.getMaster().getName(),{}).get('seq')}
db=odb.dbDatabase.create();odb.read_db(db,str(post));b=db.getChip().getBlock();parents={};phases={}
def find(x):
 if x not in parents:parents[x]=x;phases[x]=0
 if parents[x]!=x:
  root,p=find(parents[x]);phases[x]^=p;parents[x]=root
 return parents[x],phases[x]
def union(a,z,inv):
 ra,pa=find(a);rz,pz=find(z)
 if ra==rz:
  if pa^pz!=inv:raise RuntimeError('contradictory exact unary relation')
 else:parents[ra]=rz;phases[ra]=pa^pz^inv
C='literal_zero';find(C)
for i in b.getInsts():
 role=roles.get(i.getMaster().getName(),{});unary=role.get('unary')
 if unary:
  a=i.findITerm(unary['input']);z=i.findITerm(unary['output'])
  if a and z and a.getNet() and z.getNet():union(z.getNet().getId(),a.getNet().getId(),unary['invert'])
 for p in i.getITerms():
  fn=role.get('pins',{}).get(p.getMTerm().getName(),{}).get('function')
  if p.getNet() and str(p.getIoType())=='OUTPUT' and fn and re.sub(r'[()\s]','',fn) in ['0','1']:
   union(p.getNet().getId(),C,int(re.sub(r'[()\s]','',fn)))
errors=[];records=[]
def val(n):
 if n is None:return None
 root,phase=find(n.getId());cr,cp=find(C);return {'root':root,'phase':phase,'literal':phase^cp if root==cr else None}
ckport=b.findBTerm('ck');ckref=val(ckport.getNet()) if ckport else None
for i in b.getInsts():
 mn=i.getMaster().getName();role=roles.get(mn,{})
 if not role.get('seq'):continue
 if len(role['seq'])!=1 or role['seq'][0]['kind']!='ff':errors.append('unsupported_sequential:'+mn);continue
 seq=role['seq'][0];ns=seq['next_state'] or '';inames={k for k,v in role['pins'].items() if v['direction']=='input'};refs=set(re.findall(r'[A-Za-z_][A-Za-z0-9_]*',ns))
 if not refs<=inames:errors.append('state_dependent_next_state:'+mn+':'+ns)
 edge=re.sub(r'[()\s]','',seq['clocked_on'] or '');inv=int(edge.startswith('!') or edge.endswith("'"));cpn=edge.strip("!'")
 if cpn not in inames:errors.append('unsupported_clock_expression:'+mn+':'+edge);continue
 ci=i.findITerm(cpn);cv=val(ci.getNet()) if ci else None
 if cv is None:errors.append('missing_clock:'+i.getName());continue
 cv={'root':cv['root'],'phase':cv['phase']^inv}
 if ckref is None or cv!={'root':ckref['root'],'phase':ckref['phase']}:errors.append('not_same_positive_ck_phase:'+i.getName())
 ins={}
 for pn,pmeta in role['pins'].items():
  if pmeta['direction']!='input':continue
  p=i.findITerm(pn);v=val(p.getNet()) if p else None
  if v is None:errors.append('missing_sequential_input:'+i.getName()+'/'+pn)
  ins[pn]=v
 records.append({'instance':i.getName(),'master':mn,'baseline_retained':i.getName() in baseline,'master_same_as_baseline':baseline.get(i.getName())==mn if i.getName() in baseline else None,'actual_liberty_pins':role['pins'],'actual_liberty_sequential':seq,'all_input_canonical_nets':ins,'clock_edge_signal':cv,'native_reset_set_literals':{k:v for k,v in ins.items() if k in ['SETN','RESETN']}})
def signature(r):return json.dumps([r['master'],r['actual_liberty_sequential'],r['actual_liberty_pins'],r['all_input_canonical_nets'],r['clock_edge_signal']],sort_keys=True)
kept=collections.defaultdict(list)
for r in records:
 if r['baseline_retained']:kept[signature(r)].append(r['instance'])
new=[];unmatched=[]
for r in records:
 if not r['baseline_retained']:
  row=r|{'retained_exact_signature_matches':kept.get(signature(r),[])};new.append(row)
  if not row['retained_exact_signature_matches']:unmatched.append(r['instance'])
missing=sorted(set(baseline)-{r['instance'] for r in records});changed=[r['instance'] for r in records if r['master_same_as_baseline'] is False]
status='PASS' if not(errors or unmatched or missing or changed) else 'FAIL'
s={'status':status,'scope':'READONLY actualsynth→final FFbirth/copy classification. Equivalence class requires SAME actualLibmaster/pinfunctions/seqedge/nextstate(clear,set) and EVERY actualinput net canonicalized ONLY through actualLib-defined unary functions/literal0/1. Clockmustbe samepositiveactualckportphase. Combinationalstatefree D means matched independentinitialFFs converge AFTER provedcommonclockevent under compatibleasyncset/reset; never preconvergence. No sourceinit/sharedstate assumptions, no ODB/canonicalview mutations. Rawprebootvalidunconstrained; firstvalidrequires sourcecommonfreshreset/firstusematurity proof.','pre_odb_sha256':hashlib.sha256(pre.read_bytes()).hexdigest(),'post_odb_sha256':hashlib.sha256(post.read_bytes()).hexdigest(),'baseline_FF':len(baseline),'final_FF':len(records),'new_FF':len(new),'unmatched_new':unmatched,'missing_baseline':missing,'changed_baseline_master':changed,'errors':sorted(set(errors)),'liberty':libs,'all_actual_master_equations':{mn:roles[mn] for mn in {r['master'] for r in records}},'positive_clock_reference':ckref}
(out/'summary.json').write_text(json.dumps(s,indent=2)+'\n')
with gzip.open(out/'all_FF.json.gz','wt') as f:json.dump(records,f)
with gzip.open(out/'new_FF_matches.json.gz','wt') as f:json.dump(new,f)
print(json.dumps({k:v for k,v in s.items() if k in ['status','baseline_FF','final_FF','new_FF','unmatched_new','missing_baseline','changed_baseline_master','errors']}))
if status!='PASS':raise RuntimeError('actual static FFcopy proof refused')
