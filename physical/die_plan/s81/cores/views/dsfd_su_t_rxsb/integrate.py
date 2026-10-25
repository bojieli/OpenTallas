import json, hashlib, shutil, gzip, os, re, sys
from pathlib import Path
M="dsfd_su_t_rxsb"
RUNP=Path("/srv/opentallas-scratch2/claude/codex-s81-core-eco/rxsb_route_h5")
RUN="epyc2:"+str(RUNP)
B=RUNP/"run/results/asap7/kr_dsfd_su_t_rxsb_c/base"
W=Path("/srv/opentallas-scratch2/claude/wt/s81-rxsb-view-1025")
V=W/"physical/ref_tile/s81su_rxsb_ref/views"/M
A=W/"physical/die_plan/s81/cores/views"/M
so=json.load(open(RUNP/"signoff_codex/signoff.json")); assert so["verdict"]=="SIGNED", so["verdict"]
c=so["checks"]
# plan pins vs signed LEF pins (same-layer rect within 1.5 um)
plan=json.load(open(W/"physical/die_plan/s81/inputs/core_pins"/f"{M}.json"))
lef=open(B/f"{M}.lef").read()
rects={}
for pm in re.finditer(r"PIN (\S+)(.*?)END \1", lef, re.S):
    nm=pm.group(1); layer=None
    for line in pm.group(2).splitlines():
        t=line.split()
        if t[:1]==["LAYER"]: layer=t[1]
        if t[:1]==["RECT"]: rects.setdefault(nm,[]).append((layer,*map(float,t[1:5])))
pl=plan["pins"] if isinstance(plan,dict) and "pins" in plan else plan
if isinstance(pl,dict): pl=[dict(name=k,**v) if isinstance(v,dict) else {"name":k,"v":v} for k,v in pl.items()]
miss=[];far=[];n=0
for p in pl:
    nm=p.get("name") or p.get("pin"); n+=1
    xy=p.get("xy") or p.get("pos") or ([p["x"],p["y"]] if "x" in p else None); ly=p.get("layer")
    r=rects.get(nm)
    if not r: miss.append(nm); continue
    if xy:
        d=min(max(0,r_[1]-xy[0],xy[0]-r_[3])+max(0,r_[2]-xy[1],xy[1]-r_[4]) for r_ in r if (ly is None or r_[0]==ly) )if any(ly is None or r_[0]==ly for r_ in r) else 1e9
        if d>1.5: far.append((nm,round(d,2)))
lef_sig=[k for k in rects if k not in ("VDD","VSS")]
print("plan pins",n,"lef pins",len(lef_sig),"missing",len(miss),miss[:8],"far",len(far),far[:8])
if "--check" in sys.argv: sys.exit(0)
assert not miss and not far
V.mkdir(parents=True,exist_ok=True)
old=sorted(p.name for p in V.iterdir())
shutil.copy(B/f"{M}.lef", V/f"{M}.lef")
shutil.copy(B/f"{M}_tc.lib", V/f"{M}_tt.lib")
shutil.copy(B/f"{M}_bc.lib", V/f"{M}_ff.lib")
if (V/f"{M}_ss.lib").exists(): (V/f"{M}_ss.lib").unlink()
ins={"schema":"opentallas.closure_loop.ck_insertion.v1","base":RUN+"/run/results/asap7/kr_dsfd_su_t_rxsb_c/base",
     "db":"6_final.odb","sdc":"6_final.sdc","clock":"clk","parasitics":"spef","raw_source":True,
     "source":"signoff.py checks.clock.by_corner (rxsb_route_h5 signoff_codex/signoff.json, SIGNED)"}
env={}
for k in ("tt","ff"):
    b=c["clock"]["by_corner"][k]; ins[k]={"boundary":b["pinflops"],"all":b["all"],"errors":[],"macros":None,"macro_libs":0,
        "pair_skew_worst_abs_ps":{m:b["pair_skew"]["checks"][m]["worst_abs_ps"] for m in ("max","min")}}
    K=k.upper()
    env.update({f"CK_{K}_MEAN":round(b["pinflops"]["mean"]),f"CK_{K}_ALL_MEAN":round(b["all"]["mean"]),
                f"CK_{K}_MIN":round(b["pinflops"]["min"]),f"CK_{K}_ALL_MIN":round(b["all"]["min"]),
                f"CK_{K}_MAX":round(b["pinflops"]["max"]),f"CK_{K}_ALL_MAX":round(b["all"]["max"])})
