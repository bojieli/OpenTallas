#!/usr/bin/env python3
"""Additive source-pinned Q2 transport throughput prerequisite; no hardware admission."""
import argparse
import hashlib
import json
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / 'results/uarch/qwen_rom_transport_concurrency_20261002/inputs'
MANIFEST_SHA = '60fe34a295d5141b6fd615e85eeaed1772b9671cf6f44ad8bc117d42fcec61dc'

def ceildiv(n, d):
    if n < 0 or d <= 0:
        raise ValueError('nonnegative demand and positive capacity required')
    return (n + d - 1) // d

def inputs():
    raw = (INPUT / 'manifest.json').read_bytes()
    if hashlib.sha256(raw).hexdigest() != MANIFEST_SHA:
        raise ValueError('input manifest changed')
    rows = json.loads(raw)
    data = {}
    for r in rows:
        b = (INPUT / r['snapshot']).read_bytes()
        if hashlib.sha256(b).hexdigest() != r['sha256']:
            raise ValueError('source snapshot changed')
        data[r['snapshot']] = b
    return data, rows

def size(layer_bytes, window_cycles, service_cycles, stacks=4, sector_bytes=32,
         burst_sectors=32, owner_ii=12, return_ii=7, command_per_sector=1):
    """Necessary steady-state bounds, not a finite startup/completion guarantee."""
    if min(layer_bytes, window_cycles, service_cycles, stacks, sector_bytes,
           burst_sectors, owner_ii, return_ii, command_per_sector) <= 0:
        raise ValueError('positive inputs required')
    if layer_bytes % sector_bytes or layer_bytes % (sector_bytes * stacks):
        raise ValueError('require exact equal-stack sector partition for this bound')
    sectors = layer_bytes // sector_bytes
    per_stack = sectors // stacks
    credits = ceildiv(sectors * service_cycles, window_cycles)
    stack_credits = ceildiv(per_stack * service_cycles, window_cycles)
    return dict(layer_bytes=layer_bytes, conditional_window_cycles=window_cycles,
        sectors=sectors, payload_bytes_per_cycle_exact=str(Fraction(layer_bytes, window_cycles)),
        sector_rate_exact=str(Fraction(sectors, window_cycles)),
        minimum_sector_credits_global=credits,
        balanced_minimum_sector_credits_per_stack=stack_credits,
        balanced_burst_records_per_stack=ceildiv(stack_credits, burst_sectors),
        sector_return_lanes_global=ceildiv(sectors, window_cycles),
        balanced_sector_return_lanes_per_stack=ceildiv(per_stack, window_cycles),
        source_nonpipelined_owner_engines_per_stack=ceildiv(per_stack * owner_ii, window_cycles),
        source_nonpipelined_return_engines_per_stack=ceildiv(per_stack * return_ii, window_cycles),
        command_lanes_per_stack=ceildiv(per_stack * command_per_sector, window_cycles),
        fill_64B_lanes_global=ceildiv(layer_bytes, 64 * window_cycles),
        balanced_fill_64B_lanes_per_stack=ceildiv(layer_bytes, stacks * 64 * window_cycles),
        source_floor_cycles=dict(command=per_stack * command_per_sector,
            owner=per_stack * owner_ii, return_arb=per_stack * return_ii),
        single_II1_lane_per_stack_floor_cycles=per_stack,
        burst_allocation_records=ceildiv(sectors, burst_sectors),
        source_sector_command_count=sectors * command_per_sector)

