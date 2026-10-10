"""Sizing before building the default-off fence registered credit-return bridge."""

def model(clock_ghz=1.2):
    widths = [4105, 8]
    return dict(schema='opentallas.hbm.fence.pin_return.v1', adopted=False,
                default_PINRET=0, exactness='same ordered valid/ready transactions; no arithmetic',
                MACs_per_cycle=0, memory_bytes_per_cycle_delta=0,
                boundaries_bits_per_cycle=dict(host_write=4105, fence=8, credit_return=2),
                sustainable_transactions_per_cycle=1/4,
                output_payload_bytes_per_cycle_max=(4096/8)/4,
                replicas=2, added_output_register_bits=sum(widths), added_control_FF=6+130,
                mux_bits=sum(widths), demux_bits=0,
                pin_ready_fanout=2, internal_load_fanout_max=130, lane_load_fanout_max=32,
                tracks_required_delta=0,
                channel_capacity='same die-link ports; frame grows p2r3 300x300 to 360x360',
                area_upper_bound_um2=(sum(widths)+136)*0.6,
                area_basis='pre-build allowance 0.6 um2/FF including mux/route; mapping must measure',
                slot_area_um2=360*360,
                floorplan='disjoint row/site pin banks <=16um inward, <=12um along face; FIRM through DPL',
                added_output_latency_cycles=2,
                accepted_to_internal_credit_cycles=1,
                next_output_reload_cycles=3,
                single_user_latency_delta_ns_per_write=2/clock_ghz,
                single_user_latency_delta_ns_per_fence=2/clock_ghz,
                composed_delta_ns='2 * (writes + fences) / clock_ghz; sum actual trace events, no headline adoption',
                evidence_gate='full-width original fence transaction bench and mutants + TT/FF/DRC closure')
