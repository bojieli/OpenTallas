#!/usr/bin/env python3
"""Join literal canonical operations to real homes and compiled native calendars.

This is an admission pass, never a placement heuristic or runtime scheduler.
Inputs are source-bound producer catalogues and native programmes. Parent
rectangles, provider homes, priced durations and transport station counts cannot
supply an execution binding. All rank programmes are rejected atomically if any
operation, native home, calendar, or required MTP continuation is absent.
"""
from __future__ import annotations
import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
from compile_calendar import compile_program


def load(path):
    path = Path(path)
    return json.loads(gzip.decompress(path.read_bytes()) if path.suffix == '.gz' else path.read_bytes())


def pinned(ref, root):
    if not isinstance(ref, dict):
        raise ValueError('missing source-pinned input')
    path = (root / ref['path']).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError('input outside source tree')
    if hashlib.sha256(path.read_bytes()).hexdigest() != ref['sha256']:
        raise ValueError('stale source-pinned input '+ref['path'])
    return load(path)


def join(canonical, catalogue, manifest, root):
    root = Path(root).resolve()
    violations, compiled, coverage = [], [], Counter()
    def reject(kind, **witness):
        violations.append(dict(kind=kind, **witness))
    ranks = {}
    for die in canonical['rank_programme_bindings']:
        key = die['stage'], die['rank']
        if key in ranks:
            raise ValueError('duplicate canonical rank')
        ranks[key] = die['die_id']
    if set(ranks) != {(s,r) for s in range(81) for r in range(4)} or len(set(ranks.values())) != 324:
        raise ValueError('canonical81 stages/324 unique rank dies required')
    nodes = {n['node']: n for n in catalogue['source_SU_nodes']}
    if len(nodes) != len(catalogue['source_SU_nodes']) or not nodes:
        raise ValueError('duplicate or empty literal source operation catalogue')
    # The historical demand-r5 catalogue covers0..39+head only. A populated
    # MTP boolean or backbone coverage must never stand in for its operations.
    mtp = {n['node'] for n in nodes.values() if n.get('scope') == 'mtp'}
    if not mtp:
        reject('missing_literal_MTP_continuation_operations')
    try:
        inventory = pinned(manifest.get('native_instance_inventory'), root)
        if inventory.get('schema') != 'opentallas.s81.elaborated-leaf-instances.v1':
            raise ValueError('actual elaborated leaf inventory required')
        if not inventory.get('source_evidence'):
            raise ValueError('actual elaboration source closure required')
        for evidence in inventory['source_evidence']:
            # Source files can be RTL, so verify bytes without parsing JSON.
            path = (root / evidence['path']).resolve()
            if not path.is_relative_to(root) or hashlib.sha256(path.read_bytes()).hexdigest() != evidence['sha256']:
                raise ValueError('stale actual elaboration source closure')
        homes = {(h['node'], h['rank']): h for h in inventory['source_operation_homes']}
        if len(homes) != len(inventory['source_operation_homes']):
            raise ValueError('duplicate independently emitted source operation home')
        instances = {(i['die_id'], i['instance']): i for i in inventory['instances']}
        if len(instances) != len(inventory['instances']):
            raise ValueError('duplicate elaborated native instance')
    except (ValueError, KeyError, TypeError, OSError) as exc:
        instances, homes = {}, {}
        reject('missing_or_invalid_native_instance_inventory', reason=str(exc))
    seen = set()
    for record in manifest.get('rank_programmes', []):
        key = record.get('stage'), record.get('rank')
        if key not in ranks or key in seen or record.get('die_id') != ranks.get(key):
            reject('invalid_canonical_rank_programme', stage=key[0], rank=key[1]); continue
        seen.add(key)
        try:
            if 'provider_home' in record:
                raise ValueError('HE/CROM provider home is not native SU/VM home')
            epoch = record['core_epoch']
            if type(epoch) is not int or epoch < 0:
                raise ValueError('nonnegative integer actual core epoch required')
            for role in ('su', 'vm'):
                name = record[role+'_instance']
                instance = instances.get((ranks[key], name))
                if not instance or instance.get('role') != role or instance.get('die_id') != ranks[key]:
                    raise ValueError('native '+role+' home absent from actual elaboration')
            program = pinned(record['program'], root)
            binding = pinned(record['binding'], root)
            contract = pinned(record['vm_contract'], root)
            job_ids = {op['id'] for op in program['ops']}
            source_map = record['source_operations']
            if set(source_map) != job_ids:
                raise ValueError('literal source coverage must match every programme job')
            local_covered = []
            for op in program['ops']:
                members = source_map[op['id']]
                if not members:
                    raise ValueError('empty literal source group')
                if len(members) > 1:
                    proof = pinned(record['fusion_proofs'][op['id']], root)
                    if (proof.get('passed') is not True or proof.get('source_operations') != members
                            or proof.get('rounding_and_order_preserved') is not True
                            or proof.get('native_job') != op['id']):
                        raise ValueError('native fusion lacks exact rounding/order proof')
                for member in members:
                    if member['node'] not in nodes or member['template_sha256'] != nodes[member['node']]['template_sha256']:
                        raise ValueError('invented/stale literal source operation')
                    home = homes.get((member['node'], key[1]))
                    if not home or home.get('stage') != key[0] or home.get('die_id') != ranks[key]:
                        raise ValueError('source operation home disagrees with independent actual compiler assignment')
                    if home.get('template_sha256') != member['template_sha256']:
                        raise ValueError('stale independently emitted source operation home')
                    if home.get('physical_instance') != binding['jobs'][op['id']].get('physical_instance'):
                        raise ValueError('source operation native instance disagrees with actual compiler assignment')
                    local_covered.append((member['node'], key[1]))
                native = binding['jobs'][op['id']]
                home = instances.get((ranks[key], native.get('physical_instance')))
                if not home or home.get('die_id') != ranks[key] or home.get('role') != native.get('engine'):
                    raise ValueError('programme native job has no matching actual engine home')
            if len(set(local_covered)) != len(local_covered):
                raise ValueError('duplicate literal source operation within programme')
            result = compile_program(program, binding, contract, root)
            if not result['dispatch_eligible']:
                reject('native_calendar_rejected', stage=key[0], rank=key[1], report=result)
                continue
            compiled.append(dict(stage=key[0], rank=key[1], die_id=ranks[key],
                                 core_epoch=epoch, su_instance=record['su_instance'],
                                 vm_instance=record['vm_instance'], result=result))
            coverage.update(local_covered)
        except (ValueError, KeyError, TypeError, OSError) as exc:
            reject('invalid_native_rank_programme', stage=key[0], rank=key[1], reason=str(exc))
    for key in sorted(set(ranks)-seen):
        reject('missing_rank_programme', stage=key[0], rank=key[1], die_id=ranks[key])
    missing = [(node, rank) for node in sorted(nodes) for rank in range(4) if not coverage[node,rank]]
    duplicate = [(node, rank, count) for (node,rank),count in sorted(coverage.items()) if count != 1]
    if missing:
        reject('unimplemented_literal_source_operations', count=len(missing), operations=missing)
    if duplicate:
        reject('multiply_executed_literal_source_operations', operations=duplicate)
    ready = not violations
    return dict(schema='opentallas.s81.canonical-execution-join.v1',
                status='LOCAL_CANONICAL_PROGRAMMES_BOUND' if ready else 'CANONICAL_EXECUTION_INCOMPLETE',
                local_programmes_ready=ready, dispatch_eligible=False, qualified=False, source_operations=len(nodes),
                literal_mtp_operations=len(mtp), required_rank_operations=4*len(nodes),
                covered_rank_operations=len(coverage), rank_programmes_seen=len(seen),
                rank_programmes_compiled=len(compiled), violations=violations,
                # Never emit partial schedules for an incomplete global join.
                compiled_rank_programmes=compiled if ready else [],
                global_transport_and_producer_consumer_join='REQUIRED_SEPARATE_GATE',
                physical_and_throughput_qualification='NOT_ESTABLISHED_BY_COMPILER')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--canonical', type=Path, required=True)
    ap.add_argument('--catalogue', type=Path, required=True)
    ap.add_argument('--manifest', type=Path, required=True)
    ap.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    manifest = load(args.manifest)
    # Both source catalogues must be pinned by the submitting manifest.
    for name, path in [('canonical',args.canonical), ('catalogue',args.catalogue)]:
        if manifest.get(name+'_sha256') != hashlib.sha256(path.read_bytes()).hexdigest():
            raise ValueError('stale '+name+' source input')
    report = join(load(args.canonical), load(args.catalogue), manifest, args.root)
    args.out.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('violations','compiled_rank_programmes')}))
    return 0 if report['local_programmes_ready'] else 2

if __name__ == '__main__':
    raise SystemExit(main())
