#!/usr/bin/env python3
"""Literal native source and causal endpoint join; no synthetic accepted events."""
import argparse
from collections import Counter
import gzip
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'results/uarch/h3_complete_native_calendar_20261002/native_event_adapter_r9'
QPATH = 'results/uarch/h3_complete_native_calendar_20261002/bounded_provider_milestone/Qwen_tiled.json.gz'
DPATH = 'results/uarch/h3_deepseek_complete_native_20261002/program_final.json.gz'
CPATH = 'results/uarch/h3_complete_native_calendar_20261002/ds_forward_leaf_join_r3/review/forward_leaf_catalog.json.gz'


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':')) + '\n').encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def need(condition, message):
    if not condition:
        raise ValueError(message)


def read(path):
    raw = (ROOT / path).read_bytes()
    return json.loads(gzip.decompress(raw) if str(path).endswith('.gz') else raw)


def verify_inputs():
    pins = read(str(BASE.relative_to(ROOT) / 'input_manifest.json'))
    for name, row in pins.items():
        raw = (ROOT / name).read_bytes()
        need(len(raw) == row['bytes'] and hashlib.sha256(raw).hexdigest() == row['sha256'], 'source pin ' + name)
    return pins


def ds_steps(code):
    """Resolve ordered SSA definitions, typed word demand and literal attrs."""
    values = {}
    steps = []
    for index, node in enumerate(code):
        src = node['src']; op = node['op']; attrs = node['attrs']
        need(all(v in values for v in src), 'source use before definition')
        need(node['dst'] not in values, 'source SSA redefinition')
        if op in ('LOAD', 'CONST'):
            width = 8 if attrs['dtype'] == 'I64' else 4
        elif op == 'F2I':
            width = 8
        elif op in ('I2F', 'FADD', 'FMUL', 'DIV', 'SQRT', 'LDEXP', 'BITCAST_U', 'BITCAST_F') or op.startswith('FCMP'):
            width = 4
        else:
            width = max((values[v]['width'] for v in src), default=8 if op == 'IOTA' else 4)
        scalars = max(1, math.prod(node['shape']))
        values[node['dst']] = {'width': width, 'bytes': width * scalars, 'definition': index}
        steps.append(dict(code_index=index, opcode=op, result=node['dst'], sources=src,
                          source_definitions=[values[v]['definition'] for v in src],
                          source_bytes=[values[v]['bytes'] for v in src], shape=node['shape'],
                          attrs_sha256=digest(attrs), result_bytes=width * scalars,
                          primitive_scalars=scalars, batches128=math.ceil(scalars / 128),
                          RF_result_words32=width // 4, arithmetic_contract='literal retained attrs; no algebraic reordering'))
    return steps


def extract(qwen, ds, forward):
    """Independent all-PC source extraction; never executes arithmetic."""
    leaves = {}; programs = {}
    qrows = []
    aliases = qwen['primitive_ABI']['Qwen_aliases']
    for kernel, code in qwen['microcode'].items():
        abi = qwen['tile_kernel_ABI'][kernel]
        need(len(code) == len(abi['steps']), 'Qwen leaf/ABI ordered step count')
        steps = []
        for i, (node, contract) in enumerate(zip(code, abi['steps'])):
            need(node['op'] == contract['op'], 'Qwen literal ordered opcode')
            native = contract['native_steps']
            # Composite declared primitives remain individually paid demands.
            need(bool(native) and (len(native) > 1 or native[0] == ('COPY' if node['op'] == 'MOV' else aliases.get(node['op'], node['op']))), 'Qwen primitive alias')
            steps.append(dict(code_index=i, opcode=node['op'], sources=node.get('src', []), result=node['dst'],
                              native_steps=native, read_spans=contract['reads'], write_span=contract['write'],
                              arithmetic_contract=contract['round_point'], source_node_sha256=digest(node)))
        leaves['Qwen/' + kernel] = dict(steps=steps, source_code_sha256=digest(code),
                                       source_pointer=QPATH + '#/microcode/' + kernel)
    for row in qwen['operations']:
        active = row['calendar_export']['physical_primitives']['kernel_invocations']; counts = Counter()
        for kernel, repetitions in active.items():
            need(type(repetitions) is int and repetitions >= 0 and kernel in qwen['microcode'], 'Qwen invoked literal kernel')
            if not repetitions: continue
            for step in leaves['Qwen/' + kernel]['steps']:
                counts.update({k: repetitions * step['native_steps'].count(k) for k in set(step['native_steps'])})
        need(dict(counts) == row['calendar_export']['physical_primitives']['native_primitive_commands'], 'Qwen instruction-dependent primitive count')
        qrows.append(dict(pc=row['pc'], family=row['opcode'], calls=active, native_commands=dict(counts)))
    programs['Qwen'] = dict(PCs=len(qrows), families=len({r['family'] for r in qrows}), PC_bindings=qrows)
    for key, leaf in forward['leaves'].items():
        if 'program' in leaf:
            code = leaf['program']['code']; pointer = CPATH + '#/leaves/' + key + '/program/code'
        else:
            tid = leaf['source_builder_args'][0]; code = ds['templates'][tid]['code']; pointer = DPATH + '#/templates/' + tid + '/code'
        raw = json.dumps(code, sort_keys=True, separators=(',', ':')).encode()
        need(hashlib.sha256(raw).hexdigest() == leaf['code_sha256'], 'DS leaf resolves retained source code')
        steps = ds_steps(code); counts = Counter(); batches = Counter()
        for step in steps:
            counts[step['opcode']] += step['primitive_scalars']; batches[step['opcode']] += step['batches128']
        need(dict(counts) == leaf['native_scalars'] and dict(batches) == leaf['native_batches128'], 'DS literal primitive repetitions')
        leaves['DeepSeek/' + key] = dict(steps=steps, source_pointer=pointer, source_code_sha256=leaf['code_sha256'],
                                        builder=leaf['source_builder'], builder_args=leaf['source_builder_args'])
    rows = []
    for row in forward['PC_bindings']:
        calls = []; counts = Counter()
        for binding in row['bindings']:
            template = forward['templates'][binding['template']]
            for ci, call in enumerate(template['calls']):
                leaf = forward['leaves'][call['leaf']]; reps = call['repetitions']
                need(type(reps) is int and reps > 0, 'positive source loop repetition')
                counts.update({op: n * reps for op, n in leaf['native_scalars'].items()})
                calls.append(dict(rank=binding['rank'], parent_template=binding['template'], call_index=ci,
                                  leaf='DeepSeek/' + call['leaf'], repetitions=reps, source_phase=call['source_phase'],
                                  dynamic_source_parameters=call['dynamic_source_parameters'], SM_partition=binding['SM_partition']))
        need(dict(counts) == row['native_scalars'], 'DS actual PC/rank call count')
        need(ds['instructions'][row['pc']]['family'] == row['family'], 'DS actual source PC family')
        rows.append(dict(pc=row['pc'], family=row['family'], dependencies=row['dependencies'], calls=calls, native_scalars=dict(counts)))
    programs['DeepSeek'] = dict(PCs=len(rows), families=len({r['family'] for r in rows}), PC_bindings=rows)
    for name, count in [('Qwen', 1737), ('DeepSeek', 2213)]:
        need([r['pc'] for r in programs[name]['PC_bindings']] == list(range(count)), 'complete ordered PC mapping')
    return dict(schema='LITERAL_NATIVE_EVENT_SOURCE_R9', programs=programs, leaves=leaves,
                production_homes='REFUSED until actual operand-view adapter', physical_qualified=False,
                current_r33_mixing_allowed=False,
                source_scope='frozen Qwen ff789 and DS c7ae forward-leaf catalog; current r33 provider/template overlay requires matching source adapter')


def source_costs():
    w6_source = (BASE/'inputs/W6.sv').read_text()
    need('reg [143:0] protected_state;' in w6_source and 'wire [70:0] raw=' in w6_source,
         'actual selected W6 protected144/raw71 source, never legacy51')
    model = read(str((BASE / 'inputs/W2_protection.json').relative_to(ROOT)))
    current = read(str((BASE / 'inputs/W2_reconciliation.json').relative_to(ROOT)))
    inventory = model['storage'] if 'storage' in model else next(v for v in model.values() if isinstance(v, dict) and 'physical_words' in v)
    need(inventory['protected_bits_perPC'] == 13608, 'selected sealed W2 inventory, not old unchecked 9144')
    c = current['early_return_calendar']
    return dict(W2=dict(selected_bits_per_PC=13608, installed=False, NC=6, MAX_OUT=16,
                        request_min_edges=c['minimum_clean_request_edges'], read_min_edges=c['minimum_clean_read_edges'],
                        write_min_edges=c['minimum_clean_write_edges'], early_read_min_edges=c['early_read_edges'],
                        early_write_min_edges=c['early_write_edges'], lookup_II_edges=c['conservative_lookup_II_edges'],
                        coded_retirement_commit_edges=c['coded_issue_commit_edge'],
                        source='22ec32816 W2 reconciliation', target_domain='streaming', target_period_ps=model['calendar']['target_period_ps']),
                W6=dict(raw_bits_per_SM=71, protected_bits_per_SM=144, replicas=32,
                        source='e951f5097 identity-bearing retained W6', normal_min_edges=19,
                        target_domain='streaming', target_period_ps=model['calendar']['target_period_ps']),
                upper_bound_edges=None, scope='prospective positive source-clock protocol minimum; held/contended/CDC/drain maxima UNKNOWN',
                fixture_ns_as_upper_bound=False, whole_token_ns=None, area_debit='matched replacement only; no gross addition')


def direct_RF_demand(qwen, plan, *, entering_workspace=None):
    """Source-enrolled PC40 demand, live-home collision proof, no W2 owner.

    Existing RF homes are enumerated by lifetime and physical slot. A runtime
    workspace snapshot is mandatory for executable admission, independently of
    the source metadata proof. Missing snapshots cannot mean an empty machine.
    """
    command = plan['native_command']; pc = command['source_PC']; gate = plan['source_gate_home']
    need(pc == 40 and qwen['operations'][pc]['opcode'] == 'SILU_GATE', 'actual selected PC40 caller')
    need(plan['source_step'] == qwen['microcode']['exp'][0] == dict(dst='ex',op='FMAX',src=['x','f32(-87)']), 'actual FMAX leaf')
    need(command['source_bittypes'] == [32,32] and command['active_lanes'] == 128, 'full binary32 caller')
    need(plan['parent55'] is None and all(t['parent55'] is None for t in plan['transient_enrollment']), 'direct RF must not invent HBM owner')
    need(gate['RFslot9'] == 38 and gate['mirrors'] == 2 and gate['version'] in qwen['operations'][pc]['reads'], 'actual source gate RF home')
    value = next(v for v in qwen['operands'] if v['version'] == gate['version'])
    need(value['lease'] == gate['lease'] and any(h['provider_ref'] == gate['source_provider_ref'] and h['rank'] == 0 and h['SM'] == 0 for h in value['homes']), 'actual source gate lease/provider')
    need(command['program_sha256'] == 'ff789c0c464b6a13b96f197a10004bd79c0b478f9932404c1bfe25e30dd3aabc', 'exact actual Qwen program')
    layout = qwen['feasibility']['RF_layout']; start,end = layout['primitive_scratch']
    slots = [t['RF_vectors'][0] for t in plan['transient_enrollment']]
    need(slots == [17,18,19] and all(start <= s < end for s in slots), 'source-selected transient layout')
    need(len({t['lease'] for t in plan['transient_enrollment']}) == 3 and all(t['generation'] == command['generation'] for t in plan['transient_enrollment']), 'transient lease identities')
    live = []
    for value in qwen['operands']:
        if value['birth_pc'] <= pc <= value['retire_pc']:
            for home in value['homes']:
                backing = home.get('home', {})
                if backing.get('class') == 'RF':
                    for slot in range(backing['slot_first'],backing['slot_first'] + backing['vectors']):
                        live.append(dict(rank=home['rank'],SM=home['SM'],slot=slot,version=value['version'],lease=value['lease']))
    need(not any(h['rank'] == 0 and h['SM'] == 0 and h['slot'] in slots for h in live), 'workspace aliases existing live source home')
    if entering_workspace is not None:
        need(type(entering_workspace) is list and all(set(x) >= {'slot','lease','rank','SM'} for x in entering_workspace), 'actual entering workspace lease snapshot')
        need(not any(x['rank'] == 0 and x['SM'] == 0 and x['slot'] in slots for x in entering_workspace), 'workspace aliases entering active lease')
    actions = plan['ordered_producer_actions']
    need([a['action'] for a in actions] == ['read_source_home','BITCAST_U','broadcast_U32','XOR','BITCAST_F','broadcast_F32','FMAX'], 'actual NEG/constant/FMAX producer order')
    need(actions[2]['bits'] == 0x80000000 and actions[5]['bits'] == 0xc2ae0000, 'literal signbit/minus87 source')
    need(qwen['microcode']['exp'][1] == dict(dst='ex',op='FMIN',src=['ex','f32(88)']), 'actual next consumer')
    events = []; previous = None; min_edge = 0; allocation = {}; releases = []; phase_counts = Counter()
    def event(phase, *, edges, source, **extra):
        nonlocal previous,min_edge
        key = 'Qwen/PC40/tile' + str(gate['word_start']) + '/' + str(len(events))
        row = dict(eventID=key,phase=phase,depends_on=[] if previous is None else [previous],
                   target_domain='streaming',target_period_ps=833.333333,
                   min_edges=edges,max_edges=None,start_min_edges=min_edge,end_min_edges=min_edge+edges,
                   source=source,accepted_receipt=False,**extra)
        events.append(row); previous=key; min_edge+=edges; phase_counts[phase]+=1
        return key
    for index, action in enumerate(actions):
        reads = action.get('source_slots', [action['source_slot']] if 'source_slot' in action else [])
        for slot in reads: need(slot in allocation, 'source producer consumed before live allocation')
        target = action.get('destination_slot'); need(target in slots, 'actual action workspace destination')
        # Source consumes each old value before the same port overwrites it.
        event('RF_read_capture', edges=1, source='prospective explicit single read/capture edge; actual RF loaded latency unknown',
              action=index,read_slots=reads,read_ports_used=len(reads),payload_bytes=512*max(1,len(reads)))
        if target in allocation:
            releases.append(dict(slot=target,old_value=allocation[target],consumed_before=previous,
                                 deferred_reverse_required=True,actual_reverse_receipt=None))
            event('old_value_consumer_reverse',edges=2,source='prospective positive source reverse boundary; installed directRF owner producer UNKNOWN',slot=target)
        if index:
            event('native_primitive',edges=1,source='explicit prospective per-primitive minimum, exact loaded opcode latency UNKNOWN',
                  opcode=action['action'],primitive_scalars=128,source_action=index)
        event('both_RF_mirror_write',edges=1,source='c4c794 actual simultaneous mirrored write edge',slot=target,physical_copies=2,payload_bits_per_copy=4096)
        event('common_RF_ACK',edges=2,source='c4c794 registered ACK capture and held handshake minimum',slot=target)
        # No synthetic owner46 is minted for this data-only enrollment.
        if index == 6:
            event('W6_visibility',edges=2,source='e951f5097 age>=1 visibility boundary, identity adapter UNKNOWN',parent55=None,slot=target)
        allocation[target] = 'action' + str(index)
    event('source_next_consumer',edges=1,source='literal exp step1 FMIN requires output ex; RF read/capture minimum',
          opcode='FMIN',source_slot=19,literal_bits=0x42b00000)
    event('W6_consumer_reverse_CDC_drain_retire',edges=15,source='e951f5097 remaining positive normal protocol boundary minimum; full19-edge fence paid once with visibility/ACK',
          parent55=None,allcopies_producer='UNKNOWN',held_output=True)
    return dict(schema='SOURCE_ENROLLED_PC40_RF_EVENT_DEMAND_R9',source_PC=40,template='exp',ordered_step=0,
                caller_kernel_repetitions=qwen['operations'][40]['calendar_export']['physical_primitives']['kernel_invocations']['exp'],
                selected_tile_start=gate['word_start'],events=events,phase_counts=dict(phase_counts),
                existing_live_RF_homes=live,entering_workspace=entering_workspace,
                workspace_admission='REFUSED_MISSING_ENTERING_LIVE_LEASES' if entering_workspace is None else 'PROSPECTIVE_DISJOINT_SOURCE_ALLOCATION',
                workspace_overwrite_edges=releases,remaining_values=allocation,
                actual_accepted_capture_ACK_consumer_reverse_events=0,
                W2_HBM_commands=0,W2_owner46=None,parent55=None,
                W6_identity_adapter='UNKNOWN direct-RF caller identity; never synthetic HBM owner',
                RF_inventory=dict(read_ports=2,write_ports=1,mirrors=2,SMs=32),
                minimum_clock_edges=min_edge,finite_service_upper_edges=None,whole_token_ns=None,
                payload_qualified=False,hardware_qualified=False,
                scope='literal producer/consumer demand, source-static existing-home proof; runtime workspace and actual receipts separate')


PHASES = ('accepted', 'capture', 'W2_retirement_commit', 'continuation', 'common_ACK', 'visible', 'consumer', 'reverse', 'reverse_CDC', 'retire')
PORTS = dict(accepted='W2_request',capture='capture32',continuation='metadata',common_ACK='RF_mirror_ACK',
             W2_retirement_commit='W2_coded_commit',visible='W6',consumer='W6',reverse='R14_reverse',reverse_CDC='reverse_CDC',retire='W6')


def resolve_source_node(reference, qwen, ds, forward):
    """Bind PC, actually invoked leaf, ordered index and repetition to bytes."""
    model = reference['model']; pc = reference['PC']; step = reference['code_index']
    need(type(pc) is int and type(step) is int, 'integer actual source index')
    if model == 'Qwen':
        need(0 <= pc < len(qwen['operations']), 'Qwen actual PC')
        row = qwen['operations'][pc]; kernel = reference['leaf']
        active = row['calendar_export']['physical_primitives']['kernel_invocations']
        need(kernel in active and active[kernel] > 0, 'actually invoked Qwen kernel')
        code = qwen['microcode'][kernel]; reps = active[kernel]
    else:
        need(model == 'DeepSeek' and 0 <= pc < len(ds['instructions']), 'DeepSeek actual PC')
        row = forward['PC_bindings'][pc]; tid = reference['parent_template']; rank = reference['rank']
        need(any(b['template'] == tid and b['rank'] == rank for b in row['bindings']), 'actual source template/rank')
        calls = forward['templates'][tid]['calls']; ci = reference['call_index']
        need(type(ci) is int and 0 <= ci < len(calls), 'actual ordered forward call')
        call = calls[ci]; need(reference['leaf'] == call['leaf'], 'source leaf identity')
        leaf = forward['leaves'][call['leaf']]; reps = call['repetitions']
        need(not call['dynamic_source_parameters'], 'dynamic row/rank source builder adapter required; no placeholder row credit')
        code = leaf['program']['code'] if 'program' in leaf else ds['templates'][leaf['source_builder_args'][0]]['code']
        need(hashlib.sha256(json.dumps(code, sort_keys=True, separators=(',', ':')).encode()).hexdigest() == leaf['code_sha256'], 'literal DS code hash')
    need(type(reference['repetition']) is int and 0 <= reference['repetition'] < reps and reference['repetitions'] == reps, 'source-bound repetition')
    need(0 <= step < len(code), 'actual ordered microstep')
    node = code[step]
    need(reference['node_sha256'] == digest(node), 'source instruction digest')
    return node


def join_endpoint_events(reference, node, events, capacities, costs, *, production_binding=None):
    """Join actual received events, identity/lifecycle, finite port serialization.

    No event is generated here. Missing phases remain UNKNOWN. Prospective
    minimum costs cannot supply a finite production guarantee.
    """
    need(reference['node_sha256'] == digest(node), 'exact actual native source instruction')
    need(reference['opcode'] == node['op'] and reference['sources'] == node['src'] and reference['destination'] == node['dst'], 'actual source operands')
    need(type(reference['repetition']) is int and 0 <= reference['repetition'] < reference['repetitions'], 'source repetition range')
    need(set(capacities) == {'SMs', 'fragment_credit', 'child_rows_per_SM', 'RF_mirrors', 'sector_bytes', 'frame_bytes'}, 'exact finite resource inventory')
    need(capacities == dict(SMs=32, fragment_credit=1, child_rows_per_SM=128, RF_mirrors=2, sector_bytes=32, frame_bytes=512), 'selected resource capacity')
    seen = {}; last = {}; occupied = {}; phase_counts = Counter(); port_end = {}; rows = []
    fragments = {}; owners = {}; unknown = []; retired = set(); child_identity = {}; consumed = set(); W2_debt = Counter(); committed = set()
    for event in events:
        key = event['eventID']; phase = event['phase']; identity = tuple(event['identity'])
        need(key not in seen and phase in PHASES, 'unique actual event/known phase')
        need(len(identity) == 5 and all(type(x) is int for x in identity), 'rank/SM/owner46/RFslot9/generation identity')
        rank, sm, owner, slot, generation = identity
        need(0 <= rank < 96 and 0 <= sm < 32 and 0 <= owner < 2**46 and 0 <= slot < 512 and generation >= 0, 'actual identity widths')
        need(reference['model'] != 'Qwen' or rank < 2, 'actual Qwen rank inventory')
        need(event['accepted'] is True and event['native_ref'] == reference, 'actual accepted handshake/source reference')
        need(event['domain'] == 'streaming' and type(event['reset_epoch']) is int and event['reset_epoch'] >= 0, 'source domain/reset epoch')
        need(all(dep in seen for dep in event['depends_on']), 'causal event order')
        ownerkey = (rank, sm, owner, slot, generation)
        need(ownerkey not in retired, 'completion or reuse of retired identity')
        epoch = event['reset_epoch']
        if ownerkey in owners:
            need(owners[ownerkey] == epoch, 'stale reset epoch')
        else:
            need(phase == 'accepted', 'unowned completion'); owners[ownerkey] = epoch
        prior = last.get(ownerkey)
        if prior:
            need(prior in event['depends_on'], 'causal owner edge omitted')
        child = event.get('child'); context = (rank, sm); lifecycle = occupied.setdefault(ownerkey, {})
        if phase == 'accepted':
            need(child not in lifecycle and type(child) is int and 0 <= child < 128, 'child allocation/alias')
            need(sum(len(v) for k,v in occupied.items() if k[:2] == context) < 128, 'finite retained child capacity exhausted')
            fragment = (context, event['fragment'])
            need(type(event['fragment']) is int and event['fragment'] == child // 2, 'actual child/64B fragment association')
            need(sum(v in ('accepted','captured') for k,group in occupied.items() if k[:2] == context for v in group.values()) < 2, 'one64B fragment ticket contains only two sectors')
            need(context not in fragments or fragments[context] == fragment, 'single fragment credit exhausted')
            fragments[context] = fragment; lifecycle[child] = 'accepted'
            wire = (event['child_owner46'], event['backend16'])
            need(all(type(x) is int for x in wire) and 0 <= wire[0] < 2**46 and 0 <= wire[1] < 65536, 'full physical child/backend identity')
            need((wire[0] >> 36) & 7 < 6, 'actual NC6 child client')
            need(not any(k[0][0] == rank and v == wire for k,v in child_identity.items()), 'physical child alias before reverse')
            bank = (rank,wire[0] >> 39,(wire[0] >> 36) & 7)
            need(W2_debt[bank] < 16, 'finite W2 NC6/MAX16 accepted debt exhausted')
            W2_debt[bank] += 1
            child_identity[(ownerkey, child)] = wire
        elif phase == 'capture':
            need(lifecycle.get(child) == 'accepted' and event['payload_bytes'] == 32, 'capture before accepted32B sector')
            need(child_identity[(ownerkey, child)] == (event['child_owner46'], event['backend16']), 'wrong child or truncated backend generation')
            lifecycle[child] = 'captured'
        elif phase == 'W2_retirement_commit':
            need(lifecycle.get(child) in ('captured','retained') and (ownerkey,child) not in committed and event['coded_commit_complete'] is True, 'source coded retirement commit required')
            wire = child_identity[(ownerkey,child)]
            need(wire == (event['child_owner46'],event['backend16']), 'wrong coded retirement owner')
            committed.add((ownerkey,child)); W2_debt[(rank,wire[0] >> 39,(wire[0] >> 36) & 7)] -= 1
        elif phase == 'continuation':
            pair = event['children']; need(len(pair) == 2 and len(set(pair)) == 2 and all(lifecycle.get(c) == 'captured' for c in pair), 'both64B stores before continuation')
            need(fragments.get(context) == (context, event['fragment']), 'stale fragment continuation')
            for c in pair: lifecycle[c] = 'retained'
            del fragments[context]
        elif phase == 'common_ACK':
            need(set(lifecycle) == set(range(16)) and all(v == 'retained' for v in lifecycle.values()) and event['RF_mirrors'] == 2, 'full frame/both RF copies before ACK')
            need(seen[prior]['phase'] == 'continuation', 'duplicate or unordered common ACK')
        elif phase in ('visible', 'consumer'):
            need(seen[prior]['phase'] == ('common_ACK' if phase == 'visible' else 'visible'), 'premature visibility/consumer')
            if phase == 'consumer': consumed.add(ownerkey)
        elif phase == 'reverse':
            need(lifecycle.get(child) == 'retained' and ownerkey in consumed, 'reverse before consumer or wrong child')
            need((ownerkey,child) in committed, 'physical reverse before coded W2 retirement')
            need(child_identity[(ownerkey, child)] == (event['child_owner46'], event['backend16']), 'wrong reverse child/backend')
            lifecycle[child] = 'reversed'
        elif phase == 'reverse_CDC':
            need(lifecycle.get(child) == 'reversed' and event['matched'] is True, 'matched reverse CDC required')
            need(child_identity[(ownerkey, child)] == (event['child_owner46'], event['backend16']), 'wrong reverse CDC child/backend')
            del lifecycle[child]; del child_identity[(ownerkey, child)]
        elif phase == 'retire':
            need(not lifecycle and event['allcopies_drained'] is True and context not in fragments, 'retirement before all-copy drain')
            retired.add(ownerkey)
        cost = costs.get(phase)
        need(cost and type(cost['min_edges']) is int and cost['min_edges'] > 0 and cost['source'] and cost['domain'] == event['domain'], 'positive source-clock cost required')
        floor = {'accepted':8,'capture':8,'W2_retirement_commit':4,'common_ACK':2,'visible':2,
                 'consumer':2,'reverse_CDC':3,'retire':2}.get(phase,1)
        need(cost['min_edges'] >= floor, 'selected source phase minimum; coded commit is four edges, not one')
        upper = cost.get('max_edges')
        need(upper is None or type(upper) is int and upper >= cost['min_edges'], 'finite explicit service bound')
        if upper is None: unknown.append(key)
        need(event['port'] == PORTS[phase], 'selected actual unit port, no invented parallel resource')
        # W2/R14 contend at the physical PC across all SMs; RF/capture are per SM.
        unit = ('PC', event['child_owner46'] >> 39) if phase in ('accepted','W2_retirement_commit','reverse') else ('SM',sm)
        resource = (event['domain'], rank, unit, event['port'])
        start = max([port_end.get(resource, 0)] + [seen[d]['end_min_edges'] for d in event['depends_on']])
        row = dict(event, start_min_edges=start, end_min_edges=start + cost['min_edges'])
        seen[key] = row; rows.append(row); port_end[resource] = row['end_min_edges']; last[ownerkey] = key; phase_counts[phase] += 1
    missing = [phase for phase in PHASES if not phase_counts[phase]]
    debt = sum(len(v) for v in occupied.values())
    physical = bool(production_binding and production_binding.get('source_span_admitted') is True)
    return dict(events=rows, phase_counts=dict(phase_counts), missing_phases=missing, retained_child_debt=debt,
                unknown_service_eventIDs=unknown, production_status='REFUSED' if not physical else 'BOUND_SPAN_SERVICE_UNQUALIFIED',
                outstanding_W2_debt=sum(W2_debt.values()),
                finite_service_guarantee=False, complete_lifecycle=not missing and not debt and not fragments,
                scope='actual supplied source events; minimum-edge schedule only; no synthetic acceptance, no hardware rate')


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--verify', action='store_true'); args = parser.parse_args()
    pins = verify_inputs(); qwen = read(QPATH); model = extract(qwen, read(DPATH), read(CPATH)); costs = source_costs()
    plan = read(str((BASE / 'inputs/Ampere_PC40.json').relative_to(ROOT)))['selected_C0_command']
    direct = direct_RF_demand(qwen, plan)
    outputs = {'literal_source.json.gz': gzip.compress(canonical(model), mtime=0), 'source_costs.json': canonical(costs),
               'PC40_direct_RF_demand.json':canonical(direct)}
    summary = dict(schema='NATIVE_EVENT_ADAPTER_R9', input_sha256={k:v['sha256'] for k,v in pins.items()},
                   programs={k:{'PCs':v['PCs'], 'families':v['families']} for k,v in model['programs'].items()},
                   literal_leaves=len(model['leaves']), literal_ordered_steps=sum(len(l['steps']) for l in model['leaves'].values()),
                   production_homes='REFUSED', whole_token_ns=None, W2_selected_protected_bits_per_PC=13608,
                   W6_selected_raw_protected_bits=[71,144], current_r33_join='UNKNOWN; baseline immutable source only',
                   PC40_scope={'workspace_admission':direct['workspace_admission'],'actual_receipts':0,
                               'caller_repetitions':direct['caller_kernel_repetitions'],'minimum_clock_edges':direct['minimum_clock_edges'],'W2_HBM_commands':0},
                   artifact_sha256={k:hashlib.sha256(v).hexdigest() for k,v in outputs.items()})
    outputs['summary.json'] = canonical(summary)
    for name, raw in outputs.items():
        path = BASE / name
        if args.verify: need(path.read_bytes() == raw, 'byte-exact replay ' + name)
        else: need(not path.exists() or path.read_bytes() == raw, 'immutable evidence overwrite refused'); path.write_bytes(raw)
    print(json.dumps(summary, sort_keys=True))


if __name__ == '__main__':
    main()
