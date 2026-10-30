"""Native row/site body placement for the diagnostic START clock, without changing topology."""
import json,re,sys,shutil
from pathlib import Path
repo,source,planpath,lef,out=map(Path,sys.argv[1:])
sys.path[:0]=[str(repo/'tools/die_plan'),str(repo/'tools/s81_head')]
import schema,die_trial,start_stage_emit
from head_start_pack import lef_sizes
from head_start_sites import Bodies,row_orientation
plan=schema.Plan(json.load(open(planpath)),planpath);site=die_trial.SiteMap(plan)
sizes=lef_sizes(lef.read_text());text=(source/'ctree.tcl').read_text()
cells,homes=start_stage_emit.ctree_cells((source/'ctree.v').read_text(),text)
occupied=Bodies();placed={};moves=[]
def legal_body(x,y,w,h):
    return all(site.in_part((xx,yy),0) for xx in (x,x+w) for yy in (y,y+h)) and not any(min(x+w,c)-max(x,a)>1e-6 and min(y+h,d)-max(y,b)>1e-6 for a,b,c,d,*_ in site.forb)
for name,(master,*_) in sorted(cells.items()):
    ox,oy=homes[name];w,h=sizes[master]
    assert h<=.270001,(name,master,h)
    candidates=[]
    for iy in range(-40,41):
        y=round((round(oy/.27)+iy)*.27,3)
        for ix in range(-40,41):
            x=round((round(ox/.054)+ix)*.054,3)
            candidates.append((abs(x-ox)+abs(y-oy),y,x))
    for distance,y,x in sorted(candidates):
        if occupied.free(x,x+w,y) and legal_body(x,y,w,h):break
    else:raise ValueError('No native clock body home for '+name)
    occupied.add(x,x+w,y);placed[name]=(x,y)
    moves.append(dict(name=name,old=[ox,oy],new=[x,y],manhattan_um=distance))
def patch(m):
    name=m[1];x,y=placed[name]
    return f'place_inst -name {name} -location {{{x:.3f} {y:.3f}}} -orientation {row_orientation(y)}'
text=re.sub(r'place_inst -name (\S+) -location \{[-\d.]+ [-\d.]+\}',patch,text)
out.mkdir(parents=True,exist_ok=False)
(out/'ctree.tcl').write_text(text);shutil.copy2(source/'ctree.v',out/'ctree.v')
report=dict(scope='diagnostic geometry-only native clock legalization; arrivals require reroute',cells=len(cells),maximum_move_um=max(r['manhattan_um'] for r in moves),rows=moves,cycles_added=0,topology_changed=False)
(out/'legalize.json').write_text(json.dumps(report,indent=1))
print(json.dumps({k:v for k,v in report.items() if k!='rows'}))
