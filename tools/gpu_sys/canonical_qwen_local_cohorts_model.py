"""Prospective incremental cohort0/3 admission and receipt inventory.

These monitors add no SRAM/CDC/service replicas; they retain actual accepted
execution roots, not persistent RF version lifetimes. Upstream whole byte RPC
roots remain live across all of their physical sector transactions. Cold POR
only; no warm-reset/debt clearing. Compose with connections plus STATE tap,
without replacing or duplicating Popper RF or Sagan payload/reverse costs.
"""
def model():
    stage=64*(55+1)+64+20+2+1
    metadata=1*(64+1)+64+20+2+1
    return dict(stage_root_credits=64,metadata_RPC_root_credits=1,
                stage_owner_bits=55,metadata_root_identity_bits=64,
                stage_raw_bits=stage,metadata_raw_bits=metadata,
                added_raw_bits=stage+metadata,
                raw_FF_area_proxy_mm2=(stage+metadata)*.2916/.5/1e6,
                protected_bits=None,matched_old_storage_inclusion=None,
                protected_area_mm2=None,area_and_slot_fit=None,
                new_SRAM_bytes=0,new_CDC_bits=0,new_service_replicas=0,
                root_ports=dict(stage_accept_bits=64*56,stage_retire_bits=64*56,
                                metadata_accept_bits=65,metadata_retire_bits=65),
                query_bits_per_cohort=84,response_bits_per_cohort=85,
                equality_comparators=dict(stage_count=64,stage_width=55,
                                          metadata_count=1,metadata_width=64),
                quiesce_fanout=dict(stage=64,metadata=1),
                quiet_stage_reduction_inputs=64+64+64+1+1,
                quiet_metadata_reduction_inputs=1+1+1+1+1+1,
                admitted_children_blocked=False,new_roots_blocked=True,
                query_accept_to_response_min_edges=2,
                prospective_streaming_clock_GHz=1.2,
                source_root_retirement_bounds=None,
                whole_token_upper_edges=None,routed_tracks=None,
                reset_policy='cold POR only; local reset retains roots and held receipt',
                physical_qualified=False,rate_adopted=False)
