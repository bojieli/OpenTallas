"""Size an opt-in CP/native INDEX lease actor before RTL; provider remains OPEN."""

def model():
    # Full HGI record, externally accepted owner, explicit grant extent; no payload alias.
    record, frame, grant = 1819, 73, 4*(15 + 16 + 9)
    flags, state = 5, 3+2
    ff = 2 * (record + frame + grant + flags + state) + 1
    return dict(schema='opentallas.hgi.index_cp_lease.v1', default_enabled=False,
        targets=['DeepSeek-V4.1 HBM'], replicas_per_die=1, MACs_per_cycle=0,
        compute_intensity=0, memory_bytes_per_cycle=0,
        communication_intensity='one held HGI record and framed control receipts per INDEX',
        added_FF_bits=ff, estimated_FF_area_floor_um2=ff*.2916,
        added_SRAM=0, slot_um=[420,420], mapped_area_um2=None, floorplan_slot_fit=False,
        mux_demux='one held record seat; one source/native sink; no payload replicas',
        fanout='full record complementary compare; five full73 receipt comparisons; no free owner alias',
        routing_tracks_required=1819+73+6+60+36+2,
        routing_tracks_capacity=None, loaded_delay_ps=None,
        command=dict(record_bits=1819, retained_frame_bits=73,
            layer='record imm_b32 checked<40; held in actual record',
            position='record20 equals full73[72:53]', rank='die_id8 modulo96'),
        grant=dict(frame_bits=73, layer_bits=6, rank_bits=7, pos_bits=20,
            key_row0_bits=4*15, exclusive_row_end_bits=4*16, blocks_bits=4*9,
            bounds='for each nonempty contiguous2736-key quarter: row0<exclusive_end<=32768; blocks=ceil(min(max(ndie-2736*q,0),2736)/8)<=342',
            physical_row_mapping='OPEN: native99 kind2 row capabilities, not EPS physical HBM rows; provider certifies exact mapping/extent/capacity; no layer->row arithmetic'),
        receipts=dict(key_visible_frame_bits=73, query_ACK_frame_bits=73,
            prefetch_accept_frame_bits=73, prefetch_quarter_bits=2, drain_frame_bits=73,
            durable_visibility='all actual sectors committed with SECDED ACK, not issued writes/KD'),
        latency=dict(command_capture_edges=1, grant_capture_edges=1,
            visible_receipt_capture_edges=1, prefetch_accept_edges_per_nonempty_quarter=1, zero_quarter_skip_edges=1,
            native_accept_edges=1, release_edges=1,
            composed='5 local actor edges +4 quarter accept/skip edges + actual provider grant/visibility, native prefetch CDC/accept, native execution, read/consumer/VM ACK drain and release backpressure; no overlap credit',
            wrapper_crossing_edges_each=6, die_relay_hops='actual path required'),
        mutable_protection='complementary record/owner/grant/flags/state; mismatch sticky fail-stop retains lease until cold POR',
        empty_frame='n0 allowed; matching grant/query ACK required; no key visibility or blocks0 prefetch; four skip edges before empty native launch',
        grant_provider='OPEN: generic CP has no allocation owner; legacy PS row15/blocks9/tag13/KD is insufficient',
        service_binding='OPEN: wide TAG6+stack ledger must retain full73 through actual macro ACK and read drain',
        compiler_integration=False, source_provider_bound=False, physical_qualified=False,
        measured_join=False, performance_credit=0)
