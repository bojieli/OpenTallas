#!/usr/bin/env python3
"""Build coherent intermediate request calendar for actual landed PV coupling.

The native-calendar owner specifies a causal +3 shift on WS/ES and +6 on WN/EN.
Preserve each prior request target plus that explicit shift; final compiler DQ
must be measured again from the fully applied bind before image adoption.
"""
import argparse,json,re
p=argparse.ArgumentParser(description=__doc__);p.add_argument('groups');p.add_argument('previous');p.add_argument('--out',required=True);a=p.parse_args()
g=json.load(open(a.groups));d=json.load(open(a.previous));actual={}
for group in g['landing']:
 for m in group['members']:actual[(group['sink'],m['sink_port'],m['source'],m['asbuilt_stages'])]=m
shifts={};ff=0
for m in d['members']:
 q=re.fullmatch(r'vport_(WS|ES|WN|EN)_[0-3]',m['sink']);assert q,m
 shift=3 if q[1] in ['WS','ES'] else 6
 live=actual[(m['sink'],m['sink_port'],m['source'],m['asbuilt'])];bound=int(live['bound_stages']);target=int(m['landed'])+shift
 if bound>target:raise ValueError(f'causal request target insufficient: {m["sink"]}.{m["sink_port"]} {bound}>{target}')
 m.update(bound=bound,pad=target-bound,landed=target,previous_target=m['landed'],causal_pv_shift=shift)
 shifts[m['sink']]=shift;ff+=sum(hi-lo+1 for lo,hi in m['sink_bits'])*m['pad']
d['kind']='pv_landed_request_intermediate';d['note']=__doc__;d['summary']=dict(members=len(d['members']),causal_shift_by_port=shifts,logical_member_pad_ff_conservative=ff,final_compiler_DQ='REQUIRED from full coherent bind')
with open(a.out,'w') as f:json.dump(d,f,indent=1);f.write('\n')
print(d['summary'])
