"""Fixed selector track/turn construction. Geometry screen only; no route/STA."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import uarch_topk_finite_source_context as F
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'results/uarch/topk_finite_track_turn_model_20261002'
MANIFEST='25d5fe77fc7772b3acc3084dc76f943292e86df045c25da13cd819233d83b3bc'

def inputs():
    raw=(BASE/'origins.json').read_bytes()
    if hashlib.sha256(raw).hexdigest()!=MANIFEST:raise ValueError('origin manifest changed')
    entries=json.loads(raw);records={}
    for name,e in entries.items():
        b=(BASE/'inputs'/name).read_bytes()
        if len(b)!=e['bytes'] or hashlib.sha256(b).hexdigest()!=e['sha256']:raise ValueError('pinned input changed: '+name)
        records[name]=b
    return records,entries

def tracks(grid,layer,axis,lo,hi):
    phases=[g for g in grid['grids'] if g['layer']==layer]
    if len(phases)!=1:raise ValueError('unique source grid required')
    return sorted({s+i*step for s,count,step in phases[0][axis]
                   for i in range(math.ceil((lo-s)/step),math.ceil((hi-s)/step))})

def selected_half(values):
    # Pair adjacent raw track positions; one signal track and one reserve track.
    # No spare odd final track borrowed; deterministic and not an allocator search.
    return values[0:2*(len(values)//2):2]

def pin_names(inventory):
    pins=[]
    for direction in ['inputs','outputs']:
        for name,width in sorted(inventory[direction].items()):
            pins.extend(f'{direction}.{name}[{i}]' for i in range(width))
    return pins+['clock','reset']

def via_shapes(tech,name):
    b=re.search(r'^VIA '+name+r' Default\s*$(.*?)^END '+name+r'\s*$',tech,re.M|re.S)
    if not b:raise ValueError('missing default via '+name)
    return {layer:[round(float(v)*1000) for v in (a,c,d,e)] for layer,a,c,d,e in
            re.findall(r'LAYER (\w+)\s*;\s*RECT ([\d.-]+) ([\d.-]+) ([\d.-]+) ([\d.-]+)\s*;',b[1])}

def overlaps(rects):
    # Rectangles already include half the minimum spacing on each side.
    # Only necessary metal-spacing screen, not all LEF58/cut/PDN rules.
    active=[];count=0;first=None
    for r in sorted(rects,key=lambda r:r['bbox'][0]):
        b=r['bbox'];active=[q for q in active if q['bbox'][2]>b[0]]
        for q in active:
            a=q['bbox']
            if a[1]<b[3] and b[1]<a[3] and q['pin']!=r['pin']:
                count+=1
                if first is None:first={'a':q,'b':r}
        active.append(r)
    return {'pairs':count,'first':first}

def station_coordinates(entry,horizontal_start_x,hub_boundary_y,segments):
    if segments<1:raise ValueError('positive segment count required')
    x=entry['vertical_x_DBU'];y=entry['horizontal_y_DBU']
    dx=x-horizontal_start_x;dy=hub_boundary_y-y
    if dx<0 or dy<0:raise ValueError('source-aligned positive L route required')
    length=dx+dy
    return [[horizontal_start_x+d,y] if d<=dx else [x,y+d-dx]
            for d in (length*i/segments for i in range(1,segments))]

def build():
    records,pins=inputs();grid=json.loads(records['grid.json']);tech=records['tech.lef'].decode()
    parent=json.loads(records['model-r2.json']);data,_=F.A.replay(ROOT,mode='archive-only');old=json.loads(data);context=F.build()
    h=old['placement']['horizontal_escape_bbox_DBU'];v=old['placement']['vertical_escape_to_collective_lower_boundary_bbox_DBU']
    pool={l:selected_half(tracks(grid,l,axis,lo,hi)) for l,axis,lo,hi in
          [('M2','Y',h[1],h[3]),('M4','Y',h[1],h[3]),('M3','X',v[0],v[2]),('M5','X',v[0],v[2])]}
    names=pin_names(old['ports']['bit_inventory'])
    if len(names)!=4212:raise ValueError('full public geometry changed')
    # Fill low horizontal tier first; preserve independent inputs/results.
    low=min(len(pool['M2']),len(names));high=len(names)-low
    upper=min(high,len(pool['M5']));transfer=high-upper
    if high>len(pool['M4']) or low+transfer>len(pool['M3']):raise ValueError('fixed tier pools cannot carry pins')
    entries=[]
    for i,name in enumerate(names):
        if i<low:hl,vl,hi,vi,via='M2','M3',i,i,'VIA23'
        elif i<low+transfer:hl,vl,hi,vi,via='M4','M3',i-low,low+i-low,'VIA34'
        else:hl,vl,hi,vi,via='M4','M5',i-low,i-low-transfer,'VIA45'
        entries.append({'pin':name,'horizontal_layer':hl,'horizontal_y_DBU':pool[hl][hi],
                        'vertical_layer':vl,'vertical_x_DBU':pool[vl][vi],'turn_via':via})
    spacing=parent['q']['layer_minimum_spacing'];rects={}
    for e in entries:
        for layer,r in via_shapes(tech,e['turn_via']).items():
            if not layer.startswith('M'):continue
            sp=spacing[layer]['minimum_spacing_DBU']/2;x=e['vertical_x_DBU'];y=e['horizontal_y_DBU']
            rects.setdefault(layer,[]).append({'pin':e['pin'],'bbox':[x+r[0]-sp,y+r[1]-sp,x+r[2]+sp,y+r[3]+sp]})
    checks={l:overlaps(rs) for l,rs in rects.items()}
    # Source-aligned corridor centerline, not endpoint pin or free-space shortcut.
    yc=(h[1]+h[3])/2;xc=(v[0]+v[2])/2
    route=[[h[0],yc],[xc,yc],[xc,v[3]]]
    length=sum(abs(a[0]-b[0])+abs(a[1]-b[1]) for a,b in zip(route,route[1:]))/1000
    budget=context['internal_tracks']['nonlogic_wire_hop_budget_um'];segments=math.ceil(length/budget)
    longest=max((e['vertical_x_DBU']-h[0]+v[3]-e['horizontal_y_DBU'])/1000 for e in entries)
    path_segments=math.ceil(longest/budget)
    widths=context['transport_model']['pipeline_width_bits']
    drain=context['transport_model']['additional_delay_edges']['formed_VM_write']
    pipeline_bits=(widths['input']+widths['selector_return'])*(path_segments-1)+widths['formed_VM_write']*drain+drain
    added_cycles=2*(path_segments-1)+drain
    return {'schema':'FULL_SELECTOR_FIXED_TRACK_TURN_CONSTRUCTION_V1','sourcepins':pins,
      'fixed_geometry':context['compiled'],'selector_slot_DBU':context['frozen_selector_slot_DBU'],
      'selector_state_bits':698354,'raw_grid_scope':'source phase extension, not extracted placed routes',
      'signal_plus_clock_reset_pins':4212,'pin_aliasing':False,'tier_half_pool_capacity':{l:len(p) for l,p in pool.items()},
      'allocated_horizontal':{'M2':low,'M4':high},'allocated_vertical':{'M3':low+transfer,'M5':upper},
      'mandatory_M4_to_M3_tier_transfer_in_this_half_pool_mapping':transfer,
      'remaining_half_pool_tracks':{'horizontal':len(pool['M2'])+len(pool['M4'])-len(names),'vertical':len(pool['M3'])+len(pool['M5'])-len(names)},
      'clock_reset_included_once':True,'reserve_policy':'alternate raw track held separate; no PG reserve borrowing or double debit',
      'assignments':entries,'turn_metal_minimum_spacing_screen':checks,
      'turn_screen_pass':all(c['pairs']==0 for c in checks.values()),
      'actual_selector_PG_overlay_bound':False,'q_element_PDN_is_not_selector_PDN':True,
      'LEF58_cut_corner_EOL_and_pin_escape_checked':False,'actual_clock_tree_and_slew_checked':False,
      'corridor_centerline':{'polyline_DBU':route,'length_um':length,'wireonly_segments':segments,
          'even_segment_length_um':length/segments,'extra_input_and_return_edges_each':segments-1,
          'logic_budget_scope':'segment count uses retained nonlogic wire bound; FF/load/buffer/stage logic and endpoint pin offsets can require more segments',
          'actual_stations_placed':False},
      'full_allocated_lane_path':{'maximum_length_um':longest,'wireonly_segments_each_direction':path_segments,
          'maximum_equal_segment_length_um':longest/path_segments,'leftover_before_stage_logic_ps':(budget-longest/path_segments)*0.76,
          'stations':'Each assigned net follows its allocated horizontal y to its vertical x then to hub lower boundary; equal-L1 station coordinates are defined geometrically, cell/PG/clock occupation not placed',
          'actual_endpoint_pin_offsets_known':False,'no_station_containment_credit':True},
      'source_transport_price':{'proposal_only':True,'additional_FF_bits':pipeline_bits,
          'additional_cycles_per_call':added_cycles,'ninecall_additional_cycles':9*added_cycles,
          'ninecall_additional_ns_at_policyclock':9*added_cycles/1.2,
          'FF_only_reservation_mm2_at50pct':pipeline_bits*0.2916/0.5/1e6,
          'latest_owner_screen_already_including_corridor_mm2':parent['area']['screen_with_corridor_mm2'],
          'latest_owner_plus_transport_FF_floor_mm2':parent['area']['screen_with_corridor_mm2']+pipeline_bits*0.2916/0.5/1e6,
          'formed_VM_write_delay_edges':drain,'retirement_extra_edges':drain,
          'old_19segment_geometry_lowerbound_replaced_not_silently_adopted':True,'clock_buffer_hold_PG_cost_not_in_FF_floor':True},
      'G0':{'RTL_admitted':False,'PR_admitted':False,'necessary_next_action':'Allocate turn zones and actual selector PG/clock/pin escape with physical owners; retain both directions and formed-write retirement alignment; bind station cells/SSFF before launch'},
      'jobs_launched':0,'new_PVE2_PVE3_jobs':0}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if a.out.exists():raise ValueError('fresh output required')
    model=build()
    with a.out.open('x') as f:json.dump(model,f,indent=2,sort_keys=True);f.write('\n')
