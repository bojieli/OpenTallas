#!/usr/bin/env python3
"""One fixed source-clock floor site annex; routes/branches still unqualified."""
import argparse,gzip,hashlib,json,math
from pathlib import Path
import dsrom_capture_home_r49 as H
ROOT=Path(__file__).resolve().parents[1]
INPUT=ROOT/'results/uarch/dsrom_capture_identity_slot_join_20261002/inputs/selector_5ff_r2.json'
def build():
    raw=INPUT.read_bytes();pin=json.loads((INPUT.parent/'selector_origin.json').read_text());
    if hashlib.sha256(raw).hexdigest()!=pin['sha256']:raise ValueError('Selector input drift')
    s=json.loads(raw);levels=s['clock']['additional_core_fanout_floor']['leaf_to_root_counts']
    if sum(levels)!=70406 or s['clock']['station_fanout_floor']['BUF_cells']!=48007:raise ValueError('clock union drift')
    b=s['slot']['current_selector_bbox_DBU'];width=b[2]-b[0]
    columns=width//378;rows=math.ceil(sum(levels)/columns);height=rows*540
    annex=[b[0],b[3],b[2],b[3]+height]
    sites=[];offset=0
    for level,n in enumerate(levels):
        for i in range(n):
            ordinal=offset+i;x=annex[0]+(ordinal%columns)*378;y=annex[1]+(ordinal//columns)*540
            sites.append(dict(proposed_site_ID=f'selector.core_clock_floor.level{level}.buf{i}',level=level,master='BUFx4_ASAP7_75t_R',bbox_DBU=[x,y,x+378,y+270],orientation='R0',actual_instance_or_net=None))
        offset+=n
    raw=json.dumps(sites,sort_keys=True,separators=(',',':')).encode()
    reservation=width*height/1e12
    old_selector=H.H.build()['retained_selector_core_bbox_DBU']
    d,_=H.H.inputs();fields=H.H.current_fields(d['field.json'],d['frames.json']);dy=max(x['bbox_DBU'][3] for x in fields)-max(x['bbox_DBU'][3] for x in d['field.json'])
    growth=[b[0],old_selector[3],b[2],annex[3]];collisions=[]
    for name,items in [('field',fields),('cfg',d['cfg.json']),('bands',d['bands.json']),('services',d['services.json'])]:
        for item in items:
            bb=item['bbox_DBU'];bb=[v+(dy if name in ('cfg','bands') and i%2 else 0) for i,v in enumerate(bb)]
            if H.H.overlap(growth,bb):collisions.append(dict(kind=name,name=item.get('name',item.get('local_pair')),bbox_DBU=bb))
    slot_growth=(annex[3]-old_selector[3])*width/1e12
    # Current 4cc screen charged roundedcore1.68242 and station0.62337924324.
    # Source-corrected ties/guards/coreclock are replacements, never readd station.
    exactdelta=s['area']['proposed_finite_cell_reservation_with_core_clock_floor']-(1.68242+s['area']['allowed_station_including_station_clock_floor'])
    return dict(schema='DS_SELECTOR_FIXED_CLOCK_FLOOR_SITE_ANNEX_1',candidate=s['candidate'],source_commit='5ff80ab93455caddfce7c2adaed91e0cef0e3b78',source_sha256=hashlib.sha256(INPUT.read_bytes()).hexdigest(),
      source_core_bbox_DBU=b,prior_4cc_core_bbox_DBU=old_selector,clock_annex_bbox_DBU=annex,new_combined_core_bbox_DBU=[b[0],b[1],b[2],annex[3]],
      allowed_BUF_master='BUFx4_ASAP7_75t_R',cell_width_DBU=378,cell_height_DBU=270,rowpitch_DBU=540,columns=columns,rows=rows,
      core_clock_BUF70406_separate_from_transport48007=True,total_clock_floor118413=True,site_count=len(sites),proposed_sites_sha256=hashlib.sha256(raw).hexdigest(),
      proposed_sites=sites,site_capacity=columns*rows,unused_sites=columns*rows-len(sites),
      clock_annex_reservation_mm2=reservation,additional_clock_source50pct_floor_mm2=s['area']['additional_separate_core_clock_fanout_floor'],
      combined_selector_priced_mm2=s['area']['proposed_finite_cell_reservation_with_core_clock_floor'],exact_replacement_delta_vs_4cc_selector_charge_mm2=exactdelta,
      prior_4cc_selector_rect_growth_mm2=slot_growth,
      retained_whole_no_containment_with_cell_replacement_screen_mm2=H.build()['area']['whole_reticle_screen_unchanged_mm2']+exactdelta,
      no_add_rectangle_growth_on_top_of_contained_cell_debit_without_union=True,
      original_core_logic_retained=True,area_screen_is_not_actual_site_union=True,
      known_retained_rectangle_growth_collisions=collisions,annex_clearance_against_actual_OBS_PG_pin_signal_routes=None,existing_core_occupied_cells=None,required_equal_depth_pad_BUF_count=None,
      clock_network_edges_pins_wire_skew_reset_and_PG=None,actual_consumer_deadline=None,physical_fit=False,contextual_PR_admitted=False,new_jobs=[])
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.parent.mkdir(parents=True,exist_ok=True);m=build();sites=m.pop('proposed_sites');raw=json.dumps(sites,sort_keys=True,separators=(',',':')).encode();blob=gzip.compress(raw,mtime=0);(a.out.parent/'clock_sites.json.gz').write_bytes(blob);m['clock_sites_file']='clock_sites.json.gz';m['clock_sites_gzip_sha256']=hashlib.sha256(blob).hexdigest();a.out.write_text(json.dumps(m,indent=2,sort_keys=True)+'\n')
