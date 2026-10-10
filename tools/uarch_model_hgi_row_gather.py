"""G25 native row gather, sized before RTL; generic frontend still pending."""
def model(m=18, row_words=9, group=96):
    pf=m*row_words
    if not (1 <= pf <= 512 and row_words in (9,16,32)):
        raise ValueError('native staged gather shape outside PFMAX')
    return dict(schema='hgi.native-row-gather.v1', default_enable=0,
        models=['DeepSeek-V4.1 HBM','Qwen3-8B HBM'], replicas_per_die=1,
        macs_per_cycle=0, compute_intensity='bit-preserving gather and address transpose',
        communication_bytes=group*pf*64, memory_read_bytes_per_cycle=64,
        memory_write_bytes_per_cycle=4*64, staging_bytes=512*64,
        staging_required_protection='external existing protected SU/VM store; no unprotected new SRAM',
        inject_bits_per_cycle=512, deliver_bits_per_cycle=4*545,
        control_input_bits=8+8+16+16, output_bits_per_cycle=4*(512+20+16+1),
        mux_cost='existing endpoint single bypass inject, four independent delivery address pipelines',
        demux_cost='recipient rank guard; four independently registered sink lanes',
        fanout='one registered run descriptor per delivery lane',
        routing_tracks_needed=4*545+4*(512+20+16+1), routing_capacity=6250,
        routing_basis='separate input/output faces: each needs <=2196 tracks, versus6250 per300um layer; estimate, actual boundary check owed',
        new_register_bits=4*(4*512+3*8+4*16+7)+56+4,
        pipeline_address_arithmetic='rank*pf then local /9,%9 or shift, then slot*G+rank; each boundary registered',
        estimated_new_cell_area_um2=16000, floorplan_slot_um=[600,240],
        area_fit_fraction=16000/(600*240),
        delivery_added_cycles=4, launch_added_cycles=2,
        gather_flits_per_rank=pf, endpoint_pfmax=512,
        delivery_service_floor_cycles=(group*pf+3)//4,
        software_slot_cycles=m*(768+633),
        native_analytical_cycles=pf+633+(group*pf+3)//4+6,
        latency_composition='stage owned flits + one TU flight + delivery floor + six control/map edges; overlap not credited',
        numerical_order='no arithmetic; rank-major wire stream maps to slot-major j*G+r',
        qualification='analytic only; exact endpoint full shape, record/HBM binding and physical closure required')
