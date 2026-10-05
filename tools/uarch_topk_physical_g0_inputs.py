#!/usr/bin/env python3
"""Complete fixed-shape selector physical G0 inputs; no RTL or physical launch.

Geometry/track counts use immutable parent rectangles and the retained phased
routing grid. Extending the grid is a candidate model, not an existing full-die
ODB. Empty reservation geometry is not proof of detailed route/clock closure.
"""
import argparse
import ast
import gzip
import hashlib
import json
import math
from pathlib import Path
import subprocess
import uarch_topk_integer_tree_model as T

FULL='aa745a879e20e3db598f7be9345cb7ad3b1d5d2f'
SERVICE='1d8304647ceb7a1b64d96217c6dfa075b5704f0a'
PARENT='d2b3fde765a9cb1b97ec03864dbf7e48f0cf51f4'
GRID='4b6708348f3938e0830c3549fbbecadbce18e798'
POLICY='d4b9a4a6966bf211df81136b3df886a980f4bd36'
ROW_GRID_DBU=2160

def load(repo,commit,path,pins):
    b=subprocess.check_output(['git','show',commit+':'+path],cwd=repo)
    pins[commit+':'+path]={'commit':commit,'path':path,'sha256':hashlib.sha256(b).hexdigest()}
    return json.loads(gzip.decompress(b) if path.endswith('.gz') else b)

def wire_constants(repo,pins):
    path='tools/uarch_model.py'
    data=subprocess.check_output(['git','show',FULL+':'+path],cwd=repo)
    pins[FULL+':'+path]={'commit':FULL,'path':path,'sha256':hashlib.sha256(data).hexdigest()}
    required={'WIRE_PS_PER_UM_LOADED','WIRE_OVERHEAD_PS','UNCERTAINTY_PS'};values={}
    for n in ast.parse(data).body:
        if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id in required:
            values[n.targets[0].id]=ast.literal_eval(n.value)
    if set(values)!=required:raise ValueError('retained wire assumptions missing')
    return values

def overlap(a,b):
    return min(a[2],b[2])>max(a[0],b[0]) and min(a[3],b[3])>max(a[1],b[1])

def area(box):return (box[2]-box[0])*(box[3]-box[1])/1e12

def track_count(grid,layers,axis,lo,hi):
    if hi<=lo:raise ValueError('nonpositive channel interval')
    counts={}
    for layer in layers:
        match=[x for x in grid['grids'] if x['layer']==layer]
        if len(match)!=1:raise ValueError('missing unique layer grid')
        positions=set()
        for start,count,step in match[0][axis]:
            if step<=0 or count<=0:raise ValueError('invalid phased grid')
            # Explicit analytical phase extension. Endpoints are half-open.
            first=math.ceil((lo-start)/step);last=math.ceil((hi-start)/step)
            positions.update(start+i*step for i in range(first,last))
        counts[layer]=len(positions)
    return {'per_layer':counts,'unique_phased_raw_tracks':sum(counts.values()),
            'signal_tracks_after_50pct_reserve':sum(counts.values())//2,
            'scope':'candidate phase extension with 50% PG/clock/via reserve; no detailed route credit'}

def required_span(grid,layers,axis,start,tracks):
    span=ROW_GRID_DBU
    while track_count(grid,layers,axis,start,start+span)['signal_tracks_after_50pct_reserve']<tracks:
        span+=ROW_GRID_DBU
    return span

def closest_L1(a,b):
    return max(0,a[0]-b[2],b[0]-a[2])+max(0,a[1]-b[3],b[1]-a[3])

