#!/usr/bin/env python3
"""Join retained interface DATA identities to native child endpoints, without timing credit.

This pure-data consumer does not run STA, compute slack/CPPR, or qualify parent
coverage. A selected structural clock net never stands in for an observed
propagated clock source. Missing parent payload stays UNEXPANDED/NOT_ASSERTED.
"""
import argparse
import csv
import hashlib
import json
import math
import re
from pathlib import Path

ENDPOINTS = 'reference clock_pin clock late_ps early_ps edge'.split()
RELATIONS = 'launch_data_pin capture_data_pin launch_clock_ref setup_capture_clock_ref hold_capture_clock_ref'.split()
STD = ('launch_data_pin capture_data_pin delay status actual_startpoint actual_endpoint check_role '
       'native_std_slack_ps launch_clock_pin launch_clock launch_pin_edge launch_source_pin '
       'launch_source_edge launch_source_insertion_ps capture_clock_pin capture_clock capture_pin_edge '
       'capture_source_pin capture_source_edge capture_source_insertion_ps launch_clock_pin_arrival_ps '
       'capture_clock_pin_arrival_ps').split()
UNEXPANDED = 'UNEXPANDED_CHILD_ETM'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def need(ok, message):
    if not ok:
        raise ValueError(message)


def read_json(path):
    return json.loads(Path(path).read_text())


def artifact(root, corner, suffix):
    """Only declared, hashed retained tables are consumed; paths cannot escape."""
    names = [name for name in corner['files'] if name.endswith(suffix)]
    need(len(names) == 1, 'missing/ambiguous retained artifact: ' + suffix)
    path = (Path(root) / names[0]).resolve()
    need(path.is_relative_to(Path(root).resolve()), 'retained artifact path escapes root')
    need(digest(path) == corner['files'][names[0]], 'retained artifact identity mismatch: ' + names[0])
    return path


def table(root, corner, suffix, header):
    path = artifact(root, corner, suffix)
    with path.open() as stream:
        result = list(csv.DictReader(stream, delimiter='\t'))
    with path.open() as stream:
        actual = next(csv.reader(stream, delimiter='\t'), [])
    need(actual == header, 'wrong retained table header: ' + suffix)
    need(all(set(row) == set(header) and None not in row.values() for row in result), 'truncated retained table: ' + suffix)
    return result


def unique(rows, key, label):
    result = {row[key]: row for row in rows}
    need(len(result) == len(rows), 'duplicate/ambiguous ' + label)
    return result


def root_edge(label, clock):
    if label == clock:
        return 'rise'
    if label == clock + ' fall':
        return 'fall'
    raise ValueError('root does not identify an exact source edge: ' + label)


