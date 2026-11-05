#!/usr/bin/env python3
"""DIE-HBM-74 HBM plan event ev74 (COORD 11-05 12:38/12:40/12:4x rulings). mk_ev74.py PLAN_DIR(plain die_plan.json) REPO_PLAN_ROOT KITPINS
 (1) ra/rb (ot_hbm_idx_score_hcol_h0_ra/_rb) 106.272x187.488 -> 106.272x290.304 (HBM-FORM-CONG-5 rb_tall/ra_tall kits; N-edge pins +102.816)
 (2) ot_hgi_sfu_opsb_output 760.32x224.64 -> 760.32x280.8, grown DOWN in q_b113 (MX; core S-face pins keep their parent position),
     macro rows re-spaced with 21.6 um gaps in core_macros.json
 (3) ot_hbm_idx_topk_link_static 650.16x500.04 -> 650.16x535.68, +35.64 spent as 3 x 11.88 um gaps between its 4 macro rows
 (4) q_sm0 L29_i S-face window +69.168 um (HBM-BIND-9 option A)
 (5) ot_hbm_svc_sm_xcal_rel_t rst_n pin -> (121.032,224.544) M5 = signed DB (xcalt8 i1 6_final.def)
 Overlaps from the growth: hard cores in the same x span are pushed (up, or down for opsb_output) keeping their original clearance,
 shifts rounded up to the 4.32 um PG lattice. topk_store has no slot in d44v (part-30 split piece), so it is kit-local."""
import json,sys,gzip,math,os
from pathlib import Path
pd=Path(sys.argv[1]); root=Path(sys.argv[2]); kp=Path(sys.argv[3])
D=json.loads((pd/"die_plan.json").read_text()); PT=D["partition_types"]; LAT=8.64; MING=8.64; EPS=1e-6; REP={}
def ldpins(f):
    for d in [pd]+sorted(root.glob("*"),reverse=True):
        for c in (d/f, Path(str(d/f)+".gz")):
            if c.exists(): return json.load(gzip.open(c)) if c.suffix==".gz" else json.loads(c.read_text())
    raise SystemExit("no pins "+f)
GROW={"ot_hbm_idx_score_hcol_h0_ra":(290.304,"up"),"ot_hbm_idx_score_hcol_h0_rb":(290.304,"up"),
      "ot_hgi_sfu_opsb_output":(280.8,"down"),"ot_hbm_idx_topk_link_static":(535.68,"up")}
newpf={}
for h in [h for T in PT.values() for h in T.get("hard_cores",[]) if h["module"] in GROW]:
    if h["pins_file"] in newpf.values() or h["module"] in newpf: continue
    oh=h["outline_um"][1]; nh=GROW[h["module"]][0]; d=nh-oh; w=h["outline_um"][0]
    P=ldpins(h["pins_file"]); n=0
    for q in P:
        if abs(q["y"]-(oh-0.096))<1e-6: q["y"]=round(q["y"]+d,4); n+=1
    base=h["pins_file"].split("/")[-1].replace(".json","").replace(".gz","")
    nf="cores/%s__%gx%g__ev74_tall.json"%(h["module"],round(w,3),round(nh,3))
    (pd/nf).write_text(json.dumps(P,indent=1)+"\n"); newpf[h["module"]]=nf; REP.setdefault("pins",{})[h["module"]]=dict(from_=h["pins_file"],to=nf,n_pins=len(P),n_edge_moved=n,dy=round(d,3))
def box(h):
    (x,y),(w,hh)=h["origin_um"],h["outline_um"]
    if h.get("orient","R0") in("R90","R270","MXR90","MYR90"): w,hh=hh,w
    return [x,y,x+w,y+hh]
