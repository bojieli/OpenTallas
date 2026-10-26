import json,sys,collections
sys.path.insert(0, sys.argv[1])
import master_plan as MP, schema as S, infra_sites as IS
plan=sys.argv[2]; ent=json.load(open(sys.argv[3]))
from pathlib import Path; P=S.Plan(S.load(plan), Path(plan))
rows=[]
for part in P.parts:
    tn=P.parts[part]["type"]; t=P.types[tn]
    for h in t.get("hard_cores",[]):
        e=ent.get(h["module"],{}).get("xy") or [h["outline_um"][0]/2,h["outline_um"][1]/2]
        isl=MP.entry_island(e)
        r=IS.rect_pts(P,part,MP.core_to_type(h,isl))
        rows.append((part,tn,h["module"],(r[0]+r[2])/2,(r[1]+r[3])/2))
print("cores",len(rows))
by=collections.Counter(r[1] for r in rows)
def lat(sel,name):
    L=MP.core_lattice([(r[3],r[4]) for r in sel])
    print(name, {a:{k:v[k] for k in ("pitch_um","lines","n_irregular","leaf_pitch_um","leaf_cover")} for a,v in L.items()})
lat(rows,"all")
lat([r for r in rows if not r[1].startswith("q_hub")],"no_hub")
lat([r for r in rows if r[1].startswith("q_sm")],"sm only")
lat([r for r in rows if not r[1].startswith("q_hub") and not r[1].startswith("q_sm")],"rest")
json.dump(rows,open(sys.argv[4],"w"))
