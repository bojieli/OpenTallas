# DIE-QC-57: derived count-aligned RTL K for the +1 cycle value event: copy the as-built sidecar (DIE-QC-33) and move
# sched_lat / K / row added_cycles by +1 on the event ports (non-tree, depth kept; the START tree frame is unchanged, so
# K = sched_lat - 1 - (N_d - N_s) moves with sched_lat). Fails if the sidecar cycles do not equal the base plan cycles.
import json,sys
src,dst,plan_base,plan_new=sys.argv[1:5]
s=json.load(open(src)); P=s["count_aligned"]["ports"]; rows={r["port"]:r for r in s["ports"]}
b=json.load(open(plan_base))["clock"]["landing_network"]["count_aligned_cycles"]
n=json.load(open(plan_new))["clock"]["landing_network"]["count_aligned_cycles"]
assert all(P[p]["sched_lat"]==b[p]==rows[p]["added_cycles"] for p in P), "sidecar != base plan cycles"
ch=[p for p in P if n[p]!=b[p]]
for p in ch:
    d=n[p]-b[p]; assert d in (1,-1) and not P[p]["tree"] and P[p]["sched_lat"]+d>=1, (p,d)
    P[p]["sched_lat"]+=d; P[p]["K"]+=d; rows[p]["added_cycles"]+=d
s["note"]=s.get("note","")+f" | DIE-QC-57 count-aligned cycle event on {len(ch)} non-tree crossings (+1 {sum(n[p]>b[p] for p in ch)} / -1 {sum(n[p]<b[p] for p in ch)}) (sched_lat/K/added_cycles; depth, tree, regions unchanged)"
open(dst,"w").write(json.dumps(s,indent=1)+"\n"); print("sidecar ports changed",len(ch))
