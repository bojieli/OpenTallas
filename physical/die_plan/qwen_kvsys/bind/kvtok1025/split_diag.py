"""TOK-SCHED 10-25 diagnostic only: replay bind b1 to regen_params, then diff the type signatures of every TYPE_SPLIT group."""
import json,sys
from pathlib import Path
R=Path("/srv/opentallas-scratch2/claude/tok-sched/kvbind");tree=R/"tree";sys.path.insert(0,str(tree/"tools/die_plan"))
import bind
plan=tree/"physical/die_plan/qwen_kvsys/die_plan.json";bind._AB_OVERRIDE["path"]=str(R/"recipe_b1.json")
raw=bind.load_plan(plan);B=bind.Binder(raw,json.load(open(R/"b1/asbuilt.json")),plan.parent,bind.plan_base(plan,raw))
B.map_cells();B.analyse();B.build_buses();B.align_landings();B.regen_params()
rep=json.load(open(R/"b1/bind_report.json"))
out=[]
def s(x): return json.dumps(x,default=str)[:400]
for t in rep["type_splits"]:
  vs=t["variants"];ref=vs[0][0];s0=B.type_signature(ref)[0]
  for g in vs[1:]:
    p=g[0];s1=B.type_signature(p)[0]
    rec=dict(type=t["type"],ref=ref,inst=p,members=g)
    for k in s0:
      if s0[k]==s1[k]: continue
      if isinstance(s0[k],dict):
        ks=sorted(set(s0[k])|set(s1[k]),key=str);dd=[(str(x),s(s0[k].get(x)),s(s1[k].get(x))) for x in ks if s0[k].get(x)!=s1[k].get(x)]
        rec[k]=dict(n=len(dd),first=dd[:6])
      else:
        a,b=set(map(str,s0[k])),set(map(str,s1[k]))
        rec[k]=dict(only_ref=sorted(a-b)[:6],only_inst=sorted(b-a)[:6],n=len(a^b))
    out.append(rec)
(R/"split_diag.json").write_text(json.dumps(out,indent=1));print("SPLIT_DIAG",len(out))
