"""Finite return-mux sizing; replaces existing selectors, never payload ports.
No physical clock/area/track admission is inferred from a functional test.
"""
def size(inputs=128, payload_bits=291):
    if inputs < 1 or payload_bits < 1:
        raise ValueError('positive full-bundle geometry required')
    iw = max(1, (inputs - 1).bit_length())
    return dict(inputs=inputs, payload_bits=payload_bits,
                raw_ff_bits=2*iw+1, replacement_pointer_bits=iw,
                additional_raw_ff_bits=iw+1, payload_ff_bits=0,
                payload_mux_2to1_bits=(inputs-1)*payload_bits,
                input_boundary_bits_per_cycle=inputs*(payload_bits+2),
                output_boundary_bits_per_cycle=payload_bits+2,
                output_bytes_per_cycle=32, selected_port_count=1, replicas=1,
                added_unstalled_cycles=0, initiation_interval_edges=1,
                backpressure_latency_bound=None, clocks=1, added_cdc=0,
                reset_sinks=2*iw+1, physical_area_mm2=None, channel_tracks=None,
                clock_ss_ff_admitted=False,
                provider_must_hold_valid_and_payload_until_selected_accept=True)


def partition():
    pc = size(128, 35+256)
    client = size(2, 1+33+256)
    return dict(pc=pc, client=client,
                additional_raw_ff_bits=pc['additional_raw_ff_bits']+client['additional_raw_ff_bits'],
                replaces_existing_selectors=True,
                new_payload_or_memory_capacity=False,
                full_token_or_physical_admission=False)
