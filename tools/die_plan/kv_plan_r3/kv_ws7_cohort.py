#!/usr/bin/env python3
"""Declare B37's actual WS7 hsl3.bgi cohort without changing geometry/cycles."""
import argparse,copy,json
p=argparse.ArgumentParser(description=__doc__);p.add_argument('plan');p.add_argument('--out',required=True);a=p.parse_args()
d=json.load(open(a.plan));old='kv3_pc_v3__cldeeb17a5';new=old+'__ws7'
d['partition_types'][new]=copy.deepcopy(d['partition_types'][old]);d['partition_types'][new]['module']=new
d['partition_types'][new]['note']+='; explicit WS7 hsl3.bgi actual uniformity cohort, same geometry/landing'
parts=[r for r in d['partitions'] if r['name']=='pc_WS_7'];assert len(parts)==1 and parts[0]['type']==old;parts[0]['type']=new
if old in d['reset'].get('in_sites',{}):d['reset']['in_sites'][new]=d['reset']['in_sites'][old]
with open(a.out,'w') as f:json.dump(d,f,indent=1);f.write('\n')
