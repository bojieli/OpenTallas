"""DIE-QC-51: check plan landing_contract <-> sidecar collector.types sync; with --write emit a synced sidecar."""
import json,sys
plan,side,out=sys.argv[1],sys.argv[2],(sys.argv[3] if len(sys.argv)>3 else None)
base=sys.argv[4] if len(sys.argv)>4 else None
P=json.load(open(plan));S=json.load(open(side))
M=dict(tree="collector_tree",local_sources="collector_local_sources",children="collector_children",collector_root_node="collector_root_node")
ty=S["collector"]["types"];diff={};missing=[]
for tn,c in ty.items():
    t=P["partition_types"].get(tn)
    if t is None: missing.append(tn);continue
    lc=t.get("clock",{}).get("landing_contract") or {}
    for sk,pk in M.items():
        if c.get(sk)!=lc.get(pk): diff.setdefault(tn,[]).append(sk)
            
print("types",len(ty),"missing_in_plan",len(missing),"differ",len(diff),sorted({k for v in diff.values() for k in v}))
print(sorted(diff)[:12])
if out and base:
    B=json.load(open(base))
    lcb=lambda R,tn:(R["partition_types"].get(tn,{}).get("clock",{}).get("landing_contract") or {})
    diff={tn:ks for tn,ks in diff.items() if any(lcb(P,tn).get(M[k])!=lcb(B,tn).get(M[k]) for k in ks)}
    print("event-changed differ",len(diff),sorted(diff))
if out:
    for tn,ks in diff.items():
        lc=P["partition_types"][tn]["clock"]["landing_contract"]
        for sk in ks: ty[tn][sk]=lc.get(M[sk])
    S["note"]=S.get("note","")+" | DIE-QC-51: collector.types tree/local_sources/children/root re-synced from plan_qc52 landing_contract (%d types)"%len(diff)
    json.dump(S,open(out,"w"),indent=1);print("WROTE",out)
