import json,sys,statistics as S
from collections import Counter
d=json.load(open(sys.argv[1])); s=d["summary"]; R={g["region"]:g for g in d["regions"]}
xs=d["crossings"]; T=833.0
fail=[o for o in xs if not o.get("depth")]
def path(u,v):
    def up(x):
        p=[x]
        while R[x]["start_from"]: x=R[x]["start_from"]["parent"]; p.append(x)
        return p
    pu,pv=up(u),up(v); su=set(pu); c=next(x for x in pv if x in su)
    return pu[:pu.index(c)]+pv[:pv.index(c)]
amb={g["region"] for g in d["regions"] if g["start_from"] and g["start_from"]["sync_values"]>1}
print("tree edges",s["tree_edges"],"clean",s["tree_edges_clean"],"max depth",s["max_tree_depth"],"fail",s["fail"])
for name,grp in (("fail",fail),("all nontree",[o for o in xs if o.get("kind")=="nontree"])):
    hops=[len(path(o["src"],o["dst"])) for o in grp]; ah=[sum(1 for x in path(o["src"],o["dst"]) if x in amb) for o in grp]
    pa=[o.get("path_ambiguous_cycles",0) for o in grp]
    print(name,len(grp),"start-hops med/max",S.median(hops) if hops else None,max(hops,default=0),"amb edges on path med/max",S.median(ah) if ah else None,max(ah,default=0),"path amb cyc med/max",S.median(pa) if pa else None,max(pa,default=0))
w=[o["L_width_ps"] for o in xs if o.get("L_width_ps") is not None]
print("width med/p90/max", S.median(w), sorted(w)[int(.9*len(w))], max(w))
