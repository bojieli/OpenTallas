#!/usr/bin/env python3
"""One fixed full-selector placement/transport model; no RTL, job or STA credit."""
import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path
import uarch_topk_physical_g0_archive_replay as A
import uarch_topk_physical_g0_inputs as P

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'results/uarch/topk_finite_source_context_20261002'
MANIFEST_SHA='add9d7e799137d4c5b76183181c93eeca500435db0b58cb43fdf3f395f513fe6'

def inputs():
    raw=(BASE/'source_manifest.json').read_bytes()
    if A.digest(raw)!=MANIFEST_SHA:raise ValueError('current physical source manifest changed')
    records={};pins={}
    for e in json.loads(raw)['origins']:
        b=(BASE/e['archive_path']).read_bytes()
        if A.digest(b)!=e['sha256'] or len(b)!=e['bytes']:raise ValueError('current physical source bytes changed')
        records[e['path']]=b;pins[(e['commit'] or 'retained-installed')+':'+e['path']]=e
    return records,pins

def source_contract(records):
    dma=records['rtl/chip/ot_w15_coll_dma.sv'].decode();die=records['rtl/chip/ckvsel/ot_chip_v41x_die.sv'].decode();tile=records['rtl/chip/ckvsel/ot_chip_v41x_tile.sv'].decode()
    anchors={
      'dma':['assign o_ready = (GW == 4 && e_mode && !tk_r) ? tr_ready : 1\'b1;',
          'if (tk_ld && o_last) begin tk_sel <= 1; tk_go <= 1; end',
          'if (tk_ov) tk_oidx <= tk_oidx + CW\'(tk_nw);',
          'if (tk_done) begin busy <= 0; tk_r <= 0; tk_sel <= 0; end',
          'tk_wa[tj*WA +: WA] = dst_r + tk_oidx[WA-1:0] + WA\'(tj);'],
      'die':[".vm_ready4(1'b1)",'.TOPK(FULL_SHAPE)', 'parameter integer VM_AW   = FULL_SHAPE ? 19 : 16,', 'localparam integer VWA = VM_AW - 4;'],
      'tile':['if (xb_we4[b])','xb_wdata4[b*512 + 32*e +: 32]']}
    for kind,text in [('dma',dma),('die',die),('tile',tile)]:
        if any(x not in text for x in anchors[kind]):raise ValueError('native consumer contract anchor absent: '+kind)
    return {'VM_AW':19,'VWA':15,'source_contexts':1,'selector_output_ready_port':False,
      'topk_vm_ready4_consumed':False,'source_go':'tk_ld && o_last creates tk_go for following edge',
      'source_write':'tk_ov/tk_nw -> tk_oidx/address/enables -> tile VM perbank synchronous write',
      'source_release':'tk_done clears DMA busy and tk_r; must not precede all delayed writes',
      'retiming_data_alone_legal':False,'new_ACK_wire':False,'reset':'flush all transport valid/control and source busy ownership together; late old payload must not become a new command write'}

def sort_crossings():
    # Exactly one fixed8x8 mapping: column=lane>>3, row=lane&7.
    vertical=horizontal=0;records=[];k=2
    while k<=64:
        j=k//2
        while j:
            pairs=[(i,i^j) for i in range(64) if (i^j)>i]
            x=sum(2*39 for i,q in pairs if (i>>3<4)!=(q>>3<4))
            y=sum(2*39 for i,q in pairs if (i&7<4)!=(q&7<4))
            vertical+=x;horizontal+=y;records.append(dict(k=k,j=j,column_midcut_tracks=x,row_midcut_tracks=y))
            j//=2
        k*=2
    return {'mapping':'column=lane>>3, row=lane&7; one fixed8x8 lattice',
      'stages':records,'column_midcut_all_sort_levels_tracks':vertical,'row_midcut_all_sort_levels_tracks':horizontal,
      'stage_record_bits':39,'scope':'all21 simultaneous registered level nets counted, no stage-time wire alias; comparator-select/control/clock/prefix nets not free'}

