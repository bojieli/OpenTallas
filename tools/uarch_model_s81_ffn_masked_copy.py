"""Price the ownership-preserving S81 final-FFN candidate before RTL.

The committed actual819 packet proves address/fragment ownership only.  This
model deliberately leaves calendars, SRAM leases and physical closure open.
"""
from __future__ import annotations


def model():
    ranks, experts, leaves, mask_bits = 4, 7, 5, 8
    metadata_ff = mask_bits * (1 + 1 + 1 + leaves)
    return dict(
        schema='opentallas.s81.final-ffn-masked-copy-uarch.v1',
        default_off=True, adopted=False, rtl_written=False,
        actual_plan_sha256='819037bbe371ad99945d4a9b3f11a536060280b59bd1c4ac48167d9cf77b140d',
        source_counts=[107,107,53,53,107,107,53,53,53,53,107,107,53,53,107,107],
        ROM_weight_ownership_changed=False, numerical_row_tags_changed=False,
        MACs_per_cycle=0, compute_intensity_MACs_per_byte=0,
        exact_symbolic_words=ranks*experts*1280,
        memory=dict(word_bytes=4, row_bytes=16, pair_bytes=32,
            capture_stride_words_before=64,capture_stride_words_after=72,
            capture_rows_per_leaf_before=112,capture_rows_per_leaf_after=126,
            capture_extra_bytes_per_leaf=14*16, capture_rows=[128,254],
            assembled_rows=[320,432], combined_rows=[448,464],
            scratch_rows_candidate=[304,306],scratch_bytes_per_used_leaf=32,
            scratch_used_leaf_slots_all_ranks=75,scratch_bytes_all_used_leaves=2400,
            new_memory_macros=0,new_memory_ports=0,
            pair_read_bytes_per_issue=32,masked_write_bytes_per_row_upper=16,
            port_issue_interval_and_lifetime_qualified=False),
        communication=dict(external_bus_width_delta=0,new_external_tracks=0,
            local_mask_semantic_bits=8,
            configuration_body_fields=[45,52],
            existing_control_bits_all_eight_optimized_live=True,
            current_XRT_source_sha256='d2a543e4fd9f25b13ccece85058652ecb9ccae366353738b6da20346e9c030a9',
            selected_transport='RING_LAND2',
            mechanism='partial old RD/V into destination scratch, then local masked copy; full fragments retain existing path'),
        replicas=dict(ranks=ranks,experts=experts,leaves_per_XRT=leaves,
            mask_config_FF=8,mask_local_packet_twin_FF=8,
            mask_read_classifier_FF=8,mask_leaf_output_FF=40,
            added_metadata_FF_per_XRT=metadata_ff,added_data_FF=0,
            physical_XRT_replicas=16, XRT1_replicas=14, XRT3_replicas=2,
            added_metadata_FF_all_XRT=16*metadata_ff),
        mux_demux_fanout=dict(new_mask_bits_per_leaf=8,
            new_mask_output_sinks=40,mask_classifier_fanout_per_bit=5,
            existing_output_mask_registers_reused=True,
            mapped_enable_mux_and_buffer_inventory_pending=True),
        routing=dict(external_track_delta=0, internal_mask_nets_per_XRT=64,
            internal_channel_capacity_and_fanout_repair_pending=True),
        area=dict(DFF_body_proxy_um2=.2916,
            metadata_FF_floor_um2=metadata_ff*.2916,
            metadata_FF_floor_all_XRT_um2=16*metadata_ff*.2916,
            mapped_comb_CTS_hold_repair_pending=True,
            actual_floorplan_slot_fit_qualified=False),
        latency=dict(down_phases_before=35,down_phases_after=35,
            source_pair_fragments=4984,full_fragments=3976,partial_fragments=1008,
            max_full_pairs_per_bulk_packet=4,bulk_packets_unqualified_old_estimate=2632,
            route_estimate_rejected=True,
            rejected_step_counts=dict(local_copy=133,local_masked_copy=1008,
                vertical_pair=1316,wide_tier=2198),
            actual_bound_bridge_columns=[0,2,5,7],
            one_pair_legal_route_legs=dict(local_copy=329,local_masked_copy=1008,vertical_pair=2492,wide_tier=4949),
            legal_route_control_issue_words=17556,
            separate_TP4_dies_transport_floor_cycles=2436,
            separate_TP4_dies_combine_budget_deficit_cycles=1609,
            rank_contexts_shared_die_transport_floor_cycles=9324,
            rank_contexts_shared_die_combine_budget_deficit_cycles=8497,
            extra_mask_pipeline_cycles_proposed=0,
            composed_single_user_cycles=None,
            note='old directV estimate rejected: actual full boundDie Vbridges exist onlycolumns0,2,5,7; bulk4pairs needs8scratchrows, not2. Correct onepair route floor2436 alreadyexceeds827combine; ages/leases/POST remainadditional'),
        qualification='MODEL ONLY; scratch leases, finite port/calendar composition, full107/53 CAP-XR-VP exactness/miter/mutants, sustained throughput and context TT/FF remain required')


def source_near_combine_model():
    """Keep native seven-expert order and VS13 n8, return one combined beat."""
    result = model()
    result['schema'] = 'opentallas.s81.final-ffn-source-near-combine-uarch.v1'
    result['communication']['mechanism'] = (
        'assemble complete64-word beats at20 distinct source-near leaf slots per TPdie; '
        'same VS13 n8/expertstride16; return combined64-word beat to canonical POST owner')
    result['memory'].update(canonical_receive_rows=[464,480],
        canonical_receive_bytes_per_used_leaf=256,
        canonical_receive_used_leaves_per_TPdie=20,
        canonical_receive_bytes_per_TPdie=5120,
        old_inplace_receive_alias_cases_detected=18,
        POST_a1=464, original_combined_source_rows=[448,464])
    result['latency'] = dict(
        down_phases_before=35,down_phases_after=35,
        canonical_same_bulk_packets=7602,
        relocated_same_bulk_packets=4752,
        canonical_same_bulk_CTL_words=15204,
        relocated_same_bulk_CTL_words=9504,
        canonical_separate_TPdie_issue_floor=2128,
        relocated_separate_TPdie_issue_floor=1232,
        saved_CTL_words=5700,
        saved_issue_floor_cycles_per_TPdie=896,
        canonical_shared_rank_issue_floor=8092,
        relocated_shared_rank_issue_floor=4864,
        nominal_unqualified_combine_cycles=827,
        minimum_extension_over_nominal_cycles=405,
        exact_seven_expert_add_order_unchanged=True,
        native_VS13_n=8, native_expert_stride_rows=16,
        legal_bulk_policy='only fullmask singleleg local/wide<=4; V/multileg/partial onepair',
        current_missing_composition=[
            'actualCAPready and VPXlastreader rowleases',
            'selectedXRT/maskedcopy latency',
            'finite dependency/control/link calendar',
            'existingVS13~75/POST~63 plus peerflow/hostreload'],
        composed_single_user_cycles=None,
        note='827 is an incomplete nominal budget, not an adoption ceiling. Resourcefloor requires at least405 additionalcycles; wholepath extension remains unpriced. No hidden overlap duringdown without actualleases.')
    result['qualification'] = ('MODEL ONLY candidate with priced resource improvement; '
        'numeric ownership retained, noRTL/image or physical claim. Full schedule/leases, '
        'CAP-XR-VP fullshape exactness/miter/mutants, contextTT/FF and throughput remain OPEN.')
    return result
