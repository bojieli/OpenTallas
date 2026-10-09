"""Source-sized native index query and candidate formatting, no closure credit."""
def model():
    return dict(scope='prebuild; finite exact RTL gates and physical mapping required',
        query=dict(source_bits=1047,output_bits=1048,initial_credits=4,
                   added_cycles=1,accepted_blocks_per_frame=128,
                   memory_bytes_per_cycle=128,credit_bits=3,credit_protection_bits=3,
                   retained_order_bits=8,frame_owner_bits=73,
                   area_floor_ff_bits=1048+6+16),
        candidate=dict(input_bits=72,quarter_completion_sideband_bits=1,
            tuple_bits=34,tuples_per_flit=15,tu_payload_bits=512,tu_header_bits=33,
            flits_per_quarter='ceil(emitted tuple slots / 15); emitted extent not valid-count',
            serializer_tuples_per_cycle=1,packet_input_tuples=2,
            memory_bytes_per_cycle=0,output_boundary_bits_per_cycle=545,
            initial_landing_credits=8,landing_storage_bits=8*73,
            assembly_bits=510,output_bits=545,owner_metadata_bits=73,
            arithmetic_changes=0,latency='one tuple/cycle plus actual TU stalls; no overlap credit',
            area_status='FF and mux estimate only; mapped area unqualified'),
        composed_latency='formatter occupancy must be measured and composed; no adopted token-rate credit')
