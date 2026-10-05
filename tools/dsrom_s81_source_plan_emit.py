#!/usr/bin/env python3
"""Emit the real caller factory from existing dispatch and owner TP4 order.

No map reload, operation compilation, input generation or model build. The
enclosing owner supplies its selected offer indices in actual schedule order;
rank-at-a-time dispatch and inferred grouping are deliberately not used.
"""
import argparse
import json
from pathlib import Path


def emit(dispatch, groups, stage, out):
    if dispatch['schema'] != 'dsrom.S81.C8.owner-source-dispatch.v1':
        raise ValueError('existing owner source dispatch required')
    if type(stage) is not int or not 0 <= stage < 81 or not groups:
        raise ValueError('actual native stage and nonempty TP4 schedule required')
    if dispatch.get('candidate_only') or dispatch.get('active') is False:
        raise ValueError('inactive candidate cannot enroll executable source caller')
    offers = dispatch['offers']
    selected = []
    for group in groups:
        if len(group) != 4 or any(type(i) is not int or not 0 <= i < len(offers) for i in group):
            raise ValueError('owner TP4 group needs four actual offer indices')
        ranks = {}
        for i in group:
            offer = offers[i]
            rank = offer['die_id'] % 4
            if offer['die_id'] // 4 != stage or rank in ranks:
                raise ValueError('selected offer native stage/rank mismatch')
            if offer['stage'] != stage or offer['rank'] != rank or not offer['node']:
                raise ValueError('source descriptor and physical offer differ')
            ranks[rank] = offer
        first = ranks[0]
        context = ('identity', 'token', 'position', 'user', 'epoch')
        if any(any(r[name] != first[name] for name in context) for r in ranks.values()):
            raise ValueError('TP4 source context mismatch')
        selected.append([ranks[r] for r in range(4)])
    lines = ['#include "s81_source_caller_plan.hpp"',
             '#include "s81_wavefront_stage_poller.hpp"',
             'DsromS81SourcePlan dsrom_s81_bind_source(DsromS81Runtime& runtime) {',
             f'  if(runtime.stage!={stage})throw std::runtime_error("selected source plan stage mismatch");',
             '  DsromS81SourcePlan plan;']
    for group in selected:
        lines += ['  {', '    DsromS81SourceGroup group;']
        for rank, offer in enumerate(group):
            values = [str(offer['die_id'])] + [str(offer[k])+'u' for k in
                      ('token', 'position', 'user', 'epoch', 'entry')] + [str(offer['identity'])+'ull']
            node = json.dumps(offer['node'], ensure_ascii=True)
            lines += [f'    group.ranks[{rank}].offer = {{{", ".join(values)}}};',
                      f'    group.ranks[{rank}].source_node = {node};',
                      f'    dsrom_s81_bind_inputs(runtime,group.ranks[{rank}],{node});',
                      f'    dsrom_s81_bind_receipts(runtime,group.ranks[{rank}],{node});']
        lines += ['    plan.groups.push_back(std::move(group));', '  }']
    lines += ['  return plan;', '}',
              'DsromS81WaveStagePoller::NodeOrder dsrom_s81_bind_source_nodes(DsromS81Runtime& runtime) {',
              f'  if(runtime.stage!={stage})throw std::runtime_error("selected source node order stage mismatch");',
              '  return {']
    # The caller and poller MUST consume the same owner-selected order, not
    # a second traversal of the canonical field map or sorted node IDs.
    for group in selected:
        nodes = ', '.join(json.dumps(o['node'], ensure_ascii=True) for o in group)
        lines.append('    {' + nodes + '},')
    lines += ['  };', '}']
    out = Path(out)
    with out.open('x') as f:
        f.write('\n'.join(lines)+'\n')
    return out


