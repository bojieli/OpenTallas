#!/usr/bin/env python3
"""DIE-QC-46 QC plan event qc45 on plan_qc43 (e630ffb8), per the DIE-QC-45 02:07 ruling:
 (a) ring landing bands below the measured ring_ff reserve are re-sized with main clock_landing_plan.resize_undersized_bands
     (DIE-KV-32 fix-only rule: band >= ring flop count x the landing_placement.tcl 0.40-fill footprint) in every type that
     has one; types whose re-size finds no macro-free band keep their bands (listed);
 (b) R8 pad-count strap sites (Codex add_r8_strap_sites.py logic, M5, 4.32-um lattice nearest the type tap, existing
     sites kept) on EVERY type whose bind manifest (bind_parent_id_straps.json) declares r8pad_strap ports;
 (c) glue: the 4 native d2d_sram_1r1w_64x137_m1_r2c2_p192 replay SRAMs (u_bound.u_d2d_rom.u_core.u_end.u_link.
     g_bank[0..3].u_store.u_sram, CHECKED kit 1_2_yosys.v) as physical-only hard_cores (Codex add_macro_sites.py view
     + track-phase + obstacle logic), placed next to the S-face FDI tx/rx flit windows.
usage: compose_qc45.py REPO PLAN43 SIDECAR MANIFEST OUTDIR"""
import json,sys,re,math,copy,hashlib,collections
from pathlib import Path
repo,plan_in,side_in,man_in,od=sys.argv[1:6];repo=Path(repo);od=Path(od)
sys.path.insert(0,str(repo/"tools/die_plan"))
import clock_landing_plan as CP, schema as S, gen_phys as G, check as C
raw=json.load(open(plan_in));side=json.load(open(side_in));man=json.load(open(man_in))
rep={"base":plan_in,"base_sha256":hashlib.sha256(open(plan_in,"rb").read()).hexdigest()}
# (a)
def under(t):
    bands=t.get("clock",{}).get("landing_contract",{}).get("bands",{})
    return any((not k.startswith("monitor_")) and b.get("rect_um") and (b["rect_um"][2]-b["rect_um"][0])*(b["rect_um"][3]-b["rect_um"][1])+1e-6<CP.ring_ff_reserve_um2(b["width"]) for k,b in bands.items())
types=[tn for tn,t in sorted(raw["partition_types"].items()) if under(t)]
bands=[];kept={}
for tn in types:
    try:new,r=CP.resize_undersized_bands(raw,side,[tn])
    except ValueError as e:kept[tn]=str(e);continue
    raw["partition_types"][tn]=new["partition_types"][tn];bands+=r
rep["a_bands"]=dict(types_considered=len(types),types_resized=len({b["type"] for b in bands}),bands_resized=len(bands),
                   kept_no_fit=kept,max_hop_um=max(b["hop_um"] for b in bands) if bands else None)
