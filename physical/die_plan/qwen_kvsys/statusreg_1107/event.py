#!/usr/bin/env python3
"""KV-SLGLAND-2 11-07 STATUS-REG-1 plan event: landing_status_reg on the ring types with the measured lap_ok half-period miss.
No data cycle, no K change, no geometry change. usage: event.py PLAN_IN PLAN_OUT"""
import copy,json,sys
TYPES=["kv3_io_ft_v1","kv3_io_cor","kv3_io_cor_v1"]
a,b=sys.argv[1:3]; raw=json.load(open(a)); orig=copy.deepcopy(raw)
for t in TYPES:
    assert raw["partition_types"][t].get("landing_control_status_copy") is True,t
    raw["partition_types"][t]["landing_status_reg"]=True
for t in raw["partition_types"]:
    if t not in TYPES: assert raw["partition_types"][t]==orig["partition_types"][t]
assert {k:v for k,v in raw.items() if k!="partition_types"}=={k:v for k,v in orig.items() if k!="partition_types"}
json.dump(raw,open(b,"w"),indent=1); open(b,"a").write("\n")
print("SET",TYPES)
