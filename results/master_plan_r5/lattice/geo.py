import sys, json
sys.path.insert(0, sys.argv[1])
from pathlib import Path
import schema as S, infra_sites as IS, master_rulings as MR, master_plan as MP
P = S.Plan(S.load(sys.argv[2]), Path(sys.argv[2]))
parts, cores = MR.die_geometry(P, MP.core_to_type, IS.rect_pts)
json.dump(dict(parts=parts, cores=cores, types={p: P.parts[p]["type"] for p in P.parts}), open(sys.argv[3], "w"))
from collections import Counter
print(len(parts), len(cores))
print(Counter(c[6] for c in cores))
print(Counter(P.parts[p[4]]["type"] for p in parts).most_common(40))
