
from pathlib import Path
import contextlib,io,json,sys,types,importlib.util
W=Path("/srv/opentallas-scratch2/claude/wt/die-kv-100");D=Path("/srv/opentallas-scratch2/claude/tok-verify-2/kv_cpc_bridge")
sys.path[:0]=[str(W),str(W/"tools"),str(W/"tools/qwen_kv_die")]
spec=importlib.util.spec_from_file_location("tools.token_pass.kv_pv_cpc_calendar",D/"kv_pv_cpc_calendar.py");C=importlib.util.module_from_spec(spec);spec.loader.exec_module(C);sys.modules[spec.name]=C
def load(text,name):
 m=types.ModuleType(name);m.__file__=str(W/"physical/die_plan/qwen_kvsys/boot_v36/kv_boot_v36.py");exec(compile(text,m.__file__,"exec"),m.__dict__);return m
old=load((W/"physical/die_plan/qwen_kvsys/boot_v36/kv_boot_v36.py").read_text(),"old");new=load((D/"kv_boot_v36_new.py").read_text(),"new")
cal=D/"v1_test_calendar.json";cal.write_text(json.dumps(dict(schema="opentallas.kv.pv_landed_calendar.v1",result_cycles_added=3,first_input_age_cycles_added=0,arithmetic_cycles_added=0,note="Positive-cost v1 compatibility unit input, not a physical calendar/provider")))
args=dict(rs=str(D/"inputs/relay_stages.json"),model=str(D/"inputs/static_model.json"),groups=str(W/"physical/die_plan/qwen_kvsys/ns_kv100_out7/bind_1/out/bus_groups.json"),core_splits=str(W/"physical/die_plan/qwen_kvsys/plan_of_record/kv67_1104/core_splits.json"),pv_result_calendar=str(cal))
for label,m in [("old",old),("new",new)]:
 with contextlib.redirect_stdout(io.StringIO()):m.prep(types.SimpleNamespace(**args,out=str(D/("prep_v1_"+label))))
names={p.name for p in (D/"prep_v1_old").iterdir()}
assert all((D/"prep_v1_old"/n).read_bytes()==(D/"prep_v1_new"/n).read_bytes()for n in names)
r=json.loads((D/"proof_final.json").read_text());r["v1_positive_cost_byte_identical_files"]=len(names);(D/"proof_ready.json").write_text(json.dumps(r,indent=2)+"\n");print("CPC_V1_COMPAT PASS",len(names),"byte-identical files")
