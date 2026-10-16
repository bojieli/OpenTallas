"""Reset-defined service boundary state; mandatory no-X gate, no rate credit."""
def model():
    return dict(scope='held SM/PS line boundary reset definition', MACs_per_cycle=0,
        memory_bytes_per_cycle=0, communication_intensity='same boundary as current service',
        boundary_bits=dict(SM=1099,PS=1102), replicas=dict(stacks=4,SM_ports_per_stack=8,PS_ports_per_stack=8),
        extra_register_bits=0, reset_defined_bits_per_SM_slot4=2196,
        reset_defined_bits_per_PS_group=1098,
        mux_demux_fanout='no data mux change; existing segment-local reset must physically buffer added resettable boundary FF loads',
        routing_tracks_added=0, channel_capacity='unchanged data boundary; reset tree routing unqualified until context closure',
        area='resettable-cell replacement delta must be measured; no new data state', floorplan_slot_fit='requires reclosure of changed segment source',
        latency=dict(normal_added_cycles=0,reset_settle_cycles=64,token_added_cycles=0),
        adoption=False, physical_admitted=False,
        exactness='idle payloads defined zero after reset; every valid payload and transaction order unchanged')
