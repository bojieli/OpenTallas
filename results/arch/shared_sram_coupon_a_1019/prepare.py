#!/usr/bin/env python3
"""Prepare only the explicitly authorized diagnostic Stage A; no production views."""
import json,hashlib,copy
from pathlib import Path
P=Path(__file__).resolve().parent
load=lambda n:json.loads((P/'input'/n).read_text())
q=load('qwen.json'); s=load('sc2.json'); sm=load('sc2_model.json')
assert hashlib.sha256((P/'input/qwen.json').read_bytes()).hexdigest()=='55b2625c47f7354628d1a51a68d66bbd1b164e2acd92ba59456910f1620b4c11'
assert hashlib.sha256((P/'input/sc2.json').read_bytes()).hexdigest()=='daa85d7d249bb78510490343336164a6995b489288c79848ba984060dc757f24'
assert hashlib.sha256((P/'input/asap7_tech.lef').read_bytes()).hexdigest()=='7694bf4f8ef2f9745e4579f454788a0cf048e8605320f32d1d83ec540ed4ca41'
cases=[]
def overlap(a,b):return a[0]<b[2] and b[0]<a[2] and a[1]<b[3] and b[1]<a[3]
def translated(r,dx,dy):return[r[0]+dx,r[1]+dy,r[2]+dx,r[3]+dy]
for family,paths,pg in [('qwen',q['paths'],q['pg_rectangles']),('sc2',s,sm['pg_rectangles'])]:
 allshapes=[]; allvias=[]
 for p in paths:
  for shape in p['shapes']+p.get('retained_pads',[]):
   allshapes.append(dict(shape,net=p['pin']))
  for v in p['vias']:allvias.append(dict(v,net=p['pin']))
 for a in pg:allshapes.append(dict(a,net=a.get('net',a.get('pin','PG_UNKNOWN'))))
 clock='wclk' if family=='qwen' else 'clk'
 east=next(p for p in paths if p['face']=='E')
 selects=[(clock,'source'),('r_ce_in','source'),('rd_out[0]','source'),(east['pin'],'source'),('r_ce_in','vias')]
 for pin,kind in selects:
  p=next(x for x in paths if x['pin']==pin)
  anchor=p['preserved_anchor_nm'] if kind=='source' else p['vias'][0]['center_nm']
  box=[anchor[0]-500,anchor[1]-500,anchor[0]+500,anchor[1]+500]
  shapes=[]; vias=[]
  for a in allshapes:
   if overlap(a['rect_nm'],box):
    r=a['rect_nm'];shapes.append(dict(a,rect_nm=[max(r[0],box[0]),max(r[1],box[1]),min(r[2],box[2]),min(r[3],box[3])],source_rect_nm=r))
  for v in allvias:
   if any(overlap(v[k],box) for k in ['m4_rect_nm','m5_rect_nm']):vias.append(v)
  cases.append(dict(name=f'{family}_{pin}_{kind}',family=family,pin=pin,kind=kind,face=p['face'],pin_kind=p['kind'],source_anchor_nm=anchor,source_crop_nm=box,shapes=shapes,vias=vias,wire_status='ROUTED',expected='original native verdict; RECTONLY prediction conditional on visibility'))
# Seven independent causal/coverage controls; all integer nm, never fictitious subgrid.
def control(name,rects,expected,status='ROUTED'):
 cases.append(dict(name=name,family='control',pin='control',kind=name,source_anchor_nm=[0,0],shapes=[dict(layer='M4',net=net,rect_nm=r,role=name) for net,r in rects],vias=[],wire_status=status,expected=expected))
