"""Protected finite native decoded head owner before RTL construction."""
def model(dff_um2=.2916):
    payload=304;identity=64;stored=384;encoded=6*72;depth=16
    state=depth*encoded+3*(4+4+5+64+payload+identity+2+1+1+3)+encoded
    area=state*dff_um2+2600
    return dict(schema='opentallas.qwen-pc-head-owner.v1',default_off=True,adopted=False,
        model_precedes_rtl=True,replicas=128,macs_per_cycle=0,compute_intensity_macs_per_byte=0,
        memory_ports=[dict(name='finite_head_fifo',read_bytes_per_cycle=encoded/8,
            write_bytes_per_cycle=encoded/8,depth=depth,read_ports=1,write_ports=1)],
        bytes_per_cycle=payload/8,boundary_bits_per_cycle=dict(decoded_in=payload+1,
            row_heads=payload+identity+1,reverse_ack=3*71+3,actual_credit=1,fault=1),
        state_bits=state,cell_area_bound_um2=area,slot_um=[116.64,116.64],
        slot_fit_at_55pct=area<=116.64**2*.55,
        reserved_area_mm2=128*116.64**2/1e6,
        max_face_bits=369,face_layers=2,max_bits_per_um_per_layer=369/(116.64*2),
        stored_layout='304decoded row fields +64ordinal +16reserved, protected as six64+8SECDED sectors',
        finite_capacity=dict(prepaid_entries=16,includes_encoder_pending=True,
            release='one actual credit after all requested ID-matching half acknowledgments retire current head'),
        replicas_cost=dict(fifo_bits=depth*encoded,head_fanout='onehead perPC to12row endpoints; transport stillseparate',
            owner_protection='three pointer/count/ordinal/head/state copies; disagreement failsclosed',
            ecc='six pipelined64bitencoders and six twoedge decoders; CE corrected, UE halts'),
        latency=dict(ingress_encode_edges=1,raw_read_capture_edges=1,ecc_decode_edges=2,
            head_capture_edges=1,reverse_credit_capture_edges=1,
            per_layer_head_initialization_upper=6,gross_exposed_token_cycles_upper=36*6,
            row_ack_transport='actual perbranch relay count and reverseack roundtrip remain required'),
        remaining=['native rawsector todecoded row metadata adapter',
            'ECC decoder transient-state protection qualification',
            'full released producer trace and finite roundtrip composition',
            'physical controller/PC/row head bus slot and interface binding'])
