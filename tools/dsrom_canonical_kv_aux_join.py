#!/usr/bin/env python3
"""Join frozen S81 ownership metadata; propose bounded auxiliary storage only."""
import argparse
import hashlib
import json
from pathlib import Path

NAMES = ('inventory.json', 'providers.json', 'stage_map.json',
         'auxiliary_obligations.json', 'mapping_verdict.json', 'binding.json',
         'strict_model.json', 'strict_binding_result.json', 'previous_service_ledger.json')


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def load_inputs(directory):
    origins = json.loads((directory / 'origins.json').read_text())
    require(set(origins) == set(NAMES), 'incomplete input closure')
    data = {}
    for name in NAMES:
        raw = (directory / name).read_bytes()
        require(hashlib.sha256(raw).hexdigest() == origins[name]['sha256'], 'source identity: ' + name)
        require(len(origins[name]['source_commit']) == 40, 'unbound origin: ' + name)
        data[name] = json.loads(raw)
    return data, origins


def marker_proposal(inventory, aux):
    norm = [t for t in inventory['dedicated_storage']['global_tensors'] if t['tensor'] == 'norm.weight']
    require(len(norm) == 1, 'unique norm storage required')
    norm = norm[0]
    require(norm['pairs'] == 1 and norm['word_data_bits'] == 256 and norm['secded_bits'] == 0,
            'unsupported norm storage contract')
    require(norm['pair_start'] == 5050 and norm['words'] == 320, 'norm owner/range changed')
    names = ('image_end', 'image_newline', 'image_start')
    offset = norm['words']
    rows = []
    for name in names:
        tensors = [t for t in aux['tensors'] if t['tensor'] == name]
        require(len(tensors) == 1, 'unique image tensor required')
        t = tensors[0]
        require(t['dtype'] == 'BF16' and t['shape'] == [5120] and t['source_storage_bytes'] == 10240,
                'image source encoding changed')
        words = t['source_storage_bytes'] // (norm['word_data_bits'] // 8)
        rows.append(dict(t, proposed_pair=norm['pair_start'], logical_word_start=offset,
                         logical_word_end_exclusive=offset + words, words=words))
        offset += words
    require(offset <= inventory['rows'], 'proposal exceeds conservative single-leaf word capacity')
    return {'status': 'MODEL_PROPOSAL_NOT_PHYSICAL_PLACEMENT', 'tensors': rows,
            'source_bytes': sum(t['source_storage_bytes'] for t in rows),
            'existing_owner': 'norm.weight', 'owner_home_inherited_only_after_physical_binding': True,
            'existing_norm_word_range': [0, norm['words']], 'combined_end_exclusive': offset,
            'conservative_capacity_words': inventory['rows'], 'new_macros': 0,
            'physical_die': None, 'macro_instance': None, 'read_port_ABI': None,
            'caller_schedule': None, 'latency_cycles': None, 'placement_qualified': False,
            'no_physical_owner_resolution_credit': True}