def native_index(attachment, qualification, maps, witness, view, instances):
    need(qualification.get('schema') == 'opentallas.child_clock_join.v1', 'unsupported native qualification')
    graph = qualification['graph_identity']
    need(qualification.get('status') == 'QUALIFIED_NATIVE_GRAPH' and graph.get('status') == 'PASS', 'native graph unqualified')
    source = qualification.get('source_qualification', {})
    need(source.get('status') == 'PASS' and source.get('basis') in ('opentallas.lec_input_identity.v1', 'opentallas.lec_frontend_replay.v1')
         and re.fullmatch(r'[0-9a-f]{64}', source.get('receipt_sha256', '')), 'native source identity unqualified')
    need(maps.get('schema') == 'opentallas.child_boundary_clock_map.v1' and maps.get('status') == 'COMPLETE_DIRECT_BUFFER_MAPS' and not maps.get('missing'), 'native interface map incomplete')
    need(witness.get('schema') == 'opentallas.child_clock_witness.v1' and witness.get('source_identity_kind') == 'routed_native_netlist_sha256', 'unsupported native witness/source identity')
    need(graph['native'] == witness['native'] == attachment['full_native_graph']['native'], 'native graph/source mismatch')
    need(maps.get('native_netlist_sha256') == graph['native']['6_final.v'], 'boundary map native source mismatch')
    records = unique(attachment['instances'], 'instance', 'attached instance')
    need(instances and len(set(instances)) == len(instances), 'exact unique instance scope required')
    for instance in instances:
        row = records.get(instance, {})
        need(row.get('status') == 'PASS' and row.get('source_qualification') == 'PASS', 'instance is not a source-qualified selected-input join: ' + instance)
        need(row.get('master') == graph['master'] and row.get('clock_pin') == graph['clock_pin'], 'instance/master/clock pin mismatch')
        need(row.get('parent_netlist_sha256') == attachment['parent_netlist']['sha256'], 'instance parent source mismatch')
        need(row.get('parent_top') == attachment['parent_top'], 'instance parent top mismatch')
        need(row.get('parent_clock_net') == attachment['parent_structural_clock_net'], 'selected structural clock net mismatch')
        need(row.get('boundary_map_artifact_sha256') == attachment['boundary_maps']['sha256'], 'instance boundary map identity mismatch')
    result = {}
    for name in ('tt', 'ff'):
        corner = witness['corners'][name]
        selected = attachment['actual_selected_libraries'][name]
        need(selected['sha256'] == graph['corners'][name]['selected_liberty_sha256'], name + ' selected child Liberty mismatch')
        endpoints = unique(table(view, corner, '_endpoints.tsv', ENDPOINTS), 'reference', 'native endpoint')
        roots = table(view, corner, '_roots.tsv', 'clock_edge late_ps early_ps'.split())
        clocks = table(view, corner, '_clocks.tsv', 'clock source_kind source'.split())
        masters = unique(table(view, corner, '_masters.tsv', 'reference clock_pin master'.split()), 'reference', 'native master')
        index = {}
        for direction, group in (('input', 'inputs'), ('output', 'outputs')):
            for bit, rows in maps['maps'][group].items():
                need(rows, 'empty native endpoint map: ' + bit)
                seen = set()
                for row in rows:
                    ref = row['reference']; endpoint = endpoints.get(ref, {}); master = masters.get(ref, {})
                    need(endpoint and master and master['clock_pin'] == endpoint['clock_pin'], 'native endpoint/master absent: ' + ref)
                    need(endpoint['edge'] in ('rise', 'fall') and all(row[k] == endpoint[k] for k in ('clock_pin', 'clock', 'edge')), 'boundary/native clock identity mismatch: ' + bit)
                    need(row['data_pin'].startswith(ref + '/') and row['data_pin'].rsplit('/', 1)[1] in (('D',) if direction == 'input' else ('Q', 'QN')), 'wrong native DATA role: ' + bit)
                    need(row['data_pin'] not in seen, 'ambiguous native DATA endpoint: ' + bit); seen.add(row['data_pin'])
                    sources = [s for s in clocks if s['clock'] == endpoint['clock'] and s['source_kind'] == 'port' and s['source'] == graph['clock_pin']]
                    native_roots = [r for r in roots if r['clock_edge'] in (endpoint['clock'], endpoint['clock'] + ' fall')]
                    need(len(sources) == len(native_roots) == 1, 'missing/ambiguous native root/source: ' + ref)
                    chain = row.get('buffer_chain', [])
                    need(isinstance(row.get('inversions'), int) and row['inversions'] >= 0, 'invalid DATA polarity')
                    need(all(isinstance(b.get('contract'), dict) and b['contract'].get('liberty_sha256')
                         and b['contract'].get('function') in ('A', '!A', "A'")
                         and b['contract'].get('inverted') == (b['contract']['function'] != 'A') for b in chain), 'unhashed/ambiguous native DATA buffer contract')
                    need(row['inversions'] == sum(int(b['contract']['inverted']) for b in chain), 'DATA polarity/chain mismatch')
                    for instance in instances:
                        pin = instance + '/' + bit
                        value = dict(instance=instance, child_master=graph['master'], interface_bit=bit,
                            interface_direction=direction, native_reference=ref, native_master=master['master'],
                            expanded_reference=instance + '/' + ref, native_data_pin=row['data_pin'],
                            expanded_data_pin=instance + '/' + row['data_pin'], native_clock_pin=endpoint['clock_pin'],
                            expanded_clock_pin=instance + '/' + endpoint['clock_pin'], native_clock=endpoint['clock'],
                            native_pin_edge=endpoint['edge'], native_root=native_roots[0]['clock_edge'],
                            native_root_edge=root_edge(native_roots[0]['clock_edge'], endpoint['clock']),
                            native_source=sources[0], data_inversions=row['inversions'], data_buffer_chain=chain,
                            selected_child_liberty_sha256=selected['sha256'], native_netlist_sha256=graph['native']['6_final.v'])
                        if pin in index:
                            need(index[pin]['direction'] == direction and index[pin]['instance'] == instance, 'ambiguous whole-instance interface pin: ' + pin)
                        index.setdefault(pin, dict(direction=direction, instance=instance, endpoints=[]))['endpoints'].append(value)
        result[name] = index
    return result


