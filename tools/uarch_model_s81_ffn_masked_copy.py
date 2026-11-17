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
            physical_XRT_replica_count_pending=True),
        mux_demux_fanout=dict(new_mask_bits_per_leaf=8,
            new_mask_output_sinks=40,mask_config_fanout_upper=8,
            existing_output_mask_registers_reused=True,
            mapped_enable_mux_and_buffer_inventory_pending=True),
        routing=dict(external_track_delta=0, internal_mask_nets_per_XRT=64,
            internal_channel_capacity_and_fanout_repair_pending=True),
        area=dict(DFF_body_proxy_um2=.2916,
            metadata_FF_floor_um2=metadata_ff*.2916,
            mapped_comb_CTS_hold_repair_pending=True,
            actual_floorplan_slot_fit_qualified=False),
        latency=dict(down_phases_before=35,down_phases_after=35,
            source_pair_fragments=4984,full_fragments=3976,partial_fragments=1008,
            max_full_pairs_per_bulk_packet=4,bulk_packets_unqualified_old_estimate=2632,
            route_estimate_rejected=True,
            rejected_step_counts=dict(local_copy=133,local_masked_copy=1008,
                vertical_pair=1316,wide_tier=2198),
            extra_mask_pipeline_cycles_proposed=0,
            composed_single_user_cycles=None,
            note='old directV estimate rejected: actual bound sliceV exists onlycol0; bulk4pairs also needs8scratchrows, not2. Solve actual wide-col0-V-wide routes and finite scratch beforeRTL'),
        qualification='MODEL ONLY; scratch leases, finite port/calendar composition, full107/53 CAP-XR-VP exactness/miter/mutants, sustained throughput and context TT/FF remain required')
