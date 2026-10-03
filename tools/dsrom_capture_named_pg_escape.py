#!/usr/bin/env python3
"""One c9 bank: named local PG upfeed and buffer A/Y escape construction.
Geometry proposal only: does not invent supply current, clock net assignment,
RC, global route occupancy, sink timing or consumer deadline.
"""
import argparse,gzip,hashlib,json,math,re
from pathlib import Path
import dsrom_capture_selected_bank_escape as B
BASE=B.ROOT/'results/uarch/dsrom_capture_named_pg_escape_20261003'
def tech():
 for r in json.loads((BASE/'inputs/origins.json').read_text()):
  if hashlib.sha256((BASE/'inputs'/r['copy']).read_bytes()).hexdigest()!=r['sha256']:raise ValueError('Tech origin drift')
 g=json.loads((BASE/'inputs/grid.json').read_text());s=gzip.decompress((BASE/'inputs/tech.lef.gz').read_bytes()).decode()
 if 'DIRECTION HORIZONTAL' not in re.search(r'LAYER M2\n(.*?)END M2',s,re.S)[1] or 'DIRECTION VERTICAL' not in re.search(r'LAYER M3\n(.*?)END M3',s,re.S)[1]:raise ValueError('Directional grid changed')
 return g

def via(g,name,x,y,net):
 return [dict(net=net,layer=r['layer'],bbox_DBU=[x+r['bbox'][0],y+r['bbox'][1],x+r['bbox'][2],y+r['bbox'][3]],via=name) for r in g['tech_via_definitions'][name]]
def m3_phase(g):
 rows=next(r['X'] for r in g['grids'] if r['layer']=='M3')
 if len(rows)!=1:raise ValueError('M3 phase ambiguous')
 return rows[0][0]%rows[0][2],rows[0][2]
def local_escape(c,pin,g,lef):
 # Exactly one fixed construction, not a route sweep: middle of literal
 # vertical A or Y pin, M2 horizontal to nearest M3 phase, local M3 landing.
 x,y=c['bbox_DBU'][:2];px=27 if pin=='A' else 348;py=135
 a=via(g,'VIA12',x+px,y+py,c.get('instance',c.get('proposed_site_ID'))+'.'+pin)
 m1=next(r['bbox_DBU'] for r in a if r['layer']=='M1')
 if not any(B.contained(m1,B.transform(s,c)) for s in B.shapes(lef,pin)):raise ValueError('M1 landing outside literal pin')
 offset,pitch=m3_phase(g);vx=offset+math.floor((x+px-offset)/pitch+0.5)*pitch
 net=a[0]['net'];v23=via(g,'VIA23',vx,y+py,net)
 # >=38x18 M2 rectangle covers both landing polygons and minimum area666.
 lo=min(x+px-14,vx-14);hi=max(x+px+14,vx+14)
 if hi-lo<38:lo-=5;hi+=5
 stub=dict(net=net,layer='M2',bbox_DBU=[lo,y+py-9,hi,y+py+9])
 if (hi-lo)*18<666:raise ValueError('M2 minimum area')
 return dict(cell=c.get('instance',c.get('proposed_site_ID')),pin=pin,pin_orientation=c['orientation'],actual_net_assignment=None,shapes=a+[stub]+v23,M3_track_phase_extended_not_live_DEF=True,M1_literal_landing_contained=True,port_route_above_M3_not_bound=True)