def build(repo):
    pins={}
    inventory_path='tools/uarch_topk_integer_tree_model.py'
    inventory_bytes=subprocess.check_output(['git','show',FULL+':'+inventory_path],cwd=repo)
    if Path(T.__file__).read_bytes()!=inventory_bytes:
        raise ValueError('imported inventory implementation changed from complete-model source')
    pins[FULL+':'+inventory_path]={'commit':FULL,'path':inventory_path,'sha256':hashlib.sha256(inventory_bytes).hexdigest()}
    full=load(repo,FULL,'results/uarch/topk_balanced_filter_successor_model_20261002/model.json',pins)
    service=load(repo,SERVICE,'results/uarch/topk_integer_tree_service_model_20261002/model.json',pins)
    root='results/uarch/dsrom_noECC_complete_parent_map_20261002/'
    parent=load(repo,PARENT,root+'r2/model.json',pins)
    geometry={k:load(repo,PARENT,root+'r2/'+k+'.json.gz',pins) for k in ['services','field','macros','cfg','bands']}
    grid=load(repo,GRID,'results/uarch/dsrom_l20_hierarchical_reservation_20261002/grid_inputs/DS_grid.json',pins)
    policy=load(repo,POLICY,'results/uarch/ds_mtp_agentic_headline_policy_20261002.json',pins)
    wire=wire_constants(repo,pins)
    rows=[x for x in full['shapes'] if x['compiled']=={'N':4,'NMAX':2048,'LDW':4,'P':64,'PF':64,'DIG':8,'CB':14,'NBIN':256}]
    if len(rows)!=2 or {x['runtime']['n'] for x in rows}!={512,2048}:raise ValueError('full compiled instance/runtime binding changed')
    by_n={x['runtime']['n']:x for x in rows};shape=by_n[2048]
    need=shape['area']['proposed_source_50pct_proxy_core_mm2'];box=parent['selector']['single_full_slot_bbox_DBU'][:]
    width=box[2]-box[0];box[3]=box[1]+math.ceil(need*1e12/width/ROW_GRID_DBU)*ROW_GRID_DBU
    publics={'inputs':{'ld_valid':1,'ld_id':1,'ld_rank':2,'ld_word':9,'ld_data':2048,'go':1,'n':14,'k':14,'stride':32},
             'outputs':{'busy':1,'done':1,'fault':1,'out_valid':1,'out_nw':3,'out_data':2048,'out_last':1,'stat_cycles':32}}
    tracks=sum(sum(x.values()) for x in publics.values())
    services={x['name']:x['bbox_DBU'] for x in geometry['services']};hub=services['HUB_COLLECTIVE'];vm=services['HUB_VM']
    hspan=required_span(grid,['M2','M4'],'Y',box[1],tracks)
    vspan=required_span(grid,['M3','M5'],'X',hub[0],tracks)
    horizontal=[box[2],box[1],hub[0]+vspan,box[1]+hspan]
    vertical=[hub[0],box[1],hub[0]+vspan,hub[1]]
    if vertical[3]<=vertical[1] or horizontal[2]<=horizontal[0] or vertical[2]>hub[2]:raise ValueError('current route proposal invalid')
    items=[]
    for kind,data in geometry.items():
        for i,item in enumerate(data):
            items.append((kind,item.get('name',f'{kind}[{i}]'),item['bbox_DBU']))
    collisions=[]
    for label,b in [('complete_selector',box),('horizontal_escape',horizontal),('vertical_to_hub_lower_boundary',vertical)]:
        for kind,name,other in items:
            if overlap(b,other):collisions.append({'proposal':label,'retained_kind':kind,'retained':name})
    if overlap(box,horizontal) or overlap(box,vertical):raise ValueError('corridor displaces selector itself')
    shared=[max(horizontal[0],vertical[0]),max(horizontal[1],vertical[1]),min(horizontal[2],vertical[2]),min(horizontal[3],vertical[3])]
    corridor_area=area(horizontal)+area(vertical)-area(shared)
    group=service['source_service_binding']['ROM']
    calls=[]
    for call in group['calendar_calls']:
        n=call['runtime_n'];s=by_n[n];load_edges=s['ports']['minimum_accepted_load_edges_scores_plus_IDs'];cycles=s['cycle_envelope']
        calls.append(dict(call,accepted_load_min_edges=load_edges,uninterrupted_service_envelope_edges=cycles,
            burst_load_plus_service_envelope_edges=load_edges+cycles,added_service_edges=142,
            original_deadline=group['deadline']))
    def corridor_capacity(b,layers,axis):
        return track_count(grid,layers,axis,b[1] if axis=='Y' else b[0],b[3] if axis=='Y' else b[2])
    internal={'hist_first_registered_payload_bits':256*(64//2)*2,
              'suffix_max_distributed_payload_bits':256*14,
              'winner_first_distributed_payload_bits':(256//2)*(1+8+14),
              'equal_prefix_max_distributed_payload_bits':shape['routing']['equal_prefix_max_distributed_bits'],
              'sort_stage_distributed_payload_bits':shape['routing']['sort_stage_distributed_bits'],
              'sort_lane_bisection_record_tracks_one_distance32_level':64*(32+7),
              'prefix_lane_bisection_remote_count_tracks_distance32_level':32*7,
              'scope':'internal buses are separately distributed stage planes, not summed as one invented physical cut; stage placement and metadata endpoints remain to bind'}
    instance=shape['state_bits'];cell=shape['area']['accounted_cell_master_sum_um2']
    base_state=T.state_inventory(4,2048,64,64,8)
    hist_extra=256*sum((64>>level)*(level+1) for level in range(1,6))+5
    suffix_extra=(2*256-3)*14
    choose_extra=256*(14+1)+256+(256-1)*(1+8+14)-(8+14)
    control_extra=T.clog2(2*8+8+3)-2
    added_integer={'hist_registered_levels_and_valid':hist_extra,
        'suffix_internal_up_down':suffix_extra,'choose_predicate_and_highbin_tree':choose_extra,
        'pick_control':control_extra}
    filter_bits={k:v for k,v in shape['filter']['additional_bits'].items() if k!='total'}
    if base_state['storage_bits']+sum(added_integer.values())+sum(filter_bits.values())!=instance:
        raise ValueError('complete register ledger does not conserve full state')
    area_parts={'FF':shape['area']['FF_um2'],'additional_pipeline_hold_mux':shape['area']['hold_mux_um2'],
       'integer_hist_suffix_choice':shape['area']['integer_hist_suffix_choice_logic_um2'],
       **{'retained_'+k:v for k,v in shape['area']['retained_shared_cones_um2'].items()},
       **{'filter_'+k:v for k,v in shape['filter']['logic_area_um2'].items()},
       **{'other_'+k:v for k,v in shape['area']['other_source_construction_allowances_um2'].items()}}
    if not math.isclose(sum(area_parts.values()),cell,rel_tol=1e-12):raise ValueError('fullcell ledger changed')
    state=shape['area']['FF_um2']/0.5/1e6
    old_state=parent['selector']['state_already_priced_mm2'];old_extra=parent['selector']['only_additional_full_proxy_charge_mm2']
    selector_extra=area(box)-old_state
    distance={k:closest_L1(box,b)/1000 for k,b in [('collective',hub),('VM',vm)]}
    wire_budget=833-wire['UNCERTAINTY_PS']-wire['WIRE_OVERHEAD_PS']
    max_wire_hop=wire_budget/wire['WIRE_PS_PER_UM_LOADED']
    external_hop_screen={k:math.ceil(d/max_wire_hop) for k,d in distance.items()}
    return {'schema':'DSROM_COMPLETE_BALANCED_SELECTOR_PHYSICAL_G0_INPUTS_V1','sourcepins':pins,
      'compiled':shape['compiled'],'runtime_counts':[512,2048],'source_contexts':1,'selector_instances_per_die':1,
      'replicas_per_TP_group':4,'whole_system_replicas':None,'replication_scope':'all participating dies repeat identical gathered select; do not multiply latency by4; stage sharing/totaldie count remains owner-bound',
      'MACs_per_edge':0,'candidate_memory_bits':524288,'full_state_bits':instance,'added_state_bits_vs_original':shape['added_state_bits_vs_original'],
      'register_ledger':{'retained':base_state['bits_by_register_group'],'additional_integer':added_integer,
         'additional_filter':filter_bits,'total':instance,'released_or_aliased_state_credit':0,
         'new_command_contexts':0,'source_inventory_sha256':hashlib.sha256(inventory_bytes).hexdigest()},
      'area':{'full_cell_master_construction_um2':cell,'FF_cell_master_um2':shape['area']['FF_um2'],
        'cell_area_groups_um2':area_parts,
        'full_proxy_core_mm2_50pct':need,'row_aligned_complete_slot_mm2':area(box),'full_state_only_core_mm2_50pct':state,
        'already_priced_state_core_mm2':old_state,'full_state_additional_over_already_priced_core_mm2':state-old_state,
        'new_complete_selector_charge_over_already_priced_state_mm2':selector_extra,
        'previous_selector_extra_charge_mm2':old_extra,'increment_over_current_parent_selector_charge_mm2':selector_extra-old_extra,
        'new_escape_corridor_union_mm2':corridor_area,'selector_plus_corridor_increment_no_containment_credit_mm2':selector_extra-old_extra+corridor_area,
        'replacement_once':'replace parent selector extra once, retain inherited state once; no SRAM/alias or old-store free credit',
        'scope':'construction reservation, not mapped area; clockPG/timingrepair/actual instance union unclosed'},
      'ports':{'bit_inventory':publics,'signal_pin_tracks':tracks,'clock_reset_pins':2,'new_product_ports':0,
        'payload_load_B_per_edge':256,'payload_result_B_per_edge':256,'hist_RF_read_B_per_edge':256,'filter_RF_read_B_per_edge':512,
        'load_result_wire_alias_credit':0,'candidate_bytes_full_compiled':65536},
      'integer_and_communication_intensity':{'hist_add_nodes_per_issued_row':256*(64-1),
        'suffix_add_nodes_per_pass':2*(256-1),'highbin_choose_mux_nodes_per_pass':255,
        'filter_equal_prefix_add_nodes_per_row':shape['filter']['network_counts']['prefix_add_nodes'],
        'filter_sort_compare_exchange_nodes_per_row':shape['filter']['network_counts']['sort_compare_exchange_nodes'],
        'integer_ops_do_not_count_as_MACs':True,'internal_hist_plus_filter_RF_read_B_per_candidate':4*4+8,
        'candidate_load_B_per_candidate':8,'internal_RF_read_bytes_to_load_byte_ratio':3,
        'scope':'steady-state integer pipeline construction; active passes/rows source-controlled, no independent command overlap'},
      'placement':{'row_grid_DBU':ROW_GRID_DBU,'complete_bbox_DBU':box,'horizontal_escape_bbox_DBU':horizontal,
        'vertical_escape_to_collective_lower_boundary_bbox_DBU':vertical,'positive_retained_rectangle_overlaps':collisions,
        'retained_geometry_checked':{k:len(v) for k,v in geometry.items()},'inside_33000x26000um_die':all(0<=b[0]<b[2]<=33000000 and 0<=b[1]<b[3]<=26000000 for b in [box,horizontal,vertical]),
        'collective_reserved_bbox_DBU':hub,'VM_reserved_bbox_DBU':vm,'shared_hub_interior_not_assumed_free':True,
        'unknown_allocations_not_assumed_free':True},
      'tracks':{'reserve_fraction':0.5,'horizontal_escape':corridor_capacity(horizontal,['M2','M4'],'Y'),
        'vertical_escape':corridor_capacity(vertical,['M3','M5'],'X'),'internal_planes':internal,
        'selector_whole_height_horizontal_grid_screen':corridor_capacity(box,['M2','M4'],'Y'),
        'selector_whole_width_vertical_grid_screen':corridor_capacity(box,['M3','M5'],'X'),
        'actual_full_die_routed_capacity':None,'via_escape_and_actual_PG_clock_obstructions_closed':False},
      'latency':{'calls':calls,'total_calls':len(calls),'serial_service_envelope_edges_per_position':sum(c['uninterrupted_service_envelope_edges'] for c in calls),
        'minimum_burst_load_edges_per_position':sum(c['accepted_load_min_edges'] for c in calls),
        'burst_load_plus_service_envelope_edges_per_position':sum(c['burst_load_plus_service_envelope_edges'] for c in calls),
        'added_service_edges_per_position':1278,'added_ns_at_policy_1p2GHz':1065,
        'six_verify_positions_if_fully_serial_added_edges':7668,'six_verify_positions_if_fully_serial_added_us':6.39,
        'minimum_rectangle_L1_distances_um':distance,'actual_relocated_transport_latency_delta':None,
        'distance_scope':'minimum between reserved rectangles conditional on endpoints actually residing there; difference of minima is NOT a transport delta',
        'source_release':group['release'],'no_new_ACK':True,'fulltoken_or_MTP_rate':None},
      'clock':dict(shape['clock'],current_parent_branch_basis=parent['clock'],branch_counts_not_selector_stage_timing=True,
         wire_context_screen={'retained_unified_model_constants':wire,'nonlogic_wire_budget_ps':wire_budget,
           'maximum_hop_um_before_stage_logic':max_wire_hop,
           'flat64lane_over_entire_slot_max_xor32_hop_um':width/2000,
           'flat64lane_wholewidth_hop_passes_nonlogic_wire_screen':width/2000<=max_wire_hop,
           'endpoint_rectangle_conditional_minimum_segment_counts':external_hop_screen,
           'existing_physical_register_or_link_segments_verified':False,
           'scope':'retained loaded-wire analytical screen, NOT SS timing; actual gate delay reduces allowed wire further. Do not infer added stages or a transport delta from segment count.',
           'required':'bind actual stage placement/local partner hops and existing source transport registers with aligned control/data; global 64lane linear spread over full width is not admitted by this screen'},
         stages_to_close=['hist RF read/decode/6 registered integer reductions/accumulation','14bit suffix up/down level and predicate/high-bin choose','6 registered7bit equal-prefix levels','14bit quota feedback compare/subtract','21 registered7bitkey+39bitrecord compare/exchange levels','stable count/zero padding/mask/append and public VM load/write endpoints']),
      'headline_policy':{'commit':POLICY,'status':policy['status'],'qualified_rate':None,'local_tau_is_sensitivity_only':True},
      'G0':{'model_inputs_complete_for_owner_review':True,'geometry_and_track_screen_pass':not collisions,
        'RTL_admitted':False,'PR_admitted':False,'missing':['Archimedes actual selector/escape corridor ownership and fullstate logic replacement acceptance','actual via/clockPG/pin escape and sharedhubinterior route allocation','Maxwell sourceendpoint/caller transport residence bound','source-construction stage context admission followed by fullinstance SSsetup/FFhold qualification']},
      'new_jobs':0,'undersized_standin':False,'PVE2_PVE3':'drain-only'}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    with a.out.open('x') as f:json.dump(build(a.repo),f,indent=2,sort_keys=True);f.write('\n')
