import sys,json,re
sys.path.insert(0,"/srv/opentallas-scratch2/claude/wt/die-hbm-49/tools/die_plan")
import schema as S
PD="/srv/opentallas-scratch2/claude/die-hbm-48/plan/d44g"
CE=json.load(open(PD+"/clock_entries.json")); P=S.Plan(json.load(open(PD+"/die_plan.json")))
out={}
for tn,t in P.types.items():
    for c in t.get("hard_cores",[]) or []:
        e=(CE.get(tn) or {}).get(c.get("inst")) or (CE.get(tn) or {}).get(re.sub(r"__q\d+$","",c.get("inst") or ""))
        if isinstance(e,dict): out.setdefault(c["module"],set()).add((tuple(e["xy_um"]),tuple(e["island_um"])))
json.dump({k:sorted(v) for k,v in out.items()},open(sys.argv[1],"w"))
