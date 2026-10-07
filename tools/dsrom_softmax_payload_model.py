#!/usr/bin/env python3
"""Minimum protected serial payload path; full-width core path kept separate."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def build():
    path='physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.json'
    macro=json.loads((ROOT/path).read_text())
    return dict(schema='opentallas.dsrom_softmax_payload.v2', adopted=False,
        build_scope='minimum serial assembler/drain component exactness; not full core memory controller',
        source_sha256={path:hashlib.sha256((ROOT/path).read_bytes()).hexdigest()},
        shape=dict(serial_bits=1024, payload_row_bits=8192, SECDED_row_bits=9216,
            serial_beats_per_row=8, codewords_per_beat=16, SRAM_macros=36,
            macro_width_bits=256, macro_depth=128),
        mutable_payload=dict(write_assembly_bits=9216, read_hold_bits=9216,
            protection='SECDED64+8 throughout retained payload; no decoded full-row stall buffer'),
        serial_codec=dict(replicas=16, lane_registered_bits=294,
            register_bits=16*294, write_encode_edges=1, read_pipeline_edges=3,
            scope='VM ingress and egress only'),
        serial_control=dict(provisional_register_bits=124,
            protection='complemented counters, row tags, addresses, pending index, state, valid and fault'),
        serial_storage_FF_bits=2*9216+16*294+124,
        serial_FF_floor_um2=(2*9216+16*294+124)*.2916,
        serial_read_mux=dict(output_bits=1152, inputs=8, mux2_equivalents=1152*7,
            area_um2=None, timing='select precedes first registered code capture; physical measurement required'),
        core_burst_path=dict(required_parallel_decode_lanes=128,
            additional_registered_bits=128*(72+72+8+66+3),
            decoded_bits_per_stream_edge=8192, initiation_interval=1,
            throttling_allowed=False, implemented_by_serial_component=False,
            reason='existing softmax consumes40 consecutive score vectors and32 consecutive PV vectors without ready'),
        memory=dict(read_ports=1,write_ports=1,bits_per_port_edge=9216,
            SS_clk_to_q_ps=macro['timing']['ss']['clk_to_q_ps'],
            read_request_to_raw_capture_edges=1,
            raw_capture_budget_before_setup_wire_clock_ps=833.333-60-macro['timing']['ss']['clk_to_q_ps'],
            raw_macro_area_mm2=36*macro['area']['macro_area_um2']/1e6,
            floorplan_fit=False, macro_pin_stations_bound=False),
        serial_schedule=dict(write_beats_initiation_interval=1,
            final_input_beat_to_macro_write_edges=2,
            read_requests_outstanding=1,
            registered_read_address_launch_edges=1,
            read_request_to_first_accepted_beat_edges=6,
            subsequent_accepted_beat_interval_edges=4,
            unstalled_read_request_to_last_accepted_beat_edges=34,
            note='conservative repeated decode of held protected row; prices real SRAM+capture+codec boundaries'),
        T640_egress=dict(exp_rows=40,BF16_packed_rows=16,serial_row_transactions=56,
            request_to_final_take_service_edges=56*34,
            excludes='inter-row request gaps, source compute, external stalls and CDC; not token latency'),
        domains=dict(component='stream1.2GHz',serial_host='0.9GHz boundary not implemented',
            uncertainty_ps=dict(setup=60,hold=25),CDC_latency=None,physical_boundary_budget=None),
        route_admitted=False,
        missing=['mapped mux/ECC/control area','full128-lane core replay path',
            'native CDC and reset epoch protection','actual memory pin clock/input/output budget',
            'producer tags and compiler integration','measured row/parent token composition'])


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path)
    args=parser.parse_args();text=json.dumps(build(),indent=2)+'\n'
    if args.output:args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(text)
    else:print(text,end='')
