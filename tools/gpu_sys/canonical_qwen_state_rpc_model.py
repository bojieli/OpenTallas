"""Prospective actual source byte-RPC -> tap -> cohort3 caller join.

Canonical r17 source calls write8/tag counter, write1/bitmap and write16/record;
32B payload port covers these without serial software completion authority.
Reads stream all 37504B extent; larger writes are explicitly refused, never
truncated. Reuse actual W2/map/observer/controller/cohort costs once.
"""
def model():
    raw=2+64+1+1+34+16+35+34+256+46+34+1
    return dict(raw_bits=raw,raw_FF_area_proxy_mm2=raw*.2916/.5/1e6,
                source_RPC_credits=1,mapped_sector_credits=1,
                added_SRAM_bytes=0,added_W2_replicas=0,added_CDC_bits=0,
                byte_payload_bits=256,canonical_write_bytes=[8,1,16],
                implemented_write_port_bytes=32,state_bytes_per_rank=37504,
                root_admission_bits=65,root_retirement_bits=65,
                mapped_sector_bits=1+34+34+46+1,sector_reply_compare_bits=64+1+46+34,
                maximum_sectors_per_RPC=1172,
                source_payload_byte_mux_inputs=32,source_payload_byte_mux_output_bits=256,
                source_mask_decode_outputs=32,replicas=1,
                root_to_first_sector_offer_min_edges=1,
                final_sector_accept_to_parent_reply_min_edges=1,
                prospective_streaming_clock_GHz=1.2,
                OLD_NEW_service_cost='reuse STATE tap; serial OLD then NEW for writes',
                partial_OLD_recharged=False,matched_existing_inclusion=None,
                protected_bits=None,ports_mux_area_mm2=None,routed_tracks=None,
                slot_fit=None,source_service_upper_edges=None,
                whole_token_cycles=None,physical_qualified=False)
