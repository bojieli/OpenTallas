"""Existing selector causal cuts and unchanged-graph clock relocation demands.

No new RTL, cell graph, physical placement or timing execution. This is an
exact source receiver/branch ledger for the current constructive owners.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'results/uarch/dsrom_selector_causal_timing_join_20261003'
CORE='results/rtl/dsrom_balanced_selector_candidate_prepare_20261002/gate_r4/candidate/ot_coll_topk_merge_staged_impl_prepare.sv'

def sha(b):return hashlib.sha256(b).hexdigest()
def load(name):
    raw=(BASE/'inputs'/name).read_bytes()
    return json.loads(gzip.decompress(raw) if name.endswith('.gz') else raw)

def pipeline(source):
    # Each destination is an actual register declaration or preserved baseline
    # register. Widths below are source receivers, not mapped pin capacitances.
    stages=[]
    for level in range(1,7):
        dest=f'hist_pc_{level}' if level<6 else 'h2_pc'
        if level<6 and not re.search(r'reg \['+str(level)+r':0\] '+dest,source):raise ValueError('hist source width changed')
        if f'begin:g_hist_{level}' not in source:raise ValueError('hist stage removed')
        stages.append(dict(family='hist',stage=level,source='h1_hot' if level==1 else f'hist_pc_{level-1}',
            destination=dest,register_receiver_bits=256*(64>>level)*(level+1),data_adder_bits=level+1,
            edge_rule='unconditional posedge',valid='h1_v -> hist_valid six-edge shift; h2_v=hist_valid[5]',
            loaded_timing=None))
    for level in range(8):
        dest=f'suffix_up_{level}'
        if f'if(st==S_PICK && pk=={level}) {dest}' not in source:raise ValueError('suffix causal enable changed')
        stages.append(dict(family='suffix_up',stage=level,source='cnt' if level==0 else f'suffix_up_{level-1}',
            destination=dest,register_receiver_bits=(128>>level)*14,data_adder_bits=14,
            edge_rule=f'st==S_PICK && pk=={level}',source_control_FF_or_holdmux_receiver_bits=(128>>level)*14,
            loaded_timing=None))
    for level in range(8):
        dest=f'suffix_down_{level}' if level<7 else 'suf'
        if f'if(st==S_PICK && pk=={8+level}) begin' not in source:raise ValueError('suffix-down causal enable changed')
        stages.append(dict(family='suffix_down',stage=level,source='zero plus right-subtree count' if level==0 else f'suffix_down_{level-1} plus right-subtree count',
            destination=dest,register_receiver_bits=(2<<level)*14,data_adder_bits=14,
            edge_rule=f'st==S_PICK && pk=={8+level}',source_control_FF_or_holdmux_receiver_bits=(2<<level)*14,
            loaded_timing=None))
    for pk,dest,bits in [(16,'choose_lower_sum',256*15),(17,'choose_pred',256)]:
        if f'if(st==S_PICK && pk=={pk}) {dest}' not in source:raise ValueError('choose causal enable changed')
        stages.append(dict(family='choose',stage=pk,source='suf/cnt/rr' if pk==16 else 'choose_lower_sum/rr',
            destination=dest,register_receiver_bits=bits,edge_rule=f'st==S_PICK && pk=={pk}',
            source_control_FF_or_holdmux_receiver_bits=bits,loaded_timing=None))
    for level in range(7):
        dest=f'choose_node_{level}'
        if f'if(st==S_PICK && pk=={18+level}) {dest}' not in source:raise ValueError('winner stage changed')
        stages.append(dict(family='winner',stage=level,source='choose_pred+suf' if level==0 else f'choose_node_{level-1}',
            destination=dest,register_receiver_bits=(128>>level)*23,edge_rule=f'st==S_PICK && pk=={18+level}',
            source_control_FF_or_holdmux_receiver_bits=(128>>level)*23,loaded_timing=None))
    if 'if(pk==25)' not in source or 'if (pk == 26)' not in source:raise ValueError('choose capture/commit order changed')
    stages.append(dict(family='winner_root',stage=7,source='choose_node_6 pair',destination='pvalid/pbin/pgt',
        register_receiver_bits=23,edge_rule='pk25 capture; pbin/pgt conditional on root valid; pk26 commits prefix',
        extra_pipeline_stages_proposed=0,loaded_timing=None))
    for level in range(6):
        if f'eq_count_{level}[ep{level}]<=' not in source or f'begin:g_eq_{level}' not in source:raise ValueError('equal prefix stage changed')
        stages.append(dict(family='equal_prefix',stage=level,source='f1_eq/id/gt' if level==0 else f'eq_count/id/gt/mask/v_{level-1}',
            destination=f'eq_count/id/gt/mask/v_{level}',register_receiver_bits=64*(level+2+34)+1,
            data_adder_bits=level+2,edge_rule='unconditional posedge payload; asynchronous reset valid',loaded_timing=None))
    if "CB'(eq_count_5[l-1])<eq_left" not in source or 'if(eq_v_5) eq_left<=' not in source:raise ValueError('quota order/feedback changed')
    stages.append(dict(family='quota_feedback',stage=0,source='eq_left and last ordered prefix row',
        destination='eq_left/f2_take/f2_id',edge_rule='eq_v_5 ordered row, one-edge saturating subtract; strict exclusive prefix',
        feedback_width_bits=14,returned_credit_or_ACK=False,added_state_or_stage_proposed=0,loaded_timing=None))
    if "f3_tp[l]<={!f2_take[l],6'(l)}" not in source:raise ValueError('stable lane key changed')
    for level in range(1,22):
        if f'begin:g_sort_{level}' not in source:raise ValueError('stable compaction stage changed')
        stages.append(dict(family='stable_compaction',stage=level,source='f3_tp/id' if level==1 else f'sort_record_{level-1}',
            destination=f'sort_record_{level}' if level<21 else 'f4_c',register_receiver_bits=64*39 if level<21 else 64*32,
            comparator_key_bits=7,source_record_bits=39,source_receiver_record_fanout=2,
            edge_rule='unconditional posedge; sort_valid aligns21levels and take_total_20',
            final_invalid_zero_mask=level==21,loaded_timing=None))
    if 'if (st == S_DRAIN && !fpipe && stn == 0 && !out_valid)' not in source:raise ValueError('source drain predicate changed')
    return stages

def build():
    pins=json.loads((BASE/'source_pins.json').read_text())
    for p,h in pins.items():
        if sha((ROOT/p).read_bytes())!=h:raise ValueError('source pin changed '+p)
    origins=load('origins.json')
    for name,e in origins.items():
        b=(BASE/'inputs'/name).read_bytes()
        if sha(b)!=e['sha256'] or len(b)!=e['bytes']:raise ValueError('archive changed '+name)
    prior=load('bd872_model.json');relocations=[]
    for shard,wanted in [(0,102),(1,66)]:
        cuts=prior['shards'][str(shard)]['raw_only_first_hop_cut_witnesses']
        if len(cuts)!=wanted:raise ValueError('cut count changed')
        branches={(x['net'],x['destination']):x for x in load(f'shard{shard}_branches.json.gz')}
        failures={(x['net'],x['destination']):x for x in load(f'shard{shard}_deficits.json.gz')}
        for x in cuts:
            key=(x['net'],x['destination']);branch=branches[key];fail=failures[key]
            if branch['proposed_relay_BUF']<1:raise ValueError('no existing relay to relocate')
            budget=branch['first_driver_total_wire_budget_fF']/2/branch['source_fanout']
            if budget!=x['first_branch_metal_budget_fF'] or x['optimistic_C_to_any_point_in_raw_rectangle_fF']<=budget:raise ValueError('not a necessary outside-raw first-hop cut')
            relocations.append(dict(shard=shard,net=x['net'],source=x['source'],destination=x['destination'],
                source_Y_literal_rect_DBU=fail['source_Y_literal_rect_DBU'],
                first_relay_ordinal=0,existing_branch_relay_count=branch['proposed_relay_BUF'],
                existing_relay_site_assignment=None,needed_new_site=None,
                added_graph_cells=0,source_fanout=branch['source_fanout'],
                first_branch_metal_budget_fF=budget,
                first_driver_contact_stub_budget_fF=branch['first_driver_reserved_contact_stub_C_fF'],
                first_driver_pin_load_SS_FF_fF=branch['first_driver_worst_pin_load_fF'],
                source_declared_first_branch_reach_um=branch['first_branch_reach_um'],
                optimistic_C_to_any_raw_fF=x['optimistic_C_to_any_point_in_raw_rectangle_fF'],
                M1_to_M8_M9_access_route_or_PG_site_proven=False))
    if prior['source_relay_and_pad_count']!=68614:raise ValueError('existing graph count changed')
    stages=pipeline((ROOT/CORE).read_text())
    return dict(schema='DS_SELECTOR_CAUSAL_SOURCE_TIMING_AND_FIXED_GRAPH_RELOCATION_V1',
        verdict='REVIEWABLE_REQUIREMENT_DELTA_NO_TIMING_OR_BUILD_ADMISSION',
        geometry='N4 NMAX2048 LDW4 P64 PF64 DIG8 CB14',
        selected_cut='bd87257f22e78dec2947a07b5ddc361031b310f2',
        unchanged_graph=dict(existing_relay_pad_BUF=68614,added_BUF=0,removed_BUF=0,
                             core_clock_BUF=70406,transport_clock_BUF=48007,timeout4096_adopted=False),
        relocation_count=168,relocation_by_shard=[102,66],
        moved_existing_cell_body_um2=168*0.10206,
        outside_raw_50pct_space_for_moved_bodies_screen_mm2=168*0.10206*2/1e6,
        additional_body_area_um2=0,actual_owner_space_or_total_reticle_delta_mm2=None,
        relocation_requirements=relocations,selector_source_stages=stages,
        retained_source_cones=[
            dict(path='ld_data/ld_id/ld_word/ld_rank/wpr -> kmem/imem',memory_bits=524288,
                 bytes_per_load_edge=256,cone='original rank-stride address, okey, write decode and FF hold mux',
                 source_state_already_in698354=True,loaded_SSFF=None),
            dict(path='kmem row -> h0_k -> h1_hot',bytes_per_hist_read_edge=256,
                 cone='original RF read mux, key shift/prefix match and256-bin decode',loaded_SSFF=None),
            dict(path='kmem/imem -> f0 -> f1 -> six equal-prefix stages',bytes_per_filter_read_edge=512,
                 cone='original RF score/ID read, strict key compare and global-ID arithmetic',loaded_SSFF=None),
            dict(path='f4_c/f4_n -> stg/stn -> out_data/outw_left',bytes_per_result_edge=256,
                 cone='retained variable append, mask, shift and counted output drain',loaded_SSFF=None),
            dict(path='core done/output ->99return edges -> preedge tk_oidx address formation ->28formedwrite edges -> actual VM write/owner release',
                 cone='unchanged formed-address/data/we/done packet; original busy/sticky fault release contract',
                 sink_VM_ready_required=1,actual_visibility_deadline=None,loaded_SSFF=None)],
        largest_pick_stage_raw_control_receiver_bits=max(x.get('source_control_FF_or_holdmux_receiver_bits',0) for x in stages),
        timing_contract=dict(period_ps=833,SS_setup_uncertainty_ps=60,FF_hold_uncertainty_ps=25,matched_skew_budget_ps=25,
                             loaded_clock_to_QN_INV_wire_logic_setup=None,FF_earliest_path_and_hold=None,
                             decoded_control_fanout_tree_actual_pin_load=None,reset_recovery_removal=None,
                             source_control_receiver_count_is_not_clock_pin_load=True,
                             via_contact_OBS_and_PG_extracted_RC=None),
        drain_contract='All existing fpipe tokens, stn and out_valid drain before core retire; actual formed-write done travels same28-edge packet, no invented ACK/credit.',
        accepted_delivery_or_consumer_deadline=None,
        current_job=None,frontend_sim_STA_PR_launched=False,SSFF=False,physical_admitted=False,
        full_token_credit=False,hardware_source_modified=False,source_pins=pins,source_origins=origins,
        owner_actions=dict(Arch_Maxwell='Assign existing168firstrelays near literal upper parents outside raw, redistribute all68614againstsource+sink; price common site/PG ownership and loadedSSFF without graph count change.',
                           Epicurus='Use this source receiver/control ledger for full mapped-cut gate; primitive PASS and distinct fullcomponent GO still required, actual captures not inferred from fixture.',
                           Nash_Hubble='Causal typed-forward/feedback and returned-credit/home-visible/drain contract; no same-edge credit reuse, no4096timeout.'))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if a.out.exists():raise ValueError('fresh timing join output required')
    a.out.write_text(json.dumps(build(),sort_keys=True,indent=2)+'\n')
