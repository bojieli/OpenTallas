#!/usr/bin/env python3
"""One source-bound S58 representative placement and exclusion model, no flow.
Complete catalog frames are preserved. Actual LEF pins/OBS are translated;
phase extension is an analytical upper screen, never a routed PG guarantee.
"""
import gzip,hashlib,json,math,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'results/uarch/dsrom_constructive_service_binding_20261002'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def read(name): return json.loads((BASE/'inputs'/name).read_text())
def rect_area(r): return (r[2]-r[0])*(r[3]-r[1])
def overlap(a,b): return max(a[0],b[0])<min(a[2],b[2]) and max(a[1],b[1])<min(a[3],b[3])
def disjoint(rows):
 active=[]
 for name,rect in sorted(rows,key=lambda x:x[1][0]):
  active=[(n,r) for n,r in active if r[2]>rect[0]]
  for n,r in active:
   if overlap(r,rect): raise ValueError(f'overlap {name}/{n}')
  active.append((name,rect))
def lef(name):
 text=(BASE/'inputs'/name).read_text(); size=re.search(r'\bSIZE ([\d.]+) BY ([\d.]+)',text)
 w,h=[round(float(v)*1000) for v in size.groups()]
 pins=[]
 for m in re.finditer(r'\bPIN\s+(\S+)\s+(.*?)\n\s*END\s+\1\s',text,re.S):
  use=re.search(r'\bUSE (\w+)',m[2]); layer=None
  for s in re.finditer(r'LAYER\s+(\w+)\s*;|RECT\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*;',m[2]):
   if s[1]:layer=s[1]
   else:pins.append(dict(pin=m[1],use=use[1] if use else 'SIGNAL',layer=layer,bbox_DBU=[round(float(v)*1000) for v in s.groups()[1:]]))
 obs=[]
 for section in re.finditer(r'\bOBS\s+(.*?)\n\s*END',text,re.S):
  layer=None
  for s in re.finditer(r'LAYER\s+(\w+)\s*;|RECT\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*;',section[1]):
   if s[1]:layer=s[1]
   else:obs.append(dict(layer=layer,bbox_DBU=[round(float(v)*1000) for v in s.groups()[1:]]))
 assert pins and obs
 return dict(size_DBU=[w,h],pins=pins,OBS=obs)
def translate(rect,x,y,size,orientation='R0'):
 w,h=size;a,b,c,d=rect
 if orientation in ('MY','R180'):a,c=w-c,w-a
 if orientation in ('MX','R180'):b,d=h-d,h-b
 if orientation not in ('R0','MY','MX','R180'):raise ValueError('unsupported orientation')
 return [a+x,b+y,c+x,d+y]
def phases(grid,layer,lo,hi):
 row=next(r for r in grid['grids'] if r['layer']==layer)
 pos=set()
 for start,count,pitch in row['Y']:
  phase=start%pitch;first=phase+math.ceil((lo-phase)/pitch)*pitch
  pos.update(range(first,hi+1,pitch))
 return pos

