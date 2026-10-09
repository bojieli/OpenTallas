"""Native controller adapter sizing; physical maps are explicit prerequisites."""
def model(*, engine_ports=(), stage_handoffs=121, seed_route_cycles=None,
          available_tracks=None, slot_area_um2=None):
    ports = tuple(engine_ports)
    if len(set(ports)) != len(ports) or any(p not in (0,1,2,3,4,5,6,8,9,10) for p in ports):
        raise ValueError('explicit real external engines only; hop7 is internal, spare11 unowned')
    if stage_handoffs < 0 or (seed_route_cycles is not None and seed_route_cycles < 0):
        raise ValueError('nonnegative composed route latency required')
    bits = len(ports)*1984 + 2052 + 56
    # Reuse the existing553-bit reliable lane. No additional PHY/ECC credit.
    # Proximal seed capture contributes40data+one explicit metadata header.
    tracks = dict(engine_command=len(ports)*85, engine_done=len(ports)*9,
                  ctrl_lane_tx=513, ctrl_lane_rx=513, reliable_lane_each=553,
                  hc_named_command=38, hc_named_done_identity=38)
    ready = bool(ports) and seed_route_cycles is not None and available_tracks is not None and slot_area_um2 is not None
    return dict(schema='opentallas.uarch.s81-control-transport.v1',
                status='MODEL_PRICED_NOT_ADOPTED' if ready else 'MISSING_PHYSICAL_MAP_OR_CAPACITY',
                enabled_default=False, macs_per_cycle=0, compute_intensity=0,
                clocks_ghz=dict(stream=1.2, serial=.9),
                engine_ports=list(ports), engine_replicas=len(ports),
                storage_bits=dict(engine_adapters=len(ports)*1984,
                                  control_lane=2052, hc_command_bridge=56, total=bits),
                vm_bytes_per_cycle=dict(write_slot0=64, read_slot1=64),
                vm_slots='0/1 must be explicitly reserved or share with finite owner arbitration; NP8 is not additional capacity',
                bits_per_cycle=tracks, routing_tracks_required=tracks,
                available_tracks=available_tracks, slot_area_um2=slot_area_um2,
                area='Measure56controlbits+2052lanequeuebits+1984bits perrealengine; do not inherit0.15mm2 controller-only estimate',
                replicas_mux_fanout='Each real engine has its own finite queue/CDC/ownership; one selected reserved reliable lane pertruepeer',
                latency_cycles=dict(engine_cmd_async_measured=8, engine_done_async_measured=7,
                                    stage_previous_budget_per_direction=12,
                                    controller_lane_per_direction=1,
                                    stage_handoff_delta=2*stage_handoffs,
                                    hc_command_completion=1, hc_three_capture_done_delta=3,
                                    seed_formatter_per_packet=1, seed_splitter_per_packet=1,
                                    seed_route_cycles=seed_route_cycles),
                seed=dict(message_type=5, proximal_sources=12, head_rank_joins=4,
                          payload_bytes=30720, header_bytes=768,
                          flits_per_capture=41, flits_per_rank=123,
                          formatter_width=513, metadata_header_bits_used=214,
                          route='Actual L37/38/39 stage_join source/dest/TP rank mapping required; never infer physicalstage=layer'),
                exact_status='HC command and control-lane component gates passed; seed formatter/splitter not yet built',
                physical_status='No SS/FF contextual qualification credit')


def vm_read_share_model(*, replicas=12, hop_credit=32, native_latency=10,
                        other_slot_owners=None):
    """Share existing native read1, never add NP8 ports or assume others free."""
    if replicas < 1 or hop_credit != 32 or native_latency < 1:
        raise ValueError('actual hop OUT_DEPTH32 and positive native latency required')
    return dict(schema='opentallas.uarch.s81-vm-read-share.v1',
                status='PREBUILD_SIZED_PHYSICAL_SLOT_OWNERS_PENDING',
                enabled_default=False, replicas=replicas, macs_per_cycle=0,
                storage_bits_per_replica=dict(hop_rows_protected=32*28,
                    hc_row_protected=28, response_owners_protected=64*2,
                    counter_pointer_control_upper_bound=128, total=1180),
                memory_bytes_per_cycle=dict(native_read1=64, native_write0_existing=64),
                boundary_bits_per_cycle=dict(native_read_row=15, native_response=513,
                    hc_request=16, hc_response=513, hop_request=15, hop_response=513),
                replicas_mux_fanout='One2client address mux; actual owner FIFO demux returns;12proximal source replicas subject to selected placement.',
                routing_tracks_required=1085, available_tracks=None,
                area_slot_fit='1180mutable protected/control bits perreplica; first synthesis/route and actual corridor fit required',
                outstanding=dict(hop=32, hc=1, total=33, response_owner_capacity=64),
                native_port_contract='One read issue/cycle on EXISTING read1; write0 unchanged. Others2..7 unowned here. NativeVM bank queue overflow remains actual schedule fault.',
                latency_cycles=dict(request_enqueue=1, native_return_observed=native_latency,
                    hc_pending_wait_max_existing_hop=1, hop_queue_max_under_adversarial_requests=32,
                    hc_single_capture_reads=320, hc_single_capture_read_floor=320*(native_latency+2)),
                token_contribution='Component cycles compose with real mean-source schedule;12sources overlap only if actual Hrestore leases and placement allow it.',
                reset_contract='Common reset/quiescence with VM; stale response afterflush faults. No independent reset epoch safety inferred.',
                other_slot_owners=other_slot_owners,
                adoption='Native response order and actual slot1 owner reservation must be qualified; not a full-token or SS/FF claim')


def runtime_pc_lease_model(*, source_stop_roundtrip_cycles=None, native_service_cycles=None):
    return dict(schema='opentallas.uarch.s81-runtime-pc-lease.v1',
                status='COMPONENT_SIZED_PRODUCER_AND_SERVICE_BINDING_PENDING',
                enabled_default=False, pcs=64, credits_per_pc=8, macs_per_cycle=0,
                storage_bits=dict(protected_debt=64*8, protected_held=64*2, fault=64, total=704),
                bytes_per_cycle=dict(request_per_pc=341/8, read_payload_per_pc=32),
                boundary_bits_per_cycle=dict(actual_request_accept=64, owned_completion=64,
                    quiescent_ack=64, decode_held=64, lease_want_claim_release=192,
                    issue_enable_available_held=192),
                routing_tracks_required=640, available_tracks=None,
                replicas_mux_fanout='64independent protected4bit counters and lease bits; no global PCmux/data movement added',
                area_slot_fit='704mutablecontrolbits; native PCproducer placement and first physical timing pending',
                latency_cycles=dict(grant_revoke=0, claim_state=1, release_state=1,
                    source_stop_roundtrip=source_stop_roundtrip_cycles,
                    native_owned_transaction_service=native_service_cycles),
                token_contribution='Engram lease wait <= source stop roundtrip +8*nativeservice under bounded PCschedule; exact measured service and producerack needed before rate adoption',
                availability='want && debt0 && explicit sourcequiescent && !decodeheld && !sameedge acceptance; never derive from local mux occupancy alone',
                reset='Common producer/controller reset with drain or explicit discard epoch; independently resetting debt is not safe',
                adoption=False)
