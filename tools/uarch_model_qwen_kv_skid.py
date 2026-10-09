"""Q4: finite merge-output queues with credits before row-bus launch."""
import math

def model(depth=8, local_columns=32, dff_um2=0.2916):
    if depth < 2 or depth & (depth-1):
        raise ValueError('depth must be a power of two >= 2')
    word_bits=512+512+7
    # Sender is beside the row arbiter. Forward and reverse row chains each
    # visit at most 32 tile stations; decoder8, merge2, dequeue2 and credit2.
    forward=local_columns+8+2
    reverse=local_columns+2
    rtt=forward+2+reverse
    control_bits=3*math.ceil(math.log2(depth))+16
    ff=depth*word_bits+2*(word_bits+1)+control_bits
    cell_area=ff*dff_um2+1600
    slot=[160.,64.]
    return dict(schema='opentallas.qwen-kv-merge-skid.v1',default_off=True,
        adopted=False,physical_closed=False,model_precedes_rtl=True,
        replicas=1536,macs_per_cycle=0,compute_intensity_macs_per_byte=0,
        memory_ports=[dict(name='merge_output_queue',read_bytes_per_cycle=word_bits/8,
            write_bytes_per_cycle=word_bits/8,depth=depth,bits=depth*word_bits)],
        boundary_bits_per_cycle=dict(landing=word_bits+1,token=word_bits+1,
            output=word_bits+1,return_credit=1),
        routing=dict(required_tracks_per_face=word_bits+4,
            face_capacity_tracks=int(slot[0]/.048),pin_layers=['M4','M6'],
            credit_return_per_row_bits=32,return_is_registered=True),
        replicas_cost=dict(storage_bits=ff*1536,read_mux=f'{depth}:1 x {word_bits}',
            write_demux=f'{depth} local enables',token_fanout=1,
            row_credit_fanout='one independently reserved counter per tile'),
        slot_um=slot,cell_area_bound_um2=cell_area,
        cell_area_basis='DFFHQNx1 0.2916um2: unified DFF_UM2, results/floorplan/qwen_o4_unit_areas.json',
        slot_fit_at_55pct=cell_area<=math.prod(slot)*.55,
        reserved_area_mm2_per_die=math.prod(slot)*1536/1e6,
        flow=dict(depth=depth,initial_sender_credits=depth,
            forward_max_edges=forward,reverse_max_edges=reverse,
            roundtrip_max_edges=rtt,full_rate_depth_required=rtt,
            guaranteed_continuous_rate_words_per_cycle=min(1,depth/rtt),
            overflow_rule='receiver faults and suppresses releases; sender reserves before row launch',
            token_preempts_dequeue=True),
        latency=dict(added_landing_edges_min=2,
            composed_gross_added_cycles_per_token=36*2,
            token_write_edges=2,queue_stall_cost='trace measurement, no overlap credit'),
        constraints=['real row relay count must replace worst-case32 before adoption',
            'retire every credit on actual dequeue, never PHY arrival',
            'existing merged disjoint-lane golden arithmetic unchanged',
            'slot is separate added tile-side master; full die fit is an outstanding obligation'])
