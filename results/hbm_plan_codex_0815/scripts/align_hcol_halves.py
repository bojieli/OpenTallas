"""Equal source input ABI must have equal per-bit physical input order for shared zero-cycle fanout."""
import json,pathlib,sys,hashlib
pd=pathlib.Path(sys.argv[1]);d=json.load(open(pd/'die_plan.json'));files={}
for t in d['partition_types'].values():
 for c in t.get('hard_cores',[]):
  if c.get('module') in ('ot_hbm_idx_score_hcol_h0','ot_hbm_idx_score_hcol_h1'):files.setdefault(c['module'],set()).add(c['pins_file'])
assert all(len(v)==1 for v in files.values()),files
pf0=pd/next(iter(files['ot_hbm_idx_score_hcol_h0']));pf1=pd/next(iter(files['ot_hbm_idx_score_hcol_h1']));a=json.load(open(pf0));b=json.load(open(pf1));aa=a.get('pins',a) if isinstance(a,dict) else a;bb=b.get('pins',b) if isinstance(b,dict) else b
name=lambda p:p.get('name') or f"{p['bus']}[{p.get('bit',0)}]"
N0={name(p):p for p in aa if abs(p['y']-187.488)<2};N1={name(p):p for p in bb if abs(p['y']-187.488)<2};assert len(N0)==1179 and set(N0)==set(N1)
oldsha=hashlib.sha256(pf1.read_bytes()).hexdigest();changed=[]
for n,p in N1.items():
 q=N0[n]
 if (p['x'],p['y'],p['layer'])!=(q['x'],q['y'],q['layer']):changed.append(dict(pin=n,old=[p['x'],p['y'],p['layer']],new=[q['x'],q['y'],q['layer']]))
 p.update(x=q['x'],y=q['y'],layer=q['layer'])
pf1.write_text(json.dumps(b,indent=1)+'\n');newsha=hashlib.sha256(pf1.read_bytes()).hexdigest();report=dict(scope='pin geometry only; same exact native source input ABI and cycle count',input_pins=1179,moved=len(changed),h0_sha256=hashlib.sha256(pf0.read_bytes()).hexdigest(),h1_before_sha256=oldsha,h1_after_sha256=newsha,pin_window_multiset='identical to H0 already measured5.9pins/um',failed_previous_candidate='C9 independent HALF input ordering; native quarter per-bit reach18176failures, worst~482um',changes=changed)
(pd/'hcol_input_order_report.json').write_text(json.dumps(report,indent=1)+'\n');print('aligned inputs',len(N0),'moved',len(changed),'h1sha',newsha)
