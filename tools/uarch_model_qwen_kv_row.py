"""Full32-PC, three-slot option-M row arbiter before building its RTL."""
def model(dff_um2=.2916):
    heads=32*305
    packet=5+5+7+1+1+2+4+256
    state=heads+3*packet+32*4+64+1
    area=state*dff_um2+28000
    slot=[96.768,864.]
    return dict(schema='opentallas.qwen-kv-row.v1',default_off=True,adopted=False,
        model_precedes_rtl=True,physical_closed=False,replicas=48,
        rows_per_stack=12,pseudo_channels_per_stack=32,macs_per_cycle=0,
        compute_intensity_macs_per_byte=0,memory_ports=[],
        boundary_bits_per_cycle=dict(decoded_heads=heads,head_half_grants=64,
            row_launch=3*packet,return_credits=32),
        routing=dict(input_tracks=heads,output_tracks=3*packet,
            input_face_capacity_tracks=2*int(slot[1]/.048),input_face='W',
            output_face='E',pin_layers=['M4','M6'],
            same_heads_fanout_rows=12,head_fanout_transport='must be separately registered and priced'),
        state_bits=state,cell_area_bound_um2=area,logic_allowance_um2=28000,
        slot_um=slot,slot_fit_at_55pct=area<=slot[0]*slot[1]*.55,
        reserved_area_mm2_per_die=48*slot[0]*slot[1]/1e6,
        placement='replaces unimplemented tall qfd_kvc abstract with12actualrow masters; PC FIFOs separate',
        per_pc_fifo=dict(depth=16,bits_per_entry=305,replicas=128,
            cell_floor_um2_per_stack=32*16*305*dff_um2,physical_slot_unclosed=True),
        arbitration='global128-port rotating order, at most3fragments; same-tile launch shares one prepaid merged-word credit',
        retirement='independent V halves; PC head pops only after all required half grants across12rows',
        flow=dict(initial_credits_per_tile=8,credits_per_row=32,
            consume='one per distinct destination tile on one launch edge',
            release='actual merged-word dequeue at tile queue; no fragment or PHY-arrival credit',
            same_tile_launch='same word and disjoint quarters; equal hopcount preserves joint arrival'),
        latency=dict(added_row_launch_edges=1,gross_token_added_cycles=36,
            pending='actual replay must include row-slot contention, PC FIFOs, relay and credit return; no gain claimed'),
        obligations=['full32-PC RTL exactness and competing independent V halves',
            'protect mutable FIFOs/half-owner/credit state',
            'physical binding of head distribution and return credits',
            'real twelve-row slot and controller/CDC integration',
            'full-width physical closure and measured producer composition'])
