#!/usr/bin/env python3
"""Price additive reverse endpoints and a disjoint H3 spill extent before RTL."""
import argparse
import gzip
import hashlib
import json
import math
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
H3 = '400d3d0c0f9caaf5e16392b71da21d6a135d3a6d'


def frozen(path):
    raw = subprocess.check_output(['git', 'show', H3 + ':' + path], cwd=ROOT)
    return raw, hashlib.sha256(raw).hexdigest()


def model():
    raw, h3sha = frozen('results/uarch/h3_distributed_norm_endpoint_20261002/Qwen.json.gz')
    h3 = json.loads(gzip.decompress(raw))
    raw, qsha = frozen('tools/qwen_hbm_complete_program.py')
    # Only the allocation function runs, not the program compiler or tensor code.
    namespace = {}
    text = raw.decode()
    exec(text[text.index('def allocation('):text.index('def compile_program(')], namespace)
    raw, cfgsha = frozen('compiler/models/qwen3-8b/config.json')
    allocations = namespace['allocation'](json.loads(raw), tp=2, context=8192)
    extents = []
    for bind in h3['spill_resident_bindings']:
        for rank in bind['rank_group']:
            old = allocations[rank]
            scratch = old['extents'][-1]
            assert scratch == bind['source_extent'] and scratch['name'] == 'activation_scratch'
            required = bind['required_bytes']
            assert required == 32 * 1024**2
            revised = dict(scratch, bytes=max(required, scratch['bytes']))
            residents = old['extents'][:-1] + [revised]
            for left, right in zip(residents, residents[1:]):
                assert left['base'] + left['bytes'] <= right['base']
            end = revised['base'] + revised['bytes']
            striped = ((end + 127) // 128 + 3) // 4 * 128
            assert striped <= old['stack_capacity_bytes']
            assert (striped + 31) // 32 < 2**31
            extents.append({'rank': rank, 'old_extent': scratch, 'candidate_extent': revised,
                'growth_bytes': revised['bytes'] - scratch['bytes'], 'allocated_global_end_bytes': end,
                'worst_stack_allocated_bytes': striped, 'stack_capacity_bytes': old['stack_capacity_bytes'],
                'unchanged_co_resident_extents': len(old['extents']) - 1,
                'intersection_count': 0, 'all_extents': residents,
                'site_capacity_admission': 'DISJOINT_ADDRESS_CAPACITY_ONLY_NOT_RESIDENCE_OR_PHY',
                'address_recipe': {'stack': '(global_byte//128)%4',
                    'local_sector': '4*(global_byte//512)+(global_byte%128)//32',
                    'word_bit': '(global_byte%32)*8', 'system_sector_bits': 34,
                    'native_local_sector_bits': 31, 'local_upper3_zero_proven_for_extent': True},
                'H3_SM_regions': [{'SM': p['SM'], 'base': revised['base'] + p['SM'] * 1048576,
                    'bytes': p['spill_bytes']} for p in h3['peaks'] if rank in p['rank_group']],
            })
    base_path = ROOT/'results/uarch/qwen_hbm_retirement_r15_20261002/cost_before_build_r6.json'
    base = json.loads(base_path.read_text())
    # One sector-store per finite SER client. No old-register replacement refund.
    sector_bits = 4 * (1 + 12 + 5)
    spill_bits = {'vector_buffer': 4096, 'immutable_identity': 192, 'global_byte_base': 37,
                  'physical_tag_and_beat_per_sector': 16 * 17, 'capture_mask': 16,
                  'state': 5, 'issue_cursor': 5, 'reverse_cursor': 5,
                  'captured_count': 5, 'fault_cancel_mode_partial': 4}
    extra_ff = sector_bits + sum(spill_bits.values())
    buffers = 0
    n = extra_ff
    while n > 1:
        n = math.ceil(n / 16); buffers += n
    compare_bits = 4 * 17 + 4 * 16
    mux_bits = 2 * extra_ff + 17 * 15
    area = (extra_ff * base['FF_area_um2'] + mux_bits * base['mux_bit_area_um2'] +
            compare_bits * .2 / .5 + 2 * buffers * base['BUF_area_um2'] / .5) / 1e6
    return {'status': 'MODEL_READY_ADDITIVE_SOURCE_PREPARATION_NOT_RUNTIME_OR_PHY_ADMITTED',
        'source_pins': {'H3_commit': H3, 'H3_Qwen_gzip_SHA256': h3sha,
            'allocation_tool_SHA256': qsha, 'config_SHA256': cfgsha,
            'retained_r15_cost_SHA256': hashlib.sha256(base_path.read_bytes()).hexdigest()},
        'retained_r15_cost_path': str(base_path.relative_to(ROOT)),
        'extent_candidates': extents, 'extent_adopted': False,
        'reverse_repairs': ['Sector grant requires actual retire handshake plus exact saved physical tag/beat',
            'Late cancellation sampled before stored completion; held retirement stays immutable',
            'Live reader caller collision backpressures; same-edge cancellation cannot earn normal reverse quorum'],
        'sector_store_added_bits': sector_bits, 'spill_adapter_added_bits': spill_bits,
        'total_added_FF_bits_per_die': extra_ff, 'added_compare_bits': compare_bits,
        'added_mux_bit_equivalents': mux_bits, 'clock_buffers': buffers, 'reset_buffers': buffers,
        'additional_placed_proxy_mm2_per_die': area,
        'cell_source_SHA256': base['cell_source_SHA256'], 'mapped_SSFF_area': False,
        'replacement_credit_mm2': 0, 'extra_memory_ports': 0, 'extra_PHY_ports': 0,
        'spill_resource': {'vectors_inflight_per_rank': 1, 'sectors_per_vector': 16,
            'request_LEN': 1, 'native_LEN_bits': 6, 'native_BEAT_bits': 5, 'native_TAG_bits': 16,
            'sector_bytes': 32, 'buffer_bits': 4096, 'request_bits': 455,
            'owned_return_bits': 467, 'reverse_bridge_bits': 404,
            'existing_weight_transport_unchanged': True, 'weight_bandwidth_credit': 0,
            'selected_spill_throughput': 'Serialized sectors; explicitly not free32SM overlap or bulk weight service',
            'read_retirement': 'Capture all accepted sectors, hold vector until actual consumer acceptance, then reverse each saved physical ownership and wait validated grant',
            'write_retirement': 'Actual native backing-visible owned event then reverse credit then validated held grant; advance only after grant',
            'cancel': 'Stop new issues, drain accepted sector; held cancelled result accepted before read reverse; committed partial write persists and is reported',
            'reset': 'Bounded fixture coordinated reset only; external stale-wire/reset fence remains actual-provider contract, not a timer'},
        'latency': {'issue_readiness': 'max(request bridge room, queue/scan/refresh/bank readiness, WR reservation and RAW dependencies)',
            'read_vector': '16 actual sector returns -> consumer acceptance ->16 serialized reverse/validated-grant joins',
            'write_vector': '16 serialized actual column/backing-visible/reverse/grant joins',
            'reverse_lookup_CORE_edges': 12, 'CDC': 'Retained38FAST route plus two finite FIFO crossings per direction, phase/readiness measured',
            'RMW': 'Retained actual RMW read -> merge -> reverse validated grant -> WR; no serial latency-floor summation',
            'fixture': 'External25/8CORE delay remains unqualifiedPHY test abstraction'},
        'slot': {'retained_r15_margin_mm2_per_stack': base['geometry']['area_budget_margin_mm2_per_stack'],
            'client_logic_extra_mm2_per_die': area,
            'placement_or_route_fit': False, 'reason': 'SER endpoint placement/internal pins must bind context; aggregate slot margin is not a placement proof'},
        'RF_internal_branch': 'H3 r22 review belongs Maxwell; no change/free corridor credit here',
        'full_engine_or_token_admission': False, 'jobs': [], 'compile_or_PR': False}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args(); result = model()
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2, sort_keys=True)+'\n')
    print(json.dumps({'added_FF_bits': result['total_added_FF_bits_per_die'],
        'additional_mm2': result['additional_placed_proxy_mm2_per_die'], 'spill_extent_count': len(result['extent_candidates'])}))
