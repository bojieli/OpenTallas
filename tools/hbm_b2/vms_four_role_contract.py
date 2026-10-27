#!/usr/bin/env python3
"""Trace the released four-role VM service graph from the actual native top.

The unified plan retains four logical VM roles in two physical hub regions.
This is not the historical B2 two-stop remaster/drop-port graph.
"""
import argparse,json
from pathlib import Path
from b2_top import Die,parse_expr
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--native-top',type=Path,required=True);p.add_argument('--asbuilt',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
a=p.parse_args();cfg=json.loads(a.asbuilt.read_text());d=Die(a.native_top,cfg['transport'])
slots={'SW':('NW_hub',0,0,2),'SE':('NE_hub',0,1,0),'NW':('NW_hub',1,2,0),'NE':('NE_hub',1,3,0)}
roles={}
for q,(hub,local,sid,nc) in slots.items():
 name='hb_vms_'+q;obj=d.insts[name];con=obj['conns'];pins={}
 for pn in ['cq','cr','client_seq','response_enable','response_seq','bank_client','replay_source','cw_in','ccw_in']:
  if pn in con:pins[pn]=d.resolve(parse_expr(con[pn],d.widths))
 roles[q]=dict(source_instance=name,source_module=obj['master'],logical_sid=sid,scalar_clients=nc,
               proposed_physical_slot=dict(partition=hub,service_q=local),source_ports=pins,
               source_widths={pn:sum(s[0][1] if s[0][0]=='c' else s[0][3]-s[0][2]+1 for s in bs) for pn,bs in pins.items()})
result=dict(schema='opentallas.hbm.vms_four_role_contract.v1',status='SOURCE_GRAPH_ONLY_PENDING_PLAN_BIND',
            logical_roles=roles,ring_stops=4,physical_ring_cw_order=['SW','SE','NE','NW'],
            source_policy='Use existing main four-stop masters and primitives. Do not apply make_wiring.py R-VM NW2/NE2 remaster or cw/ccw/replay_source drop_ports for the canonical unified four-role graph.',
            latency_policy='Traced register ages are historical reference only; bind and price new plan stations from the actual composed graph.',
            remaining=['Actual unified source composition and physical partition mapping','Static calendar, request/response identity, root-client CQ/CR and source-graph exactness on current plan'])
a.out.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({q:{k:v for k,v in x.items() if k not in ['source_ports']} for q,x in roles.items()},indent=2))