def parent_corner(witness, folder, name, attachment, instances):
    need(witness.get('schema') == 'opentallas.child_clock_witness.v1', 'unsupported parent witness')
    need(witness['native']['6_final.v'] == attachment['parent_netlist']['sha256'], 'parent observer/attachment source mismatch')
    corner = witness['corners'][name]
    payload = corner.get('parent_boundary_relations', {})
    need(payload.get('std_path_evidence'), 'actual parent original-STD DATA/source payload absent')
    need(payload.get('scope') == 'REGISTER_STARTPOINT_INTERFACE_RELATIONS_BEFORE_CLOCK_DEDUP', 'parent DATA relations were not retained before clock-reference dedup')
    targets = table(folder, corner, '_parent_targets.tsv', ['instance'])
    need(set(instances).issubset({x['instance'] for x in targets}), 'actual parent target scope missing exact instance')
    libraries = read_json(artifact(folder, corner, 'libraries.json'))
    need(libraries.get('status') == 'LOADED' and libraries.get('corner') == name.upper(), 'actual parent corner libraries not consumed')
    inputs_path = artifact(folder, corner, '_inputs.tsv')
    inputs = list(csv.reader(inputs_path.open(), delimiter='\t'))
    need(all(len(row) == 3 for row in inputs), 'invalid actual parent input receipt')
    liberty_inputs = [row for row in inputs if row[0] == 'liberty']
    observed = {row[1]: row[2] for row in liberty_inputs}
    need(len(observed) == len(liberty_inputs), 'ambiguous actual parent library input')
    loaded = {row['path']: row['sha256'] for row in libraries['libraries']}
    need(observed == loaded and len(loaded) == len(libraries['libraries']), 'parent actual library loader/input mismatch')
    selected = attachment['actual_selected_libraries'][name]
    consumed = [row for row in libraries['libraries'] if Path(row['path']).name == Path(selected['path']).name]
    need(len(consumed) == 1 and consumed[0]['sha256'] == selected['sha256'], name + ' child Liberty not actually consumed exactly')
    # STD counts are distinct from the native graph counts; neither may substitute for the other.
    counts_names = [p for p in corner['files'] if p.endswith('parent_boundary_std_' + name + '_counts.tsv')]
    need(len(counts_names) == 1, 'missing/ambiguous original-STD counts')
    counts_path = artifact(folder, corner, 'parent_boundary_std_' + name + '_counts.tsv')
    counts_rows = [line.split('\t') for line in counts_path.read_text().splitlines()]
    need(all(len(row) == 2 for row in counts_rows), 'invalid original-STD counts')
    metadata = dict(counts_rows)
    need(len(metadata) == len(counts_rows), 'ambiguous original-STD counts')
    need(metadata.get('phase') == 'ORIGINAL_STD_BEFORE_ZERO_UNCERTAINTY', 'wrong parent observer phase')
    need(all(int(metadata[k]) == 0 for k in ('errors', 'missing_paths', 'limited_paths')), 'parent DATA observer has ERROR/NO_PATH/LIMIT')
    relations = table(folder, corner, '_parent_relations.tsv', RELATIONS)
    need(relations, 'actual parent DATA relation list empty')
    keys = [tuple(row[k] for k in RELATIONS) for row in relations]
    need(len(set(keys)) == len(keys), 'duplicate parent DATA relation')
    paths = table(folder, corner, 'parent_boundary_std_' + name + '.tsv', STD)
    index = {}
    for row in paths:
        key = row['launch_data_pin'], row['capture_data_pin'], row['delay']
        need(key not in index, 'duplicate/ambiguous original-STD DATA path')
        need(row['status'] == 'EXACT_STD_PATH', 'parent DATA path status ' + row['status'])
        need(row['launch_data_pin'] == row['actual_startpoint'] and row['capture_data_pin'] == row['actual_endpoint'], 'observed DATA identity mismatch')
        need(row['check_role'] == {'max': 'setup', 'min': 'hold'}.get(row['delay']), 'observed DATA check-role mismatch')
        for k in ('native_std_slack_ps', 'launch_source_insertion_ps', 'capture_source_insertion_ps', 'launch_clock_pin_arrival_ps', 'capture_clock_pin_arrival_ps'):
            need(math.isfinite(float(row[k])), 'nonfinite observed parent field: ' + k)
        index[key] = row
    expected = {(r['launch_data_pin'], r['capture_data_pin'], delay) for r in relations for delay in ('max', 'min')}
    need(set(index) == expected, 'missing or unrelated original-STD DATA paths')
    return dict(relations=relations, paths=index,
        endpoints=unique(table(folder, corner, '_endpoints.tsv', ENDPOINTS), 'reference', 'parent endpoint'),
        masters=unique(table(folder, corner, '_masters.tsv', 'reference clock_pin master'.split()), 'reference', 'parent master'),
        clocks=table(folder, corner, '_clocks.tsv', 'clock source_kind source'.split()),
        roots=table(folder, corner, '_roots.tsv', 'clock_edge late_ps early_ps'.split()),
        consumed_child_liberty=consumed[0], metadata=metadata)


