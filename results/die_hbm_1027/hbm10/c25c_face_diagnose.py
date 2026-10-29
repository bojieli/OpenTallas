"""List every core face failure and compute shared-master feasible pin faces from actual partners.
Uses the existing check_core_faces logic, adding a read-only collector in memory; no gate code edit.
usage: c25c_face_diagnose.py PLAN_DIR OUTPUT_DIR
"""
import collections,hashlib,inspect,json,math,re,sys
from pathlib import Path
TOOLS=Path(__file__).resolve().parents[3]/'tools/die_plan'
sys.path.insert(0,str(TOOLS));import check,schema
D,O=map(Path,sys.argv[1:3]);O.mkdir(parents=True,exist_ok=True)
p=schema.Plan(json.load(open(D/'die_plan.json')),D/'die_plan.json');r=check.Report(True)
source=inspect.getsource(check.check_core_faces)
needle='                cs = [best[f] for f in faces]'
assert needle in source
source=source.replace(needle,"                audit_rows.append(dict(type=tn,core=ci,module=hc['module'],port=lp,orient=o,targets=pts,dirs=dirs,faces=faces,outline=[cw,ch]))\n"+needle)
check.audit_rows=[];exec(source,check.__dict__);summary=check.check_core_faces(p,r,D,max_msgs=999)
failed=[]
for f in r.errors():
 m=re.match(r'type (\S+) core (\S+) port (\S+): (\d+) pins on face (\S+) .*\(re-pin to face (\S+)\)',f['msg'])
 if m:failed.append(dict(zip(('type','core','port','pins','face','requested_face'),m.groups())))
key={(q['type'],q['core'],q['port']) for q in failed};badmaster={(q['module'],q['port']) for q in check.audit_rows if (q['type'],q['core'],q['port']) in key}
by=collections.defaultdict(list)
for q in check.audit_rows:
 if (q['module'],q['port']) in badmaster:by[(q['module'],q['port'])].append(q)
out=[]
for (mod,port),rows in sorted(by.items()):
 fs={}
 for f in 'WENS':
  scores=[]
  for q in rows:
   w,h=q['outline'];xy={'W':(0,h/2),'E':(w,h/2),'N':(w/2,h),'S':(w/2,0)}[f]
   face=check._core_face(q['orient'],*xy,w,h);nx,ny=check._NORMAL[face]
   scores.append(max(nx*ux+ny*uy for _,ux,uy in q['dirs']))
  fs[f]=min(scores)
 best=max(fs,key=fs.get)
 out.append({'module':mod,'port':port,'instances':len(rows),'best_shared_face':best,'best_worst_cos':round(fs[best],4),'all_shared_face_worst_cos':{f:round(v,4) for f,v in fs.items()},'feasible_non_away':[f for f,v in fs.items() if v>=0],'uses':rows})
report={'source_sha256':hashlib.sha256((D/'die_plan.json').read_bytes()).hexdigest(),'summary':summary,'failure_count':len(failed),'failures':failed,'master_port_constraints':out}
(O/'face_diagnosis.json').write_text(json.dumps(report,indent=1)+'\n')
print(json.dumps({'summary':summary,'master_ports':len(out),'safe_shared_repin':sum(bool(q['feasible_non_away']) for q in out),'conflicting_shared_repin':sum(not bool(q['feasible_non_away']) for q in out)},indent=1))
