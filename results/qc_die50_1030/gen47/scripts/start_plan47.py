"""DIE-QC-50/gen47: START (reset-release) graph re-derived on the gen47 die clock tree (tree.json 4bad7469).
Recipe = Codex qc26_retime.py / reprice.py (codex-qc-start-provider-1029, codex-qc-start-native-0251) with NEW inputs:
proof = gen47 source-rebuilt GRT-routed proof (planned-NDR RC, proofN), plan = plan_qc49 9deec4c7.
Rows: the 2525 CA crossings (ports/regions of the old grp_spice_xing_lpo.json, all present in plan_qc49, part map
checked); their OLD d/p values are NOT kept: each row is reset to the gen47 sta_port_intervals hull only.
Main tools only (count_align_plan / count_align_bind / die_sta_related)."""
import json,sys,types,hashlib
from pathlib import Path
W=Path(sys.argv[1]);proof=Path(sys.argv[2]);plan=Path(sys.argv[3]);I=Path(sys.argv[4]);O=Path(sys.argv[5]);hop=float(sys.argv[6]) if len(sys.argv)>6 else 400.0
O.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(W/"tools/die_plan"))
import count_align_plan as P,count_align_bind as B
corners="TT_droop-regions_corelat250,FF_droop-regions_corelat202.5"
rows=P.load_rows(I/"baseline26/g26/grp_spice_xing_lpo.json",corners)
raw=json.load(open(plan));ports={p["id"]:p for p in raw["ports"]};mp=json.load(open(I/"baseline26/part_region.json"))["part_region"]
for r in rows:
 pr=ports[r["port"]]
 for s in ["src","dst"]:
  pn=pr[s]["part"];assert mp.get(pn,pn)==r[s];r[s+"_part"]=pn
args=types.SimpleNamespace(corner=corners,sta_proof=str(proof),sta_plan=str(plan),sta_clock_cal="spice_edge",sta_cppr_lca=True,sta_clock_ocv="table",sta_clock_droop="shared",sta_droop_regions=str(proof/"droop_regions.json"),sta_core_latency_ff=202.5,sta_clock_cell="inv")
import die_sta_related as DSR
ports_,pr_=P.row_ports(rows)
sta=DSR.sta_port_intervals(args.sta_proof,args.sta_plan,["FF","TT"],ports_,pr_,args.sta_clock_cal,args.sta_cppr_lca,fall=True,**P.sta_ocv_kw(args))
# reset every row to the gen47 interval only (no stale old-tree d/p)
for r in rows:
 iv=[c["rise"][r["port"]] for c in sta.values() if c["rise"].get(r["port"]) is not None]
 if iv:
  lo=min(x[0] for x in iv);hi=max(x[1] for x in iv);tt=sta["TT"]["rise"].get(r["port"])
  d=0.5*(tt[0]+tt[1]) if tt else 0.5*(lo+hi);r["d_ps"]=d;r["p_dn_ps"]=d-lo;r["p_up_ps"]=hi-d
hull=P.sta_hull(rows,sta);print("HULL",json.dumps(hull),flush=True)
assert hull["missing"]==0
ctx=P.clock_contexts(proof,plan,["TT","FF"],"spice_edge","table","shared",proof/"droop_regions.json",202.5,"inv")
cap=json.load(open(I/"physical_event/capture_taps.json"));assert len(cap)==313 and all(v.endswith("__clk") for v in cap.values())
print("CTXREADY",len(rows),flush=True)
root,edges,info=P.clock_start_edges(rows,ctx,retime_max=256,clean_by="width",retime_up=True,max_hop_um=hop,capture_taps=cap)
print("START",json.dumps(info),flush=True)
(O/"start_edges.json").write_text(json.dumps(dict(root=root,edges=edges,info=info)))
summ,out,regs=P.plan(rows,start_edges=edges,start_root=root)
summ.update(period_ps=833,aperture_ps=833/8,sync_aperture_ps=26.5,pad=0,wander_frac=.05,sta_hull=hull,proof=str(proof),plan=str(plan),plan_sha256=hashlib.sha256(open(plan,"rb").read()).hexdigest(),scope="gen47 START re-derivation; rows reset to gen47 STA hull; provisional virtual stage arrivals (node + median tap leg)")
summ["start_tree"].update(info)
doc=dict(summary=summ,crossings=out,regions=regs,start_edges=edges);(O/"plan.json").write_text(json.dumps(doc));print("SUMMARY",json.dumps(summ),flush=True)
if summ["fail"] or summ["start_tree"]["start_fail"]:raise SystemExit("gen47 START plan FAIL; artifacts retained, no emission")
b=B.bind(doc,parts=B.ocv_parts(rows));(O/"bind.json").write_text(json.dumps(b));print("BINDPASS",len(b["ports"]),len(b["start_ports"]),len(b["regions"]),flush=True)
