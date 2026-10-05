#!/usr/bin/env python3
"""Pre-RTL sizing for the source-matched finite Qwen VM admission adapter.
Default off. One full existing DS masked-visible bank4 service; no replicas.
Maxwell owns composition/adoption, this function supplies component terms.
"""
import json
from pathlib import Path


def model():
    reads=2048+3*64+16
    writes=96*16+16+64+1+16
    # One frozen logical-edge frame. Requests/raw responses stay immutable until
    # every physical write ACK. Source may not change any participant mid-frame.
    read_addr_bits=reads*25
    read_data_bits=reads*32
    write_bits=writes*57
    xvm_bits=2048*(32+1)
    output_read_bits=reads*32
    cache_bits=4096*32
    cache_coverage_bits=4096
    # DS opaque owner carries actual local epoch+seat; echo must match, never
    # synthesized ACK. r2 input TAG227 is the existing port width.
    owner_seats_bits=227*2
    frame_control_bits=32+12+11+12+6+1+1+1+1+1+15+2048+4
    bank_read_holding_bits=2048+15+1
    single_write_pack_bits=512+16+15+227
    coded_frame_bits=(reads+writes)*72
    frame_coding_delta=coded_frame_bits-(read_addr_bits+read_data_bits+write_bits)
    base_bits=frame_coding_delta+sum((read_addr_bits,read_data_bits,write_bits,xvm_bits,
                   output_read_bits,owner_seats_bits,frame_control_bits,
                   bank_read_holding_bits,single_write_pack_bits))
    cache_extra=cache_bits+cache_coverage_bits
    # Serialized slot address/data select, legal returned-word lane select.
    mux_bits=(reads-1)*(25+32)+(writes-1)*57+63*32+(4096-1)*32
    head_compare_bits=2048*24
    empty_reduce_cells=reads+writes-2
    parity_bits=2048*32
    macro_area=256*174.120*29.736
    return dict(schema='opentallas.qwen-hbm.finite-vm-adapter-prebuild.v1',
                default_enabled=False,adopted=False,RTL_ready_as_functional_candidate=False,
                status="implementation present; remote source check and connected minimum case pending",
                mutable_frame_protection_complete=False,
                provider='ot_qwen_checked_vm_bank over full16 masked R2,32 SRAM check macros',
                authoritative_model_commit='e72bb27c1',
                authoritative_placement_estimate_mm2=4.195354,required_envelope_mm2=4.8,
                authoritative_parent_containment=False,
                retained_words=177808,physical_bytes=2097152,macro_count=288,data_macro_count=256,check_macro_count=32,
                macro_body_um2=macro_area,read_seats=reads,write_seats=writes,
                frame_read_address_bits=read_addr_bits,frame_read_data_bits=read_data_bits,
                frame_write_bits=write_bits,encoded_snapshot_bits=coded_frame_bits,frame_coding_added_bits=frame_coding_delta,XVM1_holding_bits=xvm_bits,
                published_read_holding_bits=output_read_bits,bank_response_holding_bits=bank_read_holding_bits,
                opaque_owner_bits=owner_seats_bits,control_budget_bits=frame_control_bits,
                single_masked_write_pack_bits=single_write_pack_bits,
                head_cache_data_bits=cache_bits,head_coverage_bits=cache_coverage_bits,
                base_storage_bits=base_bits,head_extra_storage_bits=cache_extra,
                base_DFF_body_proxy_um2=base_bits*.2916,head_extra_DFF_body_proxy_um2=cache_extra*.2916,
                serialized_selection_mux_bits=mux_bits,serialized_selection_mux_proxy_um2=mux_bits*.2,
                head_parity_mux_bits=parity_bits,head_parity_mux_proxy_um2=parity_bits*.2,
                head_address_compare_bits=head_compare_bits,head_compare_proxy_um2=head_compare_bits*.2,
                empty_reduce_cells=empty_reduce_cells,empty_reduce_proxy_um2=empty_reduce_cells*.08748,
                model_proxy_basis='uarch_model DFF_UM2 .2916 and existing .2um2/2:1bit mux estimate; no physical closure',
                base_macro_FF_mux_body_proxy_um2=macro_area+base_bits*.2916+mux_bits*.2,
                head_macro_FF_mux_body_proxy_um2=macro_area+(base_bits+cache_extra)*.2916+(mux_bits+parity_bits+head_compare_bits)*.2+empty_reduce_cells*.08748,
                reservation_at_50pct_um2=2*(macro_area+(base_bits+cache_extra)*.2916+(mux_bits+parity_bits+head_compare_bits)*.2+empty_reduce_cells*.08748),
                read_face_bits=reads*32,read_face_address_enable_bits=reads*25,
                write_face_data_address_enable_bits=writes*57,
                global_port_expansion_bits=0,replicas=1,clock_gate_instances=1,
                bank_read_return_face_bits=2048,bank_write_face_bits=2048,
                maximum_head_parity_fanout=65536,
                source_read_wire_tracks_at_one_track_per_bit=reads*(32+25),
                source_write_wire_tracks_at_one_track_per_bit=writes*57,
                loaded_track_capacity=None,loaded_corridor_area_um2=None,clock_tree_um2=None,
                logic_other_than_priced_mux_area_um2=None,SRAM_mutable_state_protection_area_um2=None,
                floorplan_slot_fit=False,physical_build_allowed=False,functional_component_compile_allowed=True,
                core_clock_ps=833.333,SS_uncertainty_ps=60,FF_uncertainty_ps=25,
                read_result_after_accept_edges=9,write_macro_commit_after_accept_edges=12,
                write_ACK_after_accept_edges=28,read_issue_II=9,write_issue_II=28,
                calendar_basis='static registered controller accounting; not a measured result; priced target9/22 and actual prep9/28',
                serial_frame_calendar=dict(capture=1,read_slot_visits=reads,
                    read_window_miss_edges=11,write_slot_visits=writes,
                    masked_word_issue_ack_edges=30,admit=1,
                    formula='1+read_slot_visits+11*window_misses+write_slot_visits+30*masked_word_commands+1; skip/pack control additional where required',
                    all_participants_frozen=True,actual_native_edges_added=True,
                    fast_empty_or_cache_frame_shortcut=True,
                    empty_fast_path_extra_edges=0,source_checked_readonly_head_fast_path_extra_edges=0),
                head_fill=dict(issue_beats=64,issue_II=9,return_tail_edges=9,
                    issue_and_return_edges=576,minimum_issue_and_return_us=576/1200,
                    prerequisites='actual source-PC2 ownership and full4096 raw-scalar physical ACK coverage, no later writer',
                    source_copy_or_CPU_expected_activation=False,
                    cache_hit_per_native_ME_edge=2048,cache_hit_algorithm='fixed2*port+parity only with exact range/stride/owner checks',
                    extra_same_edge_ME_cache_latency_edges=0,cache_lease_ready_requires_current_frame_write_drain=True),
                weight_capture_binding='native_tick AND original me_clk_en gates existing selected weight/scale/tile/XVM capture; weight arrivals remain on original independent service clock',
                producer_visibility='freeze all native controllers/engines through current frame ACK; no source progress/chase/END consumer can advance across unpaid writes',
                headline_token_latency_us=None,headline_gain=None,
                rejection_if_unbound='No physical adoption, source-only ROM scope, no free multiplexers/clock/wire/protection or same-cycle SU reads')


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(model(),indent=2)+'\n')
