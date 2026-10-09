"""Minimum actual CP PC32 to native ten-word SM program bridge, before RTL."""
def model():
    return dict(schema='opentallas.dshbm.mtp.record_dispatch.model.v1',default_enabled=False,
        replicas_per_die=32,macs_per_cycle=0,compute_intensity=0,
        memory_bytes_per_cycle={'installed_program_service':4},
        boundary_bits_per_cycle={'CP_launch_pc':32,'actual_DS_owner':73,
            'owner_program_header':32+33+16,'result_ack':2},
        routing_tracks_needed=222,channel_capacity='existing SM-local CP/provider paths, measured collar pending',
        mux_demux_cost='single source-installed kernel map, no guessed PC/namespace',fanout='one local owner',
        area={'flop_bits_per_SM':191,'flop_bits_die':32*191,'SRAM_bits_added':0},
        floorplan_slot='existing SM-local program owner control, no fit or physical claim',
        latency_cycles={'CP_launch_capture':1,'run_owner_accept':1,'real_owner_retire_to_CP':1},
        single_user_latency='actual owner/read/SM/publication cycles plus3 bridge cycles; no arithmetic cycles replaced',
        SRAM_HBM_payload_protection='retained actual protected service; control is plain MX1 flops',
        completion='only after actual native owner done (SM arrive and matching real result-publication receipt)',
        source_PC='exact PC32 installed by actual kernel allocator; mapped source program base/count/limit checked',
        numerical_scope='minimum Markov matvec; real stored-DLOG addition/rank-ordered argmax separately required',
        physical_qualified=False)
