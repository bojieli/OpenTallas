"""HEAD-R3 11-17 NF15e corridor structure model r4 (pre-route, architectural).
Successor of allocate_memory_tracks_r3.py (inputs unchanged, read-only).  Adds the structural options:
  --relay-t T      hop halving: a dest whose full-rectangle x distance from its source exceeds T gets one relay FF
                   (one more cycle on that edge) at the hop midpoint, ON the trunk track (relay site legality checked).
  --relay-kinds    kinds that take the relay as a whole word class (uniform latency); others never relay.
  --grow G         extra corridor growth on top of the plan (upper cores/anchors with y>=--grow-from shift by G).
  --m8-all         count every M8 track of the band (grant widened) instead of the frozen type grant.
Same 405 um full-anchor-rectangle reach bound, same macro OBS / clock box / M6 PG guard exclusions as r3.
Not a route PASS: vertical branches, vias, pin access unqualified.
"""
from pathlib import Path
import argparse,collections,hashlib,json,math
ap=argparse.ArgumentParser()
for k in ["plan","edges","grant","out"]:ap.add_argument("--"+k,required=True)
ap.add_argument("--band",nargs=2,type=float,default=[490,790.96]);ap.add_argument("--max-reach",type=float,default=405);ap.add_argument("--type",default="hd_lep0N")
ap.add_argument("--relay-t",type=float,default=1e9);ap.add_argument("--relay-kinds",default="");ap.add_argument("--force-kinds",default="");ap.add_argument("--grow",type=float,default=0);ap.add_argument("--grow-from",type=float,default=786.0);ap.add_argument("--m8-all",action="store_true");ap.add_argument("--passes",type=int,default=3)
a=ap.parse_args();R=a.max_reach
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
p=json.loads(Path(a.plan).read_text());tj=p["partition_types"][a.type];es=json.loads(Path(a.edges).read_text())["edges"];grant=json.loads(Path(a.grant).read_text())
G=a.grow;band=[a.band[0],a.band[1]+G]
def sh(r):
 r=tuple(r);return (r[0],r[1]+G,r[2],r[3]+G) if r[1]>=a.grow_from-1e-6 else r
nets={}
for e in es:
 k=(str(e["source_id"]),str(e["source_bit"]))
 n=nets.setdefault(k,dict(key=list(k),src=set(),dests={}))
 n["src"].update(sh(r) for r in e.get("source_rects_um",[e["source_rect_um"]]))
 n["dests"][(str(e["dest_id"]),str(e["dest_bit"]))]=(sh(e["dest_rect_um"]),e.get("kind",""))
macros=[]
for m in tj["hard_cores"]:
 x,y=m["origin_um"];w,h=m["outline_um"]
 if y>=a.grow_from-1e-6:y+=G
 macros.append((x,y,x+w,y+h,int(m.get("obs_max","M7")[1:])))
clock=[sh(c["rect_um"]) for c in tj["clock"].get("reserved_sites_um",[])]
rows=[];bylayer=collections.Counter()
for layer,pitch,off in [(4,.048,.012),(6,.064,.016),(8,float(grant["pitch_um"]),float(grant["offset_um"]))]:
 for k in range(math.ceil((band[0]-off)/pitch),math.floor((band[1]-off)/pitch)+1):
  y=k*pitch+off
  if layer==8 and not a.m8_all and not any(lo<=k<=hi for lo,hi in grant["type_runs"]):continue
  if layer==6 and any(min((y-(1.968+v))%4.32,(1.968+v-y)%4.32)<=.288/2+.096+.064 for v in [0,.288+.096]):continue
  blocked=[]
  if layer<8:
   blocked.extend((x0,x1) for x0,y0,x1,y1,obs in macros if layer<=obs and y0<=y<=y1)
   blocked.extend((x0,x1) for x0,y0,x1,y1 in clock if y0<=y<=y1)
  merged=[]
  for lo,hi in sorted(blocked):
   if merged and lo<=merged[-1][1]+1e-9:merged[-1][1]=max(hi,merged[-1][1])
   else:merged.append([lo,hi])
  rows.append(dict(layer=layer,y_um=y,blocked=merged,ends=[]));bylayer["M"+str(layer)]+=1
HALO=1.0
def site_forbidden(x):  # y intervals where a std cell cannot sit at column x (any hard core / SRAM / clock box)
 return [(y0-HALO,y1+HALO) for x0,y0,x1,y1,_ in macros if x0-HALO<x<x1+HALO]+[(y0,y1) for x0,y0,x1,y1 in clock if x0<x<x1]
