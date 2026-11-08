import json,sys
sys.path.insert(0,"tools/s81_head"); sys.path.insert(0,"tools/die_plan")
import head_start_sources as H
plan=json.load(open("/srv/opentallas-scratch2/claude/dh62/ss/src/source_plan.json")); stages=json.load(open("/srv/opentallas-scratch2/claude/dh62/ss/start_stages.json"))
top=open("/srv/opentallas-scratch2/claude/dh61/oneplan/bindua/genrtl/s81_head_top.sv").read()
t,sp=H.complete_top(top,plan,stages)
open("/srv/opentallas-scratch2/claude/dh62/ss/src/s81_head_top.sv","w").write(t)
json.dump(dict(unused_uniform_exports=sp,scope="DH62 l48ua: gen.py rtl top + complete_top + start_stages refreshed by dh62/ss/refresh.py"),open("/srv/opentallas-scratch2/claude/dh62/ss/src/report.json","w"),indent=1)
print("TOP lines",t.count(chr(10)),"unused",len(sp))
