import json, hashlib, shutil, gzip, os
from pathlib import Path
S=Path("/srv/opentallas-scratch2/claude/s81-hcpost-h5-1025/stage")
W=Path("/srv/opentallas-scratch2/claude/wt/s81-hcpost-h5-1025")
M="ot_dsrom_su_hcpost_lane_pr"
RUN="epyc2:/srv/opentallas-scratch2/claude/codex-s81-core-eco/hcpost_route_h5"
V=W/"physical/ref_tile/s81sl_hcpl/views"/M
A=W/"physical/die_plan/s81/cores/views"/M
so=json.load(open(S/"signoff.json")); assert so["verdict"]=="SIGNED"
c=so["checks"]
# 1. die-view flow files (cores.find_views: <module>.lef, <module>_tt.lib, <module>_ff.lib)
shutil.copy(S/f"{M}.lef", V/f"{M}.lef")
shutil.copy(S/f"{M}_tc.lib", V/f"{M}_tt.lib")
shutil.copy(S/f"{M}_bc.lib", V/f"{M}_ff.lib")
(V/f"{M}_ss.lib").unlink()   # stale: prior closure-loop netlist; SS is sensitivity only, never sign-off
ins={"schema":"opentallas.closure_loop.ck_insertion.v1","base":RUN+"/run/results/asap7/kr_ot_dsrom_su_hcpost_lane_pr_c/base",
     "db":"6_final.odb","sdc":"6_final.sdc","clock":"clk","parasitics":"spef","raw_source":True,
     "source":"signoff.py checks.clock.by_corner (hcpost_route_h5 signoff_codex/signoff.json, SIGNED)"}
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
# 2. signed-off archive (VQ convention)
(A/"source").mkdir(parents=True,exist_ok=True)
for f in ("signoff.json","config.mk","constraint.sdc","freeze.json","pins.json","pins_snapped.json","face_guard.json",
          "sdc_lint.json","pin_audit.json","codex_geom_review.json","pair_skew_tt.tsv","pair_skew_ff.tsv"):
    shutil.copy(S/f, A/f)
for f in (S/"source").iterdir(): shutil.copy(f, A/"source"/f.name)
with open(S/"6_final.v","rb") as i, gzip.GzipFile(A/"6_final.v.gz","wb",mtime=0) as o: shutil.copyfileobj(i,o)
h=lambda p: hashlib.sha256(open(p,"rb").read()).hexdigest()
tt=c["setup_tt"]; ff=c["hold_ff"]
man={"schema":"opentallas.s81.native_core_view.v1","module":M,"kit":RUN,
     "routed_db":RUN+"/run/results/asap7/kr_ot_dsrom_su_hcpost_lane_pr_c/base/6_final.odb",
     "verdict":"SIGNED","variant":"hcpost_route_h5 (extracted-SPEF hold-only ECO, hold margin 5 ps); h0 also SIGNED (TT +61.09 / FF +0.13), h5 preferred",
     "signoff":{"tt_setup_wns_ps":tt["wns_ps"],"ff_hold_wns_ps":ff["wns_ps"],
                "pair_skew_worst_abs_ps":{"tt":c["clock"]["by_corner"]["tt"]["pair_skew"]["checks"]["max"]["worst_abs_ps"],
                                          "ff":c["clock"]["by_corner"]["ff"]["pair_skew"]["checks"]["max"]["worst_abs_ps"]},
                "drc":so["route"]["drc"],"antenna_nets":so["route"]["antenna_nets"],"drv":c["drv"]["verdict"],
                "sdc_lint":so["sdc_lint"]["verdict"],"generated":so["generated"]},
     "scope":"routed abstract + TT/FF timing models (ORFS generate_abstract, tc->_tt, bc->_ff); no GDS",
     "pins":341,"pins_note":"16 constant o[15:0] pins dropped (OWNER DECISION 8); plan core_pins unchanged (all 341 within 1.33 um of a same-layer LEF pin rect)",
     "physical_change":"hold-only ECO on extracted SPEF; no RTL, pin, cycle or clock change",
     "die_view":"physical/ref_tile/s81sl_hcpl/views/"+M+" (LEF, _tt.lib, _ff.lib, insertion.json replaced; stale _ss.lib removed)",
     "files":{p.name:h(p) for p in sorted(A.iterdir()) if p.is_file()},
     "view_files":{p.name:h(p) for p in (V/f"{M}.lef",V/f"{M}_tt.lib",V/f"{M}_ff.lib",V/"insertion.json")}}
json.dump(man,open(A/"MANIFEST.json","w"),indent=1)
tt_w=tt["wns_ps"]; ff_w=ff["wns_ps"]
(A/"README.md").write_text(f"Signed-off hcpost lane view from hcpost_route_h5. TT setup {tt_w:+.2f} ps, FF hold {ff_w:+.2f} ps, related-pair skew TT 25.40 / FF 22.33 ps, DRC/antenna/DRV zero, SDC lint and face guard pass. This was a hold-only ECO on extracted SPEF with no RTL, pin, cycle or clock change. The die-view files live in physical/ref_tile/s81sl_hcpl/views/{M}/. This archive holds the sign-off record, kit inputs, the exact source in source/ and the gzipped routed netlist.\n")
print(json.dumps(man["signoff"]))
