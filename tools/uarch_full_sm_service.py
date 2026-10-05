#!/usr/bin/env python3
"""Default-off finite conventional-GPU service extension of uarch_model.
Original unified-model arithmetic and all ROM paths remain byte-identical.
Token composition consumes an explicit ordered service-event ledger; no rate credit.
"""
import ast
import argparse
import hashlib
import json
import math
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
PREREQ = 'results/uarch/full_sm_actual_parent_route_20261002/'

def digest(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()

def model(enabled=False, events=()):
    # Import only on opt-in: normal unified model does not select this service.
    if not enabled:
        return dict(enabled=False, build_GO=False, rate_credit=False)
    tree = ast.parse((ROOT / "tools/uarch_model.py").read_text())
    dff = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "DFF_UM2" for t in n.targets))
    source = json.loads((ROOT / (PREREQ+'model.json')).read_text())
    outline = json.loads((ROOT / (PREREQ+'priced_full_SM_area_outline.json')).read_text())
    ports = dict(RF_read_A=512, RF_read_B=512, RF_logical_write=512,
                 RF_physical_write_A=512, RF_physical_write_B=512,
                 scratch_read=64, scratch_write=64)
    # All values are payload plus address/control incidences, not unique-net claims.
    boundaries = dict(RF_to_SIMD=8192+2, SIMD_to_RF=4096+9+2,
                      host_to_RF=4096+9+2, RF_to_host=8192+2,
                      host_to_scratch=512+10+3, scratch_to_host=512+2,
                      SIMD_command=27+1+2, SIMD_completion=3, host_RF_read_request=20, SIMD_RF_read_request=20,
                      RF_host_write_ACK=2, RF_SIMD_write_ACK=2)
    # Conservative full-page read mux: 4:1 of 256 bits per bank and copy.
    mux_bits = 16*2*256*3
    regs = 8192+4096+512+64
    models = {}
    for name in ('Qwen', 'DS'):
        r = source['models'][name]['nonmatrix_reservation']
        assert (r['RF_banks'], r['RF_pages'], r['RF_operand_read_replicas'], r['SIMD_FP32_lanes']) == (16,4,2,128)
        o = outline['models'][name]
        demand = sum(boundaries.values())
        extra_logic = regs*dff + mux_bits*.2 + 4096*.2
        area = r['RF_mux_cell_proxy_um2']+r['SIMD_cell_proxy_um2']+extra_logic
        box = o['service_logic_50pct_rectangle_um']
        capacity = (box[2]-box[0])*(box[3]-box[1])*.5
        required_h = math.ceil((2*area/(box[2]-box[0]))/2.16)*2.16
        proposed_box = [box[0],box[1],box[2],box[1]+required_h]
        models[name] = dict(SM_replicas=32, RF_banks=16, RF_pages_per_bank=4,
            RF_read_copies=2, RF_macros=128, RF_logical_bytes=262144, RF_physical_bytes=524288,
            RF_vector_address_bits=9, RF_address='vector[8:7]=page;vector[6:0]=row;lane[6:3]=bank;lane[2:0]=word',
            scratch_macros=2, scratch_bytes=65536, scratch_address='10-bit 64-byte beat;low5 byte bits implicit zero',
            ports_bytes_per_cycle=ports, boundaries_bits_per_cycle=boundaries,
            boundary_track_reservation_upper=demand, outline_channel_tracks=o['channel_M7_M9_50pct_track_budget'],
            shared_channel_screen=demand<=o['channel_M7_M9_50pct_track_budget'],
            distributed_local_routes_required=True, mux_2to1_bit_equivalents=mux_bits+4096,
            write_demux_enable_loads=128, mirrored_write_data_fanout=8,
            read_page_decode_fanout=32, SIMD_lanes=128, MACs_per_cycle=0,
            operations_per_active_cycle=128, active_compute_ops_per_RF_byte=128/1536,
            sustained_SIMD_ops_per_cycle=128/14, SIMD_issue_interval_cycles=14,
            logic_area_estimate_um2=area, estimate_basis='pinned SIMD proxy plus DFF and 0.2um2/mux-bit analytical proxies; not mapped measurement',
            existing_logic_slot_capacity_um2=capacity, existing_logic_slot_fit=area<=capacity,
            required_logic_slot_area_um2_at50pct=2*area,
            proposed_expanded_logic_rectangle_um=proposed_box,
            expanded_logic_rectangle_inside_existing_outline=proposed_box[3]<=o['element_outline_um'][1],
            SRAM_RF_physical_read_pin_bits=128*256, SRAM_RF_active_read_bits_pc=8192,
            SRAM_RF_active_write_bits_pc=8192, SRAM_RF_address_and_enable_pin_incidences=128*(7+1)*2,
            SRAM_RF_constant_mask_pin_incidences=128*256,
            physical_pin_incidence_is_not_global_unique_track_demand=True,
            scratch_macro_pin_payload_bits_each=256, scratch_macro_address_bits_each=10,
            write_ACK_semantics='registered after acceptance/macro write edge; earliest consumer retirement next edge',
            retained_element_outline_um=o['element_outline_um'], physical_admissible=False,
            read_accept_to_valid_cycles=1, write_accept_to_visible_ack_cycles=0,
            RF_read_issue_interval_cycles=3, RF_write_issue_interval_cycles=2,
            SIMD_accept_to_done_cycles=12, scratch_read_accept_to_valid_cycles=1, scratch_write_accept_to_ack_cycles=0,
            scratch_read_issue_interval_cycles=3, scratch_write_issue_interval_cycles=2,
            max_RF_transactions=1, max_SIMD_transactions=1, max_scratch_transactions=1,
            arbitration='alternating read/write priority at idle; SIMD reserves RF until result ACK; host cannot starve accepted SIMD',
            bank_conflicts='aligned vectors hit each bank once per operand copy; same-bank read/write serialized globally',
            read_lease='all RF banks locked through ready/valid operand consumption; stable registered response',
            downstream_stall_bound='external B cycles per response required by parent; never timeout/drop',
            bound_wait_cycles='host behind SIMD <=14+B; competing host read <=3+B;write <=2+B; arbiter grants alternate',
            arithmetic='existing ot_gpu_fadd/ot_gpu_fmul LAT7; single op RNE, no reassociation or epilogue',
            ROM_transfer=False, Qwen_RF_abstract_qualification=False)
    costs = dict(read=3,write=2,scratch_read=3,scratch_write=2,simd=14)
    elapsed = 0
    priced=[]
    for e in events:
        if e['kind'] not in costs or not isinstance(e['stall_cycles'],int) or e['stall_cycles']<0:
            raise ValueError('finite kind and nonnegative measured/bounded stalls required')
        n=e['count']
        if not isinstance(n,int) or n<0: raise ValueError('invalid count')
        delta=n*(costs[e['kind']]+e['stall_cycles']);elapsed+=delta
        priced.append(dict(**e, service_cycles=delta))
    return dict(schema='opentallas.uarch.full-sm-service.v1', enabled=True, default_enabled=False,
        base_intake='5250fe00a', prerequisite_commit='b655ade45', models=models,
        source_sha256={p:digest(p) for p in ('tools/uarch_model.py', 'tools/uarch_full_sm_service.py',
            PREREQ+'build_readiness.json',PREREQ+'model.json',PREREQ+'priced_full_SM_area_outline.json')},
        clock_GHz=1.2, setup_uncertainty_ps=60, hold_uncertainty_ps=25,
        event_ledger=priced, serialized_service_cycles=elapsed, serialized_service_ns=elapsed/1.2,
        token_composition='add ledger at actual dependencies of Qwen/DS issue graph; counts/stalls absent until parent ledger supplied; do not add on already-priced service edges',
        token_event_ledger_supplied=bool(priced), build_GO=False, rate_credit=False,
        blockers=['actual matrix parent source join','distributed provider routing and source-owned expanded logic slot',
                  'Qwen shallow RF abstract qualification','source-bound complete token event ledger', 'contextual SS setup/FF hold'])

if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--enable',action='store_true')
    p.add_argument('--events',type=Path);p.add_argument('--out',type=Path);a=p.parse_args()
    result=model(a.enable,json.loads(a.events.read_text()) if a.events else ())
    text=json.dumps(result,indent=2,sort_keys=True)+'\n'
    if a.out:
        a.out.parent.mkdir(parents=True,exist_ok=True)
        if a.out.exists() and a.out.read_text()!=text: raise SystemExit('immutable output differs; choose new path')
        a.out.write_text(text)
    else: print(text,end='')
