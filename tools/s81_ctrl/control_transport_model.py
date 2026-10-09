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
