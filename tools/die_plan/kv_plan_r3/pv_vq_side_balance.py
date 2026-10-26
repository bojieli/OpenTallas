#!/usr/bin/env python3
"""Pad actual fast VPORT side1 request paths to the already-priced slow-side RT."""
import argparse,json,re
p=argparse.ArgumentParser(description=__doc__);p.add_argument('groups');p.add_argument('ages');p.add_argument('--out',required=True);a=p.parse_args();g=json.load(open(a.groups));ages=json.load(open(a.ages));rows=[];seen={};ff=0
for group in g['landing']:
 for m in group['members']:
  match=re.fullmatch(r'(vport_(?:WS|WN|ES|EN)_[0-3])\.vq1_(t|valid)',m['source'])
  if not match:continue
  v=match[1];sides=ages['vport'][v]['sides'];delta=sides[0]-sides[1];assert delta>0 and m['sink_port']=='vreq'
  target=m['landed_stages']+delta;pad=target-m['bound_stages'];assert pad>=0;bits=m['sink_bits'];ff+=sum(hi-lo+1 for lo,hi in bits)*delta;seen[v]=seen.get(v,0)+1
  rows.append(dict(id=f"{group['sink']}.{m['sink_port']}"+''.join(f'[{lo}:{hi}]' for lo,hi in bits)+f"<-{m['source']}@{m['asbuilt_stages']}",sink=group['sink'],sink_part=group['sink_part'],src_part=group['src_part'],sink_port=m['sink_port'],sink_bits=bits,source=m['source'],source_bits=m['source_bits'],asbuilt=m['asbuilt_stages'],bound=m['bound_stages'],pad=pad,landed=target,lane=m['lane'],side1_extra=delta))
assert len(seen)==16 and set(seen.values())=={2},seen
out=dict(schema='opentallas.die_plan.r8_extra.v1',die='qwen_kvsys',kind='pv_vq_side1_balance',note=__doc__+' Overall RT=max and RL unchanged; actual emitted footprints and image remain gates.',members=rows,summary=dict(members=len(rows),additional_request_ff=ff,RT_change=0,RL_change=0))
with open(a.out,'w') as f:json.dump(out,f,indent=1);f.write('\n')
print(out['summary'])
