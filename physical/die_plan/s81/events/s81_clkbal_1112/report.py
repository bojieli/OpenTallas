import json,collections,statistics,re
c=json.load(open("out/pairdump.json"))
t=json.load(open("/srv/opentallas-scratch2/claude/s87bind/hybridfp_1112/taps_TT.json"))
by=collections.defaultdict(list)
for r in t: by[r[1]].append(r[2])
mean={p:statistics.mean(v) for p,v in by.items()}; T=max(mean.values()); K=0.843; W=416.5
d={p:T-mean[p] for p in mean}
rows=[]
for n,cc,s in (("TT",c[0],1.0),("FF",c[1],K)):
    for pa,pb,P,Q,cnt,tag in cc["agg"]:
        da=d.get(pa,0)*s; db=d.get(pb,0)*s
        v=max(P+da-db,Q+db-da)
        if v>250: rows.append((n,pa,pb,round(max(P,Q),1),round(v,1),cnt,tag))
rows.sort(key=lambda r:-r[4])
with open("residual_hops_ideal_gt250.tsv","w") as f:
    f.write("corner\tlaunch_part\tcapture_part\tbase_damage_ps\tideal_equal_damage_ps\tpairs\ttag\n")
    for r in rows: f.write("\t".join(str(x) for x in r)+"\n")
tr=json.load(open("out/trim_k0.84_cap99999.json"))
json.dump(dict(window_ps=W,margin_ps=30,k_ff=K,least_trim_ps=tr["trim_tt"],ideal_equal_trim_ps=d),open("trims_ready11r.json","w"),indent=0)
print(len(rows),"rows >250")
