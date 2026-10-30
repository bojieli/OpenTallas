"""Place one actual mapped START body beside its existing raw reset source."""
import json,sys,math
from pathlib import Path
r=Path(sys.argv[1]);ph=json.load(open(r/'physical_lc.json'));st=json.load(open('/srv/opentallas-scratch2/claude/die-head-33/start/map/start_stages.json'))
s=next(s for s in st['stages'] if s['id']=='r91_3');src=ph['ports'][s['reset_port']]['xy_um']
names=[n for n,c in ph['cells'].items() if c['stage']=='r91_3' and '.branch_' not in n]
assert names
obstacles=[c['rect_um'] for n,c in ph['cells'].items() if n not in names]+[c['rect_um'] for c in ph['stage_clock_drivers'].values()]
# Clock body homes are unchanged; include them as complete physical obstacles.
sys.path[:0]=['/srv/opentallas-scratch2/claude/wt/codex-head-start-1851/tools/die_plan','/srv/opentallas-scratch2/claude/wt/codex-head-start-1851/tools/s81_head']
import schema,die_trial,start_stage_emit
from head_start_pack import lef_sizes
sizes=lef_sizes(Path('/srv/opentallas-scratch2/claude/head-start-2/in/cells.lef').read_text())
tc,xy=start_stage_emit.ctree_cells((r/'clock/ctree.v').read_text(),(r/'clock/ctree.tcl').read_text())
for n,(m,*_) in tc.items():x,y=xy[n];w,h=sizes[m];obstacles.append([x,y,x+w,y+h])
p=Path('/srv/opentallas-scratch2/claude/die-head-33/start/leaf/capture/plan.json');site=die_trial.SiteMap(schema.Plan(json.load(open(p)),p))
candidates=sorted((abs(dx*.054)+abs(dy*.27),dx*.054,dy*.27) for dx in range(-120,121) for dy in range(-20,21))
def hit(a,b):return min(a[2],b[2])-max(a[0],b[0])>1e-6 and min(a[3],b[3])-max(a[1],b[1])>1e-6
for distance,dx,dy in candidates:
    bodies=[[round(v+(dx if j%2==0 else dy),3) for j,v in enumerate(ph['cells'][n]['rect_um'])] for n in names]
    if any(abs((a[0]+a[2])/2-src[0])+abs((a[1]+a[3])/2-src[1])>404 for a in bodies):continue
    if any(hit(a,b) for a in bodies for b in obstacles):continue
    if any(any(hit(a,b) for b in site.forb) or not all(site.in_part((x,y),0) for x in (a[0],a[2]) for y in (a[1],a[3])) for a in bodies):continue
    break
else:raise ValueError('no complete legal body relocation within search')
for n,b in zip(names,bodies):ph['cells'][n]['rect_um']=b;ph['cells'][n]['xy_um']=b[:2]
(r/'physical_lc_fix.json').write_text(json.dumps(ph,indent=1))
print(json.dumps(dict(stage='r91_3',cells=len(names),dx_um=dx,dy_um=dy,max_reset_reach_um=max(abs((a[0]+a[2])/2-src[0])+abs((a[1]+a[3])/2-src[1]) for a in bodies),logical_cycles_added=0)))
