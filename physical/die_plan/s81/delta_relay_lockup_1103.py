import json,sys
sys.path.insert(0,"tools/die_plan")
import added_tap_recentre as AT
src,est,out=sys.argv[1:4]
S0=open(src).read(); P=json.loads(S0)
d=json.load(open(est))["per_type"]
EX=("ot_s81sl_leaf__t65","ot_s81sl_kv_leaf__t2","bk_sel__t2")
c=sorted(t for t,v in d.items() if isinstance(v,dict) and (v.get("h_plain_neg") or 0)>0 and "slice_station" not in t and t not in EX and t in P["partition_types"])
P["reset"]["relay_lockup"]={"form":"negedge","types":c,"note":"S81-RF1 CLK FORM #7 (DIE-S81-51 ruling 11-03): internal reset relays = ot_dp_rrelay_nl on the types whose plain-relay hop hold estimate is negative (plan_clk7/nl_est.json); slice_station* (SAFE-STATION-1), leaf__t65, kv_leaf__t2, bk_sel__t2 (setup-tight) excluded"}
open(out,"w").write(AT.dumps_like(P,S0))
print(len(c))