def xo(a,b): return min(a[2],b[2])-max(a[0],b[0])>EPS
def ubox(u): bs=[box(h) for h in u]; return [min(q[0] for q in bs),min(q[1] for q in bs),max(q[2] for q in bs),max(q[3] for q in bs)]
UGAP=8.0
def units(hc):
    """rigid rows: cores with the same origin y and height whose x gaps are <= UGAP move as one (keeps ra|rb pairs aligned)"""
    par=list(range(len(hc)))
    def f(i):
        while par[i]!=i: par[i]=par[par[i]]; i=par[i]
        return i
    bx=[box(h) for h in hc]
    for i in range(len(hc)):
        for j in range(i+1,len(hc)):
            a,b=bx[i],bx[j]
            if abs(a[1]-b[1])<EPS and abs(a[3]-b[3])<EPS and max(a[0],b[0])-min(a[2],b[2])<=UGAP+EPS: par[f(i)]=f(j)
    g={}
    for i,h in enumerate(hc): g.setdefault(f(i),[]).append(h)
    return list(g.values())
def shift(u,dy):
    for h in u: h["origin_um"]=[h["origin_um"][0],round(h["origin_um"][1]+dy,4)]
moved={}
import copy
def place(tn,T,hc,tg,DIR):
    U=units(hc); ob=[ubox(u) for u in U]
    def udir(u):
        t=[h for h in u if h["module"] in GROW]
        return DIR.get(t[0]["inst"],DIR[t[0]["module"]])[1] if t else None
    for u in U:
        dr=udir(u)
        if not dr: continue
        d=0
        for h in u:
            if h["module"] not in GROW: continue
            nh=GROW[h["module"]][0]; d=max(d,nh-h["outline_um"][1]); h["outline_um"]=[h["outline_um"][0],nh]; h["pins_file"]=newpf[h["module"]]
            h["note"]=(h.get("note","")+" | ev74: %s %+.3f um (%s)"%(h["module"],nh-ob[U.index(u)][3]+ob[U.index(u)][1],dr)).strip(" |")
        if dr=="down":
            s_=math.ceil(d/LAT-1e-9)*LAT
            for h in u:
                if h["module"] in GROW: h["origin_um"]=[h["origin_um"][0],round(h["origin_um"][1]-s_,4)]
                else: h["origin_um"]=[h["origin_um"][0],round(h["origin_um"][1]-s_,4)]
    mv={}
    def isdown(i): return udir(U[i])=="down"
    def push(dirn):
        for it in range(400):
            ch=0
            for i in range(len(U)):
                for j in range(len(U)):
                    if i==j or not xo(ob[i],ob[j]): continue
                    A,B=ubox(U[i]),ubox(U[j]); oa,obb=ob[i],ob[j]
                    if dirn=="up" and obb[1]>=oa[3]-EPS and mv.get(j,0)>=0 and not isdown(j):
                        need=A[3]+min(obb[1]-oa[3],MING)-B[1]
                        if need>EPS: s_=math.ceil(need/LAT-1e-9)*LAT; shift(U[j],s_); ch+=1; mv[j]=round(ubox(U[j])[1]-obb[1],4)
                    if dirn=="down" and oa[1]>=obb[3]-EPS and (isdown(i) or mv.get(i,0)<0):
                        need=B[3]+min(oa[1]-obb[3],MING)-A[1]
                        if need>EPS: s_=math.ceil(need/LAT-1e-9)*LAT; shift(U[j],-s_); ch+=1; mv[j]=round(ubox(U[j])[1]-obb[1],4)
            if not ch: return
    push("down"); push("up")
    H=T["outline_um"][1]
    out=[[tn,h["inst"],[round(v,3) for v in box(h)]] for h in hc if box(h)[1]<-EPS or box(h)[3]>H+EPS]
    ov=[[x["inst"],y["inst"]] for i,x in enumerate(hc) for y in hc[i+1:] if xo(box(x),box(y)) and min(box(x)[3],box(y)[3])-max(box(x)[1],box(y)[1])>EPS]
    mvi={h["inst"]:s_ for j,s_ in mv.items() for h in U[j]}
    return mvi,out,ov,{id(h):ob[k] for k,u in enumerate(U) for h in u}
