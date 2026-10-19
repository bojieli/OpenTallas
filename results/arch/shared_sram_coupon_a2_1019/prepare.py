import json,hashlib,copy
from pathlib import Path
P=Path(__file__).resolve().parent
m=json.loads((P/'input/model.json').read_text()); cases=[]
def overlap(a,b):return a[0]<b[2] and b[0]<a[2] and a[1]<b[3] and b[1]<a[3]
def trans(r,dx,dy):return [r[0]+dx,r[1]+dy,r[2]+dx,r[3]+dy]
assert m['choice']=={'core_and_signal_attachment_dy_nm':39,'old_native_lead_and_via_dy_nm':48,'PG_center_dy_nm':51,'PG_width_nm':120,'outline_height_increment_nm':48,'cycle_delta_proposed':0}
for fam,d in m['families'].items():
 paths=d['signal_ledger']; shapes=[dict(a,source_identity=f'signal:{p["pin"]}:{i}') for p in paths for i,a in enumerate(p['new_shapes'])]; vias=[dict(v,source_identity=f'via:{p["pin"]}:{i}') for p in paths for i,v in enumerate(p['new_vias'])]
 shapes += [dict(layer=a['layer'],net=a['net'],rect_nm=a['new_rect_nm'],role='conditional_PG',source_identity=f'PG:{a["id"]}') for a in d['PG_ledger']]
 chosen=[]
 for pin in ['wclk' if fam=='qwen' else 'clk','r_ce_in','rd_out[0]']:
  chosen.append(next(p for p in paths if p['pin']==pin))
 for face in ['W','E']:
  seq=sorted((p for p in paths if p['face']==face),key=lambda x:x['new_source_nm'][1]);chosen.extend([seq[0],seq[-1]])
 chosen=list({p['pin']:p for p in chosen}.values())
 for p in chosen:
  anchors=[('source',p['new_source_nm'])]
  if p['new_vias']:anchors += [('via_first',p['new_vias'][0]['center_nm']),('via_last',p['new_vias'][-1]['center_nm'])]
  for kind,anchor in anchors:
   box=[anchor[0]-500,anchor[1]-500,anchor[0]+500,anchor[1]+500]; ss=[]
   for a in shapes:
    if overlap(a['rect_nm'],box):
     r=a['rect_nm']; ss.append(dict(a,source_rect_nm=r,rect_nm=[max(r[0],box[0]),max(r[1],box[1]),min(r[2],box[2]),min(r[3],box[3])]))
   vv=[copy.deepcopy(v) for v in vias if any(overlap(v[k],box) for k in ['m4_rect_nm','m5_rect_nm'])]
   obs=[dict(a,identity=f'{fam}:OBS:{i}',interpretation='reservation only; not instantiated as routing metal or hidden') for i,a in enumerate(d['new_reserved_OBS']) if overlap(a['rect_nm'],box)]
   cases.append(dict(name=f'{fam}_{p["pin"]}_{kind}',family=fam,pin=p['pin'],pin_kind=p['kind'],face=p['face'],kind=kind,source_anchor_nm=anchor,source_crop_nm=box,shapes=ss,vias=vv,neighbor_OBS=obs,wire_status='ROUTED',expected='unmeasured new-master visible-wire representative only'))
def control(name,rects):
 cases.append(dict(name=name,family='control',pin='a',kind=name,source_anchor_nm=[0,0],shapes=[dict(layer='M4',net=n,rect_nm=r,role=name) for n,r in rects],vias=[],neighbor_OBS=[],wire_status='ROUTED'))
control('aligned_rectangle',[('a',[-264,-12,24,12])])
control('original_9nm_step',[('a',[-264,-21,24,3]),('a',[0,-12,24,12])])
control('spacing_23nm',[('a',[-144,-12,144,12]),('b',[-144,35,144,59])])
control('disconnected_contact',[('a',[-264,-12,-10,12]),('a',[0,-12,24,12])])
for i,c in enumerate(cases):
 ax,ay=c['source_anchor_nm'];dx=((1008+1920*(i%6)-ax)//48)*48;dy=((1008+1920*(i//6)-ay)//48)*48;c['translation_nm']=[dx,dy];c['anchor_nm']=[ax+dx,ay+dy];x,y=c['anchor_nm'];c['score_roi_nm']=[x-200,y-200,x+200,y+200]
 for a in c['shapes']:a['rect_nm']=trans(a['rect_nm'],dx,dy)
 for v in c['vias']:
  for k in ['m4_rect_nm','m5_rect_nm','cut_rect_nm']:v[k]=trans(v[k],dx,dy)
  v['center_nm']=[v['center_nm'][0]+dx,v['center_nm'][1]+dy]
 nodes=[(a['layer'],a['rect_nm']) for a in c['shapes'] if a['net']==c['pin']]
 for v in c['vias']:
  if v['net']==c['pin']:nodes.extend([('M4',v['m4_rect_nm']),('M5',v['m5_rect_nm'])])
 edges={j:set() for j in range(len(nodes))}
 for j,(la,ra) in enumerate(nodes):
  for k,(lb,rb) in enumerate(nodes):
   if la==lb and overlap(ra,rb):edges[j].add(k)
 for v in c['vias']:
  if v['net']==c['pin']:
   hits=[j for j,(l,r) in enumerate(nodes) if overlap(r,v['m4_rect_nm'] if l=='M4' else v['m5_rect_nm'])]
   for j in hits:edges[j].update(hits)
 unseen=set(edges);comps=[]
 while unseen:
  todo=[unseen.pop()];comp=set(todo)
  while todo:
   j=todo.pop()
   for k in edges[j]-comp:comp.add(k);unseen.discard(k);todo.append(k)
  comps.append(sorted(comp))
 c['independent_geometry_components']=comps
assert len(next(c for c in cases if c['name']=='disconnected_contact')['independent_geometry_components'])==2
out=dict(status='PREENGINE_GEOMETRY_EXACT_MODEL_C634',model_sha256=hashlib.sha256((P/'input/model.json').read_bytes()).hexdigest(),dbu_per_um=1000,outline_nm=[12500,12500],cases=cases,OBS_status='all intersecting identities preserved as reservations; no AP/PG qualification')
(P/'coupon.json').write_text(json.dumps(out,indent=2)+'\n')
(P/'empty.def').write_text('''VERSION 5.8 ;
DIVIDERCHAR "/" ;
BUSBITCHARS "[]" ;
DESIGN coupon_a2 ;
UNITS DISTANCE MICRONS 1000 ;
DIEAREA ( 0 0 ) ( 12500 12500 ) ;
TRACKS Y 3 DO 261 STEP 48 LAYER M4 ;
TRACKS X 0 DO 261 STEP 48 LAYER M5 ;
GCELLGRID X 0 DO 14 STEP 1000 ;
GCELLGRID Y 0 DO 14 STEP 1000 ;
END DESIGN
''')
print('cases',len(cases),'shapes',sum(len(c['shapes']) for c in cases),'vias',sum(len(c['vias']) for c in cases))
