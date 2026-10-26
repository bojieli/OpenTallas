import json,sys,collections,re
sys.path.insert(0,sys.argv[1]); import master_plan as MP
rows=json.load(open(sys.argv[2]))
fam=lambda tn: re.sub(r"\d+$","",re.sub(r"_n[we]$","",tn))
def L(sel):
    if len(sel)<3: return None
    l=MP.core_lattice([(r[3],r[4]) for r in sel]); return {a:(v.get("lines"),v.get("n_irregular"),v.get("leaf_pitch_um"),v.get("leaf_cover")) for a,v in l.items()}
g=collections.defaultdict(list)
for r in rows: g[fam(r[1])].append(r)
for f,s in sorted(g.items(),key=lambda x:-len(x[1])): print(f,len(s),L(s))
# what fraction of all x-lines involve hubs+SM vs rest
for drop in (["q_hub_nw","q_hub_ne"],["q_hub_nw","q_hub_ne","q_su","q_b"],):
    sel=[r for r in rows if not any(r[1].startswith(d) for d in drop)]
    print("drop",drop,len(sel),L(sel))
