#!/usr/bin/env python3
"""DIE-HBM-66 d44v part 16: HBM tail Sinkhorn on the row-pipelined core (COORD ruling A). mk_p16.py PLAN_DIR (plain die_plan.json, core_conns.json)
tailx_sk_step0 + tailx_sk_steady (2 tails, 4 instances, enable-behind 7-clk datapath, step0 sign-off TT -3846) -> one ot_hbm_hc_root_static__tailx_sk_fsr per tail in the step0 slot.
Steady slots are freed. Rest rows keep outline and pins under new module names (RTL delta: calendar). Taps, islands, budgets and core_conns follow. 43 name-conflated parent station rows of the old sk pins drop."""
import json,sys,copy
from pathlib import Path
pd=Path(sys.argv[1]); D=json.loads((pd/"die_plan.json").read_text()); CC=json.loads((pd/"core_conns.json").read_text())
R=D["partition_types"]["root"]; HC=R["hard_cores"]
STEP0="ot_hbm_hc_root_static__tailx_sk_step0"; STEADY="ot_hbm_hc_root_static__tailx_sk_steady"; FSR="ot_hbm_hc_root_static__tailx_sk_fsr"
RN={"ot_hbm_hc_root_static__tailx_rest__v6bc7f2":"ot_hbm_hc_root_static__tailx_rest_fsr__v6bc7f2","ot_hbm_hc_root_static__tailx_rest__v4f4566":"ot_hbm_hc_root_static__tailx_rest_fsr__v4f4566"}
PF="cores/ot_hbm_hc_root_static__tailx_sk_fsr__155.52x241.92__p16.json"
by={h["inst"]:h for h in HC}
s0=by["u_hc_eng_tail0_sk_step0"]; old=json.loads((pd/s0["pins_file"]).read_text())
ck=[p for p in old if p["name"]=="clk"]
if len(old)!=1031 or len(ck)!=1: raise SystemExit("step0 table not as read")
m4=sorted({p["y"] for p in old if p["layer"]=="M4"}); y0=m4[0]; pitch=min(b-a for a,b in zip(m4,m4[1:]))
xw=min(p["x"] for p in old if p["layer"]=="M4")
rest=json.loads((pd/by["u_hc_eng_tail0_rest"]["pins_file"]).read_text())
def order(nm):
    v=[p for p in rest if p["name"].startswith(nm+"[")]
    if len(v)!=512: raise SystemExit("rest bus "+nm)
    return [int(p["name"].split("[")[1][:-1]) for p in sorted(v,key=lambda p:p["x"])]
T=[dict(ck[0])]; n=0
def put(name):
    global n
    T.append(dict(name=name,layer="M4",x=xw,y=round(y0+n*pitch,3))); n+=1
step=max(1,round(0.192/pitch)); 
pitch=pitch*step
for i in order("x_g_tail_0_u_t_u_tail_sink_y"): put(f"y[{i}]")
for c in ("fault","out_valid","in_ready","in_valid","rst_n"): put(c)
for i in order("x_g_tail_0_u_t_u_tail_sink_in_e"): put(f"in_e[{i}]")
top=T[-1]["y"]
if top>241.92-8: raise SystemExit(f"table overflow {top}")
(pd/PF).write_text(json.dumps(T))
new=[]; 
for h in HC:
    if h["module"]==STEADY: continue
    if h["module"]==STEP0:
        t=h["inst"][len("u_hc_eng_tail")]; sd=by[f"u_hc_eng_tail{t}_sk_steady"]; h=dict(h)
        h["inst"]=f"u_hc_eng_tail{t}_sk_fsr"; h["module"]=FSR; h["pins_file"]=PF
        if "reset_from_master" in sd: h["reset_from_master"]=sd["reset_from_master"]
        h["note"]="part 16: row Sinkhorn core, one per tail, step0 slot; steady slot freed"
    elif h["module"] in RN: h=dict(h,module=RN[h["module"]])
    new.append(h)
