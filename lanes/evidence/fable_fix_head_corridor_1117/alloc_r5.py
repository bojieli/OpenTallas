"""FABLE-FIX-HEAD-CORRIDOR 11-17: alloc_r4.py (HEAD-R3) + TRUNK-COLUMN ranks + a rip-up repair pass.
Without --columns and with --repair 0 the result is alloc_r4's (same windows, same order, same rows).
  --repair N       passes of the repair step: an unassigned net takes a row whose <= 3 blockers each move to another legal row.
  --columns F      json {tag: rect}: these FF ranks (relay or stage groups, found in the edges by their rect) are BIT-SLICE
                   COLUMNS: the rank is a narrow, tall site column and every FF sits ON its own bit's horizontal trunk (what the
                   hr3 decision model assumed for the hop-halving relays).  For such a rank the trunk must cross the column
                   inside its y span; reach is measured to the FF on the trunk (x distance to the far column edge + the y
                   distance from the other end's rect), not to the corners of a rectangle.  The D net and the Q net of one FF
                   are tied: the Q trunk lies within --jog of the D trunk (the jog is charged to the Q net's reach, counted
                   as a vertical segment inside the column and checked against the column's M5+M7 supply).
  --jog J          largest D-trunk to Q-trunk offset at a column FF (default 8.64 um).
  --cut-step       x step of the cut scan (default 10 as r4; columns are narrow, use 2).
--- alloc_r4 text follows ---
HEAD-R3 11-17 NF15e corridor structure model r4 (pre-route, architectural).
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
ap.add_argument("--relay-t",type=float,default=1e9);ap.add_argument("--relay-kinds",default="");ap.add_argument("--force-kinds",default="");ap.add_argument("--grow",type=float,default=0);ap.add_argument("--grow-from",type=float,default=786.0);ap.add_argument("--m8-all",action="store_true");ap.add_argument("--passes",type=int,default=3);ap.add_argument("--columns",default="");ap.add_argument("--jog",type=float,default=8.64);ap.add_argument("--cut-step",type=float,default=10);ap.add_argument("--repair",type=int,default=4);ap.add_argument("--repair-rows",type=int,default=80)
a=ap.parse_args();R=a.max_reach
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
p=json.loads(Path(a.plan).read_text());tj=p["partition_types"][a.type];es=json.loads(Path(a.edges).read_text())["edges"];grant=json.loads(Path(a.grant).read_text())
G=a.grow;band=[a.band[0],a.band[1]+G]
def sh(r):
 r=tuple(r);return (r[0],r[1]+G,r[2],r[3]+G) if r[1]>=a.grow_from-1e-6 else r
COLS={};J=a.jog
if a.columns:
 for tg,r in json.loads(Path(a.columns).read_text()).items():COLS[tuple(round(v,3) for v in sh(r))]=tg
def col(r):return COLS.get(tuple(round(v,3) for v in r))
destmap={}
nets={}
for e in es:
 k=(str(e["source_id"]),str(e["source_bit"]))
 n=nets.setdefault(k,dict(key=list(k),src=set(),dests={}))
 n["src"].update(sh(r) for r in e.get("source_rects_um",[e["source_rect_um"]]))
 n["dests"][(str(e["dest_id"]),str(e["dest_bit"]))]=(sh(e["dest_rect_um"]),e.get("kind",""))
 if COLS and col(sh(e["dest_rect_um"])) is not None:destmap[(str(e["dest_id"]),str(e["dest_bit"]))]=k
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
def pairwin(s,d):  # y window of the trunk for one source rect / dest rect pair; column ends are FFs on the trunk
 cs,cd=col(s),col(d)
 if cs is None and cd is None:return direct(s,d)
 x=max(abs(s[0]-d[2]),abs(s[2]-d[0]))
 if cs is not None and cd is not None:return (max(s[1],d[1]),min(s[3],d[3])) if x<=R-J else (1.0,0.0)
 if cs is not None:
  z=win_rect(d,x+J);return (max(z[0],s[1]),min(z[1],s[3]))
 z=win_rect(s,x);return (max(z[0],d[1]),min(z[1],d[3]))
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
    z=pairwin(s,d);yl=max(yl,z[0]);yh=min(yh,z[1])
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
 if COLS:  # a column FF is the END of its D net and the START of its Q net: both may use the same track, split at the FF (column centre)
  cl=[]
  for r in rects:
   if col(r) is None:cl.append(r);continue
   oth=[o for o in rects if o is not r and tuple(o)!=tuple(r)];xc=(r[0]+r[2])/2
   if oth and max(o[2] for o in oth)<=xc:cl.append((xc-0.02,r[1],xc-0.02,r[3]))
   elif oth and min(o[0] for o in oth)>=xc:cl.append((xc+0.02,r[1],xc+0.02,r[3]))
   else:cl.append(r)
  rects=cl
 lo=min(r[0] for r in rects);hi=max(r[2] for r in rects)
 items.append(dict(key=list(k),S=S,D=[d for d,_ in n["dests"].values()],rects=rects,x0=lo,x1=hi,c0=min((r[0]+r[2])/2 for r in rects),c1=max((r[0]+r[2])/2 for r in rects),ylo=yl,yhi=yh,forb=forb,hops=hops,rsite=rsite))
# column FFs: tie each Q net (a column rect is its source) to the D net that ends in that FF; windows propagate back
byk={tuple(n["key"]):n for n in items};unpaired=0
for n in items:
 n["pair"]=None
 if COLS and any(col(s) is not None for s in n["S"]):
  n["pair"]=byk.get(destmap.get(tuple(n["key"])))
  if n["pair"] is None:unpaired+=1
def lev(n,seen=()):
 if "lev" not in n:
  p=n["pair"];n["lev"]=0 if p is None or id(p) in seen else 1+lev(p,seen+(id(n),))
 return n["lev"]
for n in items:lev(n)
for n in sorted(items,key=lambda n:-n["lev"]):
 p=n["pair"]
 if p is not None:p["ylo"]=max(p["ylo"],n["ylo"]-J);p["yhi"]=min(p["yhi"],n["yhi"]+J)
for n in items:
 if n["ylo"]>n["yhi"]+1e-8:reach_bad.append(dict(key=n["key"],x_um=[n["x0"],n["x1"]],y=[n["ylo"],n["yhi"]]))
cuts=[]
for x in [i*a.cut_step for i in range(0,int(math.ceil(tj["outline_um"][0])/a.cut_step)+1)]:
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
BK=2.16;colcnt=collections.Counter();capb={tg:(r[2]-r[0])*BK*0.55/0.2916 for r,tg in COLS.items()}
for n in items:n["cd"]=collections.Counter(col(d) for d in n["D"] if col(d) is not None) if COLS else {}
def static_ok(r,n):
 y=r["y_um"]
 if n["cd"] and any(colcnt[(tg,int(y//BK))]+m>capb[tg] for tg,m in n["cd"].items()):return False
 if any(c<y<b for c,b in n["forb"]):return False
 if any(n["x0"]<hi-1e-9 and n["x1"]>lo+1e-9 for lo,hi in r["blocked"]):return False
 return True
def ok(r,n):return static_ok(r,n) and free(r,n["x0"],n["x1"])
for r in rows:r["nets"]={}
assigned=[];pending=[n for n in items if n["ylo"]<=n["yhi"]+1e-8]
pending.sort(key=lambda n:(n["lev"],int((n["yhi"]-n["ylo"])//20),n["x0"],-n["x1"]))
un=[]
kids=collections.defaultdict(list)
for n in items:
 if n["pair"] is not None:kids[id(n["pair"])].append(n)
def search(grp,wl,wh,pref):
 i0=bisect.bisect_left(ry,wl-1e-9);i1=bisect.bisect_right(ry,wh+1e-9)
 if i1<=i0:return None,0
 m=bisect.bisect_left(ry,pref);m=min(max(m,i0),i1-1)
 lo_i=m;hi_i=m+1
 while lo_i>=i0 or hi_i<i1:
  if lo_i>=i0:
   if all(ok(rows[lo_i],g) for g in grp):return lo_i,i1-i0
   lo_i-=1
  if hi_i<i1:
   if all(ok(rows[hi_i],g) for g in grp):return hi_i,i1-i0
   hi_i+=1
 return None,i1-i0
def put(n,ch):
 n["y"]=rows[ch]["y_um"];n["ri"]=ch;bisect.insort(rows[ch]["ends"],(n["x0"],n["x1"]));rows[ch]["nets"][(n["x0"],n["x1"])]=n
 for tg,m in n["cd"].items():colcnt[(tg,int(n["y"]//BK))]+=m
def unput(n):
 r=rows[n["ri"]];r["ends"].remove((n["x0"],n["x1"]));del r["nets"][(n["x0"],n["x1"])]
 for tg,m in n["cd"].items():colcnt[(tg,int(n["y"]//BK))]-=m
 del n["y"];del n["ri"]
joint=0;pairs2=0
for n in pending:
 if "y" in n:continue
 wl,wh=n["ylo"],n["yhi"];pref=(wl+wh)/2;p=n["pair"]
 if p is not None:
  if "y" not in p:n["cand"]=range(0);n["why"]="its D net is unassigned";un.append(n);continue
  wl=max(wl,p["y"]-J);wh=min(wh,p["y"]+J);pref=p["y"]
 ch=None
 ks=[q for q in kids.get(id(n),[]) if "y" not in q and q["ylo"]<=q["yhi"]+1e-8]
 # a D net and the Q nets of its column FFs take ONE track when a row is free for all of them (split at the FF)
 if ks and not any(q["x0"]<n["x1"]+1e-6 and n["x0"]<q["x1"]+1e-6 for q in ks) and not any(q["x0"]<r["x1"]+1e-6 and r["x0"]<q["x1"]+1e-6 for i,q in enumerate(ks) for r in ks[i+1:]):
  jl=max([wl]+[q["ylo"] for q in ks]);jh=min([wh]+[q["yhi"] for q in ks])
  ch,_=search([n]+ks,jl,jh,(jl+jh)/2 if p is None else pref)
  if ch is not None:
   put(n,ch);n["cand"]=range(1)
   for q in ks:put(q,ch);q["cand"]=range(1)
   joint+=1;continue
 if ks:  # D and Q leave the column on the same side: two tracks; pick the D row so that every Q finds a row within the jog
  i0=bisect.bisect_left(ry,wl-1e-9);i1=bisect.bisect_right(ry,wh+1e-9);m=min(max(bisect.bisect_left(ry,pref),i0),max(i0,i1-1));done=False
  for st in range(0,max(1,i1-i0),6):
   for ci in ([m+st,m-st] if st else [m]):
    if not (i0<=ci<i1) or not ok(rows[ci],n):continue
    y=rows[ci]["y_um"];put(n,ci);got=[]
    for q in ks:
     qc,_=search([q],max(q["ylo"],y-J),min(q["yhi"],y+J),y)
     if qc is None:break
     put(q,qc);got.append(q)
    if len(got)==len(ks):
     n["cand"]=range(i1-i0);done=True
     for q in ks:q["cand"]=range(1)
     break
    for g in got+[n]:unput(g)
   if done:break
  if done:pairs2+=1;continue
 ch,nc=search([n],wl,wh,pref);n["cand"]=range(nc)
 if ch is None:un.append(n)
 else:put(n,ch)
# repair pass (rip-up): an unassigned net takes a row of its window whose <= 3 blockers can each move to another legal row
def blockers(r,x0,x1):
 e=r["ends"];i=bisect.bisect_left(e,(x0,));out=[]
 if i>0 and e[i-1][1]>x0-1e-6:out.append(e[i-1])
 while i<len(e) and e[i][0]<x1+1e-6:out.append(e[i]);i+=1
 return [r["nets"][t] for t in out]
def lim(n):
 wl,wh=n["ylo"],n["yhi"];p=n["pair"]
 if p is not None:
  if "y" not in p:return None
  wl=max(wl,p["y"]-J);wh=min(wh,p["y"]+J)
 for q in kids.get(id(n),[]):
  if "y" in q:wl=max(wl,q["y"]-J);wh=min(wh,q["y"]+J)
 return wl,wh
def repair(u):
 z=lim(u)
 if z is None:return False
 i0=bisect.bisect_left(ry,z[0]-1e-9);i1=bisect.bisect_right(ry,z[1]+1e-9);cand=[]
 for ci in range(i0,i1):
  if not static_ok(rows[ci],u):continue
  b=blockers(rows[ci],u["x0"],u["x1"])
  if len(b)<=4:cand.append((sum(1 for x in b if x["pair"] is not None or id(x) in kids),len(b),sum(x["x1"]-x["x0"] for x in b),ci))
 cand.sort()
 for _r,nb,_,ci in cand[:a.repair_rows]:
  b=blockers(rows[ci],u["x0"],u["x1"]);old=[(x,x["ri"]) for x in b]
  for x in b:unput(x)
  if not static_ok(rows[ci],u):
   for x,o in old:put(x,o)
   continue
  put(u,ci);moved=[];good=True
  for x,o in old:
   zz=lim(x);c2=None
   if zz is not None:c2,_=search([x],zz[0],zz[1],ry[o])
   if c2 is None:good=False;break
   put(x,c2);moved.append(x)
  if good:return True
  for x in moved:unput(x)
  unput(u)
  for x,o in old:put(x,o)
 return False
repaired=0
for _ in range(a.repair):
 todo=sorted([n for n in pending if "y" not in n],key=lambda n:n["lev"]);got=0
 for u in todo:
  if repair(u):got+=1
 repaired+=got
 if not got:break
un=[n for n in pending if "y" not in n]
for n in un:
 if "cand" not in n:n["cand"]=range(0)
assigned=[dict(key=n["key"],layer="M"+str(rows[n["ri"]]["layer"]),y_um=n["y"],x_um=[n["x0"],n["x1"]]) for n in items if "y" in n]
for c in cuts:
 x=c["x_um"];u=sum(1 for t in assigned if t["x_um"][0]<x<t["x_um"][1]);c["witness_used"]=u;c["f_witness"]=u/c["total"]
# column report: FF site density along each column and the D-to-Q jogs against the column's vertical supply
colrep={}
if COLS:
 crect={tg:r for r,tg in COLS.items()};cff=collections.defaultdict(list);cjog=collections.defaultdict(list)
 for n in items:
  if "y" not in n:continue
  for d in n["D"]:
   tg=col(d)
   if tg is not None:cff[tg].append(n["y"])
  p=n["pair"]
  if p is not None and "y" in p and abs(p["y"]-n["y"])>0.27:
   tg=next(col(s) for s in n["S"] if col(s) is not None);cjog[tg].append((min(p["y"],n["y"]),max(p["y"],n["y"])))
 for tg,r in crect.items():
  w=r[2]-r[0];sup=int((w/0.048+w/0.064)*0.75);ev=sorted([(lo,1) for lo,hi in cjog[tg]]+[(hi,-1) for lo,hi in cjog[tg]],key=lambda t:(t[0],t[1]));dep=cur=0
  for _,dlt in ev:cur+=dlt;dep=max(dep,cur)
  ys=sorted(cff[tg]);dens=max(collections.Counter(int(y//BK) for y in ys).values() or [0]);capff=capb[tg]
  colrep[tg]=dict(rect_um=list(r),ff=len(ys),ff_y=[round(ys[0],2),round(ys[-1],2)] if ys else None,ff_per_8rows_max=dens,ff_site_ratio=round(dens/capff,3),jogs=len(cjog[tg]),jog_max_um=round(max([hi-lo for lo,hi in cjog[tg]] or [0]),2),jog_depth=dep,vertical_supply=sup,jog_ratio=round(dep/max(1,sup),3))
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
 worst_full_rect=dict(x=worst["x_um"],n=worst["full_rect"],cap=worst["total"],f=round(worst["f_full"],4)),worst_center=dict(x=wc["x_um"],n=wc["center_extent"],cap=wc["total"],f=round(wc["f_center"],4)),worst_mandatory=dict(x=wm["x_um"],n=wm["mandatory"],cap=wm["total"],f=round(wm["f_mand"],4)),worst_witness=round(max(c["f_witness"] for c in cuts),4),columns=len(COLS),joint_tracks=joint,repaired=repaired,two_track_pairs=pairs2,unpaired_column_q_nets=unpaired,jog_um=J,cut_step=a.cut_step,worst_jog_ratio=max([c["jog_ratio"] for c in colrep.values()] or [0]),worst_ff_site_ratio=max([c["ff_site_ratio"] for c in colrep.values()] or [0]),unassigned_by_source=dict(unk.most_common(12)))
out=dict(schema="opentallas.memory_track_witness.r5",column_report=colrep,relay_hops=hopagg,status="HORIZONTAL_WITNESS_COMPLETE" if not un and not reach_bad else "UNRESOLVED",input_sha256={"plan":sha(a.plan),"edges":sha(a.edges),"grant":sha(a.grant)},summary=summ,cuts=cuts,assigned_horizontal_trunks=assigned,unassigned=[dict(key=n["key"],x_um=[n["x0"],n["x1"]],y=[n["ylo"],n["yhi"]],cand=len(n["cand"]),why=n.get("why","")) for n in un],reach_infeasible=reach_bad,scope=["pre-route architectural model; vertical branches/vias/pin access unqualified; no route or adoption credit","relay = one extra FF and one extra cycle on that edge, sited on its trunk track at a legal std-cell column"])
Path(a.out).write_text(json.dumps(out,indent=1)+"\n");print(json.dumps(summ))
