#!/usr/bin/env python3
"""Fixed one-PAR2 model: source-site bijection, real macro placement/exclusions.
No new allocation, serial-stage/depth sweep, RTL, physical flow or clock credit.
"""
import gzip,hashlib,importlib.util,json,math,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'results/uarch/dsrom_PAR2_shard_physical_binding_20261002'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def js(name):return json.loads((BASE/'inputs'/name).read_text())
def snap(n):return math.ceil(n/2160)*2160
def build(shard=0):
 rec=json.loads((BASE/'input_receipt.json').read_text())
 for name,r in rec['inputs'].items():assert sha(BASE/'inputs'/name)==r['sha256'],name
 spec=importlib.util.spec_from_file_location('shape_helpers',BASE/'inputs/parent_shapes_tool.py');c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c);c.BASE=BASE
 p=js('successor.json')['single_parallel_successor'];assert p['candidate_id']=='DS4096-TP4-S58-PAR2-NP2048'
 mapping=p['source_site_mapping'];assert len(mapping)==4096
 for row in mapping:assert row['shard']==row['source_site']//2048 and row['local_site']==row['source_site']%2048
 for region in range(128):assert len({mapping[g]['shard'] for g in range(32*region,32*(region+1))})==1
 prices=js('price_terms.json');assert abs(prices['composed_priced_field_terms']/2-p['field_terms_per_shard_mm2'])<1e-8
 f=js('frames.json');s=js('service.json');grid=js('grid.json');templates={n:c.lef(n+'.lef') for n in ['ROM','CFG','SRAM']}
 halo=4320;macros=[];field=[];x=y=halo;rowh=0;w,h=templates['ROM']['size_DBU'];bf={i*2048//362 for i in range(362)}
 for local in range(2048):
  cls='BF16_column_pair' if local in bf else 'q_pair';cw,ch=[round(v*1000) for v in f['classes'][cls]['outline_um']]
  # Keep the full catalog reservation, add clearance outside it as necessary.
  rw=max(cw,2*w+4*halo);rh=snap(max(ch,2*h+4*halo))
  if x+rw+halo>33000000:x=halo;y+=rowh+2*halo;rowh=0
  body=[x,y,x+rw,y+rh];global_site=shard*2048+local
  field.append(dict(local_pair=local,source_pair=global_site,source_return_region=global_site//32,local_return_region=local//32,source_class=cls,catalog_area_DBU2=cw*ch,bbox_DBU=body,whole_element_hard_abstract=False))
  for slot in range(2):
   for pp in range(2):
    a=x+halo+slot*(w+2*halo);b=y+halo+pp*(h+2*halo)
    macros.append(dict(name=f'candidate.shard{shard}.pair{local}.slot{slot}.pp{pp}',template='ROM',origin_DBU=[a,b],bbox_DBU=[a,b,a+w,b+h],orientation='R0',source_pair=global_site,slot=slot,PP=pp,hierarchy_elaborated=False))
  x+=rw+2*halo;rowh=max(rowh,rh)
 field_end=max(r['bbox_DBU'][3] for r in field);cfg_y=snap(field_end+2*halo);cw,ch=templates['CFG']['size_DBU'];pw,ph=snap(cw+2*halo),snap(ch+2*halo);cols=(33000000-2*halo)//pw
 cfg_slots=[]
 for index in range(14336):
  pair,slice_index=divmod(index,7);a=halo+(index%cols)*pw;b=cfg_y+(index//cols)*ph
  cfg_slots.append([a-halo,b-halo,a-halo+pw,b-halo+ph])
  macros.append(dict(name=f'candidate.shard{shard}.cfg_pair{pair}.slice{slice_index}',template='CFG',origin_DBU=[a,b],bbox_DBU=[a,b,a+cw,b+ch],orientation='R0',source_pair=shard*2048+pair,cfg_slice=slice_index,hierarchy_elaborated=False))
 cfg_end=max(r[3] for r in cfg_slots);cursor=snap(cfg_end+2*halo);extra=[]
 # cfg slot union already pays macro halos. Its source local mux remains extra.
 cfg_body=14336*cw*ch/1e12;original_cfg=prices['config_prospective_body_plus_local_mux']/2
 cfg_mux=original_cfg-cfg_body;assert cfg_mux>0
 for name,area in [('CFG_LOCAL_WORDMUX',cfg_mux),('DECLARED_RETURN_FF50',p['return_FF50_per_shard_mm2']),('RNE_BF362',prices['RNE_BF724_upper_proxy']/2),('WAKE_DECLARED2048',prices['WAKE_full_compiled_upper_proxy']/2)]:
  height=snap(area*1e12/33000000);extra.append(dict(name=name,source_priced_mm2=area,bbox_DBU=[0,cursor,33000000,cursor+height],hard_abstract=False));cursor+=height+2*halo
 assert cursor<16000000
 service=[(r['name'],[round(v*1000) for v in r['candidate_anchor_bbox_um']]) for r in s['rectangles']]
 c.disjoint([(f'pair{x["local_pair"]}',x['bbox_DBU']) for x in field]+[(f'cfg{i}',r) for i,r in enumerate(cfg_slots)]+[(x['name'],x['bbox_DBU']) for x in extra]+service)
 for row in s['collector_macros']:
  body=[round(v*1000) for v in row['candidate_anchor_body_um']];macros.append(dict(name=row['instance'],template='SRAM',origin_DBU=body[:2],bbox_DBU=body,orientation=row['orientation'],hierarchy_elaborated=False))
 c.disjoint([(x['name'],x['bbox_DBU']) for x in macros])
 for x in macros:
  a=x['bbox_DBU'];assert 0<=a[0]<a[2]<=33000000 and 0<=a[1]<a[3]<=26000000
 # Compact transformed OBS are fully materialized; millions of pin shapes are
 # losslessly addressable by the exact template+origin+orientation records.
 obs=[]
 for macro in macros:
  t=templates[macro['template']]
  for shape in t['OBS']:obs.append(dict(instance=macro['name'],layer=shape['layer'],bbox_DBU=c.translate(shape['bbox_DBU'],*macro['origin_DBU'],t['size_DBU'],macro['orientation'])))
 band=next(r for r in s['routing_bands'] if r['name']=='collector_combined');box=[round(v*1000) for v in band['candidate_anchor_band_um']];capacity=[]
 for layer in ['M2','M4']:
  tracks=c.phases(grid,layer,box[1],box[3]);blocked=set();pin_shapes=PG_shapes=0
  for macro in macros:
   body=macro['bbox_DBU'];t=templates[macro['template']]
   # Reject whole-body-plus-halo disjointness before expanding exact pins/OBS.
   a=[body[0]-halo,body[1]-halo,body[2]+halo,body[3]+halo]
   if not c.overlap(a,box):continue
   for shape in t['OBS']+t['pins']:
    if shape['layer']!=layer:continue
    r=c.translate(shape['bbox_DBU'],*macro['origin_DBU'],t['size_DBU'],macro['orientation'])
    if max(r[0],box[0])<min(r[2],box[2]):blocked|={q for q in tracks if r[1]<=q<=r[3]}
    if 'pin' in shape:
     pin_shapes+=1;PG_shapes+=shape.get('use') in ['POWER','GROUND']
   blocked|={q for q in tracks if a[1]<=q<=a[3]}
  capacity.append(dict(layer=layer,phase_extended_tracks=len(tracks),translated_OBS_pin_PG_halo_blocked=len(blocked),unblocked_before_parent_PG_vias_clock=len(tracks)-len(blocked),intersecting_macro_pin_shapes=pin_shapes,intersecting_macro_PG_shapes=PG_shapes))
 upper=sum(x['unblocked_before_parent_PG_vias_clock'] for x in capacity)
 # Reuse the retained source's predeclared two-lane M4->M5 escape
 # hypothesis on actual collector pins; no routing or source modification.
 escape_source=(BASE/'inputs/escape_source.py').read_text()
 assert 'distance=96+(index%lanes)*96' in escape_source
 log=(BASE/'inputs/escape_loaded_rules.log').read_text()
 assert 'getDefault|34' in log
 cuts=[];escapes=[];off_track=0;halo_escape=0;band_hits=0
 gx=next(r for r in grid['grids'] if r['layer']=='M5')['X']
 assert len(gx)==1
 xo,count,xpitch=gx[0];xphase=xo%xpitch
 gy=next(r for r in grid['grids'] if r['layer']=='M4')['Y'];assert len(gy)==1
 yo,count,ypitch=gy[0];yphase=yo%ypitch
 for macro in [v for v in macros if v['template']=='SRAM']:
  t=templates['SRAM'];body=macro['bbox_DBU']
  ports=[dict(z,bbox_DBU=c.translate(z['bbox_DBU'],*macro['origin_DBU'],t['size_DBU'],macro['orientation'])) for z in t['pins'] if z['layer']=='M4' and z.get('use') not in ['POWER','GROUND']]
  for side in ['left','right']:
   group=sorted([v for v in ports if (v['bbox_DBU'][0]<(body[0]+body[2])/2)==(side=='left')],key=lambda v:v['bbox_DBU'][1])
   for index,pin in enumerate(group):
    a=pin['bbox_DBU'];cx,cy=(a[0]+a[2])//2,(a[1]+a[3])//2
    vy=yphase+round((cy-yphase)/ypitch)*ypitch
    distance=96+(index%2)*96
    vx=xphase+(math.floor((a[0]-distance-xphase)/xpitch) if side=='left' else math.ceil((a[2]+distance-xphase)/xpitch))*xpitch
    landings={v['layer']:[vx+v['bbox'][0],vy+v['bbox'][1],vx+v['bbox'][2],vy+v['bbox'][3]] for v in grid['tech_via_definitions']['VIA45']}
    metal4=[min(vx-23,a[0]),vy-12,max(vx+23,a[2]),vy+12];off_track+=not c.overlap(metal4,a)
    halo_escape+=not all(body[0]-halo<=r[0]<r[2]<=body[2]+halo and body[1]-halo<=r[1]<r[3]<=body[3]+halo for r in [metal4,*landings.values()])
    band_hits+=any(c.overlap(r,box) for r in [metal4,*landings.values()])
    cut=landings['V4'];cuts.append((macro['name'],cut));escapes.append(dict(instance=macro['name'],pin=pin['pin'],pin_DBU=a,M4_stub_DBU=metal4,via_center_DBU=[vx,vy],via_landings_DBU=landings))
 # Source V4 default edge spacing34DBU; conservative axis-separation check.
 bad_cut_pairs=0;buckets={}
 for name,rect in cuts:
  key=((rect[0]+rect[2])//2//96,(rect[1]+rect[3])//2//96)
  for dx in [-1,0,1]:
   for dy in [-1,0,1]:
    for other in buckets.get((key[0]+dx,key[1]+dy),[]):
     xgap=max(other[0]-rect[2],rect[0]-other[2],0);ygap=max(other[1]-rect[3],rect[1]-other[3],0)
     if max(xgap,ygap)<34:bad_cut_pairs+=1
  buckets.setdefault(key,[]).append(rect)
 signal_pin_count=sum(len({v['pin'] for v in templates[k]['pins'] if v.get('use') not in ['POWER','GROUND']})*sum(z['template']==k for z in macros) for k in templates)
 clock_cap_ff=sum(js(k+'_timing.json')['timing']['ss']['clk_cap_ff']*sum(z['template']==k for z in macros) for k in templates)
 field_area=sum(c.rect_area(x['bbox_DBU']) for x in field)/1e12;cfg_slot_area=sum(c.rect_area(x) for x in cfg_slots)/1e12
 added_field=field_area-prices['full_compiled_q_BF_catalog_frames']/2;added_cfg=cfg_slot_area-cfg_body
 extra_rounding=sum(c.rect_area(x['bbox_DBU'])/1e12-x['source_priced_mm2'] for x in extra)
 debit=added_field+added_cfg+extra_rounding;screen=p['conservative_priced_per_shard_mm2']+debit
 timing={}
 for master in ['ROM','CFG','SRAM']:
  t=js(master+'_timing.json')['timing'];timing[master]=dict(SS_clk_to_q_ps=t['ss']['clk_to_q_ps'],SS_min_period_ps=t['ss']['min_period_ps'],FF_hold_ps=t['ff']['hold_ps'],FF_clk_to_q_ps=t['ff']['clk_to_q_ps'],one_stream_cycle_after60ps_uncertainty_minus_macro_cq_ps=1e12/1.2e9-60-t['ss']['clk_to_q_ps'],scope='Memory compiler models; downstream cell setup, route and clock insertion still extra. No contextual closure.')
 pdn=(BASE/'inputs/pdn_rom_die.tcl').read_text();assert '-followpins' in pdn and '{M2 M5}' in pdn and '{M4 M5}' in pdn
 clocks=sum(sum(x['pin']=='clk' for x in templates[k]['pins'])*sum(v['template']==k for v in macros) for k in templates)
 model=dict(schema='opentallas.DSROM.PAR2.shard-physical-binding.v1',candidate=p['candidate_id'],shard=shard,source_receipt_sha256=sha(BASE/'input_receipt.json'),serial_stage_owners=58,logical_TP=4,physical_shards_per_owner=2,added_serial_hops=0,added_collective_tree_levels=0,
  ownership=dict(source_range=[2048*shard,2048*(shard+1)],local_NP=2048,local_BF362=sorted(bf),actual_census=p['actual_622_shard_site_census'][shard],unchanged_ordered32pair_regions=True,no_tensor_or_expert_repack=True,weight_capacity_bits=8192*4096*274),
  geometry=dict(die_DBU=[33000000,26000000],DBU_per_um=1000,halo_DBU=halo,halo_basis='Explicit4320DBU construction clearance inherited from service preparation; not measured minimum or routing proof.',field_frame_union_mm2=field_area,field_end_DBU=field_end,cfg_macro_body_mm2=cfg_body,cfg_slot_union_mm2=cfg_slot_area,additional_named_reservations=extra,all_rectangles_disjoint=True,last_field_cfg_return_repair_end_DBU=cursor,named_service_preserved=True,one_representative_layout_only=True,complete_hard_element_missing=True),
  macros=dict(weight=8192,cfg72=14336,collector=36,total=len(macros),all_current_LEF_masters=True,port_shape_count=sum(len(templates[k]['pins'])*sum(v['template']==k for v in macros) for k in templates),memory_clk_pin_shapes=clocks,unique_nonPG_pin_count=signal_pin_count,SS_macro_clock_cap_sum_fF=clock_cap_ff,compact_transform_file='macro_placement.json.gz',translated_OBS_file='translated_OBS.json.gz',pin_templates_file='macro_templates.json',pin_escape_and_full_collar_not_proven=True),
  area=dict(original_per_shard_screen_mm2=p['conservative_priced_per_shard_mm2'],original_extra_budget_mm2=p['per_shard_margin_for_extra_IO_link_adapter_hardware_mm2'],added_field_macro_clearance_mm2=added_field,added_cfg_halo_grid_mm2=added_cfg,additional_reservation_rounding_mm2=extra_rounding,total_added_debit_mm2=debit,revised_conservative_screen_mm2=screen,remaining_for_positive_endpoints_exclusions_mm2=858-screen,inherited418_and_residual47_retained=True,legal_fit_proven=False),
  collector=dict(required_parallel_tracks=20909,band_DBU=box,per_layer=capacity,phase_upper_screen=upper,maximum_remaining_PG_via_clock_exclusions_for_screen=upper-20909,half_reserve_not_used=True,admissible_capacity=None,actual_parent_PG_clock_via_bound=False),
  collector_pin_escape_hypothesis=dict(exact_current_M4_pins=len(escapes),lost_pin_intersections=off_track,escaped_outside4320halo=halo_escape,collector_band_intersections=band_hits,V4_axis_spacing34DBU_violating_pairs=bad_cut_pairs,source_hypothesis='Retained fixed96/192nm two-lane escape; not adopted or tuned. Uses actual VIA45/loadedV4default34nm.',full_DRC_or_global_route=False,PG_pin_access_and_CTS_coverage=False,artifact='collector_pin_via_escape.json.gz'),
  PG_via_clock=dict(source_PDN_scripts_pinned=True,macro_M4_PG_pins_translatable=True,source_followpins_M1_M2_requires_actual_rows=True,source_PDN_M2_M5_and_macroM4_M5_via_trees=True,tech_VIA45_template=grid['tech_via_definitions']['VIA45'],actual_via_origins_bound=False,clock_regions='Source engine singleclk; streaming1.2GHz / serial0.9GHz required; CTS/CDC/hold cuts not implemented.',setup_uncertainty_ps=60,hold_uncertainty_ps=25,source_macro_timing=timing,parent_SS_FF_qualified=False,prospective_common_controller_cut_cycles=s['clock_PG_cuts']['prospective_common_controller_cut_cycles'],controller_cut_scope=s['clock_PG_cuts']['cut_scope'],controller_cut_token_pricing='Retain diagnostic+2cycles per actual accepted traversal in Maxwell calendar; not certified minimum, not multiplied by fanout/loads.'),
  remote_endpoint=dict(source_roots=64,root_bits=69,raw_root_boundary_bits_per_cycle=4416,activation_source_width_bits=[549,1616],finite_credit_skid_visibility_lease_adapters_unpriced=True,endpoint_shoreline_and_PG_rectangle_unbound=True,no_port_width_equals_service_guarantee=True,Maxwell_conditional_critical_path=p['critical_path'],physical_latency_and_token_cost='max(local_ready, remote_accept+issue+return+transport+visible) then original orderedconsumer. No frequency, free overlap or zero-latency credit.'),
  missing_model_admission=['Source-owned PAR2 adapter and finite actual activation/cfg/root accept-visible calendar','Complete q/BF RNEWAKE element collar/pin/OBS and actual source endpoint placement','Current placement rows -> M2 followpin PG, layer-resolved PDN vias and CTS/CDC/hold exclusions in collector band','Actual DS shoreline/link endpoint instance rectangles and wholeinstance union, priced within revised remaining allowance'],physical_GO=False,new_RTL_or_PnR_jobs=0,generator_sha256=sha(Path(__file__)))
 return model,macros,obs,templates,field,escapes

def main():
 model,macros,obs,templates,field,escapes=build()
 for name,obj in [('model.json',model),('macro_placement.json.gz',macros),('translated_OBS.json.gz',obs),('macro_templates.json',templates),('field_placement.json.gz',field),('collector_pin_via_escape.json.gz',escapes)]:
  raw=(json.dumps(obj,indent=2,sort_keys=True)+'\n').encode()
  if name.endswith('.gz'):raw=gzip.compress(raw,mtime=0)
  p=BASE/name
  if p.exists():assert p.read_bytes()==raw,name
  else:p.write_bytes(raw)
 print(json.dumps(dict(candidate=model['candidate'],macro_count=len(macros),added_debit_mm2=model['area']['total_added_debit_mm2'],revised_screen_mm2=model['area']['revised_conservative_screen_mm2'],remaining_mm2=model['area']['remaining_for_positive_endpoints_exclusions_mm2'],collector_upper_screen=model['collector']['phase_upper_screen'],physical_GO=False)))
if __name__=='__main__':main()
