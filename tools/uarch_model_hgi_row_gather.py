"""G25 native row gather, sized before RTL; generic frontend still pending."""
def model(m=18, row_words=32, group=96):
    pf=m*row_words
    if not (1 <= m <= 2048 and row_words in (9,16,32)):
        raise ValueError('native staged gather shape outside M2048')
    chunk_rows=512//row_words
    chunks=(m+chunk_rows-1)//chunk_rows
    return dict(schema='hgi.native-row-gather.v1', default_enable=0,
        models=['DeepSeek-V4.1 HBM','Qwen3-8B HBM'], replicas_per_die=1,
        macs_per_cycle=0, compute_intensity='bit-preserving gather and address transpose',
        communication_bytes=group*pf*64, memory_read_bytes_per_cycle=64,
        memory_write_bytes_per_cycle=4*64,
        destination_writer_status='256B/cycle sink assumed by endpoint bus; real HBM writer throughput and ack binding required before credit', staging_bytes=512*64, row_bytes=row_words*64, native_epochs=chunks, rows_per_epoch=chunk_rows,
        descriptor_contract='current DS compiler FP32 n512 ->2048B row /32flits; packed288B read/decode not implemented or credited',
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
        delivery_added_cycles=4, launch_added_cycles=1, completion_added_cycles=5,
        gather_flits_per_rank=pf, endpoint_pfmax=512,
        full_group_gi_limit=65536, largest_epoch_gi=group*512-1,
        chunk_staging_contract='load_v/load_row/load_rows ->load_r only after protected inject store fully staged',
        delivery_service_floor_cycles=(group*pf+3)//4,
        software_slot_cycles=m*(768+633),
        native_analytical_cycles=pf+chunks*633+(group*pf+3)//4+chunks*12,
        latency_composition='stage owned flits + one TU flight per <=512flit complete-row epoch + delivery floor +12 control/drain/pin edges per epoch; overlap not credited',
        numerical_order='no arithmetic; rank-major wire stream maps to slot-major j*G+r',
        qualification='analytic only; exact endpoint full shape, record/HBM binding and physical closure required')
