"""Required re-index parent source cuts, shared by the unified model; prebuild."""
import hashlib,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def model():
    name='ot_sram_1r1w_512x128_m4_r2c2'
    path=ROOT/'physical/asap7_memory_macros'/name
    m=json.loads((path/(name+'.json')).read_text())
    npc,slots,entries,lbw=32,8,2048,14
    banks=slots*entries//2//512
    ffa=.37908
    counter_saved=32*128*2-4*128*3
    response_saved=32*128-8*32*(7+1+2+1)
    extra=dict(request_FIFO=32*(50+4),response_check=8*32*2,
               decoded_FIFO=8*254,list_capture=banks*70+4*70+70+70+12+2*14*6+8*12*2,
               pending_and_metadata_checks=3*128,local_half_copies=2*2*128)
    net_ff=sum(extra.values())-counter_saved-response_saved-256
    return dict(status='PREBUILD_DEFAULT_OFF',default_enabled=False,shape=dict(NPC=npc,WB=128,DF=8,LSW=3,lists=slots,entries_per_list=entries,local_block_bits=lbw),
        MACs_per_cycle=0,rounding_and_reduction_changes=0,
        list_memory=dict(macro=name,macros_per_stack=banks,macro_json_sha256=hashlib.sha256((path/(name+'.json')).read_bytes()).hexdigest(),logical_bits=slots*entries*lbw,physical_bits=banks*512*128,
            code='SECDED35 per payload14+full logical entry address14; two independently masked64-bit fields per128-bit macro word',
            write_entries_per_cycle=1,write_logical_bytes_per_cycle=1.75,write_physical_bytes_per_cycle=8,read_entries_per_cycle=2,read_logical_bytes_per_cycle=3.5,read_physical_bytes_per_cycle=16,
            ports_per_macro=dict(read=1,write=1),corner_timing=m['timing'],macro_area_um2=banks*m['area']['macro_area_um2'],
            finite_validity='dual-rail prefix count per list; sequential writer, active-slot overwrite forbidden; full logical address seal checked on reads',
            latency_cycles=6,SS_clkQ_ps=m['timing']['ss']['clk_to_q_ps'],FF_clkQ_ps=m['timing']['ff']['clk_to_q_ps'],
            read_capture='real macro output -> local70-bit capture -> four-way partial select -> final select -> syndrome register -> corrected/address-checked payload register; no IO falsepaths'),
        source_cuts=dict(counters_per_slot=4,counter_bits_including_check=3,code_channel_counter_index='(pseudo_channel XOR slot_fold)[1:0], only for admitted pending code channels',
            response_local_groups=8,response_fanout_bound=16,request_FIFO_entries_per_PC=1,drain_reserved_entries=4,half_die_copy_stages=1,dispatch_inflight_pairs=3,decoded_FIFO_entries=16,
            counter_FF_removed=counter_saved,response_FF_removed=response_saved,redundant_write_enable_FF_removed=256,added_FF=extra,net_FF_delta=net_ff,
            protection='SRAM SECDED; counter check bits; pending/metadata checks; full tag/beat identity; finite occupancy and reservation checks, no invented clears or credits'),
        latency=dict(list_extra_cycles=5,request_extra_cycles=1,dispatch_extra_cycles=1,drain_extra_cycles=1,
            fixed_added_cycles_upper=8,worst_pairs_per_stack=1024,dispatch_FIFO_room_policy='six free slots for three in-flight pairs',
            throughput_cycles_must_be_measured=True,token_reindex_layers=4,token_fixed_added_ns_upper=4*8*833.333/1000,
            composed_current_token_us=604.3,composed_fixed_delta_us=4*8*833.333/1e6,measured=False),
        area=dict(control_cell_cap_um2=37452.2,retained_KC8_cells_um2=37615.4,estimated_FF_delta_um2=net_ff*ffa,
            unmeasured_mapping_logic_CTS_delta_um2=None,control_cap_unchanged=True,
            list_macro_reservation_um2=banks*m['area']['macro_area_um2'],
            parent_component_outline_um=[max(310.164,4*(m['area']['macro_width_um']+8)),310.164+4*(m['area']['macro_height_um']+8)],
            parent_component_reservation_basis='control retains93630.5um2 core and37452.2um2 cell cap; sixteen aligned list macros in adjacent4x4 region, not a control density rescue',
            enclosing_die_fit=False,die_gather_reservation_mm2=1.38823),
        boundaries=dict(list_write_bits=1+3+11+14,list_read_bits=1+13+28,HBM_request_bits=npc*(1+28+4+16),HBM_response_control_bits=npc*(1+16+4),drain_metadata_bits=71,
            control_copies=8,list_macro_output_bits=16*70,local_fourway_mux_bits=4*70,MAC_to_communication_intensity=0),
        routing=dict(macro_channel_pitch_um=8,gross_tracks_per_channel_per_direction=math.floor(8/.048),tracks_after_half_clock_PG_reserve=math.floor(8/.048/2),
            local_data_tracks_needed=70,macro_array_rows=4,macro_array_columns=4,control_fixed_slot_um2=93630.5,actual_route_required=True),
        replicas=dict(stacks_per_rank=4,ranks=4,list_macros_per_stack=banks,HBM_PC_queues_per_stack=npc),
        clock=dict(period_ps=833.333,SS_setup_uncertainty_ps=60,FF_hold_uncertainty_ps=25,waivers=False),
        gates=dict(exact=False,SSFF=False,route=False,adopted=False))
if __name__=='__main__':print(json.dumps(model(),indent=2))
