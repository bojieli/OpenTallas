#!/usr/bin/env python3
"""HA4 additive microarchitecture price; no adoption or inference.

Shared inventories are imported from the canonical lifecycle model. Technology
constants are source pinned to uarch_model.py. Unknown route, CDC and backend
bounds remain unknown; they never become free latency.
"""
import ast
import hashlib
import json
from pathlib import Path
from gpu_sys.canonical_qwen_kv_controller_model import model as lifecycle_inventory
ROOT = Path(__file__).resolve().parents[1]

def price():
    source = ROOT / 'tools/uarch_model.py'
    assignments = {n.targets[0].id: n.value for n in ast.parse(source.read_text()).body
                   if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)}
    dff = ast.literal_eval(assignments['DFF_UM2'])
    baseline = lifecycle_inventory()
    # One-hot saved row, registered snapshot of one actual row. Existing arrays
    # and authority ports retained. Additional two command-dispatch edges only.
    snapshot = 1+13+64+1+64+13+2+2+2+2
    added = 72+snapshot+8+1  # FSM extends 4 -> 5 bits
    return dict(schema='opentallas.hbm_accel.ha4.price.v1', status='ESTIMATE_NOT_ADOPTED',
        source_sha256={str(source.relative_to(ROOT)): hashlib.sha256(source.read_bytes()).hexdigest()},
        reuse={'model_parent':'8564e79eaf906c820aec5eb92bfda1cca80ee43d',
               'stream':'52ce3e9c1', 'expert_fetch':'c52ae6d7f', 'clock_verdict':'2078c269c',
               'edge_owner':'Cicero01a101ea-9229'},
        lifecycle=dict(baseline=baseline, added_control_bits=added,
            added_storage_proxy_um2=added*dff, added_slot_proxy_um2=added*dff/.7,
            added_SRAM_bytes=0, added_MACs_per_cycle=0,
            memory_ports_bytes_per_cycle={'shared':64,'payload_read':32,'payload_write':32},
            boundaries_bits={'command':baseline['command_bits']+10+5+2*34+512,
                             'row_snapshot':snapshot,'shared_data':512,'payload_data':256,
                             'payload_owner_sector_address':64+20+9+34,
                             'drain_owner_cohorts':64+20+8},
            row_mux_inputs=72, row_select_flops=72, row_demux_replicas=72,
            maximum_row_select_fanout_estimate=snapshot,
            added_dispatch_cycles=2, unchanged_sector_issue_fsm=True,
            arithmetic='unchanged K byte RMW and V packed bytes',
            floorplan_slot_fit=None, routing_tracks_capacity=None,
            area_proxy_excludes=['logic','protection','clock','route','power_grid','repeaters']),
        clocks=dict(stream_ps=833, serial_ps=1111, service_ps=1024,
                    service_MHz=976.5625, headline_1p2GHz_qualified=False,
                    SS_setup_uncertainty_ps=60, FF_hold_uncertainty_ps=25),
        crossing=dict(request_bits=34+6+16, response_bits_per_pc=256+16+5,
            response_PC_lanes=32, request_latency_ns_estimate=3*1.024+2*.833,
            return_latency_ns_estimate=3*.833+2*1.024,
            status='ESTIMATE; no measured CDC, no free CDC allowed'),
        models={name:dict(added_dispatch_ns_per_command=2*.833,
            commands_per_token_estimate=commands,
            token_added_us_estimate=None if commands is None else commands*2*.833/1000,
            external_service_and_wire_ns=None, full_token_measured_gain=None,
            per_stack_index_attachment='existing scorer; exact saved owner/tag required')
            for name,commands in [('qwen3_8b_hbm',72*24),('deepseek_v41_hbm',None),
                                  ('qwen3_8b_rom',None),('deepseek_v41_rom',None),
                                  ('qwen3_8_27b_hbm',None)]},
        adoption=False, gates={'exact':'PENDING','latency':'PENDING','area':'PENDING',
            'route':'PENDING','SS_FF':'PENDING','composed_gain_ge_1pct':'PENDING'})

if __name__ == '__main__':
    print(json.dumps(price(),indent=2))