control('aligned_rectangle',[('a',[-264,-12,24,12])],'no inner-ROI RECTONLY')
step=[('a',[-264,-21,24,3]),('a',[0,-12,24,12])]
control('exact_9nm_step',step,'visible RECTONLY prediction')
control('all_fixed_9nm_step',step,'visibility negative; suppression possible; never qualification','FIXED')
control('spacing_23nm',[('a',[-144,-12,144,12]),('b',[-144,35,144,59])],'native spacing marker required')
control('disconnected_contact',[('a',[-264,-12,-10,12]),('a',[0,-12,24,12])],'independent graph disconnected required; DRC silence is insufficient')
control('old_track_phase',[('a',[-264,0,264,24])],'track-center coverage probe only; integer manufacturing grid')
control('width_33nm',[('a',[-264,-12,264,21])],'width-table coverage probe, not expected native fail')
for i,c in enumerate(cases):
 ax,ay=c['source_anchor_nm'];tx=1008+1920*(i%5);ty=1008+1920*(i//5)
 # Translation is a multiple of native 48nm pitch, preserving exact source phase.
 dx=((tx-ax)//48)*48;dy=((ty-ay)//48)*48
 c['translation_nm']=[dx,dy]; c['anchor_nm']=[ax+dx,ay+dy]; x,y=c['anchor_nm'];c['score_roi_nm']=[x-200,y-200,x+200,y+200]
 for a in c['shapes']:a['rect_nm']=translated(a['rect_nm'],dx,dy)
 for v in c['vias']:
  for key in ['cut_rect_nm','m4_rect_nm','m5_rect_nm']:v[key]=translated(v[key],dx,dy)
  v['center_nm']=[v['center_nm'][0]+dx,v['center_nm'][1]+dy]
 # Geometry connectivity is independent of net labels and native checker silence.
 target=[a for a in c['shapes'] if a['net']==c['pin'] or (c['family']=='control' and a['net']=='a')]
 nodes=[(a['layer'],a['rect_nm']) for a in target];edges={j:set() for j in range(len(nodes))}
 for a,(la,ra) in enumerate(nodes):
  for b,(lb,rb) in enumerate(nodes):
   if la==lb and overlap(ra,rb):edges[a].add(b)
 for v in c['vias']:
  if v['net']!=c['pin']:continue
  hits=[j for j,(l,r) in enumerate(nodes) if l in ('M4','M5') and overlap(r,v['m4_rect_nm' if l=='M4' else 'm5_rect_nm'])]
  for a in hits:edges[a].update(hits)
 unseen=set(edges);components=[]
 while unseen:
  todo=[unseen.pop()];comp=set(todo)
  while todo:
   a=todo.pop()
   for b in edges[a]-comp:comp.add(b);unseen.discard(b);todo.append(b)
  components.append(sorted(comp))
 c['independent_geometry_components']=components
assert next(c for c in cases if c['name']=='disconnected_contact')['independent_geometry_components'].__len__()==2
report=dict(status='STAGE_A_INPUT_ONLY_NO_NATIVE_VERDICT',outline_nm=[10000,10000],dbu_per_um=1000,manufacturing_grid_nm=1,cases=cases,source_notes=['No east read output exists; actual rd_out[0] W and first E pin separately retained.','All source, same-net and cross-net rectangles intersecting +/-500nm crop retained, complete native vias retained.','Only inner +/-200nm ROI scored; full native markers also preserved.','Fixed is diagnostic visibility control, never macro qualification.','Sub-grid control unsupported: integer DBU equals manufacturing grid.','No B/C access, routing, PG, or production geometry generated.'])
(P/'coupon.json').write_text(json.dumps(report,indent=2)+'\n')
(P/'empty.def').write_text('''VERSION 5.8 ;
DIVIDERCHAR "/" ;
BUSBITCHARS "[]" ;
DESIGN coupon_a ;
UNITS DISTANCE MICRONS 1000 ;
DIEAREA ( 0 0 ) ( 10000 10000 ) ;
TRACKS Y 3 DO 209 STEP 48 LAYER M4 ;
TRACKS X 0 DO 209 STEP 48 LAYER M5 ;
GCELLGRID X 0 DO 11 STEP 1000 ;
GCELLGRID Y 0 DO 11 STEP 1000 ;
END DESIGN
''')
print('prepared',len(cases),'cases',sum(len(c['shapes']) for c in cases),'rectangles',sum(len(c['vias']) for c in cases),'complete vias')
