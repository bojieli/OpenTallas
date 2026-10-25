import json,sys
from pathlib import Path; sys.path.insert(0,str(Path(__file__).resolve().parents[5]/"tools/die_plan"))
import kit_istations as K
P=json.load(open(sys.argv[1]))
ok=0;bad={}
for tn,T in P["partition_types"].items():
    if not tn.startswith("ot_s81sl_leaf__t"): continue
    try:
        K.core_stations(T,"ot_s81sl_leaf u_lf (",True,(4,0,0),[],[]); ok+=1
    except SystemExit as e:
        bad[tn]=str(e)[:160]
print("PASS",ok,"FAIL",len(bad))
import collections
c=collections.Counter(v.split(":")[1][:60] for v in bad.values())
for k,v in c.most_common(12): print(v,k)
