import json,sys
from pathlib import Path
Q=Path("/srv/opentallas-scratch2/claude");R=Q/"codex-qc-clock-0336";W=Q/"wt/codex-qc-clock-0336";sys.path.insert(0,str(W/"tools/die_plan"))
import count_align_plan as P,count_align_bind as B,die_sta_related as D
S=json.load(open(Q/"die-qc-46/plan/sidecar_qc33.json")); wanted=S["count_aligned"]["ports"]
rows=[]
for v in S["ports"]:
 if v["port"] not in wanted:continue
 rows.append(dict(port=v["port"],src=v["src_region"],dst=v["dst_region"],src_part=v["src"],dst_part=v["dst"]))
assert len(rows)==len(wanted),(len(rows),len(wanted))
ports,pr=P.row_ports(rows)
print("INTERVAL_START",len(rows),flush=True)
sta=D.sta_port_intervals(R/"proof",Q/"die-qc-46/plan/plan_qc45.json",["TT","FF"],ports,pr,"spice_edge",True,fall=True,clock_ocv="table",clock_droop="shared",droop_regions_file=R/"proof/droop_regions.json",core_latency_ff=202.5,clock_cell="inv")
(R/"ca/fresh_intervals.json").write_text(json.dumps(sta))
miss=[]
for r in rows:
 pid=r["port"];iv=[c["rise"].get(pid)for c in sta.values()]
 if any(z is None for z in iv):miss.append(pid);continue
 lo=min(x[0]for x in iv);hi=max(x[1]for x in iv);mid=(lo+hi)/2
 r.update(d_ps=mid,p_dn_ps=mid-lo,p_up_ps=hi-mid,unshared_sta_ps=max(c.get("unshared",{}).get(pid,0)for c in sta.values()),margin_ps=0,_named=True)
 fv=[c.get("fall",{}).get(pid)for c in sta.values()]
 r.update(fall_lo=min(x[0]for x in fv)if all(x is not None for x in fv)else None,fall_hi=max(x[1]for x in fv)if all(x is not None for x in fv)else None)
assert not miss,("missing",len(miss),miss[:10]);print("DATA_INTERVAL_READY",len(rows),flush=True)
caps=json.load(open(Q/"codex-qc-1029/physical_event/capture_taps.json"))
ctx=P.clock_contexts(R/"proof",Q/"die-qc-46/plan/plan_qc45.json",["TT","FF"],"spice_edge","table","shared",R/"proof/droop_regions.json",202.5,"inv")
D.CPPR_LCA=True
root,edges,info=P.clock_start_edges(rows,ctx,retime_max=256,clean_by="width",retime_up=True,max_hop_um=400,capture_taps=caps)
(R/"ca/fresh_start_edges.json").write_text(json.dumps(dict(root=root,edges=edges,info=info)));print("START",json.dumps(info),flush=True)
summ,cross,regs=P.plan(rows,start_edges=edges,start_root=root)
summ.update(period_ps=833,aperture_ps=833/8,sync_aperture_ps=26.5,pad=0,wander_frac=.05,scope="QC46 placement RC estimate; fresh graph/current exact data endpoint contracts. NOT PHYSICAL GATE")
summ["start_tree"].update(info);doc=dict(summary=summ,crossings=cross,regions=regs,start_edges=edges)
(R/"ca/fresh_plan.json").write_text(json.dumps(doc));print("SUMMARY",json.dumps(summ),flush=True)
if summ["fail"]or summ["start_tree"]["start_fail"]:raise SystemExit("Fresh START/data plan fails; no emission/adoption")
b=B.bind(doc,parts=B.ocv_parts(rows));(R/"ca/fresh_bind.json").write_text(json.dumps(b));print("BIND_READY",len(b["ports"]),len(b["start_ports"]),flush=True)