def build(repo=ROOT):
    records,pins=inputs();native=source_contract(records)
    data,replay=A.replay(repo,mode='archive-only');old=json.loads(data)
    current=json.loads(records['results/uarch/dsrom_I66_terminal_destination_review_20261002/composed-r1/model.json'])
    box=current['selector']['single_full_slot_bbox_DBU'];height=box[3]-box[1]
    if box!=old['placement']['complete_bbox_DBU'] or current['selector']['state_bits']!=698354:raise ValueError('frozen fullselector changed')
    a=old['area']['cell_area_groups_um2'];ledger=old['register_ledger'];ff=0.2916;mux=0.30618
    retained_filter=sum(v for k,v in ledger['retained'].items() if k.startswith(('filter_','staging_','public_')))
    filter_ff=retained_filter+sum(ledger['additional_filter'].values())
    filter_area=filter_ff*ff+sum(ledger['additional_filter'].values())*mux
    filter_keys=[k for k in a if k.startswith('filter_')]+['retained_filter_compare_and_global_ID_add','retained_filter_equal_quota_subtract_and_hold','retained_staging_variable_word_append_and_shift','other_staging_and_output_masks','other_other_declared_register_hold_allowance']
    filter_area+=sum(a[k] for k in filter_keys)
    rf_keys=['retained_candidate_write_hold_muxes','retained_filter_RF_score_and_ID_read_mux','retained_hist_RF_score_read_mux','other_candidate_data_buffer_tree','other_candidate_word_address_decode','other_load_order_key_and_NaN_detection','other_load_variable_rank_stride_address','retained_explicit_fanout4_buffer_construction']
    rf_area=ledger['retained']['candidate_score_and_ID']*ff+sum(a[k] for k in rf_keys)
    rest=old['area']['full_cell_master_construction_um2']-rf_area-filter_area
    lef=next(b.decode() for path,b in records.items() if path.endswith('asap7sc7p5t_28_R_1x_220121a.lef'))
    if 'SIZE 0.054 BY 0.270 ;' not in lef:raise ValueError('retained PDK site changed')
    site_width=54
    rf_width=math.ceil(rf_area/0.5*1e6/height/site_width)*site_width
    right=box[2]-(box[0]+rf_width);filter_height=math.ceil(filter_area/0.5*1e6/right/2160)*2160
    regions={'shared_candidate_RF':[box[0],box[1],box[0]+rf_width,box[3]],
      'balanced_filter':[box[0]+rf_width,box[1],box[2],box[1]+filter_height],
      'hist_suffix_choice_control':[box[0]+rf_width,box[1]+filter_height,box[2],box[3]]}
    areas={'shared_candidate_RF':rf_area,'balanced_filter':filter_area,'hist_suffix_choice_control':rest}
    capacities={name:P.area(b)*1e6*0.5 for name,b in regions.items()}
    fit=all(capacities[k]>=areas[k] for k in regions)
    archive=A.SourceArchive(repo,mode='archive-only')
    gp='results/uarch/dsrom_l20_hierarchical_reservation_20261002/grid_inputs/DS_grid.json'
    grid=json.loads(archive.read('4b6708348f3938e0830c3549fbbecadbce18e798',gp))
    f=regions['balanced_filter'];cross=sort_crossings()
    hcap=P.track_count(grid,['M2','M4'],'Y',f[1],f[3]);vcap=P.track_count(grid,['M3','M5'],'X',f[0],f[2])
    max_partner_um=max((f[2]-f[0])/2000,(f[3]-f[1])/2000)
    wire=old['clock']['wire_context_screen'];hops=wire['endpoint_rectangle_conditional_minimum_segment_counts']
    # Existing source boundary already includes one receiver edge. Only N-1
    # intermediate registered beats are additional. Both result+done return
    # through DMA; a separate formed-address write path preserves sink mapping.
    launch_segments=hops['collective'];return_segments=hops['collective']
    c=old['placement']['collective_reserved_bbox_DBU'];v=old['placement']['VM_reserved_bbox_DBU']
    maximum_rectangle_L1_um=(max(c[2],v[2])-min(c[0],v[0])+max(c[3],v[3])-min(c[1],v[1]))/1000
    sink_segments=math.ceil(maximum_rectangle_L1_um/wire['maximum_hop_um_before_stage_logic'])
    in_width=sum(old['ports']['bit_inventory']['inputs'].values());out_width=sum(old['ports']['bit_inventory']['outputs'].values());write_width=4+4*native['VWA']+2048
    delays={'input':launch_segments-1,'selector_return':return_segments-1,'formed_VM_write':sink_segments-1,'retirement_delay':sink_segments-1}
    bits=in_width*delays['input']+out_width*delays['selector_return']+write_width*delays['formed_VM_write']+delays['retirement_delay']
    delta=delays['input']+delays['selector_return']+delays['formed_VM_write']
    return {'schema':'FIXED_FULL_SELECTOR_FINITE_SOURCE_CONTEXT_MODEL_V1','sourcepins':pins,'portable_baseline_replay':replay,
      'compiled':old['compiled'],'frozen_selector_state_bits':698354,'frozen_selector_slot_DBU':box,'frozen_selector_slot_mm2':P.area(box),
      'placement':{'one_candidate':True,'site_width_DBU':site_width,'retained_site_height_DBU':270,'regions':regions,'component_cell_area_um2':areas,'region_cell_capacity_um2_50pct':capacities,
         'component_area_sum_exact':math.isclose(sum(areas.values()),old['area']['full_cell_master_construction_um2'],rel_tol=1e-12),
         'all_regions_inside_fullslot':all(box[0]<=b[0]<b[2]<=box[2] and box[1]<=b[1]<b[3]<=box[3] for b in regions.values()),'component_capacity_pass':fit,
         'scope':'disjoint coarse construction reservations, not FF instance placement; RF->prefix contraction, pin positions and actualstageperregiondensity still unbound'},
      'internal_tracks':{'sort':cross,'column_midcut_capacity_M2M4':hcap,'row_midcut_capacity_M3M5':vcap,
         'largest_sort_partner_hop_um':max_partner_um,'nonlogic_wire_hop_budget_um':wire['maximum_hop_um_before_stage_logic'],
         'sort_midcut_data_only_pass':hcap['signal_tracks_after_50pct_reserve']>=cross['column_midcut_all_sort_levels_tracks'] and vcap['signal_tracks_after_50pct_reserve']>=cross['row_midcut_all_sort_levels_tracks'],
         'all_sort_select_prefix_clock_reset_vias_allocated':False},
      'native_contract':native,
      'transport_model':{'proposal_not_existing_RTL':True,'minimum_wireonly_launch_segments':launch_segments,'minimum_wireonly_return_segments':return_segments,
         'conditional_direct_rectangle_sink_segments':sink_segments,'sink_distance_scope':'maximum directManhattan separation between reservedCOLL/VM rectangle points, not actual obstacle-detoured pin route',
         'pipeline_width_bits':{'input':in_width,'selector_return':out_width,'formed_VM_write':write_width},'additional_delay_edges':delays,
         'additional_pipeline_bits':bits,'pipeline_FF_cell_area_um2':bits*ff,'pipeline_FF_only_reservation_mm2_50pct':bits*ff/0.5/1e6,
         'selector_core_bits_unchanged':True,'new_command_contexts':0,'credit':'reserve entire command beforeGO; no stallable selectoroutput port; downstream must absorb every outputgroup and releasebusy only after actualsinkdrain',
         'retime_done_data_and_fault_together':True,'hold_destination_and_index_through_drain':True,'reset_flush_required':True,
         'arithmetic_order_changes':False,'new_ACK_wire':False,'actual_transport_station_placement':None,'station_clock_hold_enable_and_via_cost':None,
         'additional_cycles_per_call_if_this_chain_admitted':delta,'ninecalls_additional_cycles':9*delta,'ninecalls_additional_ns_at_policyclock':9*delta/1.2,
         'total_service_plus_proposed_transport_increment_cycles':1278+9*delta,'no_current_token_latency_or_MTP_credit':True,
         'admitted':False,'wireonly_segment_lowerbound_not_contextclosure':True},
      'area_join':{'current_Maxwell_screen_mm2':current['area']['combined_noncontainment_policy_screen_mm2'],
         'selector_replacement_already_charged_once':True,'uncontained_corridor_increment_mm2':old['area']['new_escape_corridor_union_mm2'],
         'pipeline_FF_floor_outside_frozen_selector_mm2':bits*ff/0.5/1e6,'pipeline_FF_NOT_free_corridor_containment':True,
         'no_containment_credit_subtotal_screen_mm2':current['area']['combined_noncontainment_policy_screen_mm2']+old['area']['new_escape_corridor_union_mm2']+bits*ff/0.5/1e6,
         'not_complete_physical_area':'transport buffers/reset/clockhold/PG/vias and actualstation placement remain unpriced'},
      'external_tracks':old['tracks']['horizontal_escape'],'external_signal_demand':4210,
      'G0':{'RTL_admitted':False,'PR_admitted':False,'remaining':['actual perstage FF/pin placement including RF->prefix-to-sort path','all internalcontrol/prefix/reset/clock/via routes against tightchannels','source-aligned finite station placement and contextSSsetup/FFhold','Maxwell exact source endpoint/transport calendar acceptance']},
      'jobs_launched':0,'new_PVE2_PVE3_jobs':0,'optional_variant_sweep':False}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,default=ROOT);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if a.out.exists():raise ValueError('fresh model output required')
    model=build(a.repo)
    with a.out.open('x') as f:json.dump(model,f,indent=2,sort_keys=True);f.write('\n')