def pg_feed(name,box,rails,g,clearance_left_DBU):
 # Two independent M3 trunks in existing left gap; horizontal M1 rail
 # extensions with local VIA12+VIA23 patches outside all cell bodies.
 off,pitch=m3_phase(g);right=off+math.floor((box[0]-72-off)/pitch)*pitch;left=right-2*pitch
 if left-14<clearance_left_DBU:raise ValueError('PG feed exceeds named left gap')
 xs={'VDD':left,'VSS':right};shapes=[]
 for r in rails:
  b=r['bbox_DBU'];y=(b[1]+b[3])//2;net=name+'.'+r['net'];x=xs[r['net']]
  if y%270:raise ValueError('Source row phase not covered by M2 phase0')
  shapes.append(dict(net=net,layer='M1',bbox_DBU=[x-9,y-9,b[0]+18,y+9],role='rail_extension'))
  shapes+=via(g,'VIA12',x,y,net)+via(g,'VIA23',x,y,net)
 for n,x in xs.items():
  yy=[(r['bbox_DBU'][1]+r['bbox_DBU'][3])//2 for r in rails if r['net']==n]
  shapes.append(dict(net=name+'.'+n,layer='M3',bbox_DBU=[x-9,min(yy)-14,x+9,max(yy)+14],role='local_feed_trunk'))
 return dict(name=name,existing_left_gap_DBU=box[0]-clearance_left_DBU,proposed_left_extent_DBU=left-14,local_rail_taps=len(rails),VIA12_instances=len(rails),VIA23_instances=len(rails),required_external_supply_terminals=[name+'.VDD',name+'.VSS'],upstream_supply_current_EM_voltage_drop=None,global_PG_OBS_overlap_unproven=True,shapes=shapes)

def build():
 g=tech();d=B.C.inputs();m=B.C.build();hd,_=B.C.H.H.inputs();lef=hd['cell_LEF.json']['BUFx4_ASAP7_75t_R'];a=d['model.json'];bank=a['selector_additional_core_clock_bank'];bb=bank['named_site_bank_bbox_DBU']
 groups=[('selector_bank',d['selector_core_clock_cells.jsonl.gz'])]+[(f'raw_shard{s}',inv['proposed_sites']) for s,inv in enumerate(m['raw_empty_row_correction_site_inventories'])]
 feeds=[pg_feed('selector_bank',bb,bank['PG_M1_literal_rails'],g,bank['source_current_selector_bbox_DBU'][2])]
 for s in (0,1):
  raw=a['physical_shards'][str(s)];box=raw['raw_slot_bbox_DBU'];feeds.append(pg_feed(f'raw_shard{s}',box,raw['PG_M1_literal_rails'],g,box[0]-4320))
 escapes=[]
 for name,cells in groups:
  for c in cells:
   for p in ('A','Y'):escapes.append(dict(group=name,**local_escape(c,p,g,lef)))
 return dict(schema='DS_C9_NAMED_LOCAL_PG_PIN_ESCAPE_1',candidate=m['candidate'],prerequisite_commit='78153540c36363a5ec0b6cc421c3298f60e39181',single_selected_bank=True,duplicate_bank_charge_mm2=0,buffer_groups={n:len(c) for n,c in groups},signal_ports=len(escapes),local_supply_feed_constructions=feeds,signal_escape_constructions=escapes,
  source_M1_pin_contact_VIA12_and_M2_to_M3_construction=True,M2_horizontal_M3_vertical=True,track_phase_extended_from_retained_grid_not_actual_current_DEF=True,
  physical_unimplemented_geometry=True,source_clock_branch_to_relay_site_assignment=False,FF_CLK_sink_escapes_not_constructed=True,selector_clock_sink_assignment=False,
  input_clock_reset_skew_slew_and_typed_hold_qualified=False,signal_PG_via_mutual_spacing_OBS_full_join=False,
  added_route_RC_load_ps=None,selected_station_C=None,actual_consumer_deadline=None,additional_cell_area_mm2=0,geometry_wiring_is_not_zero_cost_or_zero_latency=True,
  reticle_screen_mm2=m['whole_selector_replacement_screen_mm2'],no_new_bank_or_cell_recharge=True,remaining_proven_global_fit_deficit_mm2=None,contextual_PR_admitted=False,physical_fit=False,new_jobs=[])
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.parent.mkdir(parents=True,exist_ok=True);m=build()
 for field in ('signal_escape_constructions','local_supply_feed_constructions'):
  raw=(json.dumps(m.pop(field),sort_keys=True,separators=(',',':'))+'\n').encode();blob=gzip.compress(raw,mtime=0);fn=field+'.json.gz';(a.out.parent/fn).write_bytes(blob);m[field]=dict(file=fn,sha256=hashlib.sha256(blob).hexdigest())
 a.out.write_text(json.dumps(m,sort_keys=True,indent=2)+'\n')
