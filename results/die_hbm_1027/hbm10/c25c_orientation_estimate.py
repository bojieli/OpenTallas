"""Read-only shared-master orientation estimate using every connected port, before plan edits.
usage: c25c_orientation_estimate.py PLAN_DIR OUTPUT.json
"""
import collections,inspect,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'tools/die_plan'));import check,schema
D,F=map(Path,sys.argv[1:3]);P=schema.Plan(json.load(open(D/'die_plan.json')),D/'die_plan.json');R=check.Report(True)
s=inspect.getsource(check.check_core_faces);n='                cs = [best[f] for f in faces]';s=s.replace(n,"                audit_rows.append(dict(type=tn,core=ci,module=hc['module'],port=lp,orient=o,dirs=dirs,faces=faces,outline=[cw,ch]))\n"+n);check.audit_rows=[];exec(s,check.__dict__);check.check_core_faces(P,R,D,max_msgs=999)
by=collections.defaultdict(list)
for q in check.audit_rows:by[q['type'],q['core']].append(q)
rows=[]
for (tn,ci),ports in by.items():
 if tn not in ('q_hub_nw','q_hub_ne'):continue
 old=ports[0]['orient'];opts=[]
 for orient in ('R0','MX','MY','R180'):
  bad=[];wire=0;np=0
  for q in ports:
   vals=[]
   for face in q['faces']:
    # Current orientation is self-inverse for all supported mirrors.
    nx,ny=check._NORMAL[face]
    if old in ('MY','R180'):nx=-nx
    if old in ('MX','R180'):ny=-ny
    if orient in ('MY','R180'):nx=-nx
    if orient in ('MX','R180'):ny=-ny
    vals.append(max(nx*ux+ny*uy for _,ux,uy in q['dirs']))
   mean=sum(vals)/len(vals)
   if mean<check.FACE_AWAY_COS:bad.append({'port':q['port'],'pins':len(vals),'mean_cos':round(mean,4)})
   wire+=sum(vals);np+=len(vals)
  opts.append({'orient':orient,'bad_groups':len(bad),'bad_pins':sum(q['pins'] for q in bad),'mean_cos':round(wire/np,4),'failures':bad})
 cur=next(q for q in opts if q['orient']==old);best=min(opts,key=lambda q:(q['bad_groups'],q['bad_pins'],-q['mean_cos'],q['orient']!=old))
 if cur['bad_groups'] or best['orient']!=old:rows.append({'type':tn,'core':ci,'module':ports[0]['module'],'old':old,'current_bad':cur['bad_groups'],'best':best,'options':opts})
F.write_text(json.dumps({'status':'ESTIMATE ONLY; pin-lattice, station reach, clock coordinates and macro dataflow review required before adoption','current_bad':sum(q['current_bad'] for q in rows),'best_bad':sum(q['best']['bad_groups'] for q in rows),'cores_changed':sum(q['best']['orient']!=q['old'] for q in rows),'rows':rows},indent=1)+'\n')
print(json.dumps({'current_bad':sum(q['current_bad'] for q in rows),'best_bad':sum(q['best']['bad_groups'] for q in rows),'cores_changed':sum(q['best']['orient']!=q['old'] for q in rows)},indent=1))
