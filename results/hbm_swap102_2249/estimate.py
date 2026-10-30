import json,copy,sys,hashlib
from pathlib import Path
R=Path('/srv/opentallas-scratch2/claude/codex-hbm-bind-2249');P=Path('/srv/opentallas-scratch2/claude/die-hbm-29/plan/d29d/die_plan.json');p=json.load(P.open());parts={x['name']:x for x in p['partitions']};T=p['partition_types'];V=dict(name='CODEX_SWAP_B102_B103',rowh={'A':1555.2,'C':1572.48})
for row,y in (('A',4510.08),('C',10385.28)):
 seq=sorted((x for x in p['partitions'] if x['name'].startswith('NW_') and abs(x['origin_um'][1]-y)<.01),key=lambda x:x['origin_um'][0]);pos=0
 for x in seq:
  assert abs(x['origin_um'][0]-pos)<.01,(row,x['name'],pos,x['origin_um']);assert T[x['type']]['outline_um'][1]==V['rowh'][row]
  pos+=T[x['type']]['outline_um'][0]
 V[row]=[x['name'] for x in seq]
a,b=V['A'].index('NW_b102'),V['A'].index('NW_b103');V['A'][a],V['A'][b]=V['A'][b],V['A'][a]
assert T[parts['NW_b102']['type']]['outline_um']==T[parts['NW_b103']['type']]['outline_um']
port={x['id']:x for x in p['ports']};affected=[]
for l in p['lanes']:
 if any(port[z][side]['part'] in ('NW_b102','NW_b103','NE_b102','NE_b103') for z in l['ports'] for side in ('src','dst')):affected.append(l['id'])
report=dict(source_sha256=hashlib.sha256(P.read_bytes()).hexdigest(),swapped_parts=['NW_b102','NW_b103','NE_b102','NE_b103'],width_um=708.48,old_b102_B013_shared_um=60.48,new_b102_B013_shared_um=492.48,required_payload_bits=2746,face_pin_layers=2,approx_pin_capacity=int(492.48*6),required_window_um=2747/6,affected_lanes=affected,outline_changes=0,core_local_coordinates_changed=False,clock_contract_changed=False,physical_verdict='ESTIMATE ONLY; legal routes/clock sidecars/G0 pending')
(R/'swap102_variant.json').write_text(json.dumps(V,indent=1));(R/'swap102_estimate.json').write_text(json.dumps(report,indent=1));print(json.dumps(report,indent=1))
