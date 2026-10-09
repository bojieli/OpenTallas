"""Actual native32-bit command provider, sized before RTL."""
def model(dff_um2=.2916):
    state=3*(30+4+3+1+1+32+1+3)
    area=state*dff_um2+800
    return dict(schema='opentallas.qwen-native-cmd.v1',default_off=True,adopted=False,
        physical_closed=False,model_precedes_rtl=True,replicas=128,
        macs_per_cycle=0,compute_intensity_macs_per_byte=0,memory_ports=[],
        state_bits=state,cell_area_bound_um2=area,
        slot_um=[96.768,96.768],slot_fit_at_55pct=area<=96.768**2*.55,
        placement='inside actual controller/PCport composite if measured utilisation allows; no separate overlap claim',
        standalone_reservation_mm2=128*96.768**2/1e6,
        boundary_bits_per_cycle=dict(desc_offer=31,go=1,write_scheduler=11,
            causal_fence=3,return_cmd_credit=1,read_release=3,native_cmd=33,
            native_read_credit=3,producer_take=3,fault=1),
        routing=dict(max_face_bits=50,face_capacity_tracks=int(96.768/.048)),
        fifo=dict(native_initial_credits=8,descriptor_pending_entries=1,go_pending_entries=1,
            write_queue='existing protected ledger holds scheduler offer until wr_take'),
        mux_demux='three-source nativecmd selection; descriptor then go then write',
        fanout='one provider perPC; real per-stack descriptor distribution remains priced separately',
        protection='three copies of pending descriptor, credits, phase flags and boundary packet; disagreement suppresses all accepts/output and faults',
        latency=dict(command_output_edges=1,read_release_edges=1,
            gross_layer_desc_go_edges_upper=72,gross_added_token_ns_upper=72*1.024,
            causal_retire='new descriptor waits actual window-retired event and write/transport quiet; no elapsed-time substitute'),
        native_encoding=dict(desc='op0,n11,row19',go='op1',write='op2,reserved20,col5,bank5'),
        remaining=['actual descriptor mailbox/ordinal/ledger binding',
            'corrected read provider and real row/col->sector identity',
            'source-pinned exact/golden gates and fullshape physical closure',
            'head/row FIFO and transport identity integration'])
