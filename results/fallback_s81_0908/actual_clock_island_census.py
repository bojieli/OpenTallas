import json,sys,collections
from pathlib import Path
W=Path('/srv/opentallas-scratch2/claude/wt/codex-s81-clock14-0834');sys.path.insert(0,str(W/'tools/die_plan'))
import schema as S,die_clock_mesh as D
O=Path('/srv/opentallas-scratch2/claude/codex-s81-pd14-0818');P=S.Plan(S.load('/srv/opentallas-scratch2/claude/path-s81-pd7-1026/d/src/die_plan_pd7_composed.json'));m=json.load(open(O/'edge405_ioprune/mesh.json'));pl=json.load(open(O/'edge405_ioprune/place.json'));out=[];other=[]
for v in m['clock_hard_keepout_violations']:
 k=v['keepout'];part,inst=k.split('/',1)
 if part not in P.parts:other.append(v);continue
 c=next((c for c in P.ptype(part).get('hard_cores',[]) if c['inst']==inst),None)
 if c is None:other.append(v);continue
 x,y,x1,y1=v['rect_um'];a=D.core_frame(P,part,c,(x,y));b=D.core_frame(P,part,c,(x1,y1));r=[round(min(a[0],b[0]),6),round(min(a[1],b[1]),6),round(max(a[0],b[0]),6),round(max(a[1],b[1]),6)]
 out.append(dict(cell=v['cell'],kind=pl[v['cell']]['kind'],part=part,inst=inst,module=c['module'],core_rect_um=r,die_rect_um=v['rect_um']))
groups={}
for r in out:
 g=groups.setdefault(r['module'],dict(instances=set(),rects=set(),cells=0));g['instances'].add(r['part']+'/'+r['inst']);g['rects'].add(tuple(r['core_rect_um']));g['cells']+=1
summary=[dict(module=k,affected_instances=len(v['instances']),union_sites=len(v['rects']),blocked_cells=v['cells']) for k,v in groups.items()];summary.sort(key=lambda x:x['blocked_cells'],reverse=True)
r=dict(status='REQUEST_CENSUS_NOT_DECLARED_ISLANDS',source_plan_sha256=m['meta']['plan_sha256'] if 'plan_sha256' in m['meta'] else None,actual_hardcore_cell_hits=len(out),other_keepout_hits=len(other),modules=summary,requests=out,other=other)
(O/'edge405_ioprune/actual_island_census.json').write_text(json.dumps(r,indent=1)+'\n');print(json.dumps(dict(actual_hits=len(out),other=len(other),module_count=len(summary),top=summary[:12]),indent=1))