def compose(data, origins):
    inv, stage, bind = (data[n] for n in ('inventory.json', 'stage_map.json', 'binding.json'))
    verdict, strict, result = (data[n] for n in ('mapping_verdict.json', 'strict_model.json', 'strict_binding_result.json'))
    aux, previous = data['auxiliary_obligations.json'], data['previous_service_ledger.json']
    require((bind['stages'], bind['NP'], bind['BF'], bind['RD'], bind['ROOTD']) == (81, 2417, 519, 64, 128), 'selected contract changed')
    require(inv['layer_dies'] == 324 and inv['ROM_ECC'] is False, 'canonical die/ROM contract changed')
    require(bind['matrix_physical_owner_ranks'] == [0, 1, 2, 3] and
            bind['indexer_projection_policy'] == 'wk and wq_b local on every rank; no canonical-owner multicast',
            'rank projection copies omitted')
    require(verdict['counts'] == {'declarations': 46671, 'placed': 46671} and
            verdict['decoder_matrix_capacity_PASS'] and not verdict['failures'] and
            verdict['row_and_ordered_K_coverage_PASS'] and verdict['word_overlap_PASS'], 'decoder capacity not proven')
    exact_join_names = ('inventory.json', 'providers.json', 'stage_map.json', 'auxiliary_obligations.json')
    for name in exact_join_names:
        require(result['input_sha256'][name] == origins[name]['sha256'], 'strict canonical identity mismatch: ' + name)
    require(result['inventory_bound'] and not result['topology_changed'], 'strict topology not bound')
    require((strict['retained_nodes'], strict['retained_unilateral_nodes'], strict['retained_roots']) == (5090, 384, 128), 'compact census is not actual topology')
    require(result['selected_return_contract']['retained_nodes'] == strict['retained_nodes'] and
            bind['return_actual_retained_nodes'] == strict['retained_nodes'] and
            bind['return_actual_retained_storage_bits'] == strict['retained_storage_bits'], 'current return binding inconsistent')
    rank_rows = stage['rank_dies']
    require(len(rank_rows) == 324 and len({r['die_id'] for r in rank_rows}) == 324 and
            {(r['stage'], r['rank']) for r in rank_rows} == {(s, r) for s in range(81) for r in range(4)}, 'incomplete rank ownership')
    providers = data['providers.json']
    require(len(providers) == 80 and {(p['layer'], p['kind']) for p in providers} ==
            {(l, k) for l in range(40) for k in ('HE', 'CROM')}, 'incomplete provider inventory')
    for p in providers:
        require(p['stage'] == stage['provider_homes'][str(p['layer'])] and 0 <= p['stage'] < 81,
                'provider home mismatch')
        require(len(p['pairs']) == p['banks'] and len(set(p['pairs'])) == p['banks'] and
                all(0 <= pair < inv['pairs_per_rank_die'] for pair in p['pairs']), 'invalid provider pairs')
    scan_homes = set(stage['scan_service_homes'].values())
    require(all(0 <= s < 81 for s in scan_homes), 'invalid scan home')
    die_ledger = []
    for r in rank_rows:
        pp = [p for p in providers if p['stage'] == r['stage']]
        pair_list = [pair for p in pp for pair in p['pairs']]
        require(len(pair_list) == len(set(pair_list)), 'provider overlap at die')
        die_ledger.append(dict(r, providers=[{'layer': p['layer'], 'kind': p['kind'], 'pairs': p['pairs'],
                           'banks': p['banks'], 'useful_word_bits': p['useful_word_bits'],
                           'words_per_bank': p['words_per_bank']} for p in pp],
                           indexer_projection_policy=bind['indexer_projection_policy'],
                           proposed_KV_stacks=4 if r['stage'] in scan_homes else 1,
                           actual_KV_state_bytes_per_user=None, other_live_bytes=None,
                           usable_bytes_per_stack=None, service_ports_bytes_per_cycle=None,
                           shoreline_tracks=None, service_area_mm2=None, clock_power_W=None))
    require(len(aux['tensors']) == 2667 and len({t['tensor'] for t in aux['tensors']}) == 2667 and
            sum(t['source_storage_bytes'] for t in aux['tensors']) == aux['storage_bytes'], 'auxiliary census mismatch')
    require(aux['no_omission_credit'] and not aux['placement_qualified'], 'unexpected auxiliary qualification')
    groups = {}
    for t in aux['tensors']:
        key = t['tensor'].split('.')[0]
        g = groups.setdefault(key, {'tensors': 0, 'source_bytes': 0})
        g['tensors'] += 1
        g['source_bytes'] += t['source_storage_bytes']
    return {'schema': 'dsrom.s81.canonical_kv_aux_join.v1', 'status': 'CANONICAL_METADATA_JOIN_ONLY',
            'origins': origins, 'selected': {'stages': 81, 'rank_dies': 324, 'NP': 2417, 'BF': 519, 'RD': 64, 'ROOTD': 128},
            'decoder_capacity': verdict['counts'], 'decoder_matrix_capacity_PASS': True,
            'strict_return': strict,
            'strict_verdict_lineage': {'original_hash': result['input_sha256']['mapping_verdict.json'],
                                      'current_hash': origins['mapping_verdict.json']['sha256'],
                                      'byte_identical': result['input_sha256']['mapping_verdict.json'] == origins['mapping_verdict.json']['sha256'],
                                      'current_binding_explicitly_joins_original': bind['return_binding_note']},
            'historical_compact_nodes_superseded': 4706,
            'native_component_area_join': {'source_native_mapping': previous['return_inventory']['source_native_mapping'],
                                         'qualification': previous['return_inventory']['qualification'],
                                         'native_node_local_port_bits': previous['return_inventory']['native_node_local_port_bits'],
                                         'historical_compact_projection_not_actual_area': previous['return_inventory'],
                                         'actual_unilateral_and_root_full_mapping_mm2': None,
                                         'matched_containment_required_before_area_delta': True},
            'per_rank_die': die_ledger, 'provider_rank_bindings': sum(len(r['providers']) for r in die_ledger),
            'provider_storage_already_in_canonical_inventory': True, 'extra_provider_area_charge_mm2': 0,
            'scan_home_is_provisional': stage['scan_home_is_provisional_not_source_service_binding'],
            'provisional_stack_rule_total': sum(r['proposed_KV_stacks'] for r in die_ledger) + inv['head_dies'] * 4,
            'head_stacks_proposed': inv['head_dies'] * 4, 'KV_capacity_PASS': None,
            'capacity_gate': {'batch': 216, 'context': 1048576, 'required': 'per-die live KV bytes plus other live bytes <= proposed stacks times actual usable stack bytes; busiest-stage latency gate also required'},
            'historical_finite_capture': previous['finite_capture'],
            'historical_service_ports_not_selected_context_qualified': previous['source_capture_ports'],
            'selected_capture_occupancy_and_consumer_deadlines': None,
            'auxiliary': {'groups': groups, 'unqualified_tensors': len(aux['tensors']), 'source_bytes': aux['storage_bytes'],
                          'image_marker_proposal': marker_proposal(inv, aux)},
            'KV_stack_count_adopted': None, 'matched_area_delta_applied_mm2': None,
            'entire_shipped_checkpoint_exactonce_PASS': False, 'physical_launch_allowed': False,
            'new_allocator_run': False, 'original_files_edited': False,
            'next_owner_inputs': {'Arendt': 'accept or reject image storage proposal; retain all MTP/vision/aligner ownership obligations',
                                 'Maxwell': 'bind norm physical die/macro/read ABI and service/shoreline clock/power/port area; matched residual containment',
                                 'Nash': 'actual NP2417 phase writer occupancy, local stage namespace, replica counts and consumer deadlines',
                                 'Claude': 'actual batch216/context1M per-die live KV capacity and busiest-stage latency'}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    data, origins = load_inputs(args.inputs)
    model = compose(data, origins)
    args.out.write_text(json.dumps(model, indent=2, sort_keys=True) + '\n')


if __name__ == '__main__':
    main()
