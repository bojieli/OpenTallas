#!/usr/bin/env python3
"""Static PAR2 physical ownership and proposed gather home; no routed latency."""
import argparse,gzip,json,hashlib
from pathlib import Path
import dsrom_capture_home_r49 as H
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'results/uarch/dsrom_capture_physical_shard_paths_20261002'
SERVICE=ROOT/'results/uarch/dsrom_capture_home_20261002/inputs/services.json.gz'
def owner(row):
    if not isinstance(row,int) or isinstance(row,bool) or not 0<=row<576:raise ValueError('row bounds')
    root=(row%256)//2
    return dict(row=row,logical_root=root,physical_shard=root//64,local_root=root%64)
def rect_distance(a,b):
    # Rectangular endpoint envelopes, never obstacle-aware routed bounds.
    minimum=sum(max(0,b[i]-a[i+2],a[i]-b[i+2]) for i in (0,1))/1000
    maximum=sum(max(abs(a[i]-b[i+2]),abs(a[i+2]-b[i])) for i in (0,1))/1000
    return dict(endpoint_L1_min_um=minimum,endpoint_L1_max_um=maximum,actual_pin_route_length_um=None)
def build():
    h=H.build();services=json.loads(gzip.decompress(SERVICE.read_bytes()));g=next(v for v in services if v['name']=='HUB_GATHER');vm=next(v for v in services if v['name']=='HUB_VM')
    rows=[owner(i) for i in range(576)]
    if [sum(r['physical_shard']==s for r in rows) for s in (0,1)]!=[320,256]:raise ValueError('shard seats')
    common=h['corrected_common_bbox_DBU'];paths=[]
    for raw in h['per_shard_raw_homes']:
        s=raw['shard'];box=raw['bbox_DBU']
        paths.append(dict(shard=s,distinct_die_identity=s,island_bbox_DBU=h['canonical_island_home_DBU'],raw_bbox_DBU=box,raw_to_local_control=rect_distance(box,common),raw_to_corresponding_local_HUB_GATHER_region_projection=rect_distance(box,g['bbox_DBU']),local_control_reservation_bbox_DBU=common,
          local_control_actual_instances=None,local_control_to_corresponding_HUB_GATHER_region_projection=rect_distance(common,g['bbox_DBU']),
          actual_gather_die=0,requires_physical_stage_boundary=(s!=0),stage_link_endpoint_pin_boxes=None,
          request_bits=187,reply_bits=240,request_ACK_width_bits=None,accepted_request_ACK_return_latency_cycles=None))
    return dict(schema='DS_CAPTURE_PHYSICAL_SHARD_PATHS_1',candidate=h['candidate'],
      sources={'R49_home_model_sha256':hashlib.sha256(json.dumps(h,indent=2,sort_keys=True).encode()+b'\n').hexdigest(),'retained_services_sha256':hashlib.sha256(SERVICE.read_bytes()).hexdigest()},
      ordered_rows=rows,physical_roots_per_die=64,exact_seats_per_die=[320,256],
      frozen_global_context_bits=169,routed_context_bits=170,physical_shard_is_separate_route_field=True,phase_context_bits=170,request_bits=187,reply_bits=240,physical_shard_identity_bits=1,stage_identity_bits=6,rank_identity_bits=2,
      single_logical_phase_lease=True,physical_shard_ID_does_not_create_second_context=True,
      proposed_gather_home=dict(physical_shard_die=0,retained_region_name=g['name'],bbox_DBU=g['bbox_DBU'],actual_consumer_pin_box=None,provider_implemented=False),
      proposed_VM_home=dict(physical_shard_die=0,retained_region_name=vm['name'],bbox_DBU=vm['bbox_DBU']),
      paths=paths,ordered_output=list(range(576)),remote_rows_per_phase=256,
      same_die_projected_distance_does_not_price_remote_crossing=True,
      remote_minimum_payload_bits=256*69,remote_reply_bits_without_request_ACK_or_link_overhead=256*240,
      gathers_in_source_row_order=True,requires_remote_delivery_fence_before_phase_lease_release=True,
      no_combinational_readtree_spanning_dies=True,no_field_ready_added=True,
      register_cuts_selected=False,source_clock='single clk',target_stream_GHz=1.2,target_SU_GHz=.9,implemented_CDC=None,
      actual_accepted_consumer_deadline=None,full_phase_latency_delta_cycles=None,
      complete_cells_controls_PG_clock_reset_routes=False,physical_fit=False,contextual_PR_admitted=False,new_jobs=[])
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(build(),indent=2,sort_keys=True)+'\n')
