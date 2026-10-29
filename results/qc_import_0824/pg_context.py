import json,shutil
from pathlib import Path
Q=Path('/srv/opentallas-scratch2/claude');R=Q/'codex-qc-import-0824';o=R/'pg_b190';o.mkdir(exist_ok=True)
f=json.load(open(R/'fullpg/access_plan.json'))['failed'];assert len(f)==1;f=f[0];D=1000;x0,y0,x1,y1=f['rail'];roi=[x0-80000,y0-3000,x1+80000,y1+3000]
def hit(r):return r[0]<roi[2] and roi[0]<r[2] and r[1]<roi[3] and roi[1]<r[3]
g=json.load(open(R/'readback/geometry.json'))
for key,skip in [('obstructions',2),('signal_shapes',3),('existing_supplies',2)]:g[key]=[q for q in g[key] if hit(q[skip:])]
g['cells']=[];json.dump(g,open(o/'geometry.json','w'),separators=(',',':'))
t=json.load(open(R/'readback/power_terms.json'));t['terms']=[q for q in t['terms'] if q['inst'] in f['members'] and q['pin']==f['net']];assert len(t['terms'])==4;json.dump(t,open(o/'power_terms.json','w'),separators=(',',':'))
e=json.load(open(R/'readback/endpoints.json'));e['endpoints']={n:q for n,q in e['endpoints'].items() if hit([round(v*D) for v in q['rect_um']])};json.dump(e,open(o/'endpoints.json','w'),separators=(',',':'))
for name in ['pg_rects.json','probe_census.json']:shutil.copyfile(R/'readback'/name,o/name)
def select(path):return [q for q in json.load(open(path)) if hit([round(v*D) for v in q[2:]])]
json.dump(select(R/'clock_seed.json'),open(o/'clock_seed.json','w'),separators=(',',':'));joint=select(R/'clock_landing_reserved.json')
p=Q/'codex-qc-provider-clock-0834/lower_escape_reserved.json'
if p.exists():joint+=select(p)
json.dump(joint,open(o/'joint_clock_reserved.json','w'),separators=(',',':'));pw=select(R/'fullpg/reserved_access.json')+select(R/'nativepg/bridges/reserved_bridges.json');json.dump(pw,open(o/'reserved_power.json','w'),separators=(',',':'));json.dump(dict(scope='Exact geometry context containing all possible local access/3nearest stripe bridge candidates; not whole-die geometry',roi_dbu=roi,failed=f,clock_reserved=len(joint),power_reserved=len(pw)),open(o/'context.json','w'),indent=2);print('context',len(g['signal_shapes']),len(g['obstructions']),len(joint),len(pw),flush=True)
