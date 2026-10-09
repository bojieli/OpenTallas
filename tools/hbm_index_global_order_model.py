"""Full TP96 canonical gather mechanism, sized before its RTL implementation.

The native selectors publish ascending literal IDs within each rank. Rank-major
concatenation is not globally ascending under the round-robin owner mapping.
"""
import math

def model():
    ranks=96
    tuples_per_flit=15
    quarter_blocks=342
    quarter_flits=math.ceil(quarter_blocks/tuples_per_flit)
    per_rank_flits=4*quarter_flits
    total_flits=ranks*per_rank_flits
    heads=2*ranks*34
    positions=2*ranks*17
    valid=2*ranks
    tournament_nodes=sum((48,24,12,6,3,2,1))
    tournament_bits=2*tournament_nodes*(17+7+1)
    control=2*(73+7+17+34+16)
    ff=heads+positions+valid+tournament_bits+control
    return dict(schema='opentallas.hbm.index_global_order.v1', default_enabled=False,
        source_order='96 ascending native block-ID lists merged by minimum literal ID',
        correctness='unchanged BF16 values; signed zero preserved; duplicate IDs/NaN fault',
        ranks=ranks, MACs_per_cycle=0, arithmetic='95 unsigned17bit ID comparisons in seven registered levels',
        compute_intensity=0, memory_bytes_per_cycle=dict(head_response=34/8,
            source_publication_write=64, source_publication_read=64),
        bits_per_boundary=dict(TU_packet=545,TU_header=33,TU_payload=512,
            tuple=34, owner=73, tuple_request=7+17+73, tuple_response=34+7+17+73+1),
        format=dict(tuples_per_flit=15, low_tuple_in_low_bits=True,
            payload511='quarter-last',payload510='reserved zero',
            idx16='quarter2 then beat14',tuple34='blockID17 then BF16score16 then valid1'),
        full_1m_shape=dict(quarter_key_blocks=342,flits_per_quarter=quarter_flits,
            flits_per_rank=per_rank_flits,flits_all96=total_flits,
            TU_bytes_all96=total_flits*545/8,payload_capacity_bytes=total_flits*64,
            publication_data_macros_128x256=2*math.ceil(total_flits/128),
            maximum_valid_global_blocks=131072),
        publication_store='actual protected TU consumer publication store required; '
            'above macro count is payload only, protection and source ledger cost additional',
        register_bits=ff, FF_area_floor_um2=ff*.2916,
        replicas=1, mux_cost='96 protected head seats, rank-selected refill; no arithmetic score mux',
        fanout_cost='held owner73 and source-rank bounds; tournament registered by level',
        routing_tracks_required=2*(34+7+17+73), channel_capacity_tracks=None,
        slot_fit=False, area_and_clock_context='selected R25I endpoint placement must supply actual budgets',
        latency_cycles=dict(head_initialization='96*(actual read round trip plus acceptance)',
            select_levels=7, tuple_emit_capture=1,
            per_tuple_minimum=8, refill_round_trip='actual TU publication SRAM/relay delay additive',
            full_valid_1m_comparison_minimum=8*131072),
        single_user_composition='query and score -> native candidate publication -> real '
            'allgather and positive write ACK -> seven-level global-ID merge -> '
            'native global top2048 selector -> real keep-mask publication; no free overlap',
        clocks=dict(period_ps=833.333,setup_uncertainty_ps=60,hold_uncertainty_ps=25),
        exact_gate=False, physical_closed=False, token_rate_credit=0)
