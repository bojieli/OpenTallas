#!/usr/bin/env python3
"""Selected source calls and finite RF/shared/L2 retirement interval compiler.

This successor separates source preparation, engine-build G0 and downstream
physical admission. It never converts provisional edges into measured ns.
"""
import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOME = ROOT / 'results/uarch/h4_hbm_selected_intervals_20261002'
MANIFEST = '1a48c89f3720684c1334527a12d529bdb01b0ea68f3ecab4ea34714da3f7f483'
LEAVES = {'RF_read_pair': (3, 1024), 'RF_write_mirrors': (2, 512),
          'shared_read64': (3, 64), 'shared_write64': (2, 64),
          'L2_read128': (12, 128), 'L2_write128': (8, 128),
          'L2_write_scalar32': (2, 4)}

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def positive(x, label):
    if type(x) is not int or x < 1:
        raise ValueError(label + ' must be an explicit positive finite bound')
    return x

def inputs():
    raw = (HOME / 'manifest.json').read_bytes()
    if digest(raw) != MANIFEST:
        raise ValueError('manifest source pin')
    data = []
    for row in json.loads(raw)['inputs']:
        path = (HOME / row['archive']).resolve()
        if not path.is_relative_to(HOME.resolve()):
            raise ValueError('archive origin')
        raw = path.read_bytes()
        if digest(raw) != row['sha256'] or len(raw) != row['bytes']:
            raise ValueError('input source pin')
        data.append(json.loads(gzip.decompress(raw) if path.suffix == '.gz' else raw))
    return data

def selected_inventory():
    catalog, old, correction, reviewed, overlay, _ = inputs()
    # The catalog digest names the calendar adapter, not the producer dispatch.
    # Validate its exact native source and explicit window call overlay instead.
    if catalog['source_program_sha256'] != correction['native_input_sha256']:
        raise ValueError('eight-group input native pin')
    for pc, patch in overlay['dispatch_PC_patches'].items():
        actual = catalog['PC_bindings'][int(pc)]['bindings']
        if [(b['rank'], b['template']) for b in actual] != [(b['rank'], b['template']) for b in patch['calls']]:
            raise ValueError('source window call overlay')
    remap = {r['PC']: r for r in correction['group_PCs']}
    calls = []
    for op in catalog['PC_bindings']:
        for ordinal, binding in enumerate(op['bindings']):
            previous = binding['template']
            group = remap.get(op['pc'])
            if group is not None and previous != group['old_template']:
                raise ValueError('group source template pin')
            template = group['new_template'] if group else previous
            known = None if group else old['template_shared_bindings'].get(template, {}).get('read64')
            if known is not None:
                continue
            calls.append(dict(call_id=f"{op['pc']}:{binding['rank']}:{ordinal}",
                              PC=op['pc'], rank=binding['rank'], ordinal=ordinal,
                              template=template, previous_template=previous,
                              family=op['family'], dependencies=op['dependencies'],
                              SM_partition=binding['SM_partition'],
                              corrected_eight_group=bool(group),
                              movement_intervals=None))
    if len(calls) != reviewed['shared_unknown_calls'] or len(calls) != 193316:
        raise ValueError('selected actual call inventory differs from reviewed calendar')
    if reviewed['source_native_sha256'] != correction['native_output_sha256'] or reviewed['source_dispatch_sha256'] != correction['dispatch_output_sha256']:
        raise ValueError('reviewed current producer digests')
    return dict(schema='opentallas.HBM.selected-source-calls.v1', model='DeepSeek',
                PCs=catalog['PCs'], calls=calls,
                source_native_sha256=correction['native_output_sha256'],
                source_dispatch_sha256=correction['dispatch_output_sha256'])

def qwen_inventory():
    program = inputs()[5]
    # This is the compiler's explicit serialized worker; remote rank1 provider
    # homes remain in each operation. Do not invent one kernel call per home.
    calls = []
    for op in program['operations']:
        if op['calendar_export']['placement'] != 'serialized worker rank0 SM0, remote home transfers charged through NoC; no assumed extra local RF ports':
            raise ValueError('Qwen selected worker source changed')
        calls.append(dict(call_id=f"{op['pc']}:0:0", PC=op['pc'], rank=0, ordinal=0,
                          template=digest(json.dumps(op, sort_keys=True, separators=(',', ':')).encode()),
                          family=op['opcode'], dependencies=op['dependencies'],
                          SM_partition='selected serialized worker rank0 SM0',
                          corrected_eight_group=False, movement_intervals=None,
                          source_provider_references=op['provider_binding'],
                          source_logical_counts=op['calendar_export']['counts_full_context']['logical_counts']))
    if len(calls) != 1737:
        raise ValueError('Qwen all-PC source extent')
    artifact_digest = digest((HOME/'inputs/5.json.gz').read_bytes())
    return dict(schema='opentallas.HBM.selected-source-calls.v1', model='Qwen', PCs=1737,
                source_digest_scope='exact bounded compiler artifact; template hashes bind each ordered operation',
                source_native_sha256=artifact_digest, source_dispatch_sha256=artifact_digest, calls=calls)

