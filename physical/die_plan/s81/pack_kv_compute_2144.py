#!/usr/bin/env python3
"""Place actual KV-slice transit registers around its restored normal core field.
Finite geometric search: straight corridor, legal core-free jog bands, then up
to six more registered stages. Added stages are explicit model costs, never
inferred away. Stations cannot occupy inter-core gaps narrower than36um.
"""
import argparse, copy, json, math, os, re, sys
from pathlib import Path
from multiprocessing import get_context
HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE.parents[2]/"tools/die_plan"),str(HERE.parents[2])]
import ft_corridor as F, compact_plan
import ft_projection_union_2144 as U
F.MAX_PROJ=float(os.environ.get("KV_FT_PROJECTION_UM","40"))
if os.environ.get("KV_FT_UNION_PROJECTION")=="1":
    BaseProject=F.project
    F.project=lambda pts,boxes,bounds: U.project(pts,boxes,bounds,BaseProject,F.in_boxes)
BaseAlloc=F.RowAllocator

def slit_fill(boxes):
    out=[]
    for i,(a0,b0,a1,b1) in enumerate(boxes):
        for c0,d0,c1,d1 in boxes[i+1:]:
            yl,yh=max(b0,d0),min(b1,d1)
            if yh>yl:
                lo,hi=(a1,c0) if a1<=c0 else (c1,a0)
                if 0<hi-lo<36:out.append((lo-.02,yl,hi+.02,yh))
            xl,xh=max(a0,c0),min(a1,c1)
            if xh>xl:
                lo,hi=(b1,d0) if b1<=d0 else (d1,b0)
                if 0<hi-lo<36:out.append((xl,lo-.02,xh,hi+.02))
    return out

def channel_alloc(*args,blocked=(),**kw):
    return BaseAlloc(*args,blocked=list(blocked)+slit_fill(blocked),**kw)
F.RowAllocator=channel_alloc
BasePlaceSlot=F.place_slot
def channel_place_slot(slot,a,b,fin,fout,w,h,boxes,alloc,budget,*args,**kw):
    # Projection/DP and allocation must see the SAME blocked slits. Otherwise
    # DP chooses a narrow slit and the allocator later cannot place its bit.
    return BasePlaceSlot(slot,a,b,fin,fout,w,h,boxes+slit_fill(boxes),alloc,budget,*args,**kw)
F.place_slot=channel_place_slot

def channels(ty,slot):
    w,h=ty["outline_um"];fin=slot["in_face"];a,b=[sum(slot[k])/2 for k in ("in_window_um","out_window_um")]
    lo,hi=min(a,b),max(a,b);span=h if fin in "NS" else w
    boxes=[]
    for c in ty.get("hard_cores",[]):
        x,y=c["origin_um"];cw,ch=c["outline_um"];boxes.append((x-1.1,y-1.1,x+cw+1.1,y+ch+1.1))
    free=[];start=None
    for step in range(120,int(span*2)-120):
        v=step/2
        ok=not any(y0<v<y1 and x0<hi and x1>lo if fin in "NS" else x0<v<x1 and y0<hi and y1>lo for x0,y0,x1,y1 in boxes)
        if ok and start is None:start=v
        if not ok and start is not None:
            if v-start>=40:free.append((start,v-.5))
            start=None
    if start is not None and span-60-start>=40:free.append((start,span-60))
    return sorted([round((s+e)/2,2) for s,e in free],key=lambda x:abs(x-span/2))

def work(tn):
    raw=copy.deepcopy(RAW);ty=raw["partition_types"][tn];old={s["name"]:s["stations"] for s in ty["ft_slots"]}
    split={tn+"/"+s["name"]:128 for s in ty["ft_slots"] if s["width"]>=256}
    jogs={};tried={};added={};last=None
    for attempt in range(400):
        try:
            ledger=F.place(raw,[tn],split_bits=split,jogs=jogs)
            return tn,ty,dict(verdict="PASS",added_stations={s["name"]:[old[s["name"]],s["stations"]] for s in ty["ft_slots"] if old[s["name"]]!=s["stations"]},jogs=jogs,ledger=ledger,attempts=attempt+1)
        except Exception as e:
            last=str(e);m=re.match(r"(ft[0-9]+)",last)
            if not m:break
            sn=m.group(1);slot=next(s for s in ty["ft_slots"] if s["name"]==sn);key=tn+"/"+sn
            if slot["in_face"]==dict(N="S",S="N",W="E",E="W")[slot["out_face"]]:
                ck=(sn,slot["stations"]);todo=[x for x in channels(ty,slot) if x not in tried.setdefault(ck,[])]
                if todo:tried[ck].append(todo[0]);jogs[key]=todo[0];continue
                jogs.pop(key,None)
            if added.get(sn,0)>=6:break
            slot["stations"]+=1;added[sn]=added.get(sn,0)+1
    return tn,None,dict(verdict="FAIL",error=last,jogs=jogs,attempts=attempt+1)

def main():
    global RAW
    ap=argparse.ArgumentParser();ap.add_argument("plan");ap.add_argument("out");ap.add_argument("report");a=ap.parse_args()
    RAW=json.loads(Path(a.plan).read_text());report={}
    with get_context("fork").Pool(5) as pool:
        for tn,ty,info in pool.imap_unordered(work,[f"ot_s81sl_kv_leaf__t{i}" for i in range(1,6)]):
            report[tn]=info
            if ty is not None:RAW["partition_types"][tn]=ty
            print(tn,info["verdict"],info.get("added_stations",info.get("error")),flush=True)
    Path(a.out).write_text(compact_plan.dumps(RAW));Path(a.report).write_text(json.dumps(report,indent=1)+"\n")
if __name__=="__main__":main()
