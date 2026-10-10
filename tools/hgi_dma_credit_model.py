"""Size DMA lane credits from composed registered transport, before RTL."""
import math

def model(depth=256, data_hops=96, credit_hops=96, *, stack_local_tags=False, response_latency=0):
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
        tag_ownership=tag_model(stack_local_tags=stack_local_tags,response_latency=response_latency,data_hops=data_hops),
        measured_HBM_capacity=dict(sustained_bytes_per_cycle=3.8e12/1.2e9,nominal_bytes_per_cycle=4e12/1.2e9,
            current_lane_capacity_fraction_of_sustained=1024/(3.8e12/1.2e9),required_future_VM_bytes_per_cycle=3072,
            current_width_satisfies_90pct_HBM=False),
        physical_admitted=False, adoption=False,
        source_note='source-derived R25GPH13–26mm service/front leg35–69 hops eachway plus32cycles internal strip RTT;96perleg conservatively covers192cycle transport; final tileplacement rechecks bound')


def tag_model(*, stack_local_tags=False, response_latency=160, data_hops=96,
              source_run_sectors=256, vm_words=262144):
    """Four-bit tags are independent per stack; actual service confirms locality."""
    stacks=4
    tags=16*stacks if stack_local_tags else 16
    run_cycles=math.ceil(source_run_sectors/8)
    lifetime=response_latency+data_hops+run_cycles+2
    ideal_cycles=math.ceil(vm_words*4/1024)
    return dict(scope='front native tag ownership; no physical or token admission',
        default_stack_local_tags=0,stack_local_tags=stack_local_tags,
        stacks=stacks,tag_bits_on_service_interface=4,total_descriptor_slots=tags,
        guaranteed_slots_per_stack=16 if stack_local_tags else 4,
        descriptor_bits=18+9+1,descriptor_register_bits=tags*28,
        added_descriptor_register_bits=(tags-16)*28,
        request_mux='16-slot free pick at selected stack; 4 stack banks',
        ingress_demux='lane/8 identifies stack, tag selects descriptor within stack',
        MACs_per_cycle=0,source_bytes_per_cycle=1024,destination_bytes_per_cycle=1024,
        tracks_added=0,source_run_sectors=source_run_sectors,
        source_run_cycles=run_cycles,descriptor_lifetime_cycles=lifetime,
        tags_required_per_stack_at_full_rate=math.ceil(lifetime/run_cycles),
        vm_words=vm_words,VM_sector_address_bits=15,vm_bytes=vm_words*4,
        latency=dict(response_latency=response_latency,data_hops=data_hops,
            full_load_ideal_data_cycles=ideal_cycles,
            full_load_lower_bound_cycles=ideal_cycles+response_latency+data_hops+4,
            full_load_rate_upper_bound=ideal_cycles/(ideal_cycles+response_latency+data_hops+4)),
        floorplan_fit=False,physical_admitted=False,adoption=False,
        measured_service_contract='each stack has independent request/data engine; same4bit tag concurrently across stacks is valid')
