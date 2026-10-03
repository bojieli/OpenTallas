#!/usr/bin/env python3
"""W4 source-compatible model input. Frozen F0 does not admit RTL."""
import json,hashlib,pathlib
from Euclid_W4_RFACK_identity_contract import model,canonical,RECORD
F0=RECORD/'frozen-F0-r2'
def contract():
    old=model() # retain source pins and actual leaf write/hold/reset checks
    pins=json.loads((F0/'git-object-pins.json').read_text())
    docs={}
    for p,pin in pins.items():
        b=(F0/p).read_bytes()
        if hashlib.sha256(b).hexdigest()!=pin['sha256']:raise ValueError('frozen F0 '+p)
        docs[p]=json.loads(b)
    w=docs['W2-interface-contract-r1.json'];c=docs['contract-r4-continuous.json']
    e=w['W2_model_extension'];v=w['source_variants'];rows=w['exact_table']
    if (e['original_client_tag_bits'],e['generation_bits'],e['backend_identity_total_bits'])!=(32,4,39):raise ValueError('source compatible width')
    if not e['generation_not_taken_from_original_tag']:raise ValueError('original tag overwrite')
    if v['Nash_selected_model']['NC']!=5 or v['full_HBM_wrapper']['NC']!=6:raise ValueError('client inventory')
    if rows['row_minimum_raw_bits']!=38:raise ValueError('W2 minimum')
    # Conservative source-compatible RF identity until a reversible narrow adapter exists:
    # actual originaltag32 + client3 (source PTAG35), explicit gen4, physicalPC7, RF wr_addr9.
    bits=35+4+7+9
    return dict(schema='EUCLID_W4_FROZEN_F0_SOURCE_COMPATIBLE_MODEL_R2',hardware_admitted=False,
      original_sources_unchanged=True,new_RTL=False,F0_git_pins=pins,actual_leaf_contract=old,
      source_identity=dict(CTAGW=32,PTAGW=35,generation_bits=4,generation_is_explicit=True,
        original_tag_overwritten=False,physical_PC_bits=7,RF_slot_bits=9,
        SM_namespace='actual static RF endpoint32SMs; accepted requester SM/home map must be proved',
        local_handle='physicalPC7 + source PTAG35 + generation4 + actual wr_addr9',
        minimum_capture_if_PC_client_scoped_in_real_context=45,
        capture_with_explicit_PC7_and_client_context=52,
        selected_conservative_capture_including_client3=55,
        narrower_width_requires_real_context_ownership=True,
        optional_compact_adapter_blocks_baseline=False,
        compact_parent_tag16='optional only after reversible source adapter; PC and coalescer layouts unequal'),
      proposed_ports=dict(wr_owner_tag_bits=35,wr_generation_bits=4,wr_physical_PC_bits=7,
        ACK_owner_tag_bits=35,ACK_generation_bits=4,ACK_physical_PC_bits=7,ACK_RF_slot_bits=9,
        RF_slot_capture='actual existing wr_addr9, no synthetic receipt field',
        identity_producer='source accepted C0/KV requester identity carried through backend echo and return assembler before actual RF write_go'),
      leaf_incremental_inventory=dict(SMs=32,captured_identity_bits_per_SM=bits,captured_identity_bits_per_die=bits*32,
        live_slots_per_SM=1,register_write_ports=1,register_read_ports=1,
        input_metadata_bits_per_accepted_write=35+4+7,output_metadata_bits_per_accepted_ACK=bits,
        RF_data_write_bits_per_copy=4096,RF_data_read_bits_per_copy=4096,RF_copy_count=2,
        additional_SRAM_ports=0,additional_SRAM_macros=0,additional_MACs=0,
        captured_FF_clock_loads=bits*32,captured_FF_async_reset_loads=bits*32,
        local_capture_enable_loads=bits,metadata_output_distinct_bit_drivers=bits,
        actual_common_ACK_valid_reused=True,independent_mirror_ACK_channels=0,
        wrapper_internal_SIMD_owner_retention_bits_per_SM=bits,wrapper_identity_mux_bits_per_SM=bits,
        wrapper_retention_is_separate_not_free=True,
        mutable_control_protection_bits=None,distribution_buffers=None,wire_lengths=None),
      W2_boundary=dict(NC5_rows_per_PC=80,NC6_rows_per_PC=96,row_min_bits=38,
        NC5_raw_bits_per_PC=3040,NC6_raw_bits_per_PC=3648,
        KV_client_index5_occupied=True,production_C0_KV_caller_map=None,
        backend_generation_echo_installed=False,W2_retirement_not_RF_visibility=True),
      allcopy_reuse=dict(generation_modulus=16,local_ACK_accept_not_lease_release=True,
        reset_local_clear_not_source_quiescence=True,source_allcopies_predicate=None,
        includes=c['revised_wrap_and_reset']['quiescence_includes'],
        actual_quiescence_transition=None,actual_quiescence_wait_cycles=None,
        monotonic_ParentLeases_gt_not_continuous_semantics=True,no_arbitrary_token_or_generation_cap=True,
        release='matched child/parent reverse, CDC receipt and every copied message drained before reuse'),
      wholeprogram=dict(Qwen_PC_count=1737,DS_PC_count=2213,repeated_tokens=True,
        actual_accepted_transaction_count=None,actual_ACK_receipt_count=None,whole_stream_pass=False),
      model_admission=dict(model_owner='Popper',F0_owner='Russell',W4_owner='Euclid',
        composed_cycles=None,token_latency_s=None,area_um2=None,slot_fit=None,
        track_demand=None,track_capacity=None,clock_domain_pair=None,SS_setup=None,FF_hold=None,
        reset_and_quiescence_cost=None,whole_bridge_admitted=False),
      next_gates=['Popper composed real C0/KV caller map and finite ports/rate/clock/reset cost',
        'source all-copy quiescence transition with matched reverse CDC and continuous wrap',
        'model register/mux/protection/distribution wire/reset clock loads and selected area/corridor fit',
        'then defaultoff ACK_ID source successor with normalized original body byteidentity',
        'actual write-go source tag/gen capture; held commonACK; both copies; reset/stale/consumer/reverse gates'])
if __name__=='__main__':print(canonical(contract()),end='')
