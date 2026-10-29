#!/usr/bin/env python3
import hashlib,json,pathlib,shutil,subprocess,sys
W=pathlib.Path(__file__).resolve().parents[2]
sys.path[:0]=[str(W/"tools/die_plan"),str(W/"physical/die_plan/qwen_kvsys/cores/harden")]
import core_infra as CI,lec,gen_core_kit_kv as G
L=pathlib.Path("/srv/opentallas-scratch2/claude/codex-kv-phy-pad-1028/pv_clock")
B=pathlib.Path("/srv/opentallas-scratch2/claude/codex-kv-kits-1028/pvlc")
O=pathlib.Path("/srv/opentallas-scratch2/claude/kv-kits-16-1028/pvlc")
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
source=subprocess.check_output(["git","-C",str(W),"rev-parse","HEAD"],text=True).strip()
for view in ("R0","fMX"):
 name="kv3_pv_pair__380.16x190.08"+("_fMX" if view=="fMX"else "")
 base=B/name
 cache=O/"kits"/name if view=="R0"else B/"fMX_cts_snapshot_0108"
 kd=L/"trial_kits"/name
 if kd.exists():raise RuntimeError("fresh immutable trial directory already exists: "+str(kd))
 shutil.copytree(base,kd,ignore=shutil.ignore_patterns("run","lec","signoff","views","__pycache__","*.log","autopilot_chain_*.json"))
 if sha(base/"1_synth_odb.v")!=sha(cache/"1_synth_odb.v"):raise RuntimeError("pre-CTS source differs")
 br=cache/"run/results/asap7"/(("hc_kv3_pv_pair__380_16x190_08_fMX")if view=="fMX"else"hc_kv3_pv_pair__380_16x190_08")/"base"
 dr=kd/"run/results/asap7"/br.parent.name/"base";dr.mkdir(parents=True)
 kept=[]
 for p in br.iterdir():
  if p.is_file()and p.name.startswith(("1_","2_","3_","1_synth")):
   shutil.copy2(p,dr/p.name);kept.append(p.name)
 if "3_place.odb"not in kept or"3_place.sdc"not in kept:raise RuntimeError("no pre-CTS checkpoint")
 rtl_before={str(p.relative_to(kd)):sha(p)for p in(kd/"rtl").rglob("*")if p.is_file()}
 pin_before=sha(kd/"pins.json");config_before=sha(kd/"config.mk")
 slp=W/"results/codex_kv_pv_clock_1029"/("pv_tree_structural_balanced_"+view+".json")
 sl=json.load(open(slp));old=json.load(open(kd/"core_infra_plan.json"))
 plan=CI.compile_slice(sl,kd)
 assert old["core_tree"]["nodes"]==plan["core_tree"]["nodes"],"node geometry/stages changed"
 assert [l for l in old["core_tree"]["leaves"]if not l.get("cts_open")]==[l for l in plan["core_tree"]["leaves"]if not l.get("cts_open")],"macro leaves changed"
 # Emit only slice decks; retain every baseline shared helper and physical input.
 (kd/"master_core_infra.tcl").write_text(CI.emit_tcl(sl,kd))
 (kd/"core_infra_plan.json").write_text(json.dumps(plan,indent=2)+"\n")
 (kd/"core_infra_cts.tcl").write_text(CI.emit_cts_tcl(plan))
 shutil.copy2(slp,kd/"pv_tree_slice.json")
 f=json.load(open(kd/"freeze.json"));pf=O/"pins"/pathlib.Path(f["pins_file"]).name
 assert sha(pf)==f["pins_sha256"],"pin source differs"
 shutil.copy2(pf,kd/"plan_pins.json")
 assert rtl_before=={str(p.relative_to(kd)):sha(p)for p in(kd/"rtl").rglob("*")if p.is_file()}
 assert pin_before==sha(kd/"pins.json")and config_before==sha(kd/"config.mk")
 f.update(source_commit=source,clock_slice_source="e3d9cf09f",clock_slice_sha256=sha(slp),logical_source_unchanged="edd8dd1a674fc9283301e2817110df568782b339",trial_scope="fresh CTS+GRT only; no DRT/signoff")
 f["kit_hash"]=G.kit_hash(kd);(kd/"freeze.json").write_text(json.dumps(f,indent=1)+"\n")
 lec.write_kit_provenance(kd,W)
 receipt=dict(view=view,kit=str(kd),source=source,slice_sha256=sha(slp),logical_rtl_hashes=rtl_before,pins_sha256=pin_before,config_sha256=config_before,
  plan_pin_sha256=sha(pf),nodes_unchanged=True,macro_leaves_unchanged=True,pre_cts_source=str(cache),pre_cts_odb_sha256=sha(dr/"3_place.odb"),
  copied_pre_cts_files=kept,scope="Only new sink ownership in slice decks; all existing helpers/RTL/pins/macros/IO configs retained; fresh CTS/GRT, no old4_cts copied")
 (L/("trial_"+view+"_receipt.json")).write_text(json.dumps(receipt,indent=1)+"\n")
 print(view,kd,f["kit_hash"],"source",source,"slice",sha(slp))
