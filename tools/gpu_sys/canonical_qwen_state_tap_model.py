"""Additive prospective inventory for the actual state-sector visibility tap.

Compose with canonical_qwen_kv_connections_model.connected_model(); this is
connection/control overhead, not another W2, SRAM, payload or arithmetic cost.
Cold POR only. Local reset/repair blocks traffic and retains all accepted debt.
"""
def model():
    # state4 + route(rank1,source34,physical34,owner46) + commandwrite1,
    # original commandidentity64, source PATCH256/mask32, actual OLD256, fault1.
    raw = 4+1+34+34+46+1+64+256+256+32+1
    return dict(raw_control_and_capture_bits=raw,
                raw_FF_area_proxy_mm2=raw*.2916/.5/1e6,
                protected_bits=None, protected_area_mm2=None,
                prospective_streaming_clock_GHz=1.2, endpoint_credits=1,
                new_SRAM_bytes=0, new_W2_replicas=0, new_CDC_bits=0,
                actual_OLD_capture_bits=256, retained_source_PATCH_bits=256, retained_byte_mask_bits=32,
                merge_muxes=256, merge_mask_fanout_per_bit=8,
                source_route_bits=115, original_owner_bits=46,
                selected_NC=6, sector_bits=256, address_bits=34,
                original_tag_bits=32, generation_bits=4,
                request_mux_added=False, physical_ports_reused=True,
                request_comparison_bits=34+32+4+7+1+3+256,
                return_comparison_bits=32+4+7+1,
                reverse_comparison_bits=46+34+1+1,
                data_read_capture_FF_fanout=1, OLD_to_observer_bits=256,
                NEW_to_observer_bits=256, observer_route_bits=115,
                grant_retirement_not_W2_credit_retirement=True,
                command_to_OLD_offer_min_edges=1,
                OLD_capture_to_reverse_offer_min_edges=1,
                OLD_reverse_to_NEW_offer_min_edges=1,
                NEW_accept_to_write_capture_min_edges=1,
                write_capture_to_reverse_offer_min_edges=1,
                reverse_to_command_reply_min_edges=1,
                command_reply_waits_for_metadata_event_consumption=False,
                metadata_event_debt_remains_in_original_observer=True,
                positive_service_bounds_required=True,
                selected_W2_prospective_II=19,
                physical_timing_qualified=False, routed_tracks=None,
                mux_area_mm2=None, floorplan_slot_fit=None,
                source_service_upper_edges=None, whole_token_cycles=None,
                matched_existing_storage_inclusion=None, rate_adopted=False)


def bound(old_service, old_reverse, write_service, write_reverse, reply_wait):
    values=(old_service,old_reverse,write_service,write_reverse,reply_wait)
    if any(type(v) is not int or v<=0 for v in values):
        raise ValueError('positive bounded actual source services required')
    return sum(values)+6  # serial actual dependencies; no ideal overlap


def composed_model():
    from tools.gpu_sys.canonical_qwen_kv_connections_model import connected_model
    parent=connected_model()
    tap=model()
    return dict(existing_connected_ports=parent,state_visibility_tap=tap,
                added_raw_bits=tap['raw_control_and_capture_bits'],
                total_raw_bits=parent['total_raw_bits']+tap['raw_control_and_capture_bits'],
                state_write_sector_operations=dict(OLD_read=1,NEW_write=1),
                extra_OLD_reads_for_full_sector_write=1,
                partial_write_OLD_reads_recharged=0,
                existing_W2_cost_replaced=False,
                existing_observer_cost_recharged=False,
                whole_token_upper_edges=None,hardware_qualified=False)
