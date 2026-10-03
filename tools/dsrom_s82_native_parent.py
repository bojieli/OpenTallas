"""Replace S82 return storage proxies by measured complete-node bodies in one case.
Clock C assignment is emitted as actual named groups; oversized opaque providers
are refused, never split into imaginary subinstances.
"""
import argparse,gzip,hashlib,json,math,re
from collections import defaultdict
from pathlib import Path
import dsrom_c_s82_combined as G
import dsrom_s82_native_return as N
ROOT=G.ROOT
CLOCK=ROOT/'results/uarch/dsrom_s82_native_parent_20261003/inputs/clock_decision.json'
TECH=CLOCK.parent/'tech.lef'
RC=CLOCK.parent/'setRC.tcl'
def build():
 m=G.build();n=N.build();rect=m['rectangles'];node_area=n['actual_mapping']['FF50_component_reservation_um2']
 # One construction, not a density/count sweep. Keep the binary topology but
 # place the complete nodes in the right-side whitespace of the selected
 # named allocation. The previous slab replacement collision is archived.
 # No unnamed inherited debit is removed by using this geometric whitespace.
 byregion=defaultdict(list)
 for a in rect:
  if a['kind'].startswith('return_'):byregion[a['region']].append(a)
 for region,parts in byregion.items():
  y=13573.008
  x0=16957.648+region*(33000-16957.648)/128
  rw=(33000-16957.648)/128
  for level in range(6):
   nodes=[a for a in parts if a.get('level')==level];h=len(nodes)*node_area/rw
   for j,a in enumerate(nodes):
    a['bbox_um']=[x0+j*rw/len(nodes),y,x0+(j+1)*rw/len(nodes),y+h];a['kind']='return_complete_native_NAND_INV_FF50';a['mapped_cell_instances']=77952
   y+=h
  root=next(a for a in parts if a['kind']=='return_root_FF50_storage');b=root['bbox_um'];area=(b[2]-b[0])*(b[3]-b[1]);root['bbox_um']=[x0,y,x0+rw,y+area/rw]
 collisions=G.collision_scan(rect)
 groups=defaultdict(list);opaque=[];max_extent=5250
 no_clock_kinds={'HBM_PHY_assumed_abstract'}
 for a in rect:
  if a['kind'] in no_clock_kinds:continue
  b=a['bbox_um'];w=b[2]-b[0];h=b[3]-b[1]
  if 'CLEAR_ROUTE_BAND' in a['name'] or 'CLEAR' in a['name'] or 'band' in a['name'].lower():continue
  if max(w,h)>max_extent:
   opaque.append(dict(name=a['name'],bbox_um=b,reason='requires actual provider subinstances; no slicing of opaque macro'))
   continue
  # Initial deterministic grid, followed by splitting any oversized union.
  cx=(b[0]+b[2])/2;cy=(b[1]+b[3])/2
  groups[(min(10,int(cx//3000)),min(8,int(cy//3000)))].append(a)
 result=[];oversized=[]
 for (x,y),members in sorted(groups.items()):
  sub=[]
  for a in sorted(members,key=lambda z:tuple(z['bbox_um'])+(z['name'],)):
   found=False
   for item in sub:
    b=item['bbox_um'];c=a['bbox_um'];u=[min(b[0],c[0]),min(b[1],c[1]),max(b[2],c[2]),max(b[3],c[3])]
    if max(u[2]-u[0],u[3]-u[1])<=max_extent:
     item['bbox_um']=u;item['instances'].append(a['name']);found=True;break
   if not found:sub.append(dict(bbox_um=list(a['bbox_um']),instances=[a['name']]))
  for i,group in enumerate(sub):
   b=group['bbox_um'];group.update(name=f'clock_C_{x}_{y}_{i}',clock_root_um=[(b[0]+b[2])/2,(b[1]+b[3])/2],per_region_CTS_required=True)
   result.append(group)
 owner={name:g['name'] for g in result for name in g['instances']}
 positions={a['name']:[(a['bbox_um'][0]+a['bbox_um'][2])/2,(a['bbox_um'][1]+a['bbox_um'][3])/2] for a in rect}
 crossings=[]
 for e in m['edges']:
  src=e['source'];dst=e['destination']
  if src in m['leaves']:
   pair=m['leaves'][src]['field_pair'];src=f'pair{pair}' if pair is not None else None
  e['centre_L1_um']=sum(abs(a-b) for a,b in zip(positions[src],positions[dst])) if src in positions and dst in positions else None
  e['native_pin_length_um']=None
  e['source_clock_region']=owner.get(src);e['destination_clock_region']=owner.get(dst)
  if src in owner and dst in owner and owner[src]!=owner[dst]:
   crossings.append(dict(source=e['source'],destination=dst,bits=e['bits'],source_region=owner[src],destination_region=owner[dst],guide_L1_um=e['centre_L1_um'],guide_segments=math.ceil(e['centre_L1_um']/430.56)))
 clock_cost=clock_construction(result,crossings,n)
 # A geometric dependency-path screen only. Include the actual binary
 # subtree and root->capture edge; never price the whole parallel census as
 # per-token latency. Physical pins and the accepted phase calendar replace
 # these guides before admission.
 next_edge={e['source']:e for e in m['edges'] if e['class_name']!='cfg_read_to_local_wordmux'}
 paths=[]
 for leaf,meta in m['leaves'].items():
  if not meta['active']:continue
  current=leaf;segments=0;cross=0;length=0;unknown=False
  while current in next_edge:
   e=next_edge[current];d=e['centre_L1_um']
   if d is None:unknown=True;break
   segments+=max(0,math.ceil(d/430.56)-1);length+=d
   if e['source_clock_region']!=e['destination_clock_region']:cross+=1
   current=e['destination']
  paths.append(dict(pair=meta['field_pair'],MB=meta['MB'],guide_L1_um=length,guide_extra_forwarded_registers=segments,region_crossings=cross,missing_endpoint=unknown,central_guide_cycles=segments+cross,bound_guide_cycles=segments+4*cross))
 clock_cost['return_paths']=paths
 clock_cost['return_guide_cycles_range']={k:[min(p[k] for p in paths),max(p[k] for p in paths)] for k in ('central_guide_cycles','bound_guide_cycles')}
 decision=json.loads(CLOCK.read_text())
 return dict(candidate=m['candidate'],canonical_commit='feba0739366dfe9adb98991e59bd0cee687f5d55',return_mapping_source=n['source_commit'],clock_decision_commit='f954ad1ea67f77e8f1a5e86cf48856a96ca650bf',clock_option='C',clock_mesh=False,max_region_extent_um=5250,rectangles=rect,edges=m['edges'],collisions=collisions,out_of_die=[a['name'] for a in rect if min(a['bbox_um'][:2])<0 or a['bbox_um'][2]>33000+1e-6 or a['bbox_um'][3]>26000+1e-6],clock_groups=result,clock_group_count=len(result),oversized_groups=oversized,opaque_provider_decomposition_required=opaque,clock_crossings=crossings,clock_construction=clock_cost,PHY_clock_provider='Chandra: separate HBM clock; async receiver, not833ps assumption',clock_C=dict(per_region_CTS=True,shielded_layers=['M8','M9'],filtered_clock_rail_required=True,filtered_rail_LDO_reserved_bbox_um=None,rail_cost_unpriced=True,source_foil_DS_scope=decision['scope'],old_S73_661cycles_not_S82_calibration=True,Beauvoir_meso_FIFO_forwarded_link_required=True),actual_complete_node_area_mm2=n['node_FF50_projection_mm2'],additional_node_body_vs_retained_storage_mm2=n['node_logic_delta_before_containment_mm2'],retained_legacy_storage_charge_mm2=52.89758742528,inherited_residual_credit_mm2=0,one_native_NAND_INV_construction_not_minimum_proof=True,full_die_fit=False,selected_hierarchical_route_admitted=False,hardware_PnR_admitted=False,rate_adopted=False,source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (CLOCK,TECH,RC)},missing_owners={'Maxwell':['root control/capture/gather homes','inherited fixed/residual exclusion union'], 'Chandra':['actual W3 controller/PHY service subinstances/clock/port homes'], 'Archimedes_Maxwell':['regional CTS root/endpoint/clock-reset-PG/VIA construction'],'Epicurus':['q/BF selected source abstracts/SSFF'],'Beauvoir':['meso FIFO and forwarded link measured capacities/timing']})

def clock_construction(groups,crossings,n):
 # These are route guides, not invented pin coordinates. No availability of
 # shield tracks, CTS cells or an LDO is inferred from unused die area.
 branches=[]
 def tree(items,parent):
  if not items:return
  p=[sum(g['clock_root_um'][d] for g in items)/len(items) for d in (0,1)]
  if parent!=p:branches.append(dict(start_um=parent,end_um=p,L1_um=sum(abs(a-b) for a,b in zip(parent,p))))
  if len(items)==1:return
  axis=max((0,1),key=lambda d:max(g['clock_root_um'][d] for g in items)-min(g['clock_root_um'][d] for g in items))
  items=sorted(items,key=lambda g:(g['clock_root_um'][axis],g['name']));mid=len(items)//2
  tree(items[:mid],p);tree(items[mid:],p)
 tree(groups,[16500,13000])
 bits=sum(c['bits'] for c in crossings)
 return_flops=n['actual_mapping']['flops']*8064
 metal={}
 for layer in ('M8','M9'):
  block=re.search(r'LAYER '+layer+r'\s.*?END '+layer,TECH.read_text(),re.S).group(0)
  pitch=float(re.search(r'PITCH\s+([\d.]+)',block).group(1));width=float(re.search(r'\n\s*WIDTH\s+([\d.]+)',block).group(1))
  metal[layer]=dict(pitch_um=pitch,min_width_um=width,direction='HORIZONTAL' if layer=='M8' else 'VERTICAL',proposed_clock_width_um=2*width,proposed_shield_width_um=width,proposed_spacing_um=width,guide_corridor_um=4*pitch)
 length=sum(b['L1_um'] for b in branches)
 # 0.2fF/um and driver-load factor1 are ASSUMED in the accepted C study,
 # explicitly not a measured extraction of these new routes.
 clock_load_fF=length*.2*2
 rail_proxy=clock_load_fF*1e-15*.7*1.2e9
 guide_reserved=sum(abs(b['start_um'][0]-b['end_um'][0])*metal['M8']['guide_corridor_um']+abs(b['start_um'][1]-b['end_um'][1])*metal['M9']['guide_corridor_um'] for b in branches)/1e6
 return dict(trunk_root_guide_um=[16500,13000],native_PLL_pin_um=None,trunk_branches=branches,trunk_total_guide_L1_um=length,trunk_leaf_count=len(groups),trunk_130_leaf_screen_pass=len(groups)<=130,shielded_layers=['M8','M9'],shield_metal=metal,shield_track_guide_area_mm2=guide_reserved,shield_guide_area_is_not_disjoint_PG_available_tracks=True,available_tracks=None,return_clock_sink_pins=return_flops,other_clock_sink_pins=None,local_CTS_cell_area_mm2=None,filtered_rail_LDO_area_mm2=None,trunk_filtered_rail_current_proxy_A=rail_proxy,trunk_filtered_rail_power_proxy_W=rail_proxy*.7,trunk_cap_proxy_fF=clock_load_fF,capacitance_and_driver_load_factor_assumed_from_C_study=True,filtered_rail_actual_clock_current_A=None,clock_PG_overlap_proven=False,parallel_crossing_bits=bits,FIFO_gross_FF50_storage_proxy_mm2={str(depth):bits*depth*.75816/1e6 for depth in (4,8)},FIFO_depths_are_C_design_study_not_qualified=True,FIFO_identity_credit_control_logic_extra_mm2=None,forwarded_clock_guide_segments=sum(c['guide_segments'] for c in crossings),forwarded_stage_state_FF50_proxy_mm2=sum(c['bits']*max(0,c['guide_segments']-1) for c in crossings)*.75816/1e6,guide_segments_are_not_actual_pin_route_or_qualified_pipeline=True,per_user_latency_rule='Compose each selected phase dependency path with its own forwarded segments and entry FIFO DELTA; do not sum parallel edge counts or transfer old S73 661 cycles.',single_user_token_delta_cycles=None,PHY_900ps_clock_is_separate_async=True,reset_sync_stages=3,Beauvoir_implementation_required=True)
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();m=build();a.out.write_bytes(gzip.compress((json.dumps(m,sort_keys=True,separators=(',',':'))+'\n').encode(),mtime=0));print(json.dumps({k:v for k,v in m.items() if k not in ('rectangles','edges','clock_groups')},indent=2))
