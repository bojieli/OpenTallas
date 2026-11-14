
from pathlib import Path
import importlib.util,json,sys
W=Path("/srv/opentallas-scratch2/claude/wt/die-kv-100");D=Path("/srv/opentallas-scratch2/claude/tok-verify-2/kv_cpc_bridge")
sys.path[:0]=[str(W),str(W/"tools"),str(W/"tools/qwen_kv_die")]
spec=importlib.util.spec_from_file_location("bridge",D/"kv_pv_cpc_calendar.py");C=importlib.util.module_from_spec(spec);spec.loader.exec_module(C)
p=W/"physical/die_plan/qwen_kvsys/hubc_pair_1113/native1";b=W/"physical/die_plan/qwen_kvsys/ns_kv100_out7/bind_1/out"
args=(p/"plan_c.json",p/"asbuilt_vN.json",b,W,D/"proof")
for label,proto,base,expected in [("final_coherence_guard",False,None,"coherent matching bind"),("CPC_reapply_guard",True,D/"source_only_test_calendar.json","already present"),("unmapped_actual_trunk_guard",True,None,"unmapped changed PV path")]:
 try:C.derive(*args,prototype=proto,base_calendar=base)
 except ValueError as e:
  assert expected in str(e),(label,str(e));print(label,"CAUGHT",str(e)[:260])
 else:raise AssertionError(label)
from tools.qwen_kv_die import kv_static_programme as P
old=json.loads((D/"prep_new/die_ages_bound_padded.json").read_text());new=json.loads((D/"prep_pin/die_ages_bound_padded.json").read_text())
po=P.profile("die",old);pn=P.profile("die",new)
assert po["f_dly"]==1 and pn["f_dly"]==new["schedule"]["attn"]["F_DLY"]==57
r=json.loads((D/"proof.json").read_text());r["additional_guards"]=["final incoherent input rejected","actual complete CPC reapplication rejected before trunk derivation","actual unsupported node9->12 trunk FAIL preserved"]
r["legacy_profile_mismatch"]={"old_generated_F_DLY":old["schedule"]["attn"]["F_DLY"],"old_profile_fallback":po["f_dly"],"new_generated_F_DLY":new["schedule"]["attn"]["F_DLY"],"new_profile_F_DLY":pn["f_dly"],"scope":"Pre-existing missing boot-age field; selected v2 path attaches real generated age. Source increment remains exactly2, not56. Legacy default prep remains byte-preserved."}
(D/"proof_followup.json").write_text(json.dumps(r,indent=2)+"\n");print("CPC_FOLLOWUP PASS",r["legacy_profile_mismatch"])