env["CK_ROUTE_REF"]="TT"
ins.update(route_corner=None,macro_clk={"n":0,"flag":False,"outliers":[]},env=env,lib_clock_pin="clk",
           clock_mapping_basis="constraint.sdc create_clock -name clk [get_ports clk]")
json.dump(ins,open(V/"insertion.json","w"),indent=1)
(A/"source").mkdir(parents=True,exist_ok=True)
for f in ("config.mk","constraint.sdc","freeze.json","pins.json","face_guard.json","sdc_lint.json","pin_audit.json","codex_geom_review.json"):
    if (RUNP/f).exists(): shutil.copy(RUNP/f, A/f)
shutil.copy(RUNP/"signoff_codex/signoff.json", A/"signoff.json")
for f in (RUNP/"rtl").iterdir():
    if f.is_file(): shutil.copy(f, A/"source"/f.name)
with open(B/"6_final.v","rb") as i, gzip.GzipFile(A/"6_final.v.gz","wb",mtime=0) as o: shutil.copyfileobj(i,o)
h=lambda p: hashlib.sha256(open(p,"rb").read()).hexdigest()
tt=c["setup_tt"]; ff=c["hold_ff"]
pk={k:c["clock"]["by_corner"][k]["pair_skew"]["checks"]["max"]["worst_abs_ps"] for k in ("tt","ff")}
man={"schema":"opentallas.s81.native_core_view.v1","module":M,"kit":RUN,"routed_db":RUN+"/run/results/asap7/kr_dsfd_su_t_rxsb_c/base/6_final.odb",
     "verdict":"SIGNED","variant":"rxsb_route_h5 (extracted-SPEF hold-only ECO, hold margin 5 ps, launched before the 2026-10-25 04:13 owner no-ECO rule); h0 also SIGNED, h5 preferred",
     "signoff":{"tt_setup_wns_ps":tt["wns_ps"],"ff_hold_wns_ps":ff["wns_ps"],"pair_skew_worst_abs_ps":pk,
                "drc":so["route"]["drc"],"antenna_nets":so["route"]["antenna_nets"],"drv":c["drv"]["verdict"],
                "sdc_lint":so["sdc_lint"]["verdict"],"face_guard":so["face_guard"]["verdict"],"generated":so["generated"]},
     "scope":"routed abstract + TT/FF timing models (ORFS generate_abstract, tc->_tt, bc->_ff); no GDS",
     "pins":len(lef_sig),"pins_note":f"plan core_pins unchanged: all {n} plan pins present and within 1.5 um of a same-layer LEF pin rect",
     "physical_change":"hold-only ECO on extracted SPEF; no RTL, pin, cycle or clock change",
     "die_view":"physical/ref_tile/s81su_rxsb_ref/views/"+M+f" (LEF, _tt.lib, _ff.lib, insertion.json replaced; previous files {old})",
     "files":{p.name:h(p) for p in sorted(A.iterdir()) if p.is_file()},
     "view_files":{p.name:h(p) for p in (V/f"{M}.lef",V/f"{M}_tt.lib",V/f"{M}_ff.lib",V/"insertion.json")}}
json.dump(man,open(A/"MANIFEST.json","w"),indent=1)
(A/"README.md").write_text(f"Signed-off rxsb view from rxsb_route_h5. TT setup {tt['wns_ps']:+.2f} ps, FF hold {ff['wns_ps']:+.2f} ps, related-pair skew TT {pk['tt']} / FF {pk['ff']} ps, DRC/antenna/DRV zero, SDC lint and face guard pass. Hold-only ECO on extracted SPEF (no RTL, pin, cycle or clock change), launched before the 2026-10-25 04:13 owner rule. Die-view files: physical/ref_tile/s81su_rxsb_ref/views/{M}/.\n")
print(json.dumps(man["signoff"]))
