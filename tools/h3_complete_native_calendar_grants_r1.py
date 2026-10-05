#!/usr/bin/env python3
"""Additive source-journal to physical SRAM acceptance/ACK/lease verifier.

Edges are endpoint observations, never provider ticks. Missing physical events
remain debt. This module neither installs an owner nor qualifies clock/latency.
"""
import argparse
import ast
import math
import re
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = 'results/uarch/h3_complete_native_calendar_20261002/causal_grants_r1'
SOURCES = (
    'rtl/gpu/ot_gpu_rf_service.sv', 'rtl/gpu/ot_gpu_scratch_service.sv',
    'rtl/gpu/ot_gpu_full_sm_service.sv', 'rtl/gpu/ot_gpu_hbm_rf_shared_context.sv',
    'tools/h4_hbm_w19_pc10_endpoints.py', 'tools/ds_hbm_additive_endpoint_join_r54.py',
    'tools/h3_complete_native_calendar.py', 'tools/h3_complete_native_calendar_successor_r1.py',
    'tools/ds_producer_checkpoint_resume_v2.py',
    'results/uarch/h4_hbm_selected_cache_rmw_20261002/selected_r4/commands.json.gz',
    'results/uarch/h4_hbm_production_owner_20261002/final_r5/PC0_projection.json.gz',
)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def compile_commands(commands, source_sha256):
    """Bind retained commands; RF RMW children share a single parent credit."""
    parents = {}; children = {}; previous = {}
    def parent(key, row, resource, scope):
        dependencies = [] if resource not in previous else [previous[resource]]
        p = dict(id=key, source_command_sha256=digest(canonical(row)),
                 command_archive_sha256=source_sha256, PC=row['PC'],
                 resource=list(resource), dependencies=dependencies, scope=scope,
                 lease=row.get('source_tile_lease', row.get('version')),
                 children=[])
        parents[key] = p; previous[resource] = key
        return p
    def child(p, key, row, write, kind):
        if kind == 'RF':
            slot = row['RF_slot']
            if type(slot) is not int or not 0 <= slot < 512:
                raise ValueError('actual RF slot required')
            banks = [[copy, bank, slot // 128, slot % 128]
                     for copy in (0, 1) for bank in range(16)]
        else:
            addr = row['scratch_byte_address']
            if type(addr) is not int or addr % 64 or not 0 <= addr < 65536:
                raise ValueError('actual shared64 extent required')
            banks = [[0, bank, 0, addr // 64] for bank in (0, 1)]
        d = dict(id=key, parent=p['id'], PC=row['PC'], kind=kind,
                 write=write, resource=p['resource'], provider_reference=row['provider_reference'],
                 source_command_sha256=digest(canonical(row)), expected_SRAMs=banks,
                 endpoint_bytes=512 if kind == 'RF' else 64,
                 response_bytes=1024 if kind == 'RF' and not write else 0,
                 source_min_ACK_edge_offset=1 if write else 2,
                 domain='H1_streaming', source_observation_required=True,
                 existing_interval_id=row.get('existing_interval_id'),
                 sector_children=row.get('sector_children', []),
                 actual_journal_span=row.get('actual_journal_span'),
                 source_operand=row.get('source_operand'))
        children[key] = d; p['children'].append(key)
    for row in commands['RMW']:
        if row['kind'] != 'RF_partial_RMW' or len(row['owner']) != 5:
            raise ValueError('actual RF parent command required')
        p = parent(row['id'], row, ('RF', row['die'], row['SM']), 'actual_all96_PC0_RMW')
        p['owner'] = row['owner']; p['version'] = row['version']
        for phase, write in [('read_pair', False), ('both_copy_write', True), ('readback_pair', False)]:
            child(p, row['id'] + ':' + phase, row, write, 'RF')
    shared_parents = {}
    for row in commands['shared64']:
        owner = row['outer_owner']; key = digest(canonical(owner))
        if key not in shared_parents:
            p = parent('shared:' + key, row, ('shared64', row['die'], row['SM']),
                       'directed_PC10_rank0_journal_not_production96')
            p['owner'] = owner; shared_parents[key] = p
        p = shared_parents[key]
        if row['outer_owner']['SM'] != row['SM'] or row['outer_owner']['rank'] != row['die']:
            raise ValueError('source shared parent identity differs')
        child(p, row['id'], row, row['kind'] == 'shared_write64', 'shared64')
    for p in parents.values():
        if not p['children'] or len(p['children']) > 144:
            raise ValueError('finite parent child extent')
        p['binding_sha256'] = digest(canonical(p))
    return dict(schema='HBM_SOURCE_COMMAND_SRAM_ACCEPTANCE_BINDINGS_R1',
                parents=parents, children=children, physical_production_bindings_closed=0,
                hardware_qualified=False, cost_addition=0,
                C0_V1_I64_provider_RF_mirror_cost_added=0,
                whole_token_latency=None)


class CausalGrantLedger:
    """One credit per actual physical unit, held through matching parent reverse.

    Every accepted event resolves a retained command digest. Per-bank acceptance
    is distinct from the one common ACK. Read captures, ACK backpressure, source
    consumer and reverse are explicit. Exceptions preserve live debt.
    """
    def __init__(self, bindings):
        self.bindings = bindings; self.live = {}; self.resources = {}
        self.retired = set(); self.counts = Counter(); self.last_edge = {}
        self.observed_origins = set()

    def observe(self, event):
        p = self.bindings['parents'].get(event.get('parent'))
        if (p is None or event.get('binding_sha256') != p['binding_sha256']
                or event.get('owner') != p['owner'] or event.get('lease') != p['lease']):
            raise ValueError('retained source parent reference/digest required')
        if event.get('origin') not in ('endpoint_trace', 'directed_verifier_control'):
            raise ValueError('software ticks are not SRAM acceptance observations')
        if event.get('domain') != 'H1_streaming':
            raise ValueError('CDC requires separate matched sender/receiver receipts; no edge conversion')
        edge = event.get('edge')
        if type(edge) is not int or edge < 0:
            raise ValueError('explicit endpoint edge ordinal')
        resource = tuple(p['resource']); watermark = self.last_edge.get(resource, -1)
        if edge < watermark:
            raise ValueError('endpoint causal edge reversal')
        name = event['event']; x = self.live.get(p['id'])
        if name == 'parent_grant':
            if event.get('accepted') is not True or event.get('lease') != p['lease']:
                raise ValueError('matching accepted owner lease required')
            if resource in self.resources or x is not None or p['id'] in self.retired:
                raise ValueError('physical owner credit exhausted or stale grant')
            if not set(p['dependencies']) <= self.retired:
                raise ValueError('source owner dependencies not reverse-retired')
            x = dict(phase='CHILDREN', next_child=0, child=None, origin=event['origin'])
            self.live[p['id']] = x; self.resources[resource] = p['id']
        else:
            if x is None or self.resources.get(resource) != p['id']:
                raise ValueError('physical event without matching admitted parent')
            if event['origin'] != x['origin']:
                raise ValueError('control and endpoint evidence cannot be mixed')
            if name == 'child_issue':
                if x['phase'] != 'CHILDREN' or x['child'] is not None or x['next_child'] == len(p['children']):
                    raise ValueError('one finite in-flight source child required')
                expected = p['children'][x['next_child']]
                d = self.bindings['children'][expected]
                if (event.get('child') != expected or event.get('source_command_sha256') != d['source_command_sha256']
                        or event.get('provider_reference') != d['provider_reference']
                        or event.get('valid') is not True or event.get('ready') is not True):
                    raise ValueError('actual child source and ready/valid acceptance required')
                x['child'] = dict(id=expected, issue=edge, accepts=set(), captures=set())
            elif name in ('SRAM_accept', 'SRAM_capture', 'child_ACK'):
                active = x['child']
                if active is None or event.get('child') != active['id']:
                    raise ValueError('matching live SRAM child required')
                d = self.bindings['children'][active['id']]
                expected = {tuple(b) for b in d['expected_SRAMs']}
                if active.get('ACK_accepted'):
                    raise ValueError('child already ACKed; matching reverse required')
                if name != 'child_ACK':
                    bank = tuple(event.get('SRAM', []))
                    if bank not in expected or event.get('accepted') is not True:
                        raise ValueError('actual copy/bank/page/row acceptance required')
                    if name == 'SRAM_accept':
                        if edge != active['issue'] or bank in active['accepts'] or event.get('write') is not d['write']:
                            raise ValueError('same-go distinct bank acceptance required')
                        active['accepts'].add(bank)
                    else:
                        if d['write'] or bank not in active['accepts'] or bank in active['captures'] or edge <= active['issue']:
                            raise ValueError('causal distinct SRAM read capture required')
                        active['captures'].add(bank)
                else:
                    if (active['accepts'] != expected or (not d['write'] and active['captures'] != expected)
                            or edge < active['issue'] + d['source_min_ACK_edge_offset']
                            or event.get('valid') is not True or event.get('ready') is not True):
                        raise ValueError('all SRAM acceptances/captures and common ACK acceptance required')
                    active['ACK_accepted'] = True
            elif name == 'child_reverse':
                active = x['child']
                if active is None or event.get('child') != active['id'] or not active.get('ACK_accepted') or event.get('accepted') is not True:
                    raise ValueError('accepted child ACK and matching child reverse required')
                x['child'] = None; x['next_child'] += 1
            elif name == 'visibility_fence':
                if x['child'] is not None or x['next_child'] != len(p['children']) or x['phase'] != 'CHILDREN':
                    raise ValueError('all source children must ACK before visibility')
                if event.get('accepted') is not True:
                    raise ValueError('accepted visibility fence required')
                x['phase'] = 'CONSUMER'
            elif name == 'consumer':
                if x['phase'] != 'CONSUMER' or event.get('accepted') is not True:
                    raise ValueError('matching source consumer after visibility required')
                x['phase'] = 'REVERSE'
            elif name == 'reverse':
                if x['phase'] != 'REVERSE' or event.get('accepted') is not True or event.get('lease') != p['lease']:
                    raise ValueError('matching reverse lease after source consumer required')
                del self.live[p['id']]; del self.resources[resource]; self.retired.add(p['id'])
            else:
                raise ValueError('unsupported physical endpoint event')
        self.last_edge[resource] = edge; self.counts[name] += 1
        self.observed_origins.add(event['origin'])

    def summary(self):
        return dict(schema='HBM_CAUSAL_SRAM_GRANT_REPLAY_R1',
                    source_parents=len(self.bindings['parents']), retired_parents=len(self.retired),
                    live_parent_debt=len(self.live), physical_credit_debt=len(self.resources),
                    unobserved_parents=len(self.bindings['parents']) - len(self.retired) - len(self.live),
                    events=dict(self.counts), observation_origins=sorted(self.observed_origins),
                    all_parents_retired=len(self.retired) == len(self.bindings['parents']),
                    hardware_qualified=False, whole_token_latency=None,
                    external_consumer_reverse_CDC_HBM_wait_upper=None)


def verify_shared_journal_source(bindings, control, inventory, original_source):
    """Resolve retained instruction/typed span AND replay exact provider phases.

    No exporter ref is accepted solely because it is nonempty or hashed. This
    uses immutable original source validators, extracted without importing or
    changing canonical module identity. Directed controls remain directed.
    """
    if digest(original_source)!='c0370e63dba0eadcc06c5522c28a956ddebfd10af9b8765a61fe0e4fe025b817':
        raise ValueError('exact original typed-source verifier pin required')
    names={'native_value_specs','resolve_ds_movement_reference','verify_ds_operand_journal','positive'}
    functions=[n for n in ast.parse(original_source).body if isinstance(n,ast.FunctionDef) and n.name in names]
    if {n.name for n in functions}!=names:
        raise ValueError('source verifier function closure')
    ns=dict(math=math,re=re,hashlib=hashlib,json=json,Counter=Counter)
    exec(compile(ast.Module(body=functions,type_ignores=[]),'source-pinned-shared-span-validator','exec'),ns)
    program=dict(templates=inventory['native_templates'],instructions=[dict(pc=r['pc'],rank_bindings=r['actual_rank_template_bindings']) for r in inventory['corrected_PC_bindings']])
    journals={row['journal_id']:row['events'] for row in control['control_disk_journal_events']}
    calls={}; verified_events=0
    for call in control['control_movement_calls']:
        span=(call['journal_id'],call['journal_start'],call['journal_end'])
        if span in calls:
            raise ValueError('duplicate actual operator journal span')
        events=journals[span[0]][span[1]:span[2]]
        proof=ns['verify_ds_operand_journal'](program,call['owner']['template'],call['source_reference'],call['binding'],events)
        if proof!=call['proof'] or call['source_reference']!=proof['source_reference']:
            raise ValueError('actual source instruction/span proof differs')
        calls[span]=(call,events,proof);verified_events+=len(events)
    closed=0
    for d in bindings['children'].values():
        if d['kind']!='shared64':continue
        span=tuple(d['actual_journal_span'])
        if span not in calls:raise ValueError('actual source journal span absent')
        call,events,proof=calls[span]
        wanted='journal:%d:%d:%s'%(span[0],span[1],proof['journal_sha256'])
        if d['provider_reference']!=wanted:
            raise ValueError('reference must resolve actual source journal digest')
        ref=call['source_reference'];operand=d['source_operand']
        if operand['code_index']!=ref['code_index'] or operand['operand']!=ref['operand'] or operand['typed_bytes']!=64:
            raise ValueError('source code/operand/typed span differs')
        offset=operand['typed_offset']-ref['logical_byte_offset']
        if offset<0 or offset%64 or offset+64>ref['payload_bytes']:
            raise ValueError('source64B typed span extent')
        accepted={canonical(e['identity']) for e in events if e['event']=='request_accept'}
        returned={canonical(e['identity']) for e in events if e['event']=='validated_reverse_grant'}
        if len(d['sector_children'])!=2 or any(canonical(i) not in accepted & returned for i in d['sector_children']):
            raise ValueError('both actual32B child acceptances and reverse required')
        expected_sectors=set(range((proof['logical_byte_address']+offset)//32,(proof['logical_byte_address']+offset)//32+2))
        expected_row=(call['binding']['shared_tile_offset']+offset)//64
        if {i['sector'] for i in d['sector_children']}!=expected_sectors or any(b[3]!=expected_row for b in d['expected_SRAMs']):
            raise ValueError('source typed offset does not translate to actual sector/shared row')
        if bindings['parents'][d['parent']]['owner']!=call['owner']:
            raise ValueError('actual source parent owner differs')
        closed+=1
    return dict(source_resolved_calls=len(calls),source_resolved_shared64_children=closed,
        actual_shared_provider_events_verified=verified_events,
        templates_source_sha256=inventory['source_native_sha256'],
        directed_control=True,production_calls_closed=0,physical_SRAM_ACK_observations=0,
        software_ticks_converted=False)


def build_inventory(root=ROOT):
    inputs = {path: (root / path).read_bytes() for path in SOURCES}
    commands = json.loads(gzip.decompress(inputs[SOURCES[-2]]))
    bound = compile_commands(commands, digest(inputs[SOURCES[-2]]))
    projection = json.loads(gzip.decompress(inputs[SOURCES[-1]]))
    transactions = sum(flow['sectors32'] for row in projection['rows'] for flow in row['flows'])
    if (transactions != projection['transactions'] or transactions != 738816
            or {r['rank'] for r in projection['rows']} != set(range(96))
            or any(row['final_live_tags'] != 0 for row in projection['rows'])):
        raise ValueError('actual all96 journal projection closure')
    counts = Counter()
    for d in bound['children'].values():
        counts[d['kind'] + (':write' if d['write'] else ':read')] += 1
        counts['SRAM_bank_acceptance_obligations'] += len(d['expected_SRAMs'])
        if not d['write']:
            counts['SRAM_read_capture_obligations'] += len(d['expected_SRAMs'])
    summary = dict(schema='HBM_ACTUAL_JOURNAL_CAUSAL_GRANT_INVENTORY_R1',
        source_pins={name: digest(raw) for name, raw in inputs.items()},
        actual_PC0_transactions=transactions, actual_PC0_RF_provider_events=sum(r['events'] for r in projection['rows']),
        PC0_event_scope='96 RF provider journals only; publication/call journals excluded',
        actual_PC0_journal_sha256=projection['raw_journal_SHA256'],
        actual_software_mirror_write_pairs=projection['paired_mirror_write_sectors'],
        physical_parent_obligations=len(bound['parents']), physical_child_obligations=len(bound['children']),
        demand=dict(counts), production_endpoint_observations=0,
        physical_inventory=dict(SMs_per_die=32, RF_slots_per_SM=512, RF_lanes=128,
            RF_mirrors=2, RF_pages=4, RF_banks_per_page_and_copy=16,
            shared_bytes_per_SM=65536, shared_bytes_per_transaction=64, shared_SRAM_banks=2),
        complete_program_PC_counts={'DeepSeek': 2213, 'Qwen': 1737},
        joined_PC_scope={'DeepSeek': [0, 10], 'Qwen': []},
        shared_PC10_scope='directed rank0 operator journal; not all96 production',
        baseline_cost_replaced=False, additional_cost=0, whole_token_latency=None,
        all_program_physical_grants_complete=False, hardware_qualified=False,
        unknowns=['actual issued endpoint traces with SRAM acceptances and full owner/reference/lease',
                  'installed L2 transient reservation and bounded HBM backend service',
                  'causal consumer/reverse/CDC service bounds',
                  'remaining DS and Qwen production movement traces'],
        compact_constructor=dict(module='tools/ds_hbm_additive_endpoint_join_r54.py',
            calendar='tools/h3_complete_native_calendar_successor_r1.py',
            original_constructor_retained=True, installer='install(explicit_alias_modules) before constructor',
            checkpoint_role_blocker='V2.scope_role_proof ROLE_PINS lacks successor calendar; Peirce role successor required',
            constructor_GO=False))
    return bound, summary


def compile_qwen_kv_extension(directory, native):
    """Executable bank-credit DAG attached to retained native PC frontiers.

    Native frontiers are references to the existing complete native calendar,
    not new generic native-cost events. Source bytes are modeled at32B sector
    granularity; metadata expansion is selected-policy demand, not observed bus.
    """
    operations = {op['pc']: op for op in native['operations']}
    nodes = []; byid = {}; tails = {}; counts = Counter()
    def add(key, phase, deps, *, bank=None, acquire=None, release=None, **fields):
        if key in byid:
            raise ValueError('duplicate causal movement node')
        row = dict(id=key, phase=phase, dependencies=sorted(set(deps)), bank=bank,
                   acquire=acquire, release=release, **fields)
        nodes.append(row); byid[key] = row; counts[phase] += 1
        return key
    for pc, op in sorted(operations.items()):
        add('Qwen.PC%d.native' % pc, 'existing_native_calendar_frontier',
            ['Qwen.PC%d.retire' % d for d in op['dependencies']], PC=pc,
            native_operation_sha256=digest(canonical(op)),
            native_cost_recharged=False)
        add('Qwen.PC%d.retire' % pc, 'structural_frontier', ['Qwen.PC%d.native' % pc], PC=pc)
    def attach(pc, key):
        byid['Qwen.PC%d.retire' % pc]['dependencies'].append(key)
    def sector_chain(g, prefix, s, write, previous, pc):
        bank = ['L2', g['die'], s['L2']['slice'], s['L2']['bank']]
        identity = dict(PC=pc, group=g['key'], provider_ref=s['provider_ref'],
                        address=s['address'], mask=s['mask'], source_sector_sha256=digest(canonical(s)))
        current = add(prefix + ':grant', 'sector_grant', [previous], bank=bank, acquire=bank, **identity)
        if write and s['old_bytes_required']:
            current = add(prefix + ':old', 'KV_sector_old_capture', [current], bank=bank, **identity)
            current = add(prefix + ':merge', 'KV_sector_mask_merge', [current], bank=bank, **identity)
        current = add(prefix + ':capture', 'KV_sector_write_visible' if write else 'KV_sector_read_capture',
                      [current], bank=bank, **identity)
        current = add(prefix + ':consume', 'KV_sector_consumer', [current], bank=bank, **identity)
        return add(prefix + ':reverse', 'KV_sector_reverse', [current], bank=bank, release=bank, **identity)
    for g in directory['groups']:
        trace = g['source_events']; key = 'Qwen.KV.' + '.'.join(map(str, g['key']))
        native_refs = {op['pc']: op for op in g['source_operation_bindings']}
        for pc, ref in native_refs.items():
            op = operations.get(pc)
            if op is None or op['opcode'] != ref['opcode'] or op['dependencies'] != ref['dependencies'] or op['provider_binding'] != ref['provider_binding']:
                raise ValueError('KV source operation/provider/dependencies mismatch')
        parent = ['KV_parent', g['die']]
        writer = trace[0]['pc']; fence = trace[1]['pc']; reader = trace[2]['pc']; final = trace[5]['pc']
        deps = ['Qwen.PC%d.native' % writer]
        if g['die'] in tails:
            deps.append(tails[g['die']])
        current = add(key + ':parent', 'KV_parent_grant', deps, acquire=parent, PC=writer,
                      group=g['key'], writer_tag=g['writer_tag'], issuing_SM=None)
        for i, s in enumerate(g['sectors']):
            current = sector_chain(g, key + ':write:%d' % i, s, True, current, writer)
        attach(writer, current)
        # Metadata shares the SAME selected L2 bank-credit namespace. These
        # are mandatory selected32B-policy RMW demands, not observed bus counts.
        for label,address,payload in [
                ('record',trace[1]['state']['record_address'],bytes.fromhex(trace[1]['state']['record_hex'])),
                ('bitmap',trace[1]['state']['bitmap_address'],bytes([trace[1]['state']['bitmap_byte']]))]:
            deps=[current,'Qwen.PC%d.native' % fence] if label=='record' else [current]
            current=add(key+':'+label+':ready','structural_frontier',deps,PC=fence)
            patches={}
            for byte_offset,value in enumerate(payload):
                location=address+byte_offset;base=location & ~31
                patch=patches.setdefault(base,dict(mask=0,data=bytearray(32)))
                patch['mask'] |= 1 << (location-base);patch['data'][location-base]=value
            for ordinal,(base,patch) in enumerate(sorted(patches.items())):
                line=base//128;bank=['L2',g['die'],line%4,(line//4)%8]
                index=(line//32)&2047
                if index>=2044:
                    raise ValueError('metadata requires explicit installed reserved-L2 bypass')
                prefix=key+':'+label+':sector%d'%ordinal
                identity=dict(PC=fence,provider_ref=g['state_provider_ref'],address=base,
                    mask=patch['mask'],patch_hex=bytes(patch['data']).hex(),
                    metadata_bus_observed=False)
                current=add(prefix+':grant','KV_metadata_grant',[current],bank=bank,acquire=bank,**identity)
                for phase in ('old_capture','mask_merge','write_visible','consumer'):
                    current=add(prefix+':'+phase,'KV_metadata_'+phase,[current],bank=bank,**identity)
                current=add(prefix+':reverse','KV_metadata_reverse',[current],bank=bank,release=bank,**identity)
            current=add(key+':'+label,'KV_state_'+label+'_visible',[current],PC=fence,
                provider_ref=g['state_provider_ref'],address=address,bytes=len(payload),
                metadata_port_and_partial_RMW_binding=None)
        current = add(key + ':publish', 'KV_state_record_bitmap_fence', [current], PC=fence,
                      writer_tag=g['writer_tag'])
        attach(fence, current)
        current = add(key + ':acquire', 'KV_reader_acquire',
            [current, 'Qwen.PC%d.native' % reader], PC=reader, lease=g['reader_lease'])
        for i, s in enumerate(g['sectors']):
            current = sector_chain(g, key + ':read:%d' % i, s, False, current, reader)
        attach(reader, current)
        for name, event in zip(('SCORES', 'PV'), trace[3:5]):
            current = add(key + ':' + name, 'KV_' + name + '_consumer',
                [current, 'Qwen.PC%d.native' % event['pc']], PC=event['pc'],
                lease=g['reader_lease'], source_reads=event['reads'])
        current = add(key + ':release', 'KV_parent_reverse',
            [current, 'Qwen.PC%d.native' % final], release=parent, PC=final, lease=g['reader_lease'])
        attach(final, current); tails[g['die']] = current
    for node in nodes:
        if not set(node['dependencies']) <= byid.keys():
            raise ValueError('missing retained native PC dependency')
    return dict(schema='QWEN_SOURCE_KV_FINITE_BANK_EXTENSION_R1', nodes=nodes,
        phase_counts=dict(counts), native_PC_frontiers=len(operations),
        existing_native_cost_recharged=False, software_ticks_converted=False,
        HBM_command_count=None, physical_latency=None, issuing_SM_binding=None,
        metadata_bus_binding=None, complete_native_calendar=False,
        integration='replace matched existing KV-provider interval only; retain C0/V1/RF/I64 once',
        hardware_admitted=False)


def schedule_finite_extension(dag, phase_costs, native_frontiers):
    """Schedule actual DAG with finite bank holds; no zero missing durations.

    Explicit estimated software units are allowed. Native frontiers are supplied
    by the existing native schedule and never receive a generic CPU-op charge.
    A bank credit cannot be reissued before its causal reverse node finishes.
    """
    import heapq
    nodes = {n['id']: n for n in dag['nodes']}; indegree = {}; successors = {k: [] for k in nodes}
    for key, node in nodes.items():
        indegree[key] = len(node['dependencies'])
        for dep in node['dependencies']:
            if dep not in nodes:
                raise ValueError('missing DAG dependency')
            successors[dep].append(key)
    pending = []; probe = dict(indegree); ordered = []
    for key, count in probe.items():
        if not count: heapq.heappush(pending, key)
    while pending:
        key = heapq.heappop(pending); ordered.append(key)
        for child in successors[key]:
            probe[child] -= 1
            if not probe[child]: heapq.heappush(pending, child)
    if len(ordered) != len(nodes):
        raise ValueError('source consumer/lease dependency deadlock')
    needed = sorted({n['phase'] for n in nodes.values()} - {'structural_frontier', 'existing_native_calendar_frontier'})
    missing = [kind for kind in needed if phase_costs.get(kind) is None]
    missing_native = [key for key, n in nodes.items() if n['phase'] == 'existing_native_calendar_frontier' and key not in native_frontiers]
    for kind in needed:
        v = phase_costs.get(kind)
        if v is not None and (set(v) != {'units', 'provenance', 'scope'} or type(v['units']) is not int or v['units'] <= 0
                or not v['provenance'] or v['scope'] not in ('explicit_provisional_software', 'source_bound_endpoint_model')):
            raise ValueError('positive explicit endpoint cost/provenance required: ' + kind)
    if missing or missing_native:
        return dict(status='UNKNOWN_COMPLETE_SERVICE_INPUTS', missing_phase_costs=missing,
            missing_native_frontiers=missing_native, finite_DAG=True, scheduled_nodes=0,
            whole_token_latency=None, hardware_qualified=False)
    for key, value in native_frontiers.items():
        if type(value) is not int or value < 0:
            raise ValueError('existing native schedule frontier required')
    done = {}; held = {}; lease_time = {}; calendar = []; ready = [k for k, n in indegree.items() if not n]
    while ready:
        candidates = []
        for key in ready:
            n = nodes[key]; acquire = tuple(n['acquire']) if n['acquire'] else None
            if acquire is not None and acquire in held:
                continue
            start = max((done[d] for d in n['dependencies']), default=0)
            if n['phase'] == 'existing_native_calendar_frontier':
                if native_frontiers[key] < start:
                    raise ValueError('movement invalidates retained native frontier; source native retiming required: ' + key)
                start = native_frontiers[key]
            if acquire is not None:
                start = max(start, lease_time.get(acquire, 0))
            candidates.append((start, key))
        if not candidates:
            raise ValueError('finite physical credit dependency deadlock: ' + repr(held))
        start, key = min(candidates); ready.remove(key); n = nodes[key]
        duration = 0 if n['phase'] in ('structural_frontier', 'existing_native_calendar_frontier') else phase_costs[n['phase']]['units']
        finish = start + duration
        if n['acquire']:
            held[tuple(n['acquire'])] = key
        if n['release']:
            resource = tuple(n['release'])
            if resource not in held:
                raise ValueError('reverse without accepted finite resource owner')
            # The release must descend from the EXACT grant owning this bank.
            grant = held[resource]; stack = list(n['dependencies']); seen = set()
            while stack and grant not in seen:
                dep = stack.pop()
                if dep not in seen:
                    seen.add(dep); stack.extend(nodes[dep]['dependencies'])
            if grant not in seen:
                raise ValueError('foreign reverse cannot release another owner')
            del held[resource]; lease_time[resource] = finish
        done[key] = finish; calendar.append(dict(id=key, start=start, finish=finish, phase=n['phase']))
        for child in successors[key]:
            indegree[child] -= 1
            if not indegree[child]: ready.append(child)
    if held or len(done) != len(nodes):
        raise ValueError('unfinished physical lease or DAG debt')
    return dict(status='PASS_EXPLICIT_FINITE_EXTENSION', scheduled_nodes=len(done),
                schedule=calendar, extension_finish_units=max(done.values(), default=0),
                resource_credits_retired=True, time_scope='explicit software/source-model units; not ns',
                native_cost_recharged=False, hardware_qualified=False, whole_token_latency=None)


def load_qwen_kv_inputs(root=ROOT):
    base=root/(OUT+'_inputs');raw=(base/'manifest.json').read_bytes()
    if digest(raw)!='e340825eccb2ad66dab51fc3d20f49590b4280246cb3ed52be0e6314e7aee616':
        raise ValueError('exact Popper446 input manifest required')
    data={}
    for name,record in json.loads(raw).items():
        if name not in ('directory.json.gz','model.json','owner.py','Qwen_tiled.json.gz'):
            raise ValueError('known source archive origin required')
        value=(root/record['canonical_path'] if record.get('canonical_path') else base/name).read_bytes()
        if len(value)!=record['bytes'] or digest(value)!=record['sha256']:
            raise ValueError('exact observed KV input hash required')
        data[name]=value
    directory=json.loads(gzip.decompress(data['directory.json.gz']))
    native=json.loads(gzip.decompress(data['Qwen_tiled.json.gz']))
    if digest(data['Qwen_tiled.json.gz'])!=directory['original_native_sha256']:
        raise ValueError('source actual KV native pin required')
    return directory,native


def replace_provider_interval_once(existing, replacement, prior_receipts):
    """Replace one exact provider interval; all native/C0/V1/RF/I64 terms stay.

    Shape/position and operand reference are mandatory. A position-zero receipt
    cannot replace a full-context budget. Unknown cost stays unknown, not zero.
    """
    required=('interval_id','program_sha256','PC','rank','position','provider_ref','cost_domain')
    if any(k not in existing or k not in replacement for k in required):
        raise ValueError('exact retained provider interval/shape/reference required')
    if any(existing[k]!=replacement[k] for k in required):
        raise ValueError('provider interval source/position/reference differs')
    if replacement['interval_id'] in prior_receipts:
        raise ValueError('provider cost already replaced once')
    if existing['cost_domain'] not in ('explicit_provisional_software','source_bound_endpoint_model'):
        raise ValueError('provider ticks cannot convert to physical clocks')
    if set(existing.get('protected_costs',{}))!={'C0','V1','RF_mirrors','I64'}:
        raise ValueError('explicit protected existing cost buckets required')
    if not replacement.get('ordered_steps'):
        raise ValueError('instruction-dependent ordered provider steps required')
    for step in replacement['ordered_steps']:
        if type(step.get('repetitions')) is not int or step['repetitions']<=0:
            raise ValueError('explicit instruction-dependent repetitions required')
        value=step.get('cost_per_repetition')
        if value is not None and (type(value) is not int or value<=0):
            raise ValueError('unknown provider costs cannot be zero')
    total=None if any(x.get('cost_per_repetition') is None for x in replacement['ordered_steps']) else sum(x['repetitions']*x['cost_per_repetition'] for x in replacement['ordered_steps'])
    return dict(interval_identity={k:existing[k] for k in required},
        previous_provider_cost=existing.get('provider_cost'),replacement_provider_cost=total,
        protected_costs=dict(existing['protected_costs']),protected_costs_added=0,
        receipt=digest(canonical(replacement)),hardware_qualified=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=ROOT / OUT)
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args(); bound, summary = build_inventory()
    control_path=ROOT/'results/uarch/h3_complete_native_calendar_20261002/group128_execution_join_r1/actual_group128_execution.json.gz'
    inventory_path=ROOT/'results/uarch/h3_complete_native_calendar_20261002/portable_input_closure_r1/r34_portable_r4/source_inventory.json.gz'
    control=json.loads(gzip.decompress(control_path.read_bytes()))
    inventory=json.loads(gzip.decompress(inventory_path.read_bytes()))
    summary['DS_retained_shared_source_join']=verify_shared_journal_source(bound,control,inventory,(ROOT/'tools/h3_complete_native_calendar.py').read_bytes())
    summary['source_pins'][str(control_path.relative_to(ROOT))]=digest(control_path.read_bytes())
    summary['source_pins'][str(inventory_path.relative_to(ROOT))]=digest(inventory_path.read_bytes())
    directory,native=load_qwen_kv_inputs()
    dag=compile_qwen_kv_extension(directory,native)
    unresolved=schedule_finite_extension(dag,{}, {})
    summary['Qwen_KV_extension']=dict(native_PC_frontiers=dag['native_PC_frontiers'],
        phase_counts=dag['phase_counts'],nodes=len(dag['nodes']),
        missing_phase_costs=unresolved['missing_phase_costs'],
        missing_existing_native_frontiers=len(unresolved['missing_native_frontiers']),
        whole_token_latency=None,hardware_admitted=False)
    summary['source_pins']['KV_Popper446_manifest']=digest((ROOT/(OUT+'_inputs')/'manifest.json').read_bytes())
    values = {'bindings.json.gz': gzip.compress(canonical(bound), mtime=0),
              'Qwen_KV_finite_DAG.json.gz':gzip.compress(canonical(dag),mtime=0),
              'summary.json': json.dumps(summary, sort_keys=True, indent=2).encode() + b'\n'}
    if args.verify:
        for name, raw in values.items():
            if (args.out / name).read_bytes() != raw:
                raise ValueError('source-pinned causal inventory replay differs: ' + name)
    else:
        args.out.mkdir(parents=True, exist_ok=False)
        for name, raw in values.items():
            (args.out / name).write_bytes(raw)
    print(json.dumps({k: summary[k] for k in ('physical_parent_obligations', 'physical_child_obligations',
                                             'production_endpoint_observations', 'whole_token_latency')}))


if __name__ == '__main__':
    main()
