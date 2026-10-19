import json,re,gzip,collections
from pathlib import Path
summary={};allrows=[]
for corner in ['TT','FF']:
 s=Path(f'out/min_inventory_{corner}.log').read_text();rows=[]
 for kind,target,body in re.findall(r'BEGIN_NATIVE_MIN_TARGET (FF|OUTPUT) ([^\n]+)\n(.*?)END_NATIVE_MIN_TARGET',s,re.S):
  z=re.findall(r'([-+0-9.]+)\s+slack \((MET|VIOLATED)\)',body);assert len(z)==1,(corner,target,body[-100:])
  assert 'Startpoint:' in body and 'Endpoint:' in body
  source=body.split('Startpoint:',1)[1].split('Endpoint:',1)[0].strip()
  role='raw_input_capture' if 'input port' in source else 'internal_capture' if kind=='FF' else 'registered_output_boundary'
  def last(p):
   v=re.findall(p,body);return float(v[-1]) if v else None
  slack=float(z[0][0]);required=last(r'([-+0-9.]+)\s+data required time');arrival=last(r'([-+0-9.]+)\s+data arrival time')
  r=dict(corner=corner,target_kind=kind,target=target,startpoint=source,role=role,min_slack_ps=slack,data_arrival_ps=arrival,data_required_ps=required,native_hold_constraint_ps=last(r'([-+0-9.]+)\s+library hold time'),clock_ideal=True,wire_rc_qualified=False,neighbor_qualified=False)
  if role=='raw_input_capture':
   r.update(provisional_upstream_delay_ps=30,upstream_external_delay_for_zero_slack_ps=30-slack,upstream_external_delay_for_30ps_slack_ps=60-slack,pin_earliest_for_30ps_margin_ps=required+30)
  rows.append(r)
 assert len(rows)==5208 and len({(r['target_kind'],r['target']) for r in rows})==5208
 roles={}
 for role,n in [('raw_input_capture',600),('internal_capture',2304),('registered_output_boundary',2304)]:
  a=[r for r in rows if r['role']==role];assert len(a)==n,(role,len(a))
  roles[role]=dict(endpoints=len(a),worst=min(a,key=lambda r:r['min_slack_ps']),negative_endpoints=sum(r['min_slack_ps']<0 for r in a),below_30ps_margin=sum(r['min_slack_ps']<30 for r in a))
 summary[corner]=dict(roles=roles,actual_ff_targets=2904,actual_output_targets=2304,global_endpoint_cap=None,every_endpoint_individually_queried=True)
 allrows+=rows
with gzip.open('out/min_endpoint_inventory.json.gz','wt')as f:json.dump(allrows,f,sort_keys=True)
Path('out/min_summary.json').write_text(json.dumps(dict(scope='uncapped per-actual-endpoint source timing queries; ideal clock and no wire RC; actual neighbor qualification OPEN',corners=summary,raw_input_ports=304,source_clock_domains=1,reset_targets=0,clock_slew_condition='ideal zero; library-table domain qualification required, not true physical minimum'),indent=2)+'\n')
