import json, hashlib, math, gzip
from pathlib import Path
P=Path(__file__).resolve().parent
m=json.loads((P/'input/model.json').read_text())
assert hashlib.sha256((P/'input/model.json').read_bytes()).hexdigest()=='033b2a0e1522a9bd28b3ab9a35df88d394175fa06fbf6dca0e6f48b12e97146a'
a2=json.loads((P/'input/a2_coupon.json').read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def hit(a,b):return min(a[2],b[2])>max(a[0],b[0]) and min(a[3],b[3])>max(a[1],b[1])
def gap(a,b):return [max(0,a[0]-b[2],b[0]-a[2]),max(0,a[1]-b[3],b[1]-a[3])]
out={'status':'PROPOSAL_ONLY_NO_NATIVE_EXECUTION','source_commit':'c634d1540','A2_commit':'cf63992e4','input_sha256':{p.name:sha(p) for p in sorted((P/'input').iterdir())},'families':{}}
summary={}
for fam,d in m['families'].items():
 shapes=[];vias=[]
 for p in d['signal_ledger']:
  for i,s in enumerate(p['new_shapes']):shapes.append(dict(s,identity=f'{fam}:signal:{p["pin"]}:{i}',pin=p['pin']))
  for i,v in enumerate(p['new_vias']):
   ident=f'{fam}:via:{p["pin"]}:{i}';vias.append(dict(v,identity=ident))
   for layer,key in [('M4','m4_rect_nm'),('M5','m5_rect_nm'),('V4','cut_rect_nm')]:shapes.append(dict(identity=f'{ident}:{layer}',layer=layer,net=v['net'],rect_nm=v[key],role='via_cut' if layer=='V4' else 'via_enclosure',via_identity=ident))
 for s in d['PG_ledger']:shapes.append(dict(identity=f'{fam}:PG:{s["id"]}',net=s['net'],layer=s['layer'],rect_nm=s['new_rect_nm'],role='conditional_PG'))
 obs=[dict(s,identity=f'{fam}:OBS:{i}',interpretation='conditional reservation, NOT real metal and NOT hidden')for i,s in enumerate(d['new_reserved_OBS'])]
 for s in shapes:s['intersecting_OBS']=[o['identity'] for o in obs if o['layer']==s['layer'] and hit(o['rect_nm'],s['rect_nm'])]
 # Complete per-layer near-neighbor identity inventory; all shapes are retained globally,
 # so this diagnostic 200nm list never limits native checker context.
 neighbors=[]
 for i,a in enumerate(shapes):
  for b in shapes[i+1:]:
   g=gap(a['rect_nm'],b['rect_nm'])
   if max(g)<=200:neighbors.append(dict(a=a['identity'],b=b['identity'],gap_xy_nm=g,same_net=a['net']==b['net'],same_layer=a['layer']==b['layer'],layers=[a['layer'],b['layer']],overlap_positive_area=hit(a['rect_nm'],b['rect_nm'])))
 networks=[]
 for net in [p['pin'] for p in d['signal_ledger']]+['VDD','VSS']:
  nodes=[s for s in shapes if s['net']==net];edges={s['identity']:set() for s in nodes}
  for i,a in enumerate(nodes):
   for b in nodes[i+1:]:
    connect=a['layer']==b['layer'] and hit(a['rect_nm'],b['rect_nm'])
    if a.get('via_identity') and a.get('via_identity')==b.get('via_identity'):
     # A via joins routing layers only through its ACTUAL positive-area cut
     # within each complete enclosure. No same-net or bare-layer shortcut.
     v=next(v for v in vias if v['identity']==a['via_identity'])
     cut=v['cut_rect_nm']; connect=all(r[0]<=cut[0] and r[1]<=cut[1] and r[2]>=cut[2] and r[3]>=cut[3] for r in [v['m4_rect_nm'],v['m5_rect_nm']])
    if connect:edges[a['identity']].add(b['identity']);edges[b['identity']].add(a['identity'])
  unseen=set(edges);components=[]
  while unseen:
   todo=[unseen.pop()];c=set(todo)
   while todo:
    for j in edges[todo.pop()]-c:c.add(j);unseen.discard(j);todo.append(j)
   components.append(sorted(c))
  networks.append(dict(net=net,node_count=len(nodes),components=components,component_count=len(components),electrical_attachment='UNPROVED internal core/PG contacts; geometry only'))
 assert all(n['component_count']==1 for n in networks if n['net']not in ['VDD','VSS'])
 for v in vias:
  x,y=v['center_nm'];assert v['cut_rect_nm']==[x-12,y-12,x+12,y+12]
  assert v['m4_rect_nm']==[x-23,y-12,x+23,y+12] and v['m5_rect_nm']==[x-12,y-23,x+12,y+23]
 w,h=d['new_outline_nm'];assert all(0<=s['rect_nm'][0]<s['rect_nm'][2]<=w and 0<=s['rect_nm'][1]<s['rect_nm'][3]<=h for s in shapes)
 count=dict(signal_nets=d['signal_count'],signal_rectangles=sum(len(p['new_shapes'])for p in d['signal_ledger']),complete_vias=len(vias),via_enclosure_rectangles=2*len(vias),via_cut_rectangles=len(vias),PG_rectangles=len(d['PG_ledger']),OBS_reservations=len(obs),all_native_metal_cut_boxes=len(shapes),native_encoder_objects=sum(len(p['new_shapes'])for p in d['signal_ledger'])+len(vias)+len(d['PG_ledger']),neighbor_pairs_within_200nm=len(neighbors),same_layer_cross_net_positive_overlaps=sum(n['same_layer'] and not n['same_net'] and n['overlap_positive_area']for n in neighbors),PG_components={n['net']:n['component_count']for n in networks if n['net']in ['VDD','VSS']},OBS_intersection_pairs=sum(len(s['intersecting_OBS'])for s in shapes))
 out['families'][fam]=dict(master=d['master'],outline_nm=d['new_outline_nm'],full_native_roi_dbu=[0,0,w,h],required_track_phase_nm={'M4Y':3,'M5X':0,'pitch':48},orientation='R0 only',counts=count,shapes=shapes,vias=vias,conditional_OBS=obs,neighbors=neighbors,geometry_networks=networks)
 summary[fam]=count
out['original_controls']=[c for c in a2['cases'] if c['family']=='control']
assert len(out['original_controls'])==4
payload=(json.dumps(out,indent=2)+'\n').encode()
(P/'inventory.json.gz').write_bytes(gzip.compress(payload,mtime=0))
summary['payload_bytes']={'inventory_json':len(payload),'model_json':(P/'input/model.json').stat().st_size,'tech_lef':(P/'input/asap7_tech.lef').stat().st_size,'control_input':(P/'input/a2_coupon.json').stat().st_size}
summary['total_encoder_objects']=sum(v['native_encoder_objects']for v in summary.values()if isinstance(v,dict)and 'native_encoder_objects'in v)+sum(len(c['shapes'])+len(c['vias'])for c in out['original_controls'])
summary['A2_measured']={'rectangles':477,'vias':130,'encoder_objects':607,'elapsed_s':0.79,'peak_KiB':249580,'staged_disk_B':6988074,'native_invocations':33}
ratio=summary['total_encoder_objects']/607
summary['resource_proposal']={'encoder_object_ratio_to_A2':ratio,'linear_object_scaled_peak_KiB':math.ceil(249580*ratio),'linear_object_scaled_disk_B':math.ceil(6988074*ratio),'CPU':1,'RAM_GiB':4,'disk_GiB':2,'placement':'unpinned ot-run after ROOT grant and actual measured host memory/disk admission','engines':3,'native_invocations':9,'wall_deadline':None,'engine_plan':['Qwen full master: global + full-outline ROI','SC2 full master: global + full-outline ROI','unchanged four controls: global + four control ROIs']}
(P/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
