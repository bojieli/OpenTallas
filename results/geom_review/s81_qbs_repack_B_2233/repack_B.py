from pathlib import Path
import json,sys,re,math,hashlib
sys.path.insert(0,'/home/ubuntu/OpenTallas/tools/autopilot');import geom_rules as G
from exact_cones import endpoints,physical_port_map
P=Path(sys.argv[1]) if len(sys.argv)>1 else Path('/home/ubuntu/coord/tmp/codex-hist-anchor-2100');C=json.load(open(P/'complete.json'));D=G.Design(P/'geom.tsv');fixed={x['cid']for x in C['fixed']};delta=66.96;changes=[]
for nm,m in C['macros'].items():
 n=nm.replace('\\','')
 hc=bool(re.search(r'u_q\.u_s\.u_hc\.g_bank\[[0-7]\]\.u_bank$',n));ofq=bool(re.search(r'u_q\.u_s\.u_ofq\.g_bank\[[0-3]\]\.u_m$',n));fq=bool(re.search(r'u_q\.u_s\.u_fq\.g_bank\[[0-3]\]\.u_m$',n))
 if not(hc or ofq or fq):continue
 dy=-32.4 if fq else delta
 old=list(m['bbox_um']);m['bbox_um']=[old[0],round(old[1]+dy,6),old[2],round(old[3]+dy,6)]
 for p in m['ports']:p['xy'][1]=round(p['xy'][1]+dy,6)
 for f in C['fixed']:
  if f['cid']==m['cid']:f['bbox_um']=list(m['bbox_um'])
 c=D.cells[m['cid']];D.cells[m['cid']]=(c[0],c[1],c[2],c[3]+dy,c[4],c[5]+dy,c[6])
 changes.append(dict(name=nm,cid=m['cid'],master=m['master'],orient=m['orient'],old_bbox_um=old,new_bbox_um=m['bbox_um'],delta_um=[0,dy]))
assert len(changes)==16
# Functional pin/clock/reset ABI and all source nets remain the same. Rows/taps/PG must be regenerated in a future build.
C['proposal']=dict(enabled=False,kind='INTERNAL_MACRO_REPACK_ZERO_CYCLE',added_ff=0,added_cycles=0,canonical_adoption=False,rows_taps_PG='REGEN_REQUIRED; original row holes retained only as conservative model capacity, original locked taps historical',changes=changes)
ports=physical_port_map(C);bad=[];bounds=[];nmacro=0;fxff={i for i in fixed if i in D.cells and D.kind(i)=='S'}
for cid,c in D.cells.items():
 if c[0]!='S'or cid in fxff:continue
 ins,mi=endpoints(D,cid,False);outs,mo=endpoints(D,cid,True);pts=[(*G.ctr(D.cells[x]),'FF:'+D.cells[x][6])for x in(ins|outs)&fxff]
 for mk in mi|mo:
  assert mk in ports;pts+=ports[mk]
 if mi or mo:nmacro+=1
 if not pts:continue
 u=sorted(pts,key=lambda z:z[0]+z[1]);v=sorted(pts,key=lambda z:z[0]-z[1]);du=u[-1][0]+u[-1][1]-u[0][0]-u[0][1];dv=v[-1][0]-v[-1][1]-v[0][0]+v[0][1];rr=max(du,dv)/2;w=[u[0],u[-1]]if du>=dv else[v[0],v[-1]]
 rec=dict(name=c[6],cid=cid,radius_um=round(rr,4),witness=w)
 bounds.append(rec)
 if rr>405+1e-6:bad.append(rec)
# All macro bounding boxes/4.32um halos, fixed top face pin boxes, and root-to-macro clock distances are checked geometrically.
mac=list(C['macros'].items());over=[];mind=None
for i,(na,a)in enumerate(mac):
 x0,y0,x1,y1=a['bbox_um'];assert x0>=4.32 and y0>=4.32 and x1<=643.68 and y1<=643.68
 for nb,b in mac[i+1:]:
  X0,Y0,X1,Y1=b['bbox_um'];dx=max(X0-x1,x0-X1,0);dy=max(Y0-y1,y0-Y1,0)
  if dx<8.64-1e-6 and dy<8.64-1e-6:over.append([na,nb,dx,dy])
  dist=max(dx,dy)if dx==0 or dy==0 else None
  if dist is not None:mind=dist if mind is None else min(mind,dist)
ck=C['controlpins'][0]['boxes'][0]['bbox_um'];clockroot=[(ck[0]+ck[2])/2,(ck[1]+ck[3])/2];clock=[]
orig=json.load(open(P/'complete.json'));om={n:m for n,m in orig['macros'].items()}
for nm,m in C['macros'].items():
 for p in m['ports']:
  if p['sig']=='CLOCK':
   op=next(q for q in om[nm]['ports']if q['port']==p['port']);d=lambda xy:abs(xy[0]-clockroot[0])+abs(xy[1]-clockroot[1]);clock.append(dict(macro=nm,pin=p['port'],before_um=round(d(op['xy']),4),after_um=round(d(p['xy']),4)))
summary=dict(status='DISABLED_MODEL_ONLY',moved_macros=len(changes),native_net_graph_unchanged=True,fixed_face_ffs_preserved=len(fxff),all_movable_ffs=sum(c[0]=='S'for c in D.cells.values())-len(fxff),fixed_endpoint_bounds=len(bounds),direct_macro_ff_count=nmacro,infeasible_count=len(bad),worst_radius_um=max(r['radius_um']for r in bounds),macro_halo_overlap=over,min_parallel_macro_gap_um=round(mind,4),clock_root_um=clockroot,clock_root_macro_before_max_um=max(x['before_um']for x in clock),clock_root_macro_after_max_um=max(x['after_um']for x in clock),clock_target='UNCHANGED TT250/FF202.5ps insertion,833ps core; not measured or signed',physical_rebuild='Rows/taps/PG/CTS regenerate normally; no old-PG/clock pass transferred',new_rtl_or_ff_or_cycles=False)
(P/'repack_B_complete.json').write_text(json.dumps(C)+'\n');(P/'repack_B_bounds.json').write_text(json.dumps(dict(summary=summary,infeasible=sorted(bad,key=lambda r:-r['radius_um']),worst=sorted(bounds,key=lambda r:-r['radius_um'])[:40],clock=clock),indent=1)+'\n');(P/'repack_B_layout.json').write_text(json.dumps(C['proposal'],indent=1)+'\n');print(json.dumps(summary,indent=2))
for r in sorted(bad,key=lambda r:-r['radius_um'])[:10]:print(r)
