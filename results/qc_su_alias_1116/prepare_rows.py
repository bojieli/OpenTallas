from pathlib import Path
import json,re,hashlib
R=Path(__file__).parent
P=Path("/srv/opentallas-scratch2/claude/qc-pinaccess-o/n43_event_v5/physical/die_plan/qwen_compute/plan_of_record/zz_s29_qc103_s4q9k_sunorm43_private44868_pinv5.json")
j=json.load(open(P));raw=Path("/srv/opentallas-scratch2/claude/qc-types-r/w1_fp/group44_w1/work/orfs/layout_dump.json");d=json.load(open(raw))
canonical="qfd_qc_su_lane_w_l1_m44s1";pins=[]
for name,layer,x0,y0,x1,y1 in d["pins"]:
 if name not in {"clk","rst_n"} and not re.fullmatch(r"c_[io]\[\d+\]",name):continue
 pins.append(dict(name=name,layer=layer,x=round((x0+x1)/2,6),y=round((y0+y1)/2,6),dir="out" if name.startswith("c_o") else "in",rect_um=[x0,y0,x1,y1]))
assert len(pins)==1010==len({p["name"] for p in pins})
pinfile=dict(schema="opentallas.core_pins.v1",core=canonical,frame="core R0, origin (0,0)",source="Actual W1 2_floorplan BPin rectangles; PROVISIONAL until matching final signed LEF pin export",pins=sorted(pins,key=lambda p:p["name"]))
(R/"w1_actual_floorplan_pins.PROVISIONAL.json").write_text(json.dumps(pinfile,indent=2)+"\n")
new={p["name"]:p for p in pins};rows=[];children=[];deltas=[]
for tn,t in j["partition_types"].items():
 for hc in t.get("hard_cores",[]):
  m=re.fullmatch(r"qfd_qc_su_lane_w_l([1-7])_m44s1",hc.get("module",""))
  if not m:continue
  lane=int(m[1]);inst=hc["inst"];old=json.load(open(P.parent/hc["pins_file"]))["pins"];old={p["name"]:p for p in old}
  assert set(old)==set(new),(tn,inst,"pin ABI differs")
  changes={"physical_inst":"u_bound."+inst,"physical_master":canonical,"pins_file":"cores/su/normalized43_w1_shared_pins.json"}
  rows.append(dict(type=tn,inst=inst,expected_module=hc["module"],preserve_bound_group=hc["bound_group"],changes=changes,view_assignment="REQUIRES actual W1 SIGNED LEF/TT/FF Lib paths and hashes; no unsigned substitution",native_master=hc["module"],input_bits=760,output_bits=248))
  children.append(dict(type=tn,master=canonical,native_master=hc["module"],inst="u_bound."+inst,child_params={},binding_sha256="MUST_SEAL_ACTUAL_POST_BIND_SOURCE",port_map="IDENTITY 760 input / 248 output bits",adoptable=False))
  dd=[dict(name=n,from_um=[old[n]["x"],old[n]["y"]],to_um=[new[n]["x"],new[n]["y"]],l1_um=round(abs(old[n]["x"]-new[n]["x"])+abs(old[n]["y"]-new[n]["y"]),6)) for n in new]
  deltas.append(dict(type=tn,inst=inst,max_pin_l1_delta_um=max(x["l1_um"] for x in dd),changed_pins=sum(x["l1_um"]!=0 for x in dd),clock_reset=[x for x in dd if x["name"] in {"clk","rst_n"}]))
assert len(rows)==31,(len(rows),"exact31 selectedW1..7 rows in frozenprospectiveplan")
(R/"alias_plan_rows.PENDING_SIGNED.json").write_text(json.dumps(dict(plan=str(P),plan_sha256=hashlib.sha256(P.read_bytes()).hexdigest(),canonical_master=canonical,source_epoch="44868 only; not common+REDv2",rows=rows,adoptable=False,requires=["W0/W1 actual SIGNED records and generated views","Actual post-bind binding SHA sealed into each kit assembly contract","Final LEF pin ABI/rectangles equal proposed actual pin file","Regenerate reset/reach/clock binding for moved pin coordinates, preserving published release or explicitly pricing added boot cycles","Full successor bind/LATCHECK/G0"]),indent=2)+"\n")
(R/"assembly_child_templates.PENDING_SEAL.json").write_text(json.dumps(dict(children=children,do_not_use_unsealed=True),indent=2)+"\n")
(R/"pin_delta_report.json").write_text(json.dumps(dict(canonical_pin_count=1010,rows=deltas,old_pin_coords_reusable=False),indent=2)+"\n")
print(json.dumps(dict(plan_rows=len(rows),types=sorted({r["type"] for r in rows}),newpins=len(pins),max_delta_um=max(x["max_pin_l1_delta_um"] for x in deltas),sample=deltas[0]),indent=2))