for tn,T in PT.items():
    hc=T.get("hard_cores",[]); tg=[h for h in hc if h["module"] in GROW]
    if not tg: continue
    snap=copy.deepcopy(hc)
    def restore():
        for h,o in zip(hc,snap): h.clear(); h.update(copy.deepcopy(o))
    def excess(out):
        H=T["outline_um"][1]; return sum(max(0,-b_[1])+max(0,b_[3]-H) for _,_,b_ in out)
    DIR=dict(GROW); mv,out,ov,ob=place(tn,T,hc,tg,DIR); tries=0
    # greedy per rigid unit: flip one grown unit's direction (nearest the overflow edge first), keep it if the overflow drops
    if out:
        TU=[u for u in units(copy.deepcopy(snap)) if any(h["module"] in GROW for h in u)]
        names=[[h["inst"] for h in u if h["module"] in GROW] for u in TU]
        yc=[ubox(u)[1] for u in TU]
        best=excess(out)
        for rnd in range(3):
            if not out: break
            top=sum(max(0,b_[3]-T["outline_um"][1]) for _,_,b_ in out)>=sum(max(0,-b_[1]) for _,_,b_ in out)
            order=sorted(range(len(TU)),key=lambda k:-yc[k] if top else yc[k])
            for k in order:
                cur=DIR.get(names[k][0],GROW[[h for h in TU[k] if h["module"] in GROW][0]["module"]])[1]
                trial=dict(DIR); fl="down" if cur=="up" else "up"
                for g in TU[k]:
                    if g["module"] in GROW: trial[g["inst"]]=(GROW[g["module"]][0],fl)
                restore(); m2,o2,v2,b2=place(tn,T,hc,tg,trial); tries+=1
                if excess(o2)<best-EPS and not v2:
                    DIR=trial; best=excess(o2); mv,out,ov,ob=m2,o2,v2,b2
                    if not out: break
        restore(); mv,out,ov,ob=place(tn,T,hc,tg,DIR)
        REP.setdefault("dir_trials",{})[tn]=tries
    REP.setdefault("dirs",{})[tn]={g["inst"]:DIR.get(g["inst"],DIR[g["module"]])[1] for g in tg if DIR.get(g["inst"],DIR[g["module"]])[1]!=GROW[g["module"]][1]}
    for i,s_ in mv.items(): moved[(tn,i)]=s_
    if out: REP.setdefault("out_of_type",[]).extend(out)
    if ov: REP.setdefault("overlaps",{})[tn]=ov
for (tn,i),s in moved.items():
    h=[x for x in PT[tn]["hard_cores"] if x["inst"]==i][0]
    if h["module"] not in GROW: h["note"]=(h.get("note","")+" | ev74: pushed %+.2f um in y by the ra/rb/opsb/topk growth"%s).strip(" |")
REP["pushed"]=len([k for k in moved if [x for x in PT[k[0]]["hard_cores"] if x["inst"]==k[1]][0]["module"] not in GROW])
REP["pushed_by_type"]={}
for (tn,i),s in moved.items(): REP["pushed_by_type"].setdefault(tn,[]).append([i,s])
# (4) L29_i
n=0
for tn,T in PT.items():
    for b in T.get("buses",[]) or []:
        if tn.startswith("q_sm0") and b["name"]=="L29_i":
            assert abs(b["window_um"][0]-3975.376)<1e-3, b; b["window_um"]=[round(v+69.168,3) for v in b["window_um"]]; n+=1
            fb=[(o["name"],o["window_um"]) for o in T["buses"] if o is not b and o["face"]=="S" and min(o["window_um"][1],b["window_um"][1])>max(o["window_um"][0],b["window_um"][0])]
            assert not fb, fb
REP["L29_i_types"]=n
# (4b) the d44v L29 last hop is q_su01 ft_slot L29x1 (S->N) -> q_sm0 L29_i: its N out_window moves by the same +69.168 (schema port L29_1/L29m_1)
def nface(T,face):
    w=[(b["name"],b["window_um"]) for b in T.get("buses",[]) or [] if b.get("face")==face and b.get("window_um")]
    for f in T.get("ft_slots",[]) or []:
        if f.get("in_face")==face: w.append((f["name"]+".in",f["in_window_um"]))
        if f.get("out_face")==face: w.append((f["name"]+".out",f["out_window_um"]))
    return w
