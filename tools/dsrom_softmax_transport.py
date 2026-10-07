#!/usr/bin/env python3
"""Price the actual softmax row ports before choosing a parent transport.

This is a bandwidth and storage lower bound, not a composed token latency or
an admitted CDC implementation. The existing core has no input/output ready.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def build(tokens=640, bus_bits=1024):
    if tokens not in (128, 640) or bus_bits <= 0:
        raise ValueError('supported scored rows: 128 or 640; positive bus width')
    heads, lanes, tail = 16, 16, 64
    vectors = tokens // lanes
    pv_vectors = 512 // lanes
    fp32_bits = heads * lanes * 32
    config_bits = 7 + 3 + 32 + heads * 32 + 2 * 16 * tail
    ports = {}
    for name, width, count, direction in (
        ('scores', fp32_bits, vectors, 'into_softmax'),
        ('pv', fp32_bits, pv_vectors, 'into_softmax'),
        ('exponentials', fp32_bits, vectors, 'out_of_softmax'),
        ('result_bf16', heads * lanes * 16, pv_vectors, 'out_of_softmax'),
    ):
        ports[name] = dict(direction=direction, bits_per_stream_edge=width,
                           bytes_per_stream_edge=width // 8, vectors_per_row=count,
                           payload_bytes_per_row=width * count // 8,
                           serial_beats_per_vector=math.ceil(width / bus_bits),
                           serial_beats_per_row=count * math.ceil(width / bus_bits))
    source_paths = ['rtl/hdc/v41x/ot_dsrom_su_softmax.sv',
                    'rtl/test/tb_dsrom_su_softmax.sv']
    ingress = sum(p['serial_beats_per_row'] for p in ports.values()
                  if p['direction'] == 'into_softmax')
    egress = sum(p['serial_beats_per_row'] for p in ports.values()
                 if p['direction'] == 'out_of_softmax')
    command_beats = math.ceil(config_bits / bus_bits)
    macro_path = 'physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.json'
    macro = json.loads((ROOT / macro_path).read_text())
    # One 8192-bit payload row + 128 independent 64+8 SECDED codewords.
    # Pack two BF16 outputs per row. Inputs and outputs occupy disjoint slots.
    protected_width = 128 * 72
    memory_copies = protected_width // 256
    row_slots = vectors + pv_vectors + vectors + pv_vectors // 2
    return dict(schema='opentallas.dsrom_softmax_transport.v1',
        source_sha256={p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in source_paths},
        shape=dict(heads=heads, lanes_per_head=lanes, tokens=tokens, pv_elements_per_head=512),
        ports=ports,
        atomic_row_command=dict(bits=config_bits, bus_beats=command_beats,
            fields=dict(nv=7, lt=3, scale=32, sink=512, cosv=1024, sinv=1024),
            requirement='capture all fields atomically; hold through final output; no next row until drain'),
        auxiliary_outputs=dict(mx_d_bits=512, es_d_bits=512, den_d_bits=512,
            valid_bits=3, fault_bits=1,
            transport_in_payload_totals=False,
            requirement='bind local consumers or price their transport separately; payload totals exclude valid, fault and observation ports'),
        serial_alternative=dict(bus_bits=bus_bits, clock_GHz=0.9,
            ingress_beats=ingress + command_beats, egress_beats=egress,
            shared_half_duplex_beats=ingress + egress + command_beats,
            shared_half_duplex_transport_lower_bound_ns=(ingress + egress + command_beats) / 0.9,
            independent_direction_transport_lower_bound_ns=max(ingress + command_beats, egress) / 0.9,
            max_fp32_vectors_per_stream_edge=0.9 / 1.2 / math.ceil(fp32_bits / bus_bits),
            full_rate_compatible=False,
            buffering='reserve all row slots, gather scores before score replay, then drain exponents to P.V before gathering PV'),
        complete_row_storage=dict(
            ingress_payload_bytes=sum(p['payload_bytes_per_row'] for p in ports.values() if p['direction']=='into_softmax'),
            egress_payload_bytes=sum(p['payload_bytes_per_row'] for p in ports.values() if p['direction']=='out_of_softmax'),
            excludes='configuration, ECC, tags, validity, occupancy and implementation padding; double buffering not included'),
        reservation_fallback=dict(status='sized minimum component; no RTL/physical qualification',
            row_payload_bits=8192, protected_row_bits=protected_width,
            protection='SECDED64+8 per64data bits; SRAM protection retained',
            macro_record=macro_path, macro_sha256=hashlib.sha256((ROOT/macro_path).read_bytes()).hexdigest(),
            macro_copies=memory_copies, macro_depth=128, occupied_row_slots=row_slots,
            raw_macro_area_mm2=memory_copies*macro['area']['macro_area_um2']/1e6,
            macro_reservation_mm2_at_55pct=memory_copies*macro['area']['macro_area_um2']/1e6/.55,
            layout='disjoint score,PV,exp,and packedBF16 regions; atomic single-row ownership until output drain',
            SRAM_ports='one9216-bit read and one9216-bit write per stream edge, each distributed over36macros',
            ingress='gather8beats before writing whole protected vector; retain one protected assembly vector',
            egress='capture every fixed-rate exp vector; pack two BF16 vectors per SRAM row',
            drain='drain all exponentials after exp capture and before PV fill/replay; drain BF16 after normalize completes',
            replay='40 score edges at T640; drain exp to attention P.V; gather32 PV vectors; replay PV only after den_v',
            no_ready_output_requirement='exp and BF16 output phases must not overlap; prove before sharing write port',
            command_protected_storage_bits=math.ceil(config_bits/64)*72,
            admission='reserve capacity, NOT all input data, before starting core; PV depends on exp output; no next command until final drain',
            dependency_chain=['scores_fill','scores_replay','exp_capture','exp_drain_to_attention_PV','PV_compute_and_fill','PV_replay_after_den_v','BF16_capture','BF16_drain'],
            exact_component_gate=['beat-order conservation at8192bits','atomic config despite producer stalls',
                'output capacity conserved under indefinitely stalled drain','reject early dispatch and duplicate/extra beats',
                'production reset/CDC/protection negatives','fixed-burst phase overlap assertion'],
            missing=['memory clk-to-q and read/capture schedule','ECC encode/decode stage area/latency',
                'assembly/packing/serialization registers and mux area','CDC implementation and latency',
                'physical ports/corridor capacity','measured parent occupancy and token latency']),
        protected_lane_component=dict(payload_bits=64, code_bits=72, replicas=128,
            write_encode_registered_edges=1, read_capture_edges=1,
            read_syndrome_edges=1, read_correction_edges=1,
            memory_read_request_to_capture_edges=1,
            write_read_initiation_interval=1, codec_memory_port_bytes_per_edge=9,
            SRAM_SS_clk_to_q_ps=macro['timing']['ss']['clk_to_q_ps'],
            SRAM_SS_capture_data_budget_ps=833.333-60-macro['timing']['ss']['clk_to_q_ps'],
            actual_SS_capture_setup_wire_clock_budget_bound=False,
            register_bits_per_lane=294, full_shape_register_bits=294*128,
            DFF_floor_um2=294*128*.2916,
            combinational_area=None, routed_SS_FF=None,
            macro_clock_assumption='read sampled on stream edge; raw code captured on following edge before any syndrome logic',
            controller='one valid pipeline per replicated64-bit lane; row address, ownership and error aggregation require separate protection',
            critical_path_contribution='one encode edge before macro write; three code-input-to-decoded-valid pipeline edges; compose each dependent read/write at parent join',
            build_scope='minimum codec component exactness only; no parent SRAM or CDC adoption'),
        phase_controller_component=dict(default_off=True, replicas=1,
            states=['idle','fill_scores','replay_scores','capture_exp','drain_exp','fill_PV','replay_PV','capture_BF16','drain_BF16','fault'],
            protection='onehot state plus complement; duplicated-complement count,tag,short-row,denominator-ready and settle count; fail closed on mismatch',
            state_register_bits=20, counter_register_bits=12, row_tag_register_bits=32,
            short_row_register_bits=2, denominator_register_bits=2, settle_register_bits=4,
            total_FF_bits=72, FF_floor_um2=72*.2916,
            combinational_area_um2=None, proposed_slot_um=[100,100], slot_fit_requires_synthesis=True,
            memory_boundary_address_bits=7, memory_data_bits=0,
            MACs_per_cycle=0, configuration_payload_stored_elsewhere=True,
            accepted_events_per_edge=1, score_vector_count=[8,40], PV_vector_count=32,
            exponent_vector_count=[8,40], BF16_vector_count=32,
            registered_write_visibility_wait_edges=2, waits_per_transaction=4,
            explicit_visibility_wait_edges_per_transaction=8,
            phase_transition_extra_edges=0,
            domain='stream1.2; incoming row bus must already be synchronized',
            interface='tagged vector commits and drains; controls actual memory region/offset, but payload packing and read pipeline remain separate',
            missing=['synthesized combinational area','actual command/data CDC','memory arbiter and read-return tags','physical SS/FF and parent timing composition']),
        direct_stream_alternative=dict(clock_GHz=1.2, independent_score_and_PV_bits=2*fp32_bits,
            independent_exp_and_result_bits=fp32_bits + heads*lanes*16,
            status='requires actual producer/consumer placement and bandwidth; no free shared-memory or CDC assumption'),
        arithmetic_MACs_added=0, adopted=False, hardware_build_admitted=False,
        composed_single_user_latency_ns=None,
        obligations=['bind exact producer and consumer per port',
            'price SRAM ports, protection and muxes for chosen row buffers',
            'bind physical clock domains, crossing latency and reset ownership',
            'prove no overflow: core has no backpressure ports',
            'preserve golden row and reduction order with atomic configuration',
            'measure row-level latency; compose dependencies rather than sum overlapping link and compute times',
            'place measured pin stations and verify channel capacity at actual full width'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--tokens', type=int, default=640)
    parser.add_argument('--bus-bits', type=int, default=1024)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    text = json.dumps(build(args.tokens, args.bus_bits), indent=2) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text)
    else:
        print(text, end='')
