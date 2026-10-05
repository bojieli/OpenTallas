"""Read-only RF lifetime/alias diagnosis over immutable native/home artifacts.

Models the existing driver release rule, never relocates homes, runs arithmetic,
signals a process or releases a live lease. Post-first-failure prefix records
are static counterfactual diagnostics, not successful production execution.
"""
import argparse
import collections
import gzip
import hashlib
import json
from pathlib import Path
import numpy as np


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    p = Path(path); raw = p.read_bytes()
    return json.loads(gzip.decompress(raw) if p.suffix == '.gz' else raw)


def graph(native):
    producers = {}; consumers = collections.defaultdict(list)
    binding_consumers = collections.defaultdict(set)
    for op in native['instructions']:
        for w in op['writes']:
            if w['version'] in producers: raise ValueError('duplicate source version writer')
            producers[w['version']] = op['pc']
        for r in op['reads']:
            consumers[r['version']].append(op['pc'])
        for bindings in op.get('provider_bindings', {}).values():
            for b in bindings.values():
                for version in ([b['version']] if 'version' in b else []) + b.get('additional_versions', []) + b.get('identity_from_versions', []):
                    binding_consumers[version].add(op['pc'])
    return producers, consumers, binding_consumers


def all_nested_source_references(native):
    """Version strings everywhere in each op, not only direct read bindings.

    Writer identity and buffer write_version are declarations, not readers.
    All remaining mentions count conservatively as potential consumer edges.
    """
    producers, _, _ = graph(native)
    references = collections.defaultdict(list)
    def walk(value, path, op):
        if isinstance(value, dict):
            for key, item in value.items(): walk(item, path + [key], op)
        elif isinstance(value, list):
            for index, item in enumerate(value): walk(item, path + [index], op)
        elif isinstance(value, str) and value in producers:
            if len(path) == 3 and path[0] == 'writes' and path[2] == 'version': return
            if path[-1] == 'write_version': return
            references[value].append(dict(PC=op['pc'], path=path))
    for op in native['instructions']: walk(op, [], op)
    return references


def positions(homes, indices):
    result = set()
    for i in indices:
        h = homes[i]
        if h['home']['class'] != 'RF': raise ValueError('RF slots required')
        first = h['home']['slot_first']; length = h['home']['vectors']
        if not 0 <= first < 512 or not 0 < length <= 512 - first or not 0 <= h['SM'] < 32:
            raise ValueError('actual finite RF geometry')
        result.update((h['SM'], slot) for slot in range(first, first + length))
    return result


def audit_prefix(native, homes, stop):
    producers, consumers, bindings = graph(native)
    live = {}; collisions = []; snapshots = []
    for op in native['instructions']:
        if op['pc'] > stop: break
        for owned in op['rank_bindings']:
            if owned.get('empty_owned_extent'): continue
            rank = owned['rank']
            writes = op['writes']
            if owned.get('buffer_programs'):
                writes = [next(w for w in op['writes'] if w['version'] == b['write_version']) for b in owned['buffer_programs']]
            for w in writes:
                indices = [i for i in w['home_indices'] if rank in homes[i]['rank_group']]
                if not indices or homes[indices[0]]['home']['class'] != 'RF': continue
                slots = positions(homes, indices)
                for (old, old_rank), loc in live.items():
                    if old_rank != rank or old == w['version']: continue
                    overlap = slots & loc['slots']
                    if not overlap: continue
                    collision = dict(publication_PC=op['pc'], publication_rank=rank,
                        new_version=w['version'], new_producer_PC=producers[w['version']],
                        new_consumers=consumers.get(w['version'], []),
                        retained_version=old, retained_producer_PC=producers[old],
                        retained_consumers=consumers.get(old, []),
                        retained_binding_consumers=sorted(bindings.get(old, [])),
                        last_consumer=max(consumers[old]) if consumers.get(old) else None,
                        retained_reason='no consumers: existing read-driven release loop never visits output' if not consumers.get(old) else 'full-program last consumer not retired before current publication',
                        shared_SM_slots=[list(x) for x in sorted(overlap)],
                        new_home_records=[dict(index=i, record=homes[i]) for i in indices if positions(homes, [i]) & overlap],
                        retained_home_records=[dict(index=i, record=homes[i]) for i in loc['indices'] if positions(homes, [i]) & overlap],
                        mirror_address_spans=[dict(SM=sm, slot=slot,
                            byte_addresses=[(2 * sm + copy) * 262144 + slot * 512 for copy in (0, 1)],
                            bytes_per_vector=512) for sm, slot in sorted(overlap)],
                        execution_scope='first static refusal matches actual publish order' if not collisions else 'counterfactual static scan beyond first refusal; not executed')
                    collisions.append(collision)
                # Keep both versions in the static inventory after an overlap.
                # This does not perform a write or authorize progression.
                live[w['version'], rank] = dict(indices=indices, slots=slots)
        snapshots.append(dict(PC=op['pc'], retained_RF_version_rank_entries=len(live),
            zero_reader_entries=sum(not consumers.get(v) for v, rank in live)))
        for r in op['reads']:
            if consumers[r['version']][-1] == op['pc']:
                live = {key: value for key, value in live.items() if key[0] != r['version']}
    return dict(prefix_stop=stop, first_collision=collisions[0] if collisions else None,
        static_collision_pairs=len(collisions), collisions=collisions,
        retention_snapshots=snapshots, no_runtime_or_allocator_mutation=True)


