"""Q3 lane-local exact FP8 KV packet: full64 lanes, two address bases."""
def model(dff_um2=.2916):
    bits=64+2*24+64*8
    state=3648+2*bits+64*9+64
    slot=[384.,64.]
    area=state*dff_um2+2200
    return dict(schema='opentallas.qwen-kv624.v1',default_off=True,adopted=False,
        physical_closed=False,model_precedes_rtl=True,replicas=1,lanes=64,
        macs_per_cycle=0,compute_intensity_macs_per_byte=0,memory_ports=[],
        input_bits_per_cycle=64*(1+24+32),output_bits_per_cycle=bits,
        payload_bytes_per_cycle=64,
        boundary_bits_per_cycle=dict(su_internal=3648,kv_packet=624,fault=1),
        routing=dict(required_internal_input_tracks=3648,required_output_tracks=625,
            face_capacity_tracks=2*int(384/.048),input_face='N',output_face='S',pin_layers=['M4','M6']),
        replicas_cost=dict(state_bits=state,encode64='64 independent exact on-grid32-to8 codecs',
            address_check='two32-lane fixed-stride checks',data_mux='two32-way local address-base selects',
            fanout='base per32lanes; registered packet boundary'),
        slot_um=slot,cell_area_bound_um2=area,slot_fit_at_55pct=area<384*64*.55,
        area_reservation_mm2=.024576,
        arithmetic='same f32_e4m3 as pinned KV service; packing already-rounded on-grid values only',
        address_contract='K addresses have stride16; V addresses stride1; two32lane bases; all active lanes checked',
        latency=dict(added_write_edges=3,gross_exposed_token_cycles_upper=36*8*3,
            transport='actual die relays still separately priced; no overlap credit'))