def compose(inventory, bindings, *, require_complete=True):
    """Consume source-resolved commands, not scalar histograms or callback costs.

    One finite credit per SM leaf and per physical L2 bank, held through matched
    consumer/reverse grants. Ordered source calls serialize here conservatively;
    different rank/SM/bank resources overlap. The input explicitly bounds all
    external waits. No unbounded consumer or producer can yield a finite result.
    """
    for field in ('source_native_sha256', 'source_dispatch_sha256'):
        if bindings.get(field) != inventory[field]:
            raise ValueError('current source digest: ' + field)
    required = {c['call_id']: c for c in inventory['calls']}
    supplied = bindings.get('calls', {})
    if set(supplied) - set(required):
        raise ValueError('unknown source call')
    missing = sorted(set(required) - set(supplied))
    if require_complete and missing:
        raise ValueError(f'{len(missing)} selected calls lack finite operator intervals')
    resources, pc_end, intervals, keys = {}, {}, [], set()
    for call in inventory['calls']:
        if call['call_id'] not in supplied:
            continue
        record = supplied[call['call_id']]
        if record.get('template') != call['template']:
            raise ValueError('current source template')
        commands = record.get('commands')
        if not isinstance(commands, list) or not commands:
            raise ValueError('source-resolved commands required; empty is not a zero-cost binding')
        cursor = max((pc_end.get(pc, 0) for pc in call['dependencies']), default=0)
        for sequence, event in enumerate(commands):
            kind = event['kind']
            if kind not in LEAVES:
                raise ValueError('unsupported endpoint primitive')
            sm, die = event['SM'], event['die']
            if type(sm) is not int or not 0 <= sm < 32 or type(die) is not int or die < 0:
                raise ValueError('actual die/SM binding')
            for field in ('generation', 'lease', 'provider_reference', 'existing_interval_id'):
                if not event.get(field):
                    raise ValueError('missing owner/cost identity: ' + field)
            ref = event.get('source_operand')
            if not isinstance(ref, dict) or not {'code_index', 'operand', 'typed_offset', 'typed_bytes'} <= ref.keys():
                raise ValueError('source operand span required')
            if any(type(ref[f]) is not int or ref[f] < 0 for f in ('code_index', 'typed_offset')):
                raise ValueError('source operand offset')
            edges, payload = LEAVES[kind]
            if ref['typed_bytes'] != payload:
                raise ValueError('source operand payload does not match physical port')
            resource = (die, sm, 'RF' if kind.startswith('RF_') else 'shared')
            if kind.startswith('L2_'):
                slice_id, bank = event['slice'], event['bank']
                if type(slice_id) is not int or not 0 <= slice_id < 4 or type(bank) is not int or not 0 <= bank < 8:
                    raise ValueError('actual L2 endpoint')
                resource = (die, slice_id, bank, 'L2')
                address = event['bank_byte_address']
                if type(address) is not int or address < 0 or address % payload or address + payload > 262144:
                    raise ValueError('bank address/extent')
            elif kind.startswith('shared_'):
                address = event['scratch_byte_address']
                if type(address) is not int or address < 0 or address % 64 or address + 64 > 65536:
                    raise ValueError('64KiB shared tile bound')
                if type(event.get('group')) is not int or not 0 <= event['group'] < 8:
                    raise ValueError('eight-group scratch identity')
            else:
                slots = event['RF_slots']
                expected = 2 if kind == 'RF_read_pair' else 1
                if len(slots) != expected or any(type(s) is not int or not 0 <= s < 512 for s in slots):
                    raise ValueError('actual 2R1W RF ports')
            waits = {f: positive(event.get(f), f) for f in
                     ('backend_bound_edges', 'consumer_bound_edges', 'reverse_bound_edges')}
            # Same-bank contention is finite only when every preceding owner has
            # a bounded consumer/reverse. No assumed eight-bank speedup.
            start = max(cursor, resources.get(resource, 0))
            visible = start + 1 + edges + waits['backend_bound_edges']
            consumer = visible + waits['consumer_bound_edges']
            retired = consumer + waits['reverse_bound_edges']
            cost_key = (inventory['source_native_sha256'], call['call_id'], die, sm,
                        event['generation'], event['lease'], sequence,
                        event['existing_interval_id'])
            if cost_key in keys:
                raise ValueError('duplicate once-only cost key')
            keys.add(cost_key)
            intervals.append(dict(call_id=call['call_id'], PC=call['PC'], rank=call['rank'],
                                  sequence=sequence, kind=kind, resource=list(resource),
                                  cost_key=list(cost_key), source_operand=ref,
                                  start=start, visible_ACK=visible, consumer=consumer,
                                  reverse_grant=retired, contention_edges=start-cursor,
                                  leaf_edges=edges, arbitration_edges=1, bytes=payload,
                                  external_wait_bounds=waits))
            cursor = retired
            resources[resource] = retired
        pc_end[call['PC']] = max(pc_end.get(call['PC'], 0), cursor)
    return dict(schema='opentallas.HBM.finite-endpoint-intervals.v1', intervals=intervals,
                selected_calls=len(required), bound_calls=len(supplied), missing_calls=missing,
                selected_movement_retirement_edge_upper=max(resources.values(), default=0) if not missing else None,
                complete_token_latency=None, automatic_ns_delta=False,
                interval_scope='supplied source operand commands only; whole-operator operand coverage not attested',
                whole_operator_interval_composition_verified=False,
                contextual_engine_build_allowed=False,
                existing_RF_I64_RMW_C0_provider_charges_added=0, hardware_admitted=False)