def emit_candidate_dispatch(execution, candidate, context, out, *,
                            layers=None, expert_ids_by_node=None, include_fields=True, endpoint_map=None, fragment_endpoints=None):
    """Pack native candidate programs using the caller's existing source objects.

    This implements compiler mechanics for c3fff's rejected placement, never
    selects that placement for execution. Live EIDs are supplied by node;
    unresolved expert choices remain source events, not guessed instructions.
    """
    import hashlib
    import tempfile
    import hdc_isa_v41 as ISA

    def require(ok, why):
        if not ok:
            raise ValueError(why)

    require(candidate.get('adopted') is False and
            candidate.get('parent_dispatch_ready') is False and
            candidate.get('hardware_admission') is False,
            'explicit inactive service candidate required')
    context = dict(context)
    for name, width in [('token', 21), ('position', 21), ('user', 10), ('epoch', 16)]:
        require(type(context.get(name)) is int and 0 <= context[name] < 1 << width,
                'actual source context bounds: ' + name)
    require(context['position'] == 1048575, 'selected DS1M source position required')
    identity = (context['epoch'] << 31) | (context['user'] << 21) | context['position']
    source = execution.source
    available = sorted({n['scope'] for n in source.nodes.values() if type(n['scope']) is int})
    selected_layers = available if layers is None else list(layers)
    require(selected_layers and selected_layers == sorted(set(selected_layers)) and
            all(type(l) is int and l in available for l in selected_layers),
            'ordered actual source layers required')
    eids = {} if expert_ids_by_node is None else dict(expert_ids_by_node)
    assignments = {a['node']: a for a in candidate['assignments']}
    require(len(assignments) == len(candidate['assignments']), 'duplicate candidate node assignment')
    movements = {m['node']: m for m in candidate['field_movements']}
    require(len(movements) == len(candidate['field_movements']), 'duplicate field movement')
    runs = {}
    covered = set()
    for run in candidate['ordered_nonfield_runs']:
        require(run['nodes'] and not any(n in covered for n in run['nodes']),
                'candidate nonfield run overlap/empty')
        for node in run['nodes']:
            n = source.nodes[node]
            a = assignments[node]
            require(n['kind'] == 'instruction' and n['scope'] == run['layer'] and
                    a['stage'] == run['stage'] and
                    a['rank_dies'] == [4*run['stage']+r for r in range(4)],
                    'candidate run/source assignment differs')
        runs[run['nodes'][0]] = run
        covered.update(run['nodes'])
    service_endpoints, field_endpoints = {}, {}
    if endpoint_map is not None:
        for home in endpoint_map['homes']:
            require(home['rank_service_die_ids'] ==
                    [4*home['service_home']+r for r in range(4)],
                    'explicit rank service die mapping differs')
            service_endpoints[home['layer_provider']] = (
                home['service_home'], home['rank_service_die_ids'])
        for fragment in (fragment_endpoints if fragment_endpoints is not None
                         else endpoint_map.get('matrix_fragments', [])):
            logical, physical = fragment['logical_stage'], fragment['physical_endpoint']
            require(logical not in field_endpoints or field_endpoints[logical] == physical,
                    'field endpoint depends on fragment; explicit fragment map required')
            field_endpoints[logical] = physical
    programs, offers, groups, events, handled, deferred = {}, [], [], [], set(), []
    end = ISA.encode(full_shape=True, unit=ISA.UNIT_END, wait=31)

    def append_group(records):
        require(len(records) == 4, 'complete TP4 native group required')
        stage = records[0]['stage']
        require(all(r['rank'] == rank and r['stage'] == stage for rank, r in enumerate(records)),
                'TP4 fragment stage/rank order differs')
        endpoint = records[0].get('physical_endpoint', stage)
        require(all(r.get('physical_endpoint', stage) == endpoint for r in records),
                'TP4 endpoint differs')
        indices = []
        for rank, record in enumerate(records):
            words = record.pop('words')
            image = programs.setdefault((endpoint, rank), [])
            entry = len(image)
            require(words and entry+len(words)+9 <= 1 << 14, 'native entry14 capacity exceeded')
            image.extend(words)
            for operation in record.get('source_pc', []):
                operation['native_pc'] = entry+operation['pc']
                operation['producer'] = 9+operation['native_pc']
                word = words[operation['pc']]
                operation['native_operation'] = dict(index=operation['producer'],
                    unit=operation['instruction']['unit'],
                    template_sha256=operation['template_word_sha256'],
                    instruction=[(word>>(32*j))&0xffffffff for j in range(64)])
            indices.append(len(offers))
            offers.append(dict(record, entry=entry, physical_endpoint=endpoint, die_id=4*endpoint+rank,
                               **context, identity=identity, candidate_only=True,
                               context_restore_required=True))
        groups.append(indices)
        return len(groups)-1

    # Source dictionary preserves the owner's literal graph order, including
    # non-instruction actions/fences. Neither numeric stage sort nor cost order
    # may replace it.
    with tempfile.TemporaryDirectory(prefix='s81-candidate-runs-') as scratch:
        for node, n in source.nodes.items():
            if n['scope'] not in selected_layers or node in handled:
                continue
            if node in runs:
                run = runs[node]
                records = []
                for rank in range(4):
                    directory = Path(scratch)/f'run{len(groups)}_r{rank}'
                    native = execution.emit_nonfield_run(run['nodes'], run['stage'], rank, directory)
                    words = [int(w, 16) for w in (directory/'prog.hex').read_text().splitlines()]
                    require(native['nodes'] and
                            [r['node'] for r in native['nodes']] == run['nodes'] and
                            native['stage'] == run['stage'] and native['rank'] == rank,
                            'actual emitted nonfield run differs')
                    require(hashlib.sha256((directory/'prog.hex').read_bytes()).hexdigest() ==
                            native['program_sha256'], 'native run image changed')
                    records.append(dict(node=node, source_nodes=list(run['nodes']),
                                        stage=run['stage'], rank=rank, provider='native-source-run',
                                        physical_endpoint=service_endpoints.get(run['layer'], (run['stage'], []))[0],
                                        source_pc=[dict(r) for r in native['nodes']], words=words))
                group = append_group(records)
                events.append(dict(kind='nonfield_run', nodes=list(run['nodes']),
                                   group=group, stage=run['stage']))
                handled.update(run['nodes'])
                continue
            require(node not in covered, 'nonfield run begins outside selected source order')
            binding = source.bindings[node]
            if binding.get('address_bound'):
                require(node in movements, 'source field movement missing')
                movement = movements[node]
                live = eids.get(node)
                indexed = binding.get('selector_slot') is not None
                if not include_fields or (indexed and live is None):
                    deferred.append(node)
                    events.append(dict(kind='deferred_field', node=node,
                                       reason='live_EIDs_required' if indexed and live is None
                                              else 'field_compilation_not_selected',
                                       movement=movement))
                    continue
                dispatches = [execution.dispatch(node, r, expert_ids=live) for r in range(4)]
                count = len(dispatches[0]['fragments'])
                require(count > 0 and all(len(d['fragments']) == count for d in dispatches),
                        'actual rank fragment count mismatch')
                field_groups = []
                for ordinal in range(count):
                    records = []
                    for rank, dispatch in enumerate(dispatches):
                        f = dispatch['fragments'][ordinal]
                        require(endpoint_map is None or f['stage'] in field_endpoints,
                                'explicit selected fragment endpoint mapping required')
                        require(f['rank'] == rank and f['die_id'] == 4*f['stage']+rank and
                                f['stage'] in movement['field_stages'],
                                'actual canonical field owner differs from movement')
                        records.append(dict(node=node, source_nodes=[node],
                                            stage=f['stage'], rank=rank, provider='field',
                                            physical_endpoint=field_endpoints.get(f['stage'], f['stage']),
                                            fragment_ordinal=ordinal, phase=f['phase'], key=f['key'],
                                            gather_local_rows=f['gather_local_rows'],
                                            ordered_K=f['ordered_K'],
                                            source_matrix_sha256=f['source_matrix_sha256'],
                                            source_predicate=dispatch['predicate'],
                                            expert_ids=None if live is None else list(live),
                                            words=[f['word'], end]))
                    field_groups.append(append_group(records))
                events.append(dict(kind='field', node=node, groups=field_groups,
                                   movement=movement, expert_ids=live))
            else:
                require(n['kind'] != 'instruction', 'candidate instruction absent from ordered runs')
                require(node in assignments, 'source action/fence assignment missing')
                # These remain real source events, not fabricated native END or
                # instructions. The owner must supply their actual consumers.
                events.append(dict(kind=n['kind'], node=node, source=n,
                                   assignment=assignments[node]))
            handled.add(node)
    out = Path(out)
    require(not out.exists(), 'fresh candidate program output required')
    out.mkdir(parents=True)
    artifacts = {}
    for (stage, rank), words in programs.items():
        directory = out/f's{stage}_r{rank}'
        directory.mkdir()
        raw = ''.join(f'{word:0512x}\n' for word in words).encode()
        (directory/'prog.hex').write_bytes(raw)
        artifacts[str((directory/'prog.hex').relative_to(out))] = hashlib.sha256(raw).hexdigest()
    by_stage, by_endpoint = {}, {}
    for group in groups:
        stage = offers[group[0]]['stage']
        by_stage.setdefault(str(stage), []).append(group)
        endpoint = offers[group[0]]['physical_endpoint']
        by_endpoint.setdefault(str(endpoint), []).append(group)
    node_order = {s: [[offers[i]['node'] for i in g] for g in gs] for s, gs in by_stage.items()}
    for offer in offers:
        offer['runtime_directory'] = str((out/f"s{offer['physical_endpoint']}_r{offer['rank']}").resolve())
    unassigned = [n for n in source.nodes.values() if type(n['scope']) is not int]
    result = dict(schema='dsrom.S81.C8.owner-source-dispatch.v1',
                  offers=offers, ownerorderedgroups=groups,
                  ownerorderedgroups_by_stage=by_stage, node_order_by_stage=node_order,
                  ownerorderedgroups_by_endpoint=by_endpoint,
                  logical_serial_stages=81, added_serial_stages=0,
                  source_order=events, selected_layers=selected_layers,
                  deferred_field_nodes=deferred, unassigned_dedicated_services=unassigned,
                  source_actions_and_fences_are_native_offers=False,
                  candidate_only=True, active=False, adopted=False,
                  parent_dispatch_ready=False, hardware_admission=False,
                  source_assignment_candidate=candidate['candidate'],
                  candidate_physical_service_union=candidate['physical_service_union'],
                  native_END_is_whole_stage_or_head_completion=False,
                  artifacts=artifacts)
    (out/'parent_dispatch.json').write_text(json.dumps(result, indent=2, sort_keys=True)+'\n')
    (out/'ownerorderedgroups.json').write_text(json.dumps(groups, indent=2)+'\n')
    (out/'node_order.json').write_text(json.dumps(node_order, indent=2)+'\n')
    return result



