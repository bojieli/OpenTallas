#!/usr/bin/env python3
import json,sys
p=json.load(open(sys.argv[1]));m=p['modules']['ot_vms_rstop_static']
c={k:v for k,v in m['cells'].items() if 'u_ctrl' in k}
assert len(c)==9, len(c)
q=[tuple(v['connections']['source_q']+v['connections']['enable_q']) for v in c.values()]
assert len(set(q))==9
print('REPLICA_PRESERVATION_PASS nine instances/nine distinct source+enable outputs')
