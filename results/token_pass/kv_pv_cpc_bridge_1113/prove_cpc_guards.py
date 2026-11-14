
import contextlib,copy,io,json,sys,types
from pathlib import Path
W=Path("/srv/opentallas-scratch2/claude/wt/die-kv-100");D=Path("/srv/opentallas-scratch2/claude/tok-verify-2/kv_cpc_bridge")
sys.path[:0]=[str(W),str(W/"tools"),str(W/"tools/qwen_kv_die")]
import importlib.util
spec=importlib.util.spec_from_file_location("tools.token_pass.kv_pv_cpc_calendar",D/"kv_pv_cpc_calendar.py");C=importlib.util.module_from_spec(spec);spec.loader.exec_module(C);sys.modules[spec.name]=C
m=types.ModuleType("boot");m.__file__=str(W/"physical/die_plan/qwen_kvsys/boot_v36/kv_boot_v36.py");exec(compile((D/"kv_boot_v36_new.py").read_text(),m.__file__,"exec"),m.__dict__)
a=dict(rs=str(D/"inputs/relay_stages.json"),model=str(D/"inputs/static_model.json"),groups=str(W/"physical/die_plan/qwen_kvsys/ns_kv100_out7/bind_1/out/bus_groups.json"),core_splits=str(W/"physical/die_plan/qwen_kvsys/plan_of_record/kv67_1104/core_splits.json"))
cal=json.loads((D/"source_only_test_calendar.json").read_text())
checks=[]
for name,change,want in [("valid",{},None),("stale_bind",{"kind":"BOUND_INPUT_CONTRACT_RUNTIME_PENDING","input_identity":{"bus_groups_sha256":"0"*64}},"stale for selected bind groups"),("stale_source",{},"source identity changed")]:
 c=copy.deepcopy(cal);c.update(change)
 if name=="stale_source":c["source_pin_components"][0]["source_sha256"]="0"*64
 f=D/("cal_guard_"+name+".json");f.write_text(json.dumps(c))
 try:
  with contextlib.redirect_stdout(io.StringIO()):m.prep(types.SimpleNamespace(**a,pv_result_calendar=str(f),out=str(D/("prep_guard_"+name))))
 except ValueError as e:
  assert want and want in str(e),(name,str(e));checks.append(name+" caught")
 else:
  assert want is None,name
  r=json.loads((D/("prep_guard_"+name)/"die_ages_bound_padded.json").read_text());assert r["boot_ages"]["attn"]["F_DLY"]==57;checks.append("valid selected source F_DLY57")
r=json.loads((D/"proof_followup.json").read_text());r["source_guards"]=checks;(D/"proof_final.json").write_text(json.dumps(r,indent=2)+"\n");print("CPC_SOURCE_GUARDS PASS",checks)
