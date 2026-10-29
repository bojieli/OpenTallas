import sys,json,pathlib,hashlib
W=pathlib.Path("/srv/opentallas-scratch2/claude/wt/codex-s81-frame-sub-1028")
R=pathlib.Path("/srv/opentallas-scratch2/claude/codex-tok-s81-1028")
sys.path.insert(0,str(W/"tools/s81_dv"));import frame_schedule_asb as F
F.MANIFEST="physical/die_plan/s81/bind/asbuilt_b178_coll_s13.json"
ab=json.loads((W/F.MANIFEST).read_text());dt="\n".join((W/p).read_text() for p in ab["netlist"])
o=R/"fs_s13_bound_variants";o.mkdir(exist_ok=True)
records=[]
for m,v in (("col_h9","x"),("col_h9","nx"),("col_h10","x")):
 top=f"{m}_l4_lp_asb_{v}";work=R/f"fs_work/{m}_{v}"
 old=json.loads((R/f"fs_s13/{top}_schedule.json").read_text());chk=json.loads((R/f"fs_s13/{top}_check.json").read_text())
 stale=[p for p,h in old["source_sha256"].items() if p!="tools/s81_dv/frame_schedule_asb.py" and hashlib.sha256((W/p).read_bytes()).hexdigest()!=h]
 assert not stale,stale
 js=json.loads((work/f"{top}.json").read_text());selected,rows=F.selected_station_variants(js,top,ab,dt,F.HARD_PARAMS())
 meas=F.measure(selected,top)
 lp=json.loads((W/F.LP_SCHED.format(m=m)).read_text());pm=json.loads((W/F.PLAN_MAP.format(m=m)).read_text())
 mv=json.loads((work/f"validate_{m}_l4_lp.meas.json").read_text());mt=json.loads((work/f"{m}_l4_lp.meas.json").read_text())
 src=dict(old["source_sha256"]);src["tools/s81_dv/frame_schedule_asb.py"]=hashlib.sha256((W/"tools/s81_dv/frame_schedule_asb.py").read_bytes()).hexdigest()
 for f in ab["netlist"]+["rtl/v41rom/ot_v41_rom_elem_q_qxpq_w10_gb.sv"]:src[f]=hashlib.sha256((W/f).read_bytes()).hexdigest()
 sched,links,plan,fails=F.schedule(mv,mt,meas,lp,pm,m,v,src);sched["selected_station_variants"]=rows
 assert not fails,fails
 assert len(rows)==12
 assert all(s.get("go_boundary_edges")==1 and s.get("required_go_issue_advance_edges")==1 and s.get("native_provider_qualified")==False for s in sched["station_inputs"].values())
 sp=o/f"{top}_schedule.json";sp.write_text(json.dumps(sched,indent=1)+"\n")
 c=dict(chk);c.update(schedule_sha256=hashlib.sha256(sp.read_bytes()).hexdigest(),selected_station_variants=rows,plan_consistency=plan,links=links,verdict="PASS",fails=[])
 (o/f"{top}_check.json").write_text(json.dumps(c,indent=1)+"\n")
 record=dict(master=top,actual_frames=len(rows[0]["frames"]),stations=len(rows),gb_stations=12,legacy_reported_gb_stations=0,plan_checks=len(plan),plan_errors=len(fails),native_provider_qualified=False,original_elaboration=str(work),old_schedule_sha256=hashlib.sha256((R/f"fs_s13/{top}_schedule.json").read_bytes()).hexdigest(),selected_schedule_sha256=c["schedule_sha256"])
 records.append(record);print(record,flush=True)
(o/"receipt.json").write_text(json.dumps(dict(scope="Exact post-elaboration binder endpoint substitutions; original source elaborations reused only after every non-extractor source hash matches; no RTL/clock/token claim",frames=records,total_actual_qx=sum(r["actual_frames"]*r["stations"] for r in records)),indent=1)+"\n")