json.dump(bands,open(od/"qc45_band_resize.json","w"),indent=1)
# (b) R8 strap sites
P=S.Plan(raw,path=plan_in);r8={}
for tn,d in sorted(man["types"].items()):
    want={n:int(v["width"]) for n,v in d.items() if v.get("kind")=="r8pad_strap"}
    if not want:continue
    t=raw["partition_types"][tn];insts=[n for n,p in P.parts.items() if p["type"]==tn]
    for q in insts:
        for n,w in want.items():
            v=man["instances"][q][n]
            if v.get("kind")!="r8pad_strap" or int(v["width"])!=w or not 0<=int(v["value"])<2**w:raise ValueError(f"{tn}.{q}.{n}: bad tied contract")
    cs=t.setdefault("count_straps",[]);old={s["name"]:s for s in cs};new=[]
    for n,w in sorted(want.items()):
        if n in old:
            if old[n]["width"]!=w or len(old[n].get("sites_um",[]))!=w:raise ValueError(f"{tn}.{n}: bad existing contract")
            continue
        s=dict(name=n,width=w,note="OWNER 10-28 R8 pad-count strap; bind parent manifest, unchanged values/cycles");cs.append(s);new.append(s)
    if not new:continue
    P=S.Plan(raw,path=plan_in);w,h=t["outline_um"];blocked=[]
    for inst,mod,lef,lib,x,y,ori in G.type_macros(P,tn):
        m=re.search(r"\bSIZE\s+([\d.]+)\s+BY\s+([\d.]+)\s*;",(repo/lef).read_text());mw,mh=map(float,m.groups())
        if ori in ("R90","R270","E","W","FE","FW","MXR90","MYR90"):mw,mh=mh,mw
        blocked.append((x-5.4,y-5.4,x+mw+5.4,y+mh+5.4))
    for r in t.get("clock",{}).get("reserved_sites_um",[]):
        a,b,c,d_=r["rect_um"];blocked.append((a-1.08,b-1.08,c+1.08,d_+1.08))
    for b in t.get("clock",{}).get("landing_contract",{}).get("bands",{}).values():
        if b.get("rect_um"):a,b_,c,d_=b["rect_um"];blocked.append((a,b_,c,d_))
    occupied=[(p["x"],p["y"]) for p in G.plan_pin_records(P,tn,G.type_pins(P,tn))]
    ax,ay=t.get("clock",{}).get("tap_um",[w/2,h/2]);cand=[]
    for ix in range(2,int(w/4.32)-1):
        x=round(ix*4.32,4)
        for iy in range(2,int(h/4.32)-1):
            y=round(iy*4.32,4)
            if any(a<=x<=c and b<=y<=d_ for a,b,c,d_ in blocked):continue
            cand.append((abs(x-ax)+abs(y-ay),x,y))
    cand.sort();needed=sum(s["width"] for s in new);sites=[]
    for _,x,y in cand:
        if any(abs(x-a)<2.16 and abs(y-b)<2.16 for a,b in occupied):continue
        sites.append([x,y]);occupied.append((x,y))
        if len(sites)==needed:break
    if len(sites)!=needed:raise ValueError(f"{tn}: no physical room for {needed} R8 pins")
    cur=0
    for s in new:s["layer"]="M5";s["sites_um"]=sites[cur:cur+s["width"]];cur+=s["width"]
    r8[tn]=dict(new_bits=needed,ports={s["name"]:s["width"] for s in new},instances=insts,added_cycles=0)
rep["b_r8"]=r8
# (c) glue d2d SRAM hard cores
master="d2d_sram_1r1w_64x137_m1_r2c2_p192";d=repo/"physical/asap7_memory_macros_v2"/master;lef=d/(master+".lef")
s=lef.read_text();size=[float(x) for x in re.search(r"\bSIZE\s+(\S+)\s+BY\s+(\S+)\s*;",s).groups()]
layers=[int(x) for x in re.findall(r"\bLAYER\s+M([1-9])\b",s)]
pins=[];cur=None;layer=None;use="SIGNAL"
for line in s.splitlines():
    z=line.strip();mt=re.match(r"PIN\s+(\S+)",z)
    if mt:cur=mt[1];layer=None;use="SIGNAL";continue
    if cur is None:continue
    if z=="END "+cur:cur=None;continue
    if z.startswith("USE "):use=z.split()[1]
    mt=re.match(r"LAYER\s+(M[1-9])",z)
    if mt:layer=mt[1]
    mt=re.match(r"RECT\s+([-.0-9]+)\s+([-.0-9]+)\s+([-.0-9]+)\s+([-.0-9]+)",z)
    if mt and layer and use not in ("POWER","GROUND") and not any(q["name"]==cur for q in pins):pins.append({"name":cur,"layer":layer,"rect":[float(q) for q in mt.groups()]})
P=S.Plan(raw,path=plan_in);shifts=[]
for axis,direction in [(0,"V"),(1,"H")]:
    a=[q for q in pins if P.layers.get(q["layer"],{}).get("dir")==direction];choices=[]
    for ii in range(-24,25):
        shift=ii*.006;minimum=1e9;ok=True
        for q in a:
            L=P.layers[q["layer"]];lo,hi=q["rect"][axis],q["rect"][axis+2];mid=(lo+hi)/2+shift;v=L["offset_um"]+round((mid-L["offset_um"])/L["pitch_um"])*L["pitch_um"];margin=min(v-shift-lo,hi-(v-shift))
            if margin<1e-7:ok=False;break
            minimum=min(minimum,margin)
        if ok:choices.append((-round(minimum,6) if a else 0,abs(shift),shift))
    if not choices:raise ValueError("no common legal pin phase "+master)
    shifts.append(min(choices)[2])
