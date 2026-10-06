"""Required re-index parent source cuts, shared by the unified model; prebuild."""
import hashlib,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def native_quarter_join_model():
    """Wiring to the existing W11 scorer; no new engine or calendar stage."""
    source=ROOT/'rtl/hdc/v41x/ot_hdc_v41x_idx_lat.sv'
    return dict(default_enabled=False,source=str(source.relative_to(ROOT)),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        shape=dict(NS=4,NK=4,NB=4,IH=32,IW=20,MD=64,FPL=7,FML=5,QL=5),
        existing_MACs_per_cycle=16*32*128,new_MACs_per_cycle=0,
        key_bytes_per_cycle=16*544//8,query_bytes_per_load=(512+32+16)//8,
        key_boundary_bits=1+4+16+16+16+320+8704,key_ready_return_bits=1,
        score_boundary_bits=1+4+16+16+256+320+1,score_ready_return_bits=1,
        first_capture_replicas_per_key_bit=4,query_capture_replicas=16,
        mapped_merge_and_connected_fanout_required=True,
        incremental_FF=0,incremental_muxes=0,incremental_demuxes=0,
        existing_engine_latency_cycles=100,existing_query_settle_cycles=3,
        added_adapter_cycles=0,added_token_latency_us=0,
        composition='Existing streaming scorer term in dsrom_1m_allmeasured retained; do not add 100 cycles again to the 739 gather term.',
        arithmetic='Existing native array unchanged; key order, every full global ID and golden mdrop order retained.',
        capture_clock='Literal parent clk on native rkey/rql and credit/metadata state; no QX gated-clock alias.',
        area='Existing modeled NS16/NK4 W11 scorer, one NS4 quarter; no scorer placed in R9 control/list fence and no borrowed HBM slot fit.',
        routing='8704 key bits plus full metadata must use actual connected source/receiver channels; required added tracks unknown until enclosing floorplan binding.',
        R9_scope='R9 control/list/request/drain-header only; this join does not expand that pinned physical proof.',
        exact_qualified=False,mapping_qualified=False,clock_load_qualified=False,parent_qualified=False,
        build_rule='Port join only; no new scorer synthesis/P&R until its actual enclosing slot/channel and clock/calendar binding exists.')