def pressure(native, homes):
    producers, consumers, bindings = graph(native)
    all_refs = all_nested_source_references(native)
    count = len(native['instructions'])
    # Aggregate vectors per rank/SM, before reads and publication complete at
    # the current PC. Both copies carry the same512-vector namespace; the
    # mirror factor is reported in bytes, not charged twice against slots.
    deltas = {name: np.zeros((96, 32, count + 1), dtype=np.int32) for name in
              ('directory_declared', 'source_graph_retire_at_last_read_or_birth', 'existing_driver_zero_reader_retained')}
    retire_mismatches = []; missing_read_edges = []; rf_rows = 0
    for h in homes:
        if h['home']['class'] != 'RF': continue
        version = h['version']
        if version not in producers: continue
        birth = producers[version]
        graph_last = max(consumers[version]) if consumers.get(version) else birth
        if h['birth_pc'] != birth or h['retire_pc'] != graph_last:
            retire_mismatches.append(dict(version=version, producer_PC=birth,
                source_last_consumer=graph_last, directory_birth=h['birth_pc'], directory_retire=h['retire_pc']))
        ends = dict(directory_declared=h['retire_pc'],
            source_graph_retire_at_last_read_or_birth=graph_last,
            existing_driver_zero_reader_retained=max(consumers[version]) if consumers.get(version) else count - 1)
        ranks = h['rank_group']; sm = h['SM']; size = h['home']['vectors']
        for name, end in ends.items():
            if not birth <= end < count: raise ValueError('source home lifetime interval')
            deltas[name][ranks, sm, birth] += size
            deltas[name][ranks, sm, end + 1] -= size
        rf_rows += 1
    peaks = {}
    for name, delta in deltas.items():
        np.cumsum(delta, axis=2, out=delta)
        index = np.unravel_index(delta.argmax(), delta.shape)
        peaks[name] = dict(aggregate_vectors=int(delta[index]), rank=int(index[0]), SM=int(index[1]), PC=int(index[2]),
            logical_RF_capacity_vectors=512, physical_mirrored_bytes=int(delta[index]) * 512 * 2,
            over512_vectors=bool(delta[index] > 512),
            scope='source-metadata lifetime pressure; upper live reservations before PC end; no installed timing or allocation signoff')
    for version, edge_pcs in bindings.items():
        extra = sorted(edge_pcs - set(consumers.get(version, [])))
        if extra: missing_read_edges.append(dict(version=version, provider_binding_only_consumer_PCs=extra))
    dead = [dict(version=v, producer_PC=pc,
        source_read_consumers=[], provider_binding_consumers=sorted(bindings.get(v, [])),
        all_nested_potential_consumer_references=all_refs.get(v, []),
        hidden_consumer_warning=bool(all_refs.get(v)),
        driver_release_reason='no read edge, never visited by current release loop')
        for v, pc in producers.items() if not consumers.get(v)]
    return dict(whole_program_PCs=count, RF_home_records=rf_rows,
        peaks=peaks, directory_vs_source_lifetime_mismatch_count=len(retire_mismatches),
        directory_vs_source_lifetime_mismatch_samples=retire_mismatches[:30],
        no_source_read_consumer_versions=dead, provider_binding_edges_missing_from_driver_read_graph=missing_read_edges,
        full_native_nested_reference_audit=True,
        external_contracts_not_in_native_not_silently_assumed= True,
        resource_repair_adopted=False, original_homes_unchanged=True,
        required_release_contract='zero-reader output eligible only after actual producer publication/capture/mirrorACK, observer evidence and all owning readers/consumer/reverse obligations close; future-use versions remain retained',
        full_allocator_timing_route_model_complete=False)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    for name in ('native', 'homes', 'out'):
        p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--prefix-stop', type=int, required=True)
    a = p.parse_args()
    if a.out.exists(): raise ValueError('fresh diagnostic evidence required')
    a.out.mkdir(parents=True)
    n = load(a.native); h = load(a.homes)
    if isinstance(h, dict): h = h['homes']
    (a.out / 'prefix_aliases.json').write_text(json.dumps(audit_prefix(n, h, a.prefix_stop), sort_keys=True, indent=2) + '\n')
    (a.out / 'full_program_lifetime_pressure.json').write_text(json.dumps(pressure(n, h), sort_keys=True, indent=2) + '\n')
    (a.out / 'source_pins.json').write_text(json.dumps({str(p.resolve()): sha(p) for p in [a.native, a.homes, Path(__file__)]}, sort_keys=True, indent=2) + '\n')
    print('PASS_STATIC_RF_LIFETIME_AUDIT_NO_ALLOCATION_CHANGE')