def win_rect(r,xfar):  # |y-c| <= R-xfar-h/2
 c=(r[1]+r[3])/2;b=R-xfar-(r[3]-r[1])/2;return (c-b,c+b)
def direct(s,d):
 x=max(abs(s[0]-d[2]),abs(s[2]-d[0]));sc=(s[1]+s[3])/2;dc=(d[1]+d[3])/2
 b=R-x-(s[3]-s[1])/2-(d[3]-d[1])/2;extra=b-abs(sc-dc)
 return (min(sc,dc)-extra/2,max(sc,dc)+extra/2)
import re
def stem(x):
 x=x.replace(chr(92),"");x=re.sub(r"\[\d+\]\$_DFF.*$","",x);x=re.sub(r"\$_DFF.*$","",x);return x
rk=set(k for k in a.relay_kinds.split("|") if k);fk=set(k for k in a.force_kinds.split("|") if k)
items=[];relay_by_kind=collections.Counter();edges_by_kind=collections.Counter();reach_bad=[];relay_ff=0
for k,n in nets.items():
 S=list(n["src"]);sx0=min(s[0] for s in S);sx1=max(s[2] for s in S)
 yl,yh=band;forb=[];rel={"R":[],"L":[]};rects=S+[d for d,_ in n["dests"].values()]
 hops=[]
 for dk,(d,kind) in n["dests"].items():
  edges_by_kind[kind]+=1
  xfar=max(max(abs(s[0]-d[2]),abs(s[2]-d[0])) for s in S)
  if (kind in fk and xfar>60) or (xfar>a.relay_t and (not rk or kind in rk)):
   rel["R" if (d[0]+d[2])/2>=(sx0+sx1)/2 else "L"].append(d);relay_by_kind[kind]+=1;hops.append((kind,stem(k[0]),stem(dk[0])))
  else:
   for s in S:
    z=direct(s,d);yl=max(yl,z[0]);yh=min(yh,z[1])
 nrel=0;rsite=[]
 for side,ds in rel.items():
  if not ds:continue
  nrel+=1
  if side=="R":far=max(d[2] for d in ds);xm0=(sx0+far)/2
  else:far=min(d[0] for d in ds);xm0=(sx1+far)/2
  best=None
  for off in [0,-15,15,-30,30,-45,45,-60,60]:
   xm=xm0+off;wl,wh=yl,yh
   for s in S:
    z=win_rect(s,max(abs(xm-s[0]),abs(xm-s[2])));wl=max(wl,z[0]);wh=min(wh,z[1])
   for d in ds:
    z=win_rect(d,max(abs(d[2]-xm),abs(d[0]-xm)));wl=max(wl,z[0]);wh=min(wh,z[1])
   f=site_forbidden(xm);free=max(0,wh-wl)-sum(max(0,min(wh,b)-max(wl,c)) for c,b in f)
   if best is None or free>best[0]+1e-6:best=(free,xm,wl,wh,f)
   if off==0 and free>=40:break
  _,xm,yl,yh,f=best;forb+=f;rsite.append((side,xm))
 relay_ff+=nrel
 lo=min(r[0] for r in rects);hi=max(r[2] for r in rects)
 if yl>yh+1e-8:reach_bad.append(dict(key=list(k),x_um=[lo,hi],y=[yl,yh]))
 items.append(dict(key=list(k),rects=rects,x0=lo,x1=hi,c0=min((r[0]+r[2])/2 for r in rects),c1=max((r[0]+r[2])/2 for r in rects),ylo=yl,yhi=yh,forb=forb,hops=hops,rsite=rsite))
cuts=[]
for x in range(0,math.ceil(tj["outline_um"][0])+1,10):
 avail=collections.Counter("M"+str(r["layer"]) for r in rows if not any(lo<x<hi for lo,hi in r["blocked"]))
 man=proj=cen=0
 for n in items:
  if n["x0"]<x<n["x1"]:proj+=1
  if n["c0"]<x<n["c1"]:cen+=1
  if any(r[2]<x for r in n["rects"]) and any(r[0]>x for r in n["rects"]):man+=1
 cap=sum(avail.values());cuts.append(dict(x_um=x,capacity_tracks=dict(avail),total=cap,mandatory=man,center_extent=cen,full_rect=proj,f_mand=man/cap,f_center=cen/cap,f_full=proj/cap))
# multi-pass list colouring: each row keeps a sorted list of occupied x intervals
import bisect
def free(r,x0,x1):
 e=r["ends"];i=bisect.bisect_left(e,(x0,))
 if i<len(e) and e[i][0]<x1+1e-6:return False
 if i>0 and e[i-1][1]>x0-1e-6:return False
 return True
