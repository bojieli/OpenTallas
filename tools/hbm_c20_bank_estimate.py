#!/usr/bin/env python3
"""Payload-bank physical estimate, never an adoption or source rewrite.
Preserves source station/bit identity. Checks macro overlap and computes actual
per-bit Manhattan hops after packing. Epochs stay outside all banks.
"""
import argparse,collections,json,math
from pathlib import Path
A=argparse.ArgumentParser();A.add_argument("plan");A.add_argument("out");A.add_argument("--widths",default="256,1024");A.add_argument("--rotate",action="store_true");A.add_argument("--safe-subset",action="store_true");a=A.parse_args();widths=sorted(map(int,a.widths.split(",")))
p=json.load(open(a.plan));reach=float(p["die"]["reach_um"]);out={"scope":"estimate only, no RTL/plan adoption","types":{},"banks":{}}
G=8.64;BS=69.12
for tn in ("q_hub_nw","q_hub_ne"):
 t=p["partition_types"][tn];W,H=t["outline_um"];grid=collections.defaultdict(list)
 def bins(r):
  return ((x,y) for x in range(math.floor(r[0]/BS),math.floor((r[2]-1e-6)/BS)+1) for y in range(math.floor(r[1]/BS),math.floor((r[3]-1e-6)/BS)+1))
 def add(r):
  for k in bins(r):grid[k].append(r)
 def free(r):
  if r[0]<0 or r[1]<0 or r[2]>W or r[3]>H:return False
  for k in bins(r):
   for b in grid[k]:
    if r[0]<b[2]-1e-6 and r[2]>b[0]+1e-6 and r[1]<b[3]-1e-6 and r[3]>b[1]+1e-6:return False
  return True
 for h in t["hard_cores"]:
  x,y=h["origin_um"];w,hh=h["outline_um"];add((x,y,x+w,y+hh))
 sites=collections.defaultdict(list);chunks={};banks=[];unplaced=[]
 for si,s in enumerate(t["internal_stations"]):
  for ri,r in enumerate(s["regs_um"]):
   sites[(round(r[0]/34.56),round(r[1]/34.56))].append((si,ri,s["bits"],r))
 offsets=sorted(((x,y) for x in range(-12,13) for y in range(-12,13)),key=lambda q:(abs(q[0])+abs(q[1]),abs(q[1]),q))
 for site,items in sorted(sites.items(),key=lambda z:-sum(i[2] for i in z[1])):
  n=sum(i[2] for i in items)
  if n<128:continue
  stream=[]
  for si,ri,b,r in items:stream.append([si,ri,0,b,r]);chunks[(si,ri)]=[]
  cursor=0
  while n:
   cap=max([v for v in widths if v<=n] or [widths[0]]);used=min(n,cap);basew=math.ceil((8.64+.192*(cap-1))/G)*G;bw=basew;bh=8.64
   cx=site[0]*34.56;cy=site[1]*34.56;rect=None
   for dx,dy in offsets:
    x=round((cx-bw/2)/G)*G+dx*G;y=round((cy-bh/2)/G)*G+dy*G
    for rot in ([False,True] if a.rotate else [False]):
     ww,hh=(bh,bw) if rot else (bw,bh);rr=(x,y,x+ww,y+hh)
     if free(rr):rect=rr;vertical=rot;break
    if rect is not None:break
   if rect is None:
    unplaced.append({"site":site,"width":cap,"used":used});n-=used
    left=used
    while left:
     q=stream[cursor];k=min(left,q[3]);chunks[(q[0],q[1])].append((q[2],k,None,None));q[2]+=k;q[3]-=k;left-=k
     if not q[3]:cursor+=1
    continue
   add(rect);bi=len(banks);banks.append({"inst":"u_payload_bank%d"%bi,"width":cap,"used":used,"origin_um":list(rect[:2]),"outline_um":[rect[2]-rect[0],rect[3]-rect[1]],"vertical":vertical,"site":site})
   left=used;boff=0
   while left:
    q=stream[cursor];k=min(left,q[3]);chunks[(q[0],q[1])].append((q[2],k,bi,boff));q[2]+=k;q[3]-=k;left-=k;boff+=k
    if not q[3]:cursor+=1
   n-=used
 rejected=set()
 def point(si,ri,bit):
  s=t["internal_stations"][si]
  if (si,ri) not in chunks:return s["regs_um"][ri]
  for first,size,bi,boff in chunks[(si,ri)]:
   if first<=bit<first+size:
    if bi is None:return s["regs_um"][ri] if a.safe_subset else None
    if bi in rejected:return s["regs_um"][ri]
    b=banks[bi];off=.192*(boff+bit-first);return (b["origin_um"][0]+4.32+(0 if b["vertical"] else off),b["origin_um"][1]+4.32+(off if b["vertical"] else 0))
  raise ValueError("missing payload bit")
 def bankof(si,ri,bit):
  for first,size,bi,boff in chunks.get((si,ri),[]):
   if first<=bit<first+size:return bi if bi is not None and bi not in rejected else None
  return None
 if a.safe_subset:
  while True:
   remove=set()
   for si,station in enumerate(t["internal_stations"]):
    for bit in range(station["bits"]):
     pts=[station["from_um"]]+[point(si,ri,bit) for ri in range(len(station["regs_um"]))]+[station["to_um"]]
     for hi,(b,c) in enumerate(zip(pts,pts[1:])):
      reserve=4.32*sum(bankof(si,ri,bit) is not None for ri in (hi-1,hi) if 0<=ri<len(station["regs_um"]))
      if abs(b[0]-c[0])+abs(b[1]-c[1])+reserve<=reach:continue
      for ri in (hi-1,hi):
       if not 0<=ri<len(station["regs_um"]):continue
       for first,size,bi,boff in chunks.get((si,ri),[]):
        if first<=bit<first+size and bi is not None and bi not in rejected:remove.add(bi)
   if not remove:break
   rejected.update(remove)
   print(tn,"safe subset pruned",len(remove),"banks; total",len(rejected),flush=True)
 worst=0;bad=0;missing=0;examples=[];original=0
 for si,s in enumerate(t["internal_stations"]):
  old=[s["from_um"]]+s["regs_um"]+[s["to_um"]]
  original=max(original,max(abs(b[0]-c[0])+abs(b[1]-c[1]) for b,c in zip(old,old[1:])))
  for bit in range(s["bits"]):
   pts=[s["from_um"]]+[point(si,ri,bit) for ri in range(len(s["regs_um"]))]+[s["to_um"]]
   if any(x is None for x in pts):missing+=1;continue
   mh=max(abs(b[0]-c[0])+abs(b[1]-c[1]) for b,c in zip(pts,pts[1:]));worst=max(worst,mh)
   if mh>reach+1e-6:
    bad+=1
    if len(examples)<8:examples.append({"station":si,"conn":s["conn"],"bit":bit,"max_hop_um":mh})
 soft=[0.,0.];softpts=[]
 cut=3957.12 if tn=="q_hub_nw" else 8216.64-3957.12
 for c in t["contents"]:
  if any(h["inst"]==c["inst"] or h["inst"].startswith(c["inst"]+"_") or h["inst"].startswith(c["inst"]+".") for h in t["hard_cores"]):continue
  xx=c["origin_um"][0]+c["outline_um"][0]/2;soft[int(xx>=cut)]+=c["cells"];softpts.append((xx,c["cells"]))
 for si,station in enumerate(t["internal_stations"]):
  for ri,r in enumerate(station["regs_um"]):
   retained=sum(size for first,size,bi,boff in chunks.get((si,ri),[]) if bi is not None and bi not in rejected)
   cost=(station["bits"]-retained)*1.3;soft[int(r[0]>=cut)]+=cost;softpts.append((r[0],cost))
 active=[b for bi,b in enumerate(banks) if bi not in rejected]
 cp=collections.Counter()
 for xx,cost in softpts:cp[xx]+=cost
 cutrows=[];partcells=[];acc=0;prev=None
 for xx,cost in sorted(cp.items()):
  if acc+cost>360000 and acc:
   cutrows.append({"x_um":(prev+xx)/2,"crossing_payload_bits":0});partcells.append(acc);acc=0
  acc+=cost;prev=xx
 if acc:partcells.append(acc)
 for si,station in enumerate(t["internal_stations"]):
  for bit in range(station["bits"]):
   pts=[station["from_um"]]+[point(si,ri,bit) for ri in range(len(station["regs_um"]))]+[station["to_um"]]
   if any(q is None for q in pts):continue
   for aa,bb in zip(pts,pts[1:]):
    lo,hi=sorted((aa[0],bb[0]))
    for cr in cutrows:
     if lo<cr["x_um"]<=hi:cr["crossing_payload_bits"]+=1
 allrect=[]
 for hh in t["hard_cores"]+active:
  xx,yy=hh["origin_um"];ww,hhgt=hh["outline_um"];allrect.append((xx,yy,xx+ww,yy+hhgt,hh.get("obs_max","M5")))
 for cr in cutrows:
  cx=cr["x_um"];hit=[rr for rr in allrect if rr[0]<cx<rr[2]];cr["intersected_hard_bodies"]=len(hit);cap={}
  for metal,pitch in [(2,.036),(4,.048),(6,.064)]:
   spans=sorted((r[1],r[3]) for r in hit if int(r[4][1:])>=metal);length=0;end=0
   for lo,hi in spans:
    length+=max(0,hi-max(lo,end));end=max(end,hi)
   cap["M%d"%metal]=math.floor(.6*(H-length)/pitch)
  cr["optimistic_tracks_at_0p6"]=cap;cr["demand_over_optimistic_capacity"]=cr["crossing_payload_bits"]/sum(cap.values()) if sum(cap.values()) else None

 out["types"][tn]={"reach_um":reach,"safe_subset":a.safe_subset,"minimum_soft_subparts_360k_lowerbound":math.ceil(sum(soft)/360000),"greedy_x_soft_cells":partcells,"candidate_x_cuts_DIAGNOSTIC":cutrows,"pruned_banks":len(rejected),"remaining_soft_cells_halves_F1p3":soft,"banks":len(banks)-len(rejected),"width_counts":dict(collections.Counter(b["width"] for b in active)),"unplaced_banks":len(unplaced),"unplaced_first":unplaced[:8],"banked_payload_bits":sum(b["used"] for b in active),"max_original_hop_um":original,"max_repacked_hop_um":worst,"payload_bits_with_hop_above_reach":bad,"payload_bits_unplaced":missing,"first_hop_failures":examples,"bank_macro_area_um2":sum(b["outline_um"][0]*b["outline_um"][1] for b in active),"verdict":"ESTIMATE_FAIL" if bad or unplaced else "GEOMETRY_ESTIMATE_ONLY"}
 out["banks"][tn]=active
 print(tn,json.dumps(out["types"][tn]),flush=True)
Path(a.out).write_text(json.dumps(out,indent=1)+"\n")