def observed_side(context, ref, path, side, data_pin):
    endpoint = context['endpoints'].get(ref, {})
    master = context['masters'].get(ref, {})
    need(endpoint and master and master.get('clock_pin') == endpoint.get('clock_pin'), 'actual parent DATA endpoint/master absent or mismatched')
    need(endpoint['edge'] in ('rise', 'fall'), 'actual parent clock-pin edge absent')
    owner = endpoint['clock_pin'].rsplit('/', 1)[0]
    need(data_pin.rsplit('/', 1)[0] == owner, 'actual parent DATA/clock owner mismatch')
    for key, value in (('clock_pin', endpoint['clock_pin']), ('clock', endpoint['clock']), ('pin_edge', endpoint['edge'])):
        need(path[side + '_' + key] == value, 'actual parent DATA clock reference mismatch')
    source = path[side + '_source_pin']; edge = path[side + '_source_edge']
    need(edge in ('rise', 'fall'), 'actual parent source edge absent')
    sources = [row for row in context['clocks'] if row['clock'] == endpoint['clock'] and row['source'] == source and row['source_kind'] in ('port', 'pin')]
    root_name = endpoint['clock'] if edge == 'rise' else endpoint['clock'] + ' fall'
    roots = [row for row in context['roots'] if row['clock_edge'] == root_name]
    need(len(sources) == len(roots) == 1, 'missing/ambiguous actual parent propagated root/source/edge')
    return dict(reference=ref, instance=owner, master=master['master'], data_pin=data_pin,
                clock_pin=endpoint['clock_pin'], clock=endpoint['clock'], pin_edge=endpoint['edge'],
                source=sources[0], source_edge=edge, root=root_name,
                source_insertion_ps=path[side + '_source_insertion_ps'])


def expand_relation(context, relation, index, attachment, graph):
    source_pin, target_pin = relation['launch_data_pin'], relation['capture_data_pin']
    need(source_pin in index or target_pin in index, 'DATA relation does not touch exact selected child interface bit')
    maximum = context['paths'][source_pin, target_pin, 'max']
    minimum = context['paths'][source_pin, target_pin, 'min']
    records = {}
    for delay, path, capture_ref in (('max', maximum, relation['setup_capture_clock_ref']), ('min', minimum, relation['hold_capture_clock_ref'])):
        sides = {}
        for side, pin, ref, direction in (('launch', source_pin, relation['launch_clock_ref'], 'output'), ('capture', target_pin, capture_ref, 'input')):
            observed = observed_side(context, ref, path, side, pin)
            mapped = index.get(pin)
            if mapped:
                need(mapped['direction'] == direction, 'wrong child interface DATA direction/bit')
                need(observed['instance'] == mapped['instance'] and observed['master'] == graph['master'], 'parent child instance/master mismatch')
                need(observed['clock_pin'] == mapped['instance'] + '/' + graph['clock_pin'], 'actual parent child clock pin mismatch')
                need(all(e['native_root_edge'] == observed['pin_edge'] for e in mapped['endpoints']), 'parent macro clock-pin edge/native input-root edge mismatch')
                sides[side] = dict(kind='NATIVE_CHILD_ENDPOINT_IDENTITIES', parent_observed=observed,
                                   native_endpoints=mapped['endpoints'])
            else:
                # Do not silently relabel another attached child as a parent FF.
                need(not any(pin.startswith(row['instance'] + '/') for row in attachment['instances']), 'unresolved/ambiguous attached child DATA bit')
                sides[side] = dict(kind='OBSERVED_PARENT_NATIVE_ENDPOINT', parent_observed=observed)
        launch_rows = sides['launch'].get('native_endpoints', [sides['launch']['parent_observed']])
        capture_rows = sides['capture'].get('native_endpoints', [sides['capture']['parent_observed']])
        pairs = [dict(launch=a.get('expanded_reference', a.get('instance')), capture=b.get('expanded_reference', b.get('instance')),
                      parent_launch_clock_reference=sides['launch']['parent_observed']['reference'],
                      parent_capture_clock_reference=sides['capture']['parent_observed']['reference'])
                 for a in launch_rows for b in capture_rows]
        records[delay] = dict(check_role=path['check_role'], launch=sides['launch'], capture=sides['capture'],
                              endpoint_identity_pairs=pairs, original_STD_observation=path, timing_computation='NONE')
    return dict(DATA_relation=relation, identities=records, status='NATIVE_IDENTITIES_EXPANDED',
                parent_coverage=UNEXPANDED, qualification='NOT_ASSERTED', additional_clock_or_cppr_credit='NONE')


