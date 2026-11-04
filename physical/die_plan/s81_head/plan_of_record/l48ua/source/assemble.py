import json,sys
sys.path.insert(0,"tools/s81_head"); sys.path.insert(0,"tools/die_plan")
import head_start_sources as H
plan=json.load(open("/srv/opentallas-scratch2/claude/dh61/oneplan/bindua/src/source_plan.json")); stages=json.load(open("/srv/opentallas-scratch2/claude/dh55-cland/head_src_v3/start_stages_src25q.json"))
top=open("/srv/opentallas-scratch2/claude/dh61/oneplan/bindua/genrtl/s81_head_top.sv").read()
t,sp=H.complete_top(top,plan,stages)
open("/srv/opentallas-scratch2/claude/dh61/oneplan/bindua/src/s81_head_top.sv","w").write(t)
json.dump(dict(unused_uniform_exports=sp,scope="DH61 l48ua: gen.py rtl top + complete_top + start_stages from dh55-cland/head_src_v3 (same 171 raw exports)"),open("/srv/opentallas-scratch2/claude/dh61/oneplan/bindua/src/report.json","w"),indent=1)
print("TOP lines",t.count(chr(10)),"unused",len(sp))
