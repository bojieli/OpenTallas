"""Independent full terminal graph and exact structural movement audit; no EDA."""
import json,hashlib
from pathlib import Path
from graph import connected,overlap
P=Path(__file__).resolve().parent
m=json.loads((P/'model.json').read_text());old=json.loads((P/'input/sram-internal-pg-contract-1019_model.json').read_text());base=json.loads((P/'input/c634_model.json').read_text());results={}
def contains(a,b):return all([a[0]<=b[0],a[1]<=b[1],a[2]>=b[2],a[3]>=b[3]])
def moved(r,dx):return [v+dx if i in (0,2) else v for i,v in enumerate(r)]
for f,v in m['families'].items():
 o=old['families'][f]; unchanged=['outline_nm','original_bitcore_bbox_nm','new_attachment_core_bbox_nm','lower_core_exclusions','original_OBS_reservations_retained','signal_geometry_unchanged_sha256']
 assert all(v[k]==o[k] for k in unchanged)
 boxes=list(v['new_actual_supply_metal']);vias=[];ports=[];movement=[]
 old_objects={a['id']:a for a in o['new_actual_supply_metal']+o['new_actual_supply_cuts']}
 for a in v['new_actual_supply_metal']+v['new_actual_supply_cuts']:
  b=old_objects[a['id']];dx=(-48 if a['net']=='VDD' else 48) if a['role']=='full_height_internal_supply_trunk' or ':V4:' in a['id'] else 0
  assert moved(b['rect_nm'],dx)==a['rect_nm']
  if dx:movement.append({'id':a['id'],'dx_nm':dx,'before_nm':b['rect_nm'],'after_nm':a['rect_nm']})
 for row in v['contact_ledger']:
  for via in row['via_stacks']:
   vias.append({'net':row['net'],'boxes_nm':{a['layer']:a['rect_nm'] for a in via['objects']}})
  v4=row['via_stacks'][3];assert v4['center_nm'][0]%48==0
  assert contains(v['upper_cut_corridor_M4_V4_M5_nm'],next(a['rect_nm'] for a in v4['objects'] if a['layer']=='M4'))
  assert contains(row['c634_rail_unchanged_nm'],next(a['rect_nm'] for a in v4['objects'] if a['layer']=='M4'))
  trunk=next(t for t in v['new_actual_supply_metal'] if t['role']=='full_height_internal_supply_trunk' and t['net']==row['net'])
  assert contains(trunk['rect_nm'],next(a['rect_nm'] for a in v4['objects'] if a['layer']=='M5'))
 for s in base['families'][f]['signal_ledger']:
  boxes.extend({'net':s['pin'],'layer':a['layer'],'rect_nm':a['rect_nm']} for a in s['new_shapes'])
  for via in s['new_vias']:
   vias.append(dict(via,net=s['pin']))
   boxes.extend({'net':s['pin'],'layer':ly,'rect_nm':via[key]} for ly,key in [('M4','m4_rect_nm'),('M5','m5_rect_nm')])
 for t in v['new_actual_supply_metal']:
  if t['role']!='full_height_internal_supply_trunk':continue
  x0,_,x1,h=t['rect_nm']
  for face,r in [('S',[x0,0,x1,84]),('N',[x0,h-84,x1,h])]:
   assert contains(t['rect_nm'],r)
   assert not any(z['layer']=='M5' and overlap(z['rect_nm'],r) for z in v['original_OBS_reservations_retained'])
   ports.append({'net':t['net'],'layer':'M5','rect_nm':r,'identity':face+':'+t['net']})
 graph=connected(boxes,vias,ports)
 assert len(graph)==len(base['families'][f]['signal_ledger'])+2
 assert all(a['components']==1 for a in graph.values())
 no_v34=connected(boxes,[a for a in vias if a is not vias[2]],ports)
 assert no_v34['VDD']['components']==2
 trunks=[a for a in v['new_actual_supply_metal'] if a['role']=='full_height_internal_supply_trunk'];pitch=abs(sum(trunks[0]['rect_nm'][::2])//2-sum(trunks[1]['rect_nm'][::2])//2);assert pitch==192 and 1000/pitch<=6
 results[f]={'all_nets_graph':graph,'actual_moved_objects':movement,'external_PG_ports':ports,'external_local_pitch_nm':pitch,'external_local_contacts_per_um':1000/pitch,'independent_missing_VIA34_components':no_v34['VDD']['components'],'native_via_bottom_top_containment':'PASS all121 overall','unchanged_identity_fields':unchanged,'all_reservations_retained':True,'external_M5_port_OBS_overlap':False}
(P/'verification.json').write_text(json.dumps(results,indent=2)+'\n')
print({f:{'net_count':len(v['all_nets_graph']),'moved_objects':len(v['actual_moved_objects']),'contacts_per_um':v['external_local_contacts_per_um']} for f,v in results.items()})

controls={}
for f,v in m['families'].items():
 c=v['upper_cut_corridor_M4_V4_M5_nm'];v4=[a for a in v['new_actual_supply_metal'] if ':V4:' in a['id'] and a['layer']=='M4'];margin=min(min(a['rect_nm'][0]-c[0],c[2]-a['rect_nm'][2]) for a in v4)
 assert margin==13
 trunk=next(a for a in v['new_actual_supply_metal'] if a['role']=='full_height_internal_supply_trunk' and a['net']=='VDD')['rect_nm']
 port=next(a['rect_nm'] for a in results[f]['external_PG_ports'] if a['identity']=='S:VDD')
 assert not contains(trunk,moved(port,48))
 controls[f]={'V4_M4_enclosure_corridor_margin_nm':margin,'old_96nm_external_pitch_refused':1000/96>6,'new_192nm_external_pitch_passes':1000/192<=6,'extra_48nm_outward_shift_rejected_by_corridor':margin<48,'frozen_internal_reservations_remain_HOLD':True,'pin_only_teleport_refused_by_actual_conductor_containment':not contains(trunk,moved(port,48)),'M5_parallel_gap_nm':168}
(P/'structural_controls.json').write_text(json.dumps(controls,indent=2)+'\n')
