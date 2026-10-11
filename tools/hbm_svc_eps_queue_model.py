"""Separate pending stream descriptor from independent legacy command ingress."""
def model():
    return dict(scope='one EPS command consumer, per stack',MACs_per_cycle=0,
        bytes_per_memory_port_per_cycle=dict(ingress=127/8),boundary_bits=dict(e=129,stream_descriptor=62,legacy_command=40),
        replicas=4,pending_stream_slots=1,active_stream_slots=1,legacy_ingress_slots=4,
        added_register_bits_per_stack=128,added_register_bits_total=512,
        mux_demux=dict(stream_descriptor_mux_bits=127,mux_inputs=2,legacy_decode_unchanged=True),
        routing_tracks_added=0,channel_capacity='boundary widths unchanged; reset/descriptor local routing reclosure required',
        area='128 FF per EPS plus127-bit2:1descriptor select; mappeddelta pending',floorplan_slot_fit='existing EPS master needs context reclosure',
        latency=dict(current_stream_added_cycles=0,queued_stream_added_cycles=0,token_added_cycles=0),
        contract='at most one active and one queued stream; independent legacy commands retain existing per-kind producer windows; queued stream does not occupy legacy ingress while active stream drains',
        gate='one EPS reproduces W524 drop from4-entry HOL FIFO; pending-slot repair must dispatch both W516 andW524, queued descriptors exact; stream overlap mutant must fail',
        adoption=False,physical_admitted=False)
