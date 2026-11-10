# HBM-COLLECT-1 SF-SPLIT 11-10: apply the static_front east/west split plan event to a COPY of the HBM wave plan.
# u_sm_front_nf (ot_smh_static_front 1814.4 x 233.28) -> u_sm_front_nfw (ot_smh_static_front_w 907.2 x 233.28, same
# origin) + u_sm_front_nfe (ot_smh_static_front_e, origin + 907.2 um). The parent keeps ot_smh_static_front as a
# zero-logic wrapper (two instances + per-half bit maps), so parent nets and outer pin positions are unchanged.
import json,sys,os,copy,hashlib,subprocess,re
BASE,NEW,KW,KE,EVOUT=sys.argv[1:6]
subprocess.check_call(["cp","-a",BASE,NEW])
dp=json.load(open(NEW+"/die_plan.json"))
KITS={"W":KW,"E":KE}; MOD={"W":"ot_smh_static_front_w","E":"ot_smh_static_front_e"}; XC=907.2
pinsfile={}
for H in "WE":
    pj=json.load(open(KITS[H]+"/pins.json"));fz=json.load(open(KITS[H]+"/freeze.json"))
    orig={re.sub(r"\[\d+\]$","",p["name"]):p["dir"] for p in json.load(open(BASE+"/cores/ot_smh_static_front__1814.4x233.28__smab1108.json"))}
    out=[]
    for p in pj:
        n=p["bus"] if p.get("bit") is None else "%s[%d]"%(p["bus"],p["bit"])
        d=orig.get(p["bus"]) or ("output" if p["bus"]==fz["split_derived"]["seam_out"] else "input")
        out.append({"name":n,"layer":p["layer"],"x":p["x"],"y":p["y"],"dir":d})
    rel="cores/%s__907.2x233.28__sfs1110.json"%MOD[H]; json.dump(out,open(NEW+"/"+rel,"w")); pinsfile[H]=(rel,len(out))
changed=[]
for T in ("q_sm0","q_sm1","q_sm2","q_sm3"):
    t=dp["partition_types"][T]
    i=[k for k,h in enumerate(t["hard_cores"]) if h["inst"]=="u_sm_front_nf"]; assert len(i)==1; i=i[0]
    h=t["hard_cores"][i]; assert h["outline_um"]==[1814.4,233.28]
    new=[]
    for H in "WE":
        g=copy.deepcopy(h); g["inst"]="u_sm_front_nf"+H.lower(); g["module"]=MOD[H]; g["physical_master"]=MOD[H]
        g["origin_um"]=[round(h["origin_um"][0]+(0 if H=="W" else XC),4),h["origin_um"][1]]; g["outline_um"]=[907.2,233.28]
        g["pins_file"]=pinsfile[H][0]; g["physical_inst"]=h["physical_inst"]+".u_"+H.lower()
        g["note"]="SF-SPLIT 11-10 (HBM-COLLECT-1, COORD form b): %s half of ot_smh_static_front, cut x 907.2, launch-registered seam, 0 pin cycles; was: %s"%(H,h["note"][:120])
        if H=="E": g["reset_from_master"]={"kind":"internal","content":"u_sm","source":"SF-SPLIT: the E half has no rst_n port; its resets are launch-registered seam_w2e bits from the W half reset relays (as built in SF-C); no reset pin (pin omitted)"}
        new.append(g)
    t["hard_cores"][i:i+1]=new
    taps=t["clock"]["taps"]; j=[k for k,x in enumerate(taps) if x["name"]=="u_sm_front_nf"]; assert len(j)==1; j=j[0]; tp=taps[j]
    nt=[]
    for H,g in zip("WE",new):
        x=copy.deepcopy(tp); x["name"]=g["inst"]; x["budget_owner"]=MOD[H]; x["xy"]=[round(g["origin_um"][0]+453.6,4),tp["xy"][1]]
        x["note"]="SF-SPLIT 11-10: half centre clock entry (453.6, 116.64 in the half frame)"; nt.append(x)
    taps[j:j+1]=nt; changed.append(T)
