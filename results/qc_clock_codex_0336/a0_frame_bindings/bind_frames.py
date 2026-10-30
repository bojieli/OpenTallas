import json,sys,hashlib,collections
from pathlib import Path
Q=Path("/srv/opentallas-scratch2/claude");W=Q/"wt/codex-qc-clock-0336";R=Q/"codex-qc-clock-0336/a0_frames";sys.path.insert(0,str(W/"tools/die_plan"))
import schema as S,gen_phys as G
pf=Q/"die-qc-46/plan/plan_qc45.json";p=json.load(open(pf));P=S.Plan(p,pf);ff=Q/"codex-qc-a0-0336/impact/a0_pertype_clock_frames.json";frames=json.load(open(ff));tf=Q/"codex-qc-clock-0336/ideal/clock/tree.json";tree=json.load(open(tf))
lookup={(t["part"],t["port"].rsplit("__",1)[-1]):t for t in tree["taps"]};pin_cache={};allrows=[];counts=collections.Counter();bytype={};missing=[]
for part,pr in sorted(P.parts.items()):
 tn=pr["type"];ty=P.types[tn];cores={h["inst"]:h for h in ty.get("hard_cores",[])if h.get("module")in["qfd_tile_nk_a0c","qfd_tile_nl_a0c"]}
 if not cores:continue
 rows={c:G.core_tap_rows(P,tn,c,pending=[])for c in["TT","FF"]};xy={n:[x,y]for n,x,y in G.core_tap_pins(P,tn)}
 byinst={c:{x[1]:x for x in rows[c]}for c in rows}
 for inst,h in cores.items():
  cohort="NK"if"_nk_"in h["module"]else"NL";counts[cohort]+=1
  rt,rf=byinst["TT"][inst],byinst["FF"][inst];pn=rt[0];assert pn==rf[0]
  tap=lookup.get((part,pn))
  if tap is None:missing.append([part,pn,inst]);continue
  f=W/"physical/die_plan/qwen_compute/plan_of_record"/h["pins_file"]
  if str(f)not in pin_cache:
   x=json.load(open(f));ck=[x for x in x["pins"]if x["name"]==rt[2]];assert len(ck)==1;(pin_cache.setdefault(str(f),(ck[0],hashlib.sha256(f.read_bytes()).hexdigest())))
  ck,ph=pin_cache[str(f)];x,y=ck["x"],ck["y"];w,hh=h["outline_um"];ori=h.get("orient","R0")
  x,y={"R0":(x,y),"MX":(x,hh-y),"MY":(w-x,y),"R180":(w-x,hh-y)}[ori];off=h.get("track_offset_um",[0,0]);native=[h["origin_um"][0]+off[0]+x,h["origin_um"][1]+off[1]+y];publicdie=P.to_die(part,native);tapdie=P.to_die(part,xy[pn])
  assert max(abs(a-b)for a,b in zip(tapdie,tap["xy"]))<1e-6,(part,pn,tapdie,tap["xy"])
  cand=frames["types"][cohort];driver=tap.get("driver")or tree["node_buf"][str(tap["node"])]
  record=dict(part=part,parent_type=tn,core_inst=inst,core_module=h["module"],cohort=cohort,core_origin_um=h["origin_um"],core_orient=ori,track_offset_um=off,clock_port=rt[2],proof_port=tap["port"],tap_driver=driver,tap_node=tap["node"],tap_die_xy_um=tapdie,public_native_pin=dict(layer=ck["layer"],core_xy_um=[ck["x"],ck["y"]],type_xy_um=native,die_xy_um=publicdie,pins_file=str(f),pins_sha256=ph),landing_offset_native_minus_tap_um=[a-b for a,b in zip(publicdie,tapdie)],old_core_insertion_ps=dict(TT=rt[4],FF=rf[4]),old_core_early_ps=dict(TT=rt[3],FF=rf[3]),wrapper_common_frame_ps=dict(TT=250,FF=202.5),candidate_model=dict(model=cand["model"],plan=cand["plan"],corners=cand["corners"],binding_status="UNBOUND_PUBLIC_ABI: candidate ODB centre M5 ck versus current public E/M4 ck; E-to-centre trunk absent"),candidate_mean_delta_from_current_core_ps={c:cand["corners"][c]["weighted_mean_ps"]-old for c,old in[("TT",rt[4]),("FF",rf[4])]})
  allrows.append(record);bytype.setdefault(tn,dict(NK=0,NL=0));bytype[tn][cohort]+=1
assert not missing,missing
assert dict(counts)==dict(NK=720,NL=48),counts
out=dict(scope="SOURCE-ONLY exact existing public core/tap bindings, not old-tree timing price. Candidate frames remain unbound to public ABI; no SDC/adoption/padding.",plan=str(pf),plan_sha256=hashlib.sha256(pf.read_bytes()).hexdigest(),old_tree=str(tf),old_tree_sha256=hashlib.sha256(tf.read_bytes()).hexdigest(),frame_file=str(ff),frame_sha256=hashlib.sha256(ff.read_bytes()).hexdigest(),cohort_counts=dict(counts),parts=len({r["part"]for r in allrows}),parent_types=len(bytype),bytype=bytype,cores=allrows,missing=missing)
(R/"public_core_tap_bindings.json").write_text(json.dumps(out,indent=1)+"\n")
summary=dict(scope=out["scope"],cohorts=dict(counts),parts=out["parts"],parent_types=len(bytype),old_frames={c:sorted({(r["old_core_insertion_ps"]["TT"],r["old_core_insertion_ps"]["FF"])for r in allrows if r["cohort"]==c})for c in counts},landing_offset_range_um={str(i):[min(r["landing_offset_native_minus_tap_um"][i]for r in allrows),max(r["landing_offset_native_minus_tap_um"][i]for r in allrows)]for i in[0,1]},missing=missing)
(R/"summary.json").write_text(json.dumps(summary,indent=1)+"\n");print(json.dumps(summary))