n=0
for tn,T in PT.items():
    for f in T.get("ft_slots",[]) or []:
        if tn.startswith("q_su01") and f["name"]=="L29x1":
            assert f["out_face"]=="N" and abs(f["out_window_um"][0]-9.616)<1e-3, f["out_window_um"]
            f["out_window_um"]=[round(v+69.168,3) for v in f["out_window_um"]]; n+=1; w=f["out_window_um"]
            fb=[x for x in nface(T,"N") if x[0]!="L29x1.out" and min(x[1][1],w[1])>max(x[1][0],w[0])]
            assert not fb, (tn,fb)
REP["L29x1_ft_types"]=n
# (5) xcal rst_n
XF="cores/ot_hbm_svc_sm_xcal_rel_t__241.92x224.64__canon.json"; P=ldpins(XF); K=json.loads((kp/"xcal.json").read_text())["pins"]
r=[q for q in P if q["name"]=="rst_n"][0]; assert (r["x"],r["y"])==(121.032,112.32); r["y"]=224.544
kd={q["name"]:(q["layer"],round(q["x"],3),round(q["y"],3)) for q in K}; pd_={q["name"]:(q["layer"],round(q["x"],3),round(q["y"],3)) for q in P}
REP["xcal_vs_signed_kit_pins_diff"]=[k for k in set(kd)|set(pd_) if kd.get(k)!=pd_.get(k)]
XN="cores/ot_hbm_svc_sm_xcal_rel_t__241.92x224.64__canon__ev74rst.json"; (pd/XN).write_text(json.dumps(P,indent=1)+"\n"); nx=0
for T in PT.values():
    for h in T.get("hard_cores",[]):
        if h["pins_file"]==XF: h["pins_file"]=XN; nx+=1; h["note"]=(h.get("note","")+" | ev74: rst_n at signed DB position (121.032,224.544)").strip(" |")
REP["xcal_insts"]=nx
# kit pin check ra/rb
for m,f in (("ot_hbm_idx_score_hcol_h0_ra","ra_tall"),("ot_hbm_idx_score_hcol_h0_rb","rb_tall")):
    a={q["name"]:(q["layer"],round(q["x"],3),round(q["y"],3)) for q in json.loads((pd/newpf[m]).read_text())}
    b={q["name"]:(q["layer"],round(q["x"],3),round(q["y"],3)) for q in json.loads((kp/(f+".json")).read_text())["pins"]}
    REP.setdefault("kit_pin_diff",{})[m]=len([k for k in set(a)|set(b) if a.get(k)!=b.get(k)])
# core_macros rows
CM=json.loads((pd/"core_macros.json").read_text())
def respace(e,gap=None,extra=None,nh=None):
    ys=sorted({round(m["rect_um"][1],3) for m in e["macros"]}); sh={}
    for i,y in enumerate(ys):
        if gap is not None:
            if i==0: sh[y]=0.0
            else:
                pt=max(m["rect_um"][3] for m in e["macros"] if round(m["rect_um"][1],3)==ys[i-1])+sh[ys[i-1]]
                ny=math.ceil((pt+gap)/0.27-1e-9)*0.27; sh[y]=round(ny-y,4)
        else: sh[y]=round(i*extra/(len(ys)-1),4)
    for m in e["macros"]:
        s=sh[round(m["rect_um"][1],3)]; r=m["rect_um"]; m["rect_um"]=[r[0],round(r[1]+s,4),r[2],round(r[3]+s,4)]
    e["outline_um"]=[e["outline_um"][0],nh]; return sh
REP["opsb_rows"]=respace(CM["cores"]["ot_hgi_sfu_opsb_output"],gap=21.6,nh=280.8)
REP["topk_rows"]=respace(CM["cores"]["ot_hbm_idx_topk_link_static"],extra=35.64,nh=535.68)
(pd/"core_macros.json").write_text(json.dumps(CM,indent=1)+"\n")
(pd/"die_plan.json").write_text(json.dumps(D,indent=1)+"\n")
(pd/"ev74_event.json").write_text(json.dumps(dict(schema="opentallas.hbm_plan_event.ev74",rulings="COORD 11-05 12:38 (5), 12:40 (1)(2), 12:4x xcal rst_n",report=REP),indent=1)+"\n")
print(json.dumps({k:(v if k not in("pushed_by_type",) else {t:len(x) for t,x in v.items()}) for k,v in REP.items()},indent=0)[:4000])