json.dump(dp,open(NEW+"/die_plan.json","w"),indent=1)
ce=json.load(open(NEW+"/clock_entries.json"))
for T in changed:
    e=ce[T].pop("u_sm_front_nf")
    for H in "WE":
        x=copy.deepcopy(e); x["xy_um"]=[453.6,116.64]; x["island_um"]=[449.28,112.32,457.92,120.96]; x["tap"]="u_sm_front_nf"+H.lower()
        x["module"]=x["native_module"]=MOD[H]; x["source"]+=" | SF-SPLIT 11-10 half centre"; ce[T]["u_sm_front_nf"+H.lower()]=x
json.dump(ce,open(NEW+"/clock_entries.json","w"),indent=1)
cr=json.load(open(NEW+"/core_clock_regions.json")); m=cr["modules"]["ot_smh_static_front"]
for H in "WE":
    ents=[r for r in m["regional_entries"] if (r["xy_um"][0]<XC)==(H=="W")]
    ents=[{"xy_um":[round(r["xy_um"][0]-(0 if H=="W" else XC),2),r["xy_um"][1]],"region_um":[round(r["region_um"][0]-(0 if H=="W" else XC),2),r["region_um"][1],round(r["region_um"][2]-(0 if H=="W" else XC),2),r["region_um"][3]]} for r in ents]
    x=copy.deepcopy(m); x["regional_entries"]=ents; x["entries"]=len(ents); x["grid"]=[6,2]; x["sinks"]=None; x["sinks_per_entry"]=None; x["note"]="SF-SPLIT 11-10 half of ot_smh_static_front (sinks re-measured by the half build)"
    cr["modules"][MOD[H]]=x
json.dump(cr,open(NEW+"/core_clock_regions.json","w"),indent=1)
cm=json.load(open(NEW+"/core_macros.json"))
for H in "WE":
    x=copy.deepcopy(cm["cores"]["ot_smh_static_front"]); x["outline_um"]=[907.2,233.28]; x["basis"]="SF-SPLIT 11-10: no macros (as the parent)"; cm["cores"][MOD[H]]=x
json.dump(cm,open(NEW+"/core_macros.json","w"),indent=1)
for f in ("die_plan.json","clock_entries.json"):
    if os.path.exists(NEW+"/"+f+".gz"): subprocess.check_call("gzip -n -c %s/%s > %s/%s.gz"%(NEW,f,NEW,f),shell=True)
if os.path.exists(NEW+"/SHA256SUMS"):
    subprocess.check_call("cd %s && sha256sum -c --quiet SHA256SUMS >/dev/null 2>&1; awk '{print $2}' SHA256SUMS | sed 's/^\\*//' > .sfs_list; for f in %s; do grep -qx \"$f\" .sfs_list || echo $f >> .sfs_list; done; xargs -a .sfs_list sha256sum > SHA256SUMS.new && mv SHA256SUMS.new SHA256SUMS && rm .sfs_list"%(NEW," ".join(pinsfile[H][0] for H in "WE")),shell=True)
ev={"schema":"opentallas.hbm_plan_event.v1","event":"sfs1110","lane":"HBM-COLLECT-1 (SF-SPLIT)","status":"READY DO_NOT_COUNT (die-local)",
 "base_plan":BASE,"base_plan_sha256":hashlib.sha256(open(BASE+"/die_plan.json","rb").read()).hexdigest(),
 "new_plan":NEW,"new_plan_sha256":hashlib.sha256(open(NEW+"/die_plan.json","rb").read()).hexdigest(),
 "types":changed,"parent_core":"ot_smh_static_front","parent_outline_um":[1814.4,233.28],"cut_x_um":XC,"pin_cycles_added":0,
 "children":{MOD[H]:{"inst":"u_sm_front_nf"+H.lower(),"outline_um":[907.2,233.28],"origin_in_parent_um":[0.0 if H=="W" else XC,0.0],"pins_file":pinsfile[H][0],"pin_count":pinsfile[H][1],
   "kit":KITS[H],"kit_hash":json.load(open(KITS[H]+"/freeze.json"))["kit_hash"]} for H in "WE"},
 "wrapper":"ot_smh_static_front = u_w + u_e + per-half bit maps (split3/ot_smh_static_front_split.v), parent RTL/pins unchanged"}
json.dump(ev,open(EVOUT,"w"),indent=1); print(json.dumps({k:ev[k] for k in ("new_plan_sha256","types")}),pinsfile)
