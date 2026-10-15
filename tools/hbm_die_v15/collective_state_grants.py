#!/usr/bin/env python3
"""Typed independent state-lane requests, not complete COLL parent placement."""
import argparse,hashlib,json,subprocess
from pathlib import Path
from leaf_grants_1103 import pins
ROOT=Path(__file__).resolve().parents[2]
SOURCE='rtl/hbm_accel/generic/collective/p2p/ot_hgi_coll_pring_static.sv'
PINFILE='results/arch/hbm_die_v15/collective_state_pins_1319.json'
FACES=dict(N=[('clk',1)],W=[('lp_we',1),('lp_tag',3),('lp_data',32),('acc_we',1),('acc_tag',3),
 ('acc_data',32),('carry_we',2),('carry0_tag',3),('carry1_tag',3),('carry0_src',2),('carry1_src',2),
 ('carry0_data',32),('carry1_data',32),('read_add',1),('read_tx',1),('read_rr',1),('read_rhs_acc',1),
 ('read_tx_acc',1),('add_tag',3),('tx_tag',3),('rr_tag',3),('add_src',2)],
 E=[('rhs_add',32),('carry_add',32),('tx_data',32),('acc_rr',32)])

def apply(c,ref):
 raw=subprocess.check_output(['git','-C',str(ROOT),'show',ref+':'+SOURCE]);ps=pins(FACES,(51.84,51.84))
 assert sum(b for v in FACES.values() for _,b in v)==293
 io=dict(schema='opentallas.hbm_v15.collective_state_pins.v1',top='ot_hgi_coll_pring_static_state_lane',
  outline_um=[51.84,51.84],source_ref=ref,source_sha256=hashlib.sha256(raw).hexdigest(),pins=ps,
  pin_ranges={p['name'].split('[')[0]:p['span_um'] for p in ps},
  scope='die-assigned independent component windows; exact routed bit positions/native boundary and complete parent graph remain OPEN')
 blob=(json.dumps(io,indent=1)+'\n').encode();c['slots']=[s for s in c['slots'] if not s.get('collective_state_grant_1319')]
 parents={s['name']:s for s in c['slots']}
 for q in ('SW','SE','NW','NE'):
  parent='coll_'+q;pa=parents[parent]
  for k in range(8):
   x,y=200+(k%4)*62.64,21.6+(k//4)*62.64
   assert x+51.84<=pa['outline']['w'] and y+51.84<=pa['outline']['h']
   for other in c['slots']:
    if other.get('parent')!=parent:continue
    o=other['origin'];w,h=other['outline']['w'],other['outline']['h']
    assert not(x<o['x']+w and o['x']<x+51.84 and y<o['y']+h and o['y']<y+51.84),(parent,k,other['name'])
   c['slots'].append(dict(name=f'{parent}_state{k}',cell='ot_hgi_coll_pring_static_state_lane',source=SOURCE,
    source_sha256=io['source_sha256'],source_prerequisite=ref,params={},kind='tile',parent=parent,
    instance_pending='actual independent state lane; source-pinned parent child path/registered peer graph still OPEN',
    outline=dict(w=51.84,h=51.84),origin=dict(x=round(x,6),y=round(y,6),orient='R0'),pins=ps,
    clock_entry=dict(pin='clk',face='N',layer='M5',offset=ps[0]['offset']),clock_domain='stream',clock_period_ps=833.333333,
    io_budget=dict(in_delay_frac=.2,out_delay_frac=.2),pg_layer='M5',strap_layer='M6',signal_max_layer='M5',layer_cap='M5',layer_rule='tile',
    version=1,grant='diagnostic_component_child',collective_state_grant_1319=True,measured_std_um2=1058.95998,measured_ff=1664,
    assigned_pin_file=PINFILE,assigned_pin_file_sha256=hashlib.sha256(blob).hexdigest(),
    qualification_scope='independent actual 293-port state leaf; no parent clock/pin/reach/packing/timing qualification inherited'))
 return c,blob

def main():
 a=argparse.ArgumentParser(description=__doc__);a.add_argument('--contract',type=Path,required=True);a.add_argument('--out',type=Path,required=True);a.add_argument('--source-ref',default='3729cb8fc');o=a.parse_args()
 c,b=apply(json.loads(o.contract.read_text()),o.source_ref);(ROOT/PINFILE).write_bytes(b);o.out.write_text(json.dumps(c,indent=1)+'\n');print('32 independent 51.84-square state requests; complete COLL parent OPEN')
if __name__=='__main__':main()