R["hard_cores"]=new
IN={"u_hc_eng_tail0_sk_step0":"u_hc_eng_tail0_sk_fsr","u_hc_eng_tail1_sk_step0":"u_hc_eng_tail1_sk_fsr"}
def ren(s):
    for a,b in IN.items(): s=s.replace(a,b)
    s=s.replace(STEP0,FSR)
    for a,b in RN.items(): s=s.replace(a,b)
    return s
def walk(o):
    if isinstance(o,dict): return {ren(k):walk(v) for k,v in o.items()}
    if isinstance(o,list): return [walk(x) for x in o if not (isinstance(x,dict) and "_sk_steady" in json.dumps(x))]
    return ren(o) if isinstance(o,str) else o
ns=[x for x in R["internal_stations"] if not any(k in x["conn"] for k in ("_sk_step0","_sk_steady","tail_sink_","sk_en_sk"))]
drop=len(R["internal_stations"])-len(ns); R["internal_stations"]=ns
# typed fault endpoints (launch==capture) stay: re-point at the row core's fault pin
_fp=[p for p in T if p["name"]=="fault"][0]
for x in ns:
    if "_sk_steady" in x.get("launch",""):
        t=x["launch"][len("u_hc_eng_tail")]; h=[q for q in new if q["inst"]==f"u_hc_eng_tail{t}_sk_fsr"][0]
        x["from_um"]=[round(h["origin_um"][0]+_fp["x"],3),round(h["origin_um"][1]+_fp["y"],3)]
        for k in ("launch","capture","note"): x[k]=x[k].replace(f"u_hc_eng_tail{t}_sk_steady",f"u_hc_eng_tail{t}_sk_fsr")
R["clock"]=walk(R["clock"])
ci=D["clock"]["mesh"]["core_islands"]; ci.pop(STEADY); D["clock"]=walk(D["clock"])
for k in ("budgets","latency","census","latency_groups","lanes"):
    if k in D: D[k]=walk(D[k])
C=CC["root"]
for t in (0,1):
    g=f"x_g_tail_{t}_u_t_u_tail_"; ri=f"u_hc_eng_tail{t}_rest"; f=f"u_hc_eng_tail{t}_sk_fsr"
    fault=[x for x in C[f"u_hc_eng_tail{t}_sk_steady"].get("fault",[]) if x.startswith("bus:")]
    C.pop(f"u_hc_eng_tail{t}_sk_step0"); C.pop(f"u_hc_eng_tail{t}_sk_steady")
    C[f]=dict(clk=[f"tap:{f}"],rst_n=[f"core:{ri}"] if False else [],in_e=[f"core:{ri}"],in_valid=[f"core:{ri}"],in_ready=[f"core:{ri}"],out_valid=[f"core:{ri}"],y=[f"core:{ri}"],fault=[f"core:{ri}"]+fault)
    C[f].pop("rst_n")
    r=C[ri]
    r.pop(g+"sk_en_sk",None)
    for p in ("in_e","in_valid","in_ready","out_valid","fault","y"): r[g+"sink_"+p]=[f"core:{f}"]
txt=json.dumps(D)
for bad in ("_sk_step0","_sk_steady","tailx_rest__"):
    if bad in txt: print("LEFT",bad,txt.count(bad))
(pd/"die_plan.json").write_text(json.dumps(D,indent=1)+"\n"); (pd/"core_conns.json").write_text(json.dumps(CC))
(pd/"part16_event.json").write_text(json.dumps(dict(schema="opentallas.hbm_plan_event.part16",hard_cores=len(new),stations_dropped=drop,pins_file=PF,pins=len(T),fsr_top_pin_y=top,latency=dict(tail_launch_to_result_edges=[592,1054],sink_edges=[312,774],measured="results/die_hbm_1105/sk_fsr"))))
print("part 16 hard_cores",len(new),"stations dropped",drop,"pins",len(T),"top y",top,"m4 y0",y0,"pitch",pitch,"xw",xw)