def model():
    name='ot_sram_1r1w_512x128_m4_r2c2'
    path=ROOT/'physical/asap7_memory_macros'/name
    m=json.loads((path/(name+'.json')).read_text())
    npc,slots,entries,lbw=32,8,2048,14
    banks=slots*entries//2//512
    ffa=.37908
    counter_saved=32*128*2-4*128*5
    response_saved=32*128-8*32*(7+1+2+1+1)
    extra=dict(request_FIFO=33*(61+4),response_check=8*32*2,
               drain_metadata=4*79-4*(16+28)+3+4,decoded_FIFO=0,list_header_and_result_checks=14+14+28+1,list_capture=banks*70+4*70+70+70+12+2*14*6+8*12*2,
               pending_and_metadata_checks=3*128,local_half_copies=2*2*(95+40+7+128+1))
    net_ff=sum(extra.values())-counter_saved-response_saved-256
    measured_path=ROOT/'results/rtl/dsrom_reindex_parent_20261005/gather_r8_PASS/gather.json'
    measured=json.loads(measured_path.read_text()) if measured_path.exists() else None
    source_matched=bool(measured and measured['status']=='pass' and measured.get('backpressure',{}).get('pass_') and
        all(hashlib.sha256((ROOT/f).read_bytes()).hexdigest()==h for f,h in measured['source_sha256'].items() if f.endswith(('.sv','.v'))))
    actual_cycles=measured['worst_rank']['cycles'] if source_matched else None
    return dict(status='PREBUILD_DEFAULT_OFF',default_enabled=False,shape=dict(NPC=npc,WB=128,DF=8,LSW=3,lists=slots,entries_per_list=entries,local_block_bits=lbw),
        MACs_per_cycle=0,rounding_and_reduction_changes=0,native_quarter_port_join=native_quarter_join_model(),
        list_memory=dict(macro=name,macros_per_stack=banks,macro_json_sha256=hashlib.sha256((path/(name+'.json')).read_bytes()).hexdigest(),logical_bits=slots*entries*lbw,physical_bits=banks*512*128,
            code='SECDED35 per payload14+full logical entry address14; two independently masked64-bit fields per128-bit macro word',
            write_entries_per_cycle=1,write_logical_bytes_per_cycle=1.75,write_physical_bytes_per_cycle=8,read_entries_per_cycle=2,read_logical_bytes_per_cycle=3.5,read_physical_bytes_per_cycle=16,
            ports_per_macro=dict(read=1,write=1),corner_timing=m['timing'],macro_area_um2=banks*m['area']['macro_area_um2'],
            finite_validity='dual-rail prefix count per list; sequential writer, active-slot overwrite forbidden; full logical address seal checked on reads',
            latency_cycles=6,SS_clkQ_ps=m['timing']['ss']['clk_to_q_ps'],FF_clkQ_ps=m['timing']['ff']['clk_to_q_ps'],
            read_capture='real macro output -> local70-bit capture -> four-way partial select -> final select -> syndrome register -> corrected/address-checked payload register; no IO falsepaths'),
        source_cuts=dict(counters_per_slot=4,counter_bits_including_check=5,code_channel_counter_index='(pseudo_channel XOR slot_fold)[1:0], only for admitted pending code channels',
            response_local_groups=8,response_fanout_bound=16,request_FIFO_entries_per_PC=1,drain_reserved_entries=4,drain_metadata_code="SECDED79 per71-bit finite output header; pointers/count checked; actual key SRAM data path unchanged",half_die_copy_stages=1,half_copy_bits_per_lane=271,half_copy_lanes=4,dispatch_inflight_pairs=3,decoded_FIFO_entries=8,
            response_completion='four distinct beat bits per actual code channel; row-hit scheduler may reorder beats; protected mask resets only after all four accepted',counter_FF_removed=counter_saved,response_FF_removed=response_saved,redundant_write_enable_FF_removed=256,added_FF=extra,net_FF_delta=net_ff,
            protection='SRAM SECDED; counter check bits; pending/metadata checks; full tag/beat identity; finite occupancy and reservation checks, no invented clears or credits'),
        latency=dict(list_extra_cycles=5,request_extra_cycles=1,dispatch_extra_cycles=1,drain_extra_cycles=1,
            fixed_added_cycles_upper=8,decoded_occupancy_cut="retain8 real pairs, counting all reads in flight; pipe+head+FIFO share that conserved allocation; no drop or credit",decoded_peak_pairs_per_cycle_upper=1,decoded_sustained_pairs_per_cycle_lower_bound=8/13,worst_pairs_per_stack=1024,decoded_stall_cycles_per_stack_upper=640,decoded_stall_token_us_upper=4*640*833.333/1e6,dispatch_FIFO_room_policy='six free slots for three in-flight pairs',
            throughput_cycles_must_be_measured=not source_matched,token_reindex_layers=4,token_fixed_added_ns_upper=4*8*833.333/1000,
            historical_token_basis_us=604.3,composed_fixed_delta_us=4*8*833.333/1e6,
            measured=source_matched,measured_gather_cycles=actual_cycles,measured_record_sha256=hashlib.sha256(measured_path.read_bytes()).hexdigest() if source_matched else None,
            KC8_reference_cycles=738,composer_production_reference_cycles=757,
            measured_delta_cycles_vs_KC8=actual_cycles-738 if source_matched else None,
            measured_component_token_delta_us_vs_KC8=4*(actual_cycles-738)/1200 if source_matched else None,
            conditional_production_composer='tools/dsrom_reindex_parent_compose.py; replace gather read term only, retain scorer/streaming/CDC costs',
            stage_latency_not_assumed_equal_component_delta=True),
        area=dict(control_cell_cap_um2=37452.2,retained_KC8_cells_um2=37615.4,estimated_FF_delta_um2=net_ff*ffa,
            unmeasured_mapping_logic_CTS_delta_um2=None,control_cap_unchanged=True,
            list_macro_reservation_um2=banks*m['area']['macro_area_um2'],
            parent_component_outline_um=[max(310.164,4*(m['area']['macro_width_um']+8)),310.164+4*(m['area']['macro_height_um']+8)],
            control_fence_um=[2.052,2.160,308.124,308.070],macro_frontend_fence_um=[2.052,312.324,726.324,458.910],parent_component_reservation_basis='control retains93630.5um2 core and37452.2um2 cell cap; sixteen aligned list macros in adjacent4x4 region, not a control density rescue',
            enclosing_die_fit=False,die_gather_reservation_mm2=1.38823),
        boundaries=dict(list_write_bits=1+3+11+14,list_read_bits=1+13+28,HBM_request_bits=npc*(1+28+4+16),HBM_response_control_bits=npc*(1+16+4),drain_metadata_bits=71,
            control_copies=8,list_macro_output_bits=16*70,local_fourway_mux_bits=4*70,MAC_to_communication_intensity=0),
        routing=dict(macro_channel_pitch_um=8,gross_tracks_per_channel_per_direction=math.floor(8/.048),tracks_after_half_clock_PG_reserve=math.floor(8/.048/2),
            local_data_tracks_needed=70,macro_array_rows=4,macro_array_columns=4,control_fixed_slot_um2=93630.5,actual_route_required=True),
        replicas=dict(stacks_per_rank=4,ranks=4,list_macros_per_stack=banks,HBM_PC_queues_per_stack=npc),
        clock=dict(period_ps=833.333,SS_setup_uncertainty_ps=60,FF_hold_uncertainty_ps=25,waivers=False),
        gates=dict(exact=False,SSFF=False,route=False,adopted=False))
if __name__=='__main__':print(json.dumps(model(),indent=2))