pp=[]
for q in pins:
    L=P.layers[q["layer"]];a=0 if L["dir"]=="V" else 1;pt=[(q["rect"][i]+q["rect"][i+2])/2 for i in [0,1]];pt[a]=L["offset_um"]+round((pt[a]+shifts[a]-L["offset_um"])/L["pitch_um"])*L["pitch_um"]-shifts[a];pp.append({"name":q["name"],"layer":q["layer"],"x":round(pt[0],6),"y":round(pt[1],6)})
(od/"macro_pins").mkdir(exist_ok=True);(od/"macro_pins"/(master+".json")).write_text(json.dumps({"module":master,"pins":pp},indent=1)+"\n")
t=raw["partition_types"]["glue"];W,H=t["outline_um"];halo=4.32
def rect_hit(a,b):return a[0]<b[2]-1e-8 and b[0]<a[2]-1e-8 and a[1]<b[3]-1e-8 and b[1]<a[3]-1e-8
def ptbox(p,h=2):return [p[0]-h,p[1]-h,p[0]+h,p[1]+h]
occ=[b["rect_um"] for b in t.get("clock",{}).get("landing_contract",{}).get("bands",{}).values() if b.get("rect_um")]
ck=t.get("clock",{});occ+=[ptbox(z["xy"]) for z in ck.get("taps",[]) if "xy" in z]
if ck.get("tap_um"):occ.append(ptbox(ck["tap_um"]))
for r in ck.get("landing_contract",{}).get("collector_tree",{}).get("relays",[]):occ.append(ptbox(r["xy"],1))
for r in ck.get("reserved_sites_um",[]):occ.append(r["rect_um"])
for key in ["ft_slots","internal_stations"]:
    for f in t.get(key,[]):
        for p in f.get("regs_um",[]):occ.append(ptbox(p,1.5))
for s_ in t.get("count_straps",[]):
    for p in s_.get("sites_um",[]):occ.append(ptbox(p,1.5))
for h_ in t.get("hard_cores",[]):
    x,y=h_["origin_um"];w,hh=h_["outline_um"];hl=h_.get("halo_um",0);occ.append([x-hl,y-hl,x+w+hl,y+hh+hl])
pr=[p for p in G.plan_pin_records(P,"glue",G.type_pins(P,"glue"))]
for p in pr:occ.append(ptbox((p["x"],p["y"]),1.0))
placed=[]
for k in range(4):
    n=f"u_bound.u_d2d_rom.u_core.u_end.u_link.g_bank[{k}].u_store.u_sram";w,h=size
    px,py=60.48+k*69.12,51.84
    cands=[]
    for dx in range(-24,25):
        for dy in range(-12,40):
            x=round((px+dx*8.64)/8.64)*8.64+shifts[0];y=round((py+dy*8.64)/8.64)*8.64+shifts[1]
            a=[x-halo,y-halo,x+w+halo,y+h+halo]
            if a[0]<8.64-1e-6 or a[1]<8.64-1e-6 or a[2]>W-8.64+1e-6 or a[3]>H-8.64+1e-6:continue
            cands.append((abs(dx)+abs(dy),abs(dy),x,y,a))
    ch=None
    for _,_,x,y,a in sorted(cands):
        if any(rect_hit(a,b) for b in occ):continue
        ch=(x,y,a);break
    if ch is None:raise ValueError("no glue site for "+n)
    x,y,a=ch;occ.append(a)
    placed.append({"inst":n,"module":master,"origin_um":[round(x-shifts[0],6),round(y-shifts[1],6)],"track_offset_um":[round(q,6) for q in shifts],
                   "pins_file":"macro_pins/"+master+".json","outline_um":size,"orient":"R0","halo_um":halo,"lef":str(lef.relative_to(repo)),
                   "lib":str((d/(master+"_tt.lib")).relative_to(repo)),"obs_max":"M"+str(max(layers)),
                   "note":"DIE-QC-46 qc45: exact existing native d2d replay SRAM (kit 1_2_yosys.v), physical placement only; no logical contents, cells, ports or cycles added."})
t["hard_cores"].extend(placed);t["core_pg_connect"]=True
rep["c_glue"]=[(c["inst"],c["origin_um"]) for c in placed]
errs=S.validate(raw)
if errs:raise ValueError(errs[:10])
out=od/"plan_qc45.json";out.write_text(json.dumps(raw,indent=2)+"\n")
rep["plan_qc45_sha256"]=hashlib.sha256(out.read_bytes()).hexdigest()
json.dump(rep,open(od/"compose_qc45.json","w"),indent=1,default=list);print(json.dumps(rep,indent=1,default=list)[:4000])
