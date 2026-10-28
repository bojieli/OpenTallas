import json,sys,shutil,os
src,packet,esc=sys.argv[1],sys.argv[2],sys.argv[3]
os.makedirs(packet,exist_ok=True)
s=json.load(open(src)); s["trunk_escape"]=float(esc) if esc not in ("true","none") else (True if esc=="true" else None)
if s["trunk_escape"] is None: del s["trunk_escape"]
json.dump(s,open(packet+"/clock_spec.json","w"))
shutil.copy("/srv/opentallas-scratch2/claude/qc-infra-r31/dry15c/plan.json",packet+"/plan.json")
print(s["summary"]["geometry_verdict"],s["summary"]["errors"],s["summary"]["post_legal_reach"]["max_um"])
