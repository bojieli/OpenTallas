"""Actual chunk8 wk128x512 resource proposal; provider binding is unresolved.

Four16-lane IL8 columns cover64 adjacent8-term chunks. Eight different
output rows interleave through the fixed feedback rings. A source bubble
cannot arbitrarily move that row phase; operand delivery must prepay each
64-edge row group or insert a whole8-edge bubble round.
"""
def model():
    return dict(schema='opentallas.hbm.owner_key_projection.v1',
        rows=128, columns=512, chunk_terms=8, chunks=64,
        replicas=4, lanes_per_replica=16, row_interleave=8,
        MACs_per_cycle=64, MACs_per_key=65536,
        compute_intensity_MACs_per_weight_byte=.5,
        memory_bytes_per_cycle=dict(weight_BF16=128, activation_BF16=128),
        resident_bytes=dict(weight=131072, activation=1024, result_BF16=256),
        boundary_bits_per_cycle=dict(weight=1024, activation=1024,
            result_FP32=32, result_BF16=16),
        routing_tracks_required=2048, channel_capacity_tracks=None,
        fanout_cost='64 different activation indices perissue, no broadcast toall64lanes; fourresult tags align',
        multiplexer_cost='resident activation64-way phase gather; realweightbank selection notyetbound',
        arithmetic='64 sequential8-product chunks from+0; fixedadjacent64-leaf FP32tree; BF16round beforeRMSnorm',
        issue_cycles=1024,
        pipeline_cycles=dict(input_capture=1, BF16multiply=5, FP32feedback=7,
            column16tree=28, column_output=1, final4tree=14),
        composed_cycles_without_provider_stall=1080,
        finite_source_rule='prepay64edges for8rows, or whole8edge bubble rounds; arbitraryready stalls invalid',
        floorplan_slot_fit=False, cell_area_floor_um2=None,
        macro_inventory_status='actualnativeSMH tenword allocation book and installedweightport mapping unresolved',
        clocks=dict(target_period_ps=833.333, setup_uncertainty_ps=60,
            hold_uncertainty_ps=25, physically_qualified=False),
        token_latency_basis='one projection peractualcompressedkey onitsownerdie; compressorcollective precedes it andRMSnorm/RoPE/quant/HBMappend follow; no offpathcredit',
        dependencies=['Actual selectednativeSMH tenword issueengine/PC allocation',
            'Actualinstalled weight131072B andactivation1024B delivery withfinitegroupreservation',
            'Golden128row componentgate andchunk-order mutant',
            'ActualRMSnorm128 gainprovider, YaRN64 rotation and68-byte quantproducer',
            'Actualpaired key/CKV append completion fence'],
        ready_to_build=False, functional_qualified=False,
        physical_qualified=False, headline_credit=False)
