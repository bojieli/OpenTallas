#!/usr/bin/env python3
"""Protected native link successor sizing. Baseline and proofs remain unchanged."""
import json
from hbm_collective_storage_model import model as packet_model
from hbm_collective_cdc_refill_model import model as cdc_model
from hbm_collective_credit_protocol_model import model as credit_model
from hbm_collective_flight_model import model as flight_model


def model():
    packet = packet_model()
    return {
        'status': 'MODEL_BEFORE_NATIVE_RTL_DEFAULT_OFF',
        'ports': 8,
        'per_port_window': 64,
        'conservation': 'Every source starts at zero. Initial acknowledged grant64 permits at most64 reservations. Outstanding = reserved unsent + physical forward flight + landing unread/pending/held + CDC storage/held + WSTG + RX packet unread/pending/held. Only actual final RX packet retirement returns credit.',
        'landing': {
            'implementation': 'Existing ot_hbm_collective_packet_fifo ENABLE1 DEPTH64, single pclk domain before protected receive CDC',
            'replicas': 8, 'macros_per_replica': 3, 'added_macros': 24,
            'payload_bits': 8*64*545, 'logical_encoded_bits': 8*64*648,
            'physical_sram_bits': 24*256*256,
            'held_encoded_bits': 8*648,
            'control_plus_seal_bits': 8*(28+72),
            'raw_macro_area_um2': 24*172.8*41.04,
            'macro_reservation_at_55_percent_um2': 24*172.8*41.04/.55,
            'write_bytes_per_port_cycle': 96, 'read_bytes_per_port_cycle': 96,
            'payload_boundary_bits_per_cycle': 545, 'macro_boundary_bits_per_cycle': 768,
            'write_II': 1, 'read_II': 3, 'push_to_visible_cycles': 2,
            'capacity_proof': 'Even if downstream refuses indefinitely, at most64 total outstanding flits can arrive. Landing holds64 independently of CDC pointer coherence or scrub. If landing count64, no additional legal arrival exists until final retirement returns a credit; a same-edge full pop cannot authorize an extra arrival.',
            'fault_contract': 'Control seal mismatch and payload UE suppress valid before consumption and assert fault. This is quarantine of the current transaction, not transparent repair or successful completion. Data CE is corrected on read. No-ready PHY traffic following a fatal landing fault cannot be claimed retained; coordinated physical purge and transaction recovery required.'
        },
        'synchronous_packet_macros_total': packet['macro_count']+24,
        'synchronous_packet_raw_macro_area_um2': packet['raw_macro_area_um2']+24*172.8*41.04,
        'cdc': cdc_model(),
        'credit': credit_model(),
        'flight': flight_model(w=545,depth=14,replicas=16),
        'native_retirement': 'Gate both partial dispatch and result delivery selection with per-port credit_rx.final_retire_ready BEFORE rb_pop and delivery effects. Credit return sees exactly that accepted rb_pop. Landing pop, CDC pop and flight advance never return end-to-end credits.',
        'source_reservation': 'Real credit_source reserve handshake gates source queue removal before physical launch. Already reserved flits may drain after session closes new admission; cold reset/provider fences all eight ports.',
        'control_transport': 'Grant and ACK messages remain72 encoded bits. Real protected valid/ready CDC plus physical management transport must be bound; no ideal zero-time wire credited.',
        'clock_reset': 'Core and link are independent833.333ps inputs with local reset_entry release. Only coordinated cold session may purge queues/credits. Context arm does not reset pointers or epochs.',
        'compute': 'Zero new MACs; eight sets of nine SECDED encoders/decoders, control comparison and queue selection. Actual standard-cell area and mux/control fanout pending mapped inventory.',
        'routing': 'Added24 real SRAM macros with768-bit per-queue memory buses. Track count, pin locations, halos and clock distribution unmeasured; no inherited reduced collective slot.',
        'latency': {
            'minimum_added_receive_visibility_link_cycles': 2,
            'landing_service_flits_per_link_cycle': 1/3,
            'composed_endpoint_cycles': None,
            'single_user_token_delta_ns': None,
            'required_measurement': 'Replay full PF384 native calendar with real initial grants, final-only return, landing/CDC/flight/RX occupancy and independent clock phase. Measure two extra landing visibility cycles plus II3 contention; do not add unmatched earlier529/531 endpoint numbers.'
        },
        'adoption_holds': ['native fullshape exactness and negative controls', 'source and receiver conservation over all real flight stages', 'actual PHY/control transport binding', 'coordinated clock/reset composition', 'mapped retained protection inventory', 'SS/FF route and complete floorplan/token composition']
    }

if __name__ == '__main__':
    print(json.dumps(model(), indent=2))
