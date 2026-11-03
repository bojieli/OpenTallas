from pathlib import Path
import sys,json
sys.path.insert(0,'/home/ubuntu/OpenTallas/tools/autopilot');import geom_rules as g
P=Path(__file__).parent;D=g.Design('/srv/opentallas-scratch/claude/codex-hroot-ff-place-2338/geom.tsv');names={c[6]:k for k,c in D.cells.items()};bad=json.load(open('/srv/opentallas-scratch/claude/codex-hroot-ff-place-2338/all19_final_comparison.json'))
def upstream(cap):
 q=[cap];seen=set();seq=set();ports=set()
 while q:
  x=q.pop()
  for ni,ck in D.cell_in.get(x,[]):
   if ck:continue
   d=D.nets[ni][1];ds=[]
   if ni in D.multi_drv:ds=[('i',k,False)for k in D.multi_drv[ni]]
   elif d:ds=[d]
   for dr in ds:
    if dr[0]=='p':ports.add(D.pin_by_k[dr[1]]['name']);continue
    k=dr[1];c=D.cells[k]
    if c[0]=='S':seq.add(k)
    elif k not in seen:seen.add(k);q.append(k)
 return seq,ports
rows=[]
for z in bad:
 cap=names[z['capture']];seq,ports=upstream(cap);pts=[(k,*g.ctr(D.cells[k]))for k in seq];us=[(x+y,k)for k,x,y in pts];vs=[(x-y,k)for k,x,y in pts];umin,umax=min(us),max(us);vmin,vmax=min(vs),max(vs);rad=max(umax[0]-umin[0],vmax[0]-vmin[0])/2;uv=[umax[0]-405,umin[0]+405,vmax[0]-405,vmin[0]+405]
 rows.append({'capture':z['capture'],'old_worst':z['launch'],'old_distance':z['distance_um'],'class':z['class'],'actual_upstream_flops':len(seq),'direct_upstream_ports':sorted(ports),'best_free_capture_radius_um':round(rad,3),'capture_alone_405_feasible':uv[0]<=uv[1]and uv[2]<=uv[3],'feasible_uv':uv,'limiting_endpoints':[D.cells[k][6]for _,k in [umin,umax,vmin,vmax]],'contains_reset101':any('u_rrl_101/'in D.cells[k][6]for k in seq)})
(P/'all19_capture_feasibility.json').write_text(json.dumps(rows,indent=1)+'\n')
for r in rows:print(round(r['best_free_capture_radius_um'],2),r['capture_alone_405_feasible'],r['contains_reset101'],r['capture'])