rows.sort(key=lambda r:r["y_um"]);ry=[r["y_um"] for r in rows]
def ok(r,n):
 y=r["y_um"]
 if any(c<y<b for c,b in n["forb"]):return False
 if any(n["x0"]<hi-1e-9 and n["x1"]>lo+1e-9 for lo,hi in r["blocked"]):return False
 return free(r,n["x0"],n["x1"])
assigned=[];pending=[n for n in items if n["ylo"]<=n["yhi"]+1e-8]
pending.sort(key=lambda n:(int((n["yhi"]-n["ylo"])//20),n["x0"],-n["x1"]))
un=[]
for n in pending:
 i0=bisect.bisect_left(ry,n["ylo"]-1e-9);i1=bisect.bisect_right(ry,n["yhi"]+1e-9)
 m=bisect.bisect_left(ry,(n["ylo"]+n["yhi"])/2);m=min(max(m,i0),i1-1) if i1>i0 else i0
 ch=None;lo_i=m;hi_i=m+1
 while lo_i>=i0 or hi_i<i1:
  if lo_i>=i0:
   if ok(rows[lo_i],n):ch=lo_i;break
   lo_i-=1
  if hi_i<i1:
   if ok(rows[hi_i],n):ch=hi_i;break
   hi_i+=1
 n["cand"]=range(i1-i0)
 if ch is None:un.append(n)
 else:
  n["y"]=rows[ch]["y_um"];bisect.insort(rows[ch]["ends"],(n["x0"],n["x1"]));assigned.append(dict(key=n["key"],layer="M"+str(rows[ch]["layer"]),y_um=rows[ch]["y_um"],x_um=[n["x0"],n["x1"]]))
for c in cuts:
 x=c["x_um"];u=sum(1 for t in assigned if t["x_um"][0]<x<t["x_um"][1]);c["witness_used"]=u;c["f_witness"]=u/c["total"]
hopagg={}
for n in items:
 if "y" not in n:continue
 for h in set(n["hops"]):
  g=hopagg.setdefault(" | ".join(h),dict(bits=0,xm=[1e9,-1e9],y=[1e9,-1e9]))
  g["bits"]+=1
  for side,xm in n["rsite"]:g["xm"]=[min(g["xm"][0],xm),max(g["xm"][1],xm)]
  g["y"]=[min(g["y"][0],n["y"]),max(g["y"][1],n["y"])]
worst=max(cuts,key=lambda c:c["f_full"]);wm=max(cuts,key=lambda c:c["f_mand"]);wc=max(cuts,key=lambda c:c["f_center"])
unk=collections.Counter()
for n in un:unk[n["key"][0].split("[")[0].split("\\")[0][:40]]+=1
summ=dict(nets=len(items),assigned=len(assigned),unassigned=len(un),reach_bad=len(reach_bad),relay_ff=relay_ff,relay_edges_by_kind=dict(relay_by_kind),edges_by_kind=dict(edges_by_kind),rows=dict(bylayer),band=band,grow=G,relay_t=a.relay_t,m8_all=a.m8_all,
 worst_full_rect=dict(x=worst["x_um"],n=worst["full_rect"],cap=worst["total"],f=round(worst["f_full"],4)),worst_center=dict(x=wc["x_um"],n=wc["center_extent"],cap=wc["total"],f=round(wc["f_center"],4)),worst_mandatory=dict(x=wm["x_um"],n=wm["mandatory"],cap=wm["total"],f=round(wm["f_mand"],4)),worst_witness=round(max(c["f_witness"] for c in cuts),4),unassigned_by_source=dict(unk.most_common(12)))
out=dict(schema="opentallas.memory_track_witness.r4",relay_hops=hopagg,status="HORIZONTAL_WITNESS_COMPLETE" if not un and not reach_bad else "UNRESOLVED",input_sha256={"plan":sha(a.plan),"edges":sha(a.edges),"grant":sha(a.grant)},summary=summ,cuts=cuts,assigned_horizontal_trunks=assigned,unassigned=[dict(key=n["key"],x_um=[n["x0"],n["x1"]],y=[n["ylo"],n["yhi"]],cand=len(n["cand"])) for n in un],reach_infeasible=reach_bad,scope=["pre-route architectural model; vertical branches/vias/pin access unqualified; no route or adoption credit","relay = one extra FF and one extra cycle on that edge, sited on its trunk track at a legal std-cell column"])
Path(a.out).write_text(json.dumps(out,indent=1)+"\n");print(json.dumps(summ))
