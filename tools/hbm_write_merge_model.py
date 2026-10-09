"""Full-width per-stack shared service write admission and visibility ledger."""
def model():
    return dict(schema='opentallas.hbm-write-merge-model.v1', replicas=4,
        macs_per_cycle=0, compute_intensity=0, communication_intensity_bytes_per_write=32,
        packet_bits=291, packet_fields=dict(data=256, address=30, pc=5),
        source_ports=3, payload_bytes_per_cycle_per_port=32,
        service_bytes_per_cycle_per_stack=32, service_bits_per_cycle=292,
        boundary_tracks_per_stack=3*292+292+8+3*6,
        routing_channel_capacity=None, floorplan_slot=None, area_um2=None,
        physical_qualification='pending measured route, slot fit and channel capacity',
        mux_cost='three291-bit sources to one291-bit registered output',
        fanout='local source-ready and ledger occupancy only; replicate per stack',
        ledger_depth=8, source_id_bits=2, output_register_bits=293,
        admission='strict WB priority; alternate ingest/loader; reserve one ledger slot for WB',
        latency_cycles=1, clock_ghz=1.2, added_forward_latency_ns=1/1.2,
        acknowledgement='actual service write-completion counter delta; FIFO pop does not acknowledge visibility',
        service_order='one outstanding PHY write in svc; ordered completion across its input FIFO',
        single_user_composition='WB incurs one registered admission cycle plus occupied service and FIFO drain; background maximum6 issued plus1 pending => up to7 service completion intervals before WB',
        throughput='1 write/cycle admission when credits available; physical service cadence bounds sustained rate',
        adoption=False, performance_credit=False)


def per_pc_model():
    m=model()
    m.update(schema="opentallas.hbm-write-source-pc-model.v1", ledger_depth_per_pc=8, pc_count=32, source_id_storage_bits=512, pointer_count_bits=32*(3+3+4), service_packet_bits=294, service_return_bits=32, service_order="only per-PC issue/completion order required; cross-PC completion may reorder", admission="actual-PC issue stalls when thatPC sourceFIFO full; sourcebits travel in sameCDC entry as payload", single_user_composition="source transport adds2bits/write, returned ACKcounters add16bits/stack; no physicalwrite serialization, ledger admission bounded by8 outstanding/PC", physical_qualification="pending model channelcapacity/slot and actual newABI route", adoption=False)
    return m
