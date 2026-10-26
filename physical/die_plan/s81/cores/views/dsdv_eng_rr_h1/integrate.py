import json, hashlib, shutil, gzip
from pathlib import Path
# S81-CORES/C3 2026-10-25: publish the signed-off dsdv_eng_rr_h1 view (hcpost h5 convention, main b47cbeab2)
K=Path("/srv/opentallas-scratch2/claude/s81-kits/c3/dsdv_eng_rr_h1_c")
W=Path("/srv/opentallas-scratch2/claude/wt/s81-engh1-view-1025")
M="dsdv_eng_rr_h1"; NICK="kr_dsdv_eng_rr_h1_c"
RUN="epyc2:"+str(K)
B=K/"run/results/asap7"/NICK/"base"
SO=K/"signoff_cur"       # current main tools/die_plan/signoff.py (794550c82), pair skew + CPPR
V=W/"physical/ref_tile"/M/"views"/M
A=W/"physical/die_plan/s81/cores/views"/M
so=json.load(open(SO/"signoff.json")); assert so["verdict"]=="SIGNED", so["reasons"]
c=so["checks"]
shutil.copy(B/f"{M}.lef", V/f"{M}.lef")
shutil.copy(B/f"{M}_tc.lib", V/f"{M}_tt.lib")
shutil.copy(B/f"{M}_bc.lib", V/f"{M}_ff.lib")
ins={"schema":"opentallas.closure_loop.ck_insertion.v1","base":RUN+"/run/results/asap7/"+NICK+"/base",
     "db":"6_final.odb","sdc":"6_final.sdc","clock":"ck","parasitics":"spef","raw_source":True,
     "source":"signoff.py checks.clock.by_corner (dsdv_eng_rr_h1_c signoff_cur/signoff.json, SIGNED, main tool 794550c82)"}
env={}
ps={}
for k in ("tt","ff"):
    b=c["clock"]["by_corner"][k]; ps[k]=max(b["pair_skew"]["checks"][m]["worst_abs_ps"] for m in ("max","min"))
    ins[k]={"boundary":b["pinflops"],"all":b["all"],"errors":[],"macros":None,"macro_libs":0,
        "pair_skew_worst_abs_ps":{m:b["pair_skew"]["checks"][m]["worst_abs_ps"] for m in ("max","min")}}
    K_=k.upper()
    env.update({f"CK_{K_}_MEAN":round(b["pinflops"]["mean"]),f"CK_{K_}_ALL_MEAN":round(b["all"]["mean"]),
                f"CK_{K_}_MIN":round(b["pinflops"]["min"]),f"CK_{K_}_ALL_MIN":round(b["all"]["min"]),
                f"CK_{K_}_MAX":round(b["pinflops"]["max"]),f"CK_{K_}_ALL_MAX":round(b["all"]["max"])})
env["CK_ROUTE_REF"]="TT"
ins.update(route_corner=None,macro_clk={"n":0,"flag":False,"outliers":[]},env=env,lib_clock_pin="ck",
           clock_mapping_basis="constraint.sdc create_clock -name clk [get_ports ck]")
json.dump(ins,open(V/"insertion.json","w"),indent=1)
(A/"source").mkdir(parents=True,exist_ok=True)
shutil.copy(SO/"signoff.json", A/"signoff.json")
for f in ("config.mk","constraint.sdc","freeze.json","pins.json","pins_snapped.json","face_guard.json","sdc_lint.json","pin_audit.json"):
    shutil.copy(K/f, A/f)
shutil.copy(SO/"tt/pair_skew.tsv", A/"pair_skew_tt.tsv"); shutil.copy(SO/"ff/pair_skew.tsv", A/"pair_skew_ff.tsv")
for f in (K/"rtl").iterdir(): shutil.copy(f, A/"source"/f.name)
with open(B/"6_final.v","rb") as i, gzip.GzipFile(A/"6_final.v.gz","wb",mtime=0) as o: shutil.copyfileobj(i,o)
h=lambda p: hashlib.sha256(open(p,"rb").read()).hexdigest()
tt=c["setup_tt"]; ff=c["hold_ff"]
man={"schema":"opentallas.s81.native_core_view.v1","module":M,"kit":RUN,"routed_db":RUN+"/run/results/asap7/"+NICK+"/base/6_final.odb",
     "verdict":"SIGNED","variant":"dsdv_eng_rr_h1_c (C3 kits_repin recipe; no ECO)",
     "signoff":{"tt_setup_wns_ps":tt["wns_ps"],"ff_hold_wns_ps":ff["wns_ps"],"pair_skew_worst_abs_ps":ps,
                "drc":so["route"]["drc"],"antenna_nets":so["route"]["antenna_nets"],"drv":c["drv"]["verdict"],
                "sdc_lint":so["sdc_lint"]["verdict"],"generated":so["generated"]},
     "scope":"routed abstract + TT/FF timing models (ORFS generate_abstract, tc->_tt, bc->_ff); no GDS",
     "pins":645,"source_note":"source/ = kit rtl, byte-identical to main rtl/dsrom_sys/s81_dv/eng/dsdv_eng_rr_split.sv and rtl/dsrom_sys/engram/static_lookup_1015/ot_s81_engram_hash_n32{,_layer}.sv",
     "physical_change":"none (flow route, no ECO)",
     "die_view":"physical/ref_tile/"+M+"/views/"+M+" (LEF, _tt.lib, _ff.lib, insertion.json)",
     "files":{p.name:h(p) for p in sorted(A.iterdir()) if p.is_file() and p.name not in ("MANIFEST.json","README.md")},
     "view_files":{p.name:h(p) for p in (V/f"{M}.lef",V/f"{M}_tt.lib",V/f"{M}_ff.lib",V/"insertion.json")}}
json.dump(man,open(A/"MANIFEST.json","w"),indent=1)
(A/"README.md").write_text(f"Signed-off dsdv_eng_rr_h1 view from {RUN} (re-signed off with the current main signoff.py). TT setup {tt['wns_ps']:+.2f} ps, FF hold {ff['wns_ps']:+.2f} ps, related-pair skew TT {ps['tt']:.1f} / FF {ps['ff']:.1f} ps, DRC/antenna/DRV zero, SDC lint and face guard pass. Plain flow route, no ECO. The die-view files live in physical/ref_tile/{M}/views/{M}/. This archive holds the sign-off record, kit inputs, the exact source in source/ and the gzipped routed netlist.\n")
print(json.dumps(man["signoff"]))