def receipt(inventory):
    calls = inventory['calls']
    return dict(schema='opentallas.HBM.endpoint-build-prerequisites.v1',
                selected_calls=len(calls), PCs=inventory['PCs'],
                corrected_group_calls=sum(c['corrected_eight_group'] for c in calls),
                families=dict(sorted(Counter(c['family'] for c in calls).items())),
                source_native_sha256=inventory['source_native_sha256'],
                source_dispatch_sha256=inventory['source_dispatch_sha256'],
                model=inventory['model'],
                leaf_edge_bounds={k: v[0] for k, v in LEAVES.items()},
                physical_L2_banks_per_slice=8, L2_slices_per_die=4,
                SMs_per_die=32, RF_ports='serialized 2R1W, two write mirrors',
                shared_bytes_per_SM=65536, shared_port_bytes=64,
                pre_engine_build_missing=['selected-call ordered operand/lease/event spans',
                                         'positive backend/consumer/reverse bounds and interval reconciliation',
                                         'constructive source clock/PG/via allocation'],
                implementation_todos=['selected gateway RTL', 'generic L2 bank fence RTL',
                                      'matrix/GU/KV writers through same ownership fence'],
                downstream_PR_checks=['placed cones', 'installed CTS', 'actual PG/vias', 'SS setup/FF hold'],
                source_preparation_allowed=True, contextual_engine_build_allowed=False,
                existing_endpoint_installed_is_not_a_prebuild_requirement=True,
                complete_token_latency=None, automatic_ns_delta=False,
                admission='FAIL_FINITE_OPERATOR_INTERVAL_COMPOSITION')

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--verify', action='store_true')
    ap.add_argument('--bindings', type=Path)
    ap.add_argument('--model', choices=('DeepSeek', 'Qwen'), default='DeepSeek')
    args = ap.parse_args()
    inventory = selected_inventory() if args.model == 'DeepSeek' else qwen_inventory()
    artifacts = {'selected_calls.json.gz': gzip.compress((json.dumps(inventory, sort_keys=True, separators=(',', ':'))+'\n').encode(), mtime=0),
                 'receipt.json': (json.dumps(receipt(inventory), sort_keys=True, indent=2)+'\n').encode()}
    if args.bindings:
        result = compose(inventory, json.loads(args.bindings.read_text()))
        artifacts['finite_intervals.json.gz'] = gzip.compress(json.dumps(result, sort_keys=True).encode(), mtime=0)
    artifacts['manifest.json'] = (json.dumps(dict(tool_sha256=digest(Path(__file__).read_bytes()),
         input_manifest_sha256=MANIFEST, output_sha256={k:digest(v) for k,v in artifacts.items()}), sort_keys=True, indent=2)+'\n').encode()
    if not args.verify:
        args.out.mkdir(parents=True, exist_ok=False)
    for name, raw in artifacts.items():
        if args.verify:
            if (args.out/name).read_bytes() != raw:
                raise ValueError('replay mismatch ' + name)
        else:
            (args.out/name).write_bytes(raw)
    print('PASS_SELECTED_INTERVAL_REPLAY' if args.verify else 'PASS_SELECTED_CALL_EXPORT')

if __name__ == '__main__':
    main()
