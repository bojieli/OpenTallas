#!/usr/bin/env python3
"""Explicit successor join; preserves historical channel and reset models."""
import hashlib
import gzip
import json
import qwen_rom_kv_channel_shoreline as Q
import qwen_rom_channel_release_trim as T

R=Q.R
OUT=Q.OUT


def price():
    m=Q.price()
    dependency=R.obj(OUT/'inputs/Russell-02e9-ampere-dependency-r1.json')
    successor=R.obj(OUT/'inputs/Russell-02e9-model-r7.json')
    admission=R.obj(OUT/'inputs/Russell-02e9-admission-r1.json')
    pins=R.obj(OUT/'inputs/Russell-02e9-implementation-pins-r1.json')
    assert R.sha(OUT/'inputs/Russell-02e9-model-r7.json')==dependency['model_sha256']==admission['model_sha256']
    assert R.sha(OUT/'inputs/Russell-02e9-source.py')==pins['tools/uarch_model_qwen_kv_successor.py']
    assert successor['configuration']['tiles_per_lane']==[220,220,220,219,219,219,219]
    aligned=T.record('model-r3.json')
    #Keep the larger user-handoff service reservation; no missing-source credit.
    service=max(successor['cells']['total_known_service_mm2'],18.381568)
    increase=service-m['service_known_reservation_mm2']
    m['known_composed_area_mm2']+=increase
    m['remaining_area_before_unknown_placements_mm2']-=increase
    for slot in m['controller_slots']:
        old=slot['service_known_reservation_mm2']
        slot['service_known_reservation_mm2']=service/4
        slot['minimum_cell_macro_utilization']*=((service/4+slot['inherited_other_service_debit_reserved_mm2'])/(old+slot['inherited_other_service_debit_reserved_mm2']))
    m['service_known_reservation_mm2']=service
    m['schema']='QWEN_KV7_NATIVEPHY_CHANNEL_PARENT_ADMISSION_R6'
    m['Russell_selected_commit']='02e9c04b7'
    m['Russell_successor_model_sha256']=dependency['model_sha256']
    m['Russell_committed_service_mm2']=successor['cells']['total_known_service_mm2']
    m['handoff_discrepancy']=dict(reported_conditional_us=361.0713,reported_service_mm2=18.381568,
        committed_conditional_us=admission['full_token_conditional_s']*1e6,
        committed_service_mm2=successor['cells']['total_known_service_mm2'],larger_area_reserved=True,
        reported_model_source_available=False)
    m['successor_observed_conditional_calendar_s']=admission['full_token_conditional_s']
    m['successor_model_and_live_source_match']=True
    m['successor_source_match_scope']='pinned committed analytical implementation; hardware replacement not instantiated'
    cells=successor['cells']
    oldff=m['successor_added_FF_count'];newff=sum(cells['successor_delta_FF'].values())
    m['source_sized_clock_pins']+=newff-oldff
    m['source_reset_upper']+=newff-oldff
    m['successor_added_FF_count']=newff
    m['successor_added_collector_buffers']=cells['collector_buffers']
    m['successor_replica_counts']=cells['replicas']
    m['fill_fanout_buffers']=cells['total_fill_distribution_buffers']
    #637 shared control wires explicitly consume spare reservations. Endpoint
    #partition is a model allocation, not a claim of source routing completion.
    for channel in m['dedicated_fill_channels']:
        channel['layers']=['M6','M8']
        channel['shared_control_track_reservation']=91
        channel['remaining_spare_tracks']=93
        channel['shared_control_endpoint_source_binding_complete']=False
    m['current_shared_cut']=dict(fill=7336,shared_control=637,required=7973,available_legacy=1360,
        legacy_deficit=6613,partitioned_channel_capacity=7*1360,
        assigned_fill_control=7*(1048+91),clock_reset_reserved=7*128,remaining_spare=7*93)
    m['service_boundary_cut_ledger']=dict(source_boundary_bits=42452,fill_on_separate_M6_M8=7336,
        remaining_nonfill_bits=42452-7336,M9_two_trunk_capacity=sum(s['capacity'] for s in m['shoreline_cuts']),
        aggregate_capacity_only=True,per_family_routes_and_cuts_complete=False)
    m['aligned_local_release']=dict(model_sha256=hashlib.sha256(gzip.decompress((R.ROOT/T.OUT/'model-r3.json.gz').read_bytes())).hexdigest(),
        selected_map_sha256=aligned['selected_map_sha256'],source_clock_pins=aligned['source_clock_pins'],
        source_reset_pins=aligned['source_reset_pins'],source_counts_not_new_map=True,
        actual_local_groups=aligned['actual_reset_clock_leaf_groups'],new_local_FFs=aligned['new_local_FFs'],
        total_clock_pins=aligned['total_clock_pins'],total_reset_pins=aligned['total_reset_pins'],
        reserved_area_um2=aligned['complete_reserved_cell_area_um2'],area_scope=aligned['complete_reserved_cell_area_scope'],
        cuts=aligned['cuts'],corners={c:dict(raw_reset_failures=t['raw_reset_failures'],
            controlled_reset_failures=t['controlled_reset_failures'],
            nominal_skew_ps=max(s['skew_ps'] for s in t['nominal_same_source_clock_scenarios']),
            ACK_out_of_characterization=aligned['stage_and_ACK_audit'][c]['ACK_out_of_characterization'])
            for c,t in aligned['timing'].items()})
    m['finite_service_deficit_us']=(admission['full_token_conditional_s']-admission['target_s'])*1e6
    m['reported_service_deficit_us']=361.0713-1e6/3000
    m['admission_failures']=['finite service calendar exceeds target',
        'SS/FF clock skew exceeds unchanged 20ps construction demand',
        'startup ACK outputs outside characterized load domain',
        'controller/PHY strict refresh, held ACK and sustainable bandwidth unmeasured',
        'complete source epoch/init/abort/producer accepted-demand binding absent',
        'exclusive PG/via/OBS/pin landing and every service-family cut unproved',
        'whole field root distribution and transport pipeline/hold costs incomplete']
    m['source_matched_successor_calendar_admitted']=False
    m['status']='FAIL_G0_CONSTRUCTED_GEOMETRY_AND_LOCAL_CUTS_ONLY'
    return m


if __name__=='__main__':
    p=R.ROOT/OUT/'model-r6.json'
    if p.exists():raise ValueError('preserve verdict')
    Q.M.write(p,price())
