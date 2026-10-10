"""Size DMA lane credits from composed registered transport, before RTL."""
import math

def model(depth=64, data_hops=32, credit_hops=32):
    if depth < 4 or depth & (depth-1): raise ValueError('power-of-two lane depth >=4 required')
    rtt=data_hops+credit_hops+4 # pin capture, front FIFO pop and registered credit
    return dict(scope='DMA front finite lane buffers; streaming1.2GHz', MACs_per_cycle=0,
        compute_intensity='format conversion unchanged', source_bytes_per_cycle=1024,
        destination_bytes_per_cycle=1024, port_bytes_per_cycle=dict(lane=32,VM=1024),
        boundary_bits=dict(data=4*8*270,credit=32,VM=32*280),
        replicas=dict(stacks=4,lanes_per_stack=8,buffer_entries=depth),
        memory_bits=32*depth*274, added_memory_bits=32*(depth-4)*274,
        added_pointer_bits=32*(3*(depth.bit_length()-1)-6),
        composed_credit_round_trip_cycles=rtt,
        credit_window_rate_upper_bound=min(1,depth/rtt), required_depth_at_90pct=math.ceil(.9*rtt),
        fifo_mux_inputs=depth, lane_demux_count=32,
        latency=dict(data_hops=data_hops,credit_hops=credit_hops,front_internal_edges=4,token_added_cycles='transport cycles compose with actual DMA critical path'),
        tracks_added=0, channel_capacity='same boundary wires, svc owner independently sizes corridor',
        area='measure mapped storage or SRAM master; no inferred slot fit',floorplan_fit=False,
        physical_admitted=False, adoption=False,
        source_note='32 service-internal worst-case credit RTT from actual8500um strips plus provisional32cycles loader leg; exact loader distance must replace bound')
