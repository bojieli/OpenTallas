"""Prospective connection inventory; reuse all existing shared/W2/controller costs.

There is one global KV stage request and one native contender per physical SM.
The router has no SRAM, payload FIFO, new service replica or clock crossing.
Metadata observation retains one ACTUALLY accepted protected sector write until
its visible/reverse tuple and downstream event both complete. Gross storage
is reported separately; existing bridge inclusion is unknown, not added twice.
"""
def model():
    router = dict(service_replicas=64, ranks=2, SM_per_rank=32,
                  payload_bits_per_port=512, address_bits=10,
                  arbitration='per-service alternating KV/native at accept',
                  retained_owner_bits=64, service_live_bits=64, preference_bits=64,
                  KV_live_bits=1, KV_destination_bits=6, fault_bits=1,
                  raw_bits=200, added_SRAM_bytes=0, added_CDC_bits=0,
                  maximum_competing_services_before_KV=1,
                  arbitration_requires_actual_service_completion=True,
                  request_mux_inputs_per_service=2, response_mux_inputs=64,
                  response_mux_width_bits=512, response_fanout=1,
                  service_write_data_replica_connections=64,
                  protected_bits=None, routed_tracks=None, mux_area_mm2=None,
                  extra_registered_edges=0, physical_timing_qualified=False)
    # pending/visible/reverse/event/fault, original owner46, physical address34,
    # decoded event kind3 identity64 key20 sourcePC11. No write data storage:
    # decode is captured from the actual accepted old/new sector data at ingress.
    observer = dict(outstanding=1, event_slots=1, raw_bits=4+46+34+3+64+64+20+11,
                    source_state_bytes_per_rank=37504,
                    actual_RMW_old_capture_required=True,
                    protected_bits=None, physical_timing_qualified=False,
                    event_payload_bits=3+64+64+20+11,
                    write_capture_bits=46+34+34+1+256+256,
                    ACK_compare_bits=46+34,
                    bitmap_decode_fanout=256, record_decode_width_bits=128,
                    ingress_to_event_min_edges=3, CDC_included=False)
    for component in (router, observer):
        component['raw_FF_area_proxy_mm2']=component['raw_bits']*.2916/.5/1e6
    return dict(router=router, observer=observer, prospective_clock_GHz=1.2,
                source_costs_replaced='none; connections only',
                selected_W2_service='source-prospective II19; own measured scope retained',
                reused_controller_raw_bits=14390, composed_whole_token_bound=None,
                metadata_join_raw_bits=1, qualified_rate=False)


def bound(service_edges, reverse_edges, event_wait_edges):
    if any(type(x) is not int or x<=0 for x in (service_edges, reverse_edges, event_wait_edges)):
        raise ValueError('positive source-bounded endpoint and downstream service required')
    # A native request can win at most once before a continuously offered KV
    # request. Every admitted service still needs a bounded held-return consumer.
    return dict(shared_offer_to_capture_upper_edges=2*service_edges+2,
                metadata_accept_to_consumed_upper_edges=service_edges+reverse_edges+event_wait_edges+3,
                scope='prospective edges in source streaming domain; no ns/rate adoption')


def reader_services_model():
    # One source-serialized native parent55 and one actual eight-cohort query.
    operator_bits = 64 + 20 + 55 + 1 + 1 + 1 + 1
    drain_bits = 64 + 20 + 8 + 8 + 1
    return dict(operator_credits=1, release_credits=1, native_owner_bits=55,
                raw_bits=operator_bits + drain_bits + 1, added_SRAM_bytes=0,
                new_request_CDC_bits=8*(64+20), new_reverse_CDC_bits=8*(64+20+1),
                CDC_implementation='existing endpoint clocks/FIFOs; replacement not credited',
                endpoint_count=8, endpoint_request_bits=84, endpoint_response_bits=85,
                actual_done_and_reverse_required=True,
                done_to_consumer_offer_min_edges=1, release_response_min_edges=2,
                prospective_clock_GHz=1.2, physical_qualified=False,
                external_native_service_edges=None, external_cohort_bounds=None,
                whole_token_bound=None, matched_existing_storage_inclusion=None)


def connected_model():
    m=model(); r=reader_services_model()
    added=m['router']['raw_bits']+m['observer']['raw_bits']+1+r['raw_bits']+11
    return dict(added_raw_control_bits=added, reused_controller_raw_bits=14390,
                total_raw_bits=14390+added, added_SRAM_bytes=0,
                added_raw_FF_area_proxy_mm2=added*.2916/.5/1e6,
                source_ranks=2, SM_per_rank=32, shared_service_count=64,
                sector_operations_per_commit=528,
                actual_native_parent_owner_bits=55,
                request_CDC_bits_per_query=8*84, return_CDC_bits_per_query=8*85,
                substituted_existing_storage_credit=0,
                physical_qualified=False, whole_token_cycles=None)