def build():
    data, receipts = inputs()
    g0 = json.loads(data['g0.json']); c = json.loads(data['candidate.json'])
    owner = data['ot_hbm_r14_tag_owner.sv'].decode()
    command = data['ot_hbm_causal_command_provider.sv'].decode()
    pkg = data['ot_hbm_r14_pkg.sv'].decode()
    assert 'if(delay==11)' in owner and 'if(return_arb==6)' in command
    assert 'assign ir=(state==0)&&!held&&!av;' in owner
    assert 'cursor<=cursor+1' in command and 'identity_t; //192' in pkg
    assert g0['storage']['layer_bytes'] == 4194304
    assert c['fixed_candidate']['outstanding_sectors_per_stack'] == 512
    scenarios = {}
    for name, s in g0['refill']['source_timing_scenarios'].items():
        r = size(4194304, 4668, s['cycles_at_1p2GHz'],
                 command_per_sector=3 if name == 'row_conflict' else 1)
        r.update(source_service_cycles=s['cycles_at_1p2GHz'],
                 sixteen_burst_credits_satisfy_service_only_bound=r['balanced_minimum_sector_credits_per_stack'] <= 512)
        if name == 'row_conflict_plus_refresh':
            r['command_floor_scope'] = 'RD-only floor; PRE/ACT/REF commands and refresh stalls remain additional.'
        scenarios[name] = r
    lanes = scenarios['row_hit']['balanced_sector_return_lanes_per_stack']
    # Conditional structurally priced interface, not implemented/selected. Conservatively retain
    # 12 owner and 7 arbitration stages; do not equate pipeline latency with II.
    terms = dict(burst_record_payload_bits=4 * 16 * (192 + 12 + 32),
        sector_response_payload_bits=4 * 16 * 32 * 256,
        assembly_payload_bits=4 * 16 * c['assembly']['payload_bits_per_slot'],
        conditional_owner_pipeline_bits=4 * lanes * 12 * 465,
        conditional_return_pipeline_bits=4 * lanes * 7 * 471,
        conditional_command_output_bits=4 * lanes * 339,
        conditional_reverse_credit_echo_output_bits=4 * lanes * 465)
    unit = Fraction(2916, 10000) / Fraction(1, 2) / 1000000
    priced = {k:dict(bits=v, FF50_proxy_mm2=float(v * unit)) for k,v in terms.items()}
    return dict(schema='opentallas.qwen-rom-transport-concurrency.v1',
        source_receipts=receipts, tool_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        status='BLOCKED_ACTUAL_WINDOW_AND_THROUGHPUT_PROVIDER', build_admitted=False,
        hardware_implemented=False, calibrated_rate=False, full_token_repeat=False,
        reference=dict(cycles=4668, scope='Original TP4 SU64 context-zero host-serviced reference only; not an actual context-8K prefetch window.',
            source='dimension.py:size cycle_reference_scope', actual_context8K_available_prefetch_cycles=None),
        clock_scope='Cycles interpreted in one prospective 1.2GHz streaming domain; actual CORE/PHY clock ratios and CDC are unbound. Timing scenarios are legacy analytical assumptions, not measured bounds.',
        traffic=dict(existing_bytes_per_die_token=150994944, layer_bytes=4194304,
            layers=36, incremental_bulk_bytes=0, accounting='Price acceptance/visibility/stalls against existing read charge once. Never sum 36 serialized refills plus the already charged 144MiB bandwidth term.'),
        scenarios=scenarios,
        finite_candidate=dict(id='c88cf277c-16bursts-stack-32sectors-NOT-PRODUCT',
            equal_stack_split_proven=False, credits_per_stack=512,
            source_owner_floor_cycles=393216, source_return_arb_floor_cycles=229376,
            source_rowhit_command_floor_cycles=32768,
            shared_owned_data_and_credit_echo_floor_cycles=65536,
            queue_capacity_admits_target_throughput=False,
            lower_bounds_not_additive='max of independent throughput bounds; exact dependency calendar needed for startup/drain and shared stalls'),
        conditional_successor_interface=dict(id='Q2-conditional-balanced-throughput-interface-NOT-SELECTED',
            sector_lanes_per_stack=lanes, owner_lookup_accepts_per_stack_cycle=lanes,
            returned_sectors_per_stack_cycle=lanes, rowhit_RD_commands_per_stack_cycle=lanes,
            rowconflict_PRE_ACT_RD_command_lanes_per_stack=scenarios['row_conflict']['command_lanes_per_stack'],
            fixed_four_stacks=True, PCs_per_stack=32,
            payload_bits_per_cycle=4 * lanes * 256,
            owned_data_boundary_bits_per_cycle=4 * lanes * 465,
            reverse_credit_echo_boundary_bits_per_cycle=4 * lanes * 465,
            owned_boundary_bits_per_cycle=2 * 4 * lanes * 465,
            reverse_credit_input_bits_per_cycle=4 * lanes * (192 + 12 + 5 + 1),
            reverse_credit_rule='Source grant_valid credit echo shares owned output with returned data. Sustain eight data plus eight credit echoes/stack/cycle using separately priced outputs or sixteen shared lanes; no free echo/retirement bandwidth.',
            command_boundary_bits_per_cycle=4 * lanes * 339,
            balanced_fill_lanes_per_stack=4, addressed_fill_bits_per_cycle=16 * 1048,
            unchanged_source_cannot_supply_interface=True,
            assembly_issue='Four 64B destination writes/stack/cycle need independently selected tile macros, mask/codec visibility and read/write collision ownership; bulk SRAM capacity alone does not prove ports.',
            burst_rule='1024B descriptor can amortize allocation only; source enqueues and commands sectors serially. No burst service latency or aggregate HBM bandwidth transfer.',
            PC_rule='pc_of/bank_of and legal shoreline command lanes must bind actual addresses. A PC-bank ownership plan must prove hot-PC conflicts and allocation/lookup/commit arbitration; equal stack traffic is a conditional bound.'),
        area_structural_price=priced,
        area_FF50_proxy_sum_mm2=float(sum(terms.values()) * unit),
        area_proxy_provenance='area_proxy.py:timers .2916um2/bit at .50 occupancy; inherited area-only proxy, not synthesis or SS/FF closure.',
        mux_demux=dict(return_32_to_8_bit_mux_equivalents=4 * lanes * 31 * 471,
            owner_32_to_8_bit_mux_equivalents=4 * lanes * 31 * 465,
            command_32_to_8_bit_mux_equivalents=4 * lanes * 31 * 339,
            scope='Direct replicated 32:1 binary selection estimate, not optimized shared crossbar or placement. Separate from staged data bits.',
            owner_context_storage='Retain existing 32x128x256 SRAM/stack and tag/CAM/seen state; additional ports/replicas/bank conflicts unpriced, no replacement credit.',
            required_fanout='32 candidate PC heads per output lane; grants and decoders must arbitrate exclusive source/destination ownership.', cell_area_mm2=None),
        local_window=dict(existing_tile_capacity_bytes=12582912,
            two_unpadded_layer_windows_bytes=8388608,
            source_padded_local_words_per_tile=44,
            one_padded_window_bytes=1536 * 44 * 64,
            two_padded_windows_bytes=2 * 1536 * 44 * 64,
            padding_traffic_policy='44 words from 2*ceil(512/48)*2; padded addresses do not add HBM bytes unless actual masked-fill schedule requests them.',
            capacity_only=True, addressed_two_window_and_tail_lease_allocation_proven=False,
            prefetch_rule='Derive available cycles from accepted prefetch to dependent local-read permission in the actual ctx8K graph. Do not invent full-layer overlap or prefetch past unavailable owners.'),
        exactness_contract=['Identity192 plus physical tag and beat survive unchanged; TP4 versus source die1-bit mapping requires actual provider binding.',
            'Every beat validated against immutable base/LEN/PC, allocation generation and duplicate mask.',
            'Pipeline concurrent seen/remaining_PC updates require same-tag interlocks or merged atomic updates; duplicate/stale beats fault.',
            'Hold output under backpressure; reserve output/assembly/write credits before accepting commands.',
            'Do not reuse physical tag on lookup/output delivery: quarantine through matching destination-visible completion and validated reverse credit.',
            'Raw E4M3 byte codes retained; BF16 read-window path cannot substitute without exact repack proof.',
            'Tail writeback publication and local-window reader drain are distinct fences; no forced K RMW on every token.'],
        mandatory_missing_costs=['actual decoder/CAM/update logic and additional SRAM ports/replicas',
            'clock/hold/control/CDC and quarantine storage', 'route tracks, legal shoreline widths and mux area',
            'tile write ports/raw-code codec and visibility latency', 'actual context8K dependency window'],
        measured_or_physical_credit=False)

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--result',type=Path,required=True)
    a=ap.parse_args();r=build();a.result.parent.mkdir(parents=True,exist_ok=True)
    with a.result.open('x') as f: json.dump(r,f,sort_keys=True,indent=2);f.write('\n')
    print(json.dumps(dict(status=r['status'], row_hit=r['scenarios']['row_hit'], area_proxy=r['area_FF50_proxy_sum_mm2']),sort_keys=True))

if __name__ == '__main__': main()
