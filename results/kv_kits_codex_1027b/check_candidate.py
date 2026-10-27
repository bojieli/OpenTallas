#!/usr/bin/env python3
import gzip, json, pathlib, sys
import numpy as np
W = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(W/"tools/die_plan")); sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import schema as S
from gen_phys import type_pins
from apply_ft_delta import apply
O = pathlib.Path(__file__).resolve().parent
raw = json.loads(gzip.decompress((O/"plan_before_plus1.json.gz").read_bytes()))
delta = json.loads((O/"ft_plus1_delta.json").read_text())
new = apply(raw, delta); model = S.Plan(new)
rows=[]
for tn in delta["types"]:
    pins={(bn,i):(x,y) for bn,i,_,x,y,_ in type_pins(model,tn)}
    for sl in model.types[tn]["ft_slots"]:
        a=np.array([pins[(sl["name"]+"_i",i)] for i in range(sl["width"]+1)])
        b=np.array([pins[(sl["name"]+"_o",i)] for i in range(sl["width"]+1)])
        cell=np.array(sl["bit_site_cell_um"])
        chain=[a,*[np.array(s)+cell/2 for s in sl["bit_sites_um"]],b]
        worst=max(float(np.abs(q-p).sum(axis=1).max()) for p,q in zip(chain,chain[1:]))
        rows.append(dict(type=tn,slot=sl["name"],max_bit_hop_um=worst))
assert max(r["max_bit_hop_um"] for r in rows)<=405
try:
    apply(new,delta)
except ValueError:
    pass
else:
    raise AssertionError("reapplying +1 cycle delta must fail")
bad=dict(raw); bad["partition_types"]=dict(raw["partition_types"]); tn=delta["types"][0]
bad["partition_types"][tn]=dict(raw["partition_types"][tn]);bad["partition_types"][tn]["outline_um"]=[1,1]
try:
    apply(bad,delta)
except ValueError:
    pass
else:
    raise AssertionError("changed-outline mutant must fail")
(O/"reach_receipt.json").write_text(json.dumps(dict(verdict="PASS",slots=len(rows),max_bit_hop_um=max(r["max_bit_hop_um"] for r in rows),limit_um=405,added_slots=200,changed_outline_mutant="REJECTED",double_apply_mutant="REJECTED",rows=rows),indent=1)+"\n")
print("REACH_PASS",len(rows),max(r["max_bit_hop_um"] for r in rows))