def build():
 receipt=json.loads((BASE/'input_receipt.json').read_text())
 for name,r in receipt['inputs'].items():assert sha(BASE/'inputs'/name)==r['sha256'],name
 b=read('budget.json');s=read('service_model.json');o=read('overlay.json');f=read('frames.json');g=read('DS_grid.json');old=read('legacy_equation_fragments.json')
 assert b['candidate']=='DS4096-TP4-S58-PAIR1'
 service=[(r['name'],r['bbox_DBU']) for r in o['rectangles']];disjoint(service)
 named=sum(rect_area(r) for _,r in service)/1e12
 inherited=b['exact_once_area_ledger_mm2']['inherited_service_routes_clockPG_debit']
 hub=old['hub_block'];footprint=416.76/7102;slot_area=9931*footprint
 hub_loss=(hub['block_mm2']-hub['stream_unit_ledger_mm2'])*(1+hub['switch_fraction'])
 overhead=max(0,.125*814.982-(118.426-64.902));pre_fill=slot_area-hub_loss-overhead
 residual=old['reticle_alternative']['residual_field_debit_mm2'];corr=s['geometry']['native_bidirectional_extra_service_rectangle_mm2']
 terms={'858_minus_legacy9931_slot_area':858-slot_area,'old_hub_expansion_adjustment':hub_loss,'net_old12p5_overhead_after_old_spare_credit':overhead,'old10percent_field_fill_escrow':.1*pre_fill,'constrained_old_displacement_after_fill':.9*residual,'native_bidirectional_corridor_correction':corr}
 assert abs(sum(terms.values())-inherited)<1e-7
 # Preserve all declared complete-pair IDs, including unused and immutable slots.
 bf={i*4096//724 for i in range(724)};field=[];x=y=4320;rowh=0
 for pair in range(4096):
  cls='BF16_column_pair' if pair in bf else 'q_pair';dim=f['classes'][cls]['outline_um'];w,h=[round(v*1000) for v in dim]
  if x+w+4320>33000000:x=4320;y+=rowh+8640;rowh=0
  box=[x,y,x+w,y+h];field.append(dict(pair_id=pair,source_class=cls,bbox_DBU=box,orientation='R0',physical4096_leaves=4,hard_abstract_available=False))
  x+=w+8640;rowh=max(rowh,h)
 assert max(r['bbox_DBU'][3] for r in field)<16000000
 disjoint([(f'pair{r["pair_id"]}',r['bbox_DBU']) for r in field]+service)
 assert abs(sum(rect_area(r['bbox_DBU']) for r in field)/1e12-b['physical_array']['catalog_full_compiled_frame_mm2'])<1e-8
 # Reserve the four additional named charges disjointly, without embedding
 # them in catalog frames. These source-sized proxy rectangles have no hard
 # abstract and cannot stand in for their actual macro/control placement.
 ledger=b['exact_once_area_ledger_mm2'];additional=[]
 next_y=math.ceil((max(r['bbox_DBU'][3] for r in field)+8640)/2160)*2160
 for name,key in [('CFG_ROM_AND_LOCAL_WORDMUX','config_prospective_body_plus_local_mux'),
                  ('DECLARED_RETURN_FF50_PROXY','declared_return_FF50_proxy'),
                  ('RNE_BF724_PROXY','RNE_BF724_upper_proxy'),
                  ('WAKE_FULL_DECLARATION_PROXY','WAKE_full_compiled_upper_proxy')]:
  cost=ledger[key];height=math.ceil(cost*1e12/33000000/2160)*2160
  box=[0,next_y,33000000,next_y+height];next_y+=height+8640
  additional.append(dict(name=name,bbox_DBU=box,priced_mm2=cost,reserved_mm2=rect_area(box)/1e12,hard_abstract_available=False))
 assert next_y<16000000
 disjoint([(f'pair{r["pair_id"]}',r['bbox_DBU']) for r in field]+service+[(r['name'],r['bbox_DBU']) for r in additional])
 providers=[json.loads(line) for line in gzip.decompress((BASE/'inputs/HE_providers.jsonl.gz').read_bytes()).splitlines()]
 he=next(r for r in providers if r['kind']=='HE' and r['layer']==0)
 assert he['pairs']==[1792,1824,1856,1888,1920,1952,1984,2016]
 SRAM=lef('SRAM.lef');ROM=lef('ROM.lef');shapes=[]
 for macro in s['collector_macros']:
  body=[round(v*1000) for v in macro['candidate_anchor_body_um']];orient=macro['orientation']
  for kind in ['pins','OBS']:
   for p in SRAM[kind]:shapes.append(dict(p,kind=kind,instance=macro['instance'],bbox_DBU=translate(p['bbox_DBU'],body[0],body[1],SRAM['size_DBU'],orient)))
 # Explicit real leaf-body packing for immutable HE owners. Adjacent compute is
 # reserved by its catalog frame, but no complete-element endpoint/OBS is invented.
 he_leaves=[];w,h=ROM['size_DBU']
 for pair in he['pairs']:
  frame=field[pair]['bbox_DBU']
  assert frame[2]-frame[0]>=2*w and frame[3]-frame[1]>=2*h
  for slot in range(2):
   for pp in range(2):
    px=frame[0]+slot*w;py=frame[1]+pp*h;inst=f'candidate_stage0.pair{pair}.slot{slot}.pp{pp}'
    he_leaves.append(dict(instance=inst,pair_id=pair,logical_slot=slot,PP_parity=pp,bbox_DBU=[px,py,px+w,py+h],master='ot_rom_4096x274_m8',source_placement=False))
    for kind in ['pins','OBS']:
     for p in ROM[kind]:shapes.append(dict(p,kind=kind,instance=inst,bbox_DBU=translate(p['bbox_DBU'],px,py,ROM['size_DBU'])))
 band=next(r for r in s['routing_bands'] if r['name']=='collector_combined');bbox=[round(v*1000) for v in band['candidate_anchor_band_um']]
 capacity=[]
 for layer in ['M2','M4']:
  tracks=phases(g,layer,bbox[1],bbox[3]);blocked=set();hits=[]
  for shape in shapes:
   a=shape['bbox_DBU']
   if (shape['layer']==layer and max(a[0],bbox[0])<min(a[2],bbox[2])
       and a[1]<=bbox[3] and a[3]>=bbox[1]):
    hit={p for p in tracks if a[1]<=p<=a[3]}
    if hit:blocked|=hit;hits.append(shape['instance']+'/'+shape.get('pin',shape['kind']))
  # Halo bodies are charged separately and unioned, not added twice to OBS.
  for macro in s['collector_macros']:
   a=[round(v*1000) for v in macro['candidate_anchor_body_um']];a=[a[0]-4320,a[1]-4320,a[2]+4320,a[3]+4320]
   if max(a[0],bbox[0])<min(a[2],bbox[2]):blocked|={p for p in tracks if a[1]<=p<=a[3]}
  capacity.append(dict(layer=layer,phase_extended_positions=len(tracks),translated_pin_OBS_halo_blocked=len(blocked),remaining_before_parent_PG_clock_vias=len(tracks)-len(blocked),intersections=hits))
 gross=sum(r['remaining_before_parent_PG_clock_vias'] for r in capacity)
 required=20909
 return dict(schema='opentallas.dsrom.constructive-service-binding.v1',candidate=b['candidate'],source_receipt_sha256=sha(BASE/'input_receipt.json'),
  inherited_area_reconciliation=dict(inherited_mm2=inherited,source_equation_terms_mm2=terms,source_generator='inputs/reservation_generator.py:product_usable plus reticle residual and corridor correction',service_rectangle_union_mm2=named,envelope_mm2=s['geometry']['service_envelope_gross_mm2'],rectangle_to_envelope_padding_mm2=s['geometry']['service_envelope_gross_mm2']-named,inherited_minus_named_rectangles_mm2=inherited-named,containment_credit_mm2=0,qualification='Complement of historical analytical field allowance, not measured hard-instance area. No automatic subtraction; replacement requires actual whole-die instance union and exclusions.'),
  representative=dict(declared_pairs=4096,BFdual_pairs=724,q_pairs=3372,weight_leaves=16384,field_frame_union_mm2=sum(rect_area(r['bbox_DBU']) for r in field)/1e12,field_max_y_DBU=max(r['bbox_DBU'][3] for r in field),all_named_service_rectangles_disjoint=True,field_service_disjoint=True,additional_disjoint_named_rectangles=additional,all_named_rectangle_charge_union_mm2=named+sum(rect_area(r['bbox_DBU']) for r in field)/1e12+sum(r['reserved_mm2'] for r in additional),
   no_inherited_or_residual_charge_removed=True,placement_file='representative_placement.json.gz',placement_qualification='Constructive model coordinates only. No secondSVG; actual wholeelement RNE/WAKE abstract and source endpoint placement remain unbound.',HE_source_record=he,HE_pair_classes={str(p):field[p]['source_class'] for p in he['pairs']},HE_leaf_bodies=he_leaves,HE_adapter_qualified=False),
  collector=dict(band_DBU=bbox,required_parallel_tracks=required,actual_LEF_translated_shapes=len(shapes),per_layer=capacity,remaining_phase_upper_screen=gross,maximum_additional_blocked_tracks_for_screen=gross-required,old_assumed_half_reserve_margin=gross//2-required,percentage_reserve_used=False,parent_PG_clock_via_shape_bound=False,admissible_capacity=None,actual_native_grid_endpoints_are_not_extended_physical_tracks=True,required_next='Source-matched parent PG/clock metal and layer-resolved vias + fullgoal service pin access; subtract their interval union in this band before allocating20909tracks. Unbound exclusions are not zero.'),
  retained_ODB_scope=read('retained_ODB_scope.json'),budget=dict(historical_conservative_FAIL_mm2=924.2886185238459,not_fundamental_minimum=True,no_whole_fit_claim=True,unplaced_positive_terms=b['exact_once_area_ledger_mm2']['unpriced_nonzero_terms']),
  physical_GO=False,new_jobs=0,generator_sha256=sha(Path(__file__))),field,shapes

def main():
 model,field,shapes=build()
 for name,data in [('model.json',model),('representative_placement.json.gz',field),('translated_LEF_shapes.json.gz',shapes)]:
  raw=(json.dumps(data,indent=2,sort_keys=True)+'\n').encode()
  if name.endswith('.gz'):raw=gzip.compress(raw,mtime=0)
  p=BASE/name
  if p.exists():assert p.read_bytes()==raw,name
  else:p.write_bytes(raw)
 print(json.dumps(dict(service_union_mm2=model['inherited_area_reconciliation']['service_rectangle_union_mm2'],inherited_unreconciled_mm2=model['inherited_area_reconciliation']['inherited_minus_named_rectangles_mm2'],collector_phase_upper_screen=model['collector']['remaining_phase_upper_screen'],old_half_reserve_margin=model['collector']['old_assumed_half_reserve_margin'],admissible_capacity=model['collector']['admissible_capacity'],field_max_y_DBU=model['representative']['field_max_y_DBU'],actual_translated_LEF_shapes=model['collector']['actual_LEF_translated_shapes'])))
if __name__=='__main__':main()