def emit_native_transfer(source_offer, source_node, destination_offer, program_words,
                         source_address, destination_address, words, *, dynamic=None, out=None):
    """Append the existing native SU BYP action, with literal writer enrollment.

    program_words is the destination's REAL packed mutable program image.
    The caller holds the source publication/lease: this function supplies no
    runtime acceptance, payload, tag, or publication grant.
    """
    import hashlib
    import hdc_isa_v41 as ISA
    from dsrom_s81_execution_binding import minimum_vm_extents
    for value in (source_address, destination_address, words):
        if type(value) is not int or value < 0:
            raise ValueError('literal scalar VM extent required')
    if not 0 < words <= 65535 or max(source_address+words,destination_address+words) > 1<<19:
        raise ValueError('transfer exceeds scalar VM19')
    operation = next((r for r in source_offer['source_pc']
                      if r['node'] == source_node), None)
    if operation is None:
        raise ValueError('actual emitted source operation required')
    pc = source_offer['entry']+operation['pc']
    if operation.get('native_pc') != pc or operation.get('producer') != 9+pc:
        raise ValueError('source reader association differs from emitted program')
    ranges = minimum_vm_extents(operation['instruction'], dynamic=dynamic)
    if not any(base <= source_address and source_address+words <= base+count
               for base,count in ranges):
        raise ValueError('source span not written by actual native operation')
    if source_offer['rank'] != destination_offer['rank']:
        raise ValueError('cross-rank transfer needs explicit collective, not SU copy')
    for offer in (source_offer,destination_offer):
        if (offer.get('candidate_only') is not True or
            not 0 <= offer['identity'] < 1<<47 or
            offer['die_id'] != 4*offer['physical_endpoint']+offer['rank']):
            raise ValueError('actual candidate offer association required')
    if any(source_offer[k] != destination_offer[k]
           for k in ('identity','token','position','user','epoch')):
        raise ValueError('transfer context differs; explicit version carry required')
    entry = len(program_words)
    if entry+2+9 > 1<<14:
        raise ValueError('destination program/producer14 capacity')
    instruction = dict(unit=ISA.UNIT_SU, wait=31, su_vec=ISA.VEC_I,
                       su_nout=1, su_nin=words, dst=ISA.DST_VM,
                       o_base=destination_address, o_si=1)
    # The actual wrapper prefetches A/B/C/D unconditionally. Alias unused
    # BYP operands to the same held source span, never unwritten VM address0.
    for operand in 'abcd':
        instruction.update({operand+'_src':ISA.SRC_VM,
                            operand+'_base':source_address, operand+'_si':1})
    word = ISA.encode(full_shape=True, **instruction)
    program_words.extend([word, ISA.encode(full_shape=True, unit=ISA.UNIT_END, wait=31)])
    writer = 9+entry
    def io(offer,address):
        return dict(die_id=offer['die_id'], physical_endpoint=offer['physical_endpoint'],
                    identity=offer['identity'], address=address, words=words,
                    token=offer['token'], position=offer['position'],
                    user=offer['user'], epoch=offer['epoch'])
    result = dict(provider='s81_minimum_su256', entry=entry, producer=writer,
                instruction=instruction, word_hex=f'{word:0512x}',
                word_sha256=hashlib.sha256(word.to_bytes(256,'little')).hexdigest(),
                source=dict(io(source_offer,source_address), node=source_node,
                            native_pc=pc, producer=operation['producer']),
                destination=dict(io(destination_offer,destination_address), entry=entry,
                                 producer=writer),
                publication_enrollment=dict(producer=writer,
                    output_extents=[[destination_address,words]],
                    begin='actual native GO/ready edge only',
                    native_scalar='actual registered native VM output only',
                    complete='all matching target ACKs plus publication lease'),
                reader_held_until='validated destination publication AND reverse/allcopy drain',
                capture_owner='existing NativeSu publication',
                transfer_hook='DsromS81SourceIoTransferHooks::Binding::native_copy_visible',
                transfer_accepted=None,
                source_scalar_prefetch_reads=words,
                destination_scalar_writes=words, destination_scalar_ACKs=words,
                transfer_hooks_additional_source_reads=0,
                scalar_port_parallelism=1,
                measured_transport_latency=None, measured_native_latency=None,
                candidate_only=True, parent_dispatch_ready=False,
                hardware_admission=False)
    if out is not None:
        out = Path(out)
        out.mkdir(parents=True,exist_ok=False)
        raw = ''.join(f'{w:0512x}\n' for w in program_words)
        (out/'prog.hex').write_text(raw)
        (out/'transfer.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
        literal = ','.join(f'0x{(word>>(32*j))&0xffffffff:08x}u' for j in range(64))
        sha = result['word_sha256']
        # Existing typed operation and PrefixPublication API; no new runtime
        # ABI. Enroll is a descriptor only; begin stays at actual accepted GO.
        header = [
            '#pragma once',
            '#include "s81_prefix_publication.hpp"',
            'namespace dsrom_s81_emitted_transfer {',
            'inline DsromS81PrefixOperation operation() {',
            f'  return {{{writer}u,2u,"{sha}",{{{literal}}}}};',
            '}',
            'inline void enroll(dsrom_s81_minimum::PrefixPublication& p) {',
            f'  p.enroll_literal({writer}u,{{{{{destination_address}u,{words}u}}}});',
            '}',
            f'constexpr unsigned source_producer={operation["producer"]}u;',
            f'constexpr unsigned source_address={source_address}u;',
            f'constexpr unsigned destination_address={destination_address}u;',
            f'constexpr unsigned scalar_words={words}u;',
            f'constexpr unsigned source_die={source_offer["die_id"]}u;',
            f'constexpr unsigned destination_die={destination_offer["die_id"]}u;',
            f'constexpr uint64_t identity={source_offer["identity"]}ull;',
            '}',
        ]
        (out/'transfer.hpp').write_text('\n'.join(header)+'\n')
    return result

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dispatch', type=Path, required=True)
    p.add_argument('--groups', type=Path, required=True,
                   help='owner ordered list of four offer indices for each TP4 group')
    p.add_argument('--stage', type=int, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    print(emit(json.loads(a.dispatch.read_text()), json.loads(a.groups.read_text()), a.stage, a.out))


if __name__ == '__main__':
    main()
