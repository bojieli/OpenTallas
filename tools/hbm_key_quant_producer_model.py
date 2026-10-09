"""Actual 128-element key quantisation landing, before RTL build.

This prices only the final FP4 stage. Compressor, projection, norm, RoPE,
weight delivery and actual HBM append visibility remain separate obligations.
"""
def model():
    return dict(schema='opentallas.hbm.key_quant_producer.v1', replicas=1,
        default_enabled=False, MACs_per_cycle=0, compute_intensity=0,
        memory_bytes_per_cycle=dict(input_fp32=128, output_key=68),
        boundary_bits_per_cycle=dict(input_fp32=1024, output_key=544,
            key_index=20, layer=6),
        routing_tracks_required=1024+544+26, channel_capacity_tracks=None,
        quantizer='unchanged ot_hdc_actquant FP4, 32 elements/edge, latency13',
        quantizer_replicas=1, multiplexer_cost='four128-bit code writes and four8-bit scale writes',
        fanout_cost='one quantizer; one held68-byte key; no replica mux',
        additional_register_bits=544+26+26+26+6,
        cell_area_floor_um2=(544+26+26+26+6)*.2916,
        floorplan_slot_fit=False, placement_context='owner-die native key slot not yet selected',
        latency_cycles=dict(input_blocks=4, quantizer=13, held_output=1),
        token_latency_basis='one key per actual compressor group; output acceptance precedes WB fence; no overlap credited',
        clocks=dict(target_period_ps=833.333, setup_uncertainty_ps=60,
            hold_uncertainty_ps=25, physically_qualified=False),
        arithmetic='FP32 input; E2M1 nibbles in low-index order, UE8M0 exponent+127 per32-element block',
        dependencies=['actual chunk8 compressor and BF16 wk128x512 projection',
            'actual RMSnorm128 and golden64-element YaRN rotation',
            'actual68-byte HBM append adapter and completion fence'],
        functional_qualified=False, physical_qualified=False, headline_credit=False)
