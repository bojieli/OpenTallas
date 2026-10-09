"""Distributed row duplicate suppression and ID-tagged reverse grants."""
def model(dff_um2=.2916):
    states=3*32*(64+2+1)+3*(64+5+2)+3
    area=states*dff_um2+1800
    return dict(schema='opentallas.qwen-row-endpoint.v1',default_off=True,adopted=False,
        model_precedes_rtl=True,replicas=48,macs_per_cycle=0,compute_intensity_macs_per_byte=0,
        memory_ports=[],state_bits=states,cell_area_bound_um2=area,
        head_boundary_bits=9760+2048,reverse_grant_bits=3*(64+5+2)+3,
        row_data_boundary_bits=3*281+3,slot_um=[96.768,1200.096],
        max_input_face_bits=11808,face_pin_layers=2,
        bits_per_um_per_layer=11808/(1200.096*2),
        min_spacing_tracks=2,input_face_capacity_tracks=2*int(1200.096/.096),
        replicas_cost=dict(identity_cache='32×64bit last head ID per row',
            consumed_halves='32×2bit V/K acknowledgments; ID is updated before reuse',
            mutable_protection='three cache copies; mismatch stops grants and output',
            ack_packets='at most three ID64/source5/halfmask2 packets per launch edge'),
        latency=dict(added_launch_edges=0,reverse_ack_capture_edges=1,
            transport='actual forward/reverse relay edges required in composed model',
            head_release='only after all needed ID-tagged acknowledgments actually return'),
        remaining=['shared protected16entry PC FIFO ordinal owner',
            'row arbitration credit-state protection',
            'actual relay latency and credits',
            'full native descriptor/row/col metadata fence'])
