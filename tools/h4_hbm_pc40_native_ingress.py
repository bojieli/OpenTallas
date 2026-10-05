#!/usr/bin/env python3
"""Actual captured-source ingress for the default-off PC40 RF bridge.

No arithmetic execution: payload is the released producer output, not FMAX's
oracle. Allocation and entering leases are supplied by the system scheduler.
"""
import argparse
import hashlib
import json
from pathlib import Path
import h4_hbm_pc40_physical_ack_r3 as B

VERSION = 'Qwen.39.L0.d0.gu_post.49'
GATE_SHA = '46e599ee3d76c224d688966baecfeee2f55400b80398cd71c3b918217ad0b8e0'
CAPTURE_SHA = '2758204266ef3f9cb5471108b0d3e4a5fb93ea91f73bb41c2cf30ad95543ca83'


def model(wait_edges=4, period_ns=1 / 1.2):
    if type(wait_edges) is not int or wait_edges < 1 or period_ns <= 0:
        raise ValueError('positive eligibility and source clock sensitivity')
    base = B.compose(wait_edges=wait_edges, period_ns=period_ns)
    # Three K64/N72 metadata words; 64 payload words. No extra RF macros.
    bits = 67 * 72
    mux_bits = 4096 + 46 + 9 + 1
    gate_eq = 134 * 768 + bits * 3 + mux_bits * 3 + 55 * 3 + 256
    # Same prospective NAND-equivalent/FF screens as the antecedent; no net
    # replacement of previously counted context: these are NEW ingress seats.
    cell_um2 = bits * 1.134 + gate_eq * .0648 + 76 * 1.36
    edges = 1 + wait_edges + 1 + 1 + 1 + wait_edges
    return dict(schema='opentallas.pc40.native-ingress.v1',
        antecedent=base, source_version=VERSION, source_RFslot=38,
        new_protected_bits=bits, new_payload_bits=64*72,
        new_metadata_bits=3*72, raw_metadata_used_bits=181,
        replicas_selected=1, replicas_full32SM=32,
        MACs_per_cycle=0, arithmetic_callbacks=0,
        ports=dict(ingress_bytes_per_accept=512, RF_write_bytes_per_accept=512,
                   physical_mirror_bytes_per_accept=1024, RF_read_bytes_per_response=1024,
                   input_boundary_bits=4096+46+128+3,
                   added_RF_write_mux_bits=mux_bits, ACK_match_bits=55,
                   source_release_boundary_bits=56),
        routing=dict(lower_parallel_signal_tracks=4096+46+128+3+56,
                     actual_channel_capacity=None, actual_route_fit=False),
        gate_equivalents_ASSUMED=gate_eq, cell_um2_ASSUMED=cell_um2,
        footprint_mm2_50pct_ASSUMED=cell_um2/500000,
        full32SM_extra_mm2_ASSUMED=32*cell_um2/500000,
        conditional_publish_to_issue_edges=edges,
        selected_total_conditional_edges=edges+base['calendar']['cycles_conditional'],
        selected_total_conditional_ns=(edges+base['calendar']['cycles_conditional'])*period_ns,
        eligibility_assumption='each dependency-ready request serviced within wait_edges; emitted whole-program bound required',
        clock='same clk as source/W4/W6; 1.2GHz prospective SS/FF target, not measured',
        CDC_added=0, CDC_reason='no asynchronous port selected inside ingress; system crossings external',
        slot_fit=None, loaded_SSFF=False, whole_token_latency_ns=None,
        source_lifetime='RF38 lease retained after selected C0 done; release only actual caller matching owner46+slot38',
        reset='accepted debt faults and stays owned; cold POR is not a production recovery proof',
        once_only='replace seed fixture with new protected ingress and write mux; retain R3/W4/W6 costs once',
        functional_source_preparation=True, physical_admission=False)


def packet(payload_dir, allocation, leases):
    """Bind an actual source version, real scheduler leases and private IDs.

    A valid Boolean from a testbench is not a production lease snapshot. The
    caller supplies concrete lease IDs and the captured source version/home.
    """
    p = Path(payload_dir)
    capture_bytes=(p/'native_capture.json').read_bytes()
    if hashlib.sha256(capture_bytes).hexdigest()!=CAPTURE_SHA:
        raise ValueError('released actual capture identity')
    capture = json.loads(capture_bytes)
    gate = (p/'gate.bin').read_bytes()
    if len(gate) != 512 or hashlib.sha256(gate).hexdigest() != GATE_SHA:
        raise ValueError('released actual gate bytes')
    if capture['native_PC'] != 40 or capture['actual_gate_owner']['source_key'] != ['RF',0,0,38]:
        raise ValueError('actual native source home')
    if capture['actual_gate_owner']['lease'] != 'value:'+VERSION:
        raise ValueError('actual native source version')
    widths = dict(physical_PC=7, client=3, original_tag=32, generation=4,
                  native_tag=64, native_generation=64)
    for name, width in widths.items():
        v = allocation[name]
        if type(v) is not int or not 0 <= v < 2**width:
            raise ValueError('allocation width '+name)
    if allocation['client'] != 0 or allocation.get('live_namespace_reserved') is not True:
        raise ValueError('actual C0 client0 allocation reservation')
    if leases.get('source_version') != VERSION or leases.get('source_home') != ['RF',0,0,38]:
        raise ValueError('source lease/home join')
    if not leases.get('source_lease') or not leases.get('entering_snapshot_source'):
        raise ValueError('missing actual entering lease snapshot')
    workspace = leases.get('workspace', [])
    if [r.get('slot') for r in workspace] != [17,18,19] or any(
            not r.get('lease') or r.get('reserved') is not True or r.get('prior_live') is not False for r in workspace):
        raise ValueError('finite reserved workspace lease join')
    owner = (allocation['physical_PC'] << 39 | allocation['client'] << 36 |
             allocation['original_tag'] << 4 | allocation['generation'])
    return dict(schema='opentallas.pc40.native-ingress-packet.v1', native_PC=40,
                rank=0, SM=0, source_version=VERSION, source_RFslot=38,
                owner46=owner, native_tag64=allocation['native_tag'],
                native_generation64=allocation['native_generation'], leases=leases,
                gate_sha256=GATE_SHA, payload_hex=gate[::-1].hex(),
                executed_fragment=['BITCAST_U','XOR_sign','BITCAST_F','FMAX_minus87','FMIN_plus88'],
                result_binding='PC40.exp.step2 input; 128 little-endian F32 lanes',
                RF19_binding='PC40.exp.step0 FMAX output, not FMIN output',
                completion_scope='fragment only, not complete SILU_GATE PC40',
                oracle_payload_used=False, HBM_commands=0,
                hardware_publication_performed=False, full_token_executed=False)


if __name__ == '__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--model',action='store_true')
    ap.add_argument('--payload',type=Path);ap.add_argument('--allocation',type=Path)
    ap.add_argument('--leases',type=Path);ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args()
    r=model() if a.model else packet(a.payload,json.loads(a.allocation.read_text()),json.loads(a.leases.read_text()))
    with a.out.open('x') as f:json.dump(r,f,indent=2,sort_keys=True);f.write('\n')