def consume(attachment_path, qualification_path, maps_path, native_witness_path, native_view,
            instances, parent_witness_path=None, parent_view=None):
    result = dict(schema='opentallas.child_interface_clock_identity_join.v1', status='UNEXPANDED',
                  qualification='NOT_ASSERTED', parent_coverage=UNEXPANDED,
                  source_or_timing_coverage='NOT_ASSERTED', additional_clock_or_cppr_credit='NONE',
                  scope='Exact interface DATA/native endpoint identity composition only; no new timing, source EQ or parent coverage claim',
                  instances=list(instances), reasons=[], corners={})
    try:
        attachment, qualification, maps, native = map(read_json, (attachment_path, qualification_path, maps_path, native_witness_path))
        need(attachment.get('schema') == 'opentallas.external_child_graph_attachment.PREP.v1', 'unsupported selected-input attachment')
        for key, path in (('child_qualification', qualification_path), ('boundary_maps', maps_path)):
            need(digest(path) == attachment[key]['sha256'], key + ' attachment identity mismatch')
        need(digest(native_witness_path) == attachment['full_native_graph']['sha256'], 'native graph attachment identity mismatch')
        need(qualification['boundary_maps']['artifact_sha256'] == digest(maps_path), 'qualified boundary-map artifact mismatch')
        index = native_index(attachment, qualification, maps, native, native_view, instances)
        result['selected_input_context'] = dict(parent_netlist=attachment['parent_netlist'], parent_top=attachment['parent_top'],
            parent_structural_clock_net=attachment['parent_structural_clock_net'],
            structural_net_is_not_propagated_source=True, native_graph_manifest_sha256=digest(native_witness_path),
            native_source=qualification['graph_identity']['native'], child_source_qualification_consumed=qualification['source_qualification'])
        result['native_identity_index'] = index
        if not parent_witness_path:
            result['reasons'].append('actual parent DATA/STD/consumed-Lib/propagated-source witness absent')
            return result
        need(parent_view is not None, 'parent retained artifact root required')
        parent = read_json(parent_witness_path)
        pair_sets = {}
        for name in ('tt', 'ff'):
            try:
                context = parent_corner(parent, parent_view, name, attachment, instances)
                records = [expand_relation(context, row, index[name], attachment, qualification['graph_identity']) for row in context['relations']]
                pair_sets[name] = {(r['launch_data_pin'], r['capture_data_pin']) for r in context['relations']}
                result['corners'][name] = dict(status='NATIVE_IDENTITIES_EXPANDED', relations=records,
                    actual_consumed_child_liberty=context['consumed_child_liberty'], original_observer_metadata=context['metadata'])
            except (ValueError, KeyError, TypeError, OSError) as error:
                result['corners'][name] = dict(status='UNEXPANDED', reason=str(error))
        if len(pair_sets) == 2 and pair_sets['tt'] == pair_sets['ff']:
            result['status'] = 'NATIVE_IDENTITY_RELATIONS_EXPANDED'
        else:
            result['reasons'].append('missing/inconsistent TT/FF exact DATA identity expansion')
    except (ValueError, KeyError, TypeError, OSError) as error:
        result['reasons'].append(str(error))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('attachment', 'qualification', 'boundary-maps', 'native-witness', 'native-view', 'out'):
        parser.add_argument('--' + key, required=True)
    parser.add_argument('--instance', action='append', required=True)
    parser.add_argument('--parent-witness')
    parser.add_argument('--parent-view')
    args = parser.parse_args()
    result = consume(args.attachment, args.qualification, args.boundary_maps, args.native_witness,
                     args.native_view, args.instance, args.parent_witness, args.parent_view)
    Path(args.out).write_text(json.dumps(result, indent=2) + '\n')
    print(result['status'], result['parent_coverage'], result['qualification'])
    return 0 if result['status'] == 'NATIVE_IDENTITY_RELATIONS_EXPANDED' else 2


if __name__ == '__main__':
    raise SystemExit(main())
