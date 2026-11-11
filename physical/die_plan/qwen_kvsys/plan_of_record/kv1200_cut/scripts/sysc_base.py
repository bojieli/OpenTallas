#!/usr/bin/env python3
"""DIE-KV-98: kv3_sys_c back to kvr2 (the KV-PLAN-2 kvfix1 overlay's 0.864-um x shift of its 6 contents makes the strict bind fail:
EMIT kv3_sys_c original rst_n_t31 D=rst_rl_80 != literal predecessor rst_rl_64; plan with kvr2 sys_c binds RC 0, 0 errors).
usage: sysc_base.py KVR2_PLAN PLAN_IN PLAN_OUT ; and asbuilt_rel: strip the dkv97/src_zbk/ absolute prefix from asbuilt.json so paths resolve in the bound src."""
import json, sys
b = json.load(open(sys.argv[1])); p = json.load(open(sys.argv[2]))
p["partition_types"]["kv3_sys_c"] = b["partition_types"]["kv3_sys_c"]
json.dump(p, open(sys.argv[3], "w"), indent=1); open(sys.argv[3], "a").write("\n")
