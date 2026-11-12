import json,subprocess,shutil,os,sys,copy
E="/srv/opentallas-scratch2/claude/hbm-cut-1111/"
SRC=E+"compose/t21d/"; OUT=E+"compose/"+(sys.argv[2] if len(sys.argv)>2 else "t23")+"/"
shutil.rmtree(OUT,ignore_errors=True)
subprocess.check_call(["cp","-al",SRC.rstrip("/"),OUT.rstrip("/")])
for f in ("die_plan.json","die_plan.json.gz","SHA256SUMS"):
    if os.path.exists(OUT+f): os.remove(OUT+f)
p=json.load(open(SRC+"die_plan.json")); pt=p["partition_types"]
G="/srv/opentallas-scratch2/claude/wt/hbm-cut-1111"
def gshow(path): return subprocess.check_output(["git","-C",G,"show","origin/main:"+path])
N4="ot_hnx_fused_hub_n4ext__293.76x250.56__n4rf.json"; SW="ot_wbq_sw__233.28x544.32__wsw15.json"
open(OUT+"cores/"+N4,"wb").write(gshow("physical/die_plan/hbm/n4ext_1110/"+N4))
open(OUT+"cores/"+SW,"wb").write(gshow("physical/die_plan/hbm/plan_of_record/d44v_wsw15_1109/cores/"+SW))
changed=set(); log=[]
def core(tn,inst): return [c for c in pt[tn]["hard_cores"] if c["inst"]==inst][0]
# (1)
EX="cores/ot_hbm_su_pg_lane_exp_x_core__328.32x207.36__d44v_expx328.json"
for tn in ("q_su00","q_su10","q_su00__physical_v1","q_su10__physical_v1"):
    for c in pt[tn]["hard_cores"]:
        if c["module"]=="ot_hbm_su_pg_lane_exp_x_core" and c["outline_um"]==[319.68,207.36]:
            c["outline_um"]=[328.32,207.36]; c["pins_file"]=EX; changed.add(tn); log.append((tn,c["inst"],"lane_exp 328.32"))
# (2)
c=core("root","u_mu_fused_root"); c["outline_um"]=[293.76,250.56]; c["pins_file"]="cores/"+N4; changed.add("root")
for s in pt["root"]["internal_stations"]:
    if s["capture"].startswith("u_mu_fused_root.") and s["to_um"][0]==950.4:
        s["to_um"][0]=1028.16; log.append(("root",s["conn"],"east to_um x 950.4->1028.16"))
# (3)
DY=float(sys.argv[1]) if len(sys.argv)>1 else -125.28
def bb(c): o=c["origin_um"];w,h=c["outline_um"];return (o[0],o[1],o[0]+w,o[1]+h)
def ov(a,b,m=0): return a[0]<b[2]+m and b[0]<a[2]+m and a[1]<b[3]+m and b[1]<a[3]+m
for tn in (("q_hub_nw","q_hub_ne") if (len(sys.argv)<=3 or sys.argv[3]!="no3") else ()):
    t=pt[tn]; changed.add(tn)
    for q,(x0,nx) in (("q0",(1080.0,1002.24)),("q1",(5330.88,5253.12))):
        sw=core(tn,f"u_wbk_Q__{q}__sw"); assert sw["origin_um"][0]==x0
        sw["origin_um"][0]=nx; sw["outline_um"]=[233.28,544.32]; sw["pins_file"]="cores/"+SW
    aq=core(tn,"u_xl_Q_aqhi"); aq["origin_um"][1]=round(aq["origin_um"][1]+DY,3)
    for s in t["internal_stations"]:
        a,b=s["conn"].split("|") if "|" in s["conn"] else (None,None)
        if b=="u_xl_Q_aqhi": s["to_um"][1]=round(s["to_um"][1]+DY,3)
        if a=="u_xl_Q_aqhi": s["from_um"][1]=round(s["from_um"][1]+DY,3)
    others=[x for x in t["hard_cores"] if x["inst"] not in ("u_xl_Q_aqhi",)]
    bad=[x["inst"] for x in others if ov(bb(aq),bb(x))]
    print(tn,"aqhi new bbox",[round(v,2) for v in bb(aq)],"overlaps",bad)
    for q in ("q0","q1"):
        sw=core(tn,f"u_wbk_Q__{q}__sw"); print(" sw",q,[round(v,2) for v in bb(sw)],"overlaps",[x["inst"] for x in t["hard_cores"] if x is not sw and ov(bb(sw),bb(x))])
    for s in t["internal_stations"]:
        if "u_xl_Q_aqhi" in s["conn"]:
            pts=[s["from_um"]]+s["regs_um"]+[s["to_um"]]
            hops=[abs(pts[i][0]-pts[i+1][0])+abs(pts[i][1]-pts[i+1][1]) for i in range(len(pts)-1)]
            if max(hops)>360: print("  hop>360",s["conn"],round(max(hops),1))
json.dump(p,open(OUT+"die_plan.json","w"),indent=1)
import gzip; gzip.open(OUT+"die_plan.json.gz","wt").write(json.dumps(p,indent=1))
print("changed types",sorted(changed)); print(len(log),"log")
